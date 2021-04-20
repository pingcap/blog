---
title: Lessons from TiDB's No. 1 Bug Hunters Who've Found 400+ Bugs in Popular DBMSs
author: ['Manuel Rigger']
date: 2020-10-06
summary: Dr. Manuel Rigger and his colleague have found 400+ bugs in popular DBMSs, including 50+ TiDB bugs. Learn their experience in finding logic bugs in DBMSs.
tags: ['Bug fix', 'DevCon']
categories: ['Engineering']
image: /images/blog/find-database-bugs.jpg
---

**Author:** [Manuel Rigger](https://www.manuelrigger.at/) (Postdoctoral researcher at ETH Zurich)

**Transcreator:** [Caitin Chen](https://github.com/CaitinChen); **Editor:** Tom Dewan

![Database bug, database test](media/find-database-bugs.jpg)

## Summary

Finding logic bugs is an important part of building a reliable Database Management System (DBMS). But sometimes the most obvious approach doesn't work. You can't just query several databases and compare the results. You need a more sophisticated bug-hunting approach.

That's why we wanted you to meet Manuel Rigger. In this video, Manuel, a postdoctoral fellow at ETH Zurich, describes the techniques that have made him and his colleague, Professor Zhendong Su, [TiDB](https://docs.pingcap.com/tidb/stable/overview)'s #1 [bug hunters](https://github.com/tidb-challenge-program/bug-hunting-register). They've **found over 50 TiDB bugs**, and when you factor in their work with other popular DBMSs, they've **found over 400**.

Imagine what you could learn from them and apply to your own database work.

Manuel evaluates three techniques for finding logic bugs. Then, he gives us a demo of Non-optimizing Reference Engine Construction (NoREC), a simple, but not obvious approach to finding optimization bugs. With this technique alone, Manuel and his colleague have **found over 150 bugs**.

As Manuel explains, the key to this method is rewriting query statements so the DBMS cannot optimize the query. Although this approach isn't intuitive, it's an effective way to find optimization bugs.

Manuel gave this talk at [TiDB DevCon 2020](https://pingcap.com/community/devcon2020/).Click the video link to watch Manuel take you step-by-step through his process. You can see the slides [here](https://www.slideshare.net/PingCAP-TiDB/finding-logic-bugs-in-database-management-systems).

<iframe id="youtube-video" title="Lessons from TiDB's #1 Bug Hunters" src="https://www.youtube.com/embed/z16m9MIxgMI?rel=0" frameborder="0" allowfullscreen="allowfullscreen" mozallowfullscreen="mozallowfullscreen" msallowfullscreen="msallowfullscreen" oallowfullscreen="oallowfullscreen" webkitallowfullscreen="webkitallowfullscreen"></iframe>
<div class="caption-center"> Lessons from TiDB's #1 bug hunters </div>

## Transcript

Hello, everyone. My name is Manuel Rigger. I am a postdoctoral fellow at ETH Zurich. I am very grateful to [PingCAP](https://pingcap.com/) for inviting me to introduce myself and my work. I am from Austria, 29 years old. I like to go hiking, go travelling, and play table tennis.

So, I'm back from hiking, and now I want to take a couple of minutes to give an overview of our work on finding logic bugs in Database Management Systems (DBMSs), which is a project that I've been working on together with Professor Zhendong Su, who leads the Advanced Software Technologies Lab at ETH Zurich.

So in our work, we have tested quite a number of popular and widely used DBMSs, including TiDB, and we've found over 400 bugs so far.

With respect to TiDB, we rank on place one in the [TiDB Bug-hunting Challenge Program](https://github.com/tidb-challenge-program/bug-hunting-register), and overall we've reported over 50 bugs, so far, for TiDB, also including those that we reported before this challenge.

But let's first get a step back now and talk about our goal. So, our goal is to detect logic bugs in DBMSs.

### What are logic bugs?

What are logic bugs? Well, I want to explain this on a concrete example. Namely, we have a client application, which sends a SQL query to the DBMS, which is TiDB in our case. Then, the DBMS is supposed to go through all the relevant records. So in this example here, we have three records, two for which the condition—this predicate here—evaluates to TRUE, and one for which it evaluates to FALSE. Consequently, we would expect that the result set that is returned comprises two rows; namely, those for which the condition evaluates to TRUE. However, in some cases it can happen that by sending the query to the DBMS, we trigger a bug, and in such a case it might happen that the result set that is returned is incorrect, such as in this case here, where only a single row rather than two are fetched, and we refer to these kinds of bugs as logic bugs. So those bugs, that result in the computation of an incorrect result set.

### Bug hunting methods

How could we tackle this? Well, the most obvious approach would be to use differential testing. Differential testing in this context basically means that we have a query generator, which we use to generate a query that we send to multiple DBMSs. For example, not only to TiDB, but also MariaDB and MySQL, which are the closest, or which are DBMSs with the closest SQL dialect to TiDB. Each of these DBMSs then fetches a result set, and we can compare all the three result sets in this example, and check if they are all the same. If not, we have likely found a bug in one of these systems. Unfortunately, differential testing is _not_ applicable for DBMSs.

Why do we claim this? Well, first of all, the common SQL core is rather small, and the DBMSs differ widely.

Now, for TiDB, you might argue that TiDB tries to support the MySQL SQL dialect to a large degree, but even there, we encountered a number of problems; for example, that MySQL and TiDB shared common bugs, in which case it was impossible to detect this. So, for example, here we opened a bug report where a TiDB developer mentioned that MySQL also is affected by the same underlying bug.

So, in order to tackle this we have been coming up with approaches to detect logic bugs in DBMSs. The first approach, or the approach that I focus on in my talk today, is Non-optimizing Reference Engine Construction (NoREC). NoREC is a simple, but also a non-obvious approach to finding specifically optimization bugs.

Then, another approach that we have been working on is Pivoted Query Synthesis (PQS), which is a more powerful technique, but also more elaborate—and this point, I want to mention that PingCAP is actually the first company which has adopted this approach. Also other companies are following now, but Qiang Zhou (Efficiency Improvement Team Manager at PingCAP) and his team—they have successfully implemented it as the first company, so I want to thank them for their effort. Then, Ternary Logic Query Partitioning (TLP) is work-in-progress, and this is the approach that we have actually used to find the bugs that we reported for TiDB.

### The NoREC method: not intuitive, but effective

But let's focus on NoREC now, which is a simple, but non-obvious approach that I can also explain in a couple of minutes. And it allowed us to find over 150 bugs in widely-used DBMSs.

So as I mentioned, the approach specifically aims to find optimization bugs, which are an important subcategory of logic bugs. Namely, we can take the original motivating example and assume that the bug is caused by a bug in the query optimizer of TiDB, which causes this row to be omitted from the result set.

Now, what we would like to have is the following: Namely, we would like to have a version of TiDB where all the optimizations are enabled, and one where all of them are disabled. So, if you are familiar with C/C++ compilers like GCC or LLVM, you might know these optimization flags, where basically -O0 means that the majority of optimizations are turned off, and -O3, where the majority of optimizations are turned on. And, if you would have something like this, we could directly compare the result sets and spot errors caused by the query optimizer. Unfortunately, TiDB, but also the other DBMSs that we considered provide limited control over optimizations, so only a couple of options or flags, which do not help in detecting the majority of bugs.

So the idea that we had was that rather than relying on the DBMS, we could rewrite the query so that the DBMS cannot optimize it, and thus be able to find optimization bugs.

And we came up with the following translation routine. So, here you see the original query, where we have the WHERE rows and where the two rows are fetched for which the condition evaluates to TRUE. Now, the idea here is that we can basically take the condition from the WHERE clause and move it directly after the SELECT. And the question is: What effect does this now have? Well, this basically means that this predicate or condition is evaluated on every row in these tables here. Since we have three records in these tables, namely, two where the condition evaluates to TRUE and one where it evaluates to FALSE, we expect that the result set with three rows is returned, namely, two with the value TRUE, and one with value FALSE. There, we can basically see that for two rows the condition evaluates true. We can simply compare these two, and validate for this example here, that the expected result is computed.

And the intuition here is that the translated query cannot be efficiently optimized by the DBMS, because DBMSs typically try to be smart about only inspecting the necessary records, but here this condition has to be evaluated on every record, which disables most of the optimizations. So, if now there is a bug in the query optimizer—and for this example only a single row is fetched—we are able to detect these bugs, since there is a mismatch between the two rows for which the predicate evaluates to TRUE and the one row that is actually fetched. And this is basically already the approach that allowed us to detect this many bugs.

The concrete implementation of this approach: We implemented it in SQLancer, which soon will be available on GitHub, and SQLancer performs the following steps when using NoREC. First, it randomly generates a database, then it generates the optimized query, from which it derives the unoptimized query, and validates the result by checking that the optimized and unoptimized query are the same.

And with that, I want to also give you a short demo to actually demonstrate that our approach works in practice and could have found many of the bugs in TiDB that we already reported.

So here you can see a bug report. This was a P1 bug, so quite a severe bug, and you can see here that we create a table, we then create a view, we insert into the table, and then we have this query here that fetches records from this.

So I'm copying now these SQL statements. And here I'm going to feed them to TiDB. Let's not look too deeply into what the query should actually do, but let's observe that here now an empty result set is returned. Now, let's translate this to the unoptimized query. So I'm adding here this IS TRUE to force that the predicate is evaluated as a Boolean. And here you can actually see now that a row is returned with a value of 1, which basically means TRUE. And since we see here that a TRUE value is returned, we can infer that actually this query here [the one above] should have returned a single record, which was not the case, and thus, we would have been able to detect this bug in TiDB.

So, I hope that I could convince you that this simple, but non-obvious approach is actually quite useful to detect bugs, and I hope also that this overview of our ongoing research was interesting for you, and I hope you will have fun at the conference. And with this I say, thank you for listening and 加油 ("come on") TiDB.
