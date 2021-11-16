---
title: 'KubeCon 2021 Q&A: PingCAP Recaps the Event and Explores Its HTAP Database'
author: ['David Marshall']
date: 2021-11-16
summary: VMblog followed up with Liming Deng, PingCAP's database engineer, on his recent presentation on KubeCon 2021.
tags: ['Community news', 'TiKV']
categories: ['Community']
image: /images/blog/kubecon-2021-recap.jpg
---

![KubeCon 2021 Q&A: PingCAP Recaps the Event and Explores Its HTAP Database](media/kubecon-2021-recap.jpg)

*This post was originally published on [VMblog](https://vmblog.com/archive/2021/10/28/kubecon-2021-q-a-pingcap-recaps-the-event-and-explores-its-hybrid-transactional-and-analytical-processing-htap-database.aspx#.YZHrab1Bz0r).*

**KubeCon + CloudNativeCon 2021 - Another Successful Event. Were you in attendance? Did you meet with PingCAP?**

With the conclusion of another very successful KubeCon | CloudNativeCon event, VMblog had the pleasure to follow up with Liming Deng, [PingCAP](https://pingcap.com/)'s database engineer.

**VMblog: As a presenter at KubeCon, can you give VMblog readers a quick overview of your session?**

Liming Deng: During my presentation, [The Roadmap of TiKV, A Cloud-Native Key-value Database](https://kccncna2021.sched.com/event/o4AG/virtual-the-roadmap-of-tikv-a-cloud-native-key-value-database-liming-deng-pingcap?iframe=no&w=100%25&sidebar=yes&bg=no), I discussed the value and roadmap of [TiKV](https://docs.pingcap.com/tidb/stable/tikv-overview), including its definition, its benefits and updates. Essentially, TiKV is a highly scalable, low latency, easy-to-use and cloud-native key-value database. TiKV has been recognized by many notable companies, such as JuiceFS, which is leveraging it as a storage engine, and Tuya, which is using TiKV in their IoT scenarios for its low latency.

Low latency has become a critical component for enterprises to obtain real-time insights for their business as they accelerate their digital transformation efforts. Users want to write latency as low as possible, and desire to use new features effortlessly. During my session at KubeCon, I also dove into why API v2 is an essential feature, as it provides TiKV's scalability with numerous possibilities. API v2 enables users to enjoy the convenience brought by TiKV's transactional (TxnKV) API, and the low latency brought by its non-transactional (RawKV) API, without worrying about their coexistence.

In addition to the powerful scalability, TiKV has lower write latency and higher write throughput with the async input/output optimization. These features expand the application scenarios of TiKV.

**VMblog: How does your company or product fit within the container, cloud, Kubernetes ecosystem?**

Deng: The cloud-native design of PingCAP's TiDB, enables our development team to build the TiDB Operator based on Kubernetes, which helps bootstrap a TiDB cluster on any cloud environment, while simplifying and automating deployment, scaling, scheduling, upgrades and maintenance. With more users building their technology stacks in the cloud, a cloud-native database like TiDB enables cloud service users to easily and elastically scale in and out as business changes, as well as implement disaster recovery, further improving business continuity and availability.

**VMblog: Can you give us the high-level rundown of your company's technology offerings? Explain to readers who you are, what you do and what problems you solve.**

Deng: PingCAP is building a hybrid transactional and analytical processing (HTAP) database with global scalability, through its flagship product, [TiDB](https://pingcap.com/products/tidb/). The company aims to provide a single unified database solution that companies can rely on to drive business results.

TiDB is a cloud-native distributed SQL layer with MySQL compatibility, and one of the most popular open-source database projects in the world. TiDB's sister project, [TiKV ecosystem](https://docs.pingcap.com/tidb/stable/tikv-overview), is a cloud-native distributed Key-Value store, that is a Cloud- Native Computing Foundation (CNCF) Graduated project.

Enterprises are increasingly focused on extracting more insights at faster speed from their data to accelerate their growth fueled by digital transformation and ever-increasing intelligent services. TiDB can address all the challenges faced by enterprises by providing real-time data analysis for mission-critical decision making through HTAP, a stateless SQL layer compatible with MySQL for massive business growth, as well as providing a distributed transactional key value storage for OLTP and OLAP in single architecture.

**VMblog: In the aftermath of the event, do you see any big changes or directions in the industry? What trends do you expect to see in the next few months?**

Deng: After hearing the unique viewpoints and insights from various experts at KubeCon, we are certain the industry is heading in the open-source direction. In fact, our CTO, Ed Huang, leads with the belief that open-source is the only way to succeed for infrastructure software. Kubernetes and Linux, among many other large projects, have shown tremendous success. In that sense, PingCAP has followed in their footsteps, adopting open-source as a core strategy of developing and promoting the next-generation database, especially in the context of cloud-native computing. PingCAP's TiDB and TiKV projects, have been open-source since day one and are currently serving over 1,500 customers across the globe and various industries.

Kubernetes is eating the world, and as a result, cloud-native has become another rapidly emerging trend. As companies progressively move to the cloud and leverage distributed services and solutions, DevOps and site reliability engineer (SRE) teams are becoming increasingly essential for users. As such, Chaos Mesh, a chaos engineering platform designed for Kubernetes, helps to proactively simulate errors in containers and microservices, while improving system resilience. This is another open-source project by PingCAP, backed by the CNCF.
