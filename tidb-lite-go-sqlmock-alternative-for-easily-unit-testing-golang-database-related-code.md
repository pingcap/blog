---
title: 'tidb-lite: A go-sqlmock Alternative for Easily Unit Testing Golang Database-Related Code'
author: ['Xiang Wang']
date: 2021-03-04
summary: If your Golang app uses a MySQL-compatible database, you will have a lot of database-related code to unit test. Unlike go-sqlmock, tidb-lite lets you test your code easily without the need to start a database instance in the external environment.
tags: ['MySQL', 'Go']
categories: ['Community']
image: /images/blog/golang-database-unit-test-go-sqlmock-alternative.jpg
--- 

**Author:** [Xiang Wang](https://github.com/WangXiangUSTC) (Software Engineer at PingCAP)

**Editors:** Tom Dewan, [Caitin Chen](https://github.com/CaitinChen)

![A go-sqlmock alternative for Golang database unit test](media/golang-database-unit-test-go-sqlmock-alternative.jpg)

If your Golang application uses a MySQL-compatible database, such as MySQL, [TiDB](https://docs.pingcap.com/tidb/stable), or Amazon Aurora MySQL, you will have a lot of database-related code to unit test. Typically, developers conduct unit tests using one of the following approaches:

* Start a database instance on which to perform the unit test. However, this approach is not very elegant: you need to rely on an external environment, which increases your testing cost.
* Simulate or "mock" SQL services. This provides a test environment without having to use an actual database. 

    ![Golang unit test](media/golang-unit-test.jpg)
    <div class="caption-center"><a href="https://draveness.me/golang-101/" target="_blank"> Golang unit test </a></div>

    [go-sqlmock](https://github.com/DATA-DOG/go-sqlmock) is a commonly used tool for simulating services written in Golang. However, as we shall see, go-sqlmock also has its drawbacks.

A simpler and more effective approach is to use [tidb-lite](https://github.com/WangXiangUSTC/tidb-lite). tidb-lite enables you to create a TiDB server in `mocktikv` mode to run your Golang application or unit test. 

In addition, some applications hope to persist data locally and store it in a database to facilitate data management. tidb-lite can also be used in this scenario. To process data locally, developers use SQL that is compatible with the MySQL protocol.

This article focuses on the first scenario: how to use tidb-lite to unit test database-related code. We'll look at the limitations of go-sqlmock, discuss tidb-lite's advantages, and then show an example of tidb-lite in action.

## go-sqlmock limitations

To understand the limitations of using go-sqlmock, let's unit test a piece of database-related code. For our example, we'll use the `recordStats` function. When a user accesses a product, `recordStats` increments the number of product views and adds the user to the list of those who have viewed it. Here is the function code:

```go
package main

import (

    "database/sql"

    _ "github.com/go-sql-driver/mysql"

)

func recordStats(db *sql.DB, userID, productID int64) ( err error) {

    tx, err := db.Begin()

    if err != nil {

        return

    }

    defer func() {

        switch err {

        case nil:

            err = tx.Commit()

        default:

            tx.Rollback()

        }

    }( )

    if _, err = tx.Exec("UPDATE products SET views = views + 1"); err != nil {

        return

    }

    if _, err = tx.Exec("INSERT INTO product_viewers (user_id, product_id) VALUES (? , ?)", userID, productID); err != nil {

        return

    }

    return

}

func main() {

    // @NOTE: the real connection is not required for tests

    db, err := sql.Open("mysql", "root@/blog")

    if err != nil {

        panic(err)

    }

    defer db.Close()

    if err = recordStats(db, 1 /*some user id*/, 5 /*some product id*/); err != nil {

        panic(err)

    }

}
```

Now, let's add the information needed to test this code. If you use go-sqlmock to write unit tests, you must define each step of the database operation, the order of the steps (including the `BEGIN` and `COMMIT` parts of the transaction), and the expected return data. If the actual operation or steps are inconsistent, sqlmock reports an error. The code for unit testing this function using go-sqlmock is as follows:

```go
package main

import (

    "fmt"

    "testing"

    "github.com/DATA-DOG/go-sqlmock"

)

// a successful case

func TestShouldUpdateStats( t *testing.T) {

    db, mock, err := sqlmock.New()

    if err != nil {

        t.Fatalf("an error'%s' was not expected when opening a stub database connection", err)

    }

    defer db.Close()

    mock.ExpectBegin()

    mock.ExpectExec("UPDATE products").WillReturnResult(sqlmock.NewResult(1, 1))

    mock.ExpectExec("INSERT INTO product_viewers").WithArgs(2, 3). WillReturnResult(sqlmock.NewResult(1, 1))

    mock.ExpectCommit()

    // now we execute our method

    if err = recordStats(db, 2, 3); err != nil {

        t.Errorf("error was not expected while updating stats: %s", err)

    }

    // we make sure that all expectations were met

    if err := mock.ExpectationsWereMet(); err != nil {

        t.Errorf("there were unfulfilled expectations: %s", err )

    }

}
```

If the operations of the function or the structure of the database table are complicated, preparing this information can be difficult.

In contrast, when we use tidb-lite for our unit testing, we only need to focus on whether the return result of the function is correct—not the order of execution of each operation of the function.

## tidb-lite: a simpler alternative

**One of the most important advantages of tidb-lite over go-sqlmock is simplicity.** You can run a TiDB instance directly in the code instead of starting a MySQL or TiDB instance before running the unit test. This ensures that the unit test does not depend on the external environment. And, in contrast to go-sqlmock, we don't need to write a lot of complex or redundant test code. We can focus on the correctness of the function.

TiDB is also highly compatible with the MySQL protocol. Using tidb-lite can almost completely simulate the MySQL environment.

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('tidb-lite: A go-sqlmock Alternative for Easily Unit Testing Golang Database-Related Code', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('tidb-lite: A go-sqlmock Alternative for Easily Unit Testing Golang Database-Related Code', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
  </div>

## Using tidb-lite

To see tidb-lite in action, let's unit test another function: `GetRowCount`. `GetRowCount` returns the number of eligible rows in a table. Here is the function code: 

```go
package example

import (
    "context"
    "database/sql"
    "fmt"

    "github.com/pingcap/errors"
    "github.com/pingcap/log "
    "go.uber.org/zap"
)

// GetRowCount returns row count of the table.
// if not specify where condition, return total row count of the table.
func GetRowCount(ctx context.Context, db *sql.DB , schemaName string, tableName string, where string) (int64, error) {
    /*
        select count example result:
        mysql> SELECT count(1) cnt from `test`.`itest` where id> 0;
        +----- -+
        | cnt |
        +------+
        | 100 |
        +------+
    */

    query := fmt.Sprintf("SELECT COUNT(1) cnt FROM `%s`.`%s` ", schemaName, tableName)
    if len(where)> 0 {
        query += fmt.Sprintf(" WHERE %s", where)
    }
    log.Debug("get row count", zap.String("sql", query) )

    var cnt sql.NullInt64
    err := db.QueryRowContext(ctx, query).Scan(&cnt)
    if err != nil {
        return 0, errors.Trace(err)
    }
    if !cnt.Valid {
        return 0, errors.NotFoundf ("table `%s`.`%s`", schemaName, tableName)
    }

    return cnt.Int64, nil
}
```

To write unit tests with tidb-lite, you need to use `NewTiDBServer` to create a TiDB instance and `CreateConn` to get a link to this database. Then, you can use this connection to access the database, generate test data, and verify the correctness of the function. The unit test code of this function using tidb-lite is as follows:

```go
package example

import (
    "context"
    "testing"
    "time"

    tidblite "github.com/WangXiangUSTC/tidb-lite"
    . "Github.com/pingcap /check"
)

func TestClient(t *testing.T) {
    TestingT(t)
}

var _ = Suite(&testExampleSuite{})

type testExampleSuite struct{}

func (t *testExampleSuite) TestGetRowCount(c *C) {
    tidbServer, err: = tidblite.NewTiDBServer(tidblite.NewOptions(c.MkDir()))
    c.Assert(err, IsNil)

    dbConn, err := tidbServer.CreateConn()
    c.Assert(err, IsNil)

    ctx, cancel := context.WithTimeout (context.Background(), 10*time.Second)
    defer cancel()

    _, err = dbConn.ExecContext(ctx, "create database example_test")
    c.Assert(err, IsNil)
    _, err = dbConn.ExecContext(ctx , "create table example_test.t(id int primary key, name varchar(24))")
    c.Assert(err, IsNil)
    _, err = dbConn.ExecContext(ctx, "insert into example_test.t values(1, ' a'),(2,'b'),(3,'c')")
    c.Assert(err, IsNil)

    count, err := GetRowCount(ctx, dbConn, "example_test", "t", "id > 2")
    c.Assert(err, IsNil)
    c.Assert(count , Equals, int64(1))

    count, err = GetRowCount(ctx, dbConn, "example_test", "t", "")
    c.Assert(err, IsNil)
    c.Assert(count, Equals, int64(3))
    tidbServer.Close()

    tidbServer2, err := tidblite.NewTiDBServer(tidblite.NewOptions(c.MkDir()))
    c.Assert(err, IsNil)
    defer tidbServer2.Close()

    dbConn2, err := tidbServer2.CreateConn()
    c .Assert(err, IsNil)
    _, err = dbConn2.ExecContext(ctx, "create database example_test")
    c.Assert(err, IsNil)
}
```

As you can see, using tidb-lite is the same as using a real database. For detailed information on how to use tidb-lite, see the [README](https://github.com/WangXiangUSTC/tidb-lite/blob/master/README.md).
