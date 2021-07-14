---
title: Subquery Optimization in TiDB
author: ['Fei HAN']
date: 2016-12-07
summary: Subquery optimization, especially rewriting the correlated subquery, is a very difficult part in SQL query optimization. To be compatible with MySQL, TiDB enables users to write subqueries anywhere they want. For those subqueries that are not correlated, which are also called uncorrelated subqueries, TiDB evaluates in advance; for those correlated subqueries, TiDB removes the correlations as much as possible. For example, TiDB can rewrite a correlated subquery to `SemiJoin`. This article is focused on introducing the correlated subquery optimization methods in TiDB.
tags: ['Query execution']
aliases: ['/blog/2016/12/07/Subquery-Optimization-in-TiDB/', '/blog/2016/12/07/subquery-optimization-in-tidb/']
categories: ['Engineering']
---

<script type="text/x-mathjax-config" dangerouslySetInnerHTML={{ __html: `
  MathJax.Hub.Config({
    extensions: ["tex2jax.js"],
    jax: ["input/TeX", "output/HTML-CSS"],
    tex2jax: {
      inlineMath: [ ['$','$'], ["\\(","\\)"] ],
      displayMath: [ ['$$','$$'], ["\\[","\\]"] ],
      processEscapes: true
    },
    "HTML-CSS": { availableFonts: ["TeX"] }
  });
`}}>
</script>
<script type="text/javascript" src="path-to-MathJax/MathJax.js">
</script>
<script type="text/javascript" async
  src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_CHTML">
</script>

## Introduction to subqueries

Subquery is a query within another SQL query. A common subquery is embedded within the `FROM` clause, for example：

```
SELECT ID FROM (SELECT * FROM SRC) AS T
```

The subexpressions in the `FROM` clauses can be processed very well by the general SQL optimizers. But when it comes to subqueries in the `WHERE` clause or the `SELECT` lists, it becomes very difficult to optimize because subqueries can be anywhere in the expression, e.g. in the `CASE...WHEN...` clauses.

The subqueries that are not in the `FROM` clause are categorized as "correlated subquery" and "uncorrelated subquery". Correlated subquery refers to a subquery with columns from outer references, for example:

```
SELECT * FROM SRC WHERE

EXISTS(SELECT * FROM TMP WHERE TMP.id = SRC.id)
```

Uncorrelated subqueries can be pre-processed in the plan phase and be re-written to a constant. Therefore, this article is mainly focused on the optimization of correlated subqueries.

Generally speaking, there are following three types of subqueries:

+ Scalar Subquery like (`SELECT...`) + (`SELECT...`)
+ Quantified Comparison like `T.a = ANY(SELECT...)`
+ Existential Test like `NOT EXISTS(SELECT...)`, `T.a IN (SELECT...)`

For the simple subqueries like Existential Test, the common practice is to rewrite them to `SemiJoin`. But it is barely explored in the literature about the generic algorithm and what kind of subqueries need to remove the correlation. For those subqueries whose correlation cannot be removed, the common practice in databases is to execute in Nested Loop, which is called correlated execution.

TiDB inherits the subquery strategy in SQL Server [^1]. It introduces the `Apply` operator to use algebraic representation for subqueries which is called normalization, and then removes the correlation based on the cost information.

## The `Apply` operator

The reason why subqueries are difficult to optimize is that a subquery cannot be represented as a logic operator like `Projection` or `Join`, which makes it difficult to find a generic algorithm for subquery transformation. So the first thing is to introduce a logical operation that can represent the subqueries: the `Apply` operator, which is also called `d-Join`[^2].
The semantics of the `Apply` operator is:

\\[
R\ A^{\otimes}\ E = \bigcup\limits_{r\in R} (\\\{r\\\}\otimes E(r))
\\]

where `E` represents a parameterized subquery. In every execution, the `Apply` operator gets an `r` record from the `R` relation and sends `r` to `E` as a parameter for the &#x2297; operation of `r` and `E(r)`. &#x2297; is different based on different query types, usually it's `SemiJoin` `∃`.

