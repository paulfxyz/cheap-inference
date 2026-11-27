#!/usr/bin/env python3
"""
waste_finder.py - find retries, loops and repeated requests in a usage log.

Some of the most expensive tokens are the ones you pay for twice. This tool
scans a JSONL request log for three patterns, using only counting:

  W1  REPEATS   the same prompt (by hash) sent several times: a cache or a
                stored result would have answered all but the first
  W2  RETRIES   the same task failing repeatedly in a row (status != "ok")
  W3  LOOPS     one task producing a long run of near-identical calls inside a
                short window: typical of an agent stuck in a loop

LOG FORMAT (JSON lines): {"task":str,"prompt_hash":str,"status":"ok|error","input":int,"output":int,"t":seconds}
Only fields you have are used; missing ones are skipped.

WORKED EXAMPLE
--------------
    $ python tools/waste_finder.py examples/waste.sample.jsonl
    W1 repeats : 'a1' sent 3x (2 avoidable, ~4,000 tokens)
    W2 retries : task 'digest' failed 3 times in a row (~6,300 tokens spent on failures)
    W3 loops   : none
    Avoidable tokens (estimate): ~10,300
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def tok(r: dict) -> int:
    return int(r.get("input", 0)) + int(r.get("output", 0))


def find(rows: list[dict], min_repeat: int = 2, retry_run: int = 3, loop_calls: int = 8, loop_window: float = 120) -> dict:
    """Return the three findings as plain data (easy to unit test)."""
    # W1: group by prompt hash; everything after the first occurrence is avoidable.
    by_hash = collections.defaultdict(list)
    for r in rows:
        if r.get("prompt_hash"):
            by_hash[r["prompt_hash"]].append(r)
    repeats = [(h, len(rs), sum(tok(x) for x in rs[1:])) for h, rs in by_hash.items() if len(rs) >= min_repeat]

    # W2: runs of consecutive failures per task.
    retries, run, last = [], 0, None
    spent = 0
    for r in rows:
        failed = r.get("status", "ok") != "ok"
        if failed and r.get("task") == last:
            run += 1
            spent += tok(r)
        elif failed:
            run, last, spent = 1, r.get("task"), tok(r)
        else:
            if run >= retry_run:
                retries.append((last, run, spent))
            run, last, spent = 0, None, 0
    if run >= retry_run:
        retries.append((last, run, spent))

    # W3: many calls of one task inside a short time window.
    loops = []
    by_task = collections.defaultdict(list)
    for r in rows:
        if "t" in r:
            by_task[r.get("task")].append(float(r["t"]))
    for task, ts in by_task.items():
        ts.sort()
        for i in range(len(ts) - loop_calls + 1):
            if ts[i + loop_calls - 1] - ts[i] <= loop_window:  # sliding window over sorted times
                loops.append((task, loop_calls, loop_window))
                break
    avoidable = sum(x[2] for x in repeats) + sum(x[2] for x in retries)
    return {"repeats": repeats, "retries": retries, "loops": loops, "avoidable": avoidable}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find repeated, retried and looping requests.")
    ap.add_argument("log")
    a = ap.parse_args(argv)
    rows = [json.loads(ln) for ln in pathlib.Path(a.log).read_text(encoding="utf-8").splitlines() if ln.strip()]
    f = find(rows)
    for h, n, t in f["repeats"]:
        print(f"W1 repeats : '{h}' sent {n}x ({n - 1} avoidable, ~{t:,} tokens)")
    for task, n, t in f["retries"]:
        print(f"W2 retries : task '{task}' failed {n} times in a row (~{t:,} tokens spent on failures)")
    for task, n, w in f["loops"]:
        print(f"W3 loops   : task '{task}' made {n}+ calls within {w:.0f}s")
    if not f["loops"]:
        print("W3 loops   : none")
    print(f"Avoidable tokens (estimate): ~{f['avoidable']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
