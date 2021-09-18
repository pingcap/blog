---
title: Why did we choose Rust over Golang or C/C++ to develop TiKV?
date: 2017-09-26
summary: Every developer has his/her favorite programming language. For the TiKV team members, it's Rust.
tags: ['TiKV', 'Rust']
aliases: ['/blog/2017/09/26/whyrust/', '/blog/2017-09-26-whyrust']
categories: ['Engineering']
---

## What is Rust

[Rust](https://en.wikipedia.org/wiki/Rust_(programming_language)) is a systems programming language sponsored by Mozilla Research. It moves fast and steady with a 6-week release cycle ever since its 1.0 version in May 2015.

See the following list for some of the features that most attract us:

+ The design principles of Rust resemble with C++ in [Abstraction without overhead](https://blog.rust-lang.org/2015/05/11/traits.html) and [RAII (Resource acquisition is initialization)](https://doc.rust-lang.org/stable/rust-by-example/scope/raii.html).

+ The minimum runtime and efficient C bindings empower Rust to be as efficient as C and C++, thus making it very suitable for the systems programming field where high performance matters the most.

+ The powerful type system and unique life cycle management facilitate the memory management during the compiling, which ensures the memory and thread safety and makes the program run very fast after the compiling.

+ Rust provides pattern matching and type inference like a functional programming language and makes the code simple and elegant.

+ The macros and traits allow Rust to be highly abstract and save quite a few boilerplates during the engineering especially when it comes to the libraries.

## The Rust Ecosystem

Because of the excellent package management tool, Cargo, Rust has many types of libraries, such as Hyper for HTTP, Tokio and mio for asynchronous I/O, basically all the libraries that are required to construct a backend application.

Generally speaking, Rust is mainly used to develop server-side applications with high performance at this stage. In addition, its innovation in the type system and syntax gives it a unique edge in developing Domain-Specific Libraries (DSL).

## The Rust adoption

As a new programming language, Rust is unique. To name just a few projects that are using Rust,

+ The backend distributed storage system of Dropbox
+ [Servo](https://github.com/servo/servo), the new kernel of Firefox
+ [Redox](https://github.com/redox-os/redox), the new operating system
+ [TiKV](https://github.com/pingcap/tikv), the storage layer of [TiDB](https://github.com/pingcap/tidb), a distributed database developed by [PingCAP](https://pingcap.com/).

As one of the listed Friends of Rust, TiKV has been one of the top projects in Rust according to the Github trending.

TiKV is a distributed key-value database. It is the core component of the TiDB project and is the open source implementation of Google Spanner. We chose Rust to build such a large distributed storage project from scratch. In this blog, I will uncover the rationale.

In the past long period of time, C or C++ has dominated the development of infrastructure software such as databases. Java or Golang has problems such as GC jitter especially in case of high read/write pressure. On the one hand, Goroutine, the light-weight thread and the fascinating feature of Golang, has significantly reduced the complexity of developing concurrent applications at the cost of the extra overhead in context switching in the Goroutine runtime. For an infrastructure software like a database, the importance of performance goes without saying. On the other hand, the system needs to remain its "Certainty" which makes it convenient for performance tuning. But introducing GC and another runtime contributes to the opposite. So for quite a long time, C/C++ seems to be the only choice.

TiKV originates from the end of 2015. Our team was struggling among different language choices such as Pure Go, Go + Cgo, C++11, or Rust.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('Why did we choose Rust over Golang or C/C++ to develop TiKV?', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Why did we choose Rust over Golang or C/C++ to develop TiKV?', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

+ **Pure Go:** Our core team has rich experience in Go. The SQL layer of TiDB is developed in Go and we have benefited quite a lot from the high efficiency brought by Go. However, when it comes to the development of the storage layer, Pure Go is the first option to rule out for one simple reason: we have decided to use RocksDB as the bottom layer which is written in C++. The existing LSM-Tree implementations (like goleveldb)  in Go were hardly as mature as RocksDB.

+ **Cgo:** If we had to use Go, we had to use Cgo to bridge but Cgo had its own problems. At the end of 2015, the performance might be greatly impacted if calling Cgo in Go code rather than calling Cgo in the same thread with Goroutine. Besides, databases require frequent calls to the underneath storage libraries, aka RocksDB. It was highly inefficient if the extra overhead was needed every time the RocksDB functions were called. Of course, some workarounds could be introduced to enlarge the throughput of calling Cgo, such as packaging the calls within a certain period to be a Cgo batch call that will increase the latency of a single request and erase the Cgo overhead. But, the implementation might be very complex while the GC problem was not entirely solved. At the storage layer, we want to use the memory as efficiently as possible. Hacky workarounds such as extensive use of `syscall.Mmap` or object reuse might damage the readability of the code.

+ **C++11:** There ought to be absolutely no issue with C++11. RocksDB is developed using C++11. But given the team background and what we want to do, we didn't choose C++11. The reasons are as follows:

    1. The core team members are experienced C++ developer with rich experience in large C++ projects. But the seemingly inevitable problems in large projects like Dangling pointers, memory leak, or data race make them shudder at the thought. Of course, the probability of these problems could be lowered if well guided, or having a stringent code review and coding rules in place. But if a problem occurred, it might be costly and burdened to debug. Not to mention that we have no controls if the third-party libraries could not meet our coding rules.
    2. There are too many and too different programming paradigms in C++ as well as too many tricks. It demands extra costs to unify the coding style especially when there are more and more new members who might not be familiar with C++. After years of using languages with GC, it is very hard to go back time for manually managing the memory.
    3. The lack of package management and CI tools. It appears not to be trivial, but the automated tools are very important for a large project because it is directly related to the development efficiency and the speed of iterating. What's more, the C++ libraries are far from enough and some of them need to be created by ourselves.

+ **Rust:** The 1.0 version of Rust is released in May 2015 with some charming features:

    1. Memory safety
    2. High performance which is empowered by LLVM. The runtime is practically no different from C++. It also has affinities to the C/C++ packages.
    3. Cargo, the powerful package management tools
    4. Modern syntax
    5. Almost consistent troubleshooting and performance tuning experience. We can directly reuse some of the tools like perf which we are already very familiar with.
    6. FFI (Foreign Function Interface), call directly into the C APIs in RocksDB free of losses.

    The first and foremost reason is memory safety. As mentioned earlier, the issues in the memory management and data race might seem to be easy for C++ veterans. But I believe the utmost solution, which is what Rust is doing, is to put constraints in the compiler and solve it from the very beginning. For large projects, never ever bet the quality solely on human beings. To err is human. Though Rust is hard to begin with, I think it's totally worth the while. Besides, Rust is a very modern programming language with its extraordinary type system, pattern modeling, powerful macros, traits, etc. Once you are familiar with it, it can greatly improve the efficiency which might be the same as if we chose C++ counting the time to debug. According to our experience, it takes about 1 month for a software engineer to code in Rust from zero experience. The efficiency is almost the same between an experienced Rust engineer and a Golang engineer.

To sum up, Rust, as an emerging programming language, seems to be new to most of the developers in China, but it has become the most promising challenger to C/C++. Rust was also crowned the "most loved" technology in [StackOverflow's 2016 developer survey](http://techbeacon.com/highlights-stack-overflow-2016-developer-survey). So from a long term, Rust will shine in scenarios where memory safety and performance matter the most.
