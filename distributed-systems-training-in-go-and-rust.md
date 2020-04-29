---
title: Distributed Systems Training in Go and Rust
date: 2019-06-20
author: ['Brian Anderson']
summary: PingCAP has made a talent plan for training and/or evaluating students, new employees, and new contributors to TiDB and TiKV. This blog post gives a brief overview of training courses for this plan on writing distributed systems in Go and Rust.
tags: ['Engineering', 'Open Source Community']
categories: ['Open Source Community']
---

At PingCAP we love the [Go] and [Rust] programming languages. They are the
languages with which we write the databases [TiDB] and [TiKV], respectively.
They have empowered us to build these fast and reliable distributed systems from
the ground up, and iterate on them quickly and confidently.

These languages are the future of systems programming.

We expect a lot from ourselves &mdash; our engineers need to be, or to quickly
become, experts on both databases and distributed systems, and to be comfortable
expressing that knowledge in these modern languages. The products we
develop are on the cutting edge of distributed systems, storage technology,
software design, and programming language theory, and yet there are few
opportunities for students to gain hands-on experience with this intersection of
technologies.

At PingCAP we are committed to mentoring the next generation of systems
programmers, those who are beginning their careers in a world that is quickly
adopting next-generation systems languages.

To this end, PingCAP is creating [a series of training courses][c] on writing
distributed systems in Go and Rust. These courses consist of:

- **[Practical Networked Applications in Rust][c-rust]**. A series of projects
  that incrementally develop a single Rust project from the ground up into a
  high-performance, networked, parallel and asynchronous key/value store. Along
  the way various real-world and practical Rust development subject matter are
  explored and discussed.

- **[Distributed Systems in Rust][c-dss]**. Adapted from the [MIT 6.824]
  distributed systems coursework, this course focuses on implementing important
  distributed algorithms, including the [Raft] consensus algorithm, and
  the [Percolator] distributed transaction protocol.

- **[Distributed Systems in Go][c-go]**. A course on implementing implementing
  algorithms necessary in distributed databases, including map reduce, and
  parallel query optimization.

Today they are in an early state, but we would appreciate if you give them a
look and help us improve them over at our [PingCAP Talent Plan][c].

[Go]: https://golang.org/
[Rust]: https://www.rust-lang.org/
[TiDB]: http://github.com/pingcap/tidb
[TiKV]: https://github.com/tikv/tikv/
[c]: https://github.com/pingcap/talent-plan
[c-rust]: https://github.com/pingcap/talent-plan/tree/master/courses/rust
[c-dss]: https://github.com/pingcap/talent-plan/tree/master/courses/dss
[c-go]: https://github.com/pingcap/talent-plan/tree/master/tidb
[MIT 6.824]: http://nil.csail.mit.edu/6.824/2017/index.html
[Raft]: https://raft.github.io/
[Percolator]: https://storage.googleapis.com/pub-tools-public-publication-data/pdf/36726.pdf
