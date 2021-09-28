---
title: TiDB Internal (III) - Scheduling
author: ['Li Shen']
date: 2017-07-20
summary: This is the third one of three blogs to introduce TiDB internal.
tags: ['Distributed system']
aliases: ['/blog/2017/07/20/tidbinternal3/', '/blog/2017-07-20-tidbinternal3']
categories: ['Engineering']
---

From Li SHEN: shenli@pingcap.com

## Table of Content

+ [Why scheduling](#why-scheduling)
+ [The Requirements of Scheduling](#the-requirements-of-scheduling)
+ [The Basic Operations of Scheduling](#the-basic-operations-of-scheduling)
+ [Information Collecting](#information-collecting)
+ [The Policy of Scheduling](#the-policy-of-scheduling)
+ [The implementation of Scheduling](#the-implementation-of-scheduling)
+ [Summary](#summary)

## Why scheduling?

From [the first blog of TiDB internal](https://pingcap.com/blog/2017-07-11-tidbinternal1), we know that TiKV cluster is the distributed KV storage engine of TiDB database. Data is replicated and managed in Regions and each Region has multiple Replicas distributed on different TiKV nodes. Among these replicas, Leader is in charge of read/write and Follower synchronizes the raft log sent by Leader. Now, please think about the following questions:

+ How to guarantee that multiple Replicas of the same Region are distributed on different nodes? Further, what happens if starting multiple TiKV instances on one machine?
+ When TiKV cluster is performing multi-site deployment for disaster recovery, how to guarantee that multiple Replicas of a Raft Group will not get lost if there is outage in one datacenter?
+ How to move data of other nodes in TiKV cluster onto the newly-added node?
+ What happens if a node fails? What does the whole cluster need to do? How to handle if the node fails only temporarily (e.g. restarting a service)? What about a long-time failure (e.g. disk failure or data loss)?
+ Assume that each Raft Group is required to have N replicas. A single Raft Group might have insufficient Replicas (e.g. node failure, loss of replica) or too much Replicas (e.g. the once failed node functions again and automatically add to the cluster). How to schedule the number?
+ As read/write is performed by Leader, what happens to the cluster if all Leaders gather on a few nodes?
+ There is no need to get access to all Regions and the hotspot probably resides in a few Regions. In this case, what should we do?
+ The cluster needs to migrate data during the process of load balancing. Will this kind of data migration consume substantial network bandwidth, disk IO and CPU and influence the online service?

It is easy to solve the above questions one by one, but once mixed up, it becomes difficult. It seems that some questions just need to consider the internal situation of a single Raft Group, for example, whether to add replicas is determined by if the number is enough. But actually, where to add this replica needs a global view. The whole system is changing dynamically: situations like Region splitting, node joining, node failing and hotspot accessing changes occur constantly. The schedule system also needs to keep marching towards the best state. Without a component that can master, schedule and configure the global information, it is hard to meet these needs. Therefore, we need a central node to control and adjust the overall situation of the system. So here comes the Placement Driver (PD) module.

## The Requirements of Scheduling

I want to categorize and sort out the previously listed questions. In general, there are two types:

+ A distributed and highly available storage system must meet the following requirements:

    - The right number of replicas.
    - Replicas should be distributed on different machines.
    - Replicas on other nodes can be migrated after adding nodes.
    - When a node is offline, data on this node should be migrated.

+ A good distributed system needs to have the following optimizations:

    - A balanced distribution of Leaders in the cluster.
    - A balanced storage capacity in each node.
    - A balanced distribution of hotspot accessing.
    - Control the speed of balancing in order not to impact the online service.
    - Manage the node state, including manually online/offline nodes and automatically offline faulty nodes.

If the first type of requirements are met, the system supports multi-replica disaster recovery, dynamic scalability, tolerance of node failure and automatic disaster recovery.

If the second type of requirements are met, the load of the system becomes more balanced and easier to manage.

To meet these needs, we need to, first of all, collect enough information, such as the state of each node, information of each Raft Group and the statistics of business access and operation. Then we should set some policies for PD to formulate a schedule plan to meet the previous requirements according to this information and the schedule policy.

## The Basic Operations of Scheduling

The basic operations of schedule are the simplest. In other word, what we can do to meet the schedule policy. This is the essence of the whole scheduler.

The previous scheduler requirements seem to be complicated, but can be generalized into 3 operations:

+ Add a Replica.
+ Delete a Replica.
+ Transfer the role of Leader among different Replicas of a Raft Group.

The Raft protocol happens to meet these requirements: the `AddReplica`, `RemoveReplica` and `TransferLeader` commands support the three basic operations.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('TiDB Internal (III) - Scheduling', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Internal (III) - Scheduling', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## Information Collecting

Schedule depends on the information gathering of the whole cluster. Simply put, we need to know the state of each TiKV node and each Region. TiKV cluster reports two kinds of information to PD:

+ Each TiKV node regularly reports the overall information of nodes to PD

    There are heartbeats between TiKV Store and PD. On the one hand, PD checks whether each Store is active or if there are newly-added Stores through heartbeats. On the other hand, heartbeats carry the state information of this Store, mainly including:

    - total disk capacity
    - free disk capacity
    - the number of Regions
    - data writing speed
    - the number of sent/received Snapshot (Replicas synchronize data through Snapshots)
    - whether it is overloaded
    - label information (Label is a series of Tags that has hierarchical relationship)

+ Leader of each Raft Group reports to PD regularly

    Leader of each Raft Group and PD are connected with heartbeats, which report the state of this Region, including:

    - the position of Leader
    - the position of Followers
    - the number of offline Replicas
    - data reading/writing speed

Through these two kinds of heartbeats, PD gathers the information of the whole cluster and then makes decisions. What's more, PD makes more accurate decisions by getting extra information through the management interface. For example, when the heartbeat of a Store is interrupted, PD has no idea whether it is temporarily or permanently. PD can only waits for a period of time (30 minutes by default); if there is still no heartbeat, PD considers that the Store has been offline and it needs to move all Regions on the Store away. However, if an Operations staff manually offline a machine, he needs to tell PD through its management interface that the Store is unavailable. In this case, PD will immediately move all Regions on the Store away.

## The Policy of Scheduling

After gathering information, PD needs some policies to draw up a concrete schedule plan.

1. The number of Replica in a Region should be correct

    When PD finds that the number of Replica for a Region doesn't meet the requirement through the heartbeat of a Region Leader, it modifies the number through the Add/Remove Replica operations. This might occur when:

    + a node drops and loses all data, leading to the lack of Replica in some Regions.
    + a dropped node functions again and automatically joins in the cluster. In this case, there is a redundant Replica and needs to be removed.
    + the administrator has modified the replica policy and the configuration of max-replicas.

2. Multiple Replicas of a Raft Group should not be in the same place

    Please pay attention that it is the same place, not the same node. In general, PD can only guarantee that multiple Replicas would not be in the same node, so as to avoid the problem that many Replicas get lost when a node fails. In an actual deployment scenario, the following requirements may come out:

    + Multiple nodes are deployed on the same physical machine.
    + TiKV nodes distribute on multiple servers. It is expected that when a server powers down, the system is still available.
    + TiKV nodes distribute on multiple IDCs. When a datacenter powers down, the system is still available.

    Essentially, what you need is a node that has the common location attribute and constitutes a minimum fault-tolerance unit. We hope that  inside this unit, multiple Replicas of a Region will not co-exist. At this time, you can configure labels to nodes and location-labels in PD to designate which label to be the location identifier. When distributing Replicas, the node that stores multiple Replicas of a Region will not have the same location identifier.

3. Replicas are distributed evenly across Stores

    As the data storage capacity of each replica is fixed, if we maintain the balance of the number of replica on each node, the overall load will be more balanced.

4. The number of Leader is distributed evenly across Stores

    The Raft protocol reads and writes through Leader, so the computational load is mainly placed on Leader. Therefore, PD manages to distribute Leader among different stores.

5. The number of hotspot is distributed evenly across Stores

    When submitting information, each Store and Region Leader carry the information of the current access load, such as the read/write speed of Key. PD checks the hotspots and distributes them across nodes.

6. The storage space occupancy of each Store is roughly the same

    Each Store specifies a Capacity parameter when starting, which indicates the limit of the storage space of this Store. PD considers the remaining space of the node when scheduling.

7. Control the schedule speed so as not to affect the online service

    As scheduling operation consumes CPU, memory, disk I/O, and network bandwidth, we should not affect the online service. PD controls the number of ongoing operations and the default speed is conservative. If you want to speed up the scheduling (stop the service upgrade, add new nodes, wish to schedule as soon as possible, etc.), then you can manually accelerate it through pd-ctl.

8. Support offline nodes manually

    When offlining a node manually through pd-ctl, PD will move the data on the node away within a certain rate control. After that, it will put the node offline.

## The implementation of Scheduling

Now let's see the schedule process.

PD gets the detail data of the cluster by constantly gathering information through heartbeats of Store or Leader. Based on this information and the schedule policies, PD generates the operating sequence, and then checks whether there is an operation to be performed on this Region when receiving a heartbeat sent by the Region Leader. PD returns the upcoming operation to Region Leader through the reply message of the heartbeat and then monitors the execution result in the next heartbeat. These operations are just suggestions to Region Leader, which are not guaranteed to be executed. It is the Region Leader that decides to whether and when to execute according to its current state.

## Summary

This blog discloses information you might not find elsewhere. We hope that you've had a better understanding about what needs to be considered to build a distributed storage system for scheduling and how to decouple policies and implementation to support a more flexible expansion of policy.

We hope these three blogs ([Data Storage](https://pingcap.com/blog/2017-07-11-tidbinternal1), [Computing](https://pingcap.com/blog/2017-07-11-tidbinternal2), and [Scheduling](https://pingcap.com/blog/2017-07-20-tidbinternal3)) can help you understand the basic concepts and implementation principles of TiDB. In the future, more blogs about TiDB from code to architecture are on their way!