For the following SQL statement:

```
SELECT * FROM SRC WHERE

EXISTS(SELECT * FROM TMP WHERE TMP.id = SRC.id)
```

the `Apply` operator representation is as follows:

![The `Apply` operator](media/apply1.png)

Because the operator above `Apply` is `Selection`, formally, it is:

\\[
\{SRC}\ A^\exists\ \sigma\_{SRC.id=TMP.id}\{TMP}
\\]

For the `EXISTS` subquery in the `SELECT` list, and the data that cannot pass through the `SRC.id=TMP.id` equation, the output should be false. So `OuterJoin` should be used:

\\[
\pi\_C({SRC}\ A^{LOJ}\ \sigma\_{SRC.id=TMP.id}\{TMP})
\\]

The `C` Projection is to transform NULL to false. But the more common practice is: If the output of the `Apply` operator is directly used by the query predicate, it is converted to `SemiJoin`.

<div class="trackable-btns">
    <a href="/download" onclick="trackViews('Subquery Optimization in TiDB', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
    <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Subquery Optimization in TiDB', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## Removing the correlation

The introduction of the `Apply` operator enables us to remove the correlation of the subqueries. The two examples in the previous section can be transformed to:

\\[
\{SRC}\ \exists\_{\sigma\_{SRC.id = TMP.id}}\ \{TMP}
\\]

and

\\[
\{SRC}\ LOJ\_{\sigma\_\{SRC.id = TMP.id}}\ \{TMP}
\\]

Other rules to remove correlation can be formally represented as:

\\(R\ A^{\otimes} E= R\ {\otimes}\_{true}\ E\\), if no parameters in `E` resolved from `R` (1)

\\(R\ A^{\otimes} (\sigma\_pE) = R\ {\otimes}\_p\ E\\), if no parameters in `E` resolved from `R` (2)

\\(R\ A^\times\ (\sigma\_pE)=\sigma\_p(R\ A^\times\ E) \\) (3)

\\(R\ A^\times\\ (\pi\_vE) = \pi\_{v\bigcup\mathrm{cols}(R)}(R\ A^\times\ E) \\) (4)

\\(R\ A^\times\ (E\_1\ \bigcup\ E\_2) = (R\ A^\times\ E\_1)\ \bigcup\ (R\ A^\times\ E\_2) \\) (5)

\\(R\ A^\times\ (E\_1\ - \ E\_2) = (R\ A^\times\ E\_1)\ - \ (R\ A^\times\ E\_2) \\) (6)

\\(R\ A^\times\ (E\_1\ \times \ E\_2) = (R\ A^\times\ E\_1)\ \Join_{R.key}\ (R\ A^\times\ E\_2) \\) (7)

\\(R\ A^\times\ (\mathcal{G}\_{A,F}E) = \mathcal{G}\_{A\bigcup \mathrm{attr}(R),F} (R\ A^{\times}\ E) \\) (8)

