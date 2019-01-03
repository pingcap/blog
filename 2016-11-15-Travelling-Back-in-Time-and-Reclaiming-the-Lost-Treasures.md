---
title: Travelling Back in Time and Reclaiming the Lost Treasures
author: ['Ewan Chou']
date: 2016-11-15
summary: This document introduces the History Read feature in TiDB.
tags: ['TiDB', 'Engineering', 'Golang']
aliases: ['/blog/2016/11/15/Travelling-Back-in-Time-and-Reclaiming-the-Lost-Treasures/', '/blog/2016/11/15/travelling-back-in-time-and-reclaiming-the-lost-treasures/']
categories: ['Engineering']
---

## About the History Read feature in TiDB

Data is the core and is a matter of life and death for every business.  So ensuring the data safety is the top priority of every database. From a macro point of view, the safety of data is not only about whether a database is stable enough that no data is lost, but also about whether a sufficient and convenient solution is in place when data is lost because of the business or human errors, for example, to solve the anti-cheat problem in the game industry or to meet the audit requirements in the financing business. If a proper mechanism is enabled in the database level, it will reduce the workload and the complexity of business development significantly.

The traditional solution is to backup data in full volume periodically, in days or daily. These backups are to restore the data in case of accidents. But to restore data using backups is very costly because all the data after the backup time will be lost, which might be the last thing you want. In addition, the storage and computing overhead for full backups is no small cost for every company.

But this kind of situation cannot be avoided completely. To err is human. For every fast iterative business, it is impossible for the code of the application to be fully tested. Fault data might be written because of the bug in the application logic or the activity of malicious users. When the issue is spotted, you can roll back the application to the earlier version immediately, but the fault data remains in the database.

What can do you when things like this happen? The only thing you know is that the data is faulted. But what is the correct data? You have no idea. It would be great if you could go back in time and find the lost data.

The History Read feature of [TiDB](https://github.com/pingcap/tidb) supports reading the history versions and is specially tailored for this requirement and scenario. All the data before the faulted version can be accessed and therefore the damage can be minimized.

### How to use the History Read feature?

It is very easy to use this feature. You can simply use the following `Set` statement:

```
set @@tidb_snapshot = "2016-10-10 09:30:11.123"
```

The name of the session variable is `tidb_snapshot` which is defined in TiDB. The value is a time string with precision of milliseconds. When this statement is executed, the data read by all the read requests issued from this client is at the set time and the write operation is not allowed because the history cannot be changed. If you want to exit the History Read mode and read the latest data, you can just execute the following `Set` statement:

```
set @@tidb_snapshot = ""
```

which sets the `tidb_snapshot ` variable to be an empty string.

It doesn’t matter even if there are Schema changes after the set time in history because TiDB will use the Schema of the set time in history for the SQL request.

### Comparing the History Read feature in TiDB with the similar features in other databases

There is no such feature in MySQL. In other databases such as Oracle and PostgreSQL, this feature is called Temporal Table, which is a SQL standard. To use this feature, you need to use the special table creating grammar for the Temporal Table which has two more fields than the original table. The two extra fields are to store the valid time and are maintained by the system. When the original table is updated, the system inserts the data of the old version into the Temporal Table. When you need to retrieve the history data, you can use a special grammar to set the time in history and get the result.

Compared with the similar features of other databases, the History Read feature in TiDB has the following advantages:
- It is supported by default in the system. If it is not supported by default, usually we won’t create a Temporal Table on purpose. But when we actually need it, it might not there.
- It is very easy to use. No extra table or special grammar is needed.
- It provides a global snapshot instead of a view from individual table.
- Even if operations like Drop Table and Drop Database are executed, old data can still be retrieved in TiDB.

### The implementation of the History Read feature in TiDB

#### Multi-version Concurrency Control (MVCC)

**Note:** The implementation in this document is a simplified version and does not involve the distributed transactions. The implementation in TiDB is more complex than this. We will provide the detailed implementation of the transaction model later. Stay tuned!

TiDB is on top of [TiKV](https://github.com/pingcap/tikv). The storage engine at the bottom level for TiKV is RocksDB where data is stored in Key-Value pairs. A row in a table in the SQL layer needs to be encoded twice to get the final Key in RocksDB:

-  The Key after the first-pass encoding includes table ID and record ID. Using this Key can locate this specific row.

- Based on the Key from the first encoding, the final Key after the second-pass encoding includes a globally monotone increasing timestamp which is the time it is written.

All the Keys carry a globally unique timestamp, which means that the new writes cannot override the old ones. Even for the delete operations, the write is just a mark to delete, but the actual data is still there. The multiple versions of the data in the same row co-exist in RocksDB according to the time sequence.

When a Read transaction starts, a timestamp is allocated from the time allocator of the cluster. For this transaction, all the data written before this timestamp is visible while the data written after the transaction is invisible. In this way, the transaction can guarantee the Repeatable Read isolation level.

When a Read request is issued from TiDB to TiKV, the timestamp is carried by the request. When TiKV gets the timestamp, it compares the timestamp and the time of the different versions of the row to find the latest version that is no later than this timestamp and returns it to TiDB.

This is the simplified version of how TiDB implements MVCC.

Originally, TiDB reads data based on the historical time which is automatically obtained by the system as a transaction starts. Setting the `tidb_snapshot` session variable is merely enabling TiDB to read data using the time specified by the user to replace the time automatically obtained by the system.

You might wonder that if all the versions are kept, will the space occupied by the data inflate indefinitely？This leads to how TiDB collects garbage.

#### The Garbage Collection (GC) mechanism in TiDB

TiDB collects garbage periodically and removes the data versions that are too old from RockDB. Therefore, the space occupied by the data won’t inflate indefinitely. 

Then how old will the data to be removed? The expiration time of the GC is controlled by configuring a parameter. You can set it to be 10 mins, 1 hour, 1 day or never.
Therefore the History Read feature of TiDB is limited and only the data after the GC expiration time can be read. You might want to set the time to be as long as possible but this is not without any cost. The longer the expiration time, the more space will be occupied, and the Read performance will degrade. It depends on the business type and requirements as to how to configure the expiration time. If the data is very important and data safety is the top priority or there are very few data updates, it is recommended to set the expiration time to be long; if the data is not very important and the data updates are very frequent, it is recommended to set the expiration time to be short.

### Summary

The History Read feature of TiDB exposes the native TiDB reading mechanism and allows users to use it in the simplest way. We hope this feature can help users create more values.
