#!/usr/bin/env python3
"""
wave_plan.py - warm the cache with ONE request, then fire the rest in waves.

THE PROBLEM
-----------
You have 200 requests that share a big prefix (instructions + reference text).
If all 200 start at the same instant, none can read the prefix from the cache
because nothing has WRITTEN it yet: you pay full price 200 times. Sending one
"warm-up" request first, waiting for it to finish, then sending the rest in
controlled waves lets the other 199 read the cached prefix.

WHAT THIS TOOL PRODUCES
-----------------------
A schedule: [warm-up] + waves of at most --wave-size requests, spaced --gap
seconds apart (keep gaps shorter than the provider's cache lifetime). It also
estimates input cost with and without warming, using your price ratios:

    no warming : every request pays `plain` for the prefix
    warming    : 1 request pays `write`, the rest pay `read`

All ratios are relative to the normal input price; read your provider's docs for the
real write/read multipliers, minimum prefix size and lifetime. Nothing here is a benchmark.

WORKED EXAMPLE
--------------
    $ python tools/wave_plan.py --requests 200 --prefix-tokens 6000 --wave-size 20 --write 1.25 --read 0.1
    schedule: 1 warm-up, then 10 waves of <=20 (one every 5s)
    prefix cost: 1,200,000 -> 126,900 token-equivalents (89% fewer)
"""
from __future__ import annotations

import argparse
import math
import sys


def schedule(n: int, wave_size: int) -> list[int]:
    """Request counts per step: [1 warm-up, then waves]. Always sums to n."""
    if n <= 1:
        return [n] if n else []
    rest = n - 1
    return [1] + [min(wave_size, rest - i) for i in range(0, rest, wave_size)]


def prefix_cost(n: int, prefix_tokens: int, write: float, read: float, warmed: bool) -> float:
    """Token-equivalents spent on the shared prefix."""
    if not warmed:
        return n * prefix_tokens  # nothing cached yet when everyone starts together
    return prefix_tokens * write + (n - 1) * prefix_tokens * read


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cache-warm-up wave schedule.")
    ap.add_argument("--requests", type=int, required=True)
    ap.add_argument("--prefix-tokens", type=int, required=True)
    ap.add_argument("--wave-size", type=int, default=20)
    ap.add_argument("--gap", type=int, default=5, help="seconds between waves (keep under the cache lifetime)")
    ap.add_argument("--write", type=float, default=1.25)
    ap.add_argument("--read", type=float, default=0.1)
    a = ap.parse_args(argv)
    s = schedule(a.requests, a.wave_size)
    plain = prefix_cost(a.requests, a.prefix_tokens, a.write, a.read, False)
    warm = prefix_cost(a.requests, a.prefix_tokens, a.write, a.read, True)
    print(f"schedule: 1 warm-up, then {len(s) - 1} waves of <={a.wave_size} (one every {a.gap}s)")
    print(f"prefix cost: {plain:,.0f} -> {warm:,.0f} token-equivalents ({100 - round(100 * warm / plain)}% fewer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
