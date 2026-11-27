#!/usr/bin/env python3
"""
ladder_log.py - learn which rung really worked, and make it the new floor.

Writes one line per finished task to a JSONL file (task kind, rung used, whether
the result was accepted) and answers: "for this kind of task, what is the
lowest rung that has been accepted most of the time?" That is the data behind
the rule "once a rung has worked for a recurring workflow, treat it as the floor".

  python tools/ladder_log.py add  --kind weekly-digest --rung 2 --accepted yes
  python tools/ladder_log.py floor --kind weekly-digest

WORKED EXAMPLE
--------------
    $ python tools/ladder_log.py add --kind weekly-digest --rung 1 --accepted no     # x3
    $ python tools/ladder_log.py add --kind weekly-digest --rung 2 --accepted yes    # x3
    $ python tools/ladder_log.py floor --kind weekly-digest
    {"kind": "weekly-digest", "floor": 2, "evidence": "3/3 accepted"}

Meaning: rung 1 failed three times, rung 2 worked three times, so rung 2 is the
new floor for this kind of task. Do not start lower unless the task changes.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

DEFAULT_LOG = pathlib.Path(".cache/ladder.jsonl")


def add(log: pathlib.Path, kind: str, rung: int, accepted: bool) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": kind, "rung": rung, "accepted": accepted}) + "\n")


def floor(rows: list[dict], kind: str, min_samples: int = 3, min_rate: float = 0.8) -> dict:
    """Lowest rung with at least `min_samples` runs and `min_rate` acceptance.

    Falls back to the highest rung tried when no rung qualifies yet, and says so.
    """
    # rung -> [accepted_count, total_count]; defaultdict creates the pair on first use.
    stats = collections.defaultdict(lambda: [0, 0])  # rung -> [accepted, total]
    for r in rows:
        if r["kind"] == kind:
            stats[r["rung"]][1] += 1
            stats[r["rung"]][0] += 1 if r["accepted"] else 0
    # Walk from the cheapest rung upwards; the first one with enough good evidence wins.
    for rung in sorted(stats):
        ok, n = stats[rung]
        if n >= min_samples and ok / n >= min_rate:
            return {"kind": kind, "floor": rung, "evidence": f"{ok}/{n} accepted"}
    if stats:
        return {"kind": kind, "floor": max(stats), "evidence": "no rung has enough accepted runs yet"}
    return {"kind": kind, "floor": 0, "evidence": "no data; start at rung 0"}


def should_probe(rows: list[dict], kind: str, every: int = 10) -> bool:
    """True when it is time to RE-TEST one rung lower for this kind of task.

    A floor learned from a few lucky successes can lock a task onto a rung that is too low or too high.
    Re-probing periodically (every N runs of the kind) keeps the floor honest as models and tasks change.
    """
    n = sum(1 for r in rows if r["kind"] == kind)
    return n > 0 and n % every == 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--kind", required=True); s.add_argument("--rung", type=int, required=True); s.add_argument("--accepted", choices=["yes", "no"], required=True)
    f = sub.add_parser("floor"); f.add_argument("--kind", required=True)
    a = ap.parse_args(argv)
    log = pathlib.Path(a.log)
    if a.cmd == "add":
        add(log, a.kind, a.rung, a.accepted == "yes")
        return 0
    rows = [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()] if log.exists() else []
    print(json.dumps(floor(rows, a.kind)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