\\(R\ A^\times\ (\mathcal{G}^1\_FE) = \mathcal{G}\_{A\bigcup \mathrm{attr}(R),F'} (R\ A^{LOJ}\ E) \\) (9)

Based on the above rules, the correlation among all the SQL subqueries can be removed [^3]. But the (5), (6), and (7) rules are seldom used because the  the query cost is increased as a result of the rules about common expression.
Take the following SQL statement as an example:

```
SELECT C_CUSTKEY

FROM CUSTOMER WHERE 1000000 <

(SELECT SUM(O_TOTALPRICE)

FROM ORDER WHERE O_CUSTKEY = C_CUSTKEY)
```

The two "CUSTKEY"s are the primary keys. When the statement is transformed to `Apply`, it is represented as:

\\[
\sigma\_{1000000<X}(CUSTOMER\ A^\times\ \mathcal{G}^1\_{X=SUM(O\\\_PRICE)}(\sigma\_{O\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS))
\\]

Because of the primary keys, according to rule (9), it can be transformed to the following:

\\[
\sigma\_{1000000<X}\ \mathcal{G}_{C\\\_CUSTKEY,X = SUM(O\\\_PRICE)}(CUSTOMER\ A^{LOJ}\ \sigma\_{O\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
\\]

**Note:**

1. If there are no primary keys in `ORDERS`, the \\(\pi\\) operator should be added to allocate a unique key.
2. Pay attention to the difference between rule (8) and rule (9). For the \\(\mathcal{G}^1\_F\\) aggregation function without the aggregation column, when the input is NULL, the output should be the default value of the `F` aggregation function. Therefore, the `LeftOuterJoin` should be used and a NULL record should be the output when the right table is NULL.  In this case, based on rule (2), `Apply` can be completely removed. The statement can be transformed to a SQL statement with join:

\\[
\sigma\_{1000000<X}\mathcal{G}\_{C\\\_CUSTKEY,X=SUM(O\\\_PRICE)}(CUSTOMER\ LOJ_{O\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
\\]

Furthermore, based on the simplification of `OuterJoin`, the statement can be simplified to:

\\[
\sigma\_{1000000<X}\mathcal{G}\_{C\\\_CUSTKEY,X=SUM(O\\\_PRICE)}(CUSTOMER\ \Join_{O\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
\\]

Theoretically, the above 9 rules have solved the correlation removal problem. But is correlation removal the best solution for all the scenarios? The answer is no. If the results of the SQL statement are small and the subquery can use the index, then the best solution is to use correlated execution. The `Apply` operator can be optimized to `Segment Apply`, which is to sort the data of the outer table according to the correlated key. In this case, the keys that are within one group won't have to be executed multiple times. Of course, this is strongly related to the number of distinct values (NDV) of the correlated keys in the outer table. Therefore, the decision about whether to use correlation removal also depends on statistics. When it comes to this point,  the regular optimizer is no longer applicable.  Only the optimizer with the Volcano or Cascade Style can take both the logic equivalence rules and the cost-based optimization into consideration. Therefore, a perfect solution for subquery depends on an excellent optimizer framework.

## Aggregation and subquery

In the previous section, the final statement is not completely optimized. The aggregation function above `OuterJoin` and `InnerJoin` can be pushed down[^4]. If `OutJoin` cannot be simplified, the formal representation of the push-down rule is:

\\[
\mathcal{G\_{A,F}}(S\ LOJ\_p\ R)=\pi\_C(S\ LOJ\_p(\mathcal{G}\_{A-attr(S),F}R))
\\]

The \\(\pi\_C\\) above `Join` is to convert NULL to the default value when the aggregation function accepts empty values. It is worth mentioning that the above formula can be applied only when the following three conditions are met:

+ All the columns that are related to `R` within the `p` predicate are in the `Group by` column.
+ The key of the `S` relation is in the `Group by` column.
+ The aggregations in the \\(\mathcal{G}\\) function only uses the columns in `R`.

It is very common to use aggregation functions together with subqueries. The general solution is to use the formal representation of `Apply`, and remove the correlation based on the rules, then apply the push-down rules of the aggregation function for further optimization.

## References

[^1]: C. Galindo-Legaria and M. Joshi. "Orthogonal optimization of subqueries and aggregation". In: _Proc. of the ACM SIGMOD Conf. on Management of Data (2001)_, pp. 571–581.

[^2]: D. Maier, Q. Wang and L. Shapiro. _Algebraic unnesting of nested object queries_. Tech. rep. CSE-99-013. Oregon Graduate Institute, 1999.

[^3]: C. A. Galindo-Legaria. _Parameterized queries and nesting equivalences_. Tech. rep. MSR-TR-2000-31. Microsoft, 2001.

[^4]: W. Yan and P.-A. Larson. "Eager aggregation and lazy aggregation". In: _Proc. Int. Conf. on Very Large Data Bases (VLDB)_ (1995), pp. 345–357.
