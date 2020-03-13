---
title: TiDB Passes Jepsen Test for Snapshot Isolation and Single-Key Linearizability
date: 2019-06-12
summary: TiDB's first official Jepsen Test report is published. This post introduces some additional context to the test results and PingCAP's thoughts on what's next.
tags: ['Engineering']
categories: ['Engineering']
---

Earlier this year, we reached out to Kyle Kingsbury, the creator of the Jepsen test suite, to conduct an official Jepsen test on TiDB. Even though we've done [our own Jepsen test](https://github.com/pingcap/jepsen) before, we thought it was important and valuable to work with Kyle directly to put TiDB through the Jepsen wringer. The results would not only benefit our team as we continue to drive the development of TiDB, but also our users, partners, and community.

After several months of close collaboration with Kyle, we are excited that TiDB's first official Jepsen Test report is published. You can read it [HERE](https://jepsen.io/analyses/tidb-2.1.7). 

***tl;dr:*** Kyle tested the following versions of TiDB: 2.1.7, 2.1.8, 3.0.0-beta.1-40, and 3.0.0-rc.2. The latest version, 3.0.0-rc.2, passes Jepsen tests for snapshot isolation and single-key linearizability, and previous versions, TiDB 2.1.8 through 3.0.0-beta.1-40, also pass when the auto-retry mechanism is disabled, which was enabled by default. In 3.0.0-rc.2 and future versions of TiDB, the auto-retry mechanism is *disabled* by default. 

