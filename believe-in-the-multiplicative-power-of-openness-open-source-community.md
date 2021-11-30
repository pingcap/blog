---
title: Believe in the Multiplicative Power of Openness
author: ['Max Liu']
date: 2021-11-30
summary: Max Liu, PingCAP CEO, talks about the power of open source. Learn how the open source community helps PingCAP grow and how PingCAP gives back to the community. 
tags: ['DevCon', 'Open source']
categories: ['Company']
image: /images/blog/how-open-source-community-benefits-pingcap-and-vice-versa.png
---
**Author:** [Max Liu](https://github.com/ngaut) (CEO and co-founder of PingCAP)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![How Open Source Community Benefits PingCAP and Vice Versa](media/how-open-source-community-benefits-pingcap-and-vice-versa.png)

*This article is based on the keynote speech given by Max Liu at PingCAP DevCon 2021.*

When I started this company six years ago, in a small, drab room perched in the north suburb of Beijing, I never thought that one day I'd be connected with a professor who worked at a university in Guatemala. [Sergio Méndez](https://sergiops.xyz/about/), a professor of software engineering at Guatemala San Carlos University—the other end of the connection—built a distributed system with his students to [visualize Covid-19 vaccinated people around the world](https://github.com/sergioarmgpl/operating-systems-usac-course/blob/master/lang/en/projects/project1v3/project1.md). To ensure the stability of this system, they tested it with [Chaos Mesh](https://chaos-mesh.org/), a CNCF hosted chaos engineering platform that was originally created and open sourced by PingCAP. 

This connection caught us by surprise. We never dreamed of contributing to public health in such a meaningful way. Imagine: PingCAP playing a part in the fight against the pandemic. 

If you think about it, Sergio and his project best exemplify how the open-source community grows and changes the world. Its power is not restricted by the borders on a map. An idea goes where it's needed; it expands itself to other parts of the world and connects thousands of people. At PingCAP, we affectionately call this "the power of openness."

**The open-source community has formed a virtuous cycle.** Pick an open-source project in the wild, and you may see that it's built from several other open-source projects; if you're lucky, you may find it also spawns several other projects. An individual who _benefits_ from the open-source community also _contributes_ to the community, and the benefits pass on to even more people.

## The power of openness

Six years ago, we started PingCAP with a simple idea: to create a database that's easier to build data-intensive applications. With this database, business owners could rely on a single data stack to power their giant ideas and make informed decisions based on real and single source of truth; application developers can be freed to focus on building applications from worrying about the data infrastructure; engineers and database administrators (DBAs) that looked after large-scale databases would be able to lean back and relax and have a good night's sleep—a luxury for most of them at that time.

A database like that wouldn't be built by a handful of engineers behind closed doors. If you ask me, **a great database is never _designed_ beforehand**. It is formed, evolved, constantly improved, and battle-tested through innumerable real-world use cases in a consistent, long-term effort. 

But how can a startup database company get the real-world use cases it needs? We gained our customers and test cases one at a time. People believed in us **because our [TiDB](https://en.pingcap.com/products/tidb/) database was an open-source database and they—just like us—believed in the power of open source.** 

As our project grew, it gained traction among open-source enthusiasts and formed a vibrant community. The community fed us with feature requests, bug reports, product feedback, and code contributions. **We were no longer a handful of engineers.** The community connected us with thousands of database professionals and brought us first-hand, invaluable voices that helped TiDB grow faster. [Some](https://github.com/tikv/tikv/pull/9637) helped us build new features; [some](https://github.com/pingcap/tidb/issues/20971) put forward important requirements that leveled up our product competitiveness. Again, the open-source community did us right.

This is why we know TiDB is the product jointly created by every developer and user. They built TiDB as it is today. And I'm proud to say that PingCAP wouldn't be the same without the open-source community. 

## Giving back to the open source community

Now our projects have over 41 K stargazers on GitHub. More than 1,400 contributors have helped improve our code or documentation. More than a thousand enterprises or individual developers build their applications with TiDB and give consistent feedback.

We are grateful. In an old-fashioned software company, people say that at the end of the day their most valuable assets, their employees, of the company leave the building. But for an open-source software company, like PingCAP, the real assets are not only in the head office. Our assets are more intangible. They're on the internet—every application use case, every pull request on GitHub, and every interaction among the community members. 

**As we grow, we give back to the community.** Apart from TiDB, we also open sourced [TiKV](https://tikv.org/) and [Chaos Mesh](https://chaos-mesh.org/) and donated these projects to the [Cloud Native Computing Foundation](https://www.cncf.io/) (CNCF). In [CNCF's 2020 annual report](https://www.cncf.io/cncf-annual-report-2020/), we were recognized as [the 6th largest contributor](https://all.devstats.cncf.io/d/5/companies-table?orgId=1) across all projects in CNCF, with a total of 84,816 contributions. "... [This] is quite crazy given a company of your size," says [Chris Aniszczyk](https://twitter.com/cra), CTO of CNCF. "If you look at the companies ahead of you, like Google, Red Hat, VMware, and Microsoft—these are large companies." Crazy as we are, we pride ourselves on making active contributions. 

Sharing code is not enough, and we go far beyond this. There are 209 repositories that help make adopting TiDB easier and building Rust projects easier, and my favorite part is that we also unreservedly share our knowledge. When we focused on building a distributed SQL database and a key-value store (in Rust!), the most talented people in this field joined us. We wanted to help more people with our resources, so we designed a series of [open-source courses](https://github.com/pingcap/talent-plan) on Rust and on distributed systems. We hope to help more people gain access to the knowledge and skills in the field we're passionately working on.

## Summary

What is the essence of open-source software and the open-source community?

My experience with TiDB and PingCAP has taught me that **open source is not just making the source code available to others**. It's about the connection between technology and mankind, the connection between people. Code is just a medium for this connection.

The open-source community has helped shape PingCAP into what it is today. PingCAP gives back to the community and makes it better. That makes a good, virtuous cycle for me. 
