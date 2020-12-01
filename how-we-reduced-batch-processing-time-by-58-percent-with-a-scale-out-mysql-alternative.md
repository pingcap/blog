---
title: How We Reduced Our Batch Processing Time by About 58% with a Scale-Out MySQL Alternative
author: ['Panpan Hu', 'Wei Huang']
date: 2020-12-01
summary: WeBank is China's first privately-owned Internet bank. As they grew, they encountered database performance and capacity bottlenecks. By using TiDB, a scale-out MySQL alternative, they reduced their batch processing time by ~58%.
tags: ['Scalability', 'MySQL', 'NewSQL']
url: /success-stories/how-we-reduced-batch-processing-time-by-58-percent-with-a-scale-out-mysql-alternative/
customer: WeBank
customerCategory: Financial Services
categories: ['MySQL Scalability']
logo: /images/blog/customers/webank-logo.png
image: /images/blog/tidb-as-mysql-alternative-database-in-webank.jpg
---

**Industry:** Banking

**Authors:**

* Panpan Hu (Database Platform Manager at WeBank)
* Wei Huang (Senior DBA of Database Platform at WeBank)

![TiDB as MySQL alternative database helps WeBank achieve horizontal scaling](media/tidb-as-mysql-alternative-database-in-webank.jpg)

