---
date: 2016-11-09T00:00:00Z
excerpt: This document introduces how TiKV works as a Key-Value database.
title: A Deep Dive into TiKV
url: /2016/11/09/Deep-Dive-into-TiKV/
---

<span id="top"><span>

# Table of Content
- [About TiKV](#about-tikv)
- [Architecture](#architecture)
- [Protocol](#protocol)
- [Raft](#raft)
- [Placement Driver (PD)](#placement-driver)
- [Transaction](#transaction)
- [Coprocessor](#coprocessor)
- [Key processes analysis](#key-processes-analysis)
	- [Key-Value operation](#key-value-operation)
	- [Membership Change](#membership-change)
	- [Split](#split)

# About TiKV

TiKV (The pronunciation is: /'taɪkeɪvi:/ tai-K-V, etymology: titanium) is a distributed Key-Value database which is based on the design of Google Spanner, F1, and HBase, but it is much simpler without dependency on any distributed file system. 

# Architecture

![](media/TiKV_ Architecture.png)

* Placement Driver (PD): PD is the brain of the TiKV system which manages the metadata about Nodes, Stores, Regions mapping, and makes decisions for data placement and load balancing. PD periodically checks replication constraints to balance load and data automatically.

* Node: A physical node in the cluster. Within each node, there are one or more Stores. Within each Store, there are many Regions.

* Store: There is a RocksDB within each Store and it stores data in local disks.

* Region: Region is the basic unit of Key-Value data movement and corresponds to a data range in a Store. Each Region is replicated to multiple Nodes. These multiple replicas form a Raft group. A replica of a Region is called a Peer.

# Protocol

TiKV uses the [Protocol Buffer](https://developers.google.com/protocol-buffers/) protocol for interactions among different components. Because Rust doesn’t support [gRPC](http://www.grpc.io/) for the time being, we use our own protocol in the following format:

```
Message: Header + Payload 

Header: | 0xdaf4(2 bytes magic value) | 0x01(version 2 bytes) | msg\_len(4 bytes) | msg\_id(8 bytes) |
```


The data of Protocol Buffer is stored in the Payload part of the message. At the Network level, we will first read the 16-byte Header. According to the message length (`msg_len`) information in the Header, we calculate the actual length of the message, and then read the corresponding data and decode it.

The interaction protocol of TiKV is in the  [`kvproto`](https://github.com/pingcap/kvproto) project and the protocol to support push-down is in the [`tipb`](https://github.com/pingcap/tipb) project. Here, let’s focused on the `kvproto` project only. 

About the protocol files in the `kvproto` project:

* `msgpb.proto`: All the protocol interactions are in the same message structure. When a message is received, we will handle the message according to its `MessageType`.
* `metapb.proto`: To define the public metadata for Store, Region, Peer, etc.
* `raftpb.proto`: For the internal use of Raft. It is ported from etcd and needs to be consistent with etcd.
* `raft_serverpb.proto`: For the interactions among the Raft nodes.
* `raft_cmdpb.proto`: The actual command executed when Raft applies.
* `pdpb.proto`: The protocol for the interaction between TiKV and PD.
* `kvrpcpb.proto`: The Key-Value protocol that supports transactions.
* `mvccpb.proto`: For internal Multi-Version Concurrency Control (MVCC).
* `coprocessor.proto`: To support the Push-Down operations.

There are following ways for external applications to connect to TiKV:

* For the simple Key-Value features only, implement `raft_cmdpb.proto`.
* For the Transactional Key-Value features, implement `kvrpcpb.proto`.
* For the Push-Down features, implement `coprocessor.proto`. See [tipb](https://github.com/pingcap/tipb) for detailed push-down protocol.

[Back to the Top](#top)

# Raft

TiKV uses the Raft algorithm to ensure the data consistency in the distributed systems. For more information, see [https://raft.github.io/](https://raft.github.io/).

The Raft in TiKV is completely migrated from etcd. We chose etcd Raft because it is very simple to implement, very easy to migrate and it is production proven.

The Raft implementation in TiKV can be used independently. You can apply it in your project directly.

See the following details about how to use Raft:

1. Define its own storage and implement the Raft Storage trait. See the following Storage trait interface:

```rust
    // initial_state returns the information about HardState and ConfState in Storage
    fn initial_state(&self) -> Result<RaftState>;
    
    // return the log entries in the [low, high] range
    fn entries(&self, low: u64, high: u64, max_size: u64) -> Result<Vec<Entry>>;
    
    // get the term of the log entry according to the corresponding log index
    fn term(&self, idx: u64) -> Result<u64>;
    
    // get the index from the first log entry at the current position
    fn first_index(&self) -> Result<u64>;
    
    // get the index from the last log entry at the current position
    fn last_index(&self) -> Result<u64>;
    
    // generate a current snapshot
    fn snapshot(&self) -> Result<Snapshot>;
```

2. Create a raw node object and pass the corresponding configuration and customized storage instance to the object. About the configuration, we need to pay attention to `election_tick` and `heartbeat_tick`. Some of the Raft logics step by periodical ticks. For every Tick, the Leader will decide if the frequency of the heartbeat elapsing exceeds the frequency of the `heartbeat_tick`. If it does, the Leader will send heartbeats to the Followers and reset the elapse. For a Follower, if the frequency of the election elapsing exceeds the frequency of the `election_tick`, the Follower will initiate an election. 

3. After a raw node is created, the tick interface of the raw node will be called periodically (like every 100ms) and drives the internal Raft Step function. 

4. If data is to be written by Raft, the Propose interface is called directly. The parameters of the Propose interface is an arbitrary binary data which means that Raft doesn’t care the exact data content that is replicated by it. It is completely up to the external logics as how to handle the data.

5. If it is to process the membership changes, the `propose_conf_change` interface of the raw node can be called to send a ConfChange object to add/remove a certain node.

6. After the functions in the raw node like Tick and Propose of the raw node are called, Raft will initiate a Ready state. Here are some details of the Ready state:

    There are three parts in the Ready state:

    + The part that needs to be stored in Raft storage, which are entries, hard state and snapshot.
    + The part that needs to be sent to other Raft nodes, which are messages.
    + The part that needs to be applied to other state machines, which are committed_entries.


After handling the Ready status, the Advance function needs be called to inform Raft of the next Ready process.

In TiKV, Raft is used through [mio](https://github.com/carllerche/mio) as in the following process:

1. Register a base Raft tick timer (usually 100ms). Every time the timer timeouts, the Tick of the raw node is called and the timer is re-registered.

2. Receive the external commands through the notify function in mio and call the Propose or the `propose_conf_change` interface.

3. Decide if a Raft is ready in the mio tick callback (**Note:** The mio tick is called at the end of each event loop, which is different from the Raft tick.). If it is ready,  proceed with the Ready process.

In the descriptions above, we covered how to use one Raft only. But in TiKV, we have multiple Raft groups. These Raft groups are independent to each other and therefore can be processed following the same approach. 

In TiKV, each Raft group corresponds to a Region. At the very beginning, there is only one Region in TiKV which is in charge of the range (-inf, +inf). As more data comes in and the Region reaches its threshold (64 MB currently), the Region is split into two Regions. Because all the data in TiKV are sorted according to the key, it is very convenient to choose a Split Key to split the Region. See [Split](#split) for the detailed splitting process.

Of course, where there is Split, there is Merge. If there are very few data in two adjacent Regions, these two regions can merge to one big Region. Region Merge is in the TiKV roadmap but it is not implemented yet.

[Back to the Top](#top)

# Placement Driver

Placement Driver (PD) is in charge of the managing and scheduling of the whole TiKV cluster. It is a central service and we have to ensure that it is highly available and stable.

The first issue to be resolved is the single point of failure of PD. Our solution is to start multiple PD servers. These servers elect a Leader through the election mechanism in etcd and the leader provides services to the outside. If the leader is down, there will be another election to elect a new leader to provide services.

The second issue is the consistency of the data stored in PD. If one PD is down, how to ensure that the new elected PD has the consistent data? This is also resolved by putting PD data in etcd. Because etcd is a distributed consistent Key-Value store, it helps us ensure the consistency of the data stored in it. When the new PD is started, it only needs to load data from etcd.

At first, we used the independent external etcd service, but now we have embedded PD in etcd, which means, PD itself is an etcd. The embedment makes it simpler to deploy because there is one service less. The embedment also makes it more convenient for PD and etcd to customize and therefore improve the performance. 

The current functions of PD are as follows:

1. The Timestamp Oracle (TSO) service: to provide the globally unique timestamp for TiDB to implement distributed transactions.

2. The generation of the globally unique ID: to enable TiKV to generate the unique IDs for new Regions and Stores.

3. TiKV cluster auto-balance: In TiKV, the basic data movement unit is Region, so the PD auto-balance is to balance Region automatically. There are two ways to trigger the scheduling of a Region:

    1). The heartbeat triggering: Regions report the current state to PD periodically. If PD finds that there are not enough or too much replicas in one Region, PD informs this Region to initiate membership change.

    2). The regular triggering: PD checks if the whole system needs scheduling on a regular bases. If PD finds out that there is not enough space on a certain Store or that there are too many leader Regions on a certain Store and the load is too high, PD will select a Region from the Store and move the replicas to another Store.
    
[Back to the Top](#top)

# Transaction

The transaction model in TiKV is inspired by [Google Percolator](http://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/36726.pdf) and [Themis from Xiaomi](https://github.com/XiaoMi/themis) with the following optimizations:

1. For a system that is similar to Percolator, there needs to be a globally unique time service, which is called Timestamp Oracle (TSO), to allocate a monotonic increasing timestamp. The functions of TSO are provided in PD in TiKV. The generation of TSO in PD is purely memory operations and stores the TSO information in etcd on a regular base to ensure that TSO is still  monotonic increasing even after PD restarts.

2. Compared with Percolator where the information such as Lock is stored by adding extra column to a specific row, TiKV uses a column family (CF) in RocksDB to handle all the information related to Lock. For massive data, there aren’t many row Locks for simultaneous transactions. So the Lock processing speed can be improved significantly by placing it in an extra and optimized CF.

3. Another advantage about using an extra CF is that we can easily clean up the remaining Locks. If the Lock of a row is acquired by a transaction but is not cleaned up because of crashed threads or other reasons, and there are no more following-up transactions to visit this Lock, the Lock is left behind. We can easily discover and clean up these Locks by scanning the CF.

The implementation of the distributed transaction depends on the TSO service and the client that encapsulates corresponding transactional algorithm which is implemented in TiDB. The monotonic increasing timestamp can set the time series for concurrent transactions and the external clients can act as a coordinator to resolve the conflicts and unexpected terminations of the transactions.

Let’s see how a transaction is executed:

1. The transaction starts. When the transaction starts, the client must obtain the current timestamp (startTS) from TSO. Because TSO guarantees the monotonic increasing of the timestamp, startTS can be used to identify the time series of the transaction.

2. The transaction is in progress. During a transaction, all the read operations must carry `startTS` while they send RPC requests to TiKV and TiKV uses MVCC to make sure to return the data that is written before `startTS`. For the write operations, TiKV uses optimistic concurrency control which means the actual data is cached on the clients rather than written to the servers assuming that the current transaction doesn’t affect other transactions.  

3. The transaction commits. TiKV uses a 2-phase commit algorithm. Its difference from the common 2-phase commit is that there is no independent transaction manager. The commit state of a transaction is identified by the commit state of the `PrimaryKey` which is selected from one of the to-be-committed keys.

    1). During the `Prewrite` phase, the client submits the data that is to be written to multiple TiKV servers. When the data is stored in a server, the server sets the corresponding Key as Locked and records the the PrimaryKey of the transaction. If there is any writing conflict on any of the nodes, the transaction aborts and rolls back.

    2). When `Prewrite` finishes, a new timestamp is obtained from TSO and is set as commitTS.

    3). During the Commit phase, requests are sent to the TiKV servers with `PrimaryKey`. The process of how TiKV handles commit is to clean up the Locks from the PrimaryKey phase and write corresponding commit records with commitTS. When the `PrimaryKey` commit finishes, the transaction is committed. The Locks that remain on other Keys can get the commit state and the corresponding commitTS by retrieving the state of the `Primarykey`. But in order to reduce the cost of cleaning up Locks afterwards, the practical practice is to submit all the Keys that are involved in the transaction asynchronously on the backend.
    
[Back to the Top](#top)

# Coprocessor 

Similar to HBase, TiKV provides the Coprocessor support. But for the time being, Coprocessor cannot be dynamically loaded, it has to be statically compiled to the code. 

Currently, the Coprocessor in TiKV is mainly used in two situations, Split and push-down, both to serve TiDB.

1. For Split, before the Region split requests are truly proposed, the split key needs to be checked if it is legal. For example, for a Row in TiDB, there are many versions of it in TiKV, such as V1, V2, and V3, V3 being the latest version. Assuming that V2 is the selected split key, then the data of the Row might be split to two different Regions, which means the data in the Row cannot be handled atomically. Therefore, the Split Coprocessor will adjust the split key to V1. In this way, the data in this Row is still in the same Region during the splitting. 

2. For push-down, the Coprocessor is used to improve the performance of TiDB. For some operations like select count(*), there is no need for TiDB to get data from row to row first and then count. The quicker way is that TiDB pushes down these operations to the corresponding TiKV nodes, the TiKV nodes do the computing and then TiDB consolidates the final results.

Let’s take an example of `select count(*) from t1` to show how a complete push-down process works:

1. After TiDB parses the SQL statement, based on the range of the t1 table, TiDB finds out that all the data of t1 are in Region 1 and Region 2 on TiKV, so TiDB sends the push-down commands to Region 1 and Region 2.

2. After Region 1 and Region 2 receive the push-down commands, they get a snapshot of their data separately by using the Raft process. 

3. Region 1 and Region 2 traverse their snapshots to get the corresponding data and and calculate `count()`. 

4. Each Region returns the result of `count()` to TiDB and TiDB consolidates and outputs the total result.

[Back to the Top](#top)

# Key processes analysis

## Key-Value operation

When a request of Get or Put is sent to TiKV, how does TiKV process it?

As mentioned earlier, TiKV provides features such as simple Key-Value, transactional Key-Value and push-down. But no matter it’s transactional Key-Value or push-down, it will be transformed to simple Key-Value operations in TiKV. Therefore, let’s take an example of simple Key-Value operations to show how TiKV processes a request. As for how TiKV implements transaction Key-Value and push-down support, let’s cover that later.

Let’s take `Put` as an example to show how a complete Key-Value process works:

1. The client sends a `Put` command to TiKV, such as `put k1 v1`. First, the client gets the Region ID for the k1 key and the leader of the Region peers from PD. Second, the client sends the Put request to the corresponding TiKV node.

2. After the TiKV server receives the request, it notifies the internal RaftStore thread through the mio channel and takes a callback function with it.

3. When the `RaftStore` thread receives the request, first it checks if the request is legal including if the request is a legal epoch. If the request is legal and the peer is the Leader of the Region, the RaftStore thread encodes the request to be a binary array, calls Propose and begins the Raft process.

4. At the stage of handle ready, the newly generated entry will be first appended to the Raft log and sent to other followers at the same time.

5. When the majority of the nodes of the Region have appended the entry to the log, the entry is committed. In the following Ready process, the entry can be obtained from the `committed_entries`, then decoded and the corresponding command can be executed. This is how the `put k1 v1` command is executed in RocksDB.

6. When the entry log is applied by the leader, the callback of the entry will be called and return the response to the client.

The same process also applies to Get, which means all the requests are not processed until they are replicated to the majority of the nodes by Raft. Of course, this is also to ensure the data linearizability in distributed systems.

Of course, we will optimize the reading requests for better performance in the following aspects:

1. Introduce lease into the Leader. Within the lease, we can assume that the Leader is valid so that the Leader can provide the read service directly and there will be no need to go through Raft replicated log.

2. The Follower provides the read service.

These optimizations are mentioned in the Raft paper and they have been supported by etcd. We will introduce them into TiKV as well in the future.

[Back to the Top](#top)

## Membership Change

To ensure the data safety, there are multiple replicas on different stores. Each replica is another replica’s Peer. If there aren’t enough replicas for a certain Region, we will add new replicas; on the contrary, if the numbers of the replicas for a certain Region exceeds the threshold, we will remove some replicas.

In TiKV, the change of the Region replicas are completed by the Raft Membership Change. But how and when a Region changes its membership is scheduled by PD. Let’s take adding a Replica as an example to show how the whole process works:

1. A Region sends heartbeats to PD regularly. The heartbeats include the relative information about this Region, such as the information of the peers.

2. When PD receives the heartbeats, it will check if the number of the replicas of this Region is consistent with the setup. Assuming there are only two replicas in this Region but it’s three replicas in the setup, PD will find an appropriate Store and return the ChangePeer command to the Region.

3. After the Region receives the ChangePeer command, if it finds it necessary to add replica to another Store, it will submit a ChangePeer request through the Raft process. When the log is applied, the new peer information will be updated in the Region meta and then the Membership Change completes. 

It should be noted that even if the Membership Change completes, it only means that the Replica information is added to the meta by the Region. Later if the Leader finds that if there is no data in the new Follower, it will send snapshot to it.

It should also be noted that the Membership Change implementation in TiKV and etcd is different from what’s in the Raft paper. In the Raft paper, if a new peer is added, it is added to the Region meta at the Propose command. But to simplify, TiKV and etcd don’t add the peer information to the Region meta until the log is applied.

[Back to the Top](#top)

## Split

At the very beginning, there is only one Region. As data grows, the Region needs to be split. 

Within TiKV, if a Region splits, there will be two new Regions, which we call them the Left Region and the Right Region. The Left Region will use all the IDs of the old Region. We can assume that the Region just changes its range. The Right Region will get a new ID through PD. Here is a simple example:

```
Region 1 [a, c) -> Region 1 [a, b) + Region 2 [b, c)
```

The original range of Region 1 is [a, c). After splitting at the b point, the Left Region is still Region 1 but the range is now [a, b). The Right Region is a new Region, Region 2, and its range is [b, c).

Assuming the base size of Region 1 is 64MB. A complete spit process is as follows:

1. In a given period of time, if the accumulated size of the data in Region 1 exceeds the threshold (8MB for example), Region 1 notifies the split checker to check Region 1.

2. The split checker scans Region 1 sequentially. When it finds that the accumulated size of a certain key exceeds 64MB, it will keep a record of this key and make it the split key. Meanwhile, the split checker continues scanning and if it finds that the accumulated size of a certain key exceeds the threshold (96 MB for example), it considers this Region could split and notifies the RaftStore thread.

3. When the RaftStore thread receives the message, it sends the AskSplit command to PD and requests PD to assign a new ID for the newly generated PD, Region 2, for example.

4. When the ID is generated in PD, an Admin SplitRequest will be generated and sent to the RaftSore thread.

5. Before RaftStore proposes the Admin SplitRequest, the Coprocessor will pre-process the command and decide if the split key is appropriate. If the split key is not appropriate, the Coprocessor will adjust the split key to an appropriate one.

6. The Split request is submitted through the Raft process and then applied. For TiKV, the splitting of a Region is to change the range of the original Region and then create another Region. All these changes involves only the change of the Region meta, the real data under the hood is not moved, so it is very fast for Region to split in TiKV.

7. When the Splitting completes, TiKV sends the latest information about the Left Region and Right Region to PD.

[Back to the Top](#top)
