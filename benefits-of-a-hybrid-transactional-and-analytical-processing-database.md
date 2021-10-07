---
title: The Benefits of a Hybrid Transactional and Analytical Processing Database
author: ['Rick Golba']
date: 2021-10-07
summary: Hybrid Transactional and Analytical Processing, or HTAP, is a defining feature of TiDB. It means that you can run both transactional and analytical queries from within the same database. TiDB provides HTAP, ensuring that your queries are always running against the most current data available.
tags: ['HTAP', 'Real-time analytics']
categories: ['Product']
image: /images/blog/benefits-of-a-htap-database.png
---

**Author:** Rick Golba (Product Marketing Manager at PingCAP)

**Editors:** Fadi Azhari, [Ran Huang](https://github.com/ran-huang), [Calvin Weng](https://github.com/dcalvin), Tina Yang

![The Benefits of a Hybrid Transactional and Analytical Processing Database](media/benefits-of-a-htap-database.png)

Hybrid Transactional and Analytical Processing (HTAP) is a defining feature of [TiDB](https://pingcap.com/products/tidb/). But what is it and why is it so important in today's information processing space?

At its most basic, HTAP means that you can run both transactional and analytical queries from within the same database. But it is important that the database you use for this can handle both types of queries efficiently, and that is where things get complicated.

## Transactional and analytical queries

Transactional and analytical queries are similar in the way that they are written, but are used to serve different purposes. Transactional activities are those that support the day-to-day running of a business while analytical queries are used to provide the necessary information to support business decisions.

### Transactional queries

A transactional query is often used to complete a transaction, such as making a purchase. Another type of transactional query is a simple request for information from the database, such as reporting on the date of a transaction, given a searchable item, like a transaction ID, or username. In many cases, the generation of a report can also be run as a transactional query. For a credit card company, both the act of purchasing an item and the creation of your monthly bill would be managed through transactional queries.

In the case of a query that is intended to complete a sales transaction, it is important that the information be written to the database quickly so that charges can be recorded, inventory updated, and results reflected in a customer record. This is most easily accomplished by writing into a row store since all the necessary information can be written in a single step. With relational databases like MySQL, duplication of data, like all the user's information, can be minimized since that information is often stored in a linked table. By reducing the amount of data written for each transaction, we make the transaction run even faster. By storing the data by row, we need to write to the smallest number of tables to complete each write transaction.

In the case of a query that runs against a row store, we are usually looking for a single record of information or a subset of data. In that way, we reduce the number of tables that need to be accessed and can acquire the results quickly. Indexing can speed up queries even more, but there are some practical limits to what can be done with row store data.

### Analytical queries

Imagine a case where you wanted to know how many of your customers are based in Los Angeles, or California, or the United States, or all North America. A row store database could process a query like this, but it would not be an efficient way of gathering the data. To determine any one of the stated queries, the database would need to access the record for each customer and determine if their city, state, or country(ies) matched the request. Once it has determined that a match exists, it would increment a counter to return the result.

What if you had your data stored by column instead of by row? Now, the above-mentioned queries could be answered more quickly and with far less stress on your environment. Since each query is looking at data in a single column (either city, state, or country), less access from disk is needed, and the response can be submitted quickly. Even if we are looking for information that accesses a few of the fields in our database, for example, if we wanted to find how many people have the last name of Smith and live in California, we can still process this request much faster than would be possible with a row store.

As data volumes grow, the efficiency of the column store becomes more apparent. If you only have 1 million records, touching each one to respond to a query from a row store is an expensive, but reasonable, scenario. If you have 100 million records, the cost of accessing each record in a row store is considerably higher than the process needed to respond through a column store, since fewer disk access points are needed.

## Old world solutions

The solution that many companies have developed is to use a row store database for transactions and a separate column store database for analytics. Normally, the row store database is the database of record, since it is the first that receives the content. An Extract, Transform, and Load (ETL) process then copies that data from the row store to the column store. While this provides optimal storage for both types of queries, it also presents a host of potential problems.

First, the running of the ETL process is usually a scheduled task, meaning that there is some delay in getting the data into the column store. Second, this model means that at least 2 unique databases are being set up, maintained, and managed, adding to workload. Users need to know which database is better suited to respond to ad hoc queries, further adding confusion. Third, the ETL process can fail or have issues, causing out-of-sync issues. These issues are both labor and time-consuming and incur additional costs to the business.

Some other companies simply use their row store to process both transactional and analytical queries. While this may work in the near term, as data volumes grow and users become ever more impatient for results, this model is not sustainable for many organizations.

## The TiDB solution

TiDB solves this problem by [writing the data to both a row and column store](https://pingcap.com/blog/how-we-build-an-htap-database-that-simplifies-your-data-platform) before committing the transaction. You get the speed of the row store for transaction processing and access to the data in an efficient column store for real-time analytics. If there is an issue with writing the transaction, it does not appear in either store, keeping your data in sync.

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('The Benefits of a Hybrid Transactional and Analytical Processing Database', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('The Benefits of a Hybrid Transactional and Analytical Processing Database', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Sample use cases

This can be important in a variety of situations. Let's consider purchases made with a credit card. In this example, the first transaction is a purchase made at a store in California. It may seem that the only requirement for this transaction is the recording of the transaction, but there is more that takes place in the background to validate the transaction before processing it. When the purchase request is made, there is also a validation of the transaction: does this fit your purchase patterns, does the purchase location make sense, and more. If, for example, you normally make small purchases of under $1000 and you are now purchasing a $15000 piece of jewelry, that may seem a little suspicious. That part of the transaction requires analysis of patterns and past usage and must be responded to quickly. If everything seems to be OK with the purchase, then it will be submitted as a sales transaction.

However, a short time later, the same credit card information is presented to complete a sale in another state, far from the location of the first purchase. During the verification process, it is important that the credit card company can compare this request against the earlier transaction that was completed in California. If the California transaction had not been copied over to the analytics database, due to the timing or a failure of the ETL process, it is likely that the new transaction is not considered questionable.

When using TiDB, the initial transaction is immediately recorded in both the row and column store. Now, when the second transaction is attempted, it will be flagged as questionable since neither you nor your credit card can be in 2 places at the same time. Even if the second transaction is being made by the valid cardholder, that cardholder is quickly made aware of the fraudulent use and can take action to stop additional transactions.

Similarly, in the gaming world, it is important that game response can reflect actions taken by players in real-time. While each player action is a transaction, the game can adapt to individual users by analyzing their normal behaviors within the game. It can recommend activities, suggest different options, and improve overall interaction with the game. With HTAP, a leader board can also be continuously updated, and players feel more engaged in the game.

The Internet of Things (IoT) means that multiple devices, from our phones to our cars, are connected and feeding information back to the provider. With the ability to run queries against a continuous flow of incoming data, predictive analytics becomes a reality, meaning that your car can now display a suggestion for an oil change based on data trends and engine needs rather than the older method that relied solely on distance traveled since the last change.

TiDB processes both the transaction and the analysis against the same set of data, enabling real-time results. There is no need for an ETL process, which may cause delays or errors. When a query is submitted, the query optimizer determines whether it is better served by the row or column store, so your application continues to submit requests in the usual way. This also lessens confusion on users since they always query the same database. Since TiDB is [MySQL compatible](https://docs.pingcap.com/tidb/stable/mysql-compatibility), few, if any, changes need to be made to your application. Workload is also lessened since there is a single database that serves the application. There can also be significant cost savings since TiDB often requires a lower number of computing devices.

## Summary

TiDB provides HTAP, ensuring that your queries are always running against the most current data available. By storing the information in both a row and column store, efficiency is improved, computing resources are used appropriately, maintenance is reduced, and overall workload is lessened. Your application continues to function with TiDB; it just functions faster and more efficiently. Companies around the world have seen the benefits of TiDB and it is in use at financial firms, gaming companies, payment processing providers, and more.

Review our [documentation](https://docs.pingcap.com/tidb/stable/quick-start-with-htap) for more detailed information about how TiDB enables a Hybrid Transactional and Analytical Processing environment. You can also read a recent [blog post](https://pingcap.com/blog/empower-your-business-with-big-data-real-time-analytics-in-tidb) about real-time analytics.

PingCAP is hosting [a webinar discussing HTAP](https://bit.ly/HTAP_PingCAP) on October 19, 2021. Tim Tadeo, one of our Solutions Architects, will discuss the importance of an HTAP database, present some of the challenges that it helps to overcome, and show how TiDB solves those issues. There will also be a demo of TiDB to illustrate how queries are processed and run faster in a hybrid environment. Click [here](https://bit.ly/HTAP_PingCAP) to register.
