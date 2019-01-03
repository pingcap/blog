---
title: MVCC in TiKV
author: ['Ivan Yang']
date: 2016-11-17
summary: This document gives an overview of MVCC implementation in TiKV.
tags: ['TiKV', 'Engineering', 'Rust']
aliases: ['/blog/2016/11/17/mvcc-in-tikv/']
categories: ['Engineering']
---

## Introduction to concurrency control

Transaction isolation is important for database management system. Because database should provide an illusion that the user is the only one who connects to the database, which greatly simplifies application development. But, the concurrency controlling problems like data races must be resolved since there will be a lot of connections to the database. Due to this background, the database management system (DBMS) ensures that the resulting concurrent access patterns are safe, ideally by serializablity.

Though serializablity is a great concept, it is hard to implement efficiently. A classical solution is a variant of [Two-Phase Locking, aka 2PL][1]. Using 2PL, the DBMS maintains read and write locks to ensure that conflicting transactions are executed in a well-defined order, which results in serializable execution schedules. But, locking, however, has several drawbacks: First, readers and writers block each other. Second, most transactions are read-only and therefore harmless from a transaction-ordering perspective. Using a locking-based isolation mechanism, no update transaction is allowed to change a data object that has been read by a potentially long-running read transaction and thus has to wait until the read transaction finishes. This severely limits the degree of concurrency in the system.

*Multi-Version Concurrency Control (MVCC)* is an elegant solution for this problem, in which each update creates a new version of the data object instead of updating data objects in-place, such that concurrenct readers can still see the old version while the update transaction proceeds concurrently. Such stradegy can prevent read-only transactions from waiting, and in fact do not have to use locking at all. This is an extremely desirable property and the reason why many DBMS implements MVCC, e.g., PostgreSQL, Oracle, Microsoft SQL Server.

## MVCC in TiKV

Let's dive into `TiKV`'s MVCC implementation, located at [src/storage](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mod.rs).

### Timestamp Oracle(TSO)

Since `TiKV` is a distributed storage system, it needs a globally unique time service, called `Timestamp Oracle`(TSO), to allocate a monotonic increasing timestamp. This function is provided in `PD` in TiKV, which is provided by `TrueTime API` by using multiple modern clock references(GPS and atomic locks) in [Spanner](http://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi2012.pdf). So keep in mind that every `TS` represents a monotonic increasing timestamp.

### Storage

To dive into the Transaction part in `TiKV`, [src/storage](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage) is a good beginning, which implements the entries. `Storage` is a struct that actually receives the get/Scan commands.

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

This `start` function helps to explain how a storage runs.

### Engine

[Engine](https://github.com/pingcap/tikv/blob/master/src/storage/engine/mod.rs#L44) is the trait which describes the actual database used in storage system, which is implemented in [raftkv](https://github.com/pingcap/tikv/blob/master/src/storage/engine/raftkv.rs#L91) and [Enginerocksdb](https://github.com/pingcap/tikv/blob/master/src/storage/engine/rocksdb.rs#L66).

### StorageHandle

`StorageHandle` is the struct that handles commands received from `sendch` powered by [`mio`](https://github.com/carllerche/mio).

Then the following functions like `async_get` and `async_batch_get` will send the corresponding commands to the channel, which can be got by the scheduler to execute asynchronously.

All right, the MVCC protocol calling is exactly implemented in [Scheduler](https://github.com/pingcap/tikv/blob/master/src/storage/txn/scheduler.rs#L763).
The storage receives commands from clients and sends commands as messages to the scheduler. Then the scheduler will process the command or [call corresponding asynchronous function](https://github.com/pingcap/tikv/blob/master/src/storage/txn/scheduler.rs#L643). There are two types of operations, reading and writing. Reading is implemented in [MvccReader](https://github.com/tikv/tikv/blob/1050931de5d9b47423f997d6fc456bd05bd234a7/src/storage/mvcc/reader.rs#L20), which is easy to understand. Writing part is the core of MVCC implementation.

### MVCC

Here comes the core of the transaction model of TiKV, which called 2-Phase Commit powered by MVCC. There are two stages in one transaction.

#### Prewrite

1. Select one row as the primary row, the others as the secondary rows.
2. [Lock the primary row](https://github.com/pingcap/tikv/blob/master/src/storage/mvcc/txn.rs#L80). Before locking, it will check [whether there is other locks on this row](https://github.com/pingcap/tikv/blob/master/src/storage/mvcc/txn.rs#L71) or whether there are some commits located after startTS. These two situations will lead to conflicts.If any of themhappens, [rollback](https://github.com/pingcap/tikv/blob/master/src/storage/mvcc/txn.rs#L115) will be called.
3. Repeat the  operations on secondary row.

#### Commit

1. Write to the `CF_WRITE` with commitTS.
2. Delete the corresponding lock.

#### Rollback

[Rollback](https://github.com/pingcap/tikv/blob/master/src/storage/mvcc/txn.rs#L115) is called when there are conflicts during the `prewrite`.

#### Garbage collector
It is easy to predict that there will be more and more MVCC versions if there is no [Garbage Collector](https://github.com/pingcap/tikv/blob/master/src/storage/mvcc/txn.rs#L143) to remove the invalid versions. But we cannot just simply removeall the versions before a safe point. Since there maybe only one version for a key, it will be kept. In `TiKV`, if there is  any `Put` or `Delete` before the safe point, then all the latter writes can be deleted, otherwise only `Delete`, `Rollback` and `Lock` will be deleted.

# TiKV-Ctl for MVCC

During developing and debugging, sometimes we need to know the MVCC version information.So we develop a new tool for searching the MVCC information. `TiKV` stores the Key-Values, Locks and Writes information in `CF_DEFAULT`, `CF_LOCK`, `CF_WRITE`.
All the  values of the CF are encoded as following:

|  | default | lock | write |
| --- | --- | --- | --- |
| **key** | z{encoded_key}{start_ts(desc)} | z{encoded_key} | z{encoded_key}{commit_ts(desc)} |
| **value** | {value} | {flag}{primary_key}{start_ts(varint)} | {flag}{start_ts(varint)} |

Details can be found [here](https://github.com/pingcap/tikv/issues/1077).

Since all the MVCC version information is stored as CF Key-Values in RocksDB, to search for a Key's version information, we just need to encode the key with different formats then search in the corresponding CF. The CF Key-Values are modeled by [MvccKv](https://github.com/pingcap/tikv/blob/master/src/bin/tikv-ctl.rs#L210).

[1]: https://en.wikipedia.org/wiki/Two-phase_locking
