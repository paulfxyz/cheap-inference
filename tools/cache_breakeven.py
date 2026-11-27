#!/usr/bin/env python3
"""
cache_breakeven.py - is prompt caching worth it for THIS prompt?

Prompt caching is not free on every provider. Typical shape of the pricing
(check your provider; numbers vary and change):
  * WRITING a prefix to the cache can cost MORE than a normal input token.
  * READING it back is much cheaper than a normal input token.
  * The cache expires after a time-to-live (TTL), and prefixes under a minimum
    size are not cached at all.

So caching only pays if the prefix is reused enough times inside the TTL.

BREAK-EVEN MATH (per prefix of N tokens, prices per token)
    without cache, R requests:   R * N * p_in
    with cache:                  N * p_write + (R - 1) * N * p_read
Cache wins when  p_write + (R-1)*p_read < R*p_in. Solving for R:
    R > (p_write - p_read) / (p_in - p_read)
The tool prints that minimum number of requests and warns about the minimum size.

You provide the prices as RATIOS to the normal input price (write 1.25 means
"write costs 1.25x a normal input token"), so no real price is hard-coded.

WORKED EXAMPLE
--------------
    $ python tools/cache_breakeven.py --prefix-tokens 5000 --write 1.25 --read 0.1 --reuses 4
    break-even: caching wins from 2 requests per TTL window
    at 5 requests (1 write + 4 reuses): 33% of the no-cache input cost
"""
from __future__ import annotations

import argparse
import math
import sys


def min_requests(write: float, read: float, plain: float = 1.0) -> int:
    """Smallest request count R (inside one TTL) for which caching is cheaper.

    Derived above: R > (write - read) / (plain - read). If read >= plain the
    cache can never win, so we return 0 as a sentinel for 'never'.
    """
    if read >= plain:
        return 0
    r = (write - read) / (plain - read)
    return max(2, math.floor(r) + 1)  # need at least a write plus one reuse


def cost_ratio(requests: int, write: float, read: float, plain: float = 1.0) -> float:
    """Cached cost as a fraction of the no-cache cost for `requests` requests in one TTL."""
    with_cache = write + (requests - 1) * read
    return with_cache / (requests * plain)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Break-even for prompt caching.")
    ap.add_argument("--prefix-tokens", type=int, required=True)
    ap.add_argument("--write", type=float, default=1.25, help="cache-write price as a multiple of normal input")
    ap.add_argument("--read", type=float, default=0.1, help="cache-read price as a multiple of normal input")
    ap.add_argument("--reuses", type=int, default=4, help="expected reuses inside one TTL window")
    ap.add_argument("--min-prefix", type=int, default=1024, help="provider's minimum cacheable prefix (check docs)")
    a = ap.parse_args(argv)
    if a.prefix_tokens < a.min_prefix:
        print(f"warning: {a.prefix_tokens} tokens is under the assumed minimum of {a.min_prefix}; it may not be cached at all.")
    n = min_requests(a.write, a.read)
    print("break-even: " + (f"caching wins from {n} requests per TTL window" if n else "caching never wins with these prices"))
    total = a.reuses + 1
    print(f"at {total} requests (1 write + {a.reuses} reuses): {cost_ratio(total, a.write, a.read):.0%} of the no-cache input cost")
    return 0


if __name__ == "__main__":
    sys.exit(main())
