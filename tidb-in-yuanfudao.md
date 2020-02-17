---
title: How TiDB tackles fast data growth and complex queries for yuanfudao.com
date: 2017-08-08
summary: This document is a case study that details the reasons why yuanfudao.com chose TiDB as its backend database solution to tackle their fast data growth and complex queries.
tags: ['TiDB', 'Success Story']
url: /success-stories/tidb-in-yuanfudao/
aliases: ['/blog/2017/08/08/tidbforyuanfudao/', '/blog/2017-08-08-tidbforyuanfudao/']
customer: Yuanfudao.com
---

Yuanfudao.com is an online tutoring service targeting the K-12 educational segment in China with the largest number of elementary and secondary school student users. It owns three applications, Yuantiku, the online question bank, Xiaoyuansouti, the application for question search by taking pictures, and yuanfudao.com, an online tutoring service.

So far, the Yuanfudao APPs have more than 1.16 million paying users and provide live tutoring courses of English and Math Olympiad to the elementary users, as well as all the subjects for secondary school students. With yuanfudao.com, students from every corner of China can enjoy high-quality courses from top teachers at home.

The enormous amount of data in the question bank, the audio and video learning materials, and all the user data and log call for a high level of storage and processing capacity of yuanfudao.com’s backend system.

yuanfudao.com’s business scenario requires the following features from its backend system:

+ The storage system should be able to scale out flexibly to serve the large data volume and rapid data growth.
+ Be able to meet the complex queries and BI related requirements, and can perform real-time analysis based on indexes like cities and channels.
+ The system must be highly available, can automatically failover and is easy to maintain.

In the early stage of solution evaluation and selection, yuanfudao.com considered the standalone MySQL solution but then gave up the idea because of the following reasons:

+ They perceived that with the fast development of their business, the data storage capacity and concurrency stress would soon hit the processing bottleneck of a standalone database. 

+ If adding a sharding solution to MySQL, the sharding key must be specified, which would not support cross-shard distributed transactions. Not to mention that the proxy solution is intrusive to the business tier and developers must know clearly the partitioning rules, which makes it unable to achieve transparency.

+ Sharding is difficult to implement cross-shard aggregate queries, such as correlated query, subquery and group-by aggregation of the whole table. In these business scenarios, the query complexity is passed on to the application developers. Even though some middleware can implement simple `join` support, there is still no way to guarantee the correctness of these queries. 

+ The broadcasting solution cannot scale and the overhead would be huge when the cluster becomes larger. 

+ For a business with a relatively large data volume, the problem of locking table for DDL on traditional RDBMS would be serious with a quite long lock time. If using some third-party tools like `gh-ost` to implement non-blocking DDL, the extra space overhead would be large and manual intervention would still be needed to guarantee the data consistency. What might make things worse is that the system might jitter during the switch process. It is safe to say that the maintenance complexity will increase exponentially with more and more machines while the scaling complexity is directly passed on to DBA. 

In the end, the backend developers of yuanfudao.com decided to use a distributed storage solution and after researching quite a few community solutions, they found TiDB, a distributed relational database.

TiDB is an open source distributed Hybrid Transactional/Analytical Processing (HTAP) database. It features horizontal scalability, strong consistency, and high availability. Users can regard TiDB as a standalone database with an infinite storage capacity. TiDB is nonintrusive to business and can elegantly replace the traditional sharding solutions such as database middleware and database sharding while at the same time maintaining the ACID properties of transactions. Instead of paying too much attention to the details of database scaling, developers are freed to focus on business development, which greatly improves the R&D productivity. 

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('How TiDB tackles fast data growth and complex queries for yuanfudao.com', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('How TiDB tackles fast data growth and complex queries for yuanfudao.com', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

As the complicated distributed transactions and data replication are supported by the underlying storage engine, developers just need to concentrate on the business logic and creating values.

The following table outlines the difference between MySQL sharding solutions and TiDB:

<table>
  <tr>
    <td></td>
    <td>MySQL Sharding</td>
    <td>TiDB</td>
  </tr>
  <tr>
    <td>ACID Transaction</td>
    <td>No</td>
    <td>Yes</td>
  </tr>
  <tr>
    <td>Online Scalability</td>
    <td>No</td>
    <td>Yes</td>
  </tr>
  <tr>
    <td>Complex Query</td>
    <td>No</td>
    <td>Yes</td>
  </tr>
  <tr>
    <td>Failover</td>
    <td>Manual</td>
    <td>Auto</td>
  </tr>
  <tr>
    <td>MySQL Compatibility</td>
    <td>Low</td>
    <td>High</td>
  </tr>
</table>


(Comparison between TiDB and traditional MySQL sharding solutions)

TiDB cluster consists of three components: TiDB Server, TiKV Server, and PD Server.

![TiDB architecture](media/tidb-architecture.png)
<div class="caption-center"> The Overall Architecture of TiDB </div>

TiDB Server is responsible for processing SQL request. When the business grows, adding more TiDB Server nodes can improve the entire processing capacity and offer a higher throughput. 

TiKV is responsible for storing data. When the data volume grows, deploying more TiKV Server nodes can directly increase the data storage capacity. 

PD schedules among the TiKV nodes in Regions and migrates a portion of data to the newly-added node. Therefore, in the early stage, users can deploy a few service instances and add more TiKV or TiDB instances if needed, depending on the data volume.

For the deployment in a production environment, yuanfudao.com chose an architecture of 2 TiDB + 3 TiKV + 3 PD for the condition of 5 million rows of data volume per day, hundreds of millions of records in the routing database and the peak QPS is about 1000. It is noted that the architecture scales as the business data volume grows.

The client end of yuanfudao.com collects data about the audio and video quality of live streaming, such as packet loss, latency, and quality grading. Then the client end sends these data to the server and the latter stores all data in TiDB.

Guo Changzhen, the R&D Vice President of yuanfudao.com, expresses his appreciation towards TiDB: "TiDB is an ambitious project and solves the scaling problem of MySQL from scratch. It also has the OLAP capacity in many scenarios, saving the cost of building and learning a data warehouse, which is quite popular in the business tier." As a next step, yuanfudao.com plans to synchronize through Syncer, then merge and perform statistical analysis to other sharding businesses.

There are many other similar use cases like yuanfudao.com. With the rapid development of the Internet, plenty of businesses are booming and TiDB can meet their needs with its flexible scaling capacity.
