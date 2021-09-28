---
title: 'TiDB on Arm-based Kubernetes Cluster Achieves Up to 25% Better Price-Performance Ratio than x86'
author: ['Ron Xing']
date: 2021-03-10
summary: Running TiDB on EKS clusters with Graviton processors offers up to 25% better price-performance ratio compared to an x86-based cluster. This article discusses the benchmark tests we ran.
tags: ['Benchmark']
categories: ['Product']
image: /images/blog/tidb-on-eks-arm-vs-x86-benchmark.jpg
aliases: ['/blog/tidb-on-arm-based-k8s-cluster-x86-performance-at-15-percent-lower-cost/', '/blog/tidb-on-arm-based-k8s-cluster-is-15-percent-cheaper-than-x86-with-same-performance/']
---

**Author:** Ron Xing (Customer Support Engineer at PingCAP)

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![TiDB on EKS Arm vs. x86 benchmark](media/tidb-on-eks-arm-vs-x86-benchmark.jpg)

## Benchmark purpose

The following tests compare the performance of [TiDB](https://docs.pingcap.com/tidb/stable/), a MySQL compatible NewSQL database, running on an Arm-based Amazon Elastic Kubernetes Service (EKS) cluster and on an x86-based EKS cluster. The tests use an Online Transactional Processing (OLTP) workload, and the benchmarking tools are TPC-C and sysbench. For more information on the inspiration of the benchmark, please refer to [AWS Startups Blog](https://aws.amazon.com/blogs/startups/achieve-better-price-to-performance-for-tidb-graviton2-processors/).

## Benchmark environment

The test used two EKS clusters with the following instance types and topology.

### Instance types

The following table summarizes all the EC2 instances we used in the EKS clusters as well as the benchmark node.

<table>
  <tr>
   <td><strong>Instance size (CPU Architecture)</strong>
   </td>
   <td><strong>vCPUs</strong>
   </td>
   <td><strong>Memory (GiB)</strong>
   </td>
   <td><strong>Instance storage (GB)</strong>
   </td>
   <td><strong>Network bandwidth (Gbps)</strong>
   </td>
   <td><strong>EBS bandwidth (Mbps)</strong>
   </td>
  </tr>
  <tr>
   <td>c6g.large(Arm)
   </td>
   <td>4
   </td>
   <td>8
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>c6g.2xlarge(Arm)
   </td>
   <td>8
   </td>
   <td>16
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>r6g.2xlarge(Arm)
   </td>
   <td>8
   </td>
   <td>64
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>c5.large(x86)
   </td>
   <td>4
   </td>
   <td>8
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>c5.2xlarge(x86)
   </td>
   <td>8
   </td>
   <td>16
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>r5.2xlarge(x86)
   </td>
   <td>8
   </td>
   <td>64
   </td>
   <td>EBS-only
   </td>
   <td>Up to 10
   </td>
   <td>Up to 4,750
   </td>
  </tr>
  <tr>
   <td>c5.4xlarge(x86)
   </td>
   <td>16
   </td>
   <td>32
   </td>
   <td>EBS-only
   </td>
   <td>10
   </td>
   <td>4,750
   </td>
  </tr>
</table>

### Storage types

The following table summarizes the disk that we used for different components.

<table>
  <tr>
   <td><strong>Service type</strong>
   </td>
   <td><strong>Storage</strong>
   </td>
   <td><strong>Size (GB)</strong>
   </td>
   <td><strong>IOPS</strong>
   </td>
   <td><strong>Throughput (MiB/s)</strong>
   </td>
   <td><strong>Instances</strong>
   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>EBS gp3
   </td>
   <td>1,000
   </td>
   <td>16,000
   </td>
   <td>600
   </td>
   <td>3
   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>EBS gp2
   </td>
   <td>50
   </td>
   <td>150
   </td>
   <td>128
   </td>
   <td>1
   </td>
  </tr>
  <tr>
   <td>TPC-C/sysbench
   </td>
   <td>EBS gp3
   </td>
   <td>1,500
   </td>
   <td>16,000
   </td>
   <td>1,000
   </td>
   <td>1
   </td>
  </tr>
</table>

### Topology

We used one c5.4xlarge EC2 instance as a benchmark node where TPC-C and sysbench are deployed.

Each EKS cluster consists of seven worker nodes and one admin (control plane) node. Seven worker nodes serve as dedicated TiDB, TiKV, and PD nodes.

To better understand the role of each component and architecture diagram, please refer to [AWS Startups Blog](https://aws.amazon.com/blogs/startups/achieve-better-price-to-performance-for-tidb-graviton2-processors/).

<table>
  <tr>
   <td><strong>Cluster/processor</strong>
   </td>
   <td><strong>Service type</strong>
   </td>
   <td><strong>EC2 type</strong>
   </td>
   <td><strong>Instances</strong>
   </td>
  </tr>
  <tr>
   <td rowspan="4" >Cluster 1: Graviton2 Arm
   </td>
   <td>TiDB
   </td>
   <td>c6g.2xlarge
   </td>
   <td>3
   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>r6g.2xlarge
   </td>
   <td>3
   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>c6g.large
   </td>
   <td>1
   </td>
  </tr>
  <tr>
   <td>Admin node
   </td>
   <td>c6g.large
   </td>
   <td>1
   </td>
  </tr>
  <tr>
   <td rowspan="4" >Cluster 2: Intel Xeon Platinum 8000 series
   </td>
   <td>TiDB
   </td>
   <td>c5.2xlarge
   </td>
   <td>3
   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>r5.2xlarge
   </td>
   <td>3
   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>c5.large
   </td>
   <td>1
   </td>
  </tr>
  <tr>
   <td>Admin node
   </td>
   <td>c5.large
   </td>
   <td>1
   </td>
  </tr>
</table>

### Software version

The TiDB cluster software versions and the sysbench tool version are listed below.

<table>
  <tr>
   <td><strong>Service type</strong>
   </td>
   <td><strong>Software version</strong>
   </td>
  </tr>
  <tr>
   <td>TiDB
   </td>
   <td>v4.0.10
   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>v4.0.10
   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>v4.0.10
   </td>
  </tr>
  <tr>
   <td>TPC-C (embedded with TiUP)
   </td>
   <td>v1.0.8
   </td>
  </tr>
  <tr>
   <td>sysbench
   </td>
   <td>v1.0.20
   </td>
  </tr>
</table>

## Cost

In the following cost examples:

* Cost calculations are based on the on-demand rate for instances in the **US West (Oregon)** and **Asia Pacific (Singapore)** regions in US dollars (USD) per month.
* Monthly calculations are based on 730 hours of usage per month.

### Storage

In the following table, the total cost per month includes a daily snapshot.

<table>
  <tr>
   <td><strong>Volume type</strong>
   </td>
   <td><strong>Size (GB)</strong>
   </td>
   <td><strong>IOPS</strong>
   </td>
   <td><strong>Throughput (MiB/s)</strong>
   </td>
   <td><strong>Instances </strong>
   </td>
   <td><strong>Monthly cost (US)</strong>
   </td>
   <td><strong>Monthly cost (APAC)</strong>
   </td>
  </tr>
  <tr>
   <td>gp3
   </td>
   <td>1,000
   </td>
   <td><p style="text-align: right">
16,000</p>

   </td>
   <td><p style="text-align: right">
600 </p>

   </td>
   <td><p style="text-align: right">
3</p>

   </td>
   <td><p style="text-align: right">
648.27</p>

   </td>
   <td><p style="text-align: right">
746.58</p>

   </td>
  </tr>
  <tr>
   <td>gp2
   </td>
   <td>50
   </td>
   <td><p style="text-align: right">
100</p>

   </td>
   <td><p style="text-align: right">
128 </p>

   </td>
   <td><p style="text-align: right">
1</p>

   </td>
   <td><p style="text-align: right">
9.75</p>

   </td>
   <td><p style="text-align: right">
10.75</p>

   </td>
  </tr>
</table>

### EC2

We used the following Graviton2 Arm processor based instances. Note that unit prices are based on the rate in both the US region and the APAC region.

<table>
  <tr>
   <td rowspan="2" ><strong>Service type</strong>
   </td>
   <td rowspan="2" ><strong>EC2 type</strong>
   </td>
   <td rowspan="2" ><strong>Instances</strong>
   </td>
   <td colspan="2" ><strong>US region</strong>
   </td>
   <td colspan="2" ><strong>APAC region</strong>
   </td>
  </tr>
  <tr>
   <td><strong>Unit price (USD/hr)</strong>
   </td>
   <td><strong>Monthly cost</strong>
   </td>
   <td><strong>Unit price (USD/hr) </strong>
   </td>
   <td><strong>Monthly cost </strong>
   </td>
  </tr>
  <tr>
   <td>TiDB
   </td>
   <td>c6g.2xlarge
   </td>
   <td><p style="text-align: right">
3</p>

   </td>
   <td><p style="text-align: right">
0.272</p>

   </td>
   <td><p style="text-align: right">
595.68</p>

   </td>
   <td><p style="text-align: right">
0.3136</p>

   </td>
   <td><p style="text-align: right">
686.78</p>

   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>r6g.2xlarge
   </td>
   <td><p style="text-align: right">
3</p>

   </td>
   <td><p style="text-align: right">
0.4032</p>

   </td>
   <td><p style="text-align: right">
883.01</p>

   </td>
   <td><p style="text-align: right">
0.4864</p>

   </td>
   <td><p style="text-align: right">
1,065.21</p>

   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>c6g.large
   </td>
   <td><p style="text-align: right">
1</p>

   </td>
   <td><p style="text-align: right">
0.068</p>

   </td>
   <td><p style="text-align: right">
49.64</p>

   </td>
   <td><p style="text-align: right">
0.0784</p>

   </td>
   <td><p style="text-align: right">
57.23</p>

   </td>
  </tr>
  <tr>
   <td>Control plane
   </td>
   <td>c6g.large
   </td>
   <td><p style="text-align: right">
1</p>

   </td>
   <td><p style="text-align: right">
0.068</p>

   </td>
   <td><p style="text-align: right">
49.64</p>

   </td>
   <td><p style="text-align: right">
0.0784</p>

   </td>
   <td><p style="text-align: right">
57.23</p>

   </td>
  </tr>
  <tr>
   <td><strong>Total</strong>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td><p style="text-align: right">
<strong>1,577.97</strong></p>

   </td>
   <td>
   </td>
   <td><p style="text-align: right">
<strong>1,866.46</strong></p>

   </td>
  </tr>
</table>

Here are the configurations and costs of our Intel Xeon Platinum 8000 series processors based instances:

<table>
  <tr>
   <td rowspan="2" ><strong>Service type</strong>
   </td>
   <td rowspan="2" ><strong>EC2 type</strong>
   </td>
   <td rowspan="2" ><strong>Instances</strong>
   </td>
   <td colspan="2" ><strong>US region</strong>
   </td>
   <td colspan="2" ><strong>APAC region</strong>
   </td>
  </tr>
  <tr>
   <td><strong>Unit price (USD/hr)</strong>
   </td>
   <td><strong>Monthly cost</strong>
   </td>
   <td><strong>Unit price (USD/hr) </strong>
   </td>
   <td><strong>Monthly cost</strong>
   </td>
  </tr>
  <tr>
   <td>TiDB
   </td>
   <td>c5.2xlarge
   </td>
   <td><p style="text-align: right">
3</p>

   </td>
   <td><p style="text-align: right">
0.34</p>

   </td>
   <td><p style="text-align: right">
744.60</p>

   </td>
   <td><p style="text-align: right">
0.392</p>

   </td>
   <td><p style="text-align: right">
858.48</p>

   </td>
  </tr>
  <tr>
   <td>TiKV
   </td>
   <td>r5.2xlarge
   </td>
   <td><p style="text-align: right">
3</p>

   </td>
   <td><p style="text-align: right">
0.504</p>

   </td>
   <td><p style="text-align: right">
1,103.76</p>

   </td>
   <td><p style="text-align: right">
0.608</p>

   </td>
   <td><p style="text-align: right">
1,331.52</p>

   </td>
  </tr>
  <tr>
   <td>PD
   </td>
   <td>c5.large
   </td>
   <td><p style="text-align: right">
1</p>

   </td>
   <td><p style="text-align: right">
0.085</p>

   </td>
   <td><p style="text-align: right">
62.05</p>

   </td>
   <td><p style="text-align: right">
0.098</p>

   </td>
   <td><p style="text-align: right">
71.54</p>

   </td>
  </tr>
  <tr>
   <td>Control plane
   </td>
   <td>c5.large
   </td>
   <td><p style="text-align: right">
1</p>

   </td>
   <td><p style="text-align: right">
0.085</p>

   </td>
   <td><p style="text-align: right">
62.05</p>

   </td>
   <td><p style="text-align: right">
0.098</p>

   </td>
   <td><p style="text-align: right">
71.54</p>

   </td>
  </tr>
  <tr>
   <td><strong>Total</strong>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td><p style="text-align: right">
<strong>1,972.46</strong></p>

   </td>
   <td>
   </td>
   <td><p style="text-align: right">
<strong>2,333.08</strong></p>

   </td>
  </tr>
</table>

### Total cost

The following tables summarize the total costs per month in the **US West (Oregon)** and **Asian Pacific (Singapore)** regions. All costs are in US dollars per month.

AWS US West (Oregon)

<table>
  <tr>
   <td><strong>CPU type</strong>
   </td>
   <td><strong>EC2 cost</strong>
   </td>
   <td><strong>Storage cost</strong>
   </td>
   <td><strong>EKS cost</strong>
   </td>
   <td><strong>Total cost</strong>
   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td><p style="text-align: right">
1,577.97</p>

   </td>
   <td><p style="text-align: right">
740.86</p>

   </td>
   <td><p style="text-align: right">
73.00</p>

   </td>
   <td><p style="text-align: right">
2,391.83</p>

   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td><p style="text-align: right">
1,972.46</p>

   </td>
   <td><p style="text-align: right">
740.86</p>

   </td>
   <td><p style="text-align: right">
73.00</p>

   </td>
   <td><p style="text-align: right">
2,786.32</p>

   </td>
  </tr>
</table>

AWS Asia Pacific (Singapore)

<table>
  <tr>
   <td><strong>CPU type</strong>
   </td>
   <td><strong>EC2 cost</strong>
   </td>
   <td><strong>Storage cost</strong>
   </td>
   <td><strong>EKS cost</strong>
   </td>
   <td><strong>Total cost</strong>
   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td><p style="text-align: right">
1,866.46</p>

   </td>
   <td><p style="text-align: right">
856.71</p>

   </td>
   <td><p style="text-align: right">
73.00</p>

   </td>
   <td><p style="text-align: right">
2,796.17</p>

   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td><p style="text-align: right">
2,333.08</p>

   </td>
   <td><p style="text-align: right">
856.71</p>

   </td>
   <td><p style="text-align: right">
73.00</p>

   </td>
   <td><p style="text-align: right">
3,262.79</p>

   </td>
  </tr>
</table>

## Preparation

To deploy a TiDB cluster on an x86-based EKS cluster, follow the steps in [Deploy TiDB on AWS EKS](https://docs.pingcap.com/tidb-in-kubernetes/stable/deploy-on-aws-eks#deploy-tidb-on-aws-eks).

To deploy a TiDB cluster on an Arm-based EKS cluster, follow the steps in [TiDB Deployment on Graviton2-based EKS](https://github.com/xinghua0123/tidb-deployment/blob/main/README.md). The following [temporary Arm images](https://hub.docker.com/u/pingcap2021) are used for benchmarking:

* pingcap2021/tidb-operator:v1.1.11
* pingcap2021/pd:v4.0.10
* pingcap2021/tikv:v4.0.10
* pingcap2021/tidb:v4.0.10
* pingcap2021/tidb-monitor-initializer:v4.0.10

Above images are temporary and not meant for a production environment. Stay tuned for the official Arm images.

## TPC-C benchmark

As you review the following benchmark tests, keep in mind that these are preliminary results. They should not be considered official TPC-C results.

To facilitate benchmarking, TiUP has integrated the bench component, which provides two workloads for stress testing: TPC-C and TPC-H. The commands and flags are as follows:

```shell
tiup bench
Starting component `bench`: /Users/joshua/.tiup/components/bench/v0.0.1/bench
Benchmark database with different workloads

Usage:
  tiup bench [command]

Available Commands:
  help        Help about any command
  tpcc
  tpch

Flags:
      --count int           Total execution count, 0 means infinite
  -D, --db string           Database name (default "test")
  -d, --driver string       Database driver: mysql
      --dropdata            Cleanup data before prepare
  -h, --help                help for /Users/joshua/.tiup/components/bench/v0.0.1/bench
  -H, --host string         Database host (default "127.0.0.1")
      --ignore-error        Ignore error when running workload
      --interval duration   Output interval time (default 10s)
      --isolation int       Isolation Level 0: Default, 1: ReadUncommitted,
                            2: ReadCommitted, 3: WriteCommitted, 4: RepeatableRead,
                            5: Snapshot, 6: Serializable, 7: Linerizable
      --max-procs int       runtime.GOMAXPROCS
  -p, --password string     Database password
  -P, --port int            Database port (default 4000)
      --pprof string        Address of pprof endpoint
      --silence             Do not print error when running workload
      --summary             Print summary TPM only, or also print current TPM when running workload
  -T, --threads int         Thread concurrency (default 16)
      --time duration       Total execution time (default 2562047h47m16.854775807s)
  -U, --user string         Database user (default "root")
```

For TPC-C, the TiUP bench component supports the following commands and flags to run the test:

```shell
tiup bench tpcc
Available Commands:
  check       Check data consistency for the workload
  cleanup     Cleanup data for the workload
  prepare     Prepare data for the workload
  run         Run workload

Flags:
      --check-all        Run all consistency checks
  -h, --help             help for tpcc
      --output string    Output directory for generating csv file when preparing data
      --parts int        Number to partition warehouses (default 1)
      --tables string    Specified tables for generating file, separated by ','. Valid only if output is set. If this flag is not set, generate all tables by default.
      --warehouses int   Number of warehouses (default 10)
```

### TPC-C workloads

This table summarizes the workloads we used, both in terms of the number of warehouses and the data sizes.

<table>
  <tr>
   <td><strong>Workload</strong>
   </td>
   <td><strong>Warehouses</strong>
   </td>
   <td><strong>Data size</strong>
   </td>
  </tr>
  <tr>
   <td>Lagre1
   </td>
   <td>5000
   </td>
   <td>~500 GB
   </td>
  </tr>
  <tr>
   <td>Large2
   </td>
   <td>10000
   </td>
   <td>~1 TB
   </td>
  </tr>
</table>

### TPC-C test procedures

1. On the benchmark VM (c5.4xlarge), deploy the latest version of TiUP.

2. Create warehouses. You should specify the hostname as the load balancer's DNS name since we deployed the TiDB in EKS and exposed the database service as the LoadBalancer type:

    ```shell
    tiup bench tpcc --warehouses 10000 --host xxxxxxxxxxx.elb.us-west-2.amazonaws.com prepare
    ```

3. Run the TPC-C test for different threads. (We used 150, 300, 500, 800, and 1000). Each test runs for 30 minutes.

    ```shell
    tiup bench tpcc --warehouses 10000 --host xxxxxxxxxxx.elb.us-west-2.amazonaws.com --threads 150 --time 10m run
    ```

4. Note the tpmC result for each test case. The following is sample output:

    ```shell
    Finished
    [Summary] DELIVERY - Takes(s): 1796.7, Count: 88527, TPM: 2956.3, Sum(ms): 242093840, Avg(ms): 2734, 90th(ms): 4000, 99th(ms): 8000, 99.9th(ms): 8000
    [Summary] DELIVERY_ERR - Takes(s): 1796.7, Count: 133, TPM: 4.4, Sum(ms): 206560, Avg(ms): 1553, 90th(ms): 4000, 99th(ms): 4000, 99.9th(ms): 8000
    [Summary] NEW_ORDER - Takes(s): 1798.8, Count: 1002915, TPM: 33453.0, Sum(ms): 916326214, Avg(ms): 913, 90th(ms): 1500, 99th(ms): 2000, 99.9th(ms): 4000
    [Summary] NEW_ORDER_ERR - Takes(s): 1798.8, Count: 319, TPM: 10.6, Sum(ms): 118662, Avg(ms): 371, 90th(ms): 1000, 99th(ms): 1500, 99.9th(ms): 1500
    [Summary] ORDER_STATUS - Takes(s): 1798.9, Count: 89022, TPM: 2969.3, Sum(ms): 4346202, Avg(ms): 48, 90th(ms): 80, 99th(ms): 160, 99.9th(ms): 512
    [Summary] ORDER_STATUS_ERR - Takes(s): 1798.9, Count: 1, TPM: 0.0, Sum(ms): 19, Avg(ms): 19, 90th(ms): 20, 99th(ms): 20, 99.9th(ms): 20
    [Summary] PAYMENT - Takes(s): 1798.9, Count: 956516, TPM: 31903.7, Sum(ms): 628421123, Avg(ms): 656, 90th(ms): 1000, 99th(ms): 1500, 99.9th(ms): 2000
    [Summary] PAYMENT_ERR - Takes(s): 1798.9, Count: 201, TPM: 6.7, Sum(ms): 46899, Avg(ms): 233, 90th(ms): 512, 99th(ms): 1000, 99.9th(ms): 1000
    [Summary] STOCK_LEVEL - Takes(s): 1798.9, Count: 89370, TPM: 2980.8, Sum(ms): 6052088, Avg(ms): 67, 90th(ms): 112, 99th(ms): 256, 99.9th(ms): 512
    [Summary] STOCK_LEVEL_ERR - Takes(s): 1798.9, Count: 3, TPM: 0.1, Sum(ms): 342, Avg(ms): 114, 90th(ms): 192, 99th(ms): 192, 99.9th(ms): 192
    tpmC: 33453.0
    ```

5. To proceed with the next workload, change the number of warehouses.

    ```shell
    tiup bench tpcc --warehouses 5000 --host xxxxxxxxxxx.elb.us-west-2.amazonaws.com --threads 150 --time 10m run
    ```

6. Beginning at step 2, repeat this procedure for different numbers of warehouses.

### TPC-C benchmark results

The following table shows the results for a large1 workload:

<table>
  <tr>
   <td><strong>tpmC</strong>
   </td>
   <td><strong>150</strong>
   </td>
   <td><strong>300</strong>
   </td>
   <td><strong>500</strong>
   </td>
   <td><strong>800</strong>
   </td>
   <td><strong>1000</strong>
   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td><p style="text-align: right">
30603.8</p>

   </td>
   <td><p style="text-align: right">
33270.4</p>

   </td>
   <td><p style="text-align: right">
36813.8</p>

   </td>
   <td><p style="text-align: right">
36388.6</p>

   </td>
   <td><p style="text-align: right">
34956.3</p>

   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td><p style="text-align: right">
34114.3</p>

   </td>
   <td><p style="text-align: right">
36715.2</p>

   </td>
   <td><p style="text-align: right">
42493.1</p>

   </td>
   <td><p style="text-align: right">
41275.0</p>

   </td>
   <td><p style="text-align: right">
41426.9</p>

   </td>
  </tr>
  <tr>
   <td>(Arm-x86)/x86
   </td>
   <td><p style="text-align: right">
11.47%</p>

   </td>
   <td><p style="text-align: right">
10.35%</p>

   </td>
   <td><p style="text-align: right">
15.43%</p>

   </td>
   <td><p style="text-align: right">
13.43%</p>

   </td>
   <td><p style="text-align: right">
18.51%</p>

   </td>
  </tr>
</table>

![TPC-C Arm vs. x86 on EKS for a large1 workload](media/tpc-c-arm-vs-x86-on-eks-for-large1-workload.jpg)
<div class="caption-center"> TPC-C Arm vs. x86 on EKS for a large1 workload </div>

The following table shows the results for a large2 workload:

<table>
  <tr>
   <td><strong>tpmC</strong>
   </td>
   <td><strong>150</strong>
   </td>
   <td><strong>300</strong>
   </td>
   <td><strong>500</strong>
   </td>
   <td><strong>800</strong>
   </td>
   <td><strong>1,000</strong>
   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td><p style="text-align: right">
28624.3</p>

   </td>
   <td><p style="text-align: right">
33464.3</p>

   </td>
   <td><p style="text-align: right">
31478.6</p>

   </td>
   <td><p style="text-align: right">
33892.9</p>

   </td>
   <td><p style="text-align: right">
31562.9</p>

   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td><p style="text-align: right">
29858.5</p>

   </td>
   <td><p style="text-align: right">
35259.4</p>

   </td>
   <td><p style="text-align: right">
34088.0</p>

   </td>
   <td><p style="text-align: right">
35899.8</p>

   </td>
   <td><p style="text-align: right">
33453.0</p>

   </td>
  </tr>
  <tr>
   <td>(Arm-x86)/x86
   </td>
   <td><p style="text-align: right">
4.31%</p>

   </td>
   <td><p style="text-align: right">
5.36%</p>

   </td>
   <td><p style="text-align: right">
8.29%</p>

   </td>
   <td><p style="text-align: right">
5.92%</p>

   </td>
   <td><p style="text-align: right">
5.99%</p>

   </td>
  </tr>
</table>

![TPC-C Arm vs. x86 on EKS for a large2 workload](media/tpc-c-arm-vs-x86-on-eks-for-large2-workload.jpg)
<div class="caption-center"> TPC-C Arm vs. x86 on EKS for a large2 workload </div>

### TPC-C price-performance ratio

In the following price-performance table:

* The tpmC values are derived from the average tpmC among 300, 500, and 800 threads.
* The total system costs for the US and APAC regions reflect the estimated five year hardware cost.
* The price-performance ratios compare x86 and Graviton2 Arm processors. A lower cost for more performance is better.
* All costs are in US dollars.

<table>
  <tr>
   <td rowspan="2" >
   </td>
   <td rowspan="2" >
<strong>Workload</strong>
   </td>
   <td rowspan="2" ><strong>tpmC</strong>
   </td>
   <td colspan="2" ><strong>US region</strong>
   </td>
   <td colspan="2" ><strong>APAC region</strong>
   </td>
  </tr>
  <tr>
   <td><strong>Total system cost</strong>
   </td>
   <td><strong>Price-performance</strong>
   </td>
   <td><strong>Total system cost</strong>
   </td>
   <td><strong>Price-performance</strong>
   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td>Large1
   </td>
   <td><p style="text-align: right">
35,490.93</p>

   </td>
   <td><p style="text-align: right">
162,208.80</p>

   </td>
   <td><p style="text-align: right">
4.57</p>

   </td>
   <td><p style="text-align: right">
189,804.60</p>

   </td>
   <td><p style="text-align: right">
5.35</p>

   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td>Large1
   </td>
   <td><p style="text-align: right">
40,161.10</p>

   </td>
   <td><p style="text-align: right">
138,539.40</p>

   </td>
   <td><p style="text-align: right">
3.45</p>

   </td>
   <td><p style="text-align: right">
161,807.40</p>

   </td>
   <td><p style="text-align: right">
4.03</p>

   </td>
  </tr>
  <tr>
   <td>(Arm-x86)/x86
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-24.52%</p>

   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-24.66%</p>

   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td>Large2
   </td>
   <td>32,945.27
   </td>
   <td><p style="text-align: right">
162,208.80</p>

   </td>
   <td><p style="text-align: right">
4.92</p>

   </td>
   <td><p style="text-align: right">
189,804.60</p>

   </td>
   <td><p style="text-align: right">
5.76</p>

   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td>Large2
   </td>
   <td>35,082.40
   </td>
   <td><p style="text-align: right">
138,539.40</p>

   </td>
   <td><p style="text-align: right">
3.95</p>

   </td>
   <td><p style="text-align: right">
161,807.40</p>

   </td>
   <td><p style="text-align: right">
4.61</p>

   </td>
  </tr>
  <tr>
   <td>(Arm-x86)/x86
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-19.79%</p>

   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-19.94%</p>

   </td>
  </tr>
</table>

As the following graphic shows, when we compare the absolute tpmC performance under each workload, the Arm-based system outperforms the x86-based system by 5%-15%. After we factor in the hardware cost, the Arm price-performance ratio is up to 25% lower than x86.

![TPC-C price-performance ratio](media/tpc-c-price-performance-ratio.jpg)
<div class="caption-center"> TPC-C price-performance ratio </div>

## Sysbench

We will be using `oltp_read_write.lua` to test the performance for the OLTP workload.

### Sysbench workloads

* Read (75%) and Write (25%)
* Table: 16
* Table size: 10 M rows per table
* Data size: around 100 GB

### Sysbench test procedures

1. Deploy the latest version of sysbench on the benchmark VM (c5.4xlarge).

2. Set the sysbench configurations and save them in the configuration file. The following is a sample configuration file:

    ```shell
    mysql-host={TIDB_HOST}
    mysql-port=4000
    mysql-user=root
    mysql-password=password
    mysql-db=sbtest
    time=600
    threads=8 # set to 8 while importing the data
    report-interval=10
    db-driver=mysql
    ```

3. Before you import the data, it is necessary to make some settings to TiDB. Execute the following command in MySQL client:

    ```sql
    set global tidb_disable_txn_auto_retry = off;
    ```

4. Use [BR](https://docs.pingcap.com/tidb/stable/backup-and-restore-tool) to import the prepared data in S3.

5. Change the thread in config file to 300.

6. Run the sysbench test:

    ```shell
    sysbench --config-file=config oltp_read_write --tables=16 --table-size=10000000 run
    ```

7. Note the test results. The following are sample test results:

    ```shell
    SQL statistics:
        queries performed:
            read:                            10457930
            write:                           2966386
            other:                           1515584
            total:                           14939900
        transactions:                        746995 (2489.02 per sec.)
        queries:                             14939900 (49780.45 per sec.)
        ignored errors:                      0      (0.00 per sec.)
        reconnects:                          0      (0.00 per sec.)

    General statistics:
        total time:                          300.1146s
        total number of events:              746995

    Latency (ms):
            min:                                   43.84
            avg:                                  120.50
            max:                                  381.92
            95th percentile:                      153.02
            sum:                             90013122.40

    Threads fairness:
        events (avg/stddev):           2489.9833/235.76
        execution time (avg/stddev):   300.0437/0.03
    ```

8. Beginning at step 5, repeat this procedure and set the thread to 600 and 900.

### Sysbench benchmark results

Results for 300, 600, and 900 threads are listed below. Since the QPS and TPS in sysbench are proportional, we will only compare the TPS in our test.

<table>
  <tr>
   <td><strong>Metrics</strong>
   </td>
   <td><strong>300</strong>
   </td>
   <td><strong>600</strong>
   </td>
   <td><strong>900</strong>
   </td>
  </tr>
  <tr>
   <td>x86 P95 latency (ms)
   </td>
   <td><p style="text-align: right">
155.80</p>

   </td>
   <td><p style="text-align: right">
282.25</p>

   </td>
   <td><p style="text-align: right">
427.07</p>

   </td>
  </tr>
  <tr>
   <td>Arm P95 latency (ms)
   </td>
   <td><p style="text-align: right">
147.61</p>

   </td>
   <td><p style="text-align: right">
267.41</p>

   </td>
   <td><p style="text-align: right">
383.33</p>

   </td>
  </tr>
  <tr>
   <td>x86 QPS
   </td>
   <td><p style="text-align: right">
48814.94</p>

   </td>
   <td><p style="text-align: right">
52342.03</p>

   </td>
   <td><p style="text-align: right">
52413.17</p>

   </td>
  </tr>
  <tr>
   <td>Arm QPS
   </td>
   <td><p style="text-align: right">
51892.58</p>

   </td>
   <td><p style="text-align: right">
55886.22</p>

   </td>
   <td><p style="text-align: right">
57465.90</p>

   </td>
  </tr>
  <tr>
   <td>x86 TPS
   </td>
   <td><p style="text-align: right">
2440.75</p>

   </td>
   <td><p style="text-align: right">
2617.10</p>

   </td>
   <td><p style="text-align: right">
2620.66</p>

   </td>
  </tr>
  <tr>
   <td>Arm TPS
   </td>
   <td><p style="text-align: right">
2594.63</p>

   </td>
   <td><p style="text-align: right">
2794.31</p>

   </td>
   <td><p style="text-align: right">
2873.30</p>

   </td>
  </tr>
  <tr>
   <td>For TPS: (Arm-x86)/x86
   </td>
   <td><p style="text-align: right">
6.30%</p>

   </td>
   <td><p style="text-align: right">
6.77%</p>

   </td>
   <td><p style="text-align: right">
9.64%</p>

   </td>
  </tr>
</table>

![Sysbench Arm vs. x86 on EKS](media/sysbench-arm-vs-x86-on-eks.jpg)
<div class="caption-center"> Sysbench Arm vs. x86 on EKS </div>

### Sysbench price-performance ratio

In the following price-performance table:

* TPS values are derived from the average TPS among 300, 600, and 900 threads.
* The total system cost reflects the estimated five year hardware cost. All costs are in US dollars.
* Price-performance compares x86 and Graviton2 Arm processors. A lower value is better. That indicates a lower cost for more performance.

<table>
  <tr>
   <td rowspan="2" >
   </td>
   <td rowspan="2" >
<strong>TPS</strong>
   </td>
   <td colspan="2" ><strong>US region</strong>
   </td>
   <td colspan="2" ><strong>APAC region</strong>
   </td>
  </tr>
  <tr>
   <td><strong>Total system cost</strong>
   </td>
   <td><strong>Price-performance</strong>
   </td>
   <td><strong>Total system cost</strong>
   </td>
   <td><strong>Price-performance</strong>
   </td>
  </tr>
  <tr>
   <td>x86
   </td>
   <td><p style="text-align: right">
2,559.50</p>

   </td>
   <td><p style="text-align: right">
162,208.80</p>

   </td>
   <td><p style="text-align: right">
63.38</p>

   </td>
   <td><p style="text-align: right">
189,804.60</p>

   </td>
   <td><p style="text-align: right">
74.16</p>

   </td>
  </tr>
  <tr>
   <td>Arm
   </td>
   <td><p style="text-align: right">
2,754.08</p>

   </td>
   <td><p style="text-align: right">
138,539.40</p>

   </td>
   <td><p style="text-align: right">
50.30</p>

   </td>
   <td><p style="text-align: right">
161,807.40</p>

   </td>
   <td><p style="text-align: right">
58.75</p>

   </td>
  </tr>
  <tr>
   <td>(Arm-x86)/x86
   </td>
   <td>
   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-20.64%</p>

   </td>
   <td>
   </td>
   <td><p style="text-align: right">
-20.77%</p>

   </td>
  </tr>
</table>

## Conclusion

Benchmarking results from both TPC-C and sysbench have shown that the Graviton2 processor has better performance compared to the x86 processor. In some cases, Graviton2 outperforms x86 by up to 18%. After factoring in the hardware cost, the Graviton2 processor has a better price-performance ratio than the x86—on average 20% lower. The results are only based on the workloads (100 GB, 500 GB, 1 TB) we tested. For limitations and future plans on the benchmark, please refer to [AWS Startups Blog](https://aws.amazon.com/blogs/startups/achieve-better-price-to-performance-for-tidb-graviton2-processors/).
