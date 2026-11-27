#!/usr/bin/env python3
"""
batch_pack.py - pack many small items into micro-batches, with a retry plan.

WHY PACK
--------
Sending 400 tiny requests repeats the same instructions 400 times. Packing 20
items per request pays the instructions once per 20 items. But bigger batches
have costs too: quality can drop when a prompt holds many items, and ONE bad
item forces a retry of the whole batch. So the right size is a trade-off, and
partial retry (re-send only the items that failed) is what keeps it cheap.

THE TOOL
--------
  plan    split N items into batches of at most --size items AND at most
          --max-tokens input tokens (whichever bound is hit first)
  gain    print the instruction tokens saved versus one-item-per-request
  retry   given the ids that failed, build ONLY the follow-up batches

Items are sorted by length first so batches have similar sizes (less padding of
effort, steadier quality).

WORKED EXAMPLE
--------------
    $ python tools/batch_pack.py items.txt --size 20 --instructions 300
    400 items -> 20 batches (size<=20)
    instruction tokens: 120,000 -> 6,000 (95% fewer)
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def est(s: str) -> int:
    return round(len(s) / 4)


def plan(items: list[str], size: int = 20, max_tokens: int = 4000) -> list[list[int]]:
    """Return batches as lists of ORIGINAL indices, so results can be mapped back."""
    order = sorted(range(len(items)), key=lambda i: len(items[i]))  # similar lengths together
    batches, cur, used = [], [], 0
    for i in order:
        t = est(items[i])
        # Close the batch when either bound would be exceeded (but never leave a batch empty).
        if cur and (len(cur) >= size or used + t > max_tokens):
            batches.append(cur)
            cur, used = [], 0
        cur.append(i)
        used += t
    if cur:
        batches.append(cur)
    return batches


def gain(n_items: int, n_batches: int, instruction_tokens: int) -> tuple[int, int]:
    """(instruction tokens without packing, with packing)."""
    return n_items * instruction_tokens, n_batches * instruction_tokens


def retry_plan(failed: list[int], items: list[str], size: int = 20, max_tokens: int = 4000) -> list[list[int]]:
    """Batches for ONLY the failed ids (partial retry). Indices stay original."""
    sub = [items[i] for i in failed]
    return [[failed[j] for j in b] for b in plan(sub, size, max_tokens)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pack items into micro-batches.")
    ap.add_argument("items", help="text file, one item per line")
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--instructions", type=int, default=300, help="tokens of instructions repeated per request")
    a = ap.parse_args(argv)
    items = [ln for ln in pathlib.Path(a.items).read_text(encoding="utf-8").splitlines() if ln.strip()]
    b = plan(items, a.size, a.max_tokens)
    before, after = gain(len(items), len(b), a.instructions)
    print(f"{len(items)} items -> {len(b)} batches (size<={a.size})")
    print(f"instruction tokens: {before:,} -> {after:,} ({100 - round(100 * after / max(1, before))}% fewer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
