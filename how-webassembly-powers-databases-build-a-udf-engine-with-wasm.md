---
title: 'How WebAssembly Powers Databases: Build a UDF Engine with WASM'
author: ['Tenny Zhuang']
date: 2021-10-18
summary: WebAssembly is a binary instruction format designed for secure and near-native execution in the sandboxed environment. This post shares how we use WebAssembly to build a user-defined function engine for TiDB.
tags: ['Hackathon']
categories: ['Engineering']
image: /images/blog/how-webassembly-powers-databases-build-a-udf-engine-with-wasm.png
---

**Author:** [Tenny Zhuang](https://github.com/TennyZhuang) (TiKV committer)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![How WebAssembly Powers Databases: Build a UDF engine with WASM](media/how-webassembly-powers-databases-build-a-udf-engine-with-wasm.png)

*This article is based on a project at [TiDB Hackathon 2020](https://pingcap.com/community/events/hackathon2020/).*

User-defined functions (UDFs) are an important extension to the SQL language. When you want to do customized computations in a database, you can write the desired computation logic as a UDF and pass it to the database. But not all DBMSs accept UDFs. For those that don't, a UDF engine is the solution we need.

That's why we built a UDF engine that gives [TiDB](https://pingcap.com/products/tidb/), an open source database, the ability to execute UDFs. Based on [WebAssembly](https://en.wikipedia.org/wiki/WebAssembly) (Wasm), this UDF engine boasts near-native performance and high flexibility. You can create functions using your familiar languages and greatly extend the capabilities of your database.

In this article, I'll share why and how we built the UDF engine, its outstanding features, and how we look forward to tapping into more of its potential.

## Why we need a UDF engine

Built-in SQL functions are often too simplistic to handle complex and volatile real-world business situations. To keep up with the business logic, sometimes, you need to create customized functions. Some DBMSs provide a UDF feature that allows you to write your own function logic and perform the computation in the database, thereby simplifying the application logic.

With UDFs, a database can:

* Supplement unsupported functions.
* Request cloud resources to perform computations.
* Integrate the cloud database with your microservices via a VPC peering connection.

Although it is such an important feature for meeting diversified user requirements, some DBMSs don't provide it. For on-prem, open source databases like TiDB, you can alter the database code and add built-in functions that meet your business needs. However, in the cloud-native era, users often can't touch the database binaries. TiDB also offers its Database as a Service (DBaaS) solutions on the cloud. In this case, users must have a UDF engine to create their own functions.

## Building a Wasm-based UDF engine

### Why Wasm?

To build a UDF engine on top of TiDB, we needed a secure, high performance, and lightweight VM. We chose **[WebAssembly](https://webassembly.org/)** (Wasm).

Wasm is a binary instruction format designed for secure execution in the sandboxed environment. It allows you to execute code written in other languages at near-native speed, so it's a suitable extension for performance-sensitive systems like databases. In recent years, many infrastructure projects (including [Envoy](https://www.envoyproxy.io/) and [OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift)) have adopted Wasm to add extensibility.

We also chose **[Wasmer](https://docs.wasmer.io/)** as a server-side runtime for Wasm and embedded it in TiDB's executor. Wasmer integrates with many programming languages, such as C, C++, Go, and Rust. It supports **LLVM** compilers, which enables fast Wasm bytecode compilation.

### Highlights

**Our UDF engine is fast.** To benchmark UDF performance, we implemented an [`n-body`](https://github.com/tidb-hackathon-2020-wasm-udf/tidb/commit/bbcf0d5748a6462e1030bca07b30d848ea250648) function using our UDF engine and then implemented two more `n-body` functions using TiDB and TiKV's native code (Go and Rust). The results show that UDF `n-body` execution speed is close to Rust and higher than Go.

**The UDF engine is highly flexible.** Theoretically, you can write your UDF in almost any of your favorite languages, given a toolchain that compiles your code into Wasm bytecode. We already developed a set of toolchains for Rust, Go, and C so that their code is compiled into our expected bytecode format.

**The UDF engine is secure.** In the sandbox environment, the UDF engine can only execute limited instructions, without the risk of executing malicious code or invoking system calls. This makes the UDF engine a safe sandbox on the cloud. But its power is not crippled: it can still call the host system's APIs.

**Wasm bytecode is platform agnostic.** You don't need to think about whether the database is on x86 or Arm. You submit your bytecode once, and your custom function can be executed across all TiDB nodes, be they on x86 or Arm.

**It's easy to create and run a UDF.** Simply write the function in your favorite programming language and compile it to Wasm bytecode using [emscripten](https://emscripten.org/). Then you can pass the bytecode into TiDB using `CREATE FUNCTION` and run it like a built-in function. The machine code is stored in a system table. The first time the function is executed, TiDB compiles the code and caches it on the current node.

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('How WebAssembly Powers Databases: Build a UDF Engine with WASM', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('How WebAssembly Powers Databases: Build a UDF Engine with WASM', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## UDF and beyond

Besides the features we've already mentioned, Wasm-based UDF opens up more possibilities for TiDB.

**UDFs can replace the stored procedure feature.** They can expose controlled internal interfaces to execute queries or update data, which achieves a stored procedure-like effect. Traditional stored procedures consume database resources, use non-standard syntax, and often can't be ported. The Wasm-based UDF mechanism prevails because it:

* Accepts any general-purpose language (GPL) that can be compiled to Wasm. GPL is portable and can express more complex logic than domain-specific languages.
* Adapts to any architecture—compile once, run anywhere.
* With the just-in-time compilation, Wasm stored procedures achieve near-native speed.

**UDFs can be used in custom triggers to improve observability.** Custom triggers can call UDFs in the event of data update, timestamp distribution, calculation pushdown, data replication, or any operations that are worth observing. The UDFs can efficiently collect metrics in TiDB and report them to other systems.

**Cloud-based UDFs can connect the database with other systems over the cloud.** A UDF can read data from object storage to achieve heterogeneous storage, or call machine learning models to perform face recognition and then join the recognition results with other tables. With UDFs, you can perform all these operations inside TiDB.

When we implemented this UDF engine using Wasm, we actually realized the tremendous potential Wasm has in server-side applications. If Wasm gains traction in more systems, it will bring users powerful and flexible customizability while ensuring data security. Solomon Hykes, the founder of Docker, once [said](https://twitter.com/solomonstre/status/1111004913222324225) that **WebAssembly on the server is the future of computing**. We, too, believe in that future, and we hope that our small project will give more people a peek into it.

*This article was originally published on [VMblog](https://vmblog.com/archive/2021/09/20/how-webassembly-powers-database-build-a-udf-engine-with-wasm.aspx#.YVUGBWYzb0p).*
