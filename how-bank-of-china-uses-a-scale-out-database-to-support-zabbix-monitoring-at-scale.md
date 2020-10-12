---
title: 'How Bank of China Uses a Scale-Out Database to Support Zabbix Monitoring at Scale'
author: ['Yu Han']
date: 2020-10-12
summary: 
tags: ['Scalability', 'MySQL compatibility', 'MySQL', 'Best practice']
url: /case-studies/how-bank-of-china-uses-a-scale-out-database-to-support-zabbix-monitoring-at-scale/
customer: Bank of China
customerCategory: Financial Services
categories: ['MySQL Scalability']
logo: /images/blog/customers/bank-of-china-logo.png
image: /images/blog/how-bank-of-china-uses-a-scale-out-database-to-support-zabbix-monitoring-at-scale.jpg
---

**Industry:** Banking

**Author:** Yu Han (DevOps Engineer at VNG Corporation)

![How Bank of China Uses a Scale-Out Database to Support Zabbix Monitoring at Scale](media/how-bank-of-china-uses-a-scale-out-database-to-support-zabbix-monitoring-at-scale.jpg)

Bank of China is the fourth largest state-owned commercial bank in China. Since 2016, we've been using Zabbix, a popular open-source monitoring solution, to monitor our IT infrastructure. We used to use MySQL as the backend storage for Zabbix; however, MySQL is not scalable enough to monitor IT environments on a large scale. After trying different solutions, we chose TiDB, a **MySQL-compatible**, **open-source**, **distributed SQL database** to replace MySQL as the backend for a large-scale Zabbix. (We call this collaboration **"TiZabbix"**.) With TiZabbix, we successfully monitor more than 10,000 hosts and query 18 TB of monitoring data.

In this blog post, I will first introduce the traditional Zabbix monitoring solution we adopted and our pain points at the time. Then, I will give a detailed look at how we use TiDB in Zabbix. Finally, I will share our further plans to optimize TiZabbix.

## Our pain points

Zabbix mainly consists of the following four components:

- **Zabbix agent**: A process deployed on hosts (that is, monitoring targets) that actively monitors local resources and applications and reports the collected data to Zabbix server.
- **Zabbix server**: A central process of Zabbix software that performs monitoring, interacts with Zabbix proxies and agents, calculates triggers, and sends notifications.
- **Frontend**: The Zabbix web interface used to configure data collection and alert rules, visualize data, and make API calls.
- **Database**: The backend storage for all configuration information and the monitoring data collected by Zabbix server.

The standalone MySQL database fit our needs well until the data size surged and reached the TB level. After the database became the bottleneck, we had to make tradeoffs between the number of hosts and how long we store the collected data.

The Zabbix team introduced "proxies" as a solution to manage more hosts, but the proxies, as well as the servers, send the data to the database backend, which does not ease the burden on the database.

Aiming to use Zabbix for large-scale monitoring, we decided to replace MySQL with TiDB, a horizontally scaling database, as the backend storage.

## TiZabbix: use the TiDB database as Zabbix backend

