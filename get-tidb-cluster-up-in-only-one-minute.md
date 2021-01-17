---
title: Get a TiDB Cluster Up in Only One Minute
author: [Heng Long]
date: 2020-04-29
summary: TiUP is a component manager that streamlines installing and configuring a TiDB cluster into a few easy commands. It helps get your cluster up and running quickly with a minimal learning curve.
tags: ['Ecosystem tools']
categories: ['Product']
image: /images/blog/quickly-install-tidb-cluster.jpg
---

![Quickly install a TiDB cluster](media/quickly-install-tidb-cluster.jpg)

[TiDB](https://pingcap.com/docs/stable/) is an open-source, distributed, [NewSQL](https://en.wikipedia.org/wiki/NewSQL) database that supports [hybrid transactional and analytical processing](https://en.wikipedia.org/wiki/HTAP) (HTAP) workloads. Nearly 1,000 companies in a variety of industries use TiDB in their production environments.

However, some users tell us TiDB can be challenging to install. Have you tried to set up a TiDB test cluster, but given up because you thought it was too complicated? Or maybe you're new to TiDB and want to adapt your application to a distributed data environment. You don't have time to become a distributed database expert just to set up a production cluster.

All this is about to change. TiDB 4.0 introduces [TiUP](https://pingcap.com/docs/stable/how-to/deploy/orchestrated/tiup/), a component manager that streamlines installing and configuring a TiDB cluster into a few easy commands. With TiUP, you can get your cluster up in just one minute! Whatever your need or experience level, TiUP will get your cluster up and running quickly with a minimal learning curve. In addition, TiUP is an "App Store" for your TiDB: it offers a unified interface for you to manage various TiDB tools.

TiUP uses a command-line interface, so if you like rustup, gcloud, or UNIX, you'll feel right at home.

## Life before TiUP: a steep learning curve

Before TiUP, setting up a TiDB cluster was a steep, uphill climb. A cluster consists of the TiDB core components, [TiDB](https://pingcap.com/docs/stable/architecture/#tidb-server), [TiKV](https://pingcap.com/docs/stable/architecture/#tikv-server), and [Placement Driver](https://pingcap.com/docs/stable/architecture/#placement-driver-server) (PD), as well as three monitoring components, Prometheus, Grafana, and Node Explorer. For each component, you needed to understand:

* Startup parameters
* Port configurations
* Startup sequence
* Interactive port configurations

For example, let's say we want to create a 10-instance local debugging cluster, with three PD instances, three TiDB instances, and four TiKV instances. Here are the startup parameters for the three PD instances.

```shell
$ bin / pd-server --name = pd-0
--data-dir = data / Rt1J27k / pd-0 / data
--peer-urls = http: //127.0.0.1: 2380
--advertise-peer-urls = http: //127.0.0.1: 2380 --client-urls = http: //127.0.0.1: 2379 --advertise-client-urls = http: //127.0.0.1: 2379 --log-file = data / Rt1J27k / pd-0 / pd.log --initial-cluster = pd-0 = http: //127.0.0.1: 2380, pd-1 = http: //127.0.0.1: 2381, pd-2 = http: //127.0.0.1: 2383

$ bin / pd-server --name = pd-1
--data-dir = data / Rt1J27k / pd-1 / data
--peer-urls = http: //127.0.0.1: 2381 --advertise-peer-urls = http: //127.0.0.1:2381 --client-urls = http: //127.0.0.1: 2382 --advertise-client-urls = http: //127.0.0.1: 2382 --log-file = data / Rt1J27k / pd -1 / pd.log --initial-cluster = pd-0 = http: //127.0.0.1: 2380, pd-1 = http: //127.0.0.1: 2381, pd-2 = http: //127.0. 0.1: 2383

$ bin / pd-server --name = pd-2
--data-dir = data / Rt1J27k / pd-2 / data
--peer-urls = http: //127.0.0.1: 2383 --advertise- peer-urls = http: //127.0. 0.1: 2383 --client-urls = http: //127.0.0.1: 2384 --advertise-client-urls = http: //127.0.0.1: 2384 --log-file = data / Rt1J27k / pd-2 / pd .log --initial-cluster = pd-0
```

Even if you're a TiDB expert, deciphering these intricate commands isn't easy. And these are just the commands for the PD instances. We haven't gotten to TiDB, TiKV, and the monitoring components.

Let's say you make it through this first challenge and manage to build the cluster. Now you face a second challenge: how do you get data into the cluster so you can run some tests? You need to use the [TiDB Data Migration (DM)](https://github.com/pingcap/dm) component, but where can you download these tools? How do you use them?

You start to wonder: do you want to experience the latest trend of distributed data or become an expert in distributed databases?

## TiUP: flattening the learning curve

TiUP simplifies cluster installation and configuration. It:

* Distributes all the components of the TiDB ecosystem. You get everything you need to install TiDB in one place. No more searching for and downloading "missing pieces" online.
* Organizes components into a consistent user experience. TiUP uses one set of simple commands and one basic syntax. You don't need to learn a set of commands for each component.

To get started, let's install TiUP. Navigate to the [TiUP home page](https://tiup.io/). There, you'll see a two-line shell script.

The first command installs TiUP.

```shell
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
```

The second runs a single-machine cluster.

```shell
tiup playground
```

Let's modify the second command to set up the cluster we mentioned earlier (three PD instances, three TiDB instances, and four TiKV instances). See how much easier it is.

1. Launch the cluster.

    ```shell
    tiup playground --pd 3 --db 3 --kv 4
    ```

2. While the cluster launches, configure monitoring.

    ```shell
    tiup playground --pd 3 --db 3 --kv 4 --monitor
    ```

3. Start a TiDB cluster version that you want to run.

    ```shell
    tiup playground v3.0.10
    ```

4. Specify that TiUP will use the latest release version (v4.0.0-rc) so you get the most up-to-date features. This command specifies that this set of features is called "example-features." You can then use this tag to assign this set of features to clients.

    ```shell
    tiup --tag example-features playground v4.0.0-rc
    ```

5. Connect to the cluster that you've just started. The following command connects a client to the playground cluster. `example-features` is the tag you gave to the playground, and the client automatically connects to this tag corresponding to TiUP.

    ```shell
    tiup client example-features
    ```

## What else can TiUP do?

TiUP can do more than just install and configure a cluster. It can:

* Install, update, or uninstall a component (`tiup install <component>`, `tiup update <component>`, `tiup uninstall <component>`)
* Uninstall TiUP and clear all downloaded components and data generated by the component when it runs (`tiup uninstall --self`)
* Display a list of components (`tiup list`)
* Display the status of running components (`tiup status`)
* Delete the temporary data that is generated when an application runs (`tiup clean`)

You can use TiUP to install many TiDB components. Further, you can use it "as is." You can install TiUP immediately, and there's no daemon.

## A good start with great potential

TiDB's ecology is far more than TiDB, TiKV, and PD. It also includes components that migrate, monitor, synchronize, backup, and restore data. TiUP is not just a component management tool, it is building an ecosystem. If you are used to installing apps using Apple's App Store, then you see the potential TiUP has to improve your TiDB experience.

Over time, we'll enhance TiUP to include more tried-and-tested tools from the TiDB ecosystem, making them easier to use. They include:

* TPC-C performance benchmarking (`tiup bench tpcc`)
* TPC-H performance benchmarking (`tiup bench tpch`)
* Integrated cluster tools for one-stop production cluster maintenance and scaling in or out (`tiup cluster`)
We've open-sourced the [TiUP project](https://github.com/pingcap/tiup), and we look forward to working with the community to improve this ecosystem and to develop new components to cover various use cases. The community can share their own achievements and empower users with the same needs by writing components that cover dedicated scenarios. You're welcome to join the [TiDB Community on Slack](http://suo.im/5BmPAe) to give us advice or feedback on your user experience.

_*App Store is a trademark of Apple Inc., registered in the U.S. and other countries._
