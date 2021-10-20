---
title: the TiDB Source Code
date: 2020-01-06
summary: The target audience of this document is the contributors in the TiDB community. The document aims to help them understand the TiDB project. It covers the system architecture, the code structure, and the execution process.
tags: ['Architecture', 'Query execution']
aliases: ['/blog/2017/01/06/about-the-tidb-source-code/', '/blog/2017-01-06-about-the-tidb-source-code']
categories: ['Engineerng']
image: /images/a_fake_path.png
---

The distributed executor is mainly about distributing tasks and collecting results. The `Select` interface returns a data structure, which is called `SelectResult`. The structure can be considered to be an iterator. Because there are many region servers at the bottom layer, the results returned from each node is `PartialResult`. On top of these results is an encapsulated `SelectResult` which is an iterator of `PartialResult`. The next `PartialResult` can be obtained by using the `next` method.

The internal implementation of the `SelectResult` can be considered to be a pipeline. TiDB can send requests to each region server concurrently and return the results to the upper layer. The order is determined by the order of the returned results from the bottom layers and the `KeepOrder` parameter of the `Select` interface.

See the related code in the [distsql](https://github.com/pingcap/tidb/tree/master/distsql) package and the [store/tikv/coprocessor.go](https://github.com/pingcap/tidb/blob/master/store/tikv/coprocessor.go) file.
