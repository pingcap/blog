---
title: A TiKV Source Code Walkthrough – Raft Optimization
author: ['Siddon Tang']
date: 2017-11-28
summary: Paxos or Raft is frequently used to ensure data consistency in the distributed computing area. But Paxos is known for its complexity and is rather difficult to understand while Raft is very simple. Therefore, a lot of emerging databases tend to use Raft as the consensus algorithm at its bottom layer. TiKV is no exception.
tags: ['Raft', 'TiKV', 'Rust']
categories: ['Engineering']
---

Paxos or [Raft](https://raft.github.io/) is frequently used to ensure data consistency in the distributed databases. But Paxos is known for its complexity and is rather difficult to understand while Raft is very simple. Therefore, a lot of emerging databases tend to use Raft as the consensus algorithm at its bottom layer. [TiKV](https://github.com/pingcap/tikv) is no exception.

Simple as Raft is, its performance is not ideal if we follow exactly the way introduced in the Paper. Therefore, optimizations are essential. This blog introduces how we optimize Raft to ensure its performance in TiKV. It presumes that the audience is very familiar with Raft algorithm and don't need much explanation. (If not, please see [Raft in TiKV](https://pingcap.com/blog/2017-07-28-raftintikv/)).

## A simple Raft process

Below is the simple Raft process:

1. The leader receives the request sent by the client.

2. The Leader appends the request to its log.

3. The Leader sends the corresponding log entry to other followers.

4. The Leader waits for the result of followers. If the majority of nodes have committed this log, then Leader applies.

5. The Leader returns the result to the client.

6. The Leader continues to handle the next request.

You can see, the above flow is a typical sequential operation and if we exactly follow this workflow, the performance would be far from ideal.

## Batch and Pipeline

The first approach that comes to our minds is to use batch to solve the performance problem. As is known to all, using batch could remarkably improve the performance in most cases. For example, as for the writes to RocksDB, we usually don't write one value each time;  instead, we use `WriteBatch` to cache a batch of updates and write them all. For Raft, the Leader can gather multiple requests at a time and send this batch to its Follower. Of course, we also need a maximum size to limit the amount of data sent each time.

If we merely use batch, the Leader couldn't proceed to the subsequent flow until its Follower returns the result. Thus, we use Pipeline to speed up the process. The Leader maintains a `NextIndex` variable to represent the next log position that will be sent to the Follower. Usually, once the Leader establishes a connection with the Follower, we will consider that the network is stable and connected. Therefore, when the Leader sends a batch of logs to the Follower, it can directly update `NextIndex` and immediately sends the subsequent log without waiting for the return of the Follower. If the network goes wrong or the Follower returns a few errors, the Leader needs to readjust `NextIndex` and resends log.

## Append Logs Parallelly

We can execute the 2nd and 3rd steps of the above simple Raft process in parallel. In other words, the Leader can send logs to the Followers in parallel before appending logs. The reason is that in Raft if a log is appended by the majority of nodes, we consider the log committed. Thus, even if the Leader cannot append the log and goes panic after it sends a log to its Follower, the log can still be considered committed as long as `N/2 + 1` followers have received and appended the log. The log will then be applied successfully.

Since appending log involves disk writing and overhead, we'd better make the Follower receive log and append as quickly as possible when the Leader is writing to the disk.

Note that though the Leader can send the log to the Follower before appending log, the Follower cannot tell the Leader that it has successfully appended this log in advance. If the Follower does so but fails, the Leader will still think that the log has been committed. In this case, the system might be at the risk of data loss.

## Asynchronous Apply

As I mentioned previously, when a log is appended by the majority of the nodes, we consider it committed. When the committed log is applied has no impact on data consistency. So when a log is committed, we can use another thread to apply this log asynchronously.

So the entire Raft process becomes as follows:

1. The leader receives a request sent by a client.

2. The Leader sends the corresponding log to other followers and appends locally.

3. The leader continues to receive requests from other clients and executes step 2.

4. The Leader finds that the log has been committed, and apply the log in another thread.

5. Leader returns the result to the corresponding client after asynchronously applying the log.

The benefit of using asynchronous apply is that we are now able to append and apply log in parallel. Although to a client, its single request still needs to go through the whole Raft process; to multiple clients, the overall concurrency and throughput have improved.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('A TiKV Source Code Walkthrough – Raft Optimization', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('A TiKV Source Code Walkthrough – Raft Optimization', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## SST Snapshot

In Raft, if a Follower lags far behind the Leader, the Leader will probably send a snapshot to the Follower directly. In TiKV, Placement Driver sometimes schedules a few replicas inside a Raft Group onto other machines. All of this involves Snapshot.

Below is a Snapshot process in the current implementation:

1. The Leader scans all data of a region and creates a snapshot file.

2. The Leader sends the snapshot file to Follower.

3. The Follower receives the snapshot file, reads it and writes to RocksDB in batches.

If there are multiple Followers of the Raft Group processing the snapshot file within one node, RocksDB's write load will be huge, which easily leads to the condition that the whole write process slows down or stalls when RocksDB struggles to cope with so many compactions.

Fortunately, RocksDB offers the [SST](https://github.com/facebook/rocksdb/wiki/Creating-and-Ingesting-SST-files) mechanism, with which we can directly create an SST snapshot file. Then the Follower loads the SST file to RocksDB  by calling `DB::IngestExternalFile()` and passes the file paths as a vector of `std::string`. For more information, see [Ingesting SST files](https://github.com/facebook/rocksdb/wiki/Creating-and-Ingesting-SST-files#ingesting-sst-files).

## Asynchronous Lease Read or Append Log

TiKV uses `ReadIndex` and Lease Read to optimize the Raft Read operation, but these two operations are performed within the Raft thread, which is the same as the appended log process of Raft. However fast the appended log is written to RocksDB, this process still delays Lease Read.

Thus, currently, we are trying to asynchronously implement Lease Read in another thread. We'll move the Leader Lease judgment to another thread, and the thread in Raft will update Lease regularly through messages. In this way, we can guarantee that the write process of Raft will not influence that of read.

We are also trying to append the Raft log in another thread at the same time. We will compare the performance of the two approaches and choose the better one later.

## Summary

We will continuously optimize the Raft process in the future. And up to now, our hard work pays off as we have significant improvements in performance. But we know that there are more difficulties and challenges to resolve. We are looking forward to experienced experts who are good at performance optimization. If you have interest in our project and want to improve Raft, do not hesitate to contact us: [info@pingcap.com](mailto:info@pingcap.com).

## Fore more information

- [Raft in TiKV](https://pingcap.com/blog/2017-07-28-raftintikv/)
- [The Design and Implementation of Multi-raft](https://pingcap.com/blog/2017-08-15-multi-raft/)
