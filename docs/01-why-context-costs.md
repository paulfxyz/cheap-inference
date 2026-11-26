# 1. Why context is the bill

> Goal of this chapter: build an accurate mental model of where tokens go, so every later technique has an obvious reason to exist.

## 1.1 The three kinds of tokens you pay for

Every call to a language model is billed on tokens, and they come in three kinds:

| Kind | What it is | Typical price behaviour |
| --- | --- | --- |
| Fresh input | Everything you send that the provider has not seen in the same position recently | Full input price |
| Cached input | A repeated prefix that the provider can reuse (if it supports prompt caching) | Usually a fraction of the input price |
| Output | What the model writes back | Usually the most expensive per token |

Prices differ per provider and change often, so this repository never hard-codes them. The `costcalc.py` tool takes a price table you fill in yourself.

## 1.2 The multiplication problem

Most waste is not in the question you typed. It is in everything that rides along with it, again and again:

```
cost of a session  =  static context  x  number of requests
                    + tool and file reads
                    + conversation history re-sent each turn
                    + output
```

Two consequences follow:

1. A small, always-loaded file is expensive in aggregate. A 2,000-token guide loaded in 500 sessions is 1,000,000 tokens of pure overhead. See `tools/budget.py`.
2. Conversation history grows. In a long agent session, each new turn re-sends the earlier turns. Cost per turn rises even if each question is short. Starting fresh sessions for unrelated work is a real saving, not a nicety.

## 1.3 Where the hidden cost usually is

Ranked by how often it is the real cause:

1. **Reading things that were not needed.** An agent that opens a knowledge base for a question about a regular expression has spent tokens for nothing.
2. **Eager includes.** Importing a large index file into a guide loads it at the start of every session, whether or not it is used. Linking to it costs almost nothing until opened.
3. **Re-doing finished work.** Re-ingesting 500 unchanged files because nothing recorded that they were done.
4. **Asking a model to check a model.** Review passes over thousands of pages that a 100-line script could do in milliseconds.
5. **Over-powered models for easy jobs.** Using the most capable model to rename files or reformat text.
6. **Flooding the main context.** Reading 40 documents in the main thread when 40 workers could each return a three-line summary.

Each of these maps to a chapter:

| Waste | Fix | Chapter |
| --- | --- | --- |
| Unneeded reads | Tiered loading, "when not to read" lines | [2](02-tiered-loading.md) |
| Eager includes, bloated guides | Budgets | [2](02-tiered-loading.md), [10](10-checklist.md) |
| Re-doing work | Manifests and hashes | [5](05-incremental-ingest.md) |
| Model checking model | Deterministic checks | [4](04-deterministic-checks.md) |
| Over-powered models | Cheap-first ladder | [6](06-routing-ladder.md) |
| Flooded context | Cheap fan-out | [7](07-fan-out.md) |
| Re-sending stable text | Prompt order for caching, batching | [8](08-caching-and-batching.md) |

## 1.4 Measure first

Before changing anything, get two numbers:

```bash
# 1. How big is what I always load?
python tools/tokens.py templates/AGENTS.md templates/hot.md

# 2. What does that cost me per month in loading alone?
python tools/budget.py examples/budget.json
```

If the second number is small compared with your real work, stop optimising loading and look at routing and fan-out instead. Measure, then spend effort where the money is.

## 1.5 A note on honesty

Token counts in this repository are estimates (characters divided by four, or words times 1.33). Real tokenizers differ, and code, JSON and non-Latin scripts usually take more tokens per character than English prose. Treat the numbers as good for ranking and for setting limits, and use your provider's own counter when you need an exact figure.
