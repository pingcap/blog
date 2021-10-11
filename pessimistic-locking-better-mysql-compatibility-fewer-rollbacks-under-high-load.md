---
title: 'Pessimistic Locking: Better MySQL Compatibility, Fewer Rollbacks Under High Load'
author: [Transaction team]
date: 2020-05-22
summary: With improvements in stability and functionality in TiDB 4.0, we finally remove the experimental label for pessimistic locking, making it a generally available feature. See how pessimistic locking behaves in TiDB.
tags: ['Transaction']
categories: ['Product']
image: /images/blog/pessimistic-locking.jpg
---

<!-- markdownlint-disable MD037 -->

**Author:** The Transaction team at PingCAP

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![Concurrency control in database](media/pessimistic-locking.jpg)

It's critical for modern distributed databases to provide fully ACID transactions. Distributed transactions require some form of concurrency control to guarantee that transactions are executed serially. The choice of concurrency control algorithm affects transaction restrictions and performance under high contention. That's why we did something about it.

Since 2015, we at [PingCAP](https://pingcap.com/) have been building [TiDB](https://docs.pingcap.com/tidb/v4.0/overview), an open-source, MySQL-compatible, distributed SQL database. When MySQL users use TiDB, they don't need to modify much application code and can onboard TiDB more easily. It's known that MySQL uses pessimistic locking as its concurrency control method to ensure data consistency. **TiDB supports pessimistic locking, which improves TiDB's compatibility with MySQL and reduces transaction rollback rates in high-conflict scenarios.** Before TiDB 4.0, pessimistic locking was an experimental feature. Now we've improved its performance, stability, and compatibility with MySQL. Pessimistic locking becomes generally available in TiDB 4.0.

In this post, I'll explain what pessimistic locking is, how it behaves, and how it differs from the MySQL version of pessimistic locking.

## What is pessimistic locking?

There are two common concurrency control mechanisms in the database field:

* **[Optimistic concurrency control](https://en.wikipedia.org/wiki/Optimistic_concurrency_control) (OCC)** allows multiple transactions to modify data without interfering with each other. While a transaction is running, the data that will be edited isn't locked. Before a transaction commits, optimistic concurrency control checks whether a conflicting modification exists. If a conflict exists, the committing transaction is rolled back.
* **Pessimistic concurrency control**: when a transaction is modifying data, pessimistic locking applies a lock to the data so other transactions can't access the same data. After the transaction commits, the lock is released.

Pessimistic concurrency control can solve some of the issues caused by optimistic concurrency control. TiDB now implements both pessimistic and optimistic concurrency control mechanisms, which means:

* **Transaction commits in TiDB won't fail due to locking issues except deadlocks.**
* **MySQL users can use TiDB more easily.** MySQL supports pessimistic locking by default. Now TiDB also supports pessimistic locking, so MySQL users don't need to modify much application code to get started with TiDB.

To help you better understand the two locking models, let's take online shopping as an analogy.

Assume that there are two websites where you can shop online. To complete an order, you choose an item, click "Add to Cart" to add the item to the shopping cart, check out, and place an order. But you have different shopping experiences on the two websites:

<table>
  <tr>
   <td><strong>Website</strong>
   </td>
   <td><strong>Add to Cart</strong>
   </td>
   <td><strong>Place an order</strong>
   </td>
  </tr>
  <tr>
   <td>A
   </td>
   <td>Quick and usually succeeds
   </td>
   <td>When products are out of stock, the order fails
   </td>
  </tr>
  <tr>
   <td>B
   </td>
   <td>Slower; if a product is out of stock, the request may fail
   </td>
   <td>Usually succeeds
   </td>
  </tr>
</table>

In this case, Website A uses optimistic concurrency control, while Website B uses pessimistic locking.

### Optimistic concurrency control in online shopping

Website A uses optimistic concurrency control. If you try to buy something, you can quickly add items to your shopping cart, but:

* You might fail to place an order.
* If other people place an order for the same item before you, the inventory changes. You may encounter a conflict and have to reorder.
* In scenarios with severe conflicts and high retry costs, for example, when you want to buy 10,000 items in a single order, you will probably fail to place an order.

### Pessimistic locking in online shopping

Website B uses pessimistic locking. It assumes that other buyers who add the same item before you might also place an order before you. So the inventory you see doesn't include items which are already in someone else's cart.

If you shop on Website B, you get this kind of experience:

* When you click "Add to Cart", the system responds a little slower.
* If you successfully add an item to your shopping cart, you'll succeed in placing an order.

## TiDB's pessimistic locking behavior

In TiDB, you can enable pessimistic locking in multiple ways. For details, see [TiDB Pessimistic Transaction Model](https://pingcap.com/docs/stable/reference/transactions/transaction-pessimistic/). In this section, I'll use three examples to introduce TiDB pessimistic locking's behaviors.

Note that in these example:

* We set the session `tidb_txn_mode` = 'pessimistic'. It will make the following transactions in this session work in the pessimistic mode.
* We set the global `tidb_txn_mode` = 'pessimistic'. You can also set the `tidb_txn_mode` in a global scope. It will affect the following new sessions. All of them will run in the pessimistic mode. We will use this setting for the following sections.
* To achieve compatibility with MySQL syntax, we add the comment `BEGIN / *! 90000 PESSIMISTIC * /;`.

### Update the same row concurrently

In the table below, assume that we have set the global `tidb_txn_mode` = 'pessimistic', and that Session A and Session B are new sessions. Both sessions use pessimistic locking and update the same row concurrently. From top to bottom, here are Session A's and Session B's operations in chronological order:

<table>
  <tr>
   <td><strong>Session A</strong>
   </td>
   <td><strong>Session B</strong>
   </td>
  </tr>
  <tr>
   <td>> BEGIN;
   </td>
   <td>> BEGIN;
   </td>
  </tr>
  <tr>
   <td>> UPDATE test SET v = v + 1 WHERE k = 1;
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>> UPDATE test SET v = v + 1 WHERE k = 1;
<br/>
<span style="color: red;">block...</span>
   </td>
  </tr>
  <tr>
   <td>> COMMIT;
   </td>
   <td><span style="color: red;">Query OK, 1 row affected (0.00 sec)</span>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>> COMMIT;
<br/>
<span style="color: red;">Query OK, 0 row affected (0.00 sec)</span>
   </td>
  </tr>
</table>

We can see in the pessimistic locking model:

* When Session B tries to execute a data manipulation language (DML) statement, it finds that Session A has locked the same row. After Session A commits its update, Session B executes the DML statement.
* When Session B successfully executes the DML statement, the final commit also succeeds.

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('Pessimistic Locking: Better MySQL Compatibility, Fewer Rollbacks Under High Load', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Pessimistic Locking: Better MySQL Compatibility, Fewer Rollbacks Under High Load', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Isolation

Let's look at the following table to see the transaction isolation:

<table>
  <tr>
   <td><strong>Session A</strong>
   </td>
   <td><strong>Session B</strong>
   </td>
  </tr>
  <tr>
   <td>> BEGIN;
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>> SELECT * FROM test;
<br/>
+------+------+
<br/>
|     k  |   v    |
<br/>
+------+------+
<br/>
|    1   |   1    |
<br/>
+------+------+
   </td>
   <td>> UPDATE test SET v = v + 1 WHERE k = 1;
   </td>
  </tr>
  <tr>
   <td>> SELECT * FROM test;
<br/>
+------+------+
<br/>
|     k  |   v    |
<br/>
+------+------+
<br/>
|    1   |   1    |
<br/>
+------+------+
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>> SELECT * FROM test FOR UPDATE; -- get an updated snapshot
<br/>
+------+------+
<br/>
|     k  |   v    |
<br/>
+------+------+
<br/>
|    1   |   2    |
<br/>
+------+------+
   </td>
   <td>
   </td>
  </tr>
</table>

This example shows that the TiDB pessimistic transaction's behavior is consistent with MySQL's pessimistic transactions:

* The isolation level of a non-locking read DML statement is snapshot isolation (SI). When the transaction begins, this statement reads the data.
* A normal `SELECT` statement always uses the snapshot at the beginning of the transaction, ensuring repeatable reads.

    As the statement is executed, the `SELECT FOR UPDATE` statement and other DML statements such as `INSERT`, `UPDATE`, `DELETE`, and `REPLACE` get an updated snapshot to read the data and lock it.

### Deadlock

Let's see what may happen when a deadlock occurs.

Taking shopping online as an example, suppose that both User A and User B want to buy masks and disinfectant. User A has all the disinfectant in his shopping cart, but he doesn't have any masks; User B has all the masks in his shopping cart, but he doesn't have any disinfectant.

If both Users A and B want to buy masks and disinfectant successfully, they should wait for each other to release some masks or disinfectant. Thus, a deadlock occurs.

Here's how a similar case looks in the database:

<table>
  <tr>
   <td><strong>Session A</strong>
   </td>
   <td><strong>Session B</strong>
   </td>
  </tr>
  <tr>
   <td>> BEGIN;
   </td>
   <td>> BEGIN;
   </td>
  </tr>
  <tr>
   <td>> UPDATE test SET v = 2 WHERE k = 1;
   </td>
   <td><strong>> </strong>UPDATE test SET v = 1 WHERE k = 2;<strong> </strong>
   </td>
  </tr>
  <tr>
   <td>> UPDATE test SET v = 1 WHERE k = 2;
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td><strong>> UPDATE test SET v = 2 WHERE k = 1;</strong>
<br/>
<strong><span style="color: red;">ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction</span></strong>
   </td>
  </tr>
  <tr>
   <td>> COMMIT;
   </td>
   <td>
   </td>
  </tr>
</table>

In the example above, Sessions A and B meet a deadlock. In this case, TiDB's deadlock manager immediately detects the deadlock and returns an error to the client.

## Comparison with MySQL InnoDB

As a distributed SQL database, TiDB tries to maintain protocol compatibility with MySQL to benefit the majority of MySQL users. However, TiDB and MySQL differ in implementation. TiDB is not 100% compatible with MySQL in some details. For a complete list of incompatible behaviors between TiDB and MySQL, see [Differences with MySQL InnoDB](https://pingcap.com/docs/dev/pessimistic-transaction/#difference-with-mysql-innodb).

Here, I'll briefly discuss these differences:

* MySQL supports gap locking while TiDB does not.
* MySQL and TiDB have different behaviors for embedded `SELECT` statements.

### No gap lock in TiDB

A [gap lock](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html#innodb-gap-locks) is a lock on a gap between index records, or a lock on the gap before the first or after the last index record. MySQL supports gap locking while TiDB does not.

When the database can't guarantee that the data that matches the filter condition is unique:

* MySQL locks all the rows that the filter condition can cover, including rows that may not exist. It uses range locking or table locking.
* TiDB only locks the existing rows it reads.

The following table shows a specific comparison. Note that `id` is the primary key.

<table>
  <tr>
   <td><strong>Session A</strong>
   </td>
   <td><strong>Session B (MySQL)</strong>
   </td>
   <td><strong>Session B (TiDB)</strong>
   </td>
  </tr>
  <tr>
   <td>mysql> BEGIN;
<br/>
Query OK, 0 rows affected (0.00 sec)
<br/>

<br/>
mysql> SELECT * FROM t WHERE id>=10 AND id&lt;11 FOR UPDATE;
<br/>
<span style="color: red;">Empty set (0.00 sec)</span>
   </td>
   <td>
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>>BEGIN;
<br/>
Query OK, 0 rows affected (0.00 sec)
<br/>

<br/>
> SELECT * FROM t WHERE id>=10 AND id&lt;11 FOR UPDATE;
<br/>
<span style="color: red;">// block</span>
   </td>
   <td>> BEGIN;
<br/>
Query OK, 0 rows affected (0.00 sec)
<br/>

<br/>
> SELECT * FROM t WHERE id>=10 AND id&lt;11 FOR UPDATE;
<br/>
<span style="color: red;">Empty set (0.00 sec)</span>
   </td>
  </tr>
</table>

### Different embedded `SELECT` behaviors

When TiDB executes a DML statement that includes an embedded `SELECT`, TiDB does not lock the data in an embedded `SELECT`. By contrast, MySQL does.

<table>
  <tr>
   <td colspan="3" >CREATE TABLE t1 (a INT, b INT DEFAULT 0, PRIMARY KEY (a,b));
<br/>
INSERT INTO t1 (a,b) VALUES (1070109, 99);
<br/>
CREATE TABLE t2 (b INT, a INT, PRIMARY KEY (b));
<br/>
INSERT INTO t2 (b,a) VALUES (7,1070109);
   </td>
  </tr>
  <tr>
   <td><strong>Session A</strong>
   </td>
   <td><strong>Session B</strong>
   </td>
   <td><strong>MySQL vs. TiDB </strong>
   </td>
  </tr>
  <tr>
   <td>> BEGIN;
   </td>
   <td>SET innodb_lock_wait_timeout = 1;
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>> SELECT b FROM t2 WHERE b=7 FOR UPDATE;
   </td>
   <td>BEGIN;
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>SELECT b FROM t2 WHERE b=7 FOR UPDATE;
   </td>
   <td>Both MySQL and TiDB fail with an error `lock wait timeout`.
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>INSERT INTO t1 (a) VALUES ((SELECT a FROM t2 WHERE b=7));
   </td>
   <td>TiDB does not lock the data in `(SELECT a FROM t2 WHERE b=7)`, so it succeeds.
<br/>
MySQL tries to lock the data in `(SELECT a FROM t2 WHERE b=7)`, so it fails with an error `lock wait timeout`.
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>UPDATE t1 SET a='7000000' WHERE a=(SELECT a FROM t2 WHERE b=7);
   </td>
   <td>TiDB succeeds, while MySQL fails with an error `lock wait timeout`.
   </td>
  </tr>
</table>

## Looking ahead

Since it began, TiDB has been known for supporting high-performance distributed transactions. With improvements in stability and functionality in TiDB 4.0, we finally remove the experimental label for pessimistic locking, making it a generally available feature. In our future posts, we'll deep dive into TiDB pessimistic locking's implementation principles and performance tuning. Stay tuned.

TiDB's transaction model continues to improve. If you're interested, you can help build this cutting-edge distributed transaction model along with us. You're welcome to try our pessimistic locking in the [TiDB 4.0 release candidate](https://pingcap.com/docs/stable/releases/release-4.0.0-rc.2/) and join [our Transaction Special Interest Group (SIG) on Slack](https://slack.tidb.io/invite?team=tikv-wg&channel=transaction-sig&ref=pingcap-blog), or contact [transaction-group@pingcap.com](mailto:transaction-group@pingcap.com) to give us your feedback.
