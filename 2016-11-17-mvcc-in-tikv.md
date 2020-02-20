---
title: MVCC in TiKV
author: ['Ivan Yang']
date: 2016-11-17
summary: This document gives an overview of MVCC implementation in TiKV.
tags: ['TiKV', 'MVCC']
aliases: ['/blog/2016/11/17/mvcc-in-tikv/']
categories: ['Engineering']
---

## Introduction to concurrency control

Serializability is the classical concurrency scheme. It ensures that a schedule for executing concurrent transactions is equivalent to one that executes the transactions serially in some order. Though serializablity is a great concept, it is hard to implement efficiently. A classical solution is a variant of [Two-Phase Locking, aka 2PL](https://en.wikipedia.org/wiki/Two-phase_locking). Using 2PL, the database management system (DBMS) maintains read and write locks to ensure that conflicting transactions are executed in a well-defined order, or in serializable execution schedules. Locking, however, has several drawbacks. First, readers and writers block each other. Second, most transactions are read-only and are therefore harmless from a transaction-ordering perspective. Under a locking-based isolation mechanism, no update transaction is allowed on a data object that is being read by a potentially long-running read transaction. Thus the update has to wait until the read finishes. This severely limits the degree of concurrency in the system.

*Multi-Version Concurrency Control (MVCC)* is an elegant solution for this problem, where each update creates a new version of the data object instead of updating it in-place, so that concurrent readers can still see the old version while the update transaction proceeds. Such a strategy can prevent read-only transactions from waiting. In fact, locking is not required at all. This is an extremely desirable property and the reason why many database systems like PostgreSQL, Oracle, and Microsoft SQL Server implement MVCC.

In this post, we will explore the complexities of implementation of MVCC in TiKV.

## MVCC in TiKV

Let's dive into `TiKV`'s MVCC implementation, which is located at [src/storage](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mod.rs).

### Timestamp Oracle(TSO)

Since `TiKV` is a distributed storage system, it needs a globally unique time service, called `Timestamp Oracle`(TSO), to allocate a monotonic increasing timestamp. Similar to the TrueTime API from Google's [Spanner](http://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi2012.pdf), this service is implemented in Placement Driver (PD) in TiKV. Every `TS` represents a monotonic increasing timestamp.

### Storage

To dive into the transaction part in `TiKV`, [src/storage](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage) is a good starting point. `Storage` is a struct that actually receives the Get/Scan commands.

```rust
pub struct Storage {
    engine: Box<Engine>,
    sendch: SendCh<Msg>,
    handle: Arc<Mutex<StorageHandle>>,
}


impl Storage {
    pub fn start(&mut self, config: &Config) -> Result<()> {
        let mut handle = self.handle.lock().unwrap();
        if handle.handle.is_some() {
            return Err(box_err!("scheduler is already running"));
        }


        let engine = self.engine.clone();
        let builder = thread::Builder::new().name(thd_name!("storage-scheduler"));
        let mut el = handle.event_loop.take().unwrap();
        let sched_concurrency = config.sched_concurrency;
        let sched_worker_pool_size = config.sched_worker_pool_size;
        let sched_too_busy_threshold = config.sched_too_busy_threshold;
        let ch = self.sendch.clone();
        let h = try!(builder.spawn(move || {
            let mut sched = Scheduler::new(engine,
                                           ch,
                                           sched_concurrency,
                                           sched_worker_pool_size,
                                           sched_too_busy_threshold);
            if let Err(e) = el.run(&mut sched) {
                panic!("scheduler run err:{:?}", e);
            }
            info!("scheduler stopped");
        }));
        handle.handle = Some(h);


        Ok(())
    }
}
```

This `start` function in the example above explains how the storage struct runs.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('MVCC in TiKV', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('MVCC in TiKV', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Engine

[Engine](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/engine/mod.rs#L44) is the trait which describes the actual database used in the storage system. It is implemented in [raftkv](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/engine/raftkv.rs#L91) and [rocksdb_engine](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/engine/rocksdb.rs#L137).

### StorageHandle

`StorageHandle` is the struct that handles commands received from `sendch`. The I/O is processed by [`mio`](https://github.com/carllerche/mio).

Then functions like `async_get` and `async_batch_get` in the `storage` struct will send the corresponding commands to the channel, which can be obtained by the scheduler to execute asynchronously.

The MVCC layer is called in [Scheduler](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/txn/scheduler.rs#L763).
The storage receives commands from clients and sends commands as messages to the scheduler. Then the scheduler will process the command or [call corresponding asynchronous function](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/txn/scheduler.rs#L643). There are two types of operations - read and write. Read is implemented in [MvccReader](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/reader.rs#L20), which is easy to understand so we will not elaborate on it. Let's focus on write, which is the core of MVCC implementation.

### MVCC

#### Column family

Compared with Percolator where the information such as Lock is stored by adding an extra column to a specific row, TiKV uses a column family (CF) in RocksDB to handle all the information related to Lock. To be specific, TiKV stores the Key-Values, Locks and Writes information in `CF_DEFAULT`, `CF_LOCK`, and `CF_WRITE`.

All the values of the CF are encoded as following:

| | Default | Lock | Write |
| --- | --- | --- | --- |
| **Key** | z{encoded_key}{start_ts(desc)} | z{encoded_key} | z{encoded_key}{commit_ts(desc)} |
| **Value** | {value} | {flag}{primary_key}{start_ts(varint)} | {flag}{start_ts(varint)} |

More details can be found [here](https://github.com/pingcap/tikv/issues/1077).

#### Transaction model

Here comes the core of the transaction model for TiKV, which is MVCC powered by 2-phase commit. There are two stages in one transaction:

- **Prewrite**

  1. The transaction starts. The client obtains the current timestamp (`startTS`) from TSO.
  2. Select one row as the primary row, the others as the secondary rows.
  3. Check [whether there is another lock on this row](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/txn.rs#L71) or whether there are any commits located after `startTS`. These two situations will lead to conflicts. If either happens, the commit fails and [rollback](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/txn.rs#L115) will be called.
  4. [Lock the primary row](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/txn.rs#L80).
  5. Repeat the steps above on secondary rows.

- **Commit**

  1. Obtain the commit timestamp `commit_ts` from TSO.
  2. Check whether the lock on the primary row still exists. Proceed if the lock is still there. Roll back if not.
  3. Write to column `CF_WRITE` with `commit_ts`.
  4. Clear the corresponding primary lock.
  5. Repeat the steps above on secondary rows.

#### Garbage collector

It is easy to predict that there will be more and more MVCC versions if there is no [Garbage Collector](https://github.com/pingcap/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/txn.rs#L143) to remove the invalid versions. But we cannot simply remove all the versions before a safe point, for there may be only one version for a key, which must be kept. In TiKV, if there is any `Put` or `Delete` records before the safe point, then all the latter writes can be deleted; otherwise only `Delete`, `Rollback` and `Lock` will be deleted.

