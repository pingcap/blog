---
title: Migrating the TiKV Rust Client from Futures 0.1 to 0.3
author: ['Nick Cameron']
date: 2019-08-08
summary: This post introduces Nick's experience in migrating the TiKV Rust client from Futures 0.1 to 0.3.
tags: ['TiKV', 'Rust']
categories: ['Engineering']
---

I recently migrated a small/medium-sized crate from Futures 0.1 to 0.3. It was fairly easy, but there were some tricky bits and some things that were not well documented, so I think it is worth me writing up my experience.

The crate I migrated is the [Rust client](https://github.com/tikv/client-rust) for the TiKV database. It is about 5500 LoC and uses futures fairly heavily (because it communicates with TiKV using gRPC and the interface to that is async).

Asynchronous programming in Rust is a large area and has been in development for some time. One of the core parts is the [futures](https://github.com/rust-lang-nursery/futures-rs) library, a standard Rust library which provides data types and functionality for programming using futures. It is essential for asynchronous programming, but it is not everything you need - you also need libraries for driving the event loop and interacting with the operating system.

Over the years, the futures library has changed a lot. A lot of older code was developed using the 0.1 series of releases and has not been updated. The more recent versions are the 0.3 series (futures-preview on crates.io). The reason for this divergence is that there are a lot of changes between 0.1 and 0.3. 0.1 is fairly stable, whereas 0.3 has been evolving rapidly. In the long term, 0.3 will turn into 1.0; parts of the library are moving into std, and the first parts have recently been stabilized (e.g., the `Future` trait).

We want the Rust client to work with stable compilers, so we limited the core library to only use features which are stable or would be soon. We did use async/await in our documentation and examples since it is so much more ergonomic, and will eventually be the recommended way to program asynchronously in Rust. As well as avoiding async/await in our library, we also depend on crates which use futures 0.1, which means we needed to use the compatibility layer a lot. Therefore, this might not be a totally typical migration.

I'm not an async expert and I think there might be ways we could make this migration (and the code in general) more idiomatic. If you have suggestions, please let me know on [Twitter](https://twitter.com/nick_r_cameron). If you'd like to contribute a PR, that would be even better! We would love to get more people involved with the [TiKV client](https://github.com/tikv/client-rust).

## Mechanical changes

These changes were either "search and replace" changes, or didn't require much thinking.

The biggest change is that the 0.1 `Future` signature included an `Error` associated type and `poll` always returned a `Result`. In 0.3, the error type has been removed and if you want to handle errors you must do so explicitly. To preserve behavior, we need to change all occurrences of `Future<Item=Foo, Error=Bar>` to `Future<Output=Result<Foo, Bar>>` (note the name change from `Item` to `Output`). With that change, `poll` returns the same type and so there are no changes required when using futures.

If you define your own futures, then you need to update their definitions too, considering whether you need to handle errors.

There is a `TryFuture` type in futures 0.3 which is roughly equivalent to `Future<Output=Result<...>>`. However, it is best to avoid it as much as possible - using it means you have to convert between `Future` and `TryFuture`. It has a blanket impl, which makes it easy to use some functions on these kind of futures by using the `TryFutureEx` trait.

`Future::poll` takes a new context argument in futures 0.3. Mostly, this just needs propagating through `poll` calls (and occasionally ignoring).

Our dependencies are still using futures 0.1, so we have to convert between the two libraries. This is mostly not too difficult because futures 0.3 includes some compatibility shims and other utilities (`Compat01As03`, etc.). These must be used where we call into our dependencies.

The `wait` method has been removed from the `Future` trait. This was a good idea since the method was  a bit of a footgun. It can be replaced by either `.await` or `executor::block_on` (note that the latter blocks the whole thread, not just the current future).

## Pin

Futures 0.3 makes heavy use of the [`Pin`](https://doc.rust-lang.org/nightly/std/pin/index.html) type, in particular for the type of `self` in the signature of `Future::poll`. Other than the mechanical change to signatures, I had to do a bit of juggling using `Pin::get_unchecked_mut` and `Pin::new_unchecked` (both unsafe) to project fields of futures.

Pinning is a subtle and complicated concept. I still don't feel like I have a great grasp of it all. The best reference I'm aware of is the [std::pin docs](https://doc.rust-lang.org/nightly/std/pin/index.html). I'll try and summarize the ideas here (there are some important subtleties that I'm not going to touch on at all, and this is not intended to be a tutorial on pinning):

* `Pin` is a type constructor which only makes sense when applied to a pointer type, e.g., `Pin<Box<_>>`.
* `Pin` itself is a marker/wrapper type (a bit like [`NonNull`](https://doc.rust-lang.org/nightly/std/ptr/struct.NonNull.html)), not a pointer type. You should read `Pin<Box<Foo>>` as "a pinned Box pointer to Foo" or "a Box\<Foo\> which is guaranteed to be pinned".
* If a pointer is pinned, that means that the value pointed to by the pointer will never be moved (moving happens when a non-`Copy` object is passed by value, or via `mem::swap`). Note that the value is allowed to move *before* the pointer is pinned, but not *after*.
* If a type implements the `Unpin` trait, it means that it never actually matters whether that type is moved or not. In other words, we can safely pretend that a pointer to that type is pinned, even when it is not.
* `Pin` and `Unpin` are not built into the language at all, although some language features indirectly rely on pinning guarantees. Pinning is compiler-enforced without the compiler knowing anything about it. (This is really cool, and is a great demonstration of how powerful Rust's trait system is for this sort of thing). It works like this: `Pin<P<T>>` only permits safe access to `P`, which does not permit moving any value that `P` points to, unless `T` implements `Unpin` (i.e., the programmer has asserted that `T` does not care about being moved). Operations which could allow a non-`Unpin` value to be moved (basically mutable access) is `unsafe`, and it is up to the programmer to not move anything and guarantee that nothing can be moved later in safe code.

OK, back to the futures migration. Whenever you end up using unsafe methods on `Pin` you have to think about all of the above in order to ensure the pinning invariants. See the [std::pin docs](https://doc.rust-lang.org/nightly/std/pin/index.html) for more on how to reason about this. In many of the places I had to use field projection, the reason is to call `poll` on another future (sometimes indirectly). For that you need a pinned pointer and so you need *structural pinning* (i.e., you project a field of `Pin<&mut T>` to `Pin<&mut FieldType>`).

## Functions

An irritating aspect of the migration was that a lot of the names of functions (and types) in the futures library have changed. These name changes were sometimes hard to automate because the names are often shared with very common names in standard libraries. Some example name changes are `Async` to `Poll`, `Ok` to `ready`, `for_each` to `then`, `then` to `map`, and `Either::A` to `Either::Left` (likewise, `B`/`Right`).

Sometimes the name stayed the same, but the semantics of the function changed slightly (or both!). A common change was taking a closure which returned a future that produces a `T` rather than returning a `T` itself.

Many of the combinator functions moved from the `Future` trait to one of the extension crates. This is an easy issue to fix, but sometimes this fix is hard to deduce from the error message.

## LoopFn

The futures 0.1 library included a `LoopFn` future for handling futures which do something multiple times. It has been removed from futures 0.3, which, I believe, is because a `for` loop in an `async` function or using streams are better solutions in the long term. To make the migration straightforward, I created our own version of the 0.3 `LoopFn` future. This was mostly a copy/paste job with some adjustments (e.g., to handle pinning projection): [code](https://github.com/tikv/client-rust/pull/41/commits/6353dbcfe391d66714686aafab9a49e593259dfb#diff-eeffc045326f81d4c46c22f225d3df90R28). Later I converted several uses of `LoopFn` to use streams, which improved the code somewhat.

## Sink::send_all

In a few places in the project, we use sinks. I found the migration of these much less easy than for futures. The trickiest issue was that `Sink::send_all` has changed. In 0.1, it took ownership of a stream and once everything is resolved, returned the sink and stream. In 0.3, it takes a mutable reference to the stream and returns nothing. I created our own [compatibility layer](https://github.com/tikv/client-rust/pull/41/commits/6353dbcfe391d66714686aafab9a49e593259dfb#diff-eeffc045326f81d4c46c22f225d3df90R68) to emulate 0.1 sinks with 0.3 futures. This wasn't particularly difficult, but there might be a better way to do this.

You can see the whole conversion in [Migrate to futures 0.3 from 0.1](https://github.com/tikv/client-rust/pull/41). This article was originally posted at [Featherweight Musings](https://www.ncameron.org/blog/migrating-a-crate-from-futures-0-1-to-0-3/).
