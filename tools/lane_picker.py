#!/usr/bin/env python3
"""
lane_picker.py - pick the cheapest service LANE that still meets the deadline.

Many providers sell the same model in lanes with different price and speed, for
example: real-time (fast, full price), a standard lane, and an asynchronous batch
or "flex" lane that is cheaper but can take minutes to hours. The cheapest lane
that finishes before you need the result is the right one.

INPUT: a JSON lane table that YOU fill from your provider's docs (nothing is
hard-coded here because lane names, discounts and turnaround times change):

    {"lanes": [{"name": "realtime", "price_multiplier": 1.0, "max_latency_minutes": 0.1},
               {"name": "batch",    "price_multiplier": 0.5, "max_latency_minutes": 1440}]}

`max_latency_minutes` is the SLOWEST turnaround you must plan for in that lane (the
documented upper bound), not the typical one: planning on typical times is how
deadlines get missed.

DECISION: among lanes whose worst-case latency fits `--deadline-minutes`, choose the
smallest price_multiplier. If none fits, say so instead of guessing.

WORKED EXAMPLE
--------------
    $ python tools/lane_picker.py examples/lanes.example.json --deadline-minutes 600
    lane: batch (x0.5, worst case 1440 min) does NOT fit 600 min
    lane: realtime (x1.0, worst case 0.1 min) fits but is dearer 600 min
    lane: standard (x0.8)  <- cheapest lane that meets the deadline
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def pick(lanes: list[dict], deadline_minutes: float) -> dict | None:
    """Cheapest lane whose worst-case latency fits the deadline, or None."""
    fits = [l for l in lanes if l["max_latency_minutes"] <= deadline_minutes]
    return min(fits, key=lambda l: l["price_multiplier"]) if fits else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Choose the cheapest lane that meets a deadline.")
    ap.add_argument("lanes")
    ap.add_argument("--deadline-minutes", type=float, required=True)
    a = ap.parse_args(argv)
    lanes = json.loads(pathlib.Path(a.lanes).read_text())["lanes"]
    best = pick(lanes, a.deadline_minutes)
    for l in sorted(lanes, key=lambda x: x["price_multiplier"]):
        if best is None or l["name"] != best["name"]:
            ok = l["max_latency_minutes"] <= a.deadline_minutes
            print(f"lane: {l['name']} (x{l['price_multiplier']}, worst case {l['max_latency_minutes']:g} min) {'fits but is dearer' if ok else 'does NOT fit'} {a.deadline_minutes:g} min")
    if best:
        print(f"lane: {best['name']} (x{best['price_multiplier']})  <- cheapest lane that meets the deadline")
        return 0
    print("no lane meets the deadline: relax the deadline or accept the fastest lane")
    return 1


if __name__ == "__main__":
    sys.exit(main())
