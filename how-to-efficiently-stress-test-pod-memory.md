---
title: How to Efficiently Stress Test Pod Memory
author: ['Yinghao Wang']
date: 2021-07-13
summary: Chaos Mesh provides StressChaos, a tool that allows you to inject CPU and memory stress into your Pod. Learn how to get the most of StressChaos.
tags: ['Chaos Engineering']
categories: ['Community']
image: /images/blog/how-to-efficiently-stress-test-kubernetes-pod-memory.jpg
---

**Author**: [Yinghao Wang](https://github.com/AsterNighT) (Contributor of Chaos Mesh)

**Editors:** [Ran Huang](https://github.com/ran-huang), Tom Dewan

![How to efficiently stress test Pod memory in Kubernetes](media/how-to-efficiently-stress-test-kubernetes-pod-memory.jpg)

[Chaos Mesh](https://github.com/chaos-mesh/chaos-mesh) is a cloud-native Chaos Engineering platform that orchestrates chaos on Kubernetes environments. Among its various tools, Chaos Mesh provides [StressChaos](https://chaos-mesh.org/docs/simulate-heavy-stress-on-kubernetes/), which allows you to inject CPU and memory stress into your Pod. This tool can be useful when you test or benchmark a CPU-sensitive or memory-sensitive program and want to know its behavior under pressure.

However, as we tested and used StressChaos, we found some issues in usability and performance. For example, StressChaos uses far less memory than we configured.

To correct these issues, we developed a new set of tests. In this article, I'll describe how we troubleshooted these issues and corrected them. This information might help you get the most out of StressChaos.

## Injecting stress into a target Pod

Before you continue, you need to [install Chaos Mesh](https://chaos-mesh.org/docs/production-installation-using-helm/) in your cluster.

To begin with, I'll walk you through how to inject StressChaos into a target Pod. For demonstration purposes, I'll use [hello-kubernetes](https://github.com/paulbouwer/hello-kubernetes), a demo app managed by [helm charts](https://helm.sh/). The first step is to clone the `hello-kubernetes` repo and modify the chart to give it a resource limit.

```shell
git clone [https://github.com/paulbouwer/hello-kubernetes.git](https://github.com/paulbouwer/hello-kubernetes.git)
code deploy/helm/hello-kubernetes/values.yaml # or whatever editor you prefer
```

Find the resources configuration, and modify it as follows:

```yaml
resources:
  requests:
    memory: "200Mi"
  limits:
    memory: "500Mi"
```

Before we inject StressChaos, let's see how much memory the target Pod is currently consuming. Go into the Pod and start a shell. Enter the following command with the name of your Pod:

```shell
kubectl exec -it -n hello-kubernetes hello-kubernetes-hello-world-b55bfcf68-8mln6 -- /bin/sh
```

Display a summary of memory usage by entering:

```
/usr/src/app $ free -m
/usr/src/app $ top
```

As you can see from the output below, the Pod is consuming 4,269 MB of memory:

```
/usr/src/app $ free -m
            used
Mem:          4269
Swap:            0

​/usr/src/app $ top
Mem: 12742432K used
PID PPID USER     STAT   VSZ %VSZ CPU %CPU COMMAND
   1     0 node     S     285m   2%   0   0% npm start
  18     1 node     S     284m   2%   3   0% node server.js
  29     0 node     S     1636   0%   2   0% /bin/sh
  36    29 node     R     1568   0%   3   0% top
```

`top` and `free` commands give similar answers, but those numbers don't meet our expectations. We've limited the Pod's memory usage to 500 MiBs, but now it seems to be using several GBs.

To figure out the cause, we can run a StressChaos experiment on the Pod and see what happens. Here's the YAML file we use:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: mem-stress
  namespace: chaos-testing
spec:
  mode: all
  selector:
    namespaces:
      - hello-kubernetes
  stressors:
    memory:
      workers: 4
      size: 50MiB
      options: [""]
  duration: "1h"
```

Save the above file to `memory.yaml`. Apply the chaos experiment by running:

```shell
~ kubectl apply -f memory.yaml
stresschaos.chaos-mesh.org/mem-stress created
```

Let's check the memory usage again:

```
            used
Mem:          4332
Swap:            0

Mem: 12805568K used
PID PPID USER     STAT   VSZ %VSZ CPU %CPU COMMAND
  54    50 root     R    53252   0%   1  24% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  57    52 root     R    53252   0%   0  22% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  55    53 root     R    53252   0%   2  21% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  56    51 root     R    53252   0%   3  21% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  18     1 node     S     289m   2%   2   0% node server.js
   1     0 node     S     285m   2%   0   0% npm start
  51    49 root     S    41048   0%   0   0% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  50    49 root     S    41048   0%   2   0% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  52    49 root     S    41048   0%   0   0% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  53    49 root     S    41048   0%   3   0% {stress-ng-vm} stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  49     0 root     S    41044   0%   0   0% stress-ng --vm 4 --vm-keep --vm-bytes 50000000
  29     0 node     S     1636   0%   3   0% /bin/sh
  48    29 node     R     1568   0%   1   0% top
```

You can see that `stress-ng` instances are injected into the Pod. There is a 60 MiB rise in the Pod, which we didn't expect. The [`stress-ng` documentation](https://manpages.ubuntu.com/manpages/artful/man1/stress-ng.1.html#:~:text=is%20not%20available.-,--vm-bytes%20N,-mmap%20N%20bytes) indicates that the increase should be 200 MiB (4 * 50 MiB).

Let's increase the stress by changing the memory stress from 50 MiB to 3,000 MiB. This should break the Pod's memory limit. I'll delete the chaos experiment, modify the memory size, and reapply it.

And then, boom! The shell exits with code 137. A moment later, I reconnect to the container, and the memory usage returns to normal. No `stress-ng` instances are found! What happened?

## Why does StressChaos disappear?

In the above chaos experiment, we saw abnormal behaviors: the memory usage doesn't add up, and the Shell exits. In this section, we are going to find out all the causes.

Kubernetes limits the container memory usage through the [cgroup](https://man7.org/linux/man-pages/man7/cgroups.7.html) mechanism. To see the 500 MiB limit in our Pod, go to the container and enter:

```shell
/usr/src/app $ cat /sys/fs/cgroup/memory/memory.limit_in_bytes
524288000
```

The output is displayed in bytes and translates to 500 \* 1024 \* 1024 (500 MiB).

Requests are used only for scheduling where to place the Pod. The Pod does not have a memory limit or request, but it can be seen as the sum of all its containers.

So, we've been making mistakes since the very beginning. `free` and `top` are not "cgrouped." They rely on `/proc/meminfo` (procfs) for data. Unfortunately, `/proc/meminfo` are old, so old that they predate cgroup. They provide you with _host_ memory information instead of the container memory info.

Bearing that in mind, let's start all over again and see what memory usage we get this time.

To get the "cgrouped" memory usage, enter:

```shell
/usr/src/app $ cat /sys/fs/cgroup/memory/memory.usage_in_bytes
39821312
```

Apply the 50 MiB StressChaos, and yield the following result:

```shell
/usr/src/app $ cat /sys/fs/cgroup/memory/memory.usage_in_bytes
93577216
```

That is about 51 MiB more memory usage than without StressChaos.

Next question: why did our shell exit? Exit code 137 indicates "failure as container received SIGKILL." That leads us to check the Pod. Pay attention to the Pod state and events:

```shell
~ kubectl describe pods -n hello-kubernetes
......
  Last State:     Terminated
    Reason:       Error
    Exit Code:    1
......
Events:
  Type     Reason     Age                 From               Message
  ----     ------     ----                 ----               -------
......
  Warning Unhealthy 10m (x4 over 16m)   kubelet           Readiness probe failed: Get "http://10.244.1.19:8080/": context deadline exceeded (Client.Timeout exceeded while awaiting headers)
  Normal   Killing   10m (x2 over 16m)   kubelet           Container hello-kubernetes failed liveness probe, will be restarted
......
```

The events tell us why the shell crashed. `hello-kubernetes` has a liveness probe. When the container memory is reaching the limit, the application starts to fail, and Kubernetes decides to terminate and restart the Pod. When the Pod restarts, StressChaos stops. By now, you can say that the StressChaos experiment works fine: it finds a vulnerability in your Pod. You could now fix it, and reapply the chaos.

Everything seems perfect now—except for one thing. Why do four 50 MiB vm workers result in 51 MiB in total? The answer will not reveal itself until we go into the [stress-ng source code](https://github.com/ColinIanKing/stress-ng/blob/819f7966666dafea5264cf1a2a0939fd344fcf08/stress-vm.c#L2074):

```c
vm_bytes /= args->num_instances;
```

Oops! So the document is wrong. The multiple vm workers take up the total size specified, rather than `mmap` that much memory per worker. Finally, we get an answer for everything. In the following sections, we'll discuss some other situations involving memory stress.

## What if there was no liveness probe?

To figure out what happens if there is no liveness probe, let's delete the probes and try again.

Find the following lines in `deploy/helm/hello-kubernetes/templates/deployment.yaml` and delete them.

```yaml
livenessProbe:
  httpGet:
    path: /
    port: http
readinessProbe:
  httpGet:
    path: /
    port: http
```

After that, upgrade the deployment.

Interesting enough, in this scenario, the memory usage goes up continuously, and then drops sharply; it goes back and forth. What is happening now? Let's check the kernel log. Pay attention to the last two lines.

```
/usr/src/app $ dmesg
...
[189937.362908] [ pid ]   uid tgid total_vm     rss nr_ptes swapents oom_score_adj name
[189937.363092] [441060]  1000 441060    63955     3791      80     3030           988 node
[189937.363145] [443265]     0 443265   193367    84215     197     9179          1000 stress-ng-vm
...
[189937.363148] Memory cgroup out of memory: Kill process 443160 (stress-ng-vm) score 1272 or sacrifice child
[189937.363186] Killed process 443160 (stress-ng-vm), UID 0, total-vm:773468kB, anon-rss:152704kB, file-rss:164kB, shmem-rss:0kB
```

It's clear from the output that the `stress-ng-vm` process is being killed because of out of memory (OOM) errors.

If processes can't get the memory they want, they are very likely to fail. Instead of waiting for processes to crash, it'd be better if you kill some of them to release more memory. The OOM killer stops processes in an order and tries to recover the most memory while causing the least trouble. For detailed information on this process, see [this introduction](https://lwn.net/Articles/391222/) to OOM killer.

Looking at the output above, you can see that `node`, our application process that should never be terminated, has an `oom_score_adj` of 988. That is quite dangerous, because it is the process with the highest score to get killed.

To stop the OOM killer from killing a specific process, you can try a simple trick. When you create a Pod, assign the Pod [a Quality of Service (QoS) class](https://kubernetes.io/docs/tasks/configure-pod-container/quality-service-pod/). Generally, if you create a Pod with precisely-specified resource requests, it is classified as a `Guaranteed` Pod. OOM killers do not kill containers in a Guaranteed Pod if there are other options to kill. These options include non-`Guaranteed` Pods and `stress-ng` workers. A Pod with no resource requests is marked as `BestEffort`, and is likely to be killed by the OOM killer at first priority.

That's all for the tour. When you inject StressChaos into your Pods, we have two suggestions:

* Do not use `free` and `top` to assess memory in containers.
* Be careful when you assign resource limits to your Pod, and select the right QoS.

In the future, we'll create a more detailed StressChaos document.

<div class="trackable-btns">
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('How to Efficiently Stress Test Pod Memory', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
  </div>

## Dive deeper into Kubernetes memory management

Kubernetes tries to evict Pods that use too much memory (but not more memory than their limits). Kubernetes gets your Pod memory usage from `/sys/fs/cgroup/memory/memory.usage_in_bytes` and subtracts it by the `total_inactive_file` line in `memory.stat`.

Keep in mind that Kubernetes **does not** support swap. Even if you have a node with swap enabled, Kubernetes creates containers with `swappiness=0`, which means swap is actually disabled. That is mainly for performance concerns.

`memory.usage_in_bytes` equals `resident set` plus `cache`, and `total_inactive_file` is memory in `cache` that the OS can retrieve when the memory is running out. `memory.usage_in_bytes - total_inactive_file` is called `working_set`. You can get this `working_set` value by `kubectl top pod <your pod> --containers`. Kubernetes uses this value to decide whether or not to evict your Pods.

Kubernetes periodically inspects memory usage. If a container's memory usage increases too quickly or the container cannot be evicted, the OOM killer is invoked. Kubernetes has its way of protecting its own process, so the OOM killer always picks the container. When a container is killed, it may or may not be restarted, depending on your restart policy. If it is killed, when you execute `kubectl describe pod <your pod>`, you will see it is restarted and the reason is `OOMKilled`.

Another thing worth mentioning is the kernel memory. Since v1.9, Kubernetes enables kernel memory support by default. It is also a feature of cgroup memory subsystems. You can limit container kernel memory usage. Unfortunately, this causes a cgroup leak on kernel versions up to v4.2. You can either upgrade your kernel to v4.3 or disable the feature.

## How we implement StressChaos

StressChaos is a simple way to test your container's behavior when it is low on memory. StressChaos utilizes a powerful tool named `stress-ng` to allocate memory and continue writing into the allocated memory. Because containers have memory limits and container limits are bound to a cgroup, we must find a way to run `stress-ng` in a specific cgroup. Luckily, this part is easy. With enough privileges, we can assign any process to any cgroup by writing to files in `/sys/fs/cgroup/`.

If you are interested in Chaos Mesh and would like to help us improve it, you're welcome to join [our Slack channel](https://slack.cncf.io/) (#project-chaos-mesh)! Or submit your pull requests or issues to our [GitHub repository](https://github.com/chaos-mesh/chaos-mesh).
