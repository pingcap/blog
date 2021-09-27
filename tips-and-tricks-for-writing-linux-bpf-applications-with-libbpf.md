---
title: Tips and Tricks for Writing Linux BPF Applications with libbpf
author: ['Wenbo Zhang']
date: 2020-12-14
summary: Compared to BCC, the libbpf + BPF CO-RE solution greatly reduces storage space and runtime overhead. That's why we switched from bcc-tools to libbpf-tools. This post introduces some tips and tricks for writing BPF applications with libbpf.
tags: ['Performance tuning', 'Linux']
categories: ['Engineering']
image: /images/blog/linux-bpf-performance-analysis-tools.jpg
---

**Author:** [Wenbo Zhang](https://github.com/ethercflow) (Linux Kernel Engineer of the EE team at PingCAP)

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![Linux BPF performance analysis tools](media/linux-bpf-performance-analysis-tools.jpg)

At the beginning of 2020, when I used the BCC tools to analyze our database performance bottlenecks, and pulled the code from the GitHub, I accidentally discovered that there was an additional [libbpf-tools](https://github.com/iovisor/bcc/tree/master/libbpf-tools) directory in the BCC project. I had read an article on [BPF portability](https://facebookmicrosites.github.io/bpf/blog/2020/02/19/bpf-portability-and-co-re.html) and another on [BCC to libbpf conversion](https://facebookmicrosites.github.io/bpf/blog/2020/02/20/bcc-to-libbpf-howto-guide.html), and I used what I learned to convert my previously submitted bcc-tools to libbpf-tools. I ended up converting nearly 20 tools. (See [Why We Switched from bcc-tools to libbpf-tools for BPF Performance Analysis](https://pingcap.com/blog/why-we-switched-from-bcc-tools-to-libbpf-tools-for-bpf-performance-analysis).)

During this process, I was fortunate to get a lot of help from [Andrii Nakryiko](https://github.com/anakryiko) (the libbpf + BPF CO-RE project's leader). It was fun and I learned a lot. In this post, I'll share my experience about writing Berkeley Packet Filter (BPF) applications with libbpf. I hope this article is helpful to people who are interested in libbpf and inspires them to further develop and improve BPF applications with libbpf.

Before you read further, however, consider reading [these posts for important background information:](https://facebookmicrosites.github.io/bpf/blog/2020/02/19/bpf-portability-and-co-re.html)

* [BPF Portability and CO-RE](https://facebookmicrosites.github.io/bpf/blog/2020/02/19/bpf-portability-and-co-re.html)
* [HOWTO: BCC to libbpf conversion](https://facebookmicrosites.github.io/bpf/blog/2020/02/20/bcc-to-libbpf-howto-guide.html)
* [Building BPF applications with libbpf-boostrap](https://nakryiko.com/posts/libbpf-bootstrap/)

This article assumes that you've already read these posts, so there won't be any systematic descriptions. Instead, I'll offer you some tips for certain parts of the program.

## Program skeleton

### Combining the open and load phases

If your BPF code doesn't need any runtime adjustments (for example, adjusting the map size or setting an extra configuration), you can call `<name>__open_and_load()` to combine the two phases into one. This makes our code look more compact. For example:

{{< copyable "" >}}

```c
obj = readahead_bpf__open_and_load();
if (!obj) {
        fprintf(stderr, "failed to open and/or load BPF object\n");
        return 1;
}
err = readahead_bpf__attach(obj);
```

You can see the complete code in [readahead.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/readahead.c#L75).

### Selective attach

By default, `<name>__attach()` attaches all auto-attachable BPF programs. However, sometimes you might want to selectively attach the corresponding BPF program according to the command line parameters. In this case, you can call `bpf_program__attach()` instead. For example:

{{< copyable "" >}}

```c
err = biolatency_bpf__load(obj);
[...]
if (env.queued) {
        obj->links.block_rq_insert =
                bpf_program__attach(obj->progs.block_rq_insert);
        err = libbpf_get_error(obj->links.block_rq_insert);
        [...]
}
obj->links.block_rq_issue =
        bpf_program__attach(obj->progs.block_rq_issue);
err = libbpf_get_error(obj->links.block_rq_issue);
[...]
```

You can see the complete code in [biolatency.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/biolatency.c#L264).

### Custom load and attach

Skeleton is suitable for almost all scenarios, but there is a special case: perf events. In this case, instead of using links from `struct <name>__bpf`, you need to define an array: `struct bpf_link *links[]`. The reason is that `perf_event` needs to be opened separately on each CPU.

After this, open and attach `perf_event` by yourself:

{{< copyable "" >}}

```c
static int open_and_attach_perf_event(int freq, struct bpf_program *prog,
                                struct bpf_link *links[])
{
        struct perf_event_attr attr = {
                .type = PERF_TYPE_SOFTWARE,
                .freq = 1,
                .sample_period = freq,
                .config = PERF_COUNT_SW_CPU_CLOCK,
        };
        int i, fd;

        for (i = 0; i < nr_cpus; i++) {
                fd = syscall(__NR_perf_event_open, &attr, -1, i, -1, 0);
                if (fd < 0) {
                        fprintf(stderr, "failed to init perf sampling: %s\n",
                                strerror(errno));
                        return -1;
                    }
                links[i] = bpf_program__attach_perf_event(prog, fd);
                if (libbpf_get_error(links[i])) {
                        fprintf(stderr, "failed to attach perf event on cpu: "
                                "%d\n", i);
                        links[i] = NULL;
                        close(fd);
                        return -1;
                }
        }

        return 0;
}
```

Finally, during the tear down phase, remember to destroy each link in the `links` and then destroy `links`.

You can see the complete code in [runqlen.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/runqlen.c).

### Multiple handlers for the same event

Starting in [v0.2](https://github.com/libbpf/libbpf/releases/tag/v0.2), libbpf supports multiple entry-point BPF programs within the same executable and linkable format (ELF) section. Therefore, you can attach multiple BPF programs to the same event (such as tracepoints or kprobes) without worrying about ELF section name clashes. For details, see [Add libbpf full support for BPF-to-BPF calls](https://patchwork.ozlabs.org/project/netdev/cover/20200903203542.15944-1-andriin@fb.com/). Now, you can naturally define multiple handlers for an event like this:

{{< copyable "" >}}

```c
SEC("tp_btf/irq_handler_entry")
int BPF_PROG(irq_handler_entry1, int irq, struct irqaction *action)
{
            [...]
}

SEC("tp_btf/irq_handler_entry")
int BPF_PROG(irq_handler_entry2)
{
            [...]
}
```

You can see the complete code in [hardirqs.bpf.c](https://github.com/ethercflow/libbpf-bootstrap/blob/master/src/hardirqs.bpf.c) (built with [libbpf-bootstrap](https://github.com/libbpf/libbpf-bootstrap)).

If your libbpf version is earlier than v2.0, to define multiple handlers for an event, you have to use multiple program types, for example:

{{< copyable "" >}}

```c
SEC("tracepoint/irq/irq_handler_entry")
int handle__irq_handler(struct trace_event_raw_irq_handler_entry *ctx)
{
        [...]
}

SEC("tp_btf/irq_handler_entry")
int BPF_PROG(irq_handler_entry)
{
        [...]
}
```

You can see the complete code in [hardirqs.bpf.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/hardirqs.bpf.c).

<div class="trackable-btns">
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Tips and Tricks for Writing Linux BPF Applications with libbpf', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
  </div>

## Maps

### Reduce pre-allocation overhead

Beginning in Linux 4.6, BPF hash maps perform memory pre-allocation by default and introduce the `BPF_F_NO_PREALLOC` flag. The motivation for doing so is to avoid kprobe + bpf deadlocks. The community had tried other solutions, but in the end, pre-allocating all the map elements was the simplest solution and didn't affect the user space visible behavior.

When full map pre-allocation is too memory expensive, define the map with the `BPF_F_NO_PREALLOC` flag to keep old behavior. For details, see [bpf: map pre-alloc](https://lwn.net/Articles/679074/). When the map size is not large (such as `MAX_ENTRIES` = 256), this flag is not necessary. `BPF_F_NO_PREALLOC` is slower.

Here is an example:

{{< copyable "" >}}

```c
struct {
        __uint(type, BPF_MAP_TYPE_HASH);
        __uint(max_entries, MAX_ENTRIES);
        __type(key, u32);
        __type(value, u64);
        __uint(map_flags, BPF_F_NO_PREALLOC);
} start SEC(".maps");
```

You can see many cases in [libbpf-tools](https://github.com/iovisor/bcc/tree/master/libbpf-tools).

### Determine the map size at runtime

One advantage of libbpf-tools is that it is portable, so the maximum space required for the map may be different for different machines. In this case, you can define the map without specifying the size and resize it before load. For example:

In `<name>.bpf.c`, define the map as:

{{< copyable "" >}}

```c
struct {
        __uint(type, BPF_MAP_TYPE_HASH);
        __type(key, u32);
        __type(value, u64);
} start SEC(".maps");
```

After the open phase, call `bpf_map__resize()`. For example:

{{< copyable "" >}}

``` c
struct cpudist_bpf *obj;

[...]
obj = cpudist_bpf__open();
bpf_map__resize(obj->maps.start, pid_max);
```

You can see the complete code in [cpudist.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/cpudist.c#L223).

### Per-CPU

When you select the map type, if multiple events are associated and occur on the same CPU, using a per-CPU array to track the timestamp is much simpler and more efficient than using a hashmap. However, you must be sure that the kernel doesn't migrate the process from one CPU to another between two BPF program invocations. So you can't always use this trick. The following example analyzes soft interrupts, and it meets both these conditions:

{{< copyable "" >}}

```c
struct {
        __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
        __uint(max_entries, 1);
        __type(key, u32);
        __type(value, u64);
} start SEC(".maps");

SEC("tp_btf/softirq_entry")
int BPF_PROG(softirq_entry, unsigned int vec_nr)
{
        u64 ts = bpf_ktime_get_ns();
        u32 key = 0;

        bpf_map_update_elem(&start, &key, &ts, 0);
        return 0;
}

SEC("tp_btf/softirq_exit")
int BPF_PROG(softirq_exit, unsigned int vec_nr)
{
        u32 key = 0;
        u64 *tsp;

        [...]
        tsp = bpf_map_lookup_elem(&start, &key);
        [...]
}
```

You can see the complete code in [softirqs.bpf.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/softirqs.bpf.c).

## Global variables

Not only can you use global variables to customize BPF program logic, you can use them instead of maps to make your program simpler and more efficient. Global variables can be any size. You just need to set global variables to be a fixed size (or at least with a bounded maximum size if you don't mind wasting some memory).

For example:

Because the number of SOFTIRQ types is fixed, you can define global arrays to save counts and histograms in `softirq.bpf.c`:

{{< copyable "" >}}

```c
__u64 counts[NR_SOFTIRQS] = {};
struct hist hists[NR_SOFTIRQS] = {};
```

Then, you can traverse the array directly in user space:

{{< copyable "" >}}

```c
static int print_count(struct softirqs_bpf__bss *bss)
{
        const char *units = env.nanoseconds ? "nsecs" : "usecs";
        __u64 count;
        __u32 vec;

        printf("%-16s %6s%5s\n", "SOFTIRQ", "TOTAL_", units);

        for (vec = 0; vec < NR_SOFTIRQS; vec++) {
                count = __atomic_exchange_n(&bss->counts[vec], 0,
                                        __ATOMIC_RELAXED);
                if (count > 0)
                        printf("%-16s %11llu\n", vec_names[vec], count);
        }

        return 0;
}
```

You can see the complete code in [softirqs.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/softirqs.c)

## Watch out for directly accessing fields through pointers

As you know from the [BPF Portability and CO-RE](https://facebookmicrosites.github.io/bpf/blog/2020/02/19/bpf-portability-and-co-re.html#reading-kernel-structures-fields) blog post, the libbpf + `BPF_PROG_TYPE_TRACING` approach gives you a smartness of BPF verifier. It understands and tracks BTF natively and allows you to follow pointers and read kernel memory directly (and safely). For example:

{{< copyable "" >}}

```c
u64 inode = task->mm->exe_file->f_inode->i_ino;
```

This is very cool. However, when you use such expressions in conditional statements, there is a bug that this branch is optimized away in some kernel versions. In this case, until [bpf: fix an incorrect branch elimination by verifier](https://www.spinics.net/lists/bpf/msg21897.html) is widely backported, please use `BPF_CORE_READ` for kernel compatibility. You can find an example in [biolatency.bpf.c](https://github.com/iovisor/bcc/blob/master/libbpf-tools/biolatency.bpf.c#L63):

{{< copyable "" >}}

```c
SEC("tp_btf/block_rq_issue")
int BPF_PROG(block_rq_issue, struct request_queue *q, struct request *rq)
{
        if (targ_queued && BPF_CORE_READ(q, elevator))
                return 0;
        return trace_rq_start(rq);
}
```

You can see even though it's a `tp_btf` program and `q->elevator` will be faster, I have to use `BPF_CORE_READ(q, elevator)` instead.

## Conclusion

This article introduced some tips for writing BPF programs with libbpf. You can find many practical examples from [libbpf-tools](https://github.com/iovisor/bcc/tree/master/libbpf-tools) and [bpf](https://github.com/torvalds/linux/tree/master/tools/testing/selftests/bpf). If you have any questions, you can join the [TiDB community on Slack](https://slack.tidb.io/invite?team=tidb-community&channel=everyone&ref=pingcap-blog) and send us your feedback.
