---
title: Power Up Your Rails Apps with a NewSQL Database
author: ['Matt Wang']
date: 2020-09-30
summary: This post helps Ruby on Rails developers get started with TiDB and use it as the backend storage layer of Rails applications.
tags: ['Tutorial']
categories: ['Community']
image: /images/blog/build-rails-apps-with-a-newsql-database.png
---

**Author:** [Matt Wang](https://github.com/hooopo) (Engineer at PingCAP, moderator of Ruby-China community)

**Editor:** [Fendy Feng](https://github.com/septemberfd), Tom Dewan

![Build a Rails App with a NewSQL Database](media/build-rails-apps-with-a-newsql-database.png)

If you are a Ruby on Rails developer, I think you'll really enjoy this article. It aims to help you get started with [TiDB](https://github.com/pingcap/tidb), an open-source NewSQL database, and use it to power up your Rails applications.

## Use TiDB to build up your Ruby on Rails applications

[TiDB](https://github.com/pingcap/tidb) is an open-source NewSQL database that supports Hybrid Transactional and Analytical Processing (HTAP) workloads. It is MySQL compatible and features horizontal scalability, strong consistency, and high availability.

To build apps with Rails, TiDB offers you MySQL interfaces which can be used as the backend database layers. TiDB allows you to use Active Record Object Relational Mapping (ORM) directly, and also provides you with an alternative: the [activerecord-tidb-adapter](https://github.com/pingcap/activerecord-tidb-adapter), a lightweight extension of Active Record that offers compatible patches and TiDB-exclusive functions such as [Sequence](https://docs.pingcap.com/tidb/stable/sql-statement-create-sequence).

## Getting started with TiDB

The instructions below teach you how to build a Rails application with TiDB as the backend storage.

If you already know how to build a Rails app from scratch, you can skip steps 2-4 and start playing with our [demo application](https://github.com/hooopo/rails-tidb).

### Step 1: Set up your local TiDB server

Deploy a TiDB cluster on your local machine.

1. Install TiUP.

TiDB provides a smooth deployment experience using [TiUP](https://docs.pingcap.com/tidb/stable/tiup-overview), a package manager for you to manage different cluster components easily in the TiDB ecosystem.

```shell
$ curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
```

2. Start TiDB playground.

Start a TiDB nightly instance by running the `tiup playground` command:

```shell
$ tiup playground  nightly
```

3. Connect to the TiDB instance in a similar way as you connect to MySQL.

```
mysql --host 127.0.0.1 --port 4000 -u root -p
```

### Step 2: Initialize the Rails application

1. Make sure that you have Ruby and Rails installed, and  initiate a Rails app named `tidb-rails`; also be sure to set the database as `mysql` because TiDB speaks the MySQL protocol.

```
$ ruby -v
ruby 2.7.0

$ rails -v
Rails 6.1.4

$ rails new tidb-rails --database=mysql --api
```

2. Add [activerecord-tidb-adapter](https://github.com/pingcap/activerecord-tidb-adapter) to Gemfile. Activerecord-tidb-adapter allows you to use TiDB as a backend for ActiveRecord and Rails apps.

```
$ bundle add activerecord-tidb-adapter --version "~> 6.1.0"
```

3. After you create a new app, edit `config/database.yml` to configure the connection setting to TiDB.

```yaml
default: &default
 adapter: tidb
 encoding: utf8mb4
 collation: utf8mb4_general_ci
 pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
 host: 127.0.0.1
 port: 4000
 variables:
   tidb_enable_noop_functions: ON
 username: root
 password:
development:
 <<: *default
 database: tidb_rails_development
```

Now, TiDB is already set up and ready to use with your Rails app. You don't have to configure anything else.

### Step 3: Create a database

Create the local database for your rails application.

```
$ bundle exec rails db:create
Created database 'tidb_rails_development'
Created database 'tidb_rails_test'
```

### Step 4: Manipulate TiDB data through your Rails app

Before you play with your app with TiDB, you need to define the model and migrate the database.

1. Define the model by executing `rails g` command.

```
$ bundle exec rails g model user email:string name:string gender:integer
...
$ vim ./db/migrate/20210826174523_create_users.rb # edit
```

2. Edit the `db/migrate/20210826174523_create_users.rb` file:

```
class CreateUsers &lt; ActiveRecord::Migration[6.1]
 def change
   create_table :users do |t|
     t.string :email, index: {unique: true}
     t.string :name
     t.integer :gender
     t.timestamps
   end
 end
end
```

3. Migrate your database.

```
$ bundle exec rails db:migrate
== 20210826174523 CreateUsers: migrating ======================================
-- create_table(:users)
  -> 0.1717s
== 20210826174523 CreateUsers: migrated (0.1717s) =============================
```

4. Launch the Rails console to play with the app.

```
$ bundle exec rails c
Running via Spring preloader in process 13378
Loading development environment (Rails 6.1.4.1)
irb(main):001:0> 30.times.each { |i| User.create!(email: "user-#{i}@example.com", name: "user-#{i}", gender: i % 3) }
  (1.2ms)  select version()
 TRANSACTION (0.8ms)  BEGIN
 User Create (93.5ms)  INSERT INTO `users` (`email`, `name`, `gender`, `created_at`, `updated_at`) VALUES ('user-0@example.com', 'user-0', 0, '2021-08-26 17:50:40.661945', '2021-08-26 17:50:40.661945')
 TRANSACTION (14.9ms)  COMMIT
...

=> 30
irb(main):002:0> User.count
  (8.9ms)  SELECT COUNT(*) FROM `users`
=> 30
irb(main):003:0> User.first
 User Load (5.8ms)  SELECT `users`.* FROM `users` ORDER BY `users`.`id` ASC LIMIT 1
=> #<User id: 1, email: "user-0@example.com", name: "user-0", gender: 0, created_at: "2021-08-26 17:50:40.661945000 +0000", updated_at: "2021-08-26 17:50:40.661945000 +0000">
```

## Try us out!

Pretty simple, huh? Try TiDB now to develop your Rails applications!

If you have any question or feedback about TiDB during your app building, feel free to contact us. You're also welcome to [join our Slack channel](https://slack.tidb.io/invite?team=tidb-community&channel=sig-k8s&ref=pingcap-blog) to have direct conversations with us, or [join us on GitHub](https://github.com/pingcap/tidb) to help improve TiDB further.
