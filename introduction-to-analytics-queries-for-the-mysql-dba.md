---
title: Introduction to Analytics Queries for the MySQL DBA
author: ['Morgan Tocker']
date: 2019-03-28
summary: This post introduces some simple use cases of analytics queries where a MySQL DBA can expand their repertoire and answer some basic business questions by writing SQL queries with window functions.
tags: ['MySQL', 'Tutorial']
categories: ['Product']
---

If you come to [TiDB](https://github.com/pingcap/tidb), an open source NewSQL database, from a MySQL background, you are likely comfortable with transaction processing workloads, but analytics may be new to you.

I know in my case, as someone who's spent more than 15 years in the MySQL world, while I can explain how redo log flushing works in InnoDB, only until recently did it become natural for me to write a simple query with a window function.

So in this post, I want to go through some simple use cases where a MySQL DBA can expand their *repertoire* and answer some basic business questions by writing SQL queries with window functions. This knowledge could add a lot of value, especially if you work at a company that doesn't yet have a full-fledged data science team, but is already doing some analytics.

Our sample data set will be the 30 years of USA flight on-time statistics [loaded](https://github.com/Percona-Lab/ontime-airline-performance) into [TiDB 3.0 BETA](https://pingcap.com/blog/tidb-3.0-beta-stability-at-scale/).

## Finding the average arrival delay

Our sample data set includes all the flights in the U.S. and their on-time performance. But for your purposes, it could equally be the initial wait time a customer experiences before receiving customer service per location that you operate, or the average spend per customer per sales person.

One of the most common types of queries you will need to do is to show the average for one group, and compare that to the previous year. Here is the query to do that:

```sql
SET tidb_enable_window_function = 1;
SELECT
  year,
  UniqueCarrier,
  COUNT(*) AS Flights,
  AVG(ArrDelay) AS avgArrDelay,
  lag(AVG(ArrDelay), 1)
    OVER (PARTITION BY UniqueCarrier ORDER BY year)
    AS prevAvgArrDelay,
  lag(AVG(ArrDelay), 1)
    OVER (PARTITION BY UniqueCarrier ORDER BY year)-AVG(ArrDelay)
    AS improvement
FROM ontime
WHERE UniqueCarrier IN ('AA', 'UA', 'DL')
GROUP BY UniqueCarrier, year
ORDER BY year, UniqueCarrier;
+------+---------------+---------+-------------+-----------------+-------------+
| year | UniqueCarrier | Flights | avgArrDelay | prevAvgArrDelay | improvement |
+------+---------------+---------+-------------+-----------------+-------------+
| 1987 | AA            |  165121 |      4.8399 |            NULL |        NULL |
| 1987 | DL            |  185813 |     11.7843 |            NULL |        NULL |
| 1987 | UA            |  152624 |      8.5594 |            NULL |        NULL |
| 1988 | AA            |  694757 |      4.1720 |          4.8399 |      0.6679 |
| 1988 | DL            |  753983 |      6.1164 |         11.7843 |      5.6679 |
| 1988 | UA            |  587144 |      7.2269 |          8.5594 |      1.3325 |
| 1989 | AA            |  723252 |      6.0706 |          4.1720 |     -1.8986 |
| 1989 | DL            |  783320 |      8.3806 |          6.1164 |     -2.2642 |
| 1989 | UA            |  574674 |     11.0119 |          7.2269 |     -3.7850 |
| 1990 | AA            |  712060 |      6.4061 |          6.0706 |     -0.3355 |
| 1990 | DL            |  824062 |      9.3586 |          8.3806 |     -0.9780 |
| 1990 | UA            |  606713 |      7.3276 |         11.0119 |      3.6843 |
| 1991 | AA            |  725191 |      3.8323 |          6.4061 |      2.5738 |
| 1991 | DL            |  874791 |      6.6681 |          9.3586 |      2.6905 |
| 1991 | UA            |  630093 |      6.5496 |          7.3276 |      0.7780 |
| 1992 | AA            |  782371 |      5.1185 |          3.8323 |     -1.2862 |
| 1992 | DL            |  916593 |      7.4197 |          6.6681 |     -0.7516 |
| 1992 | UA            |  639349 |      4.8295 |          6.5496 |      1.7201 |
| 1993 | AA            |  786696 |      5.9946 |          5.1185 |     -0.8761 |
| 1993 | DL            |  898896 |      8.5415 |          7.4197 |     -1.1218 |
| 1993 | UA            |  649086 |      6.7061 |          4.8295 |     -1.8766 |
| 1994 | AA            |  722277 |      5.6174 |          5.9946 |      0.3772 |
| 1994 | DL            |  874526 |      6.4898 |          8.5415 |      2.0517 |
| 1994 | UA            |  638750 |      5.0592 |          6.7061 |      1.6469 |
| 1995 | AA            |  688471 |      7.1322 |          5.6174 |     -1.5148 |
| 1995 | DL            |  884019 |      8.1233 |          6.4898 |     -1.6335 |
| 1995 | UA            |  724807 |      7.0768 |          5.0592 |     -2.0176 |
| 1996 | AA            |  655539 |     10.6212 |          7.1322 |     -3.4890 |
| 1996 | DL            |  888306 |     11.2632 |          8.1233 |     -3.1399 |
| 1996 | UA            |  735266 |      9.9883 |          7.0768 |     -2.9115 |
| 1997 | AA            |  663954 |      4.7461 |         10.6212 |      5.8751 |
| 1997 | DL            |  921850 |      9.3616 |         11.2632 |      1.9016 |
| 1997 | UA            |  743847 |      8.4969 |          9.9883 |      1.4914 |
| 1998 | AA            |  653919 |      4.2881 |          4.7461 |      0.4580 |
| 1998 | DL            |  915095 |      5.6418 |          9.3616 |      3.7198 |
| 1998 | UA            |  748459 |     10.6677 |          8.4969 |     -2.1708 |
| 1999 | AA            |  692653 |      8.5167 |          4.2881 |     -4.2286 |
| 1999 | DL            |  914130 |      6.5076 |          5.6418 |     -0.8658 |
| 1999 | UA            |  774370 |      9.5113 |         10.6677 |      1.1564 |
| 2000 | AA            |  742265 |      9.3036 |          8.5167 |     -0.7869 |
| 2000 | DL            |  908029 |      7.9747 |          6.5076 |     -1.4671 |
| 2000 | UA            |  776559 |     17.3881 |          9.5113 |     -7.8768 |
| 2001 | AA            |  716985 |      5.5074 |          9.3036 |      3.7962 |
| 2001 | DL            |  835236 |      4.7777 |          7.9747 |      3.1970 |
| 2001 | UA            |  704977 |      8.1830 |         17.3881 |      9.2051 |
| 2002 | AA            |  852439 |      1.1673 |          5.5074 |      4.3401 |
| 2002 | DL            |  728758 |      5.6401 |          4.7777 |     -0.8624 |
| 2002 | UA            |  587887 |      2.4105 |          8.1830 |      5.7725 |
| 2003 | AA            |  752241 |      3.1490 |          1.1673 |     -1.9817 |
| 2003 | DL            |  660617 |      3.8085 |          5.6401 |      1.8316 |
| 2003 | UA            |  543957 |      3.0751 |          2.4105 |     -0.6646 |
| 2004 | AA            |  698548 |      7.9799 |          3.1490 |     -4.8309 |
| 2004 | DL            |  687638 |      8.0693 |          3.8085 |     -4.2608 |
| 2004 | UA            |  555812 |      5.8948 |          3.0751 |     -2.8197 |
| 2005 | AA            |  673569 |      8.1702 |          7.9799 |     -0.1903 |
| 2005 | DL            |  658302 |      7.6846 |          8.0693 |      0.3847 |
| 2005 | UA            |  485918 |      7.4487 |          5.8948 |     -1.5539 |
| 2006 | AA            |  643597 |      9.4219 |          8.1702 |     -1.2517 |
| 2006 | DL            |  506086 |      6.8902 |          7.6846 |      0.7944 |
| 2006 | UA            |  500008 |     10.2646 |          7.4487 |     -2.8159 |
| 2007 | AA            |  633857 |     13.9857 |          9.4219 |     -4.5638 |
| 2007 | DL            |  475889 |      7.1869 |          6.8902 |     -0.2967 |
| 2007 | UA            |  490002 |     12.4171 |         10.2646 |     -2.1525 |
| 2008 | AA            |  604885 |     12.2029 |         13.9857 |      1.7828 |
| 2008 | DL            |  451931 |      7.7162 |          7.1869 |     -0.5293 |
| 2008 | UA            |  449515 |     11.0016 |         12.4171 |      1.4155 |
| 2009 | AA            |  551597 |      6.2162 |         12.2029 |      5.9867 |
| 2009 | DL            |  428007 |      4.7114 |          7.7162 |      3.0048 |
| 2009 | UA            |  377049 |      1.3351 |         11.0016 |      9.6665 |
| 2010 | AA            |  540963 |      3.7431 |          6.2162 |      2.4731 |
| 2010 | DL            |  732973 |      5.3897 |          4.7114 |     -0.6783 |
| 2010 | UA            |  343081 |     -3.9465 |          1.3351 |      5.2816 |
| 2011 | AA            |  538179 |      5.1049 |          3.7431 |     -1.3618 |
| 2011 | DL            |  732331 |      1.7066 |          5.3897 |      3.6831 |
| 2011 | UA            |  311212 |      2.6463 |         -3.9465 |     -6.5928 |
| 2012 | AA            |  525220 |      6.2599 |          5.1049 |     -1.1550 |
| 2012 | DL            |  726879 |     -0.7959 |          1.7066 |      2.5025 |
| 2012 | UA            |  531245 |      5.0069 |          2.6463 |     -2.3606 |
| 2013 | AA            |  537891 |      5.7763 |          6.2599 |      0.4836 |
| 2013 | DL            |  754670 |      1.9709 |         -0.7959 |     -2.7668 |
| 2013 | UA            |  505798 |      3.7126 |          5.0069 |      1.2943 |
| 2014 | AA            |  537697 |      8.1398 |          5.7763 |     -2.3635 |
| 2014 | DL            |  800375 |      2.2953 |          1.9709 |     -0.3244 |
| 2014 | UA            |  493528 |      6.8186 |          3.7126 |     -3.1060 |
| 2015 | AA            |  725984 |      3.3893 |          8.1398 |      4.7505 |
| 2015 | DL            |  875881 |      0.1856 |          2.2953 |      2.1097 |
| 2015 | UA            |  515723 |      5.3477 |          6.8186 |      1.4709 |
| 2016 | AA            |  914495 |      5.0123 |          3.3893 |     -1.6230 |
| 2016 | DL            |  922746 |     -0.5527 |          0.1856 |      0.7383 |
| 2016 | UA            |  545067 |      1.7335 |          5.3477 |      3.6142 |
| 2017 | AA            |  896348 |      3.7901 |          5.0123 |      1.2222 |
| 2017 | DL            |  923560 |     -0.0739 |         -0.5527 |     -0.4788 |
| 2017 | UA            |  584481 |      1.7156 |          1.7335 |      0.0179 |
| 2018 | AA            |  766133 |      5.5236 |          3.7901 |     -1.7335 |
| 2018 | DL            |  798041 |      0.1130 |         -0.0739 |     -0.1869 |
| 2018 | UA            |  518243 |      5.5611 |          1.7156 |     -3.8455 |
+------+---------------+---------+-------------+-----------------+-------------+
96 rows in set (1 min 25.95 sec)
```

**Note:** I have reduced the results to UA (United Airlines), DL (Delta) and AA (American) for readability.

So in this query we are using a *window function* named LAG() to find the previous row. The window is defined as `(PARTITION BY UniqueCarrier ORDER BY year)`.

You can think of window functions like a GROUP BY, but the rows don't collapse. The name literally comes from peeking through a window to observe other rows in the result.

## Sharpening our statistics skills

In the previous example, we used the average or statistical mean. Let's now discuss why that might not be the best approach.

The mean sums up all of the values, and then divides the total by the number of values. By *design* each value contributes to the final mean. So take the following examples:

```
# Series A
97.5
98.1
98.5
98.8
99.2
Average=98.42
```

```
# Series B
97.5
98.2
104.0
97.7
98.1
Average=99.1
```

The average between these two series is not that much different, but you will notice that there is one anomaly in Series B with a value of 104.0. Now let me tell you that each one of these numbers refers to a temperature sample taken from a patient in a hospital.

By looking only at the average, we wouldn't see the fact that a person in series B has a high fever. The *outlier* is washed away by a series of typical values in sequence.

I use this example to prove a point, but it is actually **even worse** in the case of our flight statistics data. An early arrival will subtract from the average, which resulted in some of the averages in the first result even being negative!

A more statistically sound approach would be to know how many times a customer had a frustrating experience, for example how many times is the ArrDelay greater than 30 minutes? What about greater than 4 hours? Here's the query for that:

```sql
SELECT
  year,
  UniqueCarrier,
  COUNT(*) AS Flights,
  COUNT(CASE WHEN ArrDelay>=30 THEN 1 END) as AtLeast30Delayed,
  COUNT(CASE WHEN ArrDelay>=30 THEN 1 END)/COUNT(*)
    AS PctAtLeast30Delayed
FROM ontime
WHERE UniqueCarrier IN ('AA', 'UA', 'DL')
GROUP BY UniqueCarrier, year
ORDER BY year, UniqueCarrier;
+------+---------------+---------+------------------+---------------------+
| year | UniqueCarrier | Flights | AtLeast30Delayed | PctAtLeast30Delayed |
+------+---------------+---------+------------------+---------------------+
| 1987 | AA            |  165121 |            12346 |              0.0748 |
| 1987 | DL            |  185813 |            18888 |              0.1017 |
| 1987 | UA            |  152624 |            17274 |              0.1132 |
| 1988 | AA            |  694757 |            47368 |              0.0682 |
| 1988 | DL            |  753983 |            47947 |              0.0636 |
| 1988 | UA            |  587144 |            59490 |              0.1013 |
| 1989 | AA            |  723252 |            66833 |              0.0924 |
| 1989 | DL            |  783320 |            62688 |              0.0800 |
| 1989 | UA            |  574674 |            81840 |              0.1424 |
| 1990 | AA            |  712060 |            67445 |              0.0947 |
| 1990 | DL            |  824062 |            77552 |              0.0941 |
| 1990 | UA            |  606713 |            63128 |              0.1040 |
| 1991 | AA            |  725191 |            51298 |              0.0707 |
| 1991 | DL            |  874791 |            64441 |              0.0737 |
| 1991 | UA            |  630093 |            62718 |              0.0995 |
| 1992 | AA            |  782371 |            57435 |              0.0734 |
| 1992 | DL            |  916593 |            68987 |              0.0753 |
| 1992 | UA            |  639349 |            50734 |              0.0794 |
| 1993 | AA            |  786696 |            67134 |              0.0853 |
| 1993 | DL            |  898896 |            75070 |              0.0835 |
| 1993 | UA            |  649086 |            65217 |              0.1005 |
| 1994 | AA            |  722277 |            63183 |              0.0875 |
| 1994 | DL            |  874526 |            61312 |              0.0701 |
| 1994 | UA            |  638750 |            52269 |              0.0818 |
| 1995 | AA            |  688471 |            75638 |              0.1099 |
| 1995 | DL            |  884019 |            88067 |              0.0996 |
| 1995 | UA            |  724807 |            78906 |              0.1089 |
| 1996 | AA            |  655539 |            91140 |              0.1390 |
| 1996 | DL            |  888306 |           114817 |              0.1293 |
| 1996 | UA            |  735266 |            98186 |              0.1335 |
| 1997 | AA            |  663954 |            64981 |              0.0979 |
| 1997 | DL            |  921850 |           102956 |              0.1117 |
| 1997 | UA            |  743847 |            84287 |              0.1133 |
| 1998 | AA            |  653919 |            63789 |              0.0975 |
| 1998 | DL            |  915095 |            82049 |              0.0897 |
| 1998 | UA            |  748459 |           102644 |              0.1371 |
| 1999 | AA            |  692653 |            88601 |              0.1279 |
| 1999 | DL            |  914130 |            93147 |              0.1019 |
| 1999 | UA            |  774370 |            98750 |              0.1275 |
| 2000 | AA            |  742265 |           103812 |              0.1399 |
| 2000 | DL            |  908029 |           106408 |              0.1172 |
| 2000 | UA            |  776559 |           158790 |              0.2045 |
| 2001 | AA            |  716985 |            80906 |              0.1128 |
| 2001 | DL            |  835236 |            78697 |              0.0942 |
| 2001 | UA            |  704977 |            91435 |              0.1297 |
| 2002 | AA            |  852439 |            71723 |              0.0841 |
| 2002 | DL            |  728758 |            65772 |              0.0903 |
| 2002 | UA            |  587887 |            49202 |              0.0837 |
| 2003 | AA            |  752241 |            71713 |              0.0953 |
| 2003 | DL            |  660617 |            53110 |              0.0804 |
| 2003 | UA            |  543957 |            48557 |              0.0893 |
| 2004 | AA            |  698548 |            94164 |              0.1348 |
| 2004 | DL            |  687638 |            80397 |              0.1169 |
| 2004 | UA            |  555812 |            63657 |              0.1145 |
| 2005 | AA            |  673569 |            88955 |              0.1321 |
| 2005 | DL            |  658302 |            78669 |              0.1195 |
| 2005 | UA            |  485918 |            62448 |              0.1285 |
| 2006 | AA            |  643597 |            91935 |              0.1428 |
| 2006 | DL            |  506086 |            62476 |              0.1234 |
| 2006 | UA            |  500008 |            76146 |              0.1523 |
| 2007 | AA            |  633857 |           117190 |              0.1849 |
| 2007 | DL            |  475889 |            56768 |              0.1193 |
| 2007 | UA            |  490002 |            85587 |              0.1747 |
| 2008 | AA            |  604885 |           103339 |              0.1708 |
| 2008 | DL            |  451931 |            54234 |              0.1200 |
| 2008 | UA            |  449515 |            75641 |              0.1683 |
| 2009 | AA            |  551597 |            72859 |              0.1321 |
| 2009 | DL            |  428007 |            47621 |              0.1113 |
| 2009 | UA            |  377049 |            41298 |              0.1095 |
| 2010 | AA            |  540963 |            60678 |              0.1122 |
| 2010 | DL            |  732973 |            84765 |              0.1156 |
| 2010 | UA            |  343081 |            29130 |              0.0849 |
| 2011 | AA            |  538179 |            64273 |              0.1194 |
| 2011 | DL            |  732331 |            66637 |              0.0910 |
| 2011 | UA            |  311212 |            35384 |              0.1137 |
| 2012 | AA            |  525220 |            65438 |              0.1246 |
| 2012 | DL            |  726879 |            51601 |              0.0710 |
| 2012 | UA            |  531245 |            67504 |              0.1271 |
| 2013 | AA            |  537891 |            65891 |              0.1225 |
| 2013 | DL            |  754670 |            65048 |              0.0862 |
| 2013 | UA            |  505798 |            61274 |              0.1211 |
| 2014 | AA            |  537697 |            73391 |              0.1365 |
| 2014 | DL            |  800375 |            69403 |              0.0867 |
| 2014 | UA            |  493528 |            68606 |              0.1390 |
| 2015 | AA            |  725984 |            78905 |              0.1087 |
| 2015 | DL            |  875881 |            69486 |              0.0793 |
| 2015 | UA            |  515723 |            67958 |              0.1318 |
| 2016 | AA            |  914495 |           107857 |              0.1179 |
| 2016 | DL            |  922746 |            73814 |              0.0800 |
| 2016 | UA            |  545067 |            62831 |              0.1153 |
| 2017 | AA            |  896348 |            98221 |              0.1096 |
| 2017 | DL            |  923560 |            78034 |              0.0845 |
| 2017 | UA            |  584481 |            65504 |              0.1121 |
| 2018 | AA            |  766133 |            97683 |              0.1275 |
| 2018 | DL            |  798041 |            67532 |              0.0846 |
| 2018 | UA            |  518243 |            65981 |              0.1273 |
+------+---------------+---------+------------------+---------------------+
96 rows in set (1 min 22.44 sec)
```

**Note:** SQL:2003 introduced the [FILTER clause](https://modern-sql.com/feature/filter) which would make this query easier to read.  It is not yet supported in MySQL or TiDB.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('Introduction to Analytics Queries for the MySQL DBA', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Introduction to Analytics Queries for the MySQL DBA', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## Improving query readability

If we combine our knowledge of window functions from the first example, we can write a query to express the percentage of flights delayed by greater than 30 minutes and compare that to the previous year. At this point, our queries are also getting sufficiently complicated. We can make two improvements:

- Break down the complexity by moving part of the query into a VIEW.
- Name the WINDOW as w, and make shared use of it in all the relevant places.

```sql
CREATE OR REPLACE VIEW stats AS
SELECT
  year,
  UniqueCarrier,
  COUNT(*) AS Flights,
  COUNT(CASE WHEN ArrDelay>=30 THEN 1 END) as AtLeast30Delayed
FROM ontime
WHERE UniqueCarrier IN ('AA', 'UA', 'DL')
GROUP BY UniqueCarrier, year;

SET tidb_enable_window_function = 1;
SELECT
  year,
  UniqueCarrier,
  flights,
  AtLeast30Delayed,
  AtLeast30Delayed/Flights as PctDelayed,
  LAG(AtLeast30Delayed) OVER w/LAG(Flights) OVER w
    AS LastYearPctDelayed
FROM stats
WINDOW w AS (PARTITION BY UniqueCarrier ORDER BY year)
ORDER BY year, UniqueCarrier;
+------+---------------+---------+------------------+------------+--------------------+
| year | UniqueCarrier | flights | AtLeast30Delayed | PctDelayed | LastYearPctDelayed |
+------+---------------+---------+------------------+------------+--------------------+
| 1987 | AA            |  165121 |            12346 |     0.0748 |               NULL |
| 1987 | DL            |  185813 |            18888 |     0.1017 |               NULL |
| 1987 | UA            |  152624 |            17274 |     0.1132 |               NULL |
| 1988 | AA            |  694757 |            47368 |     0.0682 |             0.0748 |
| 1988 | DL            |  753983 |            47947 |     0.0636 |             0.1017 |
| 1988 | UA            |  587144 |            59490 |     0.1013 |             0.1132 |
| 1989 | AA            |  723252 |            66833 |     0.0924 |             0.0682 |
| 1989 | DL            |  783320 |            62688 |     0.0800 |             0.0636 |
| 1989 | UA            |  574674 |            81840 |     0.1424 |             0.1013 |
| 1990 | AA            |  712060 |            67445 |     0.0947 |             0.0924 |
| 1990 | DL            |  824062 |            77552 |     0.0941 |             0.0800 |
| 1990 | UA            |  606713 |            63128 |     0.1040 |             0.1424 |
| 1991 | AA            |  725191 |            51298 |     0.0707 |             0.0947 |
| 1991 | DL            |  874791 |            64441 |     0.0737 |             0.0941 |
| 1991 | UA            |  630093 |            62718 |     0.0995 |             0.1040 |
| 1992 | AA            |  782371 |            57435 |     0.0734 |             0.0707 |
| 1992 | DL            |  916593 |            68987 |     0.0753 |             0.0737 |
| 1992 | UA            |  639349 |            50734 |     0.0794 |             0.0995 |
| 1993 | AA            |  786696 |            67134 |     0.0853 |             0.0734 |
| 1993 | DL            |  898896 |            75070 |     0.0835 |             0.0753 |
| 1993 | UA            |  649086 |            65217 |     0.1005 |             0.0794 |
| 1994 | AA            |  722277 |            63183 |     0.0875 |             0.0853 |
| 1994 | DL            |  874526 |            61312 |     0.0701 |             0.0835 |
| 1994 | UA            |  638750 |            52269 |     0.0818 |             0.1005 |
| 1995 | AA            |  688471 |            75638 |     0.1099 |             0.0875 |
| 1995 | DL            |  884019 |            88067 |     0.0996 |             0.0701 |
| 1995 | UA            |  724807 |            78906 |     0.1089 |             0.0818 |
| 1996 | AA            |  655539 |            91140 |     0.1390 |             0.1099 |
| 1996 | DL            |  888306 |           114817 |     0.1293 |             0.0996 |
| 1996 | UA            |  735266 |            98186 |     0.1335 |             0.1089 |
| 1997 | AA            |  663954 |            64981 |     0.0979 |             0.1390 |
| 1997 | DL            |  921850 |           102956 |     0.1117 |             0.1293 |
| 1997 | UA            |  743847 |            84287 |     0.1133 |             0.1335 |
| 1998 | AA            |  653919 |            63789 |     0.0975 |             0.0979 |
| 1998 | DL            |  915095 |            82049 |     0.0897 |             0.1117 |
| 1998 | UA            |  748459 |           102644 |     0.1371 |             0.1133 |
| 1999 | AA            |  692653 |            88601 |     0.1279 |             0.0975 |
| 1999 | DL            |  914130 |            93147 |     0.1019 |             0.0897 |
| 1999 | UA            |  774370 |            98750 |     0.1275 |             0.1371 |
| 2000 | AA            |  742265 |           103812 |     0.1399 |             0.1279 |
| 2000 | DL            |  908029 |           106408 |     0.1172 |             0.1019 |
| 2000 | UA            |  776559 |           158790 |     0.2045 |             0.1275 |
| 2001 | AA            |  716985 |            80906 |     0.1128 |             0.1399 |
| 2001 | DL            |  835236 |            78697 |     0.0942 |             0.1172 |
| 2001 | UA            |  704977 |            91435 |     0.1297 |             0.2045 |
| 2002 | AA            |  852439 |            71723 |     0.0841 |             0.1128 |
| 2002 | DL            |  728758 |            65772 |     0.0903 |             0.0942 |
| 2002 | UA            |  587887 |            49202 |     0.0837 |             0.1297 |
| 2003 | AA            |  752241 |            71713 |     0.0953 |             0.0841 |
| 2003 | DL            |  660617 |            53110 |     0.0804 |             0.0903 |
| 2003 | UA            |  543957 |            48557 |     0.0893 |             0.0837 |
| 2004 | AA            |  698548 |            94164 |     0.1348 |             0.0953 |
| 2004 | DL            |  687638 |            80397 |     0.1169 |             0.0804 |
| 2004 | UA            |  555812 |            63657 |     0.1145 |             0.0893 |
| 2005 | AA            |  673569 |            88955 |     0.1321 |             0.1348 |
| 2005 | DL            |  658302 |            78669 |     0.1195 |             0.1169 |
| 2005 | UA            |  485918 |            62448 |     0.1285 |             0.1145 |
| 2006 | AA            |  643597 |            91935 |     0.1428 |             0.1321 |
| 2006 | DL            |  506086 |            62476 |     0.1234 |             0.1195 |
| 2006 | UA            |  500008 |            76146 |     0.1523 |             0.1285 |
| 2007 | AA            |  633857 |           117190 |     0.1849 |             0.1428 |
| 2007 | DL            |  475889 |            56768 |     0.1193 |             0.1234 |
| 2007 | UA            |  490002 |            85587 |     0.1747 |             0.1523 |
| 2008 | AA            |  604885 |           103339 |     0.1708 |             0.1849 |
| 2008 | DL            |  451931 |            54234 |     0.1200 |             0.1193 |
| 2008 | UA            |  449515 |            75641 |     0.1683 |             0.1747 |
| 2009 | AA            |  551597 |            72859 |     0.1321 |             0.1708 |
| 2009 | DL            |  428007 |            47621 |     0.1113 |             0.1200 |
| 2009 | UA            |  377049 |            41298 |     0.1095 |             0.1683 |
| 2010 | AA            |  540963 |            60678 |     0.1122 |             0.1321 |
| 2010 | DL            |  732973 |            84765 |     0.1156 |             0.1113 |
| 2010 | UA            |  343081 |            29130 |     0.0849 |             0.1095 |
| 2011 | AA            |  538179 |            64273 |     0.1194 |             0.1122 |
| 2011 | DL            |  732331 |            66637 |     0.0910 |             0.1156 |
| 2011 | UA            |  311212 |            35384 |     0.1137 |             0.0849 |
| 2012 | AA            |  525220 |            65438 |     0.1246 |             0.1194 |
| 2012 | DL            |  726879 |            51601 |     0.0710 |             0.0910 |
| 2012 | UA            |  531245 |            67504 |     0.1271 |             0.1137 |
| 2013 | AA            |  537891 |            65891 |     0.1225 |             0.1246 |
| 2013 | DL            |  754670 |            65048 |     0.0862 |             0.0710 |
| 2013 | UA            |  505798 |            61274 |     0.1211 |             0.1271 |
| 2014 | AA            |  537697 |            73391 |     0.1365 |             0.1225 |
| 2014 | DL            |  800375 |            69403 |     0.0867 |             0.0862 |
| 2014 | UA            |  493528 |            68606 |     0.1390 |             0.1211 |
| 2015 | AA            |  725984 |            78905 |     0.1087 |             0.1365 |
| 2015 | DL            |  875881 |            69486 |     0.0793 |             0.0867 |
| 2015 | UA            |  515723 |            67958 |     0.1318 |             0.1390 |
| 2016 | AA            |  914495 |           107857 |     0.1179 |             0.1087 |
| 2016 | DL            |  922746 |            73814 |     0.0800 |             0.0793 |
| 2016 | UA            |  545067 |            62831 |     0.1153 |             0.1318 |
| 2017 | AA            |  896348 |            98221 |     0.1096 |             0.1179 |
| 2017 | DL            |  923560 |            78034 |     0.0845 |             0.0800 |
| 2017 | UA            |  584481 |            65504 |     0.1121 |             0.1153 |
| 2018 | AA            |  766133 |            97683 |     0.1275 |             0.1096 |
| 2018 | DL            |  798041 |            67532 |     0.0846 |             0.0845 |
| 2018 | UA            |  518243 |            65981 |     0.1273 |             0.1121 |
+------+---------------+---------+------------------+------------+--------------------+
96 rows in set (1 min 23.64 sec)
```

**Note:** Another way of solving this problem is with a CTE or WITH query instead of a VIEW. CTEs are a useful feature, and we are planning to support them in TiDB soon.

When we look at these numbers, the results are not so impressive. All airlines routinely have greater than 10 percent of flights delayed over 30 minutes!

## Conclusion

In this post, I tried to show how to write elegant queries that provide analytics processing that help deliver value to your organization beyond the standard responsibilities of a MySQL DBA. My hope is that you can use *a similar query* at work to, for example, find issues in your business that are at high risks, or customer service cases that could be analyzed to improve user experience. The possibilities are endless.

We have really just scratched the surface with basic window functions though; there is a lot more to offer! Stay tuned for future blog posts that expand on this subject.
