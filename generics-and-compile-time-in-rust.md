---
title: Generics and Compile-Time in Rust
author: ['Brian Anderson']
date: 2020-06-15
summary: This is the second episode of the Rust Compile Time series. Brian Anderson, one of Rust's original authors, talks about monomorphization, using the TiKV project as a case study.
tags: ['TiKV', 'Rust']
categories: ['Engineering']
image: /images/blog/rust-compile-time-adventures.png
---

**Author:** [Brian Anderson](https://github.com/brson?locale=ja) (Senior Database Engineer at PingCAP)

**Editor:** [Caitin Chen](https://github.com/CaitinChen)

![Rust Compile Time Adventures with TiKV](media/rust-compile-time-adventures.png)

The Rust programming language compiles fast software slowly.

In this series we explore Rust's compile times within the context of [TiKV], the key-value store behind the [TiDB] database.

[TiKV]: https://github.com/tikv/tikv
[TiDB]: https://github.com/pingcap/tidb

&nbsp;

## Rust Compile-time Adventures with TiKV: Episode 2

In [the previous post in the series][prev] we covered Rust's early development history, and how it led to a series of decisions that resulted in a high-performance language that compiles slowly. Over the next few we'll describe in more detail some of the designs in Rust that make compile time slow.

This time, we're talking about monomorphization.

[prev]: https://pingcap.com/blog/rust-compilation-model-calamity/

- [Comments on the last episode](#comments-on-the-last-episode)
- [A brief aside about compile-time scenarios](#a-brief-aside-about-compile-time-scenarios)
- [Monomorphized generics](#monomorphized-generics)
- [An example in Rust](#an-example-in-rust)
- [More about the tradeoff](#more-about-the-tradeoff)
- [In the next episode of Rust Compile-time Adventures with TiKV](#in-the-next-episode-of-rust-compile-time-adventures-with-tikv)
- [Thanks](#thanks)

## Comments on the last episode

After the [previous][prev] episode of this series, people made a lot of great comments on [HackerNews], [Reddit], and [Lobste.rs].

[HackerNews]: https://news.ycombinator.com/item?id=22197082
[Reddit]: https://www.reddit.com/r/rust/comments/ew5wnz/the_rust_compilation_model_calamity/
[Lobste.rs]: https://lobste.rs/s/xup5lo/rust_compilation_model_calamity

Some common comments:

- The compile times we see for TiKV aren't so terrible, and are comparable to
  C++.
- What often matters is partial rebuilds since that is what developers
  experience most in their build-test cycle.

Some subjects I hadn't considered:

- [WalterBright pointed out][wb] that data flow analysis (DFA) is expensive
  (quadratic). Rust depends on data flow analysis. I don't know how this
  impacts Rust compile times, but it's good to be aware of.
- [kibwen reminded us][kb] that faster linkers have an impact on build times,
  and that LLD may be faster than the system linker eventually.

[wb]: https://news.ycombinator.com/item?id=22199471
[kb]: https://www.reddit.com/r/rust/comments/ew5wnz/the_rust_compilation_model_calamity/fg07hvv/

## A brief aside about compile-time scenarios

It's tempting to talk about "compile-time" broadly, without any further clarification, but there are many types of "compile-time", some that matter more or less to different people. The four main compile-time scenarios in Rust are:

- development profile / full rebuilds
- development profile / partial rebuilds
- release profile / full rebuilds
- release profile / partial rebuilds

The "development profile" entails compiler settings designed for fast compile times, slow run times, and maximum debuggability. The "release profile" entails compiler settings designed for fast run times, slow compile times, and, usually, minimum debuggability. In Rust, these are invoked with `cargo build` and `cargo build --release` respectively, and are indicative of the compile-time/run-time tradeoff.

A full rebuild is building the entire project from scratch, and a partial rebuild happens after modifying code in a previously built project. Partial rebuilds can notably benefit from [incremental compilation][ic].

[ic]: https://rust-lang.github.io/rustc-guide/queries/incremental-compilation.html

In addition to those there are also

- test profile / full rebuilds
- test profile / partial rebuilds
- bench profile / full rebuilds
- bench profile / partial rebuilds

These are mostly similar to development mode and release mode respectively, though the interactions in cargo between development / test and release / bench can be subtle and surprising. There may be other profiles (TiKV has more), but those are the obvious ones for Rust, as built-in to cargo. Beyond that there are other scenarios, like typechecking only (`cargo check`), building just a single project (`cargo build -p`), single-core vs. multi-core, local vs. distributed, local vs. CI.

Compile time is also affected by human perception &mdash; it's possible for compile time to feel bad when it's actually decent, and to feel decent when it's actually not so great. This is one of the premises behind the [Rust Language Server][RLS] (RLS) and [rust-analyzer] &mdash; if developers are getting constant, real-time feedback in their IDE then it doesn't matter as much how long a full compile takes.

[RLS]: https://github.com/rust-lang/rls
[rust-analyzer]: https://github.com/rust-analyzer/rust-analyzer

So it's important to keep in mind through this series that there is a spectrum of tunable possibilities from "fast compile / slow run" to "fast run / slow compile", there are different scenarios that affect compile time in different ways, and in which compile time affects perception in different ways.

It happens that for TiKV we've identified that the scenario we care most about with respect to compile time is "release profile / partial rebuilds". More about that in future installments.

The rest of this post details some of the major designs in Rust that cause slow compile time. I describe them as "tradeoffs", as there are good reasons Rust is the way it is, and language design is full of awkward tradeoffs.

## Monomorphized generics

Rust's approach to generics is the most obvious language feature to blame on bad compile times, and understanding how Rust translates generic functions to machine code is important to understanding the Rust compile-time/run-time tradeoff.

Generics generally are a complex topic, and Rust generics come in a number of forms. Rust has generic functions and generic types, and they can be expressed in multiple ways. Here I'm mostly going to talk about how Rust calls generic functions, but there are further compile-time considerations for generic type translations. I ignore other forms of generics (like `impl Trait`), as either they have similar compile-time impact, or I just don't know enough about them.

As a simple example for this section, consider the following `ToString` trait and the generic function `print`:

```rust
use std::string::ToString;

fn print<T: ToString>(v: T) {
     println!("{}", v.to_string());
}
```

`print` will print to the console anything that can be converted to a `String` type. We say that "`print` is generic over type `T`, where `T` implements `Stringify`". Thus I can call `print` with different types:

```rust
fn main() {
    print("hello, world");
    print(101);
}
```

The way a compiler translates these calls to `print` to machine code has a huge impact on both the compile-time and run-time characteristics of the language.

When a generic function is called with a particular set of type parameters it is said to be _instantiated_ with those types.

In general, for programming languages, there are two ways to translate a generic function:

1) translate the generic function for each set of instantiated type parameters, calling each trait method directly, but duplicating most of the generic function's machine instructions, or

2) translate the generic function just once, calling each trait method through a function pointer (via a ["vtable"]).

["vtable"]: https://en.wikipedia.org/wiki/Virtual_method_table

The first results in _static_ method dispatch, the second in _dynamic_ (or "virtual") method dispatch. The first is sometimes called "monomorphization", particularly in the context of C++ and Rust, a confusingly complex word for a simple idea.

### An example in Rust

The previous example uses Rust's type parameters (`<T: ToString>`) to define a
statically-dispatched `print` function. In this section we present two more Rust
examples, the first with static dispatch, using references to `impl` trait
instances, and the second with dynamic dispatch, with references to `dyn` trait
instances.

Static ([playground link][pl1]):

[pl1]: https://play.rust-lang.org/?version=stable&mode=release&edition=2018&gist=066e72731fbdbf212f68c25b5a4e3b72

```rust
use std::string::ToString;

#[inline(never)]
fn print(v: &impl ToString) {
     println!("{}", v.to_string());
}

fn main() {
    print(&"hello, world");
    print(&101);
}

```

Dynamic ([playground link][pl2]):

[pl2]: https://play.rust-lang.org/?version=stable&mode=release&edition=2018&gist=d359d0440acaeed1d25020955979b9ce

```rust
use std::string::ToString;

#[inline(never)]
fn print(v: &dyn ToString) {
     println!("{}", v.to_string());
}

fn main() {
    print(&"hello, world");
    print(&101);
}
```

Notice that the only difference between these two cases is that the first
`print`'s argument is type `&impl ToString`, and the second's is `&dyn
ToString`. The first is using static dispatch, and the second dynamic.

In Rust `&impl ToString` is essentially shorthand for a type parameter argument
that is only used once, like in the earlier example `fn print<T: ToString>(v:
T)`.

Note that in these examples we have to use `inline(never)` to defeat the
optimizer. Without this it would turn these simple examples into the exact same
machine code. I'll explore this phenomenon further in a future episode of this
series.

Below is an extremely simplified and sanitized version of the assembly
for these two examples. If you want to see the real thing, the playground
links above can generate them by clicking the buttons labeled `... -> ASM`.

```
print::hffa7359fe88f0de2:
    ...
    callq   *::core::fmt::write::h01edf6dd68a42c9c(%rip)
    ...

print::ha0649f845bb59b0c:
    ...
    callq   *::core::fmt::write::h01edf6dd68a42c9c(%rip)
    ...

main::h6b41e7a408fe6876:
    ...
    callq   print::hffa7359fe88f0de2
    ...
    callq   print::ha0649f845bb59b0c
```

And the dynamic case:

```
print::h796a2cdf500a8987:
    ...
    callq   *::core::fmt::write::h01edf6dd68a42c9c(%rip)
    ...

main::h6b41e7a408fe6876:
    ...
    callq   print::h796a2cdf500a8987
    ...
    callq   print::h796a2cdf500a8987
```

The important thing to note here is the duplication of functions or lack
thereof, depending on the strategy. In the static case there are two `print`
functions, distinguished by a hash value in their names, and `main` calls both
of them. In the dynamic case, there is a single `print` function that `main`
calls twice. The details of how these two strategies actually handle their
arguments at the machine level are too intricate to go into here.

### More about the tradeoff

These two strategies represent a notoriously difficult tradeoff: the first creates lots of machine instruction duplication, forcing the compiler to spend time generating those instructions, and putting pressure on the instruction cache, but &mdash; crucially &mdash; dispatching all the trait method calls statically instead of through a function pointer. The second saves lots of machine instructions and takes less work for the compiler to translate to machine code, but every trait method call is an indirect call through a function pointer, which is generally slower because the CPU can't know what instruction it is going jump to until the pointer is loaded.

It is often thought that the static dispatch strategy results in faster machine code, though I have not seen any research into the matter (we'll do an experiment on this subject in a future edition of this series). Intuitively, it makes sense &mdash; if the CPU knows the address of all the functions it is calling it should be able to call them faster than if it has to first load the address of the function, then load the instruction code into the instruction cache. There are though factors that make this intuition suspect:

- first, modern CPUs have invested a lot of silicon into branch prediction, so
  if a function pointer has been called recently it will likely be predicted
  correctly the next time and called quickly;
- second, monomorphization results in huge quantities of machine instructions, a
  phenomenon commonly referred to as "code bloat", which could put great
  pressure on the CPU's instruction cache;
- third, the LLVM optimizer is surprisingly smart, and with enough visibility
  into the code can sometimes turn virtual calls into static calls.

C++ and Rust both strongly encourage monomorphization, both generate some of the fastest machine code of any programming language, and both have problems with code bloat. This seems to be evidence that the monomorphization strategy is indeed the faster of the two. There is though a curious counter-example: C. C has no generics at all, and C programs are often both the slimmest _and_ fastest in their class. Reproducing the monomorphization strategy in C requires using ugly C macro preprocessor techniques, and modern object-orientation patterns in C are often vtable-based.

_Takeaway: it is a broadly thought by compiler engineers that monomorphiation results in somewhat faster generic code while taking somewhat longer to compile._

Note that the monomorphization-compile-time problem is compounded in Rust because Rust translates generic functions in every crate (generally, "compilation unit") that instantiates them. That means that if, given our `print` example, crate `a` calls `print("hello, world")`, and crate `b` also calls `print("hello, world, or whatever")`, then both crate `a` and `b` will contain the monomorphized `print_str` function &mdash; the compiler does all the type-checking and translation work twice. This is partially mitigated today at lower optimization levels by [shared generics], though there are still duplicated generics [in sibling dependencies][sib],
and at higher optimization levels.

[shared generics]: https://github.com/rust-lang/rust/issues/47317#issuecomment-478894318
[sib]: https://github.com/rust-lang/rust/pull/48779

All that is only touching on the surface of the tradeoffs involved in monomorphization. I passed this draft by [Niko], the primary type theorist behind Rust, and he had some words to say about it:

[Niko]: https://github.com/nikomatsakis

> niko: so far, everything looks pretty accurate, except that I think the monomorphization area leaves out a lot of the complexity. It's definitely not just about virtual function calls.

> niko: it's also things like `foo.bar` where the offset of bar depends on the type of foo

> niko: many languages sidestep this problem by using pointers everywhere (including generic C, if you don't use macros)

> niko: not to mention the construction of complex types like iterators, that are basically mini-programs fully instantiated and then customizable -- though this *can* be reproduced by a sufficiently smart compiler

> niko: (in particular, virtual calls can be inlined too, though you get less optimization; I remember some discussion about this at the time ... how virtual call inlining happens relatively late in the pipeline)

> brson: does the field offset issue only come in to play with associated types?

> niko: no

> niko: `struct Foo<T> { x: u32, y: T, z: f64 }`

> niko: `fn bar<T>(f: Foo<T>) -> f64 { f.z }`

> niko: as I recall, before we moved to monomorphization, we had to have two paths for everything: the easy, static path, where all types were known to LLVM, and the horrible, dynamic path, where we had to generate the code to dynamically compute the offsets of fields and things

> niko: unsurprisingly, the two were only rarely in sync

> niko: which was a common source of bugs

> niko: I think a lot of this could be better handled today -- we have e.g. a reasonably reliable bit of code that computes Layout, we have MIR which is a much simpler target -- so I am not as terrified of having to have those two paths

> niko: but it'd still be a lot of work to make it all work
>
> niko: there was also stuff like the need to synthesize type descriptors on the fly (though maybe we could always get by with stack allocation for that)

> niko: e.g., `fn foo<T>() { bar::<Vec<T>>(); } fn bar<U>() { .. }`

> niko: here, you have a type descriptor for T that was given to you dynamically, but you have to build the type descriptor for Vec&lt;T&gt;

> niko: and then we can make it even worse

> niko: `fn foo<T>() { bar::<Vec<T>>(); } fn bar<U: Debug>() { .. }`

> niko: now we have to reify all the IMPLS of Debug

> niko: so that we can do trait matching at runtime

> niko: because we have to be able to figure out `Vec<T>: Debug`, and all we know is `T: Debug`

> niko: we might be able to handle that by bubbling up the Vec&lt;T&gt; to our callers...

## In the next episode of Rust Compile-time Adventures with TiKV

In the next episode of this series we'll discuss compilation units -- the
bundles of code that a compiler processes at a single time -- and how selecting
compilation units affects compile time.

Stay Rusty, friends.

## Thanks

A number of people helped with this blog series. Thanks especially to Niko Matsakis for the feedback, and Calvin Weng for proofreading and editing.
