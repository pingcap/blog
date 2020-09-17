---
title: 'ZaloPay: Using a Scale-Out MySQL Alternative to Serve Millions of Users'
author: ['Tan To Nguyen Duy']
date: 2020-09-17
summary: A DevOps engineer in ZaloPay, Vietnam's most popular mobile payment application, shared why his team chose TiDB as ZaloPay's merchant platform core database. He talked about their pain points, how they use TiDB, and what he likes about it the most.
tags: ['HTAP', 'DevCon','TiSpark','Real-time analytics']
url: /case-studies/zalopay-choosing-a-scale-out-database-to-serve-100-million-users/
customerCategory: Internet
categories: ['HTAP']
logo: /images/blog/customers/vng-logo.png
image: /images/blog/zalopay-user-story.jpg
---

![ZaloPay: Using a Scale-Out MySQL Alternative to Serve Millions of Users](media/zalopay-choosing-scale-out-mysql-alternative-database-tidb.jpg)

VNG is a leading internet technology company in Vietnam. Their flagship product, Zalo, is the most popular chat platform in Vietnam. [ZaloPay](https://www.facebook.com/zalopay.engineering/) is a mobile payment application built on top of Zalo. Today, more than 100 million users worldwide use ZaloPay to transfer money and make payments.

As the company's business rapidly expanded, data storage and data processing became a major and immediate concern. They needed a new infrastructure that could respond to the booming business.

At TiDB DevCon 2020, a DevOps engineer at VNG shared why his team chose TiDB as ZaloPay's merchant platform core database.

<iframe id="youtube-video" title="[DevCon 2020] Using TiDB as the Merchant Platform Core Database in ZaloPay" src="https://www.youtube.com/embed/I-1FHgpGdqw?rel=0" frameborder="0" allowfullscreen="allowfullscreen" mozallowfullscreen="mozallowfullscreen" msallowfullscreen="msallowfullscreen" oallowfullscreen="oallowfullscreen" webkitallowfullscreen="webkitallowfullscreen"></iframe>

<div class="caption-center"> [DevCon 2020] Using TiDB as the Merchant Platform Core Database in ZaloPay </div>

Here's a recap of what his team has learned.

## Our pain points at ZaloPay

*"We need a system that handles a very significant volume of users and non-stop scalability."*

In early 2020, we launched a new feature in ZaloPay that allows over 100 million active users in Zalo to do things such as money transfer, bill payments, mobile top-ups, and hotel/travel booking. Each merchant has an official fan page like a Facebook fan page, where Zalo users can browse products and easily make payments.

In the general billing section alone, we've got a many-hundred-thousand-transaction a day. This means that **our database needs to serve a million requests a day**.

Building an infrastructure that satisfies this massive user base to integrate with ZaloPay is no small challenge, but a very big concern. We cannot design our architecture and build services based on the old model, because the new system **requires scalability, resiliency, always-on availability, performance monitoring, and guaranteed security**. Also, it must **meet as many cloud patterns as possible**.

ZaloPay's system requires many flows of business transactions that are happening super tightly, in parallel with business analytics and recommendations swiftly. Our database must not only support **large-scale transactional queries** but also feed **real-time analytics** to our data analytics and recommendation systems.

## ZaloPay's database of choice: TiDB

While researching to find a suitable database solution, we found [TiDB](https://docs.pingcap.com/tidb/stable), a NewSQL database that supports Hybrid Transactional/Analytical Processing (HTAP) workloads and familiar MySQL protocol.

*> At ZaloPay, we use TiDB as a core database to store most of the payment transaction data, billing, config data, and customer data of many services (such as billing, traveling, and F&B integration). At the present time, we have more than 20 nodes in our production system, storing a lot of significant data. We're running TiDB and our other product on-premise (bare machine).*

*> TiDB acts as a MySQL 5.7 server and supports MySQL protocol and a majority of MySQL syntax. You can use all of the existing MySQL client's libraries. In many cases, you won't need to change a single line of code in your application.*

To learn more about how we use TiDB at ZaloPay, please see my other post, [TiDB at ZaloPay Infrastructure & Lesson Learned](https://pingcap.com/success-stories/tidb-at-zalopay-infrastructure-lesson-learned/#introducing-zalopay).

## HTAP: a one-stop solution for both transactions and analytics

*"TiDB is built to meet the needs of data development, data scalability, data analytics, et cetera! That's exactly what we want now and in the future."*

The main technical challenges for an HTAP database are how to be efficient both for many small transactions with a high fraction of updates and complex queries traversing a large number of rows on the same database system and how to prevent the interference of the analytical queries over the operational workloads.

Most HTAP applications are enabled by in-memory technologies that can process a high volume of transactions and that offer features such as forecasting and simulations. HTAP has the potential to change the way organizations do business by offering immediate business decision-making capabilities based on live and sophisticated analytics of large volumes of data. Business leaders can be informed of real-time issues, outcomes, and trends that require action, such as in the areas of risk management and fraud detection.

What I like most about TiDB is that I can analyze data very easily with [TiSpark](https://docs.pingcap.com/tidb/dev/tispark-overview). The tool is very useful in fast-growing business situations that require data storage scalability and analyze that bunch of data to give out business recommendations quickly.

I recommend these [HTAP](https://pingcap.com/blog/category/HTAP) blog posts if you want to learn more.

## Additional values TiDB has brought

Our slogan is "ZaloPay—Pay in Two Seconds." To achieve this goal, we have to improve many business and technical flows. We use Golang to implement services, which matches with TiDB implementation. Our engineers are familiar with Golang, so they can easily read and understand TiDB code, which makes it easy to optimize the performance of the service as well as the software between the applications and the TiDB database core.

TiDB is a **cloud-native database**, which makes it much easier to achieve the cloud pattern of our services and applications, including scalability, resiliency, and monitoring.

TiDB's open-source nature helps us better understand the principles and features of the database, as well as how it works.

TiDB has an active community and very helpful community support. Not too long ago, we had some trouble using and maintaining services with TiDB. I went to the PingCAP community, and I got very enthusiastic and dedicated support from the Senior Engineers, VP of Engineering, and professional community staff. They helped us investigate and fix problems. Not every open-source organization or individual will do that.

## Last word

Data can be plentiful, spawned, and found everywhere. Although recognizing it as a gold mine, not many people or organizations can afford to mine that pile of data because of technological and human limitations. The right database helps you get the most out of your data and turn data into decisions.

Again, thank you PingCAP for the great open-source product and professional support.
