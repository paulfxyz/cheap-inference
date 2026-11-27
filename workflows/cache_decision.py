#!/usr/bin/env python3
"""
cache_decision.py - decide, for one prompt, whether caching and warming are worth it.

CHAINS: tokens -> cache_breakeven -> wave_plan

Given a prompt's shared prefix (a file) and how many requests will reuse it, it answers:
  1. Is the prefix big enough to be cached at all (provider minimum)?
  2. Do enough requests reuse it inside the cache lifetime to beat the write premium?
  3. If many start together, what warm-up + wave schedule lets them all read the cache?

All prices are RATIOS you pass in (write/read relative to normal input). Nothing is assumed
about any provider; read their documentation for the real numbers.

USAGE
    python workflows/cache_decision.py --prefix prompt-prefix.md --requests 200 --write 1.25 --read 0.1 --min-prefix 1024
"""
import argparse
import pathlib

from _common import capture
import cache_breakeven, tokens, wave_plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Caching decision for one shared prefix.")
    ap.add_argument("--prefix", required=True, help="file containing the shared prefix text")
    ap.add_argument("--requests", type=int, required=True, help="requests that will reuse it inside one cache lifetime")
    ap.add_argument("--write", type=float, default=1.25)
    ap.add_argument("--read", type=float, default=0.1)
    ap.add_argument("--min-prefix", type=int, default=1024)
    ap.add_argument("--wave-size", type=int, default=20)
    a = ap.parse_args(argv)

    n = tokens.estimate_tokens(pathlib.Path(a.prefix).read_text(encoding="utf-8"))["tokens_by_kind"]
    print(f"prefix: ~{n} tokens")
    if n < a.min_prefix:
        print(f"verdict: SKIP caching. Under the assumed {a.min_prefix}-token minimum the prefix is probably not cached at all.")
        return 1
    need = cache_breakeven.min_requests(a.write, a.read)
    if not need or a.requests < need:
        print(f"verdict: SKIP caching. It needs at least {need or 'infinitely many'} reuses per lifetime; you expect {a.requests}.")
        return 1
    ratio = cache_breakeven.cost_ratio(a.requests, a.write, a.read)
    print(f"verdict: USE caching. At {a.requests} requests the prefix costs {ratio:.0%} of the uncached price.")
    if a.requests > a.wave_size:
        print("start-up: do NOT launch all requests together; warm the cache first.")
        print(capture(wave_plan.main, "--requests", str(a.requests), "--prefix-tokens", str(n), "--wave-size", str(a.wave_size), "--write", str(a.write), "--read", str(a.read)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
