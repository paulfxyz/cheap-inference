#!/usr/bin/env python3
"""
fewshot_prune.py - keep the fewest examples that still do the job.

Few-shot examples in a prompt are paid for on every request. Often 3 well
chosen examples work as well as 12. This tool picks a SMALL SUBSET using
evidence, not taste.

INPUT: a JSON results matrix from your own experiments. For each example you
tried including, the list of golden-set item ids that were answered correctly
WHEN THAT EXAMPLE WAS PRESENT:
    {"ex1": [1,2,3,5], "ex2": [2,3], "ex3": [1,2,3,4,5,6]}
(`ex1` helped items 1,2,3,5...). It is a GREEDY SET COVER: repeatedly add the
example that fixes the most still-uncovered items, stop when coverage stops
improving or you hit --max.

WHY GREEDY IS FINE: set cover is hard in general but greedy is a standard,
well-behaved approximation, and the matrix is small.

HONESTY: coverage here is a PROXY measured on your golden set. Re-run the final
prompt through eval_gate.py before adopting it.

WORKED EXAMPLE
--------------
    $ python tools/fewshot_prune.py matrix.json --max 3
    keep: ex3  (covers 6 of 6 items, drops 2 of 3 examples)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def greedy_cover(matrix: dict[str, list], max_examples: int = 5) -> tuple[list[str], set]:
    """Return (chosen example names in order, covered item ids)."""
    covered: set = set()
    chosen: list[str] = []
    remaining = {k: set(v) for k, v in matrix.items()}
    while remaining and len(chosen) < max_examples:
        # Pick the example adding the most NEW items; ties broken by name for determinism.
        best = max(sorted(remaining), key=lambda k: len(remaining[k] - covered))
        gain = remaining[best] - covered
        if not gain:
            break  # nothing left to gain: stop early, fewer examples = cheaper prompt
        chosen.append(best)
        covered |= gain
        del remaining[best]
    return chosen, covered


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Greedy few-shot example pruning.")
    ap.add_argument("matrix")
    ap.add_argument("--max", type=int, default=5)
    a = ap.parse_args(argv)
    m = json.loads(pathlib.Path(a.matrix).read_text())
    chosen, covered = greedy_cover(m, a.max)
    universe = set().union(*map(set, m.values())) if m else set()
    print(f"keep: {', '.join(chosen)}  (covers {len(covered)} of {len(universe)} items, drops {len(m) - len(chosen)} of {len(m)} examples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
