---
title: Create a Scale-Out Hive Cluster with a Distributed, MySQL-Compatible Database
author: ['Mengyu Hu']
date: 2020-08-04
summary: This post shows how to deploy a Hive cluster with TiDB to achieve horizontal scalability of Hive Metastore.
image: /images/blog/horizontal-scaling-hive.jpg
tags: ['Scalability', 'Tutorial']
categories: ['Engineering']
---

**Author:** Mengyu Hu (Platform Engineer at Zhihu)

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![Horizontal scaling for Hive](media/horizontal-scaling-hive.jpg)

Hive Metastore supports various backend databases, among which MySQL is the most commonly used. However, in real-world scenarios, MySQL's shortcoming is obvious: as metadata grows in Hive, MySQL is limited by its standalone performance and can't deliver good performance. When individual MySQL databases form a cluster, the complexity drastically increases. In scenarios with huge amounts of metadata (for example, a single table has more than 10 million or even 100 million rows of data), MySQL is not a good choice.

We had this problem, and our [migration story](https://en.pingcap.com/case-studies/horizontally-scaling-hive-metastore-database-by-migrating-from-mysql-to-tidb) proves that [TiDB](https://docs.pingcap.com/tidb/v4.0), an open-source distributed [Hybrid Transactional/Analytical Processing](https://en.wikipedia.org/wiki/HTAP) (HTAP) database, is a perfect solution in these scenarios.

In this post, I'll share with you how to create a Hive cluster with TiDB as the Metastore database at the backend so that you can use TiDB to horizontally scale Hive Metastore without worrying about database capacity.

## Why use TiDB in Hive as the Metastore database?

[TiDB](https://github.com/pingcap/tidb) is a distributed SQL database built by [PingCAP](https://pingcap.com/) and its open-source community. **It is MySQL compatible and features horizontal scalability, strong consistency, and high availability.** It's a one-stop solution for both Online Transactional Processing (OLTP) and Online Analytical Processing (OLAP) workloads.

In scenarios with enormous amounts of data, due to TiDB's distributed architecture, query performance is not limited to the capability of a single machine. When the data volume reaches the bottleneck, you can add nodes to improve TiDB's storage capacity.

Because TiDB is compatible with the MySQL protocol, it's easy to switch Hive's Metastore database to TiDB. You can use TiDB as if you were using MySQL, with almost no changes:

* For the existing Hive cluster, you can use the `mysqldump` tool to replicate all data in MySQL to TiDB.
* You can use the metadata initialization tool that comes with Hive to create a new Hive cluster.

## How to create a Hive cluster with TiDB

Creating a Hive cluster with TiDB involves the following steps:

* [Meet component requirements](#components-required)
* [Install a Hive cluster](#install-a-hive-cluster)
    * [Deploy a TiDB cluster](#step-1-deploy-a-tidb-cluster)
    * [Configure Hive](#step-2-configure-hive)
    * [Initialize metadata](#step-3-initialize-metadata)
    * [Launch Metastore and test](#step-4-launch-metastore-and-test)

### Components required

<table>
  <tr>
   <td><strong>Component</strong>
   </td>
   <td><strong>Version</strong>
   </td>
  </tr>
  <tr>
   <td>Hive
   </td>
   <td> 3.1.2
   </td>
  </tr>
  <tr>
   <td>Hadoop
   </td>
   <td>2.6.0-cdh-5.16.1
   </td>
  </tr>
  <tr>
   <td>TiDB
   </td>
   <td>4.0
   </td>
  </tr>
  <tr>
   <td>Java Development Kit (JDK)
   </td>
   <td>1.8.0_221
   </td>
  </tr>
</table>

There are no mandatory requirements for the component versions, as long as the components are compatible with each other. After you confirm that you have successfully installed Hadoop and JDK and can use them directly, you can move on to the next step.

### Install a Hive cluster

#### Step 1: Deploy a TiDB cluster

1. To set up a TiDB cluster, refer to [this document](https://docs.pingcap.com/tidb/stable/production-deployment-using-tiup).

2. Create a Hive user in TiDB and set a password.

3. Create a database named `hive` and grant privileges to the `hive` user.

    ```sql
    -- Create a database for Hive Metastore.
    create database hive;
    -- Create a user and password for Hive Metastore.
    create user 'hive'@'%' identified by '123456';
    -- Grant privileges to the user.
    grant all privileges on hive.* to 'hive'@'%' identified by '123456';
    -- Flush privileges.
    flush privileges;
    ```

4. Set the configuration item.

    ```sql
    set global tidb_skip_isolation_level_check=1;
    ```

    If you don't set the configuration item, Metastore throws the following exception when it is running:

    ```java
    MetaException(message:The isolation level 'SERIALIZABLE' is not supported. Set tidb_skip_isolation_level_check=1 to skip this error)
    ```

#### Step 2: Configure Hive

1. Download and decompress Hive. In this example, the decompression directory for Hive is ${HIVE_HOME}.

2. To edit the `hive-site.xml` configuration file, run `vim ${HIVE_HOME}/conf/hive-site.xml`. (The configuration items only use the minimum configuration.)

    ```xml
    <configuration>
      <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:mysql://host:port/hive</value>
        <description>TiDB address</description>
      </property>

      <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>hive</value>
        <description>TiDB username</description>
      </property>

      <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>123456</value>
        <description>TiDB password</description>
      </property>

      <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>com.mysql.jdbc.Driver</value>
      </property>

      <property>
        <name>hive.metastore.uris</name>
        <value>thrift://localhost:9083</value>
      </property>

      <property>
        <name>hive.metastore.schema.verification</name>
        <value>false</value>
      </property>
    </configuration>
    ```

3. To edit the `hive-env.sh` configuration file, run `vim ${HIVE_HOME}/conf/hive-env.sh`.

    ```bash
    export HADOOP_HOME=...
    export JAVA_HOME=...
    ```

4. Copy `mysql-connector-java-${version}.jar` to the lib directory in Hive.

    ```bash
    cp ${MYSQL_JDBC_PATH}/mysql-connector-java-${version}.jar ${HIVE_HOME}/lib
    ```

#### Step 3: Initialize metadata

You're performing this step to create a table for Hive metadata. The SQL script is in `${HIVE_HOME}/scripts/metastore/upgrade/mysql`.

To initialize metadata, run the following command.

```bash
${HIVE_HOME}/bin/schematool -dbType mysql -initSchema --verbose
```

When `schemaTool completed` appears in the last line, it means the metadata is successfully initialized.

#### Step 4: Launch Metastore and test

1. Launch Metastore.

    ```bash
    ${HIVE_HOME}/bin/hive --service metastore
    ```

2. Start the Hive client for testing.

    ```bash
    ${HIVE_HOME}/bin/hive
    ```

## Conclusion

If you use MySQL as the Hive Metastore database, as data grows in Hive, MySQL might become the bottleneck for the entire system. In this case, TiDB is a good solution, because it **is compatible with the MySQL protocol and has excellent horizontal scalability.** Due to its distributed architecture, **TiDB far outperforms MySQL on large data sets and large numbers of concurrent queries**.

This post showed how to deploy a Hive cluster with TiDB as the Metastore database. We hope TiDB can help you horizontally scale your Hive Metastore to meet your growing business needs.

In addition, if you're interested in our MySQL-to-TiDB migration story, check out [this post](https://en.pingcap.com/case-studies/horizontally-scaling-hive-metastore-database-by-migrating-from-mysql-to-tidb).
