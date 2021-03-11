---
title: Empowering Your Gaming Application with a Scale-out NewSQL Database
author: ['Han Liu']
date: 2021-03-11
summary: To handle increasing data of their gaming business, Kunlun migrated from MySQL to TiDB, a MySQL compatible NewSQL database featuring horizontal scalability and a powerful ecosystem.
tags: ['Scalability', 'Cloud', 'MySQL']
customer: Kunlun
customerCategory: Gaming
logo: /images/blog/customers/kunlun-logo.png
image: /images/blog/kunlun-empowering-your-gaming-application-with-a-scale-out-newsql-database.png
---

**Industry:** Gaming

**Author:** Han Liu (Director of IT operations at Kunlun)

![Empowering Your Gaming Application with a Scale-out NewSQL Database](media/kunlun-empowering-your-gaming-application-with-a-scale-out-newsql-database.png)

[Kunlun](https://www.crunchbase.com/organization/kunlun) is an industry leading internet company, focused on gaming and information. Its gaming platform, [GameArk](http://www.gameark.com/), develops and distributes games across the globe, boasting over 100 million monthly active users.

As our gaming business booms, data is generated at an increasingly fast speed. To store and analyze the data, we tried various database solutions, from traditional RDBMS to NoSQL to NewSQL. Thanks to **[TiDB](https://docs.pingcap.com/tidb/stable), a MySQL-compatible, horizontally scalable NewSQL database**, we are able to **make full use of terabytes of data to provide big data analytics for our business**.

In this article, I'll share with you how we struggled with previous MySQL solutions and why we chose TiDB to replace them. I'll also introduce how we are using TiDB now in our system.

## Our pain points

When users play online games, they generate lots of data. Every aspect of a game—the location of players in the game space, the tasks they complete, their fights, and their promotion to higher levels in the game and so on—generates meaningful information. As our business evolves, we need to store and analyze these data to better understand our users and facilitate marketing and operations.

Back in 2008, we used MySQL to support our data analytics system. The gaming application sent the generated data to the specified interface in real time, and MySQL received and stored the data. At the beginning, the small data volume didn't put much pressure on the database. However, as our user base grew, **a single table in MySQL had to store more than 50 million rows of data, resulting in slow reads and writes**. So we started the quest for a database solution that can scale horizontally to support our business.

### Optimize SQL statements

Thinking over our application and system architecture, we decided to reform the current MySQL database with as little code change as possible. The first plan was to optimize SQL statements and locate slow queries.

However, as the table became larger, we couldn't significantly improve SQL execution efficiency. **Creating more shards might be helpful in the short term, but it would entail a series of other problems**, such as cross-node SQL joins, cross-node paginating, sorting, and functions. That would be complicated and require code changes. In effect, this plan was to achieve horizontal scaling by "adding patches."

### From standalone MySQL to MySQL Cluster

[MySQL Cluster](https://en.wikipedia.org/wiki/MySQL_Cluster) is the shared-nothing enterprise database solution provided by Oracle. It tackles the single point of failure issue in standalone MySQL and supports automatic failover. In addition, it provides better scalability and higher performance.

To address the single point of failure issue, we migrated from standalone MySQL to MySQL Cluster. But MySQL Cluster also had obvious downsides:

* **High cost.** The old version of MySQL Cluster stored data in memory, so a single machine needed 512 GB of memory, sometimes even more. As the data piled up, the hardware cost skyrocketed.
* **Restricted features.** MySQL Cluster didn't support foreign keys, and each row of data had to be smaller than 8 KB.
* **Poor backup and restore methods.** DBAs had to manually enter backup commands on each node. Moreover, we couldn't store the backup data in remote storage like Amazon S3.
* **Complicated deployment, management, and configuration.** It was difficult to make it work with our IT infrastructure on the cloud.

Therefore, MySQL Cluster was not an ideal solution for us, either.

## Why we chose TiDB

To meet our requirements for performance, scalability, cloud deployment, and maintenance, we decide to adopt TiDB, a NewSQL database, because:

* **TiDB is compatible with the MySQL protocol**. We can migrate to TiDB with little code change.
* TiDB can **elastically scale its computing and storage capacity**, thanks to the architecture that separates storage from computing. Its read and write Queries per Second (QPS) and average latency meet the requirements of our application.
* TiDB has **a powerful ecosystem**. We can integrate TiDB into other data services, such as Spark, Flink, and Kafka, to build a one-stop data platform.
* TiDB can **reduce our hardware cost**. TiDB supports cloud deployment and connects seamlessly with Amazon S3. After deploying the entire data analytics system on the cloud, we reduce our hardware costs by 50%.

## Our current status with TiDB

Currently, GameArk has deployed a TiDB cluster that is **highly available** and **supports high concurrency and horizontal scalability on public clouds**. With the help of [TiDB Data Migration](https://docs.pingcap.com/tidb-data-migration/stable/overview/), we migrate **dozens of TB of data** from multiple MySQL databases to the TiDB cluster, which in theory provides infinite scalability. We also integrate the TiDB cluster with Kafka, Flink, Hive, Spark, and Aerospike to establish a comprehensive data system:

![TiDB architecture at Kunlun](media/kunlun-tidb-architecture.png)
<div class="caption-center"> TiDB architecture at Kunlun </div>

In the future, we would like to build a more agile data service:

* We'll improve database service efficiency by using the distributed architecture so that the database can better service our application.
* We'll also try to decouple the database application layer from the underlying infrastructure layer, making the application less dependent on the infrastructure technology and lowering the overall IT construction and maintenance cost.

With the help of TiDB, a cloud-native NewSQL database, we are more than confident in building a data service that meets our needs.