*See the discussion of [TiDB's results on Hacker News](https://news.ycombinator.com/item?id=20163975).*

In this blog post, we would like to provide some additional context to the results and share our thoughts on what's next.

## To (Auto) Retry or Not (Auto) Retry?

Although TiDB tries to be as compatible with MySQL as possible, its nature of a distributed system results in certain [differences](https://pingcap.com/docs/dev/reference/mysql-compatibility/), one of which is the [transaction-model](https://pingcap.com/docs/dev/reference/transactions/transaction-model/). On the one hand, TiDB adopts an optimistic transaction model that detects conflicts only when transactions are committing, and the transaction will be rolled back if any conflicts are detected. On the other, being a distributed database means that transactions in TiDB will also be rolled back in the event of failures such as network partitions. However, many of the clients that our current customers use to talk to the databases are tailored for traditional databases like MySQL and Oracle, where commits rarely fail at the default isolation level so retry mechanisms are not needed. For these clients, when commits fail, they abort with errors as this is rendered as rare exceptions in these databases. Unlike traditional databases such as MySQL, in TiDB, if users want to avoid massive commit failures, they need to add mechanisms in their own business logic of their applications to handle the related errors, which is the last thing some customers are willing to do. 

To help our customers solve this problem, we provide a retry mechanism for those failed commits, which automatically retry the conflicting transactions in TiDB. This, however, has its downsides, which we didn't clearly document. Thanks to Kyle and Jepsen tests for pointing this out, we have updated our [documentation](https://pingcap.com/docs/dev/reference/transactions/transaction-model/#transaction-retry) to keep the users aware of the difference and its possible consequences, and we [disabled the transaction retry mechanism by default](https://pingcap.com/docs/dev/reference/transactions/transaction-model/#transaction-retry) by changing the default value of `tidb_disable_txn_auto_retry` to `on`.

Regarding the decision on whether to enable or disable the retry mechanism by default, we had gone through some changes. For the 3.0.0 GA version, we had originally planned to change the behavior of `tidb_disable_txn_auto_retry` to make it control the retry over transactions in write conflicts only, and we implemented the same in 3.0.0-beta.1-40. Unfortunately, though, we didn't update the documentation to reflect the change in time. Thanks to Jepsen tests, we reflected on this change and believed this was not a good design. Therefore, in 3.0.0-rc2, we have adjusted the behavior of `tidb_disable_txn_auto_retry` to what it used to be prior to 3.0.0-beta.1-40, which is consistent with the [documentation](https://pingcap.com/docs/dev/reference/configuration/tidb-server/tidb-specific-variables/#tidb-disable-txn-auto-retry). 

To disable or enable the transaction retry, users can configure both `tidb_retry_limit` and `tidb_disable_txn_auto_retry`, with the following differences:

- **tidb_retry_limit = 0** disables all forms of retries.
- **tidb_disable_txn_auto_retry = on** only disables retries for explicit transactions, while those auto-committed transactions are still available for the auto-retry if conditions are met. For the auto-committed transactions, auto-retry would not break Snapshot Isolation. 

## What Else?

[Jepsen report](https://jepsen.io/analyses/tidb-2.1.7) has also found some other issues, some of which are expected behaviors, and some are already fixed or being fixed. Here is more information about these issues:

### Expected behavior: Crashes on Startup

This behavior is expected for TiDB server. We decided to adopt the fail-fast approach when we first designed TiDB, so that DBAs and operation engineers can quickly discover and identify issues at the deployment stage. If the startup fails because of errors with some processes, or the system restarts frequently after startup, an alerting system is available to inform the DBAs and operation engineers timely as well. In a production environment, we use `systemd` to ensure that the service can be restarted even if there are any issues.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('TiDB Passes Jepsen Test for Snapshot Isolation and Single-Key Linearizability', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Passes Jepsen Test for Snapshot Isolation and Single-Key Linearizability', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Fixed in the 3.0.0-rc.2: Created Tables May Not Exist

This issue is fixed in 3.0.0-rc.2 and the [pull request](https://github.com/pingcap/tidb/pull/10029) to handle the related issue had been merged into the master branch before Kyle [filed the issue](https://github.com/pingcap/tidb/issues/10410). The reason for this issue is that if a new cluster is created and multiple TiDB servers are bootstrapped, write conflicts occur because the bootstrapping process changes the global variables in one TiKV server. The issue is triggered only if all the following 3 conditions are met:

1) The TiDB server in the DDL Owner node which handles the DDL job is not the first one to finish bootstrapping, and

2) Write conflict occurs right before the very same TiDB server finishes bootstrapping, and

3) When 2) happens, the TiDB server that finishes bootstrapping receives the DDL request

The issue is fixed by ensuring that only the TiDB server who is the DDL Owner can process the bootstrap logic.

### Fixing: Under-Replicated Regions
 
To ensure all regions in the cluster have enough replicas before providing services, we have added [a new API](https://github.com/pingcap/pd/pull/1555) to let users know quickly when a cluster is initialized and ready. This new API will be integrated into the deployment tools such as [TiDB Ansible](https://github.com/pingcap/tidb-ansible/pull/774) and TiDB Operator (a Kubernetes operator) so that we can identify a successful deployment only when the number of replicas is sufficient.

### Documentation Fixes

Admittedly, there is always room for improvement in our documentation. Thanks to Jepsen tests, here are some immediate fixes per issues found in the test report:

> **Comment from Jepsen report:** "The documentation is therefore somewhat confusing: some of its descriptions of repeatable read actually refer to repeatable read, and other parts refer to snapshot isolation."		
		
- **Fix:** We have updated our [transactional isolation](https://pingcap.com/docs/dev/reference/transactions/transaction-isolation/#difference-between-tidb-and-ansi-repeatable-read) documentation to state that "TiDB allows some phantoms (P3), but does not allow strict phantoms (A3)" to clear the inconsistency implied in our documentation. 

> **Comments from Jepsen report:** "TiDB's automatic transaction retry mechanism was documented, but poorly'", "The documentation for auto-retries was titled "Description of optimistic transactions", and it simply said that the automatic-retry mechanism "cannot guarantee the final result is as expected" — but did not describe how."

- **Fix:** We have updated the TiDB [transaction documentation](https://pingcap.com/docs/dev/reference/transactions/transaction-isolation/#transaction-retry) to note that automatic transaction retry is disabled in TiDB by default and that enabling it can result in lost updates. Transactional anomalies caused by automatic retries are also introduced in detail. 

> **Comment from Jepsen report:** "PingCAP's official documentation did not describe what select ... for update should have done."

- **Fix:** We have updated the description of [`Select for Update`](https://pingcap.com/docs/dev/reference/sql/statements/select/#description-of-the-syntax-elements) with more detailed behaviors of the clause and its difference with other databases.


## Next Steps

Building a distributional database and continuously improving it is a long stretching battle. Inspired by Jepsen tests, we are planning to continue to integrate Jepsen and other forms of tests more comprehensively across our processes and components.

- Integrate Jepsen tests with our own Continuous Integration (CI) system to make sure each commit passes Jepsen tests.

- Add more TiDB test cases to Jepsen tests, including membership changes, DDL, etc. We are also considering adding an independent Jepsen tests for TiKV.

- Support pessimistic transaction locking to make transactions behave more similarly to that in MySQL. TiDB 3.0.0-rc.2 has provided pessimistic transaction locking as an experimental support and users can configure whether to enable it. This for sure needs to pass Jepsen tests.

- Continuously amplify and improve our documentation to provide comprehensive, consistent, accurate, and user-friendly content and user experience. 

## Conclusion

As we work to finalize the final steps of releasing TiDB 3.0 for General Availability in the coming weeks, the results of this Jepsen tests was incredibly helpful for us to build the strongest TiDB yet. It was a pleasure working with Kyle throughout this whole process, and we encourage you to read the full report [HERE](http://jepsen.io/analyses/tidb-2.1.7). 
