---
title: Five Principles that Guide TiDB and PingCAP (Part II)
author: ['Max Liu']
date: 2021-01-26
summary: PingCAP's CEO talks about the philosophy of TiDB's evolution, focusing on two more principles.
tags: ['Architecture']
categories: ['Company']
image: /images/blog/tidb-philosophy-five-principles-that-guide-tidb-and-pingcap.jpg
---

![Five Principles that Guide TiDB and PingCAP](media/tidb-philosophy-five-principles-that-guide-tidb-and-pingcap.jpg)

_This article is based on a talk given by Max Liu at PingCAP Infra Meetup._

In [my last post](https://pingcap.com/blog/five-principles-that-guide-tidb-and-pingcap), I talked about how we made TiDB work, made it right, and, finally, made it fast. But we didn't stop there. To build an ideal database, we need to make TiDB affordable for all and adopted by all.

## Make it cheap

To tap into TiDB's full potential, users must deploy it on SSDs. Some complained that SSD costs were high. At first, we were confused because SSDs were not so expensive, and storage devices only made up a small fraction of the total cost.

But from the users' perspective, the story was different. In most applications, there were peak hours and off-peak hours. For example, for a user who has hundreds of TB data, if they only need to generate a report for the daily revenue at the end of every day, it doesn't make sense to use the most expensive configuration that is reserved for peak hours.

### Elastic scaling

So we were confronted with a new dilemma: only a part of user data was hot, but the machine had to handle all the data. Can we separate hot data from cold data in the system? Can we elastically scale out the database so that TiDB only scales the hot data and, once the peak is over, release resources?

If an application's peak and off-peak periods are only different because in peak hours 5% of the data become hot spots, it isn't necessary to handle all the data. When the system detects a hot spot, it creates a new node for the hot data only. When the peak is over, it pulls the plug on the new node. In this way, more expensive configuration resources are not occupied for the whole time, and the system stays elastically scalable.

The scenario above presents a challenge to the database architecture. For traditional Relational Database Management Systems (RDBMSs) in a primary-secondary architecture like MySQL, if the primary database meets a hot spot, the only way to balance the load is to add a machine with the same configuration and replicate all the data. However, the application only needs to access the hot data, which is 5% of the total.

With TiDB, the situation is quite different. TiDB is a highly dynamic system, whose architecture can adapt to these requirements. TiDB splits data into [small ranges of 96 MB](https://docs.pingcap.com/tidb/stable/glossary#regionpeerraft-group), so the system can tell precisely which range of data is hot and scale out that range.

### More possibilities with the architecture

The same idea can be applied to other use cases, including:

* For data analytics, TiDB doesn't have to scan all the data.
* For a multi-tenancy system, TiDB can fetch the data of a single tenant without effort.
* For columnar computing, TiDB only needs to replicate the range of data it needs.

These use cases are only possible with a highly elastic and dynamic architecture. This architecture, combined with Kubernetes and the cloud, can bring us more value than we anticipated.

## Build a universal, globally-adopted database

At PingCAP, our goal is to build a universal, globally-adopted database. To achieve this goal, we have adopted **Principle #4: Focus on creating a universal database**. This means:

* Creating a database that could be used in any industry, in any scenario, and anywhere. We believed that TiDB should be a universal database, rather than an industry-specific one. We stuck by this idea, even though it meant at early stages we couldn't acquire customers rapidly.
* We made sure that we had global adopters. Our adopters include companies in North America, Europe, and Asia. They've tested TiDB in a huge array of scenarios and won over many other customers.
* We have a global workforce. Our remote workforce culture ensures that we hire the best talent, no matter where they live. We also maintain an active open source community and engage with contributors worldwide.
* We don't ignore the "vertical" part of our product; we just focus on it when the time is right. Only when we established a full-scale, elastic, and extensible architecture, did we turn our attention to performance.

## Attract top customers and the others will follow

Initially, we didn't try to sell TiDB to everyone. This reflects TiDB Principle #5: **Focus on and win over high value, industry leading companies, and the smaller companies will follow**.

Looking at TiDB's customer stories, our early adopters had some common characteristics, including:

* Market values over 10 billion dollars.
* The largest data volume and the most challenging scenarios.
* Extremely high queries per second (QPS) and rigorous standards for database stability.

In addition, these companies were not very sensitive to costs, so when they chose infrastructure software like databases, they weren't concerned with the price. They based their decision solely on the product itself: can the product solve their problems or not?

Therefore, we decided to target TiDB at those companies, because TiDB is a distributed database designed for massive data. By verifying TiDB's usability in those large companies, we felt it would be easier to persuade smaller companies (those valued at US $1 billion) to try it. After that, if our database was proven to be stable and scalable and that it could handle various use cases, it would be even easier to win the trust of other companies.

## Looking back and going forward

In 2015, when we started the company, people mocked us: how dare you claim to build a new database? Just five years later, in 2020, we had adopters across the globe and closed $270 million of series D round of funding. TiDB had higher performance and lower latency, supported hybrid cloud service and elastic scaling, and became a true HTAP database. We acquired major customers in the financial and banking industries, including companies in China, Japan, and North America.

In 2021, the world is full of uncertainty and change, but with TiDB's principles in place, we're confident we can meet our challenges and prosper.
