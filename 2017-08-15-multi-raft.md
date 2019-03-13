---
title: The Design and Implementation of Multi-raft
date: 2017-08-15
summary: The goal of TiKV is to support 100 TB+ data and it is impossible for one Raft group to make it, we need to use multiple Raft groups, which is called Multi-raft.
tags: ['TiKV', 'Engineering', 'Raft', 'Golang', 'Rust']
aliases: ['/blog/2017/08/15/multi-raft/']
categories: ['Engineering']
---

(Email: tl@pingcap.com)

<span id="top"> </span>

+   [Placement Driver](#placement-driver)
+   [Raftstore](#raftstore)
    -   [Region](#region)
    -   [RocksDB / Keys Prefix](#rocksdb-keys-prefix)
    -   [Peer Storage](#peer-storage)
    -   [Peer](#peer)
    -   [Multi-raft](#multi-raft)
+   [Summary](#summary)

## Placement Driver

Placement Driver (PD), the global central controller of TiKV, stores the metadata information of the entire TiKV cluster, generates Global IDs, and is responsible for the scheduling of TiKV and the global TSO time service.

PD is a critical central node. With the integration of etcd, it automatically supports the distributed scaling and failover as well as solves the problem of single point of failure. We will write another article to thoroughly introduce PD.

In TiKV, the interaction with PD is placed in the [pd](https://github.com/pingcap/tikv/tree/master/src/pd) directory. You can interact with PD with your self-defined RPC and the protocol is quite simple. In [pd/mod.rs](https://github.com/pingcap/tikv/blob/master/src/pd/mod.rs), we provide the Client trait to interact with PD and have implemented the RPC Client.

The Client trait of PD is easy to understand, most of which are the set/get operations towards the metadata information of the cluster. But you need to pay extra attention to the operations below:

**`bootstrap_cluster`**: When we start a TiKV service, we should firstly find out whether the TiKV cluster has been bootstrapped through `is_cluster_bootstrapped`. If not, then create the first region on this TiKV service.

**`region_heartbeat`**: Region reports its related information to PD regularly for the subsequent scheduling. For example, if the number of peers reported to PD is smaller than the predefined number of replica, then PD adds a new Peer replica to this Region.

**`store_heartbeat`**: Store reports its related information to PD regularly for the subsequent scheduling. For example, Store informs PD of the current disk size and the free space. If PD considers it inadequate, it will not migrate other Peers to this Store.

**`ask_split/report_split`**: When a Region needs to split, it will inform PD through `ask_split` and PD then generates the ID of the newly-split Region. After split successfully, Region informs PD through `report_split`.

By the way, we will make PD support gRPC protocol in the future, so the `ClientAPI` will have some changes.

[Back to the top](#top)

## Raftstore

The goal of TiKV is to support 100 TB+ data and it is impossible for one Raft group to make it, we need to use multiple Raft groups, which is **Multi-raft**. In TiKV, the implementation of Multi-raft is completed in Raftstore and you can find the code in the [raftstore/store](https://github.com/pingcap/tikv/tree/master/src/raftstore/store) directory.

### Region

To support Multi-raft, we perform data sharding and make each Raft store a portion of data.

Hash and Range are commonly used for data sharding. TiKV uses Range and the main reason is that Range can better aggregate keys with the same prefix, which is convenient for operations like scan. Besides, Range outperforms in split/merge than Hash. Usually, it only involves metadata modification and there is no need to move data around.

The problem of Range is that a Region may probably become a performance hotspot due to frequent operations. But we can use PD to schedule these Regions onto better machines.

To sum up, we use Range for data sharding in TiKV and split them into multiple Raft Groups, each of which is called a Region.

Below is the protocol definition of Region’s protbuf:

```

message RegionEpoch {

     optional uint64 conf_ver  = 1 [(gogoproto.nullable) = false];

     optional uint64 version     = 2 [(gogoproto.nullable) = false];

}

message Region {

    optional uint64 id                  = 1 [(gogoproto.nullable) = false];

    optional bytes  start_key           = 2;

    optional bytes  end_key             = 3;

    optional RegionEpoch region_epoch   = 4;

    repeated Peer   peers               = 5;

}

message Peer {      

    optional uint64 id          = 1 [(gogoproto.nullable) = false]; 

    optional uint64 store_id    = 2 [(gogoproto.nullable) = false];

}

```

**`region_epoch`**: When a Region adds or deletes Peer or splits, we think that this Region’s epoch has changed. RegionEpoch’s `conf_ver` increases during ConfChange while `version` increases during split/merge.

**`id`**: Region’s only indication and PD allocates it in a globally unique way.

**`start_key`**, **`end_key`**: Stand for the range of this Region [start_key, end_key). To the very first region, start and end key are both empty, and TiKV handles it in a special way internally.

**`peers`**: The node information included in the current Region. To a Raft Group, we usually have three replicas, each of which is a Peer. Peer’s `id` is also globally allocated by PD and `store_id` indicates the Store of this Peer.

[Back to the top](#top)

### RocksDB / Keys Prefix

In terms of actual data storage, whether it’s Raft Metadata, Log or the data in State Machine, we store them inside a RocksDB instance. More information about RocksDB, please refer to[ https://github.com/facebook/rocksdb](https://github.com/facebook/rocksdb).

We use different prefixes to differentiate data of Raft and State Machine. For detailed information, please refer to [raftstore/store/keys.rs](https://github.com/pingcap/tikv/blob/master/src/raftstore/store/keys.rs). As for the actual data of State Machine, we add "z" as the prefix and for other metadata stored locally, including Raft, we use the 0x01 prefix.

I want to highlight the Key format of some important metadata and I’ll skip the first 0x01 prefix.

+ 0x01: To store `StoreIdent`. Before initializing this Store, we store information like its Cluster ID and Store ID into this key.

+ 0x02: To store some information of Raft. 0x02 is followed by the ID of this Raft Region (8-byte big endian) and a Suffix to identify different subtypes.

+ 0x01: Used to store Raft Log, followed by Log Index (8-byte big endian)

+ 0x02: Used to store `RaftLocalState`

+ 0x03: Used to store `RaftApplyState`

+ 0x03：Used to store some local metadata of Region. 0x03 is followed by the Raft Region ID and a Suffix to represent different subtypes.

+ 0x01: Used to store `RegionLocalState`

Types mentioned above are defined in protobuf:

```

message RaftLocalState {

    eraftpb.HardState hard_state = 1;

    uint64 last_index = 2;

}

message RaftApplyState {

    uint64 applied_index = 1;

    RaftTruncatedState truncated_state = 2;

}

enum PeerState {

    Normal = 0;

    Applying = 1;

    Tombstone = 2;

}

message RegionLocalState {

    PeerState state = 1;

    metapb.Region region = 2;

}

```

**`RaftLocalState`:** Used to store `HardState` of the current Raft and the last Log Index.

**`RaftApplyState`:** Used to store the last Log index that Raft applies and some truncated Log information.

**`RegionLocalStaste`:** Used to store Region information and the corresponding Peer state on this Store. `Normal` indicates that this Peer is normal, `Applying` means this Peer hasn’t finished the `apply snapshot` operation and `Tombstone` shows that this Peer has been removed from Region and cannot join in Raft Group.

[Back to the top](#top)

### Peer Storage

We use Raft through `RawNode` because one Region corresponds to one Raft Group. Peer in Region corresponds to one Raft replica. Therefore, we encapsulate operations towards `RawNode` in Peer.

To use Raft, we need to define our storage and this can be implemented in the `PeerStorage` class of [raftstore/store/peer_storage.rs](https://github.com/pingcap/tikv/blob/master/src/raftstore/store/peer_storage.rs).

When creating `PeerStorage`, we need to get the previous `RaftLocalStat`, `RaftApplyState` and `last_term` of this Peer from RocksDB. These will be cached to memory for the subsequent quick access.

Below requires extra attention:

The value of both `RAFT_INIT_LOG_TERM` and `RAFT_INIT_LOG_INDEX` is 5 (as long as it's larger than 1). In TiKV, there are several ways to create a Peer:

1. Create actively: In general, for the first Peer replica of the first Region, we use this way and set its Log Term and Index as 5 during initialization.

2. Create passively: When a Region adds a Peer replica and this `ConfChange` command has been applied, the Leader will send a Message to the Store of this newly-added Peer. When the Store receives this Message and confirms its legality, and finds that there is no corresponding Peer, it will create a corresponding Peer. However, at that time, this Peer is an uninitialized and any information of its Region is unknown to us, so we use 0 to initialize its Log Term and Index. Leader then will know this Follower has no data (there exists a Log notch from 0 to 5) and it will directly send snapshot to this Follower.

3. Create when splitting: When a Region splits into two Regions, one of the Regions will inherit the metadata before splitting and just modify its Range while the other will create relevant meta information. The corresponding Peer of this newly-created Region and the initial Log Term and Index is also 5. The reason is that by then Leader and Follower both have the latest data and don’t need snapshot. (Note: Actually, the Split process is much more complicated and the situation of sending snapshot may occur. But I’m not going to elaborate in this article.)

Then you need to pay attention to snapshot. Both generating and applying snapshot are time-consuming operations. `PeerStore` will only synchronize the meta information related to the snapshot to avoid the situation that the whole Raft thread will get stuck and obstruct the subsequent Raft process. Instead, `PeerStore` asynchronously performs snapshot on another thread and it maintains the state of snapshot:

```

  pub enum SnapState {

      Relax,

      Generating(Receiver<Snapshot>),

      Applying(Arc<AtomicUsize>),

      ApplyAborted,

  }

```

`Generating` here is a channel Receiver. Once the asynchronous snapshot is generated, it will send a message to this channel. Thus, during the next Raft check, it can get the snapshot from this channel directly. `Applying` is a shared atomic integer, so we can determine the state of the current `applying` in a multithreading manner.

```

pub const JOB_STATUS_PENDING: usize = 0;

pub const JOB_STATUS_RUNNING: usize = 1;

pub const JOB_STATUS_CANCELLING: usize = 2;

pub const JOB_STATUS_CANCELLED: usize = 3;

pub const JOB_STATUS_FINISHED: usize = 4;

pub const JOB_STATUS_FAILED: usize = 5;

```

For example, the state `JOB_STATUS_RUNNING**`** indicates that applying snapshot is in progress. Currently, `JOB_STATUS_FAILED` is not allowed. In other words, if the applying snapshot fails, the system would panic.

[Back to the top](#top)

### Peer

Peer encapsulates `Raft RawNode`. Those `Propose` and `ready` operations towards Raft are done in Peer.

The `propose` function of Peer is the interface of the external Client command. Peer will determine the type of this command:

+ If it’s a read-only operation and Leader is still within the validity period of lease, Leader will provide local read directly without going through Raft.

+ If it’s a Transfer Leader operation, Peer will first of all determine whether it is still Leader and whether the log of the Follower that needs to be the new Leader is latest. If so, Peer will call RawNode’s `transfer_leader` command.

+ If it’s a Change Peer operation, Peer will call RawNode’s `propose_conf_change` command.

+ For other operations, Peer will directly call RawNode’s `propose` command.

Before `propose`, Peer will also store the corresponding callback into `PendingCmd`. When the corresponding log has been applied, it will call the corresponding callback through the unique UUID in the command and return the corresponding result to Client.

Peer’s `handle_raft_ready` functions also require extra attention. We’ve mentioned that in the previous Raft session, when a `RawNode` is ready, we need to do a series of process to the data in `ready`, including writing entries into Storage, sending messages, applying `committed_entries`, `advance`, etc. All of these are done in the `handle_raft_ready` functions of Peer.

As for `committed_entries`, Peer will parse the actual command, call the corresponding process and execute the corresponding function. For example, for `exec_admin_cmd`, Peer executes administering commands like `ConfChange` and `Split`; for `exec_write_cmd`, it executes the common data operation commands towards State Machine. To guarantee the data consistency, Peer will only store the modified data into `WriteBatch` of RocksDB when executing and then atomically write in RocksDB. It cannot modify the corresponding memory metadata unless the write operation is successful. If it fails, we will directly go panic to guarantee the data integrity.

When Peer is handling `ready`, we pass in a `Transport` object for Peer to send message. Below is the definition of the Transport’s trait:

```

pub trait Transport: Send + Clone {

    fn send(&self, msg: RaftMessage) -> Result<()>;

}

```

It only has one function: `send`. Transport implemented by TiKV will send the needed message to the Server layer which then sends to other nodes.

[Back to the top](#top)

### Multi-raft

Peer is a replica of a single Region. TiKV supports Multi-raft, so for a Store, we need to manage multiple Region replicas, which are managed systematically in the Store class.

Store will use `region_peers: HashMap<u64, Peer>` to store all the information of Peers:

The key of `region_peers` is the Region ID and Peer is the Peer replica on this Store of this Region.

Store uses mio to drive the whole process (we will use `tokio-core` to simplify the asynchronous logic processing later).

We have registered a base Raft Tick in mio and call it every 1000ms. Store will traverse all Peers, call the corresponding `RawNode tick` function at a time to drive Raft.

Store accepts the request from the outside Client and Raft message sent by other Stores through the notify mechanism of mio. For example, when receiving `Msg::RaftCmd` message, Store will call `propose_raft_command`,  while for `Msg::RaftMessage`, it will call `on_raft_message` .

After each `EventLoop`, i.e. inside the tick call-back of mio, Store will perform `on_raft_ready`:

1. Store traverses all the ready Peers and calls `handle_raft_ready_append`. We will use a `WriteBatch` to handle all ready append data and store the corresponding result at the same time.

2. If `WriteBatch` succeeds, it will then call `post_raft_ready_append` successively, mainly for the Follower to send message. (Leader’s message has been completed in `handle_raft_ready_append`)

3. Then, Store successively calls `handle_raft_ready_apply` and committed entries related to `apply` and then calls the final result of `on_ready_result`. 


## Summary

In this blog, I’ve shared the details about Multi-raft, one of TiKV’s key technologies. In the subsequent sections, we will introduce Transaction, Coprocessor, and how Placement Drivers schedules the entire cluster. Stay tuned!

[Back to the top](#top)

