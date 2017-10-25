---
date: 2017-10-17T00:00:00Z
excerpt: TiDB is compatible with MySQL, strong consistent and highly available.
title: PingCAP Launches TiDB 1.0
url: /2017/10/17/announcement/
---

## PingCAP Launches TiDB 1.0, A Scalable Hybrid Database Solution

October 16, 2017 - PingCAP Inc., a cutting-edge distributed database technology company, officially announces the release of [TiDB](https://github.com/pingcap/tidb) 1.0. TiDB is an open source distributed Hybrid Transactional/Analytical Processing (HTAP) database that empowers businesses to meet both workloads with a single database. 

In the current database landscape, infrastructure engineers often have to use one database for online transactional processing (OLTP) and another for online analytical processing (OLAP). TiDB aims to break down this separation by building a HTAP database that enables real-time business analysis based on live transactional data. With TiDB, engineers can now spend less time managing multiple database solutions, and more time delivering business value for their companies. One of TiDB’s many users, a financial securities firm, is leveraging this technology to power its application for wealth management and user personas. With TiDB, this firm can easily process web-scale volumes of billing records and conduct mission-critical time sensitive data analysis like never before. 

*"Two and a half years ago, Edward, Dylan and I started this journey to build a new database for an old problem that has long plagued the infrastructure software industry. Today, we are proud to announce that this database, TiDB, is production ready,"* said Max Liu, co-founder and CEO of PingCAP. *“Abraham Lincoln once said, ‘the best way to predict the future is to create it.’ The future we predicted 771 days ago we now have created, because of the hard work and dedication of not just every member of our team, but also every contributor, user, and partner in our open source community. Today, we celebrate and pay gratitude to the power of the open source spirit. Tomorrow, we will continue to create the future we believe in.”*

TiDB has already been deployed in production in more than 30 companies in the APAC region, including fast-growing Internet companies like [Mobike](https://en.wikipedia.org/wiki/Mobike), [Gaea](http://www.gaea.com/en/), and [YOUZU](http://www.yoozoo.com/aboutEn). The use cases span multiple industries from online marketplace and gaming, to fintech, media, and travel. 

### TiDB features

**Horizontal Scalability**

TiDB grows as your business grows. You can increase the capacity for storage and computation simply by adding more machines.

**Compatible with MySQL Protocol**

Use TiDB as MySQL. You can replace MySQL with TiDB to power your application without changing a single line of code in most cases and with nearly no migration cost.

**Automatic Failover and High Availability**

Your data and applications are always-on. TiDB automatically handles malfunctions and protects your applications from machine failures or even downtime of an entire data-center.

**Consistent Distributed Transactions**

TiDB is analogous to a single-machine RDBMS. You can start a transaction that crosses multiple machines without worrying about consistency. TiDB makes your application code simple and robust.

**Online DDL**

Evolve TiDB schemas as your requirement changes. You can add new columns and indexes without stopping or affecting your ongoing operations.

[Try TiDB Now!](https://pingcap.com/doc-QUICKSTART)

### Use cases

[How TiDB tackles fast data growth and complex queries for yuanfudao.com](https://pingcap.github.io/blog/2017/08/08/tidbforyuanfudao/)

[Migration from MySQL to TiDB to handle tens of millions of rows of data per day](https://pingcap.github.io/blog/2017/05/22/Comparison-between-MySQL-and-TiDB-with-tens-of-millions-of-data-per-day/)

### For more information:

TiDB internal: 
- [Data Storage](https://pingcap.github.io/blog/2017/07/11/tidbinternal1/)
- [Computing](https://pingcap.github.io/blog/2017/07/11/tidbinternal2/)
- [Scheduling](https://pingcap.github.io/blog/2017/07/20/tidbinternal3/)

[Release Notes](https://pingcap.com/doc-rn)

[Best Practice](https://pingcap.github.io/blog/2017/07/24/tidbbestpractice/)

[Documents](https://pingcap.com/docs)

[Weekly Update](http://weekly.pingcap.com/)
