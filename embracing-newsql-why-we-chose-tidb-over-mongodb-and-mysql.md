---
title: 'Embracing NewSQL: Why We Chose TiDB over MongoDB and MySQL'
author: ['Xianlin Chen']
date: 2020-11-12
summary: In this post, PalFish explains why they chose TiDB over MongoDB and MySQL. The key factors were their application requirements and their perspective on NewSQL databases.
tags: ['NewSQL', 'ACID transaction', 'MySQL', 'Big data']
image: /images/blog/palfish-embracing-newsql-tidb.png
url: /success-stories/embracing-newsql-why-we-chose-tidb-over-mongodb-and-mysql/
customer: PalFish
customerCategory: Internet
logo: /images/blog/customers/palfish-logo.png
---

**Industry:** EdTech

**Author:** Xianlin Chen (Head of Technology Hub at PalFish)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![PalFish Embracing NewSQL](media/palfish-embracing-newsql-tidb.png)

[PalFish](https://www.crunchbase.com/organization/palfish) is a fast-growing online education platform that focuses on English learning. It offers tailored English speaking experience to English as a Second Language (ESL) students. As of October 2020, PalFish has over 40 million users, of which more than 2 million are paid users.

As our business rapidly grew, the surge of data posed a severe challenge to our MongoDB database. MongoDB (2.x and 3.x) does not support transactions and has no predefined schema to directly regulate data. This blocked our business growth. To solve these problems, we migrated from MongoDB to [TiDB](https://github.com/pingcap/tidb), an open-source, MySQL-compatible, distributed SQL database that supports [Hybrid Transactional/Analytical Processing](https://en.wikipedia.org/wiki/Hybrid_transactional/analytical_processing) (HTAP) workloads. This turned out to be the right move.

In this post, we'll share with you why we chose TiDB over MongoDB and MySQL and **how TiDB supports our application with doubled users**. We hope our experience can help you find the most appropriate database for your application.

## Why we outgrew MongoDB

_(In this section, the MongoDB discussion is based solely on MongoDB 2.x and 3.x.)_

To understand our migration from MongoDB to TiDB, we must first understand PalFish's application scenarios. Application requirements are a significant factor in choosing the data infrastructure, including the database.

When PalFish was established in 2015, NoSQL databases were prevalent in the market. At PalFish, we were still exploring our business model, and our products iterated at an incredible speed. Given the situation, MongoDB was a good fit:

* Since MongoDB was a NoSQL database, we didn't need to use any data definition language (DDL) operations, like creating schemas or creating tables. At that time, this approach was more efficient because we needed to frequently add and delete fields.
* As a standalone database, MongoDB also performed better than MySQL, so it saved us a great deal of maintenance cost.
* MongoDB offered various options on data consistency, which, combined with multi-version concurrency control (MVCC) on the application layer, could implement simple transactions. Because we didn't need full-fledged transactions, MongoDB met our needs.

In other words, in the early stage of PalFish, the selection of MongoDB was a trade-off. We traded data constraints and transactions for efficiency. But as our business expanded and our product matured, the priority shifted: efficiency, transactions, and constraints became equally important. MongoDB was no longer a good pick. Our new requirements are:

* **We need [ACID transactions](https://en.wikipedia.org/wiki/ACID).** ACID, which is short for atomicity, consistency, isolation, and durability, can guarantee data validity in the event of failure. Our applications extend from money to virtual currency, and the level of concurrency rises drastically. Without the guarantee of ACID transactions, there would be more conflicts. In MongoDB, we had to implement transactions in the application layer, but it wasn't efficient and was prone to errors.
* **We need big data capacity.** It was already hard enough to do OLAP workloads in a traditional OLTP database like MongoDB, and our huge data volumes only added to the difficulty. To make matters worse, almost the entire big data ecosystem was built on top of MySQL. If we tried to integrate MongoDB into that ecosystem, it would be almost like reinventing the wheel.
* **We need more data constraints.** MongoDB had almost no data constraints, which meant the data schema could be out of control. With more engineers involved in the development cycle, it might become a disaster. Data constraints were now a higher priority.

After we analyzed our use scenarios, we realized that we needed a new database that provided:

* High availability
* High throughput
* ACID transactions
* Big data ecosystem
* Horizontal scalability, without intrusion into the application

Viewing these requirements, we knew that NoSQL wouldn't be an option. To address massive amounts of data, NoSQL is designed to be "[basically available, soft state, eventual consistency](https://www.techopedia.com/definition/29164/basically-available-soft-state-eventual-consistency-base) (BASE)"—just the opposite of ACID. The lack of an ACID transactional capability limits the use scenarios of MongoDB, as well as other NoSQL databases. Besides, NoSQL doesn't support SQL, so we can't reuse the rich resources accumulated by other RDBMSs in the past few decades.

Bearing these in mind, we started the quest for the ideal database. And that's when TiDB was brought to our attention.

## Why we chose TiDB

[TiDB](https://docs.pingcap.com/tidb/stable/overview) is an open source, distributed SQL database. It is MySQL compatible and features horizontal scalability, strong consistency, and high availability.

From our past impressions, distributed databases are good at coping with massive data that traditional standalone databases cannot handle. But it's troublesome to guarantee consistency in distributed storage, not to mention ACID transactions.

Therefore, in our initial investigation, what surprised us most was that as a distributed database, **TiDB supports ACID transactions**. It uses [the Raft consensus algorithm](https://en.wikipedia.org/wiki/Raft_(computer_science)) to achieve data consistency across multiple replicas, [the two-phase commit (2PC) protocol](https://en.wikipedia.org/wiki/Two-phase_commit_protocol) to ensure the atomicity of transactions, and [optimistic concurrency control](https://en.wikipedia.org/wiki/Optimistic_concurrency_control), combined with [MVCC](https://en.wikipedia.org/wiki/Multiversion_concurrency_control), to implement a repeatable read level of isolation.

We decided to give it a shot and started a simulation test. In this test, our application wrote to MongoDB synchronously and wrote to TiDB asynchronously, but only read data from MongoDB. Three months went by, and TiDB worked almost flawlessly, so we read and wrote to TiDB synchronously, while we wrote to MongoDB asynchronously. MongoDB was the backup, and all was right with the application.

As we have mentioned, TiDB is an open source project. The primary maintainer behind it is the [PingCAP](https://pingcap.com/) team. Before we put TiDB into full production, we met with engineers at PingCAP. After learning about the wide usage of TiDB in various companies, we felt more than optimistic about TiDB's prospects.

## MySQL vs. TiDB

Some may ask, if we want ACID transactions so badly, why go through all that trouble to try out an unfamiliar database, when MySQL, a long-established database with transaction guarantees, is just a click away?

The motivation behind this is complicated. For mature businesses, choosing a database is never a simple decision. **It's not just about the technology today, but where it's going**. It's a reflection of how you view technology and how you position your company in this fast-changing world.

### Attitudes toward new technology: NewSQL is the future

When you compare MySQL and TiDB, TiDB doesn't seem like a strong competitor. MySQL is proven to be a stable database. For all our requirements, it has available solutions, such as high availability and scalability, although the implementation is not very elegant. (You must manually shard the data.)

However, at PalFish, the real problem is that a standalone database can't handle the huge amount of data, and in this regard, a distributed database is a better fit. With TiDB, which is a horizontally-scalable database, **sharding is permanently taken out of mind**. It provides a solution, not a compromise. Indeed, TiDB is less stable and mature than MySQL, but we believe given enough time, it will outperform traditional relational databases.

### The cost of the machine or the cost of the talent?

Cost and efficiency were also important factors in our decision-making. At first glance, the hardware resources needed by TiDB are daunting. But we know that machines take up only a portion of the total cost—not all of it.

TiDB needs more and better machines than MySQL does, but it also saves more time for developers and DBAs. Remember the rule of economy in the Unix philosophy? "Programmer time is expensive; conserve it in preference to machine time." **At PalFish, we always expect the machine and software to do more, and our people to do less**. That's exactly what TiDB has to offer.

MySQL does provide high availability, but our DBA and infrastructure team needs to spend time on the implementation. MySQL can handle big tables, but the data sharding must be done by DBAs and engineers. It takes time—time that we could invest more wisely. With MySQL, the consumption of talent is also the cost: it's just not so apparent and tangible as the extra machines TiDB requires. As machines become cheaper and talent more expensive, we must be aware of such invisible expenses.

### The latecomer advantage

Another incentive is our role as a startup. In areas of mature technologies, we can hardly compete with tech giants. They have spent years accumulating their strengths, while we just built our business from scratch. Often, we have no choice but to be a follower of old tech; but when new technology is arriving, what will become of us if we don't jump at the opportunity?

As latecomers, we must turn our weakness into our edge. That is, when established companies are still trudging along the old way, we'll predict the trends and choose the technology that faces the future. This is how we avoid technical debt and overtake older tech companies like a fast car passing a slower one on a corner.

### Tech ecosystem

Choosing a technology is also choosing the ecosystem that comes with it. MySQL has a well-rounded ecosystem, which enables us to do more with less. Thanks to the MySQL-compatible strategy, as a TiDB user, **we can share the MySQL ecosystem, as well as enjoying the benefits of NewSQL**.

After a thorough review, **PalFish decided to go all-in with TiDB**. We no longer add new databases or tables to MongoDB, and instead migrated all big tables from MongoDB to TiDB.

## How we're using TiDB

Here I'd like to share two typical scenarios of TiDB in PalFish: the online class data storage and the trading system.

### Application 1: Online class

Online class is one of PalFish's core applications. In our online classes, students and teachers frequently interact. During the class, teachers often need to write or draw on the digital whiteboard and present contents to students. All these data must be stored in our databases.

In the first half of this year, due to the pandemic, the number of online class users and classes taken more than doubled. Our data volume skyrocketed. Even a single table that stored the whiteboard track records reached 1.5 TB. The total data exceeded 4.3 TB.

In face of such intense data growth, TiDB perfectly fulfilled its duty. **Without any extra adjustment, TiDB horizontally scaled out to handle the massive data from our applications**.

### Application 2: The trading system

As a for-profit online education platform, PalFish provides an online marketplace and the corresponding trading system. Our trading system includes cash payment and virtual currency payment in various applications. This use case has the most stringent database requirements:

* No data loss.
* No inconsistent data.
* The database must support ACID-compliant transactions.
* Because of the explosive growth of data, the database must be able to scale out.

From the end of 2019 to October 2020, our paid users increased from 500,000 to over 2 million. **Even under the pressure of quadrupling users, TiDB successfully supported our core trading system**.

### Our current status with TiDB

This is how we're using TiDB now at PalFish:

* We have 10 TiDB clusters, over 60 instances, 107 nodes, and 6 core clusters, each of which processes over 10,000 transactions per second (TPS).
* Our 99.9th percentile latency remains as low as 16~30 ms.
* Response time, stability, and scalability meet our expectations.

Looking back, we can say with confidence that moving to TiDB was the right decision. We have overtaken established companies in database technology and enjoyed the benefits of a NewSQL database. Since the migration, the R&D and DBA teams are working with much greater efficiency. What's more, TiDB's [new releases](https://docs.pingcap.com/tidb/stable/release-notes) never fail to impress us.

## Lesson learned

While we reap the benefits of TiDB, we also have to bear the cost of the unknown. Here, I'd like to show you the problems we encountered in our adjustment period.

### Optimizer index selection

There were several times when the optimizer couldn't select a correct index, and this resulted in failure.

PingCAP engineers investigated the issue and found it was caused by a bug in the optimizer index selection. Luckily, they took measures to fix it. From TiDB 1.x to 3.x, the optimizer has grown more and more efficient. With performance monitoring and slow log monitoring, our DBA team can now quickly spot the problem. We also force indexes on big tables to avoid potential risks.

### Big data replication

To do data analysis, we gathered data from many upstream TiDB clusters into a single TiDB cluster to be used for big data analytics. However, the data replication was slow, and the data and data encoding were inconsistent, which caused replication failure.

As we deepened our knowledge of TiDB, and with the support of the PingCAP team, we got better at managing TiDB and successfully resolved the data replication problem.

## Conclusion

As a NewSQL database, TiDB is compatible with the MySQL protocol and supports horizontal scalability, high availability, ACID transactions, and real-time analytics for large amounts of data. That's why we chose it over MongoDB and MySQL.

In this day and age, when Moore's law is starting to fail, and high availability and cost optimization have become high-level concerns, a distributed architecture inevitably gains traction. For stateless services, we have traffic routing strategies plus multi-replica deployments (like microservices); for caching, we have schemes like Redis Cluster and Codis; with Kubernetes, the operating system also completed its own course of evolution.

And what about databases? If you ask me, the NewSQL database is surely the next big thing.

_Note: An abridged version of this article was published on [The New Stack](https://thenewstack.io/embracing-newsql-why-palfish-chose-tidb/)._
