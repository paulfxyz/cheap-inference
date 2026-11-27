#!/usr/bin/env python3
"""
edit_guard.py - apply SEARCH/REPLACE edits safely, so a model returns a patch, not a file.

WHY
---
Asking a model to reprint a whole file to change three lines costs output
tokens for every unchanged line (output is the priciest token) and risks silent
changes elsewhere. Asking for SEARCH/REPLACE blocks instead means the model
writes only what changes. This script APPLIES those blocks and refuses
anything ambiguous, so a sloppy patch can never corrupt the file.

BLOCK FORMAT (what you ask the model to return)
    <<<<<<< SEARCH
    old text, copied exactly
    =======
    new text
    >>>>>>> REPLACE

SAFETY RULES (each one is a check, none needs a model)
  E1  the SEARCH text must appear EXACTLY ONCE (0 = nothing to replace, 2+ = ambiguous)
  E2  blocks are applied in order, each on the result of the previous one
  E3  nothing is written unless EVERY block succeeds (all-or-nothing)
  E4  --dry-run shows what would change without touching the file

WORKED EXAMPLE
--------------
    $ python tools/edit_guard.py settings.py patch.txt --dry-run
    block 1: ok (1 match, -1/+1 lines)
    all 1 block(s) would apply
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

BLOCK = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.S)


def parse_blocks(patch: str) -> list[tuple[str, str]]:
    """Extract (search, replace) pairs from the model's patch text."""
    return BLOCK.findall(patch)


def apply_blocks(text: str, blocks: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Apply all blocks or raise ValueError. Returns (new_text, per-block report)."""
    report = []
    for i, (old, new) in enumerate(blocks, 1):
        n = text.count(old)
        if n == 0:
            raise ValueError(f"block {i}: SEARCH text not found (the model may have mis-copied it)")
        if n > 1:
            raise ValueError(f"block {i}: SEARCH text matches {n} places; ask for more surrounding context")
        text = text.replace(old, new, 1)
        report.append(f"block {i}: ok (1 match, -{old.count(chr(10)) + 1}/+{new.count(chr(10)) + 1} lines)")
    return text, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Apply SEARCH/REPLACE blocks all-or-nothing.")
    ap.add_argument("file")
    ap.add_argument("patch")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    path = pathlib.Path(a.file)
    blocks = parse_blocks(pathlib.Path(a.patch).read_text(encoding="utf-8"))
    if not blocks:
        print("no SEARCH/REPLACE blocks found")
        return 1
    try:
        new_text, report = apply_blocks(path.read_text(encoding="utf-8"), blocks)
    except ValueError as e:
        print(f"refused: {e}")
        return 2  # nothing was written (rule E3)
    print("\n".join(report))
    if a.dry_run:
        print(f"all {len(blocks)} block(s) would apply")
    else:
        path.write_text(new_text, encoding="utf-8")
        print(f"applied {len(blocks)} block(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
