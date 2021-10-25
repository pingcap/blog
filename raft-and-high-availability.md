---
title: Raft and High Availability
author: ['Rick Golba']
date: 2021-09-01
summary: Raft is a consensus-based method that distributes data in such a way that it creates and maintains a high availability environment for your database. This article introduces the general components and mechanisms of Raft, and how distributed databases such as TiDB and TiKV use Raft to achieve high availability and consistency.
tags: ['Raft']
categories: ['Engineering']
image: /images/blog/raft-and-high-availability-in-tikv-and-tidb.png
---

**Author:** Rick Golba (Product Marketing Manager at PingCAP)

**Editors:** [Calvin Weng](https://github.com/dcalvin), [Ran Huang](https://github.com/ran-huang)

![Raft and High Availability in TiKV and TiDB](media/raft-and-high-availability-in-tikv-and-tidb.png)

Raft is a consensus-based method that distributes data in such a way that it creates and maintains a high availability environment for your database. It does this by replicating content across multiple nodes so that, when a node fails, other nodes are able to continue accepting read and write requests, thus ensuring the availability of your data.

In this post, I will introduce the general components and mechanisms of Raft, and how distributed databases such as [TiDB](https://pingcap.com/products/tidb) and [TiKV](https://tikv.org/) use Raft to achieve high availability and consistency.

## Leaders and Followers

In a standard Raft cluster, each server is either a leader or a follower. The leader replicates log information to the follower(s) and keeps them in sync so that your data is durable and reliably replicated. There can be one or more followers of each leader. In TiDB, an additional role of learner is available. Learners are non-voting followers that only serve in the process of replica addition; they cannot be elected to the role of leader. The TiDB default is to have at least 2 followers for each leader since this enables a high level of fault tolerance and a lower Recovery Point Objective. This means that your environment can tolerate the failure of a node without any data loss, and the recovery from the node failure happens at a rapid pace. Learner nodes are also used for TiFlash, the column store, to ensure that any leader is always a TiKV node.

First, let's talk about the leader. The leader is the node that accepts all write requests and processes all read requests. It is also responsible for replication to its followers and learners. All communication to and from the client is handled through the leader. The leader sends a heartbeat to each of its followers and learners on a regular basis to keep them apprised of its continued operation. It maintains the role of leader until such time as the node in which it is running fails or disconnects from the environment. At that point, the followers and learners no longer receive a heartbeat notification from the leader and a new leader must be appointed.

When a follower realizes that it has not gotten a heartbeat from the leader within a predefined time period, it initiates an election process by putting itself forth as the candidate server. In order to understand the election process, we must discuss the concept of a _term number_ in Raft. The Raft protocol divides time into small _terms_, each identified by an incrementing number, known as the _term number_. Each server maintains its own term number, which, by design, is unique.

## Electing a new leader

When an election occurs, the candidate server sends a message to the other servers asking for their vote. Each server can only vote once per election; learner servers do not vote. If a majority of followers vote for the candidate to become the leader, the election ends and the candidate server is promoted to leader. However, if one of the voting servers passes a term number that is greater than the term number of the candidate, the candidate is defeated and the server with the higher term number is designated as the leader. This ensures that the server with the most current term number is designated as the new leader.

It all sounds complex, and it is, but this process happens internally and with minimal impact on the performance of your environment. While an election is underway, some requests may be queued, but the rapidity of the election ensures that there is a low likelihood of any noticeable issues.

## Raft in TiKV and TiDB

TiKV in TiDB uses Raft for a variety of reasons. Its primary purpose is to manage the replication of data. This is done by replicating the logs to the followers. It is also used to maintain high availability, using the majority concept defined above.

By default, TiDB uses 2 followers for each leader, for a total of 3 data replicas. This allows for the failure of the leader, which triggers an election. The candidate server, which was previously a follower, asks the other server for a vote. If the term number for the candidate server is greater than the term number for the voting server, the candidate is promoted to leader. If the term number for the voting server is greater than the term number for the candidate server, the election fails and the voting server is promoted to leader.

If the leader is available and one of the follower servers fails, a recovery process takes place. Recovery also takes place after an election since a new follower server needs to be brought into the environment to replace the failed server. In either case, the leader, either the previously existing one or a newly elected one, replicates the log files to the new server and recreates the data from the logs. Once that process is complete, the new server is a fully functioning member of the cluster.

Raft also ensures that writes are processed by a majority of the servers before the write transaction is committed. This means that the data is consistent and available, even when a server is in failure or recovery. Having an odd number of servers is ideal since it allows for a majority to be easily determined. If you have 4 servers and 2 fail, the remaining 2 servers do not constitute a majority of the expected servers. However, if you have 5 servers and 2 fail, the remaining 3 servers do make up a majority of the expected servers.

## Summary

The Raft protocol is one of several options for designing a high availability environment. It is used in TiDB to both ensure data integrity and availability. There are a variety of system parameters that determine how Raft functions in your specific environment. For details on the Raft parameters, consult [TiDB documentation](https://docs.pingcap.com/tidb/stable/tikv-configuration-file).

Additional blog posts:

* [How TiKV Reads and Writes](https://pingcap.com/blog/how-tikv-reads-and-writes) describes the use of Raft in more detail.
* [TiDB: A Raft-based HTAP Database](https://www.vldb.org/pvldb/vol13/p3072-huang.pdf) explores how TiDB benefits from the application of Raft.
* [Building a Large Scale Distributed Storage System Based on Raft](https://pingcap.com/blog/building-a-large-scale-distributed-storage-system-based-on-raft) covers the rationale behind the use of Raft with TiDB.
