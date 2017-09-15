---
layout: post
title: RocksDB in TiKV
excerpt: This is the speech Tang Liu gave at the RocksDB meetup on August 28, 2017.
---

This is the speech Tang Liu gave at the [RocksDB meetup](https://www.meetup.com/RocksDB/events/242226234/) on August 28, 2017.
<span id="top"><span>
<!-- TOC -->

- [RocksDB in TiKV](#rocksdb-in-tikv)
    - [Speaker Introduction](#speaker-introduction)
    - [Agenda](#agenda)
    - [Why did we choose RocksDB?](#why-did-we-choose-rocksdb)
    - [TiKV Architecture](#tikv-architecture)
    - [Region](#region)
    - [Raft](#raft)
    - [InsertWithHint](#insertwithhint)
    - [Prefix Iterator](#prefix-iterator)
    - [Table Property for Region Split Check](#table-property-for-region-split-check)
    - [Table Property for GC Check](#table-property-for-gc-check)
    - [Ingest the SST File](#ingest-the-sst-file)
    - [Others](#others)
    - [How are we contributing?](#how-are-we-contributing)
    - [Future Plans](#future-plans)

<!-- /TOC -->

# RocksDB in TiKV

## Speaker Introduction

Hi every one,  thanks for having me here, the RocksDB team. 

Today, I will talk about how we use [RocksDB](https://github.com/facebook/rocksdb) in [TiKV](https://github.com/pingcap/tikv). Before we start, I will introduce myself briefly. My name is Tang Liu, chief engineer of PingCAP. Now I am working on [TiDB](https://github.com/pingcap/tidb), the next generation SQL database; and [TiKV](https://github.com/pingcap/tikv),  a distributed transactional key-value store. I am an open source lover and I have developed some open source projects like LedisDB (BTW, the backend engine is also RocksDB), go-mysql, go-mysql-elasticsearch, etc…

## Agenda

What I will talk about today is as follows: 

* Why did we choose RocksDB in TiKV?

* How are we using RocksDB in TiKV?

* How are we contributing to RocksDB?

* Our future plan

## Why did we choose RocksDB?

OK, let’s begin. Why did we decided to use RocksDB instead of LevelDB, WiredTiger, or any other engines. Why? I have a long list of reasons:

* First of all, RocksDB is fast. We can keep high write/read speed even there’s a lot of data in a single instance. 

* And of course, RocksDB is stable. I know that RocksDB team does lots of stress tests to guarantee the stability；

* And it’s easy to be embedded. We can call RocksDB’s C API in Rust directly through FFI, because TiKV is written in Rust. 

* Not to mention that it has many useful features. We can use them directly in production to improve the performance.

* In addition, RocksDB is still in fast development. Many cool features are added, and the performance is being improved continuously.

* What’s more, RocksDB has an very active community. If we have questions, we can easily ask for help. Many RocksDB team members and us are even WeChat (a very popular IM tool in China) friends, we can talk to each other directly.

[Back to the top](#top)

## TiKV Architecture

After we decided to use RocksDB, the next question is how to use it in TiKV. Let me start with the TiKV architecture briefly.

![TiKV Architecture]({{ site.baseurl }}/assets/img/tikvarchitecuture.png)

First of all, all data in a TiKV node shares two RocksDB instances. One is for data, and the other is for Raft log. 

## Region

Region is a logical concept: it covers a range of data. Each region has several replicas, residing on multiple machines. All these replicas form a Raft group.

![Region]({{ site.baseurl }}/assets/img/tikvarchiregion.png)

## Raft

TiKV uses the [Raft consensus algorithm](https://raft.github.io/) to replicate data, so for every write request, we will first write the request to the Raft log, after the log is committed, we will apply the Raft log and write the data. 

![Raft]({{ site.baseurl }}/assets/img/raft.png)

The key format for our Raft log saved in RocksDB is: region ID plus log ID, the log ID is monotonically increased. 

## InsertWithHint

![InsertWithHint]({{ site.baseurl }}/assets/img/InsertWithHint.png)

We will append every new Raft log to the region. For example, we first append log 1 for region 1, then we might append log 2 for the same region later. So we use memtable insert with the hint feature, and this feature improves the insert performance by fifteen percent at least. 

![Key and Version]({{ site.baseurl }}/assets/img/keyandversion.png)

The version is embedded in the key as a suffix, and used for ACID transaction support. But transaction management is not our topic today, so I just skip it.

[Back to the top](#top)

## Prefix Iterator

![Prefix Iterator]({{ site.baseurl }}/assets/img/prefixiterator.png)

As you can see, we save the key with a timestamp suffix, but can only seek the key without the timestamp, so we set a prefix extractor and enable the memtable bloom filter, which helps us improve the read performance by ten percent at least. 

## Table Property for Region Split Check

![Table Property for Region Split Check]({{ site.baseurl }}/assets/img/splitcheck.png)

If we insert a lot of data into a region, the data size will soon exceed the threshold which we predifine and need to be split. 

In our previous implementation, we must first scan the data in the range of the region, then calculate the total size of the data, if the total size is larger than the threshold, we split the region.

Scanning a region has a high I/O cost, so now, we use table properties instead. We record the total data size in the SST table property when doing compaction, get all table properties in the range, then add up the total size. 

Although the final calculated total size is approximate, it is more effective, we can avoid the useless scan to reduce the I/O cost.

## Table Property for GC Check

![Table Property for GC Check]({{ site.baseurl }}/assets/img/tablecheck.png)

We use multiple versions for a key, and will remove the old keys periodically. But we don’t know whether we need to do GC in a range or not, in the past, we simply scanned all the data.

However, since we only need to do GC before a specified safe point, and most keys have only one version, scanning these keys every time is wasteful. 

So we create an MVCC property collector to collect the version information, including the maximum and minimum timestamp, the row number and version number. Then every time before scanning a range, we can check these properties to see if we can skip the GC procedure or not. 

For example, if we find the minimal timestamp in the table property is bigger than the safe point, we can immediately skip scanning the range. 

[Back to the top](#top)

## Ingest the SST File

![Ingest the SST File]({{ site.baseurl }}/assets/img/ingest.png)

And in our previous implementation, if we wanted to do bulk load, we must scan all the key-values in the range and save them into a file. Then in another RocksDB, read all the key-values from this file and inserted them in batches. 

As you can see, this flow is very slow and can cause high pressure in RocksDB. So now, we use the `IngestFile` feature instead. At first, we scan the key-values and save them to an SST file, then we ingest the SST file directly. 

## Others

![Others]({{ site.baseurl }}/assets/img/others.png)

More than that, we enable sub compaction, pipelined write, and use direct I/O for compaction and flush. These cool features also help to improve the performance. 

## How are we contributing?

We are not only using RocksDB, we also do our best to contribute to the community. We have done many stress tests and have found some serious data corruption bugs. Like these issues. 

* [#1339](https://github.com/facebook/rocksdb/issues/1339): sync write + WAL may still lose newest data 

* [#2722](https://github.com/facebook/rocksdb/issues/2722): some deleted keys might appear after compaction

* [#2743](https://github.com/facebook/rocksdb/issues/2743): delete range and memtable prefix bloom filter bug

Thank goodness, we haven’t found any of our users meet these problems in production. 

We also added features and fixed some bugs, like these. Because TiKV can only call the RocksDB C API, we also add many missing C APIs for RocksDB. 

* [#2170](https://github.com/facebook/rocksdb/pull/2170): support PopSavePoint for WriteBatch

* [#2463](https://github.com/facebook/rocksdb/pull/2463): fix coredump when release nullptr

* [#2552](https://github.com/facebook/rocksdb/pull/252): cmake, support more compression type

* many C APIs

## Future Plans

In the future, we are planning DeleteRange API, which is a very useful for us. But now we found some bugs [2752](https://github.com/facebook/rocksdb/issues/2752) and [2833](https://github.com/facebook/rocksdb/issues/2833), we are trying our best to fix them, of course, together with the RocksDB team. 

And we will try to use BLOB DB when it’s stable. On the other hand, we will also try different memtable types to speed up the insert performance, and use partitioned indexes and filters for SATA disks. 

[Back to the top](#top)