---
title: TiDB Best Practices
author: ['Li Shen']
date: 2017-07-24
summary: This article summarizes some best practices in using TiDB, mainly including SQL usage, OLAP/OLTP optimization techniques and especially TiDB's exclusive optimization switches.
tags: ['Best practice']
aliases: ['/blog/2017/07/24/tidbbestpractice/', '/blog/2017-07-24-tidbbestpractice']
categories: ['Product']
---

From Li SHEN: shenli@pingcap.com

See the following blogs ([Data Storage](https://pingcap.com/blog/2017-07-11-tidbinternal1), [Computing](https://pingcap.com/blog/2017-07-11-tidbinternal2), [Scheduling](https://pingcap.com/blog/2017-07-20-tidbinternal3)) for TiDB's principles.

## Table of Content

+ [Preface](#preface)
+ [Basic Concepts](#basic-concepts)
  - [Raft](#raft)
  - [Distributed Transactions](#distributed-transactions)
  - [Data Sharding](#data-sharding)
  - [Load Balancing](#load-balancing)
  - [SQL on KV](#sql-on-key-value)
  - [Secondary Indexes](#secondary-indexes)
+ [Scenarios and Practices](#scenarios-and-practices)
  - [Deployment](#deployment)
  - [Importing Data](#importing-data)
  - [Write](#write)
  - [Query](#query)
  - [Monitoring and Log](#monitoring-and-log)
  - [Documentation](#documentation)
  - [Best Scenarios for TiDB](#best-scenarios-for-tidb)

## Preface

Database is a generic infrastructure system. It is important to, for one thing, consider various user scenarios during the development process, and for the other, modify the data parameters or the way to use according to actual situations in specific business scenarios.

TiDB is a distributed database compatible with MySQL protocol and syntax. But with the internal implementation and supporting of distributed storage and transactions, the way of using TiDB is different from MySQL.

## Basic Concepts

The best practices are closely related to its implementation principles. This article briefly introduces Raft, distributed transactions, data sharding, load balancing, the mapping solution from SQL to KV, implementation method of secondary indexing and distributed execution engine.

### Raft

Raft is a consensus algorithm and ensures data replication with strong consistency. At the bottom layer, TiDB uses Raft to synchronize data. TiDB writes data to the majority of the replicas before returning the result of success. In this way, the system will definitely have the latest data even though a few replicas might get lost. For example, if there are three replicas, the system will not return the result of success until data has been written to two replicas. Whenever a replica is lost, at least one of the remaining two replicas have the latest data.

To store three replicas, compared with the synchronization of primary-secondary, Raft is more efficient. The write latency of Raft depends on the two fastest replicas, instead of the slowest. Therefore, the implementation of geo-distributed and multiple active datacenters becomes possible by using the Raft synchronization. In the typical scenario of three datacenters distributing in two sites, to guarantee the data consistency, we just need to successfully write data into the local datacenter and the closer one, instead of writing to all three data-centers. However, this does not mean that cross-datacenter deployment can be implemented in any scenario. When the amount of data to be written is large, the bandwidth and latency between data-centers become the key factors. If the write speed exceeds the bandwidth or the latency is too high, the Raft synchronization mechanism still cannot work well.

### Distributed Transactions

TiDB provides complete distributed transactions and the model has some optimizations on the basis of [Google Percolator](http://research.google.com/pubs/pub36726.html). Here, I would just talk about two things:

+ Optimistic Lock

    TiDB's transaction model uses the optimistic lock and will not detect conflicts until the commit phase. If there are conflicts, retry the transaction. But this model is inefficient if the conflict is severe because operations before retry are invalid and need to repeat. Assume that the database is used as a counter. High access concurrency might lead to severe conflicts, resulting in multiple retries or even timeouts. Therefore, in the scenario of severe conflicts, it is recommended to solve problems at the system architecture level, such as placing counter in Redis. Nonetheless, the optimistic lock model is efficient if the access conflict is not very severe.

+ Transaction Size Limits

    As distributed transactions need to conduct two-phase commit and the bottom layer performs Raft replication, if a transaction is very large, the commit process would be quite slow and the following Raft replication flow is thus struck. To avoid this problem, we limit the transaction size:

    - A transaction is limited to 5000 SQL statements (by default)
    - Each Key-Value entry is no more than 6MB
    - The total number of Key-Value entry is no more than 300,000 rows
    - The total size of Key-Value entry is no more than 100MB

    There are [similar limits](https://cloud.google.com/spanner/docs/limits) on Google Cloud Spanner.

### Data Sharding

TiKV automatically shards bottom-layered data according to the Range of Key. Each Region is a range of Key, from a left-close-right-open interval, [StartKey, EndKey). When the amount of Key-Value in Region exceeds a certain value, it will automatically split.

### Load Balancing

PD will automatically balance the load of the cluster according to the state of the entire TiKV cluster. The unit of scheduling is Region and the logic is the strategy configured by PD.

### SQL on Key-Value

TiDB automatically maps the SQL structure into Key-Value structure. For more information, please refer to [Computing](https://pingcap.com/blog/2017-07-11-tidbinternal2). Simply put, TiDB has done two things:

+ A row of data is mapped to a Key-Value pair. Key is prefixed with TableID and suffixed with row ID.

+ An index is mapped as a Key-Value pair. Key is prefixed with TableID+IndexID and suffixed with the index value.

As you can see, data and index in the same table have the same prefix, so that these Key-Values are at adjacent positions in the Key space of TiKV. Therefore, when the amount of data to be written is large and all is written to one table, the write hotspot is thus created. The situation gets worse when some index values of the continuous written data is also continuous (e.g. fields that increase with time, like update time), which will create a few write hotspots and become the bottleneck of the entire system. Likewise, if all data is read from a focused small range (e.g. the continuous tens or hundreds of thousands of rows of data), access hotspot of data will probably occur.

### Secondary Indexes

TiDB supports the complete secondary indexes which are also global indexes. Many queries can be optimized by index. Lots of MySQL experience is also applicable to TiDB, it is noted that TiDB has its unique features. Below are a few notes when using secondary indexes in TiDB.

+ The more secondary indexes, the better?

    Secondary indexes can speed up query, but adding an index has side effects. In the last section, we've introduced the storage model of index. For each additional index, there will be one more Key-Value when inserting a piece of data. Therefore, the more indexes, the slower the writing speed and the more space it takes up. In addition, too many indexes will influence the runtime of the optimizer. And inappropriate index will mislead the optimizer. Thus, the more secondary indexes is not necessarily the better.

+ Which columns should create indexes?

    As mentioned before, index is important but the number of indexes should be proper. We need to create appropriate indexes according to the characteristics of business. In principle, we need to create indexes for the columns needed in the query, the purpose of which is to improve the performance. Below are the conditions that need to create indexes:

    - For columns with a high degree of differentiation, the number of filtered rows is remarkably reduced though index.
    - If there are multiple query criteria, you can choose composite indexes. Note to put the columns with equivalent condition before composite index.

    For example, for a commonly-used query is `select * from t where c1 = 10 and c2 = 100 and c3 > 10`, you can create a composite index `Index cidx (c1, c2, c3)`. In this way, you can use the query criterion to create an index prefix and then Scan.

- The difference between query through indexes and directly scan Table

    TiDB has implemented global indexes, so indexes and data of the Table are not necessarily on data sharding. When querying through indexes, it should firstly scan indexes to get the corresponding row ID and then use the row ID to get the data. Thus, this method involves two network requests and has a certain performance overhead.

    If the query involves lots of rows, scanning index proceeds concurrently. When the first batch of results is returned, getting the data of Table can then proceed. Therefore, this is a parallel + Pipeline model. Though the two accesses create overhead, the latency is not high.

    The following two conditions don't have the problem of two accesses:

    + Columns of the index have already met the query requirement. Assume that the `c` Column on the `t` Table has an index and the query is: `select c from t where c > 10;`. At this time, all needed data can be obtained if accessing the index. We call this condition Covering Index. But if you focus more on the query performance, you can put a portion of columns that don't need to be filtered but need to be returned in the query result into index, creating composite index. Take `select c1, c2 from t where c1 > 10;` as an example. You can optimize this query by creating composite index `Index c12 (c1, c2)`.

    + The Primary Key of table is integer. In this case, TiDB will use the value of Primary Key as row ID. Thus, if the query criterion is on PK, you can directly construct the range of the row ID, scan Table data, and get the result.

+ Query concurrency

    As data is distributed across many Regions, TiDB makes query concurrently. But the concurrency by default is not high in case it consumes lots of system resources. Besides, as for the OLTP query, it doesn't involve a large amount of data and the low concurrency is enough. But for the OLAP Query, the concurrency is high and TiDB modifies the query concurrency through System Variable.

    - [tidb\_distsql\_scan\_concurrency](https://pingcap.com/docs/v3.0/reference/configuration/tidb-server/tidb-specific-variables/#tidb-distsql-scan-concurrency)

        The concurrency of scanning data, including scanning the Table and index data.

    - [tidb\_index\_lookup\_size](https://pingcap.com/docs/v3.0/reference/configuration/tidb-server/tidb-specific-variables/#tidb-index-lookup-size)

        If it needs to access the index to get row IDs before accessing Table data, it uses a batch of row IDs as a single request to access Table data. This parameter can set the size of Batch. The larger Batch increases latency while the smaller one may lead to more queries. The proper size of this parameter is related to the amount of data that the query involves. Generally, no modification is required.

    - [tidb\_index\_lookup\_concurrency](https://pingcap.com/docs/v3.0/reference/configuration/tidb-server/tidb-specific-variables/#tidb-index-lookup-concurrency)

        If it needs to access the index to get row IDs before accessing Table data, the concurrency of getting data through row IDs every time is modified through this parameter.

+ Ensure the order of results through index

    Index cannot only be used to filter data, but also to sort data. Firstly, get row IDs according to the index order. Then return the row content according to the return order of row IDs. In this way, the return results are ordered according to the index column. I've mentioned that the model of scanning index and getting Row is parallel + Pipeline. If Row is returned according to the index order, a high concurrency between two queries will not reduce latency. Thus, the concurrency is low by default, but it can be modified through the [tidb\_index\_serial\_scan\_concurrency](https://pingcap.com/docs/v3.0/reference/configuration/tidb-server/tidb-specific-variables/#tidb-index-serial-scan-concurrency) variable.

+ Reverse index scan

    As in MySQL 5.7, all indexes in TiDB are in ascending order. TiDB supports the ability to read an ascending index in reverse order, at a performance overhead of about 23%. Earlier versions of TiDB had a higher performance penalty, and thus reverse index scans were not recommended.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('TiDB Best Practices', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Best Practices', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## Scenarios and Practices

In the last section, we discussed some basic implementation mechanisms of TiDB and their influence on usage. Let's start from specific usage scenarios and operation practices. We'll go through from deployment to business supporting.

### Deployment

Please read [Software and Hardware Requirements](https://pingcap.com/docs/op-guide/recommendation/) before deployment.

It is recommended to deploy the TiDB cluster through [TiDB Ansible](https://pingcap.com/docs/op-guide/ansible-deployment/). This tool can deploy, stop, destroy, and update the whole cluster, which is quite convenient.

### Importing Data

If there is a Unique Key and if the business end can ensure that there is no conflict in data, you can turn on this switch in Session:

`SET @@session.tidb_skip_constraint_check=1;`

In order to improve the write performance, you can tune TiKV's parameters as stated in [this document](https://pingcap.com/docs/op-guide/tune-tikv/).

Please pay extra attention to this parameter:

```
[raftstore]
# The default value is true, which means data is forced to be flushed to the disk. If the business scenario is non-financial security, it is recommended to set as false,
# for getting higher performance.

sync-log = true
```

### Write

As mentioned before, TiDB limits the size of a single transaction in the Key-Value layer. As for the SQL layer, a row of data is mapped to a Key-Value entry. For each additional index, there will be one more Key-Value entries. So the limits mirrored in the SQL layer for a single transaction are:

+ A transaction is limited to 5000 SQL statements (by default)
+ Each Key-Value entry is no more than 6MB
+ The total number of rows * (1 + the number of indexes) is less than 300,000
+ The total data of a single commit is less than 100MB

> **Note:** Either the size limit or the number of rows limit needs to consider the overhead of TiDB encoding and the extra transaction Key. **It is recommended that the number of rows of each transaction is less than 200 and the data size of a single row is less than 100KB**; otherwise, the performance is bad.

When deleting a large amount of data, it is recommended to use `Delete * from t where xx limit 5000;`. It deletes through the loop and use `Affected Rows == 0` as a condition to end the loop, so as not to exceed the limit of transaction size. If the amount of data that needs to be deleted at a time is large, this loop method will get slower and slower because each deletion traverses backward. After deleting the previous data, lots of deleted flags will remain in a short period (then all will be Garbage Collected) and influence the following `Delete` statement. If possible, it is recommended to refine the `Where` condition. Assume that you need to delete all data on 2017-05-26, you can:

```
for i from 0 to 23:
    while affected_rows > 0:
        delete * from t where insert_time >= i:00:00 and insert_time < (i+1):00:00 limit 5000;
        affected_rows = select affected_rows()
```

This pseudocode means to split huge chunks of data into small ones and then delete, so that the following `Delete` statement will not be influenced.

### Query

For query requirements and specific statements, please refer to [this statement](https://pingcap.com/docs/v3.0/reference/sql/statements/add-column/).

You can control the concurrency of SQL execution through the `SET` statement and the selection of the `Join` operator through `Hint`.

In addition, you can also use MySQL's standard index selection, the `Hint` syntax: control the optimizer to select index through `Use Index/Ignore Index hint`.

If the business scenario needs both OLTP and OLAP, you can send the TP request and AP request to different tidb-servers, diminishing the impact of AP business on TP. It is recommended to use high-end machines (e.g. more processor cores, larger memory, etc.) for the tidb-server that carries AP business.

### Monitoring and Log

TiDB uses [Grafana+Prometheus to monitor the system state](https://pingcap.com/docs/op-guide/monitor-overview/). The monitoring system is automatically deployed and configured if using TiDB Ansible.

There are lots of items in the monitoring system, the majority of which are for TiDB developers. There is no need to understand these items but for an in-depth knowledge of the source code. We've picked out some items that are related to business or to the state of system key components in a separate panel for users.

In addition to monitoring, you can also view the system logs. The three components of TiDB, `tidb-server`, `tikv-server` and `pd-server`, each has a `--log-file` parameter. If this parameter has been configured when initiating, logs will be stored in the file configured by the parameter and Log files are automatically archived on a daily basis. If the `--log-file` parameter has not been configured, log will be output to stderr.

### Documentation

TiDB has a large number of official documents either in [Chinese](https://pingcap.com/docs-cn/) or [English](https://pingcap.com/docs/). You can also search the issue list for a solution.

If you have met an issue, you can start from the [FAQ](https://pingcap.com/docs/FAQ/) and [Troubleshooting](https://pingcap.com/docs/trouble-shooting/) sections. If the issue is not documented, please [file an issue](https://github.com/pingcap/tidb/issues/new).

For more information, see [our website](https://pingcap.com/) and our [Technical Blog](https://pingcap.com/blog/).

### Best Scenarios for TiDB

Simply put, TiDB can be used in the following scenarios:

+ The amount of data is too large for a standalone database
+ Don't want to use the sharding solutions
+ The access mode has no obvious hotspot
+ Transactions, strong consistency, and disaster recovery
