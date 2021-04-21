---
title: "How China's Insurance Giant Improved Agile Application Performance with a NewSQL Database"
author: ['Ping An Jin Guanjia Application Development Team']
date: 2020-12-08
summary: Ping An Life Insurance shares a case where TiDB helped them support 100 billion RMB payment volume in a single day, the pain points before they used TiDB, how they use TiDB, and why they chose TiDB.
tags: ['MySQL compatibility', 'NewSQL', 'Data replication', 'Disaster recovery']
url: /success-stories/how-chinas-insurance-giant-improved-agile-application-performance-with-a-newsql-database/
customer: Ping An Life Insurance
customerCategory: Financial Services
logo: /images/blog/customers/pingan-life-insurance-logo.png
image: /images/blog/china-insurance-giant-improved-agile-application-performance-with-newsql-tidb-database.jpg
---

**Industry:** Insurance

**Author:** Ping An Jin Guanjia Application Development Team

**Transcreator:** [Coco Yi](https://github.com/yikeke); **Editor:** Tom Dewan

![How China's Insurance Giant Improved Agile Application Performance with a NewSQL Database](media/china-insurance-giant-improved-agile-application-performance-with-newsql-tidb-database.jpg)

[Ping An Life Insurance](https://www.bloomberg.com/profile/company/OPAHWZ:CH) is a world-leading life insurance company under the [Ping An Insurance Group](https://wikipedia.org/wiki/Ping_An_Insurance). The company builds a one-stop mobile application to provide services such as insurance policies, life assistants, and health management. We are the development team behind the app.

In the past three years, the number of our users has increased by 6 times, with more than 200 million registered users, and nearly 10 million daily active users (DAU) at the peak time. **The database gradually became the biggest bottleneck in the IT infrastructure.**

To solve the bottleneck, we migrated from Oracle to [TiDB](https://docs.pingcap.com/tidb/stable), an **open-source, MySQL-compatible, distributed SQL database** that supports [Hybrid Transactional/Analytical Processing](https://wikipedia.org/wiki/Hybrid_transactional/analytical_processing) (HTAP) workloads. Now, users can submit and receive claims online within a few hours. (Previously, it would take weeks.)

This post will first describe a case where TiDB helped us support 100 billion RMB payment volume in a single day, as well as the pain points before we used TiDB, how we use TiDB now, and why we chose TiDB.

## Surviving our big day of the year

Every year, on January 8, we hold an online financial carnival, "Wealth God Festival," which is similar to the shopping carnival "Black Friday." On that day, millions of consumers will log on to the app and participate in various online activities such as [seckills](https://www.urbandictionary.com/define.php?term=seckill), lucky draws, and lucky money collection.

These agile operating activities are a big challenge to our application team because of:

* Huge and intensive traffic
* Tight development time and pressure to create new, innovative gameplay
* Rigorous requirements for financial business

Specifically, the database requirements include:

* High concurrency and low latencies
* Elastic scale on demand because the Transactions Per Second (TPS) is uncertain
* Financial-level consistency and real-time online analysis capabilities

2019's "Wealth God Festival" saw a big success—the payment volume exceeded 100 billion RMB in a single day. Behind the scenes, hundreds of TiDB database instances were unremittingly delivering **smooth frontend queries** and **convenient backend operations**. TiDB enabled us to:

* Use standard SQL syntax to speed up agile application development
* Scale out and in quickly by adding or removing nodes online
* Use secondary indexes and use SQL statements to analyze real-time data
* Simplify the database operations; for example, we did not need to maintain a complicated tech stack such as NoSQL with Hadoop

## Previous pain points

Our app's backend system originally used minicomputers and the Oracle database. As the data size grew, Oracle mainly brought the following two problems:

* The hardware costs to support traffic-intensive online activities.
* In some cases, we needed to split complex logical tables, causing high operational costs.

We considered using MySQL. However, that would require us to do some things we'd prefer not to. Namely:

* Separate read and write workloads
* Shard databases and tables
* Implement the distributed transactions on the application layer

We needed to find another database that met our agile business requirements. We turned our attention to distributed NewSQL databases.

After a comprehensive investigation of factors such as **open-source technology ecosystems,** **enterprise-level application scenarios**, and **professional support services**, we decided to use TiDB as the backbone of our app's core modules and most agile modules.

## How we use TiDB

> *"NewSQL databases can be scaled on demand, dynamically adapting the entire system's performance to meet uncertain business needs. The storage and query of massive structured data are no longer a headache, greatly improving the efficiency of our application development. TiDB performs well in steady-state business scenarios. It is also an ideal choice in agile business scenarios." Ping An Jin Guanjia Application Development Team*

We've built a set of distributed TiDB clusters that support high concurrency, high availability, and horizontal scalability. Production data from various application modules are written to the clusters in real time, while guaranteeing financial-level intra-city and offsite disaster tolerance.

Our TiDB clusters include production databases, databases for intra-city disaster recovery, and databases for offsite disaster recovery. We replicate production data from Oracle to MySQL through Oracle Golden Gate (OGG), and then replicate the data from MySQL to TiDB in real time through the [TiDB Data Migration](https://docs.pingcap.com/tidb-data-migration/stable) tool. We use [TiDB Binlog](https://docs.pingcap.com/tidb/stable/tidb-binlog-overview) to ensure data consistency between the recovery databases and development databases in different cities.

From the application layer, we can easily call TiDB's standardized API. TiDB provides an easy-to-use query interface, which makes our application operators' life easier.

TiDB also provides a solution for multi-active data centers—if any data center is down, the entire cluster can automatically switch traffic and resume service without users' awareness. In addition, TiDB can be well integrated into the cloud-native data ecosystem, avoiding data silos.

Currently, we've migrated more than **30 TB** of data to the TiDB clusters. The migration is still going, and the overall migrated data volume is expected to exceed **100 TB**.

## Why we chose TiDB

The TiDB distributed database integrates perfectly into the new tech stack of our distributed application core systems. We trust our data to TiDB because it:

* **Reduced financial and development costs**

    Compared with an Oracle-based IT infrastructure, the hardware cost was reduced by over 30%, and TiDB's MySQL compatibility significantly lowers the learning curve and improves the development efficiency of our app developers.

* **Scaled up the database performance**

    Through elastically and horizontally scaling, our database's performance was improved by orders of magnitude. For example, our Internet insurance core module can smoothly respond to **thousands of orders per second**.

* **Minimized operational costs**

    PingCAP, the team behind TiDB, provides very professional support. We can truly trust TiDB to do all the "dirty" work and let our technical team focus on core module development.

## Last word

With TiDB, we improved our data infrastructure's capabilities, laying a solid foundation for larger-scale business growth in the future. Thank you TiDB, for making it so much easier for us.
