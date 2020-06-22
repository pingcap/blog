---
title: Building, Running, and Benchmarking TiKV and TiDB
author: [Nick Cameron]
date: 2020-05-04
summary: This post introduces how to build and run your own TiDB or TiKV, and how to run some benchmarks on those databases.
tags: ['How to', 'Benchmark', 'TiKV']
categories: ['Product']
image: /images/blog/building-running-benchmarking-tikv-tidb.jpg
---

![Building, running, and benchmarking TiKV and TiDB](media/building-running-benchmarking-tikv-tidb.jpg)

[TiDB](https://pingcap.com/docs/stable/) is a distributed, MySQL-compatible database. It is built on top of [TiKV](https://pingcap.com/docs/stable/architecture/#tikv-server), a distributed key-value store. Building these projects is easy - clone the Git repos, then run `make`. Unfortunately, running development builds is a bit more complicated. (Although hopefully it will get a lot easier in the near future thanks to TiUP). In this post, I'm going to go over how to build and run your own TiDB or TiKV, and how to run some benchmarks on those databases.

If you just want to run TiDB or TiKV, it is much easier to use [TiUP](https://pingcap.com/docs/stable/how-to/deploy/orchestrated/tiup/) or [Docker Compose](https://pingcap.com/docs/stable/how-to/get-started/deploy-tidb-from-docker-compose/).

## Building

Assuming you want to run TiDB, you will need [TiDB](https://github.com/pingcap/tidb), [Placement Driver (PD)](https://github.com/pingcap/pd), and [TiKV](https://github.com/tikv/tikv). Clone each repo and run `make` in the root directory of each cloned repo. For TiKV `make` (and `make release`) produce an optimised build (you might want to use `make unportable_release` which permits more optimisations), but not the one we actually build for distribution. If you need that (fully optimised, but takes a long time to build), run `make dist_release`.

See the appendix for information on prerequisites.

## Running

The easiest way to run TiDB is to run all servers on the same machine. More realistic is to put each server on its own machine (the TiDB server can share a machine with one PD server). These instructions are for using one machine. A good topology to start with is one TiDB server, one PD server, and three TiKV servers. Some benchmarking works fine with one of each server, others might work better with many more servers. Getting things running is similar no matter the number of servers.

First run PD:

```bash
$PD_DIR/bin/pd-server --name=pd1 \
    --data-dir=pd1 \
    --client-urls="http://127.0.0.1:2379" \
    --peer-urls="http://127.0.0.1:2380" \
    --initial-cluster="pd1=http://127.0.0.1:2380" \
    --log-file=pd1.log &
```

You can change the names of the data directory and log file if you like.

Before running TiKV, you might need to increase your open file descriptor limit: `ulimit -S -n 1000000`.

Then start your TiKV servers:

```bash
$TIKV_DIR/target/release/tikv-server --pd-endpoints="127.0.0.1:2379" \
    --addr="127.0.0.1:20160" \
    --status-addr="127.0.0.1:20181" \
    --data-dir=tikv1 \
    --log-file=tikv1.log &
$TIKV_DIR/target/release/tikv-server --pd-endpoints="127.0.0.1:2379" \
    --addr="127.0.0.1:20161" \
    --status-addr="127.0.0.1:20182" \
    --data-dir=tikv2 \
    --log-file=tikv2.log &
$TIKV_DIR/target/release/tikv-server --pd-endpoints="127.0.0.1:2379" \
    --addr="127.0.0.1:20162" \
    --status-addr="127.0.0.1:20183" \
    --data-dir=tikv3 \
    --log-file=tikv3.log &
```

The pattern for running more TiKV servers should be obvious, you can run as many as you like and don't need to change anything other than the command line.

For TiDB, you'll need a [config file](https://github.com/pingcap/tidb/blob/master/config/config.toml.example); I assume it is called config.toml, but it doesn't matter. Depending on what you're benchmarking you'll need different configurations, I think you always want:

```
[prepared-plan-cache]
enabled = true
mem-quota-query = 10737418240
```

Then, to run:

```bash
$TIDB_DIR/bin/tidb-server --store=tikv \
    --path="127.0.0.1:2379" \
    --log-file=tidb.log \
    # Remove the next line if you want verbose logging.
    -L=error \
    --config=config.toml &
```

If you put these commands in a script, then I recommend putting `sleep 5` between the PD, TiKV, and TiDB launch commands (but you don't need it between the each TiKV command).

You can check everything has launched with `ps`. To check things are running properly, run:

```bash
$PD_DIR/bin/pd-ctl store -u http://127.0.0.1:2379
```

Check that all `store`s have `state_name: Up`.

You can then use TiDB via the MySQL client:

```bash
mysql -h 127.0.0.1 -P 4000 -u root
```

When you're done, terminate each process using `kill` or `killall`.

## Getting metrics

TiDB supports metrics via [Prometheus](https://prometheus.io) and [Grafana](https://grafana.com/grafana). You will run Prometheus on the same machine as TiDB. Grafana can be run on the same machine or a different one.

To install Prometheus:

```bash
# Find the latest version at https://prometheus.io/download/
wget https://github.com/prometheus/prometheus/releases/download/v2.17.2/prometheus-2.17.2.linux-amd64.tar.gz
tar -xzf prometheus-2.17.2.linux-amd64.tar.gz
rm prometheus-2.17.2.linux-amd64.tar.gz
```

Then edit prometheus.yml so it looks something like:

```
global:
  scrape_interval:     15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: tikv
    honor_labels: true
    static_configs:
      - targets: ['127.0.0.1:20181', '127.0.0.1:20182', '127.0.0.1:20183']
  - job_name: pd
    honor_labels: true
    static_configs:
      - targets: ['127.0.0.1:2379']
  - job_name: 'tidb'
    honor_labels: true
    static_configs:
    - targets: ['127.0.0.1:10080']
```

Note that you need a target for each server. For TiKV, the URLs are the `--status-addr` URLs.

Run Prometheus:

```
./prometheus --config.file=prometheus.yml &
```

You can check Prometheus is running by pointing your browser at port 9090, e.g., `http://127.0.0.1:9090`.

I like to run Grafana on my local machine so that the test machine has more stable resources, but it is fine to run it on the test machine too. To get Grafana, see [grafana.com/grafana/download](https://grafana.com/grafana/download). On Mac, you can use `brew install grafana`.

To run:

* Linux (systemd): `sudo systemctl start grafana-server`
* Linux (init.d): `sudo service grafana-server start`
* Mac:

    ```bash
    grafana-server --config=/usr/local/etc/grafana/grafana.ini \
        --homepath /usr/local/share/grafana --packaging=brew \
        cfg:default.paths.logs=/usr/local/var/log/grafana \
        cfg:default.paths.data=/usr/local/var/lib/grafana \
        cfg:default.paths.plugins=/usr/local/var/lib/grafana/plugins
    ```

Then visit port 3000, e.g., <http://127.0.0.1:3000>.

You'll need to add a data source for Prometheus, the URL will be something like <http://127.0.0.1:9090>.

Then import a Grafana dashboard, some useful dashboards:

* [TiDB](https://github.com/pingcap/tidb-ansible/tree/master/scripts/tidb.json)
* [PD](https://github.com/pingcap/tidb-ansible/tree/master/scripts/pd.json)
* [TiKV details](https://github.com/pingcap/tidb-ansible/tree/master/scripts/tikv_details.json)
* [TiKV trouble shooting](https://github.com/pingcap/tidb-ansible/tree/master/scripts/tikv_trouble_shooting.json)

## Benchmarking

There are numerous ways to benchmark TiDB or TiKV, the most common are YCSB and Sysbench. There is also the [automated tests repo](https://github.com/pingcap/automated-tests), but that is not open source.

### YCSB

YCSB is the Yahoo! Cloud Serving Benchmark. We'll use PingCAP's open source [Go port of YCSB](https://github.com/pingcap/go-ycsb) to test TiKV (without TiDB). See also [Running a workload in YCSB](https://github.com/brianfrankcooper/YCSB/wiki/Running-a-Workload).

To install and build, run

```bash
git clone https://github.com/pingcap/go-ycsb.git \
  $GOPATH/src/github.com/pingcap/go-ycsb --depth 1
cd $GOPATH/src/github.com/pingcap/go-ycsb
make
cd -
```

You'll need PD and TiKV to be running, but you don't need to initialise a database. Choose a workload from these [workloads](https://github.com/pingcap/go-ycsb/tree/master/workloads) (we'll use `workloadc` in the following example). You'll probably want to customise the `operationcount`, `recordcount`, and `threadcount`.

Running a benchmark has two phases, load and run:

```bash
$GOPATH/src/github.com/pingcap/go-ycsb/bin/go-ycsb load tikv \
    -P $GOPATH/src/github.com/pingcap/go-ycsb/workloads/workloadc \
    -p dropdata=false -p verbose=false -p debug.pprof=":6060" \
    -p tikv.pd="127.0.0.1:2379" -p tikv.type="raw" \
    -p tikv.conncount=128 -p tikv.batchsize=128 \
    -p operationcount=100000 -p recordcount=100000 \
    -p threadcount=500
$GOPATH/src/github.com/pingcap/go-ycsb/bin/go-ycsb run tikv \
    -P $GOPATH/src/github.com/pingcap/go-ycsb/workloads/workloadc \
    -p verbose=false -p debug.pprof=":6060" \
    -p tikv.pd="127.0.0.1:2379" -p tikv.type="raw" \
    -p operationcount=100000 -p recordcount=100000 \
    -p threadcount=500
```

If you prefer you can put all the `-p` arguments in a property file and load it with `-P`. See the [workload files](https://github.com/pingcap/go-ycsb/tree/master/workloads) for example property files. There are many other properties you can use to customise YCSB, here is an example property file:

```
"insertproportion"="0"
"readproportion"="1"
"updateproportion"="0"
"scanproportion"="0"

"workload"="core"
"recordcount"="1000000"
"operationcount"="1000000"
"threadcount"="500"
"readallfields"="true"

"dotransactions"="true"
"tikv.type"="raw"
"tikv.conncount"="128"
"tikv.pd"="127.0.0.1:2379"

"requestdistribution"="zipfian"
```

### Sysbench

[Sysbench](https://github.com/akopytov/sysbench) tests TiDB and TiKV.

To install:

```bash
curl -s https://packagecloud.io/install/repositories/akopytov/sysbench/script.deb.sh | sudo bash
sudo apt -y install sysbench
```

You'll need a config file, mine is called 'config' and looks like this:

```
mysql-host=127.0.0.1
mysql-port=4000
mysql-user=root
mysql-db=sbtest
threads=32
report-interval=10
db-driver=mysql
```

Before each run, you'll need to initialise the database:

```bash
# if the sbtest database exists:
mysql -h 127.0.0.1 -P 4000 -u root -D sbtest \
  -Be "DROP DATABASE sbtest;"

mysql -h 127.0.0.1 -P 4000 -u root -Be "create database sbtest;"
mysql -h 127.0.0.1 -P 4000 -u root -D sbtest \
  -Be "SET GLOBAL tidb_disable_txn_auto_retry = 0;"
mysql -h 127.0.0.1 -P 4000 -u root -D sbtest \
  -Be "SET GLOBAL tidb_retry_limit = 10000;"

sysbench --config-file=config oltp_point_select \
  --tables=32 --table-size=200000 --time=30 prepare
```

Then to run the benchmark:

```bash
sysbench --config-file=config oltp_point_select \
  --tables=32 --table-size=200000 --warmup-time=30 --time=300 \
  --mysql-ignore-errors=8005 run
```

You can vary the number of tables and the table size. Useful sysbench benchmarks are:

* `oltp_point_select`
* `oltp_read_only`
* `oltp_update_index`
* `oltp_update_non_index`
* `oltp_read_write`

You need to change both the `prepare` and `run` statements so that their parameters match.

### Some benchmarking tips

How to make a perform good benchmarking is a pretty big topic. Here are some basic tips

* Make the benchmark as close to reality as possible
  - Use hardware and OS similar to client hardware and OS
  - Use a realistic benchmark and workload, preferably use real data
  - Use a fully optimised build (including using SIMD, etc.)
* Make the benchmark as reliable as possible
  - Run it on dedicated hardware
  - Perform multiple runs, exclude outliers, and use an average
  - Run as few other processes as possible; avoid using a window manager
  - Use a reproducible and deterministic workload
* Record details of the benchmark
  - what code was built, any configuration
  - what was tested
  - the systems and techniques used in the benchmark
  - ...
* Report relative, not absolute numbers
  - e.g., 'the new feature improved QPS by 4.2%'
  - not 'the new feature improved QPS by 2000' or 'the new feature has QPS of 8.2m'
  - unless doing regression testing on standardised hardware
* Listen to anything Brendan Gregg says

## Profiling

Benchmarking can tell you if a change makes a program run faster or slower, but it can't tell you *why*. For that you need to profile the code.

### Perf

Perf is a huge, powerful tool for profiling programs in Linux. It's too big a topic for this blog post, so I'll just document a few ways I use it with TiKV. First start your benchmark running, then find the process id (`PID`) of the process you want to profile (e.g., one of the TiKV servers). You can use `perf stat` to get some high-level statistics on your program:

```bash
perf stat -p $PID
```

Or you can get a more detailed profile by recording a profile and exploring it (where `TIME` is the number of seconds to collect data for, I usually use `30` or `60`):

```bash
perf record -F 99 -p $PID -g --call-graph dwarf -- sleep $TIME
perf report
```

For profiling TiDB/TiKV, I find it is often useful to profile [IO](http://www.brendangregg.com/FlameGraphs/offcpuflamegraphs.html#IO) or [off CPU time](http://www.brendangregg.com/offcpuanalysis.html).

### Flamegraphs

[Flamegraphs](http://www.brendangregg.com/flamegraphs.html) are a way to visualise performance data. You collect data using a profiling tool, then feed it into the Flamegraph tools. Install by cloning the Git repo:

```bash
git clone git@github.com:brendangregg/FlameGraph.git
```

To use perf and flamegraphs, run the following:

```bash
perf record -F 99 -p $PID -g --call-graph dwarf -- sleep $TIME
perf script > run1.perf
$FLAMEGRAPH_DIR/stackcollapse-perf.pl run1.perf > run1.folded
$FLAMEGRAPH_DIR/FlameGraph/flamegraph.pl run1.folded > run1.svg
```

You'll end up with an interactive flame graph in run1.svg.

## Appendix: prerequisites

Assuming you have a clean Ubuntu machine, this script will get you ready to build and run (this isn't the absolute minimum, but includes some useful tools for debugging, etc):

```bash
sudo apt update
sudo apt --yes install net-tools
sudo apt --yes install build-essential
sudo apt --yes install cmake
sudo apt --yes install unzip
sudo apt --yes install pkg-config
sudo apt --yes install autoconf
sudo apt --yes install clang
sudo apt --yes install python-pip
sudo apt --yes install linux-tools-common
# You will need to check the actual version you need.
sudo apt --yes install linux-tools-5.3.0-26-generic
sudo apt --yes install linux-tools-generic
sudo apt --yes install zsh
sudo apt --yes install nfs-kernel-server
sudo apt --yes install ntpdate
sudo apt --yes install valgrind
sudo apt --yes install libtool
sudo apt --yes install libssl-dev
sudo apt --yes install zlib1g-dev
sudo apt --yes install libpcap-dev
sudo apt --yes install mysql-client

# Rust
curl https://sh.rustup.rs -sSf | bash -s -- '-y' '--default-toolchain' 'nightly'
source $HOME/.cargo/env
rustup component add rustfmt

# go
sudo snap install go --classic
go get -u golang.org/x/lint/golint
```

To clone the Git repos, run:

```bash
git clone https://github.com/pingcap/tidb.git
git clone https://github.com/pingcap/pd.git
git clone https://github.com/tikv/tikv.git
```

*This post was originally published on [Nick Cameron‘s blog](https://www.ncameron.org/blog/building-running-and-benchmarking-tikv-and-tidb/).*
