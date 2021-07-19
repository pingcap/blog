---
title: Reducing Query Latency from Seconds to Milliseconds with a Scale-Out Database
author: ['China Zheshang Bank']
date: 2021-06-17
summary: As China Zheshang Bank's data size boomed, their databases couldn't meet their requirements for data storage and analytics. They switched to TiDB to scale out their databases and perform real-time analytics.
image: /images/blog/open-source-sql-database-scale-out-mysql-bank.jpg
tags: ['Scalability', 'ACID transaction', 'High availability', 'HTAP', 'Real-time analytics']
customer: China Zheshang Bank
customerCategory: Financial Services
logo: /images/blog/customers/china-zheshang-bank-logo.png
---

**Industry:** Banking

**Author:** China Zheshang Bank

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![An open source SQL database for MySQL horizontal scaling](media/open-source-sql-database-scale-out-mysql-bank.jpg)

[China Zheshang Bank](https://en.wikipedia.org/wiki/China_Zheshang_Bank) is a national joint-stock commercial bank based in China. We aim to provide customers with open, efficient, flexible, and shared comprehensive financial services. By the end of June 2020, we had established 260 branches throughout the country. In terms of total assets, we ranked 97th on the "Top 1000 World Banks 2020" list by the British magazine [The Banker](https://en.wikipedia.org/wiki/The_Banker).

As our businesses grew, our data size boomed. Our databases couldn't meet our requirements for data storage and analytics. After comparing multiple distributed databases, we adopted [TiDB](https://docs.pingcap.com/tidb/stable/overview), an open-source, Hybrid Transactional/Analytical Processing (HTAP) database. Thanks to TiDB, we can easily scale out our databases and perform real-time analytics. In our telecom fraud risk inquiry system, **our query latency is reduced from tens of seconds to tens of _milliseconds_**.

In this post, we'll share our pain points, why we chose TiDB, how we use it now, and our plans for it in the future.

## Our pain points

As our businesses developed, our data volume rapidly increased, and we gradually found our original database solution's shortcomings in data processing and storage. **Our data architecture system couldn't meet our new application scenarios' requirements.** Therefore, we looked for a solution among various distributed databases that were widely used in the internet industry.

## Our database requirements

We wanted an OLTP database that:

* Supports massive amounts of data
* Supports complete distributed transactions
* Provides enterprise-grade high performance, high concurrency, and continuous high availability
* Supports horizontal scalability and smoothly tackles traffic in various kinds of applications
* Has a strong ecosystem to connect to various data application ecosystems

After we tested multiple products and verified application compatibility, we found that **TiDB took the lead in terms of database scalability, query performance under massive data scale, and transaction integrity**. So we adopted it.

## Why we chose TiDB

[TiDB](https://docs.pingcap.com/tidb/stable/overview) is an open-source, cloud-native, distributed SQL database built by [PingCAP](https://pingcap.com/) and its open-source community. It is MySQL compatible and features horizontal scalability, strong consistency, and high availability. You can learn more about TiDB's architecture [here](https://docs.pingcap.com/tidb/v4.0/architecture).

As for its functionalities, TiDB supports complete distributed transactions. It's a one-stop solution for both Online Transactional Processing (OLTP) and Online Analytical Processing (OLAP) workloads for massive data. It provides enterprise-grade high reliability and high availability. If a data center (DC) is down, the cluster can automatically failover.

As for its architecture, TiDB is a NewSQL distributed database. It separates the computing layer from the storage layer, so we can scale the storage capacity and the computing resources by different amounts as needed. It applies to a wide range of applications.

In terms of operations and maintenance, TiDB is compatible with the MySQL protocol, so it significantly reduces personnel learning and development costs. It provides a flexible query interface for application operations personnel. It's easy to monitor and maintain.

## TiDB use cases

Currently, we have deployed TiDB in two DCs in the local city and use five data replicas, which we can scale out later. Eventually, we plan to deploy three DCs in two cities. In the production environment, we've run TiDB in three applications: telecom fraud risk inquiry (telecom anti-fraud), foreign exchange transaction management, and executive cockpit. We'll gradually deploy TiDB to operational data stores (ODSs) and the internet consumer-end inquiry transaction scenario.

### The telecom fraud risk inquiry system

The telecom fraud risk inquiry system saves nationwide telecom anti-fraud data, including transaction accounts and transaction amounts. The system supports querying and monitoring suspicious transactions. It analyzes the characteristics of the transaction amount, number of transactions, type, time, frequency, and recipient and payer. If it finds an abnormal transaction, the transaction will be suspended or it will be immediately reported to the public security authorities.

The telecom anti-fraud system has exceeded 2 billion rows of data in a single table, and the data size increases by millions of rows of data every day. **Our former OLAP database couldn't meet our expectations for data storage and application query performance.**

**But TiDB can elastically scale.** Simply by adding nodes, we can improve the system performance and throughput. Besides, TiDB supports storing and querying massive structural data. Therefore, **our SQL queries' processing time is reduced from tens of seconds to tens of milliseconds**. Thanks to [TiDB Lightning](https://docs.pingcap.com/tidb/stable/tidb-lightning-overview/), a data import tool, we can quickly import millions of data records in a single issued data file to meet the application operational window requirements.

### Foreign exchange transaction management

Based on the foreign exchange supervision requirements, the foreign exchange transaction management system needs to collect, import, store, analyze, and mine foreign exchange transaction data. Related data requires long-term storage. We expect that, in the next few years, the data scale will reach one billion rows. Our previous database Oracle needed sharding. This increased our operations, maintenance, and development costs.

**We switched from Oracle to TiDB and found**:

* TiDB's distributed architecture meets our needs for data scalability.
* TiDB's elastic scalability helps achieve data auto-rebalancing. The scaling process is transparent to application operations and maintenance staff.
* TiDB provides high-availability capabilities for active/active data centers in different places. When a node in the TiDB cluster fails, the system can implement auto-failover to ensure cluster high availability.

### Executive cockpit (real-time operating metric analysis)

The executive cockpit is an analysis system that provides real-time operating metrics for bank managers. By breaking data silos, it can reflect the operating status of various applications in real time and visualize the collected data to analyze metrics and implement decisions.

We use a data replication tool to write the upstream Db2's data changes to TiDB in real time. At the same time, we replicate TiDB's change data to the downstream Apache Kafka platform. Apache Flink receives messages from Kafka for streaming calculations. This system forms an efficient and easy-to-use real-time computing platform. It collects statistics for various business operating conditions of the bank in real time and displays them on a large screen. By capturing massive financial data changes online and performing real-time analytics, the system helps bank managers to make business decisions, and it improves service efficiency.

## Exploring further uses for TiDB

### Distributed real-time ODS

TiDB is a one-stop solution for both OLTP and OLAP applications to process HTAP workloads. [TiFlash](https://docs.pingcap.com/tidb/v4.0/tiflash-overview) is an analytical engine and columnar store for TiDB. A TiDB database that incorporates TiFlash lets you perform real-time HTAP analytics.

Our bank has multiple OLTP heterogeneous databases, mainly Db2 and MySQL, as well as Oracle and SQL Server. We don't have an efficient way to replicate data among these databases, so this creates data silos.

To perform real-time analytics for various applications, we plan to scale out our existing platform and build a distributed real-time ODS based on TiDB. This will enable us to replicate different types of data in heterogeneous databases in near real time.

[TiCDC](https://pingcap.com/docs/dev/ticdc/ticdc-overview/) is TiDB's [change data capture](https://en.wikipedia.org/wiki/Change_data_capture) framework. This open-source feature replicates TiDB's incremental changes to downstream platforms, such as MySQL and Apache Kafka, Pulsar, Flink, and Canal. TiCDC provides real-time, high throughput, and high-availability replication services.

### Internet query transaction

Our bank provides payroll services for government and enterprise users. Each month, we process tens of millions of transactions. Our existing database can't meet our application storage requirement. On one hand, its slow query speed affects our customer experience. On the other hand, it can't be connected with other data. In the future, we'll consider using TiDB as a pilot to replace our existing database.

If you have any questions or want detailed information about our experience, you could join the [TiDB community on Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog).
