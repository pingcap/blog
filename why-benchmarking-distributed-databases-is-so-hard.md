---
title: Why Benchmarking Distributed Databases Is So Hard
date: 2019-07-08
author: ['Ana Hobden']
summary: Benchmarks are hard to get right, and many articles touting benchmarks are actually benchmarketing, showcasing skewed outcomes to sell products. This post introduces some of the motivations for benchmarking and the common tools, and discusses a few things to keep in mind when benchmarking.
tags: ['Benchmark', 'Distributed system']
categories: ['Engineering']
image: /images/blog/why-benchmarking-distributed-databases-is-so-hard-1.png
---

![Why Benchmarking Distributed Databases Is So Hard](media/why-benchmarking-distributed-databases-is-so-hard-2.png)

At KubeCon+CloudNativeCon Europe 2019, [Iqbal Farabi](https://www.linkedin.com/in/iqbal-farabi-02756923/) and [Tara Baskara](https://www.linkedin.com/in/tara-baskara-5050003b/) from [GO-JEK](https://www.go-jek.com/) presented their findings on experiments to benchmark various cloud native databases, such as Vitess, CockroachDB, FoundationDB, TiDB, YugaByte DB, etc. They applied the following filters to the list:

- Open source
- Operational database
- ACID compliance
- Provides SQL-like API

The result was the following list of databases to benchmark:

- [CockroachDB](https://github.com/cockroachdb/cockroach)
- [TiDB](https://github.com/pingcap/tidb)
- [YugaByte DB](https://github.com/YugaByte/yugabyte-db)

For the database benchmarking, they used [go-ycsb](https://github.com/pingcap/go-ycsb), a Go port of Yahoo! Cloud System Benchmark (YCSB) from PingCAP. Feel free to check out the [video recording](https://youtu.be/cz-eHwqtyvU) and [slides](https://static.sched.com/hosted_files/kccnceu19/22/Benchmarking%20Cloud%20Native%20Database%20Running%20on%20Kubernetes.pdf).

We highly appreciate the great work from Iqbal Farabi and Tara Baskara. Their presentation about benchmarking cloud native databases is a great one, and we believe it could benefit the entire cloud native and open source database community.

However, in the TiDB part of the presentation, the benchmark results were not ideal. We tried to reproduce what's in the slide, but because there was some unclear information about the setup and configuration, we have got very different benchmark results. If you are interested in our results, feel free to email: info@pingcap.com. As a next step, we will work closely with Iqbal Farabi and Tara Baskara to update the results.

In the meantime, their work got us into thinking: why is it so hard to benchmark distributed databases? As mentioned by &lt;antirez&gt; in [Why we don't have benchmarks comparing Redis with other DBs](http://antirez.com/news/85), you can see how choosing an unrealistic deployment and workload for a benchmark can easily impact the reaction to the results.

If you're an avid reader of distributed system news like we are, you've probably seen your share of benchmarks. You've also probably stopped taking them at face value.

Unfortunately, benchmarks are hard to get right, and even more unfortunately, many articles touting benchmarks are actually _benchmarketing_, showcasing skewed outcomes to sell products.

So why do it at all? Let's take a look at some of the motivations for benchmarking, the common tools, and discuss a few things to keep in mind when benchmarking.

## Why benchmark at all?

If you don't have reproducible, fair benchmarking, you can be blinded by your own hubris. Our contributors and maintainers depend on benchmarks to ensure that as we strive to improve TiDB, we don't negatively impact its performance. To us, not having benchmarks is like not having logging or metrics.

For our business, benchmarks give us tangible, real data we can share with both potential and existing users:

_How will new feature X impact the performance of workload Y that customer Z uses?_

Being able to benchmark against these workloads can inform our development, and positively impact all users — not just the originating benchmarker.

While benchmarks can be used for these noble purposes, they can also be used for evil. They can be used for _benchmarketing_, which skews the results in favor of a particular deployment. Sometimes it's hard to spot, and for some readers, the easiest way to understand if something is or isn't *benchmarketing* is to look in the comments.

## What makes it so hard?

On the surface, benchmarking sounds pretty easy. You turn on the service, you make a bunch of requests, and you measure the time it takes.

But as you start to dive in, the story changes. Computers aren't the same, and distributed systems are even less so.

Different RAM configurations, CPU sockets, motherboards, virtualization tools, and network interfaces can all impact the performance of a single node. Across a set of nodes, things such as routers, firewalls, and other services can also interact with metrics.

Heck, even processing architectures aren't even all the same! For example, our software uses Streaming SIMD Extensions 3 (SSE3), a feature that isn't available on all processors. This could mean huge performance differences between otherwise similarly-specced machines.

So instead of worrying too much about the specifics of how workloads perform on a particular machine, it's fairly common to focus on relative benchmarks between different versions of the same product, or different products, on the same hardware.

While everyone wants to be incomparable, it's very important to compare yourself to something. Knowing relative numbers gives us the ability to understand how a new change might impact our product, or to learn our weaknesses based on the results of another product.

### The status quo

It's fairly common to see articles touting benchmarks gathered off big cloud machines in fairly small deployments. The author will go over the deployment specifications, then run a few tools like Yahoo! Cloud Serving Benchmark (YCSB) and Transaction Processing Performance Council Benchmark C (TPC-C), and show off some graphs comparing the outcomes to either other versions or other products.

This is pretty awesome, actually.

Being able to (mostly) replicate their deployment, readers should be able to replicate their results. It also gives readers a chance to see any configuration the author might have done to favor results.

For example, it would be hardly fair to test key-value store TiKV 2.1 with sync-log off vs TiKV 3.0 with sync-log on. There are big performance (and safety) characteristics between the two settings.

Comparing products can be even worse. Products with different features and configurations are hard to compare — especially if the author is an expert in one system and a novice in another.

If you're like some of our contributors, you might have smirked at a few benchmarks before as you saw configurations that clearly favored one product or another. They're as subtle as possible, of course, but they're often the key to understanding a surprising result.

### Distributed systems are complex!

When you consider a distributed system, it's important to choose a realistic topology. We doubt a user will ever deploy  six stateless query layers (like TiDB) to talk to two key-value store (TiKV) services and one Placement Driver (PD) service, so why would we benchmark that?

Choosing the right machines is important too. Production deployments of distributed systems often suggest (or require) certain configurations. For example, we suggest you use your fastest storage and memory nodes to serve TiKV. If most TiKV nodes were running on a spinning disk machine, it's likely system performance would be heavily degraded, and benchmarks would be skewed.

We maintain a dedicated cluster of machines that our maintainers can use for benchmarking and testing. This gives us consistent, reliable benchmarks, because the topology is stable, and the machines do not run other noisy VMs or services.

Also, distributed systems like TiDB are often flexible, and tuning can dramatically impact the metrics for specific workloads. Tuning the database properly to the workload can help us properly test features, and inform our users of possible easy-gains for their use cases.

### Different scenarios, different standards

Databases have an incredible variety of use cases and workloads. Understandably, there is no universal, all-encompassing benchmark. Instead, we have a variety of tools at our disposal.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('Why Benchmarking Distributed Databases Is So Hard', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Why Benchmarking Distributed Databases Is So Hard', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

#### TPC-C

The [TPC-C benchmark](http://www.tpc.org/tpc_documents_current_versions/pdf/tpc-c_v5.11.0.pdf) is an Online Transactional Processing (OLTP) standard that takes the perspective of distributing orders to customers. The metric it measures is the number of orders processed by the benchmark per minute.

The TPC-C tries to measure the essential performance characteristics of some operations portrayed through the lens of a company distributing products to warehouses and districts, and then on to customers.

The benchmark doesn't attempt to measure the impact or cost of ad-hoc operational or analytical queries, such as the effect of decision support or auditing requests.

It uses fixed, scaling, and growing tables, and has a number of operations, such as creating new orders, paying for orders, checking the status of orders, and inquiring into the stock level of items.

The benchmark defines strict requirements for response time and consistency, and it uses multiple client connections to do this. (An example of a multiple client connection is creating an order with one client, and checking for it with another.)

The TPC-C has been one of the more popular OLTP benchmarks for a couple of decades, and it is commonly used to determine a system's cost or power efficiency. It's useful for determining the common, day-to-day performance of an OLTP database.

#### TPC-H

The [TPC-H benchmark](http://www.tpc.org/tpc_documents_current_versions/pdf/tpc-h_v2.18.0.pdf) is a decision-support benchmark. It operates over a minimum dataset size of about 1 gigabyte, though it's commonly run on larger populations. It measures metrics through composite queries per hour. (The standard discourages comparing between sizes, which is misleading.)

The TPC-H tries to measure the ability of a database to handle complex, large, ad-hoc queries. It functions similar to how a data lake functions in an extract, transform, load (ETL) pipeline, staying closely synchronized with an online transactional database. Complex queries are run over the dataset ad-hoc, and at varied intervals.

In many ways, TPC-H complements TPC-C. TPC-H represents the analytical database which handles the queries the TPC-C doesn't.

#### Sysbench

Unlike the TPC benchmarks, [sysbench](https://github.com/akopytov/sysbench) is a scriptable benchmarking system in C and Lua. It offers a number of simple tests, and allows them to define subcommands (for example prepare and cleanup).

Because it's scriptable, you can use sysbench to create your own benchmarks, and also use the included benchmarks like `oltp_read` and `oltp_point_select`.

Sysbench is useful when you're trying to isolate problem cases, or want specific workload metrics.

#### YCSB

The [YCSB](https://github.com/brianfrankcooper/YCSB) is a framework and common set of workloads for evaluating databases. Unlike the TPC benchmarks, it supports key-value stores, such as TiKV or redis. It reports in operations/sec.

YCSB is  not as complex as the TPC benchmarks, but it has a number of fairly simple core workloads that you can use to evaluate system performance. Workloads A through F each offer a simplified workload of situations such as photo tagging, session stores, news, conversations, and user settings management.

PingCAP maintains a [Go fork of YCSB](https://github.com/pingcap/go-ycsb) that we regularly use to test our own database and those of our respected colleagues.

## What makes a good benchmark?

The best benchmark has two things going for it: It is **reproducible** and **convincing**.

As we discussed earlier, when you benchmark a distributed system there are a wide variety of variables. Choosing and detailing the topology, hardware, and configuration of the deployment is key for reproducibility. If you're testing multiple products, make their configurations as equivalent as possible.

It's not fair to compare an in-memory, single-node service against a persisted, redundant service. Pay attention to consistency guarantees in the documentation. If one database uses snapshot isolation by default, and the other requires you to enable it, make sure to make the configurations consistent so the comparison is fair.

Being convincing also involves accepting your weaknesses. A benchmark result where your preferred database clearly outperforms all the others in every result *_feels_* a lot like benchmarketing. Including outcomes that don't favor your preferred database can help keep you honest, and show folks you aren't trying to be evil.

## How to make a decent benchmark

Before we even get started on making a benchmark, we need to Read Those Fricking Manuals™ for each of the databases we'd like to benchmark, as well as each of the tools or workloads we want to benchmark. Understand what the tools are good at, and what they're bad at.

Numbers that are just numbers mean nothing  — you must have an understanding of what you have benchmarked, and what the results mean. You should ensure that the benchmark configurations, specs, and topologies are all realistic and appropriate for the situation.

Pay attention to tuning guides or recommended deployment options. If possible, use official deployment tools like [TiDB Ansible](https://github.com/pingcap/tidb-ansible) or [TiDB Operator](https://github.com/pingcap/tidb-operator/), because they often are built to handle things like essential OS configuration.

If you're looking for a model to start from, our friends at Percona do a great job with their benchmarking articles like [PostgreSQL and MySQL: Millions of Queries per Second](https://www.percona.com/blog/2017/01/06/millions-queries-per-second-postgresql-and-mysql-peaceful-battle-at-modern-demanding-workloads/).

### Focus on a realistic metric

The TPC-C and TPC-H don't focus on just plain operations/second. TPC-H only measures _complex_ queries. In contrast, TPC-C doesn't consider ad-hoc or complex queries, it just measures how many orders can be processed. Consider the use cases that you need to evaluate, and find or create a benchmark that is an appropriate match.

Since you're considering a _distributed system_, you should also consider testing the database over different latencies or failure cases. You can use tools like traffic control (`tc`) to introduce delays or unreliability in a controlled way.

You should also consider what percentiles you're interested in, and how much outliers mean to you. Measuring only the 99th percentile of requests can be misleading if one system has some possibly problematic outliers.

Stutter can affect high-load databases just like other performance games. You can learn more about percentiles and stutter in [Iain's (NVIDIA) excellent stutter article](https://developer.nvidia.com/content/analysing-stutter-%E2%80%93-mining-more-percentiles-0).

### Distribute the workload

A naive approach to writing a benchmark might involve a single client interacting with a distributed database and running a workload.

However this is rarely a realistic situation. It's much more likely that a large number of clients will be interacting with the database. Consider the TPC-C. It's unlikely that all of the warehouses and districts would connect over the same connection, or wait to take turns running their queries!

When you benchmark a distributed system intended to handle a high volume of traffic, like TiDB, using only one connection will almost certainly result in your benchmarking tool becoming bottlenecked. Instead of benchmarking the database, you're actually benchmarking the tool!

Instead, it's better to use multiple connections like TPC-C and sysbench do. Not only is this more realistic, in many cases it will result in more accurate performance numbers. This is because distributed algorithms like 2PC are impacted by network round trips, and the overall throughput of the system will be higher, despite the average latency being possibly higher too.

### Dig into the why

A good benchmark report doesn't just show off numbers and state “X is faster” — that's not interesting! _Why_ is X faster? Is it because of mistakes? Or is it the result of deliberate choices that had consequences?

Talking about why one test subject is faster not only makes the results more interesting, it also makes them more legitimate. If an author can explain why results differ, it demonstrates that they performed the necessary research to make an accurate benchmark.

### Consult the experts

If you're surprised or puzzled by your initial results, sometimes it's a good idea to email or call the database vendor. It's very likely they can help you find a tuning option or implementation detail that might be causing these results.

It's common for proprietary databases to have restrictive clauses against publishing benchmarks. We don't. At PingCAP, we love reading the benchmarks folks do on our database, and we try to help them set up fair, realistic scenarios for their benchmarks.

After all, talk is cheap — show us the code!
