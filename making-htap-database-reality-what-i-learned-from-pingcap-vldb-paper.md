---
title: "Making an HTAP Database a Reality: What I Learned from PingCAP's VLDB Paper"
author: ['Xianlin Chen']
date: 2020-10-22
summary: "Recently, VLDB published the PingCAP paper, TiDB: A Raft-based HTAP Database. In this article, a DBA at PalFish shares his thoughts on the article and his expectations for TiDB's future development."
tags: ['HTAP', 'VLDB', 'Raft']
categories: ['Community']
image: /images/blog/making-htap-database-reality-what-i-learned-from-pingcap-vldb-paper.jpg
---

**Author:** Xianlin Chen (Head of Technology Hub at PalFish)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![HTAP database](media/making-htap-database-reality-what-i-learned-from-pingcap-vldb-paper.jpg)

Recently, [VLDB 2020](https://vldb2020.org/) published [PingCAP](https://pingcap.com/)'s paper, [TiDB: A Raft-based HTAP Database](https://pingcap.com/blog/vldb-2020-tidb-a-raft-based-htap-database). This is the first paper in the industry to describe the Raft-based implementation of a distributed [Hybrid Transactional/Analytical Processing](https://en.wikipedia.org/wiki/Hybrid_transactional/analytical_processing) (HTAP) database. As a DBA who benefits greatly from [TiDB](https://docs.pingcap.com/tidb/stable/overview), an open-source, distributed SQL database, I'm happy that VLDB recognized TiDB, and I'm inspired by the PingCAP engineering team's novel ideas.

PingCAP's paper is not the typical theoretical research paper, proposing an idea that may never be implemented. Instead, it proves, clearly and pragmatically, that a distributed HTAP database is achievable. Database researchers can use this information to head more confidently in the right direction.

In this article, I'll share with you my thoughts about TiDB's implementation of an HTAP database that provides strong data consistency and resource isolation, as well as my expectations of TiDB in the future.

## The trouble with OLTP and OLAP databases

As you probably know, databases are divided into two types: [Online Transactional Processing](https://en.wikipedia.org/wiki/Online_transaction_processing) (OLTP) and [Online Analytical Processing](https://en.wikipedia.org/wiki/Online_analytical_processing) (OLAP). But have you ever wondered why?

OLTP and OLAP describe two very different data processing methods, and, therefore, they have different database requirements.

| **Characteristics** | **OLTP** | **OLAP** |
|:--|--|--|
| Data queried in one request | Small (a few rows) | Large |
| Real-time update | Yes | No |
| Transactions | Yes | No |
| Concurrency | High | Low |
| Query pattern | Similar | Varies a lot |

Years ago, databases made little distinction between OLTP and OLAP. Instead, one database processed both types of requests. However, as the data volume grew, it became difficult to process two types of workloads in a single database. Most significantly, the different workload types interfered with each other.

Thus, to meet the special needs of OLAP workloads, people designed a separate database that only processed OLAP workloads. They exported data from OLTP databases to OLAP databases, and processed the OLAP workloads there. Separating the OLTP and OLAP workloads resolved the conflicts between the two workloads, but it also introduced external data replication. During the replication, it was hard to ensure that data was consistent and in real time.

PingCAP's paper proposes a new way to solve this problem: **the replication should take place inside the database**, rather than outside of it.

## Strong consistency or resource isolation

Because OLTP and OLAP are very different workloads, it is difficult to do both kinds of jobs in a single database. There are two general schemas:

* **Design a storage engine suitable for both OLTP and OLAP**. In the storage engine, data is consistent and real time, but it's hard to make sure that two workloads do not get in the way of each other.
* **Build two sets of storage engines in one database**. Each storage engine would handle one type of workload, so OLTP and OLAP don't affect each other. However, since data is replicated between two engines, it might be challenging to achieve strong data consistency and resource isolation at the same time.

TiDB chose the second method. [TiKV](https://tikv.org/), the row-based storage engine, handles OLTP workloads, while [TiFlash](https://docs.pingcap.com/tidb/dev/tiflash-overview/), the columnar storage engine, handles OLAP workloads. But how do they provide strong consistency and resource isolation?

For most distributed storage systems, strong consistency and resource isolation is an either-or question. You can't have both. But TiDB has an answer: **extend the [Raft consensus algorithm](https://en.wikipedia.org/wiki/Raft_(computer_science)) by adding a Learner role**.

## Solving a major issue by extending the Raft algorithm

In TiKV, the basic unit of data storage is the [Region](https://docs.pingcap.com/tidb/dev/glossary#regionpeerraft-group), which represents a range of data (96 MB by default). Each Region has three replicas by default. Replicas of the same Region replicate data from Leader to Follower via the Raft consensus algorithm. This is synchronous replication.

Assuming that TiFlash is a Follower in the Raft group, the replication between TiKV and TiFlash is synchronous. When TiFlash's replication is slow, or when a TiFlash node goes down, a majority of nodes are less likely to successfully replicate data, thus affecting TiKV's availability. So TiFlash can't be a Follower, because it interferes with TiKV, and the resources are not isolated.

To solve this problem, TiDB extends the Raft algorithm by adding a Learner role to it. The Learner replica only receives Raft logs asynchronously. It doesn't commit logs or participate in the Leader election. When the Learner replica is replicating data, the Followers' and Leader's performance overhead is very low. When TiFLash's Learner replica receives data, TiFlash converts the row format tuples to column format data and stores it in the column store. In this way, data is both in row store and column store format at the same time.

However, if TiFlash's Learner replica asynchronously receives logs from the Raft group, how does it ensure the data is strongly consistent?

TiFlash guarantees strong consistency when the application reads data from TiFlash. Similar to Raft's follower read mechanism, the Learner replica provides snapshot isolation, so we can read data from TiFlash using a specified timestamp. When TiFlash gets a read request, the Learner replica sends a `ReadIndex` request to its Leader. According to the received `ReadIndex`, the Leader holds back the request until the corresponding Raft log is replicated to the Learner, and then filters the required data by the specified timestamp. This is how TiFlash can provide strongly consistent data.

When the application reads data from TiFlash, TiFlash's Learner replica only needs to perform a `ReadIndex` operation with TiKV's Leader replica. This operation imposes very little burden on TiKV. According to the paper, when TiDB processed both OLTP and OLAP workloads, OLAP throughput decreased by less than 5%, and OLTP throughput decreased by only 10%.

Moreover, the paper documents an experiment in which the asynchronous data replication from TiKV to TiFlash produced a very low latency. In the case of a data volume of 10 warehouses, the latency was mostly within 100 ms, with the largest latency smaller than 300 ms. In the case of 100 warehouses, the latency was mostly within 500 ms, with the largest latency smaller than 1500 ms. Most importantly, the latency didn't affect data consistency. It only made TiFlash process requests a little slower.

## TiDB: uniting OLTP and OLAP

TiDB has two storage engines, TiKV for OLTP and TiFlash for OLAP, and both support strongly consistent data replication and provide the same snapshot isolation.

This is a huge bonus for optimizing queries at the computing layer. When the optimizer processes a request, it has three options: row scan ([TiKV](https://docs.pingcap.com/tidb/dev/tikv-overview)), index scan ([TiKV](https://docs.pingcap.com/tidb/dev/tikv-overview)), or column scan ([TiFlash](https://docs.pingcap.com/tidb/dev/tiflash-overview)). For a single request, the optimizer can apply different scans for different parts of data, which provides a lot of flexibility for optimization. The PingCAP paper also proved that **an OLAP request that uses both storage engines works better than a request that uses either of the two engines**.

While older databases required users to divide their requests and send them to the appropriate database, **TiDB offers a different workflow**: there's only one database for the user. The database analyzes the request and determines which storage engine to use. **It takes the trouble of dividing databases and requests out of the user's mind**, which is a higher level of abstraction.

## Decentralized or centralized architecture?

Different architectural designs coexist in the current distributed database industry. One prominent design is decentralized architecture, like Cassandra or CockroachDB. But TiDB is not strictly decentralized, because it has the [Placement Driver](https://docs.pingcap.com/tidb/stable/tidb-architecture#placement-driver-pd-server) (PD), a central scheduling manager.

**Decentralized architecture excels at fault tolerance, attack resistance, and collusion resistance**. But since databases are deployed in reliable, internal networks, resisting attacks or collusion is not an issue. Fault tolerance, on the other hand, can also be handled in a centralized architecture. Therefore, decentralization is not required.

Compared to decentralized architecture, **centralized architecture is better at scheduling**. HTAP databases are made for huge volumes of data. When the number of nodes and data volumes grow to an unprecedented extent, the database must be able to elastically scale. Whether a database has intelligent scheduling capabilities will become the key ingredient that determines its performance and stability. However, in the decentralized architecture, scheduling is difficult, because the scheduler can't detect everything happening in the cluster, nor can it easily coordinate the decision-making process between multiple nodes.

So you see, a centralized scheduler—in this case, PD—has a unique strength. It has a global view and multi-node coordination for better scheduling. Therefore, for a distributed database, as long as the centralized scheduler doesn't become the system bottleneck, the benefits greatly outweigh the costs. In this paper, PingCAP also conducted strict performance testing to prove that PD, as a single point, will not limit the horizontal scalability of the whole system.

## My future expectations for TiDB

In TiDB, the storage is completely detached from the computing. The storage layer has two engines, TiKV and TiFlash, and the computing layer also has two engines,  SQL engine and [TiSpark](https://docs.pingcap.com/tidb/dev/tispark-overview) (a thin layer for running Apache Spark). In the future, both layers can easily extend into other ecosystems. From a user's perspective, I hope PingCAP will expand TiDB from a database into a distributed storage ecosystem.

HTAP is highly efficient in a single TiDB cluster. It offers strong consistency and resource isolation and eliminates the process of replicating data between different databases. Engineers can write code without worrying about importing and exporting data.

However, when you have multiple TiDB clusters, things get a bit tricky. Though TiDB provides horizontal scalability, it doesn't support [multitenancy](https://en.wikipedia.org/wiki/Multitenancy). Currently, due to application and maintenance requirements (such as backup and restore), a company is unlikely to put all its data in a single TiDB cluster. Thus, if the data required for OLAP requests is stored across multiple clusters, users still have to load data from multiple clusters into a database that processes OLAP requests—again, the troublesome process of importing and exporting data.

One solution is to add a layer similar to [Google F1](https://dbdb.io/db/google-f1) on top of TiDB clusters. Under a unified F1 layer there are multiple TiDB clusters. Each cluster is a tenant completely isolated from the others. The F1 layer manages metadata, routes read and write requests, and processes OLAP requests across clusters.

Another formula is adding tenant management in the storage layer. Each tenant corresponds to a group of storage nodes. In this architecture, the tenants are isolated in the storage layer, and the computing layer can process cross-tenant OLAP requests.

In a word, this is a question about isolating resources in the storage layer and providing a unified view in the computing layer. I look forward to seeing how TiDB will follow up on this.

## Conclusion

PingCAP's implementation of an HTAP database has elegantly solved a decades-long conflict: how to process two types of queries in a single database. [Their paper](https://www.vldb.org/pvldb/vol13/p3072-huang.pdf) does more than lay out a theoretical case; it shows exactly how they implemented the database, and it backs up their claims with solid testing.

As the first paper in the industry to describe the Raft-based implementation of a distributed HTAP database, TiDB's paper proved that a distributed, Raft-based HTAP database is achievable. It may speed up the development and adoption of distributed HTAP databases. In this regard, it marks a milestone.