[WeBank](https://en.wikipedia.org/wiki/WeBank_(China)) is China's first privately-owned internet bank. It is backed by reputable companies such as Tencent. It offers convenient and high-quality financial services to underbanked individuals as well as small- and medium-sized enterprises. So far, we've served 250 million+ individual customers, 20 million+ individual business customers, and 1.5 million+ corporate customers. 

As our businesses grew, our data size soared, and we encountered database performance and capacity bottlenecks. After we compared multiple solutions, we chose [TiDB](https://docs.pingcap.com/tidb/stable/overview), an open-source, MySQL-compatible, [NewSQL](https://en.wikipedia.org/wiki/NewSQL) database. Thanks to its horizontal scalability, in a financing system, **our batch processing time has been reduced by about 58%**. In our evidence data storage system, **we fixed the capacity bottleneck and improved the throughput**. 

In this post, I'll share with you why we chose TiDB over other solutions and how we use TiDB as an alternative to our MySQL database in typical financial scenarios.

## Our pain points: database performance and capacity bottlenecks 

To make our applications horizontally scalable, we designed a distributed, scalable core architecture based on a Data Center Node (DCN). A DCN includes an application layer, an access layer, and a database. Each DCN carries a specified number of users. You can treat a DCN as an online virtual branch of WeBank. This virtual branch serves only a subset of WeBank's customers.

This architecture has these advantages:

* It helps implement cluster horizontal scalability and is friendly to the database. 
* The number of users for each DCN is determined, so we can clearly know the database capacity and performance requirements. 
* We can build the database without using middleware or sharding. This greatly simplifies our database architecture and reduces application development costs.

But we encountered a problem. Internally, DCNs use a single-instance deployment mode. In some application scenarios, we couldn't split a DCN to scale out the database. And in some scenarios, we needed to aggregate data. In these cases, **a single instance's performance and capacity quickly caused a bottleneck**.

## Why we chose TiDB, a NewSQL database

To solve the problems above, we did a thorough investigation and evaluation. In 2018, we compared multiple NewSQL databases and finally adopted TiDB. 

[TiDB](https://github.com/pingcap/tidb) is an open-source, distributed, Hybrid Transactional/Analytical Processing (HTAP) database developed by [PingCAP](https://pingcap.com/) and its open-source community.

TiDB attracted us, because it had these advantages:

* TiDB's distributed architecture helps **horizontally scale our database** while **maintaining strong data consistency**. 
* TiDB is** compatible with the MySQL protocol**. We can use MySQL as the primary database and TiDB as its secondary database. We can seamlessly replicate data from MySQL to TiDB in real time, which minimizes application migration costs.
* TiDB is an **open-source database** with an active open-source community and numerous users. It rapidly iterates. This is in line with our embrace of open source.
* TiDB supports **high availability** with **automatic fault recovery**.
* PingCAP Tech Centers provide **professional technical support** for us. They are responsive and experienced. During our estimation, testing, and deployment to production, they participated actively and gave us constructive solutions and advice.

## How we're using TiDB as an alternative to MySQL

So far, we've deployed TiDB in dozens of application systems in the production environment. **These systems‘ data volumes range from hundreds of gigabytes to dozens of terabytes. **Currently, multiple important systems are under proof of concept (POC) or are ready  for the production environment. 

Today, I'll introduce how we're using TiDB in two important scenarios:

* The batch processing scenario of a financing system
* The evidence data storage system

### TiDB in one of our financing systems

Every day, one of our financing systems replicates tens of millions of basic data from the upstream system, and, in the future, it's expected to access more product data. **Before we adopted TiDB, we faced data currency pressure, and our database capacity was expected to become our bottleneck.** In addition, because our system relied on the upstream system's table schema, it often followed the upstream system to make data definition language (DDL) changes, while the [pt-online-schema-change](percona.com/doc/percona-toolkit/LATEST/pt-online-schema-change.html) (pt-osc) solution has many limitations.

We had these problems:

* A standalone MySQL database's capacity didn't support horizontal scalability. As our business grew, the database capacity bottleneck became increasingly severe.
* A standalone MySQL database's performance didn't support horizontal scalability. We couldn't linearly improve batch processing efficiency by scaling resources.
* For basic data, in full table cleaning and highly concurrent insertion scenarios, highly concurrent threads might cause primary-secondary delays, so the standalone MySQL database limited the flow. This reduced the overall currency of batch processing.
* A standalone MySQL database's online DDL feature had problems such as table locks, primary-secondary delays, and sudden I/O increases. And the pt-osc solution had many restrictions.

**Thanks to TiDB's horizontal scalability, our batch processing time has been reduced by about 58%.** In the future, we'll use [TiFlash](https://docs.pingcap.com/tidb/stable/tiflash-overview), TiDB's analytical engine, in the production environment for offline report statistical logic to reduce processing time.

### Migrating our evidence data storage system from MySQL to TiDB

The evidence data storage system is a very important WeBank system. 

**Before we used TiDB, we encountered system capacity and throughput bottlenecks.** As we connected more application systems to this system, data quickly grew. We couldn't find a MySQL-compatible database that could keep up. In addition, the application data was global data that couldn't be split based on DCN, so it couldn't horizontally scale.

To solve these issues, we decided to [migrate from MySQL to TiDB](https://pingcap.com/blog/dm-2.0-ga-secure-easy-highly-available-data-migration#webank) with [TiDB Data Migration](https://docs.pingcap.com/tidb-data-migration/stable/), an integrated data migration tool. During migration, we hoped:

* Data wouldn't be incorrect or lost. 
* We could seamlessly switch to TiDB. 
* If we had any difficulties during migration, we could switch back to MySQL at any time, because we were in a critical financial scenario.  

**The migrating process was a little long, but it was smooth and secure.** After we performed a series of migration operations and observations, all our performance metrics were stable. Therefore, we decided to disconnect reverse replication to MySQL. This means that our evidence data storage system is completely running on TiDB. **Due to TiDB's horizontal scalability, we've fixed the capacity bottleneck and improved the throughput.**

## What's next

Because of TiDB's horizontal scalability and MySQL compatibility, we can use it as an alternative to the MySQL database to resolve our database capacity and performance bottlenecks. 

Since WeBank was established, technology has always been the core engine driving our business development. Now, our core system can support **100 million+ users** and** highly concurrent transactions**. We've achieved an average of **300 million+ daily transactions** and **a peak of 600 million+ single-day transactions**. Our operation and maintenance cost per account is** less than one-tenth of the industry average**.

In the future, based on our application requirements and TiDB's new features, we'll explore more application scenarios at WeBank.

If you'd like to learn more about our experience with TiDB, you can join the [TiDB community on Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog).
