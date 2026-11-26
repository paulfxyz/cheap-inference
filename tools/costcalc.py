#!/usr/bin/env python3
"""
costcalc.py - compare the cost of a workload across routes.

IMPORTANT HONESTY NOTE
----------------------
This tool ships with NO real prices. Prices change often and differ per
provider, so inventing them would make the output look authoritative when it
is not. Instead you provide a small JSON price table (see
examples/prices.example.json - its numbers are PLACEHOLDERS for illustration).
Fill it from your provider's current pricing page.

THE MODEL
---------
Cost of one call =  (fresh_input_tokens   * input_price
                   + cached_input_tokens  * cached_input_price
                   + output_tokens        * output_price) / 1,000,000

A workload is  N calls x (input + output tokens) and a "cache hit rate": the
share of the input that is a repeated prefix a provider can serve at the
cached price (if it supports prompt caching). A route may also be flagged
"batch": true to apply a batch discount factor you define in the table.

USAGE
-----
    python tools/costcalc.py examples/prices.example.json \
        --calls 2000 --input 3000 --output 400 --cache-hit 0.6

WORKED EXAMPLE (placeholder prices from examples/prices.example.json)
-----------------------------------------------------------------------
    $ python tools/costcalc.py examples/prices.example.json --calls 2000 --input 3000 --output 400 --cache-hit 0.6
    route                       per call         total  x cheapest   (USD)
    small-model                  0.00065          1.30         1.0
    mid-model-batch              0.00162          3.25         2.5
    mid-model                    0.00325          6.50         5.0
    premium-model                0.01625         32.50        25.0

How to read it: the last column is how many times more the workload costs than
on the cheapest route. The numbers are made up; the SHAPE (a 25x spread between
routes) is why routing matters. Re-run with your own prices.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def call_cost(route: dict, input_tokens: int, output_tokens: int, cache_hit: float) -> float:
    """Cost in currency units of ONE call on ONE route.

    cache_hit is clamped to [0, 1]. If the route has no cached price we fall
    back to the normal input price, i.e. caching gives no benefit there.
    """
    cache_hit = max(0.0, min(1.0, cache_hit))
    in_price = route["input_per_million"]
    cached_price = route.get("cached_input_per_million", in_price)
    out_price = route["output_per_million"]

    # Split the input into the part served from cache and the part billed fresh.
    cached_tokens = input_tokens * cache_hit
    fresh_tokens = input_tokens - cached_tokens
    cost = (fresh_tokens * in_price + cached_tokens * cached_price + output_tokens * out_price) / 1_000_000
    # Optional multiplier, e.g. 0.5 for an asynchronous batch endpoint.
    return cost * route.get("multiplier", 1.0)


def compare(table: dict, calls: int, input_tokens: int, output_tokens: int, cache_hit: float) -> list[dict]:
    """Return routes sorted from cheapest to most expensive for this workload."""
    rows = []
    for name, route in table["routes"].items():
        per_call = call_cost(route, input_tokens, output_tokens, cache_hit)
        rows.append({"route": name, "per_call": per_call, "total": per_call * calls})
    # Cheapest first: the first row is the baseline every other route is compared to.
    rows.sort(key=lambda r: r["total"])
    if rows:
        cheapest = rows[0]["total"] or 1e-12  # avoid division by zero
        for r in rows:
            r["x_cheapest"] = r["total"] / cheapest
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare workload cost across routes.")
    ap.add_argument("prices", help="JSON price table")
    ap.add_argument("--calls", type=int, required=True)
    ap.add_argument("--input", type=int, required=True, help="input tokens per call")
    ap.add_argument("--output", type=int, required=True, help="output tokens per call")
    ap.add_argument("--cache-hit", type=float, default=0.0, help="share of input served from cache, 0..1")
    args = ap.parse_args(argv)

    # The price table is user-supplied JSON (see examples/prices.example.json); nothing is hard-coded.
    table = json.loads(pathlib.Path(args.prices).read_text(encoding="utf-8"))
    cur = table.get("currency", "USD")
    rows = compare(table, args.calls, args.input, args.output, args.cache_hit)
    print(f"{'route':<24}{'per call':>12}{'total':>14}{'x cheapest':>12}   ({cur})")
    for r in rows:
        print(f"{r['route']:<24}{r['per_call']:>12.5f}{r['total']:>14.2f}{r['x_cheapest']:>12.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
