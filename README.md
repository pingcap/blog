# PingCAP Blog

## Front Matter Example

```yaml
---
title: Blog Title
author: ['Author']
date: yyyy-mm-dd
summary: Blog Summary
tags: ['tag1', 'tag2']
categories: ['category']
image: /images/blog/...
---
```

## Metadata

- title
- author
  - format: list(array) **['author-1', 'author-2']**
- date:
  - format: **yyyy-mm-dd**
- summary
- tags -
  - format: list(array)  **['tag-1', 'tag-2']**
- categories
  - format: list(array) **['category']**
  - category values: Engineering, HTAP, MySQL Scalability, Open Source Community

## For SEO and social media share

- image: /images/blogs/...

> This is used to show the thumbnail shown in the social media platform.

- summary: PingCAP is focused on developing distributed NewSQL and is the team building TiDB, an open-source distributed NewSQL database.

> This is for the description shown in the social media platform.

## Lint

We use [https://github.com/DavidAnson/markdownlint](https://github.com/DavidAnson/markdownlint) to lint all `.md` files.

To better check while writing, you can use [vscode](https://code.visualstudio.com/) + [vscode-markdownlint extension for VS Code](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint).
