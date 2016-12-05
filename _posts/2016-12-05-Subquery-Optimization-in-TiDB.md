---
layout: post
title: Subquery Optimization in TiDB
excerpt: Subquery optimization, especially rewriting the correlated subquery, is a very difficult part in SQL query optimization. To be compatible with MySQL, TiDB enables users to write subqueries anywhere they want. For those subqueries that are not correlated, which are also called uncorrelated subqueries, TiDB evaluates in advance; for those correlated subqueries, TiDB removes the correlations as much as possible. For example, TiDB can rewrite a correlated subquery to `SemiJoin`. This article is focused on introducing the correlated subquery optimization methods in TiDB.
---

<script type="text/javascript" async
  src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_CHTML">
</script>



# Subquery Optimization in TiDB


## Introducing subqueries
Subquery is a query within another SQL query. A common subquery is embedded within the `FROM` clause, for example：

```
SELECT ID FROM (SELECT * FROM SRC) AS T
```
The subexpressions in the `FROM` clauses can be processed very well by the general SQL optimizers. But when it comes to subqueries in the `WHERE` clause or the `SELECT` lists, it becomes very difficult to optimize because subqueries can be anywhere in the expression, in the `CASE...WHEN...` clauses for example.

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

TiDB inherits the subquery strategy in SQL Server. It introduces the `Apply` operator to use algebraic representation for subqueries which is called normalization, and then removes the correlation based on the Cost information.

## The `Apply` operator

The reason why subqueries are difficult to optimize is that a subquery cannot be executed as a logic operator like Projection or Join, which makes it difficult to find a generic algorithm for subquery transformation. So the first thing is to introduce a logic operation that can represent the subqueries: the `Apply` operator.
The semantics of the `Apply` operator is:


\\ R\ A^{\otimes}\ E = \bigcup\limits_{r\in R} ({r}\otimes E(r))


where `E` represents a parameterized subquery. In every execution, the `Apply` operator gets a `r` record from the `R` relation and sends `r` to `E` as a parameter for the &#x2297; operation of `r` and `E(r)`. &#x2297; is different based on different query types, usually it’s `SemiJoin` `∃`. 

For the following SQL statement:

```
SELECT * FROM SRC WHERE

EXISTS(SELECT * FROM TMP WHERE TMP.id = SRC.id)
```
the `Apply` operator representation is as follows:

![]({{ site.baseurl }}/assets/img/apply1.png)

Because the operator above `Apply` is `Selection`, formally, it is:

$$
\{SRC}\ A^\exists\ \sigma_\{SRC.id=TMP.id}\{TMP}
$$

For the `EXISTS` subquery in the `SELECT` list, and the data that cannot pass through the `SRC.id=TMP.id equation`, the output should be false. So `OuterJoin` should be used:

$$
\pi_C({SRC}\ A^{LOJ} \sigma\_\{SRC.id=TMP.id}\{TMP})
$$

The C Projection is to transform NULL to false.

## Removing the correlation
The introduction of the `Apply` operator enables us to remove the correlation of the subqueries. The two examples in the previous section can be transformed to:

$$
\{SRC}\ \exists_{\sigma\_\{SRC.id = TMP.id}}\ \{TMP}
$$

and

$$
\{SRC}\ LOJ\_{\sigma\_\{SRC.id = TMP.id}}\ \{TMP}
$$

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

Based on the above rules, the correlation among all the SQL subqueries can be removed. Take the following SQL statement as an example:

```
SELECT C_CUSTKEY

FROM CUSTOMER WHERE 1000000 <

(SELECT SUM(O_TOTALPRICE)

FROM ORDER WHERE O_CUSTKEY = C_CUSTKEY)
```

The two “CUSTKEY”s are the primary keys. When the statement is transformed to `Apply`, it is represented as:

$$
\sigma\_{1000000<X}(CUSTOMER\ A^\times\ \mathcal{G}^1\_{X=SUM(0\\\_PRICE)})(\sigma\_{0\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
$$

Because of the primary keys, according to rule (9), it can be transformed to the following: 

$$
\sigma\_{1000000<X}\ \mathcal{G}\_{C\\\_CUSTKEY\ ,X = SUM(0\\\_PRICE)}(CUSTOMER\ A^{LOJ}\ \sigma\_{0\\\_CUSTKEY=c\\\_CUSTKEY}ORDERS)
$$

**Note:**

1. If there are no primary keys in `ORDERS`, the \\(\pi\\) operator should be added to allocate a unique key.
2. Pay attention to the difference between rule (8) and rule (9). For the aggregation function (\\(\mathcal{G}^1\_F\\)) without the aggregation column, when the input is NULL, the output should be the default value of the `F` aggregation function. Therefore, the left `OuterJoin` should be used and a NULL record should be the output when the right table is NULL.  In this case, based on rule (2), `Apply` can be completely removed. The statement can be transformed to a SQL statement with join:
$$
\sigma\_{1000000<X}\mathcal{G}\_{C\\\_CUSTKEY,X=SUM(0\\\_PRICE)}(CUSTOMER\ LOJ\_{0\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
$$
Furthermore, based on the simplification of `OuterJoin`, the statement can be simplified to:
$$
\sigma\_{1000000<X}\mathcal{G}\_{C\\\_CUSTKEY,X=SUM(0\\\_PRICE)}(CUSTOMER\ \Join\_{0\\\_CUSTKEY=C\\\_CUSTKEY}ORDERS)
$$

Theoretically, the above 9 rules have resolved the correlation removal problem. But is correlation removal the best solution for all the scenarios? The answer is no. If the results of the SQL statement are small and the subquery can use the index, then the best solution is to use correlated execution. The decision about whether to use correlation removal also depends on statistics. When it comes to this point,  the regular optimizer is no longer applicable.  Only the optimizer with the Volcano or Cascade Style can take both the logic equivalence rules and the cost-based optimization into consideration. Therefore, a perfect solution for subquery depends on an excellent optimizer framework.

## Aggregation and subquery
In the previous section, the final statement is not completely optimized. The aggregation function above `OuterJoin` and `InnerJoin` can be pushed down. If `OutJoin` cannot be simplified, the formal representation of the push-down rule is:

$$
\mathcal{G\_{A,F}}(S\ LOJ\_p\ R)=\pi\_C(S\ LOJ\_P(\mathcal{G}\_{A-attr(S),F}R))
$$

The \\(\pi\_C\\) above `Join` is to convert NULL to the default value when the aggregation function accepts empty values. It is very common to use aggregation functions together with subqueries. The general solution is to use the formal representation of `Apply`, and remove the correlation based on the rules, then apply the push-down rules of the aggregation function for further optimization.
		




