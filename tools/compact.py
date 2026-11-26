#!/usr/bin/env python3
"""
compact.py - shrink long tool outputs and logs BEFORE they enter a context.

Conversation history is re-sent every turn, so a 20,000-line log pasted once
is paid for again and again. The cheapest fix is to never let it in whole.
This helper applies deterministic, lossless-where-possible reductions:

  1. strip ANSI colour codes and trailing whitespace
  2. collapse runs of identical lines into "line  (xN)"
  3. drop blank-line runs
  4. optionally keep only lines matching --grep (plus --context lines around)
  5. keep the HEAD and TAIL of what is left, with an explicit omission marker,
     because errors cluster at the end and headers at the start

It always says how much it removed, so nothing is dropped silently.

USAGE
-----
    some-command 2>&1 | python tools/compact.py --head 40 --tail 60
    python tools/compact.py build.log --grep "error|warn" --context 2
"""
from __future__ import annotations

import argparse
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def collapse_repeats(lines: list[str]) -> list[str]:
    """Replace consecutive identical lines by one line with a repeat count."""
    out: list[str] = []
    prev, n = None, 0
    for ln in lines + [None]:  # sentinel flushes the last run
        if ln == prev:
            n += 1
            continue
        if prev is not None:
            out.append(prev if n == 1 else f"{prev}  (x{n})")
        prev, n = ln, 1
    return out


def grep_with_context(lines: list[str], pattern: str, context: int) -> list[str]:
    """Keep matching lines and `context` lines around them, marking gaps."""
    rx = re.compile(pattern, re.I)
    keep = set()
    for i, ln in enumerate(lines):
        if rx.search(ln):
            keep.update(range(max(0, i - context), min(len(lines), i + context + 1)))
    out, last = [], -1
    for i in sorted(keep):
        if last >= 0 and i != last + 1:
            out.append("...")
        out.append(lines[i])
        last = i
    return out


def compact(text: str, head: int = 40, tail: int = 60, grep: str | None = None, context: int = 1) -> tuple[str, dict]:
    """Return (compacted_text, stats). Pure function, easy to test."""
    raw_lines = [ANSI.sub("", ln).rstrip() for ln in text.splitlines()]
    before = len(raw_lines)
    lines = collapse_repeats(raw_lines)
    # drop runs of blank lines down to one
    lines = [ln for i, ln in enumerate(lines) if ln or (i and lines[i - 1])]
    if grep:
        lines = grep_with_context(lines, grep, context)
    if len(lines) > head + tail:
        omitted = len(lines) - head - tail
        lines = lines[:head] + [f"... [{omitted} lines omitted] ..."] + lines[-tail:]
    result = "\n".join(lines)
    stats = {"lines_before": before, "lines_after": len(lines), "chars_before": len(text), "chars_after": len(result)}
    return result, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compact long output before it enters a context.")
    ap.add_argument("file", nargs="?", help="file to read (default: stdin)")
    ap.add_argument("--head", type=int, default=40)
    ap.add_argument("--tail", type=int, default=60)
    ap.add_argument("--grep", help="regex of lines to keep")
    ap.add_argument("--context", type=int, default=1)
    a = ap.parse_args(argv)
    text = open(a.file, encoding="utf-8", errors="ignore").read() if a.file else sys.stdin.read()
    out, st = compact(text, a.head, a.tail, a.grep, a.context)
    print(out)
    saved = 100 - round(100 * st["chars_after"] / max(1, st["chars_before"]))
    print(f"[compact] {st['lines_before']} -> {st['lines_after']} lines, ~{saved}% fewer characters", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
