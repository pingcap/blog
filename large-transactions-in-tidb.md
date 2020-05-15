---
title: Large Transactions in TiDB
author: [Nick Cameron]
date: 2020-05-15
summary: This post describes how we implemented support for large transactions in TiDB 4.0.
tags: ['Transaction']
categories: ['Engineering']
image: /images/blog/large-transactions.jpg
---

![Large transactions in TiDB](media/large-transactions.jpg)

[TiDB](https://pingcap.com/docs/stable/) is an open-source, distributed SQL database that supports [Hybrid Transactional/Analytical Processing](https://en.wikipedia.org/wiki/HTAP) (HTAP) workloads. In [TiDB 4.0](https://pingcap.com/docs/stable/releases/release-4.0.0-rc.1/), we've extended the transaction system to handle large transactions. Previously, TiDB limited the number of reads and writes in a transaction. In version 4.0, there is a much larger size limit on transactions (10 GB). In this blog post, I'll describe how we implemented support for large transactions. This post won't explain TiDB's transactions, I'll have a post about that at some point.

Large transactions caused problems for a few reasons: they take up a lot of memory in TiDB, they keep locks on many keys for a long time, which blocks other transactions from making progress, and they can exceed their time-to-live (TTL) and be rolled-back even though they are still working.

To deal with the memory issues, we have made changes to our in-memory buffers in TiDB, I don't do much work with TiDB, so I'm afraid I can't go into detail.

Solving the issue with transactions timing out is fairly straightforward: the TTL is stored with the primary lock in [TiKV](https://pingcap.com/docs/stable/architecture/#tikv-server), the storage engine for TiDB. (Each lock in a transaction has a reference to the primary). TiDB can send a heartbeat message to TiKV to extend the TTL and keep the transaction alive if necessary.

For the problem of blocking other transactions, we must introduce a new concept - the `min_commit_ts`, which is the minimum time at which the transaction can be committed. We start a transaction with `min_commit_ts = start_ts + 1`. When a transaction is committed, if the `commit_ts` is smaller than the `min_commit_ts`, then an error is triggered and sent to TiDB. TiDB can then retry committing with a later timestamp.

The clever part happens when another transaction (let’s call it txn B) is blocked from reading by the large transaction (txn A). In this case, rather than txn B being blocked, it will update the `min_commit_ts` of txn A's lock, setting it to the `start_ts` of txn B `+ 1`. (We can't do this for writes, but that is not too bad since we would always expect writes from one transaction to block writes from another). This is a `CheckTxnStatus` request, but TiKV adds it to its work queue, directly rather than sending it. The `min_commit_ts` can also be updated by TiDB sending an explicit `CheckTxnStatus` request.

The addition of `min_commit_ts` maintains our snapshot isolation property. For an intuition why, imagine that txn B came after txn A was committed. If txn B's `start_ts` is less than `txn A`'s `commit_ts`, we would read the old value (i.e., pre-txn A). By adding the `min_commit_ts` to txn A and keeping it up to date, we are guaranteeing in advance that txn A will not be committed until after txn B's `start_ts`, i.e., that reading the old value is valid for txn B.

_This post was originally published on [Nick Cameron‘s blog](https://www.ncameron.org/blog/large-transactions-in-tidb/)._
