---
title: 'Why We Switched from bcc-tools to libbpf-tools for BPF Performance Analysis'
author: ['Wenbo Zhang']
date: 2020-12-03
summary: Libbpf + BPF CO-RE is better than BCC. It greatly reduces storage space and runtime overhead, and it improves programmers' deployment and development experience.
tags: ['Performance tuning']
categories: ['Engineering']
image: /images/blog/bcc-vs-libbpf-bpf-performance-analysis.jpg
---

![BPF Linux, BPF performance tools](media/bcc-vs-libbpf-bpf-performance-analysis.jpg)

Distributed clusters might encounter performance problems or unpredictable failures, especially when they are running in the cloud. Of all the kinds of failures, kernel failures may be the most difficult to analyze and simulate. 

A practical solution is [Berkeley Packet Filter](https://en.wikipedia.org/wiki/Berkeley_Packet_Filter) (BPF), a highly flexible, efficient virtual machine that runs in the Linux kernel. It allows bytecode to be safely executed in various hooks, which exist in a variety of Linux kernel subsystems. BPF is mainly used for networking, tracing, and security.

Based on BPF, there are two development modes:

* The [BPF Compiler Collection](https://github.com/iovisor/bcc) (BCC) toolkit offers many useful resources and examples to construct effective kernel tracing and manipulation programs. However, it has disadvantages. 
* libbpf + BPF CO-RE (Compile Once – Run Everywhere) is a different development and deployment mode than the BCC framework. **It greatly reduces storage space and runtime overhead, which enables BPF to support more hardware environments, and it optimizes programmers' development experience.**

In this post, I'll describe why libbpf-tools, a collection of applications based on the libbpf + BPF CO-RE mode, is a better solution than bcc-tools and how we're using libbpf-tools at [PingCAP](https://pingcap.com/).

## Why libbpf + BPF CO-RE is better than BCC

### BCC vs. libbpf + BPF CO-RE

BCC embeds LLVM or Clang to rewrite, compile, and load BPF programs. Although it does its best to simplify BPF developers' work, it has these drawbacks:

* It uses the Clang front-end to modify user-written BPF programs. When a problem occurs, it's difficult to find the problem and figure out a solution. 
* You must remember naming conventions and automatically generated tracepoint structs. 
* Because the libbcc library contains a huge LLVM or Clang library, when you use it, you might encounter some issues:
* When a tool starts, it takes many CPU and memory resources to compile the BPF program. If it runs on a server that lacks system resources, it might trigger a problem.
* BCC depends on kernel header packages, which you must install on each target host. If you need unexported content in the kernel, you must manually copy and paste the type definition into the BPF code.
* Because BPF programs are compiled during runtime, many simple compilation errors can only be detected at runtime. This affects your development experience.

By contrast, BPF CO-RE has these advantages:

* When you implement BPF CO-RE, you can directly use the libbpf library provided by kernel developers to develop BPF programs. The development method is the same as writing ordinary C user-mode programs: one compilation generates a small binary file. 
* Libbpf acts like a BPF program loader and relocates, loads, and checks BPF programs. BPF developers only need to focus on the BPF programs' correctness and performance. 
* This approach minimizes overhead and removes huge dependencies, which makes the overall development process smoother.

For more details, see [Why libbpf and BPF CO-RE?](https://facebookmicrosites.github.io/bpf/blog/2020/02/20/bcc-to-libbpf-howto-guide.html#why-libbpf-and-bpf-co-re).

### Performance comparison

Performance optimization master [Brendan Gregg](https://github.com/brendangregg) used libbpf + BPF CO-RE to convert a BCC tool and compared their performance data. [He said](https://github.com/iovisor/bcc/pull/2778#issuecomment-594202408): "As my colleague Jason pointed out, **the memory footprint of opensnoop as CO-RE is much lower than opensnoop.py**. **9 Mbytes for CO-RE vs 80 Mbytes for Python**."

According to his research, compared with BCC at runtime, libbpf + BPF CO-RE reduced memory overhead by nearly nine times, which greatly benefits servers with scarce physical memory.

## How we're using libbpf-tools at PingCAP

At PingCAP, we've been following BPF and its community development for a long time. In the past, every time we added a new machine, we had to install a set of BCC dependencies on it, which was troublesome. After [Andrii Nakryiko](https://github.com/anakryiko) (the libbpf + BPF CO-RE project's leader) added the first libbpf-tools to the BCC project, we did our research and switched from bcc-tools to libbpf-tools. Fortunately, during the switch, we got guidance from him, Brendan, and [Yonghong Song](https://github.com/yonghong-song) (the BTF project's leader). We've converted 18 BCC or bpftrace tools to [libbpf + BPF CO-RE](https://github.com/iovisor/bcc/tree/master/libbpf-tools), and we're using them in our company. 

For example, when we analyzed the I/O performance of a specific workload, we used multiple performance analysis tools at the block layer:

<table>
  <tr>
   <td><strong>Task</strong>
   </td>
   <td><strong>Performance analysis tool</strong>
   </td>
  </tr>
  <tr>
   <td>Check I/O requests' latency distribution
   </td>
   <td><a href="https://github.com/iovisor/bcc/blob/master/libbpf-tools/biolatency.bpf.c">./biolatency -d nvme0n1</a>
   </td>
  </tr>
  <tr>
   <td>Analyze I/O mode
   </td>
   <td><a href="https://github.com/iovisor/bcc/blob/master/libbpf-tools/biopattern.bpf.c">./biopattern -T 1 -d 259:0</a>
   </td>
  </tr>
  <tr>
   <td>Check the request size distribution diagram when the task sent physical I/O requests
   </td>
   <td><a href="https://github.com/iovisor/bcc/blob/master/libbpf-tools/bitesize.bpf.c">./bitesize -c fio -T</a>
   </td>
  </tr>
  <tr>
   <td>Analyze each physical I/O
   </td>
   <td><a href="https://github.com/iovisor/bcc/blob/master/libbpf-tools/biosnoop.bpf.c">./biosnoop -d nvme0n1</a>
   </td>
  </tr>
</table>

The analysis results helped us optimize I/O performance. We're also exploring whether the scheduler-related libbpf-tools are helpful for tuning the [TiDB database](https://docs.pingcap.com/tidb/stable/). 

These tools are universal: feel free to give them a try. In the future, we'll implement more tools based on libbpf-tools. If you'd like to learn more about our experience with these tools, you can join the [TiDB community on Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog).
