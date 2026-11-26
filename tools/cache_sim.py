#!/usr/bin/env python3
"""
cache_sim.py - why prompt ORDER decides your cache hit rate.

Providers that support prompt caching can reuse the work done on an identical
PREFIX of the previous request. The cache matches from the first token
onward and stops at the first difference. So:

  GOOD:  [stable rules][stable tools][stable docs] | [changing question]
  BAD:   [timestamp][stable rules][stable tools]   | [changing question]
         ^ one changing token at the start invalidates everything after it.

This script simulates a sequence of prompts (each a list of "segments") and
reports the share of tokens that sit in a prefix identical to the previous
request, i.e. the best-case cacheable share. It is a teaching aid: real
providers add minimum sizes, time-to-live limits and block granularity, which
you should read in their documentation.

WORKED EXAMPLE
--------------
    $ python tools/cache_sim.py
    stable-first order : 97% of tokens cacheable
    timestamp-first    : 0% of tokens cacheable

Why 97%: each prompt is rules(800) + tools(1200) + docs(3000) + question(150).
The first 5,000 tokens repeat exactly, so 5000/5150 = 97%. A timestamp in front
changes the very first segment, so nothing after it can be reused.
"""
from __future__ import annotations

import sys


def common_prefix_tokens(prev: list[tuple[str, int]], cur: list[tuple[str, int]]) -> int:
    """Tokens in the longest identical leading run of (text, tokens) segments."""
    total = 0
    # zip pairs segment i of the previous prompt with segment i of the current one.
    for (pt, _), (ct, cn) in zip(prev, cur):
        if pt != ct:
            break  # first difference: the cache stops matching here
        total += cn
    return total


def cacheable_share(prompts: list[list[tuple[str, int]]]) -> float:
    """Average cacheable share across consecutive prompts (the first has no predecessor)."""
    if len(prompts) < 2:
        return 0.0
    shares = []
    for prev, cur in zip(prompts, prompts[1:]):
        size = sum(n for _, n in cur) or 1
        shares.append(common_prefix_tokens(prev, cur) / size)
    return sum(shares) / len(shares)


def demo() -> None:
    rules, tools, docs = ("rules", 800), ("tools", 1200), ("docs", 3000)
    good = [[rules, tools, docs, (f"question {i}", 150)] for i in range(10)]
    bad = [[(f"timestamp {i}", 10), rules, tools, docs, (f"question {i}", 150)] for i in range(10)]
    print(f"stable-first order : {cacheable_share(good):.0%} of tokens cacheable")
    print(f"timestamp-first    : {cacheable_share(bad):.0%} of tokens cacheable")


if __name__ == "__main__":
    demo()
    sys.exit(0)
