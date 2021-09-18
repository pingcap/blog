---
title: TiDB Internal (II) - Computing
author: ['Li SHEN']
date: 2017-07-11
summary: This is the second one of three blogs to introduce TiDB internal.
tags: ['Architecture', 'TiKV']
aliases: ['/blog/2017/07/11/tidbinternal2/', '/blog/2017-07-11-tidbinternal2']
categories: ['Engineering']
---

From Li SHEN: shenli@pingcap.com

## Table of Content

+ [Mapping the Relational Model to the Key-Value Model](#mapping-the-relational-model-to-the-key-value-model)
+ [Metadata Management](#metadata-management)
+ [Architecture of SQL on Key-Value](#architecture-of-sql-on-key-value)
+ [SQL Computing](#sql-computing)
+ [Distributed SQL Operation](#distributed-sql-operation)
+ [Architecture of the SQL Layer](#architecture-of-the-sql-layer)
+ [Summary](#summary)

My [last blog](https://pingcap.com/blog/2017-07-11-tidbinternal1) introduces the way that TiDB stores data, which is also the basic concepts of TiKV. In this article, I'll elaborate on how TiDB uses the bottom layer Key-Value to store data, maps the relational model to the Key-Value model and performs SQL computing.

### Mapping the Relational Model to the Key-Value Model

Let's simplify the Relational Model to be just about Table and the SQL statements. What we need to think about is how to store Table and run the SQL statements on top of the Key-Value structure.

Assuming we have a Table as follows:

```
CREATE TABLE User {
    ID int,
    Name varchar(20),
    Role varchar(20),
    Age int,
    PRIMARY KEY (ID),
    Key idxAge (age)
};
```

Given the huge differences between the SQL and Key-Value structures, how to map SQL to Key-Value conveniently and efficiently becomes vital. The article will, first of all, go through the requirements and characteristics of data computing, which is essential to determine whether a mapping solution is good or not.

A Table contains three parts of data:

1. Metadata about the table
2. Rows in the Table
3. Index data

Note that metadata will not be discussed in this article.

Data can be stored either in rows or in columns, both have their advantages and disadvantages. The primary goal for TiDB is online transactional processing (OLTP), which supports read, save, update, and delete a row of data quickly. Therefore, row store seems better.

TiDB supports both the Primary Index and Secondary Index. The function of Index is for faster query, higher query performance, and the Constraints. There are two forms of query:

+ Point query, which uses equivalent conditions such as Primary Key or Unique Key for a query, e.g. `select name from user where id=1;`, locating a certain row of data through index.
+ Range query, e.g. `select name from user where age > 30 and age < 35;`, querying the data that the age is between 30 and 35 through `idxAge`.

There are two types of Indexes: Unique Index and Non-unique Index, both of which are supported by TiDB.

After analyzing the characteristics of the data to be stored, let's move on to what we need to do to manipulate the data, including the Insert/Update/Delete/Select statements.

+ The `Insert` statement writes Row into Key-Value and creates the index data.
+ The `Update` statement updates Row and index data if necessary.
+ The `Delete` statement deletes both Row and index.
+ Among the four, the `Select` statement deals with the most complicated situation:
  - Reading a row of data easily and quickly. In this case, each Row needs to have an ID (explicit or implicit).
  - Continuously reading multiple rows of data, such as `Select * from user;`.
  - Reading data through index, leveraging the index either in Point query or Range query.

A globally ordered and distributed Key-Value engine satisfies the above needs. The feature of being globally ordered helps us solve quite a few problems. Take the following as two examples:

+ To get a row of data quickly. Assume that we can create a certain or some Keys, when locating this row, we'd be able to use the Seek method provided by TiKV to quickly locate this row of data.
+ To scan the whole table. If the table can be mapped to the Range of Key, then all data can be got by scanning from StartKey to EndKey. The way to manipulate Index data is similar.

Now let's see how this works in TiDB.

TiDB allocates a `TableID` to each table, an `IndexID` to each index, and a `RowID` to each row. If the table has an integer Primary Key, then the value will be used as the `RowID`. The `TableID` is unique in the whole cluster while the `IndexID/RowID` unique in the table. All of these ID are int64.

Each row of data is encoded into a Key-Value pair according to the following rule:

```
Key: tablePrefix{tableID}_recordPrefixSep{rowID}
Value: [col1, col2, col3, col4]
```

The `tablePrefix`/`recordPrefixSep` of the Key are specific string constants and used to differentiate other data in the Key-Value space.

Index data is encoded into a Key-Value pair according to the following rule:

```
Key: tablePrefix{tableID}_indexPrefixSep{indexID}_indexedColumnsValue
Value: rowID
```

The above encoding rule applies to Unique Index while it cannot create a unique Key for Non-unique Index. The reason is that the `tablePrefix{tableID}_indexPrefixSep{indexID}` of an Index is the same. It's possible that the `ColumnsValue of` multiple rows is also the same. Therefore, we've made some changes to encode the Non-unique Index:

```
Key: tablePrefix{tableID}_indexPrefixSep{indexID}_indexedColumnsValue_rowID
Value: null
```

In this way, the unique Key of each row of data can be created.

In the above rules, all `xxPrefix` of the Keys are string constants with the function of differentiating the namespace to avoid the conflict between different types of data.

```
var(
    tablePrefix     = []byte{'t'}
    recordPrefixSep = []byte("_r")
    indexPrefixSep  = []byte("_i")
)
```

Note that the Key encoding solution of either Row or Index has the same prefix. Specifically speaking, all Rows in a Table has the same prefix, so does data of Index. These data with the same prefix is arranged together in the Key space of TiKV. In other words, we just need to carefully design the encoding solution of the suffix, ensuing the comparison relation remains unchanged, then Row or Index data can be stored in TiKV orderly. The solution of maintaining the relation unchanged before and after encoding is called `Memcomparable`. As for any type of value, the comparison result of two objects before encoding is consistent with that of the byte array after encoding (Note: both Key and Value of TiKV are the primitive byte array). For more detailed information, please refer to the [codec package](https://github.com/pingcap/tidb/tree/master/util/codec) of TiDB. When adopting this encoding solution, all Row data of a table will be arranged in the Key space of TiKV according to the RowID order. So will the data of a certain Index, according to the ColumnValue order of Index.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('TiDB Internal (II) - Computing', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Internal (II) - Computing', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

Now we take the previous requirements and TiDB's mapping solution into consideration and verify the feasibility of the solution.

1. Firstly, we transform Row and Index data into Key-Value data through the mapping solution and make sure that each row and each piece of index data has a unique Key.
2. Secondly, we can easily create the corresponding Key of some row or some piece of index by using this mapping solution as it is good for both Point query and Range query.
3. Lastly, when ensuring some Constraints in the table, we can create and check the existence of a certain Key to determine whether the corresponding Constraint has been satisfied.

Up to now, we've already covered how to map Table onto Key-Value. Here is one more case with the same table structure. Assume that the table has three rows of data:

```
1, "TiDB", "SQL Layer", 10
2, "TiKV", "KV Engine", 20
3, "PD", "Manager", 30
```

First, each row of data will be mapped as a Key-Value pair. As this table has an Int Primary Key, the value of RowID is the value of this Primary Key. Assume that the TableID of this table is 10, its Row data is:

```
t10_r1 --> ["TiDB", "SQL Layer", 10]
t10_r2 --> ["TiKV", "KV Engine", 20]
t10_r3 --> ["PD", "Manager", 30]
```

In addition to Primary Key, this table also has an Index. Assume that the ID of Index is 1, its data is:

```
t10_i1_10_1 --> null
t10_i1_20_2 --> null
t10_i1_30_3 --> null
```

The previous encoding rules help you to understand the above example. We hope that you can realize the reason why we chose this mapping solution and the purpose of doing so.

### Metadata Management

After explaining how data and index of a table is mapped to Key-Value, this section introduces the storage of metadata.

Both Database and Table have metadata, which refers to its definition and various attributes. All of this information needs to be persisted and stored in TiKV. Each Database/Table gets a unique ID and this ID serves as the unique identification. When encoding into Key-Value, this ID will be encoded in Key, with a prefix of m_. In this way, a Key is created and the corresponding Value stores the serialized metadata.

Apart from this, a specialized Key-Value stores the version of the current Schema information. TiDB uses the Online Schema change algorithm of Google F1. A background thread constantly checks whether the Schema version stored on TiKV has changed. If so, it manages to get the updates within a certain period of time. For more detailed information, please refer to [The Implementation of Asynchronous Schema Change of TiDB (In Chinese)](https://github.com/ngaut/builddatabase/blob/master/f1/schema-change-implement.md).

### Architecture of SQL on Key-Value

The following diagram shows the entire architecture of TiDB:

![TiDB architecture](media/tidbarchitecture.png)

The main function of the TiKV Cluster is to serve as the Key-Value engine to store data, which is thoroughly introduced in the last column. This article focuses on the SQL layer, i.e. the TiDB Servers. Nodes of this layer are stateless, storing no data, and each of them is completely equivalent. TiDB Server is responsible for handling user requests and executing SQL operation logic.

### SQL Computing

The mapping solution from SQL to Key-Value shows how to store the relational data. Then we need to understand how to use these data to meet the query requests, which, in other words, the process of how a query statement accesses the data stored in the bottom layer.

The easiest way is to map the SQL query to Key-Value query through the mapping solution that I introduced in the last section, and then get the corresponding data through the Key-Value interface before executing any kind of operations.

As for the statement `Select count(*) from user where name="TiDB";`, we need to read all the data in the table and then check if the Name field is TiDB. If so, return this row. The operation is transferred to the following Key-Value operation process:

+ Create Key Range: As all RowIDs in a table are in the [0, MaxInt64) range, we use 0 and MaxInt64 and Row's Key encoding rule to create a left-close-right-open interval, [StartKey, EndKey).
+ Scan Key Range: Read data in TiKV according to the Key Range previously created.
+ Filter the data: Evaluate the name="TiDB" expression when reading each row of data. If the result is true, return to this row. If not, skip this row.
+ Evaluate Count: For each row that meets the requirement, add up to the Count value.

See the following diagram for the process:

![SQL computing](media/queryprocess.png)

This solution works though it still has the following drawbacks:

1. When scanning data, each row needs to be read from TiKV through Key-Value operation. Therefore, there is at least one RPC overhead. The overhead becomes huge if there is a large amount of data to be scanned.
2. It is not applicable to all rows. Data that doesn't meet the conditions doesn't need to be read.
3. The value of the rows that meet the conditions is meaningless. What we need here is just the number of rows.

### Distributed SQL Operation

It is simple to avoid the above drawbacks.

1. Firstly, we need to operate close to the storage nodes to stop massive RPC callings.
2. Then we need to push down Filter to the storage nodes as well. In this case, only valid rows will be returned and meaningless network transmission will be avoided.
3. Lastly, we can push down the Aggregate function and GroupBy for pre-aggregation. Each node only needs to return one Count value and then tidb-server Sums all the values.

The following sketch shows how data returns layer by layer:

![How data returns layer by layer](media/dist-query.png)

You can refer to [MPP and SMP in TiDB (in Chinese)](https://mp.weixin.qq.com/s?__biz=MzI3NDIxNTQyOQ==&mid=2247484187&idx=1&sn=90a7ce3e6db7946ef0b7609a64e3b423&chksm=eb162471dc61ad679fc359100e2f3a15d64dd458446241bff2169403642e60a95731c6716841&scene=4) to know how TiDB makes the SQL statement run faster.

### Architecture of the SQL Layer

The previous sections introduce some functions of the SQL layer and I hope you have a basic idea about how to process the SQL statement. Actually, TiDB's SQL Layer is much complicated and has lots of modules and layers. The following diagram lists all important modules and the call relation:

![Architecture of the SQL Layer](media/sqlarchitecture.png)

The SQL requests will be sent directly or via a Load Balancer to tidb-server, which then parses the MySQL Protocol Packet for the request content. After that, it performs syntax parsing, makes and optimizes the query plan and executes the plan to access and process data. As all data is stored in the TiKV cluster. Tidb-server needs to interact with tikv-server for accessing data during the process. Finally, tidb-server needs to return the query result to users.

### Summary

Up till now, we've known how data is stored and used for operation from the perspective of SQL. Information about the SQL layer, such as the principle of optimization and the detail of the distributed execution framework will be introduced in the future.

In the next article, we will dwell on information about PD, especially the cluster management and schedule. This is an interesting part as you will see things that are invisible when using TiDB but important to the whole cluster.
