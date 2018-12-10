---
title: How TiKV Uses "Lease Read" to Guarantee High Performances, Strong Consistency and Linearizability
author: ['Siddon Tang']
date: 2018-11-14
summary: This post discusses Raft Log Read, `ReadIndex` Read, and Lease Read, and why TiKV adopts the Lease Read approach.
tags: ['TiKV', 'Engineering']
image: /images/blog-article/p32.jpg
categories: ['Engineering']
---

TiKV, an open source distributed transactional key-value store (also a Cloud Native Computing Foundation member project), uses the [Raft](https://raft.github.io/) consensus algorithm to ensure strong data consistency and high availability. Raft bears many similarities to other consensus algorithms like Paxos in its ability to ensure fault-tolerance and its performance implementations, but generally easier to understand and implement. While our team has written extensively on how Raft is used in TiKV (some examples: [Raft in TiKV](https://www.pingcap.com/blog/2017-07-28-raftintikv/), [the Design and Implementation of Multi-raft](https://www.pingcap.com/blog/2017-08-15-multi-raft/), [Raft Optimization](https://www.pingcap.com/blog/optimizing-raft-in-tikv/)), one topic we haven’t discussed is when stale read happens due to a brain split within a Raft group, and the old Raft leader is not aware that a new leader is elected, what should we do? This post discusses three different approaches to this problem: Raft Log Read, `ReadIndex` Read, and Lease Read, and why TiKV adopts the Lease Read approach. 

## Raft Log Read

Because Raft is a consensus algorithm that is designed for distributed environments, one way we can resolve the stale read issue is by using the Raft process itself. Inside Raft, we can make the read request go through the Raft log. After the log is committed, we can then read data from the state machine during `apply`. This approach helps us make sure that the data we read is strongly consistent. 

However, one significant drawback is each read request needs to go through the entire Raft process, which could lead to severe performance issues, thus very few projects apply this approach.

## `ReadIndex` Read

`ReadIndex` Read is a different approach and was originally proposed in the Raft paper. We know that inside Raft, a Region can be in 1 of 3 states: leader, candidate and follower. Any Raft write operation must go through the leader. Only when the leader replicates the corresponding Raft log to a majority of the Regions inside the same Raft group will we consider this write successful. 

Simply put, as long as the leader *really is* the leader, then we can directly read data from it. But how do we confirm that fact while handling the read request? Here’s the process that `ReadIndex` Read will go through: 

1. Record its current commit index into the local variable `ReadIndex`.
2. Send a heartbeat message to other Regions. If the majority of Regions replies with the corresponding heartbeat response, then the leader confirms its state.
3. Wait for the execution of its state machine until the `apply` index equals to or exceeds `ReadIndex`. By then, the data can be read consistently.
4. Execute the read request and return the result to the client.

You can see that unlike reading through the Raft log, `ReadIndex` Read uses heartbeats to make leader confirm its state, which is much easier. Although there is still network overhead for the heartbeats, the performance is better than the Raft Log Read.

## Lease Read

In TiKV, we adopt a third and optimized way --  Lease Read -- another approach introduced in the Raft paper. When the leader sends a heartbeat, it records a timestamp `start`. When the majority of Regions in the group reply the heartbeat response, we think that the lease validity of the leader can last till `start` + `election timeout` / `clock drift bound`.

The Lease Read implementation of TiKV is the same as that in the Raft paper in principle, with some optimizations included. In TiKV, the lease is updated through write operations instead of heartbeats. Since any write operation goes through Raft log, when we propose this write request, we record the current timestamp as `start` and wait for the corresponding `apply` before renewing the leader’s lease. A couple of additional implementation details worth noting:

1. The election timeout is 10 seconds by default and we use the fixed max time value of 9 seconds to renew the lease. So even in case of split brain, we can guarantee that the older leader lease is expired when the next leader is elected.
2. We use the monotonic raw clock instead of the monotonic clock. The reason is that the rate of the latter will be influenced by factors like NTP, even though it will not have the time jump back problem.

With this approach the response to the client within the lease is initiated by the leader’s state machine. As long as the leader’s state machine is strongly consistent, so will the data that is read from that leader, regardless of when the read occurs. 
