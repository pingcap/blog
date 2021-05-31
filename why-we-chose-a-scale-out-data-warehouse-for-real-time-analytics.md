---
title: Why We Chose a Scale-Out Data Warehouse for Real-Time Analytics
author: ['PatSnap']
date: 2021-05-31
summary: As PatSnap's businesses developed, their data size quickly grew. To perform real-time analytics, they replaced their Segment + Amazon Redshift data analytics architecture with a TiDB + Apache Flink data warehouse solution.
image: /images/blog/free-real-time-data-analytics-tools.jpg
tags: ['HTAP', 'Real-time analytics']
customer: PatSnap
customerCategory: Internet
logo: /images/blog/customers/patsnap-logo.png
---

**Industry:** Artificial Intelligence

**Author:** PatSnap

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![Real time data streaming tools and technologies](media/free-real-time-data-analytics-tools.jpg)

[PatSnap](https://www.crunchbase.com/organization/patsnap) is a global patent search database that integrates 150 million+ patent data records, 170 million+ chemical structure data records, and thousands of records about financial news, scientific literature, market reports, and investment information. Our users can search, browse, and translate patents, and generate patent analysis reports. We help 10,000+ customers in 50+ countries make better innovation decisions.

As our businesses developed, our data size quickly grew. Previously, we used the Segment + Amazon Redshift data analytics architecture, but it delivered data with poor currency. We needed a data analytical tool that provided more current data. After we compared multiple solutions, we chose the [TiDB](https://docs.pingcap.com/tidb/stable/overview) + [Apache Flink](https://flink.apache.org/) real-time data warehouse solution. It is fast and horizontally scalable. Now, we can perform data analytics in minutes and make faster and wiser business decisions.

In this post, we'll share why we adopted TiDB + Flink, how we use this data warehouse, and what benefits it brings us.

## Our paint points

As our businesses develop and our users quickly grow, during business operations, we deeply rely on real-time data analytics and result reports to analyze user behaviors. We need real-time market data, operational data for specific scenarios, and traffic and service analysis.

Originally, we used the Segment + Amazon Redshift data analytics architecture and only built the operational data store (ODS) layer. We couldn't control data write rules and schemas. In addition, we needed to write complex extract-transform-load (ETL) job scripts for ODS. To complete data requests from upper-level applications, we needed to calculate various metrics based on application requirements. Redshift stored a large amount of data, and it calculated data slowly. This lowered external service efficiency.

## Why we chose the TiDB + Flink real-time data warehouse 

After we compared multiple solutions, we decided to use the TiDB + Flink real-time data warehouse solution to improve our data analytical capabilities.

[TiDB](https://docs.pingcap.com/tidb/stable/overview) is an open-source, distributed, Hybrid Transactional/Analytical Processing (HTAP) database. It's a one-stop solution for both Online Transactional Processing (OLTP) and Online Analytical Processing (OLAP) workloads. TiDB's architecture integrates row storage and column storage. Its storage uses separated nodes to ensure that OLTP and OLAP workloads don't interfere with each other. 

[Apache Flink](https://flink.apache.org/flink-architecture.html) is a big data computing engine with low latency, high throughput, and unified stream- and batch-processing. It's widely used in scenarios with high real-time computing requirements and provides exactly-once semantics.

Combining TiDB and Flink into a real-time data warehouse has these advantages:

* **Fast speed.** You can process streaming data in seconds and perform real-time data analytics. 
* **Horizontal scalability.** You can increase computing power by adding nodes to both Flink and TiDB.
* **High availability.** With TiDB, if an instance fails, the cluster service is unaffected, and the data remains complete and available. Flink supports multiple backup and restore measures for jobs or instances.
* **Low learning and configuration costs.** TiDB is highly compatible with the MySQL protocol. In Flink 1.11, you can use the Flink SQL syntax and powerful connectors to write and submit tasks.

## How we use TiDB + Flink

When we replaced our Segment + Redshift architecture with Kinesis + Flink + TiDB, we found that we didn't need to build an ODS layer in the database, but just in Amazon Simple Storage Service (S3) storage.

As a precomputing unit, Flink builds a Flink ETL job for the application. This fully controls data saving rules and customizes the schema; that is, it only cleans the metrics that the application focuses on and writes them into TiDB for analytics and queries.

We build three layers on top of TiDB: data warehouse detail (DWD), data warehouse service (DWS), and analytical data store (ADS). These layers serve application statistics and list requirements. They are based on user, tenant, region, and application metrics, as well as time windows of minutes or days. The upper application can directly use the constructed data and perform real-time analytics within seconds.

![PatSnap real-time analytics platform](media/patsnap-data-analytics-platform-architecture.jpg)
<div class="caption-center"> PatSnap data analytics platform architecture </div>

This real-time analytical platform architecture realizes truly **_real-time data as a service_**. We use it to analyze and track user behaviors and analyze tenant behaviors in real time. It provides real-time data support for our business operations.

## How we benefit from TiDB + Flink

After we adopted the TiDB + Flink architecture, we found that:

* Inbound data, inbound rules, and computational complexity are greatly reduced.
* Queries, updates, and writes are much faster.
* Reasonable data layering greatly simplifies the TiDB-based real-time data warehouse, and makes development, scaling, and maintenance easier. **Our query performance for complex reports remarkably increases.** In many application scenarios, our queries' data currency greatly improves. Previously, after some data was generated, it took one day to retrieve queries for business use. But now, they are near real time for analytics. 
* This solution meets requirements for different ad hoc queries, and we don't need to wait for Redshift precompilation.

If you want to know more details about our story or have any questions, you're welcome to join the [TiDB community on Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog) and send your feedback. 