[TiDB](https://github.com/pingcap/tidb) is an open-source, distributed SQL database. It is MySQL compatible and features **horizontal scalability**, strong consistency, and high availability. It's a one-stop solution for both Online Transactional Processing (OLTP) and Online Analytical Processing (OLAP) workloads.

We tried Zabbix with different deployments and backends until we finally settled on TiZabbix. Here is a simple timeline:

- 2016: We started off by using a single Zabbix server instance with the MySQL backend to monitor over 1,000 Linux servers. At the time, the database stored 60 days of history data collected on a per-minute basis.

- 2017: We deployed two Zabbix server instances, each of which monitored over 1,000 Linux servers. We used Python to write the history data collected by Zabbix to Elasticsearch. But Python's read/write process is not as stable as a database read/write, so we quickly abandoned this method.

- 2018: We replaced MySQL with TiDB as the backend of the native Zabbix solution in production.

    > Background story: At the time, Elasticsearch was officially supported by native Zabbix as the backend storage. But we figured that TiDB might be more suitable in our case as TiDB is a distributed SQL database and compatible with the MySQL protocol. Also, Elasticsearch's usability was not very good; for example, Elasticsearch's upgrade operations were not as friendly for beginners as TiDB's.

- 2019: After we deployed TiDB and resolved several issues, the number of TiZabbix's hosts exceeded 9,000 and the stored data size reached 15 TB.

- 2020: The number of TiZabbix's hosts exceeded 10,000 and the stored data size reached 18 TB. Each day, TiZabbix updated about 1.45 billion monitoring items. Meanwhile, TiZabbix's stability has improved.

## Issues we solved

We solved some major issues before we put forward a relatively stable solution to monitor the current 18 TB of data. We followed one simple principle: try not to change the Zabbix source code, which is complex and difficult. Instead, we read the source code to find an alternative or workaround solution.

In the beginning, we used TiDB 2.1. Due to some version-specific issues, we upgraded to version 3.0. Here are some typical issues we encountered and our solutions.

- TiDB 2.1 only supports optimistic locking. In our case, it causes serious transaction conflicts when a large number of new hosts are automatically registered to the Zabbix server. To avoid the conflicts, we disabled Zabbix's automatic registration feature and used the API to delay registration of the hosts.

- TiDB 2.1 does not support table partitioning, which makes it harder to clean up large tables in Zabbix. So we upgraded to TiDB 3.0, which does support table partitioning. For super large tables like the "history" tables, we partitioned them and used `DROP PARTITION` SQL statements to delete the history data.

- When we used TiDB 2.1, we found that the log type of data collected by Zabbix, which was a long string, might lead to write amplification. Thus, data could not be written to the database that stored a certain volume of data. From the perspective of monitoring, log data have a smaller reference value than numeric data. So we disabled the log data collection, which resumed the write process.

- TiDB does not support foreign key constraints. As our data volume grew, this known MySQL incompatibility issue caused many false alarms generated by Zabbix's automatic discovery feature. This alert malfunction could not be easily solved.

- Another alert-based implementation of Zabbix prevents data from being written to TiDB. Data collected from Zabbix agents are first cached to the Zabbix server. But when evaluating alert conditions, the Zabbix server's cache is locked. Thus, the locked cache data cannot be written to the database.

To solve these two alert-related issues, we removed the alert functionality from TiZabbix. We use TiZabbix to only collect, store, and query data.

But how did we receive alerts instead? Luckily, Zabbix agents support writing data to different servers. We configured Zabbix agents to write data to two servers:

- A Zabbix server with the MySQL backend, which implements alerts. On the server, alerting is normal without the impact of foreign keys. Even better, this server stores a small amount of data, which improves the alert performance.
- A Zabbix server with the TiDB backend, which implements large-scale data storage and queries.

With this method, we successfully separated the alert and data storage functionalities.

## Some tips on using TiZabbix

I'd like to share some tips on using Zabbix, especially with TiDB as the backend.

- **Keep the architectural design as simple as possible.** Zabbix supports proxies on the main server, but I do not recommend using proxies at first because it introduces complexity. In our case, a single Zabbix server is expected to manage at least 20,000 hosts.

- **Use the "Zabbix agent active" mode.** It effectively distributes the loads from the Zabbix server to the agents.

- **Set Zabbix's configuration item `HistoryCache Size` to the maximum value (2G).** If you are using hardware with poorer performance than officially suggested for TiDB, setting a larger cache size can prevent data loss and compensate for the performance instability of the hardware.

- **Do not call the API too frequently.** Permission checks during the API call frequently read and write the same row of data on the same table, which cause serious transaction conflicts and degrade performance. If you must use multiple processes or threads to call the API, I recommend using multiple session IDs, the minimum unit of permission checks, to avoid this situation.

- **Use APIs smartly.** As the data volume increases, some operations on the web interface might fail because large database transactions cause a frontend timeout. In such cases, use APIs to automate your operations.

## Advantages of TiZabbix

After years of application, we conclude that TiZabbix has the following advantages.

- TiZabbix is a centralized monitoring platform, which enables us to collect, store, and query a huge amount of monitoring data. Now, it is much easier for us to access a longer history of data, perform analysis, and locate complicated issues.

- TiDB has great horizontal scalability and usability. By simply adding new nodes to the TiDB cluster, we increase the database's capacity and performance, getting us more data, longer storage, and faster queries.

- Zabbix server has high collection efficiency and effectiveness. We ran each Zabbix server on a virtual machine with up to 64 GB of memory. Our single Zabbix server can collect data from more than 20,000 Linux disk partitions. Zabbix also supports multiple data collection methods and has a web interface that provides rich APIs.

## Further plans

As data continues to increase, bottlenecks will appear. Here's how we plan to address them:

- On the Zabbix server side, memory will become the bottleneck. We can introduce proxies on the single main server to solve the problem, but system complexity will increase.

- On the TiDB side, concurrency conflicts might be the bottleneck. We are not using good hardware for TiDB, so concurrent performance is expected to decrease. This is mainly because some of the auto-generated monitoring items might cause write hotspots. We can optimize the strategy to auto-generate the items by avoiding generating too many items in the same period of time. Also, improving the hardware's performance will help fix the issue.

This is the application of TiDB in our Zabbix monitoring solution at Bank of China. I hope this article provides some useful information. And thanks, PingCAP, for providing the great technology.
