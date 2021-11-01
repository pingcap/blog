---
title: 'Transparent Huge Pages: Why We Disable It for Databases'
author: ['Wenbo Zhang']
date: 2020-12-10
summary: This post dives deep into how transparent huge pages (THP) slow down the system. You'll learn why you should disable THP to improve your database performance and how to disable it in Linux.
tags: ['Performance tuning', 'Linux']
categories: ['Engineering']
aliases: ['/blog/how-thp-slows-down-your-database-performance-and-what-to-do-about-it', '/blog/why-we-disable-linux-thp-feature-for-databases']
image: /images/blog/how-thp-slows-down-your-database-performance-banner.jpg
---

**Author:** [Wenbo Zhang](https://github.com/ethercflow) (Linux Kernel Engineer of the EE team at PingCAP)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![Disable transparent huge pages to improve database performance](media/how-thp-slows-down-your-database-performance-banner.jpg)

Linux's memory management system is transparent to the user. However, if you're not familiar with its working principles, you might meet unexpected performance issues. That's especially true for sophisticated software like databases. When databases are running in Linux, even small system variations might impact performance.

After an in-depth investigation, we found that [Transparent Huge Page](https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html) (THP), a Linux memory management feature, often slows down database performance. In this post, I'll describe how THP causes performance to fluctuate, the typical symptoms, and how to disable transparent huge pages in your Linux system.

## What are transparent huge pages

THP is an important feature of the Linux kernel. It maps page table entries to larger page sizes to reduce page faults. This improves the [translation lookaside buffer](https://en.wikipedia.org/wiki/Translation_lookaside_buffer) (TLB) hit ratio. TLB is a memory cache used by the memory management unit to improve the translation speed from virtual memory addresses to physical memory addresses.

When the application data being accessed is contiguous, THP often boosts performance. In contrast, if the memory access patterns are not contiguous, THP can't fulfill its duty, and it may even cause system instability.

Unfortunately, database workloads are known to have sparse rather than contiguous memory access. Therefore, you should disable THP for your database.

### How Linux manages its memory

To understand the harm THP can cause, let's consider how Linux manages its physical memory.

For different architectures, the Linux kernel employs different memory mapping approaches. Among them, the user space maps the memory via multi-level paging to save space, while the kernel space uses linear mapping to achieve simplicity and high efficiency.

When the kernel starts, it adds physical pages to [the buddy system](https://en.wikipedia.org/wiki/Buddy_memory_allocation). Every time the user applies for memory, the buddy system allocates the desired pages. When the user releases memory, the buddy system deallocates the pages.

To accommodate low-speed devices and various workloads, Linux divides the memory pages into anonymous pages and file-based pages. Linux uses page cache to cache files for low-speed devices. When memory is insufficient, users can employ swap cache and swappiness to specify a proportion of the two types of pages to be released.

To respond to the user's memory application as soon as possible and guarantee that the system runs normally when the memory resources are insufficient, Linux defines three watermarks: `high`, `low`, and `min`.

* If the unused physical memory is less than `low` and more than `min`, when the user applies for memory, the page replacement daemon `kswapd` asynchronously frees memory until the available physical memory is higher than `high`.
* If the asynchronous memory reclaim can't keep up with the memory application, Linux triggers the synchronous direct reclaim. In such cases, all memory-related threads synchronously take part in freeing memory. When enough memory becomes available, the threads start to get the memory space they apply for.

During the direct reclaim, if the pages are clean, the blockage caused by synchronous reclaim is short; otherwise, it might result in tens of milliseconds of latency, and, depending on the back-end devices, sometimes even seconds.

Apart from the watermarks, another mechanism may also cause direct memory reclaim. Sometimes, a thread applies for a large section of continuous memory pages. If there is enough physical memory, but it's fragmented, the kernel performs memory compaction. This might also trigger a direct memory reclaim.

To sum up, when threads apply for memory, the major causes of latency are direct memory reclaim and memory compaction. For workloads whose memory access is not very contiguous, such as databases, THP may trigger the two tasks and thus cause fluctuating performance.

## When THP causes performance fluctuation

If your system performance fluctuates, how can you be sure THP is the cause? I'd like to share three symptoms that we've found are related to THP.

### The most typical symptom: `sys cpu` rises

Based on our customer support experience, the most typical symptom of THP-caused performance fluctuation is sharply rising system CPU utilization.

In such cases, if you create an on-cpu flame graph using [perf](https://en.wikipedia.org/wiki/Perf_(Linux)), you'll see that all the service threads that are in the runnable state are performing memory compaction. In addition, the page fault exception handler is `do_huge_pmd_anonymous_page`. This means that the current system doesn't have 2 MB of contiguous physical memory and that triggers the direct memory compaction. The direct memory compaction is time-consuming, so it leads to high system CPU utilization.

### The indirect symptom: `sys load` rises

Many memory issues are not as obvious as those described above. When the system allocates or other high-level memory, it doesn't perform memory compaction directly and leave you an obvious trace. Instead, it often mixes the compaction with other tasks, such as direct memory reclaim.

Involving direct reclaim in the process makes our troubleshooting more perplexing. For example, when the unused physical memory in the normal zone is higher than the `high` watermark, the system still continuously reclaims memory. To get to the bottom of this, we need to dive deeper into the processing logic of slow memory allocation.

The slow memory allocation breaks down into four major steps:

1. Asynchronous memory compaction
2. Direct memory reclaim
3. Direct memory compaction
4. Out of memory (OOM) collection

After each step, the system tries to allocate memory. If the allocation succeeds, the system returns the allocated page and skips the remaining steps. For each allocation, the kernel provides a fragmentation index for each order in the buddy system, which indicates whether the allocation failure is caused by insufficient memory or by fragmented memory.

The fragmentation index is associated with the `/proc/sys/vm/extfrag_threshold` parameter. The closer the number is to 1,000, the more the allocation failure is related to memory fragmentation, and the kernel is more likely to perform memory compaction. The closer the number is to 0, the more the allocation failure is related to insufficient memory, and the kernel is more inclined to perform memory reclaim.

Therefore, even when the unused memory is higher than the `high` watermark, the system may also frequently reclaim memory. Because THP consumes high-level memory, it compounds the performance fluctuation caused by memory fragmentation.

To verify whether the performance fluctuation is related to memory fragmentation:

1. View the direct memory reclaim operations taken per second. Execute `sar -B` to observe `pgscand/s`. If this number is greater than 0 for a consecutive period of time, take the following steps to troubleshoot the problem.
2. Observe the memory fragmentation index. Execute `cat /sys/kernel/debug/extfrag/extfrag_index` to get the index**.** Focus on the fragmentation index of the block whose order is >= 3. If the number is close to 1,000, the fragmentation is severe; if it's close to 0, the memory is insufficient.
3. View the memory fragmentation status. Execute `cat /proc/buddyinfo` and `cat /proc/pagetypeinfo` to show the status. (Refer to the [Linux manual page](https://man7.org/linux/man-pages/man5/proc.5.html) for details.) Focus on the number of pages whose order is >= 3.

    Compared to `buddyinfo`, `pagetypeinfo` displays more detailed information grouped by migration types. The buddy system implements anti-fragmentation through migration types. Note that if all the `Unmovable` pages are grouped in order &lt; 3, the kernel slab objects have severe fragmentation. In such cases, you need to troubleshoot the specific cause of the problem using other tools.

4. For kernels that support the [Berkeley Packet Filter](https://en.wikipedia.org/wiki/Berkeley_Packet_Filter) (BPF), such as CentOS 7.6, **you may also perform quantitative analysis on the latency** using [drsnoop](https://github.com/iovisor/bcc/blob/master/tools/drsnoop_example.txt) or [compactsnoop](https://github.com/iovisor/bcc/blob/master/tools/compactsnoop_example.txt) developed by PingCAP.
5. (Optional) **Trace the `mm_page_alloc_extfrag` event with [ftrace](https://en.wikipedia.org/wiki/Ftrace)**. Due to memory fragmentation, the migration type steals physical pages from the backup migration type.

### The atypical symptom: abnormal RES usage

Sometimes, when the service starts on an AARCH64 server, dozens of gigabytes of physical memory are occupied. By viewing the `/proc/pid/smaps` file, you may see that most memory is used for THP. Because AARCH64's CentOS 7 kernel sets its page size as 64 KB, its resident memory usage is many times larger than that of the x86_64 platform.

## How to deal with THP

For applications that are not optimized to store their data contiguously, or applications that have sparse workloads, enabling THP and THP defrag is detrimental to the long-running services.

Before Linux v4.6, the kernel doesn't provide `defer` or `defer + madvise` for THP defrag. Therefore, for CentOS 7, which uses the v3.10 kernel, it is recommended to disable THP. If your applications do need THP, however, we suggest that you set THP as `madvise`, which allocates THP via the [madvise system call](https://www.man7.org/linux/man-pages/man2/madvise.2.html). Otherwise, setting THP as `never` is the best choice for your application.

To disable THP:

1. View the current THP configuration:

    ```shell
    cat /sys/kernel/mm/transparent_hugepage/enabled
    ```

2. If the value is `always`, execute the following commands:

    ```shell
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
    echo never > /sys/kernel/mm/transparent_hugepage/defrag
    ```

Note that if you restart the server, THP might be turned on again. You can write the two commands in the `.service` file and let [systemd](https://en.wikipedia.org/wiki/Systemd) manage it for you.

## Join our community

If you have any other questions about database performance tuning, or would like to share your expertise, feel free to join the [TiDB Community Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog) workspace.
