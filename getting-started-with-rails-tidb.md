---
title: Getting Started with Rails & TiDB
author: ['Hooopo']
date: 2021-04-28
summary: Integrating a complex ORM like ActiveRecord with TiDB can be difficult. This tutorial helps you get started with TiDB and Rails.
tags: ['Tutorial']
categories: ['Community']
image: /images/blog/getting-started-with-rails-tidb.jpg
---

**Author:** [Hooopo](https://github.com/hooopo) (Active contributor of Ruby China)

**Editor:** [Ran Huang](https://github.com/ran-huang)

![Getting Started with Rails & TiDB](media/getting-started-with-rails-tidb.jpg)

*An original version of this article was published on [dev.to](https://dev.to/hooopo/getting-started-with-rails-tidb-4pni).*

This tutorial, perhaps, is the first Rails + TiDB integration tutorial across the web. [TiDB](https://pingcap.com/products/tidb) is an open-source, distributed SQL database that features horizontal scalability, high availability, and MySQL compatibility.

For beginners, integrating a complex ORM like ActiveRecord with TiDB could be difficult. Since there are few articles on the web touching this topic, I wrote this tutorial to help Rails users to get started with TiDB.

## Build a local TiDB development environment

Before integrating with Rails, you need to deploy a TiDB cluster on your local machine. TiDB provides a smooth deployment experience using [TiUP](https://docs.pingcap.com/tidb/dev/tiup-overview), a package manager for the TiDB ecosystem.

### Install TiUP

[Installing TiUP](https://docs.pingcap.com/tidb/dev/tiup-overview#install-tiup) is pretty straightforward for either Darwin or Linux operating systems. All you need to do is a single line of command:

{{< copyable "shell-regular" >}}

```shell
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
```

This will also add `$HOME/.tiup/bin` in your `PATH` environment variable, so you can use TiUP directly.

### Spin up a local cluster

As a typical TiDB cluster requires multiple nodes, deploying it might be time-consuming and complicated. Therefore, TiUP offers [`playground`](https://docs.pingcap.com/tidb/dev/tiup-playground), a TiUP component that enables you to quickly build a local TiDB test environment.

The command is as simple as follows:

{{< copyable "shell-regular" >}}

```shell
tiup playground
```

You'll see the output like this:

```
tiup playground
Starting component ``playground``: /Users/hooopo/.tiup/components/playground/v1.4.1/tiup-playground
Use the latest stable version: v5.0.0

    Specify version manually: tiup playground <version>
    The stable version: tiup playground v4.0.0
    The nightly version: tiup playground nightly

Playground Bootstrapping...
Start pd instance
Start tikv instance
Start tidb instance
Waiting for tidb instances ready
127.0.0.1:4000 ... Done
Start tiflash instance
Waiting for tiflash instances ready
127.0.0.1:3930 ... Done
CLUSTER START SUCCESSFULLY, Enjoy it ^-^
To connect TiDB: mysql --host 127.0.0.1 --port 4000 -u root -p (no password)
To view the dashboard: http://127.0.0.1:2379/dashboard
To view the Prometheus: http://127.0.0.1:9090
To view the Grafana: http://127.0.0.1:3000
```

Congrats! Your local cluster is now up and running.

### Access TiDB Dashboard

TiDB provides [TiDB Dashboard](https://docs.pingcap.com/tidb/dev/dashboard-intro), a Web UI for monitoring your cluster. It is already built into the PD component, so you can directly access it via <http://127.0.0.1:2379/dashboard>.

![TiDB Dashboard overview](media/rails-and-tidb-access-tidb-dashboard.jpg)

For more information on TiUP, see the [official documentation](https://docs.pingcap.com/tidb/stable/tiup-overview).

## Configure Rails for TiDB

Now that you have a running TiDB cluster, the next step is to integrate it with Rails.

### Create a Rails project

Because TiDB is compatible with MySQL, you can create a Rails app configured for MySQL:

```shell
rails new myapp --database=mysql
```

### Configure `database.yml`

There are two configurations you need to pay attention to in `database.yml`:

- Set `port` to `4000`. The local TiDB cluster uses `4000` as the default port.
- Set the database connection variable `tidb_enable_noop_functions` to `ON`. Rails needs to use the `get_lock` function, which is disabled in TiDB by default.

```yaml
default: &default
  adapter: mysql2
  encoding: utf8mb4
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  port: 4000
  username: root
  password:
  host: 127.0.0.1
  variables:
    tidb_enable_noop_functions: ON
```

If you configure the database connection using the URI method, the configuration is similar:

```yaml
default: &default
  adapter: mysql2
  encoding: utf8mb4
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  url: <%= ENV.fetch("DB_URL") || "mysql2://root:pass@localhost:4000/myapp" %>
  variables:
    tidb_enable_noop_functions: ON
```

### Configure primary key, auto-increment, unique-index

Create a table named `users`:

```ruby
class CreateUsers < ActiveRecord::Migration[6.1]
  def change
    create_table :users do |t|
      t.string :email
      t.string :password
      t.string :username

      t.timestamps
    end
  end
end
```

Add a unique index:

```ruby
class AddUniqueIndexForEmail < ActiveRecord::Migration[6.1]
  def change
    add_index :users, :email, unique: true
  end
end
```

Because TiDB is compatible with MySQL, the usage is almost identical to that of a standalone MySQL database. Compared with other distributed databases that are incompatible in terms of features like primary keys, auto-increment, and unique indexes, TiDB is much more easy to get started with because no extra handling is required.

Now you can take a look at the generated data table:

```sql
mysql> show create table users;
+ -------+------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- -------------------------------------------------------------+
| Table | Create Table |
+-------+------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- -------------------------------------------------------------+
| users | CREATE TABLE `users` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `index_users_on_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001 |
+-------+------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------- -------------------------------------------------------------+
1 row in set (0.01 sec)
```

### Add a patch for savepoints

The only obstacle to combining TiDB and ActiveRecord is that [TiDB doesn't support savepoints](https://github.com/pingcap/tidb/issues/6840) for now, so I wrote a simple patch to solve it:

```ruby
# https://github.com/rails/rails/blob/6-1-stable/activerecord/lib/active_record/connection_adapters/abstract/database_statements.rb#L313
require 'active_record/connection_adapters/abstract/database_statements.rb'

module DisableSavepoint
  def transaction(requires_new: nil, isolation: nil, joinable: true)
    if requires_new
      requires_new = nil
      Rails.logger.warn "savepoint statement was used, but your db not support, ignored savepoint."
      Rails.logger.warn caller
      super(requires_new: requires_new, isolation: isolation, joinable: joinable)
    else
      super(requires_new: requires_new, isolation: isolation, joinable: joinable)
    end
  end
end

ActiveRecord::ConnectionAdapters::DatabaseStatements.send(:prepend, DisableSavepoint)
```

In Rails, savepoints are introduced only when the transaction passes `true` to the parameter `requires_new`. When that happens, this patch will change the value of `requires_new` to `nil` and output logs for migration.

From my experience, most Rails projects don't use savepoints very often, so migration wouldn't be much of a problem if needed. A savepoint is introduced when you perform migration, but if there's no concurrent migration, removing it won't bring unexpected consequences.

## References

* [What's New in TiDB 5.0](https://docs.pingcap.com/tidb/stable/release-5.0.0)
* [`tidb_enable_noop_functions`](https://docs.pingcap.com/tidb/stable/system-variables#tidb_enable_noop_functions-new-in-v40)
* [TiDB's Compatibility with MySQL](https://docs.pingcap.com/tidb/stable/mysql-compatibility)
* [Source code for rails-tidb Demo](https://github.com/hooopo/rails-tidb)
