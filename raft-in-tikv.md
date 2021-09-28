---
title: A TiKV Source Code Walkthrough - Raft in TiKV
author: ['Siddon Tang']
date: 2017-07-28
summary: TiKV uses the Raft algorithm to implement the strong consistency of data in a distributed environment. This blog introduces the details how Raft is implemented.
tags: ['TiKV', 'Raft']
aliases: ['/blog/2017/07/28/raftintikv/','/blog/2017-07-28-raftintikv']
categories: ['Engineering']
---

(Email: tl@pingcap.com)

## Table of content

+ [Architecture](#architecture)
+ [Raft](#raft)
  - [Storage](#storage)
  - [Config](#config)
  - [RawNode](#rawnode)

## Architecture

Below is TiKV's overall architecture:

![TiKV architecture](media/TiKV_ Architecture.png)

**Placement Driver:** Placement Driver (PD) is responsible for the management scheduling of the whole cluster.

**Node:** Node can be regarded as an actual physical machine and each Node is responsible for one or more Store.

**Store:**  Store uses RocksDB to implement actual data storage and usually one Store corresponds to one disk.

**Region:** Region is the smallest unit of data movement and it refers to the actual data extent in Store. Each Region has multiple replicas, each of which is placed in different Stores and these replicas make up a Raft group.

## Raft

TiKV uses the Raft algorithm to implement the strong consistency of data in a distributed environment. For detailed information about Raft, please refer to the paper [In Search of an Understandable Consensus Algorithm](https://web.stanford.edu/~ouster/cgi-bin/papers/raft-atc14) and [the official website](https://raft.github.io/). Simply put, Raft is a model of replication log + State Machine. We can only write through a Leader and the Leader will replicate the command to its Followers in the form of log. When the majority of nodes in the cluster receive this log, this log has been committed and can be applied into the State Machine.

TiKV's Raft mainly migrates etcd Raft and supports all functions of Raft, including:

+ Leader election

+ Log replicationLog compaction

+ Membership changesLeader transfer

+ Linearizable / Lease read

Note that how TiKV and etcd process membership change is different from what is in the Raft paper. TiKV's membership change will take effect only when the log is applied. The main purpose is for a simple implementation. But it will be risky if we only have two nodes. Since we have to remove one node from inside and if a Follower has not received the log entry of `ConfChange`, the Leader will go down and be unrecoverable, then the whole cluster will be down. Therefore, it is recommended that users deploy 3 or more odd number of nodes.

The Raft library is independent and users can directly embed it into their applications. What they need to do is to process storage and message sending. This article will briefly introduce how to use Raft and you can find the code under the directory of TiKV source code /src/raft.

### Storage

First of all, we need to define our Storage, which is mainly used for storing relevant data of Raft. Below is the trait definition:

```
pub trait Storage {

    fn initial_state(&self) -> Result<RaftState>;

    fn entries(&self, low: u64, high: u64, max_size: u64) -> Result<Vec<Entry>>;

    fn term(&self, idx: u64) -> Result<u64>;

    fn first_index(&self) -> Result<u64>;

    fn last_index(&self) -> Result<u64>;

    fn snapshot(&self) -> Result<Snapshot>;

}
```

We need to implement our Storage trait and I'll elaborate on the implication of each interface:

`initial_state`: Call this interface when initializing Raft Storage and it will return `RaftState`, whose definition is shown below:

```

pub struct RaftState {

    pub hard_state: HardState,

    pub conf_state: ConfState,

}

```

`HardState` and `ConfState` is protobuf defined as follows:

```
message HardState {
  optional unit64 term    = 1;
  optional unit64 vote    = 2;
  optional unit64 commit  = 3;
}

message ConfState {
  repeated unit64 nodes   = 1;
}
```

`HardState` stores the following information:

+ the last saved term information of this Raft node

+ which node was voted

+ the log index that is already committed.

`ConfState` saves all node ID information of the Raft cluster.

When calling relevant logic of Raft from outside, users need to handle the persistence of `RaftState`.

`entries:` Get the Raft log entry of the [low, high) interval and controls the maximum number of the returned entries through `max_size`.

`term`, `first_index` and `last_index` **refers to getting the current term, the smallest and the last log index respectively.

`snapshot`: Get a snapshot of the current Storage. Sometimes, the amount of the current Storage is large and it takes time to create a snapshot. Then we have to asynchronously create it in another thread, so that the current Raft thread will not be clocked. At this time, the system can return `SnapshotTemporarilyUnavailable` error so that Raft will know snapshot is being prepared and will try again after a while.

Note that the above Storage interface is just for Raft. But actually we also use this Storage to store data like Raft log and so we need to provide other interfaces, such as `MemStorage` in Raft storage.rs for testing. You can refer to `MemStorage` to implement your Storage.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('A TiKV Source Code Walkthrough - Raft in TiKV', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('A TiKV Source Code Walkthrough - Raft in TiKV', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Config

Before using Raft, we need to know some relevant configuration of Raft. Below are the items that need extra attention in Config:

```
pub struct Config {
  pub id: u64,
  pub election_tick: usize,
  pub heartbeat_tick: usize,
  pub applied: u64,
  pub max_size_per_msg: u64,
  pub max_inflight_msgs: usize,
}
```

`id`: The unique identification of the Raft node. Within a Raft cluster, `id` has to be unique. Inside TiKV, the global uniqueness of `id` is guaranteed through PD.

`election_tick`: When a Follower hasn't received the message sent by its Leader after the `election_tick` time, then there will be a new election and TiKV uses 50 as the default.

`heartbeat_tick`: The Leader sends a heartbeat message to its Follower every `hearbeat_tick`. The default value is 10.

`applied`: It is the log index that was last applied.

`max_size_per_msg`: Limit the maximum message size to be sent each time. The default value is 1MB.

`max_inflight_msgs`: Limit the maximum number of in-flight message in replication. The default value is 256.

Here is the detailed implication of tick: TiKV's Raft is timing-driven. Assume that we call the Raft tick once every 100ms and when we call the tick times of `headtbeat_tick`, the Leader will send heartbeats to its Follower.

### RawNode

We use Raft through RawNode and below is its constructor:

```
pub fn new(config: &Config, sotre: T, peers: &[peer]) -> Result<RawNode<T>>
```

We need to define Raft's Config and then pass an implemented Storage. The `peers` parameter is just used for testing and it will not be passed. After creating the `RawNode` object, we can use Raft. Below are some functions that we pay attention to:

`tick`: We use the tick function to drive Raft regularly. In TiKV, we call tick once every 100ms.

`propose`: The Leader writes the command sent by client to the Raft log through the `propose` command and replicates to other nodes.

`propose_conf_change`: Like `propose`, this function is just used for handling the `ConfChange` command.

`step`: When the node receives the message sent by other nodes, this function actively calls the driven Raft.

`has_ready`: Used to determine whether a node is ready.

`ready`: Get the ready state of the current node. Before that, we will use `has_ready` to determine whether a RawNode is ready.

`apply_conf_change`: When a log of `ConfChange` is applied successfully, we need to actively call this driven Raft.

`advance`: Tell Raft that `ready` has been processed and it's time to start successive iterations.

As for `RawNode`, we should emphasize the `ready` concept and below is its definition:

```
pub struct Ready  {
  pub ss: Option<SoftState>,
  pub hs: Option<HardState>,
  pub entries: Vec<Entry>,
  pub snapshot: Snapshot,
  pub committed_entries: Vec<Entry>,
  pub messages: Vec<Message>,
}
```

`ss`: If `SoftState` has changes, such as adding or deleting a node, `ss` will not be empty.

`hs`: If `HardState` has changes, such as re-voting or term increasing, `hs` will not be empty.

`entries`: Needs to be stored in Storage before sending messages.

`snapshot`: If `snapshot` is not empty, it needs to be stored in Storage.

`committed_entries`: The Raft log that has been committed can be applied to State Machine.

`messages`: Usually, the message sending to other nodes cannot be sent until entries are saved successfully. But to a Leader, it can send messages first before saving entries. This is the optimization method introduced in the Raft paper and is also what TiKV adopts.

When the outside finds that a `RawNode` has been ready and gets `Ready`, it will:

1. Persist the non-empty `ss`and `hs`.

2. If it is a Leader, it will send messages first.

3. If the snapshot is not empty, store snapshot to Storage and asynchronously apply the data inside snapshot to State Machine (Even though it can be applied synchronously, the size of snapshot is large and will block the thread if doing so.)

4. Store entries to Storage.

5. If it is a Follower, send messages.

6. Apply `committed_entries` to State Machine.

7. Call `advance` to inform Raft that `ready` has been processed.
