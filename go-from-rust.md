---
title: Early Impressions of Go from a Rust Programmer
author: ['Nick Cameron']
date: 2020-02-26
summary: Nick Cameron is a long-time Rust programmer who has recently started using Go. In this post, he talks about his early impressions of Go. Read this post to learn more. 
tags: ['Go', 'Rust']
categories: ['Engineering']
image: /images/blog/early-impressions-of-go-from-a-rust-programmer.jpg
---


I've been using [Go](https://en.wikipedia.org/wiki/Go_(programming_language)) for the past few weeks. It's my first time using Go for a large (-ish), serious project. I've previously looked at Go a lot and played with examples and toy programs when researching features for [Rust](https://en.wikipedia.org/wiki/Rust_(programming_language)). Real programming is a very different experience.

I thought it would be interesting to write about my impressions. I'll try and avoid too much comparison with Rust, but since that is the language I'm coming from, there will be some. I should declare in advance a strong bias for Rust, but I'll do my best to be objective.

## General impression

Programming with Go is nice. It had everything I wanted in the libraries and there were not too many rough edges. Learning it was a smooth experience, and it is a well-designed and practical language. Some examples: once you know the syntax, many idioms from other languages carry over to Go. Once you've learned some Go, it is relatively easy to predict other features. With some knowledge of other languages, I was able to read Go code and understand it without too much googling.

It is a lot less frustrating and a lot more productive than using C/C++, Java, Python, etc. It did feel, however, like part of that generation of languages. It has learnt some lessons from them, and I think it is probably the best language of that generation; but it is definitely part of that generation. It is an incremental improvement, rather than doing something radically different (to be clear, this is not a value judgement, incremental is often good in software engineering). A good example of this is `nil`: languages like Rust and Swift have removed the concept of `null` and eliminated a whole class of errors. Go makes it a bit less dangerous: no null *values*, distinguishes between `nil` and `0`. But the core idea is still there, and so is the common runtime error of dereferencing a null pointer.

## Learnability

Go is incredibly easy to learn. I know this is an often-touted benefit, but I was really surprised how quickly I was able to be productive. Thanks to the language, docs, and tools, I was writing 'interesting', commit-able code after literally two days.

A few factors contributing to learnability are:

* Go is small. Lots of languages try to be small, Go really is small; really small. (This is mostly a good thing and I'm impressed with the discipline this must have taken).
* The standard library is good (and again, small). Finding and using libraries from the ecosystem is very easy.
* There is very little in the language which is not in other languages. Go takes lots of bits from other established languages, polishes them, and puts them together nicely. It tries very hard to avoid novelty.

## Boilerplate

Go code becomes very repetitive very quickly. It is missing any mechanism like macros or generics for reducing repetition (interfaces are nice for abstraction, but don't work so well to reduce code duplication). I often end up with lots of functions, identical except for types.

Error handling also causes repetition. Many functions have more `if err != nil { return err }` boilerplate than interesting code.

Using generics or macros to reduce boilerplate is sometimes criticised for making code easy to write at the expense of making it harder to read. But I found the opposite with Go. It is quick and easy to copy and paste code, but reading Go code is frustrating because you have to ignore so much of it or search for subtle differences.

## Things I like

* Compile times. Definitely quick; definitely a lot quicker than Rust. But not actually as quick as I was expecting (it feels to me to be similar to or a little faster than C/C++ for medium to large projects, I was kind of expecting instant).
* Go routines and channels. Having lightweight syntax for spawning Go routines and using channels is really nice. It really shows the power of syntax that such a small detail makes concurrent programming feel so much nicer than in other languages.
* Interfaces. They're not very sophisticated but they are easy to understand and use, and useful in a lot of places.
* `if ...; ... { }` syntax. Being able to restrict the scope of variables to the body of `if` statements is nice. This has a similar effect to `if let` in Swift and Rust, but is more general purpose (Go does not have pattern matching like Swift and Rust, so it cannot use `if let`.
* Testing and doc comments are easy to use.
* The `Go` tool is nice - having everything in one place rather than requiring multiple tools on the command line.
* Having a garbage collector (GC)! Not thinking about memory management really does make programming easier.
* Varargs.

## Things I did not like

In no particular order.

* `nil` slices - `nil`, a `nil` slice, and an empty slice are all different. I'm pretty sure you only need two of those things, not three.
* No first class enums. Using constants feels backwards.
* Disallowing import cycles. This really limits how useful packages are for modularising a project, since it encourages putting lots of files in a package (or having lots of small packages, which can be just as bad if files which should be together are not).
* `switch` may be non-exhaustive.
* `for ... range` returns a pair of index/value. Getting just the index is easy (just ignore the value) but getting just the value requires being explicit. This seems back-to-front to me since I need the value and not the index in most cases.
* Syntax:
  - Inconsistency between definitions and uses.
  - Pickiness of the compiler (e.g., requiring or forbidding trailing commas); this is mostly alleviated by good tooling, but there a still a few times when this creates an annoying extra step.
  - When using multiple-value return types, parentheses are required on the type, but not in the `return` statement.
  - Declaring a struct requires two keywords (`type` and `struct`).
  - Using capitalisation for marking variables public or private. It's like Hungarian notation but worse.
* Implicit interfaces. I know I have this on my thing I like list too, but sometimes it is really annoying - e.g., trying to find all types which implement an interface, or which interfaces are implemented for a given type.
* You can't write functions with a receiver in a different package, so even though interfaces are 'duck typed' they can't be implemented for upstream types making them much less useful.

I've already mentioned the lack of generics and macros above.

## Consistency

As a language designer and a programmer, probably the thing that most surprised me about Go is the frequent inconsistency between what is built-in and what is available to users. It has been a goal of many languages to eliminate as much magic as possible, and make built-in features available to users. Operator overloading is a simple, but controversial, example. Go has a lot of magic! And you very easily run into the wall of not being able to do things that built-in stuff can.

Some things that stood out to me:

* There is nice syntax for returning multiple values and for channels, but the two cannot be used together because there are no tuple types.
* There is a `for ... range` statement for iterating over arrays and slices, but you can't iterate over other collections because there is no concept of iterators.
* Functions like `len` and `append`, are global, but there is no way to make your own functions global. Those global functions only work with built-in types. They can also be generic, even though Go has 'no generics'!
* There is no operator overloading, this is particularly annoying with `==` because it means you can't use custom types as keys in a map unless they are *comparable*. That property is derived from the structure of a type and can't be overridden by the programmer.

## Conclusion

Go is a simple, small, and enjoyable language. It has some odd corners, but is mostly well-designed. It is incredibly fast to learn, and avoids any features which are not well-known in other languages.

Go is a very different language to Rust. Although both can vaguely be described as systems languages or 'replacements' for C, they have different goals and applications, styles of language design, and priorities. Garbage collection is a really huge differentiator. Having GC in Go makes the language much simpler and smaller, and easy to reason about. Not having GC in Rust makes it *really* fast (especially if you need guaranteed latency, not just high throughput), and enables features and programming patterns which are not possible in Go (or at least not without sacrificing performance).

Go is a compiled language with a well-implemented runtime. It is fast. Rust is also compiled, but has a much smaller runtime. It is *really fast*. Assuming no other constraints, I think the choice between using Go and Rust is a trade-off between a much shorter learning curve and simpler programs (which means faster development), versus Rust being really, really fast, and having a more expressive type system (which makes your programs safer and means faster debugging and error hunting).
