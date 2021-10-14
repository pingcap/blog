---
title: Rust's Huge Compilation Units
author: ['Brian Anderson']
date: 2020-06-22
summary: The third episode of the Rust Compile Time series discusses why Rust's compilation units are so big and how that affects compile times.
tags: ['TiKV', 'Rust']
categories: ['Engineering']
image: /images/blog/rust-compile-time-adventures.png
aliases: ['/blog/Rust-s-Huge-Compilation-Units/']
---

**Author:** [Brian Anderson](https://github.com/brson) (Senior Database Engineer at PingCAP)

**Editor:** [Caitin Chen](https://github.com/CaitinChen)

![Rust huge compilation units](media/rust-compile-time-adventures.png)

The Rust programming language compiles fast software slowly.

In this series we explore Rust's compile times within the context of [TiKV](https://github.com/tikv/tikv), the key-value store behind the [TiDB](https://docs.pingcap.com/tidb/stable/overview) database.

## Rust Compile-time Adventures with TiKV: Episode 3

Lately we're exploring how Rust's designs discourage fast compilation. In [the previous post in the series](https://pingcap.com/blog/generics-and-compile-time-in-rust/) we discussed the difficult compile-time tradeoffs required to implement generics.

This time we're going to talk about compilation units.

- [Compilation units](#compilation-units)
- [Dependency graphs and unstirring spaghetti](#dependency-graphs-and-unstirring-spaghetti)
- [Trait coherence and the orphan rule](#trait-coherence-and-the-orphan-rule)
- [Internal parallelism](#internal-parallelism)
- [Large vs. small crates](#large-vs-small-crates)
- [In the next episode of Rust Compile-time Adventures with TiKV](#in-the-next-episode-of-rust-compile-time-adventures-with-tikv)
- [Thanks](#thanks)

## Compilation units

A _compilation unit_ is the basic unit of work that a language's compiler operates on. In C and C++ the compilation unit is a source file. In Java it is a source file. In Rust the compilation unit is a _crate_, which is composed of many files.

The size of compilation units incur a number of tradeoffs. Larger compilation units take longer to analyze, translate, and optimize than smaller compilation units. And in general, when a change is made to a single compilation unit, the whole compilation unit must be recompiled.

More, smaller crates improve the _perception_ of compile time, if not the total compile time, because a single change may force less of the project to be recompiled. This benefits the "partial recompilation" use cases. A project with more crates though may do more work on a full recompile due to a variety of factors, which I will summarize at the end of this post.

Rust crates don't have to be large, but there are a variety of factors that encourage them to be. The first is simply the relative complexity of adding new crates to a Rust project vs. adding a new module to a crate. New Rust projects tend to turn into monoliths unless given special attention to abstraction boundaries.

## Dependency graphs and unstirring spaghetti

Within a crate, there are no fundamental restrictions on module interdependencies, though there are language features that allow some amount of information-hiding within a crate. The big advantage and risk of having modules coexist in the same crate is that they can be _mutually dependent_, two modules both depending on names exported from the other. Here's an example similar to many encountered in TiKV, in which `engine` imports ("uses") `network::Message` and `network` imports `storage::Engine`.

```rust
mod storage {
  use network::Message;

  pub struct Engine;

  impl Engine {
    pub fn handle_message(&self, msg: Message) -> Result<()> { ... }
  }
}

mod network {
  use storage::Engine;

  pub enum Message { ... }

  struct Server {
    engine: Engine,
  }

  impl Server {
    fn handle_message(&self, msg: Message) -> Result<()> {
      ...

      self.engine.handle_message(msg)?;

      ...
    }
  }
}
```

Modules with mutual dependencies are useful for reducing cognitive complexity simply because they break up code into smaller units. As an abstraction boundary though they are deceptive: they are not truly independent, and cannot be trivially reduced further into separate crates.

And that is because _dependencies between crates must form a directed acyclic graph (a DAG)_; they do not support mutual dependencies.

Rust crates being daggish are mostly due to fundamental reasons of type checking and architectural complexity. If crates allowed for mutual dependencies then they would no longer be self-contained compilation units.

In preparation for this blog I asked a few people if they could recall the reasons why Rust crates must form a DAG, and [Graydon](https://github.com/graydon) gave a typically thorough and authoritative answer:

> graydon: Prohibits mutual recursion between definitions across crates, allowing both an obvious deterministic bottom-up build schedule without needing to do some fixpoint iteration or separate declarations from definitions
and enables phases that need to traverse a complete definition, like typechecking, to happen crate-at-a-time (enabling _some_ degree of incrementality / parallelism).

> graydon: (once you know you've seen all the cycles in a recursive type you can check it for finiteness and then stop expanding it at any boxed variants -- even if they cross crates -- and put a lazy / placeholder definition in those boxed edges; but you need to know those variants don't cycle back!)

> graydon: (I do not know if rustc does anything like this anymore)

> graydon: cyclicality concerns are even worse with higher order modules, which I was spending quite a lot of time studying when working on the early design. most systems I've seen require you to paint some kind of a boundary around a group of mutually-recursive definitions to be able to resolve them, so the crate seemed like a natural unit for that.

> graydon: then there is also the issue of versioning, which I think was pretty heavy in my mind (especially after the experience with monotone and git): a lot of versioning questions don't really make sense without acyclic-by-construction references. Like if A 1.0 depends on B 1.0 which depends on A 2.0 you, again, need to do something weird and fixpointy and potentially quite arbitrary and hard to explain to anyone in order to resolve those dependencies.

> graydon: also recall we wanted to be able to do hot code loading early on, which means that much like version-resolving, compiling or linking, your really in a much simpler place if there's a natural topological order to which things you have to load or unload. you can decide whether a crate is still live just by reference-counting, no need to go figure out cyclical dependencies and break them in some random order, etc.

> graydon: I'm not sure which if any of these was the dominant concern. If I had to guess I'd say avoiding problems with separate compilation of recursive definitions and managing code versioning. recall the language in the manual / the rationale for crates: "units of compilation and versioning". Those were the consideration for their existence as separate from modules. Modules get to be recursive. Crates, no. Because of things to do with "compilation and versioning".

> graydon: I cannot make a simple argument about this because I'm still not smart enough about module systems — the full thing is laid out in [dreyer's thesis](https://people.mpi-sws.org/~dreyer/thesis/main.pdf) and discussed in shorter [slide-deck form here](http://macqueenfest.cs.uchicago.edu/slides/dreyer.pdf) — but suffice to say that recursive modules make it possible to see the "same" opaque type through two paths that should probably be considered equal but aren't easily determined to be so, I think in part due to the mix of opacity that modules provide and the fact that you have to partly look through that opacity to resolve recursion. so anyway I decided this was probably getting into "research" and I should just avoid the problem space, go with acyclic modules.

Although driven by fundamental constraints, the hard daggishness of crates is useful for a number of reasons: it enforces careful abstractions, defines units of _parallel_ compilation, defines basically sensible codegen units, and dramatically reduces language and compiler complexity (even as the compiler likely moves toward whole-program, demand-driven, compilation in the future).

Note the emphasis on _parallelism_. The crate DAG is the simplest source of compile-time parallelism Rust has access to. Cargo today will use the DAG to automatically divide work into parallel compilation jobs.

So it's quite desirable for Rust code to be broken into crates that form a _wide_ DAG.

In my experience though projects tend to start in a single crate, without great attention to their internal dependency graph, and once compilation time becomes an issue, they have already created a spaghetti dependency graph that is difficult to refactor into smaller crates.

It happened to Servo, and it has also been my experience on TiKV, where I have made multiple aborted attempts to extract various modules from the main program, in long sequences of commits that untangle internal dependencies. I suspect that avoiding problematic monoliths is something that Rust devs learn with experience, but it is a repeating phenomenon in large Rust projects.

<div class="trackable-btns">
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('Rust's Huge Compilation Units', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

## Trait coherence and the orphan rule

Rust's trait system further makes it challenging to use crates as abstraction boundaries because of a thing call the _orphan rule_.

Traits are the most common tool for creating abstractions in Rust. They are powerful, but like much of Rust's power, it comes with a tradeoff.

The [orphan rule](https://smallcultfollowing.com/babysteps/blog/2015/01/14/little-orphan-impls/) helps maintain [trait coherence](https://doc.rust-lang.org/reference/items/implementations.html#trait-implementation-coherence), and exists to ensure that the Rust compiler never encounters two implementations of a trait for the same type. If it were to encounter two such implementations then it would need to resolve the conflict while ensuring that the result is sound.

What the orphan rule says, essentially, is that for any `impl`, either the _trait_ must be defined in the current crate, or the _type_ must be defined in the current crate.

This can create a tight coupling between abstractions in Rust, discouraging decomposition into crates &mdash; sometimes the amount of ceremony, boilerplate and creativity it takes to obey Rust's coherence rules, while also maintaining principled abstraction boundaries, doesn't feel worth the effort, so it doesn't happen.

This results in large crates which increase partial rebuild time.

This subject deserves more examples and a stronger argument, but I haven't the enthusiasm for it now.

Haskell's type classes, on which Rust's traits are based, do not have an orphan rule. I do not know the extent of problems this causes in practice for Haskell. At the time of Rust's design, it was thought to be problematic enough to correct.

## Internal parallelism

As crates are the main unit of parallelism in compilation pipeline, in theory it is desirable to have a wide crate DAG with roughly equally-complex crates, such that the compiler can be using all the machines cores all the time. In practice though there are almost always bottlenecks where there is only one compiler instance running, working on a single crate.

So in addition to `cargo`s parallel crate compilation, `rustc` itself is parallel over a single crate. It wasn't designed to be parallel though, so its parallelism is limited and hard-won.

Today the only real internal parallelism in `rustc` is the use of [_codegen units_](https://doc.rust-lang.org/rustc/codegen-options/index.html), by which `rustc` automatically divides a crate into multiple LLVM modules during translation. By doing this it can perform code generation in parallel. Like a crate, a Rust codegen-unit is also a compilation unit, but it is an LLVM compilation unit.

Combined with [_incremental compilation_](https://rust-lang.github.io/rustc-guide/queries/incremental-compilation.html), it can avoid re-translating codegen units which have not changed from run to run, decreasing partial rebuild time. Unfortunately, the impact of codegen units and incremental compilation on both compile-time and run-time performance is hard to predict: improving rebuild time depends on `rustc` successfully dividing a crate into independent units that are unlikely to force each other to recompile when changed, and it's not obvious how humans should write their code to help `rustc` in this task; and arbitrarily dividing up a crate into codegen units creates arbitrary barriers to inlining, causing unexpected de-optimizations.

The rest of the compiler's work is completely serial, though soon it should [perform some analysis in parallel](https://internals.rust-lang.org/t/help-test-parallel-rustc/11503/14).

### Large vs. small crates

The compilation properties affected by compilation unit size is large, and I've given up trying to explain them all coherently. Here's a list of some of them.

- Compilation unit parallelism &mdash; as discussed, parallelising compilation units is trivial.

- Inlining and optimization &mdash; inlining happens at the compilation unit level, and inlining is the key to unlocking optimization, so larger compilation units are better optimized. This story is complicated though by link-time-optimization (LTO).

- Optimization complexity &mdash; optimization tends to have superlinear complexity in code size, so bigger compilation units increase compilation time non-linearly.

- Downstream monomorphization &mdash; generics are only translated once they are instantiated, so even if all crates are perfectly equally sized for parallel compilation, their generic types will not be translated until later stages in the crate graph. This can result in the "final" crate having a disproportionate amount of translation compared to the others.

- Generic duplication &mdash; generics are translated in the crate which instantiates them, so more crates that use the same generics means more translation time.

- Link-time optimization (LTO) &mdash; release builds tend to have a final "link-time optimization" step that performs optimizations across multiple code units, and it is extremely expensive.

- Saving and restoring metadata &mdash; Rust needs to save and load metadata about each crate and each dependency, each time it is run, so more crates means more redundant loading.

- Parallel "codegen units" &mdash; `rustc` can automatically split its LLVM IR into multiple compilation units, called "codegen units". The degree to which it is effective at this depends a lot on how a crate's internal dependencies are organized and the compiler's ability to understand them. This can result in faster partial recompilation, at the expense of optimization, since inlining opportunities are lost.

- Compiler-internal parallelism &mdash; Parts of `rustc` itself are parallel. That internal parallelism has its own unpredictable bottlenecks and unpredictable interactions with external build-system parallelism.

Unfortunately, because of all these variables, it's not at all obvious for any given project what the impact of refactoring into smaller crates is going to be. Anticipated wins due to increased parallelism are often erased by other factors such as downstream monomorphization, generic duplication, and LTO.

## In the next episode of Rust Compile-time Adventures with TiKV

In the next episode of this series we'll wrap up this exploration of the reason's for Rust's slow compile times with a few smaller slow-compilation tidbits.

Then maybe we'll move on to something new, like techniques for speeding up Rust builds.

Stay Rusty, friends.

## Thanks

A number of people helped with this blog series. Thanks especially to Graydon Hoare for the feedback, and Calvin Weng for proofreading and editing.
