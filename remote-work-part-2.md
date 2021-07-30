---
title: Remote Work - Part 2
author: ['Nick Cameron']
date: 2020-02-14
summary: Nick Cameron has nearly ten-year experience of remote work. In this post, he discusses communication in remote work.
tags: ['Careers']
categories: ['Company']
image: /images/blog/remote-work-part-2.png
---

**Author:** [Nick Cameron](https://github.com/nrc) (Database Engineer at PingCAP)

**Editor:** [Caitin Chen](https://github.com/CaitinChen)

![Remote work - part 2](media/remote-work-part-2.png)

In my [last post](https://pingcap.com/blog/remote-work-part-1/) I talked a bit about some general issues with remote work. In this post I am going to focus on communication - probably the most important thing for remote workers to master. I am personally still working on this stuff - I'm a bit shy and an introvert and need to do better at keeping in touch.

Two things that impact communication for remote workers is that you are not visible and you are not present. The first means that, despite their best efforts, you will not be at the forefront of your colleagues minds. The second means that you cannot pop over to a colleague's desk or catch up on things informally (e.g., over lunch).

The best thing to counteract those effects is to over-communicate and to encourage your team to over-communicate. Let everyone know what you're working on, what is worrying you, what cool stuff you did, what you are thinking about doing next. Encourage others to share the outcomes of every meeting and conversation. Talk (or chat by text) with your whole team and with individuals. Say 'yes' to more meetings than you would if you were in an office (even if you don't get much out of the meeting, it's an opportunity to be seen and to pick up on things like people's work relationships and ways of interaction). Have non-work conversations with your colleagues - if you were in the office you would talk every day over lunch and coffee, and not all about work. So say 'good morning' and find out how the weather is. If you can, try to encourage your team to be open, transparent, and generous with information - the more that is shared in public (or the relative public of your team chat) rather than in private conversations, the more remote workers will feel a part of the team.

As I mentioned in the last post, having more formal and defined processes for your team should make life for remote workers easier. Prioritise making communication asynchronous, text-based, and public. Asynchronous communication (e.g., email, bug trackers) allows people to participate equally, independent of timezone or working hours. Text-based communication is easier to record and share. If communication is public (e.g., a team Slack channel vs a private Slack conversation), then fewer people will miss out on the conversation.

As should be well-known by now, communicating over the internet, even using video-conferencing but especially using text, loses a lot of the nuance of irl communication. Therefore, you should take extra care with the tone of your conversation. Be more polite than you think you might need to be. Be clear if you are joking or being sarcastic (or just don't be sarcastic). Use emoji to communicate your feelings and to clarify tone (even if you're cynical about using emoji in 'formal' work-related communication).

Email is pretty good, but unfortunately it is a bit out of fashion. It is inherently asynchronous and text-based, can be as public as appropriate, has no problems with interoperability, and clients can be customised for users' needs. However, it is a bit too easy for it to be used badly. You should try to encourage a culture where email is treated more like a Slack message than a paper letter: email can and (usually) should be short and informal.

Make sure you have a good system of folders and filters in your email client so you don't get overwhelmed. Don't feel the need to check or reply to email immediately. Use email lists with care - ensure you don't re-add people who have left, don't include too many people, don't change the subject field, and don't change the subject matter of an email chain (e.g., digressing into tangents or small talk).

Sharing documents is great (e.g., Google docs/sheets, Dropbox paper, code in playgrounds, etc). Again sharing can be as public as appropriate, and they are fairly asynchronous (edits are synchronous, but history is usually preserved and there is no time-limit on the current state). The best thing though is that you can choose a format that is optimal for the situation - you can use plain text, formatted text, diagrams, spreadsheets, graphs, code, etc.

If you like to pair program, this can work pretty well remotely. Screen sharing and a voice call is all you really need.

If you want to pair on design work I suggest you both have whiteboards and point a camera at each, rather than trying to share a document (whiteboards are just easier to scribble on). Sharing a doc to record notes is a good idea though.

My final tip is to turn off all your notifications. You can poll your apps, don't let them be in control. This lets you maintain focus and prevents you being overwhelmed with input and context switching. Often for remote workers, there is a (well-founded) desire to stay connected, but there are very few messages that need immediate action. Especially out of work hours, you should be in charge of your attention, not others.

Getting the team together a few times each year for planning, design work, and team building is pretty much essential. The benefits in improved work and motivation far outweigh the cost. It's amazing the difference a little bit of in-person time makes to later online communication.

## Different timezones and languages

Remote work in the same or similar timezones, and where the whole team speaks the same language is easy mode. Having a team spread around the world with different timezones, languages, work cultures, etc. adds an order of magnitude of difficulty.

Making communication asynchronous and text-based is even more important. Asynchronous means people in different timezones can participate. Text means you can easily use translation tools to communicate even if you don't share a language.

Translation tools are amazing. Learn how to use a few and via different interfaces. For example, Google Translate can live-translate text via the camera, can be used in Google Docs to translate documents, can be used in Chrome to translate the web, or can be used via its webpage. Different translation tools may give different translations, so you might use several on the same piece of text to get a good translation.

When others are reading your messages as a second language or in translation, you need to be extra careful with your language. Be aware of cultural context - many idioms and metaphors do not translate. Use straightforward language and avoid dialect (you may be surprised that some things that you think are standard are only standard in your local area - e.g., 'chief' is a neutral or positive term of address in most places, but an insult in England). As a rough test, you can run your message through a translation cycle (e.g., from English to Chinese and back to English) to get an idea of what a translation tool might do.

Documentation (of processes and code) also needs to be available for translation. If you export a document as an image, then it becomes much harder to translate. Some software does not allow easy translation or copying of text.

Be aware of any process that require synchronisation. For example, if your reviews are conversational, i.e., the reviewer asks a question, the author answers, then the reviewer asks another question and repeat, then if there is no timezone overlap then a review with n questions will take 2n days to complete. If the reviewer asks all their questions at once and the author answers them all at once, it should only take two days (i.e., linear time vs constant time).

Collaboration across very different timezones is difficult (if timezones are close then there is collaboration time where work hours overlap and focus time where they don't). If people in different timezones need to work on the same code, then you have to have processes to handover code asynchronously - which is possible but a pain. For short periods, it might be possible to adjust work hours so you have a longer overlap period.

The easiest way to collaborate is to work on different tasks on the same project. This is very natural for open source projects. However, this is a bit difficult to scale. Once you have more than a few people on a small-ish project (or a small-ish part of a big project) then you need a well-thought out design and good project management to make it work. Otherwise you end up wasting a lot of time rebasing.

*This post was first published [here](https://www.ncameron.org/blog/remote-work-part-2/).*
