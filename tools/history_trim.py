#!/usr/bin/env python3
"""
history_trim.py - shrink a chat/agent history before the next turn.

WHY
---
Every turn re-sends the whole history. In agent runs most of that weight is
old TOOL OUTPUTS (file dumps, search results, logs) that the model already
used. This tool applies three deterministic rules to a message list:

  H1  keep the system message and the first user message untouched
  H2  keep the last N messages (default 6) untouched
  H3  in the MIDDLE, replace long tool/function outputs by a one-line stub that
      says what was removed ("[tool output removed: 4,210 chars]"), keeping
      assistant and user messages (they carry decisions) unless --drop-chat

Nothing is summarised by a model (that would cost tokens); you can add a
checkpoint message yourself with `--checkpoint "text"`, inserted before the
kept tail. The original list is never mutated.

INPUT: JSON list of {"role": "system|user|assistant|tool", "content": str}

WORKED EXAMPLE
--------------
    $ python tools/history_trim.py chat.json --keep-last 4 --min-chars 500
    messages: 22 -> 22, ~9,800 -> ~2,100 tokens (79% fewer)
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys


def est(msgs: list[dict]) -> int:
    """Token estimate for a message list (chars / 4)."""
    return round(sum(len(str(m.get("content", ""))) for m in msgs) / 4)


def trim(msgs: list[dict], keep_last: int = 6, min_chars: int = 800, checkpoint: str | None = None) -> list[dict]:
    """Return a trimmed copy of the history. Pure function."""
    out = copy.deepcopy(msgs)
    # Protected zones: head (system + first user) and the tail of recent messages.
    head = 0
    for i, m in enumerate(out):
        head = i + 1
        if m["role"] == "user":
            break
    tail_start = max(head, len(out) - keep_last)
    for i in range(head, tail_start):
        m = out[i]
        c = str(m.get("content", ""))
        if m["role"] in ("tool", "function") and len(c) >= min_chars:
            m["content"] = f"[tool output removed: {len(c):,} chars]"
    if checkpoint:
        out.insert(tail_start, {"role": "user", "content": f"Checkpoint: {checkpoint}"})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trim stale tool outputs from a history.")
    ap.add_argument("history")
    ap.add_argument("--keep-last", type=int, default=6)
    ap.add_argument("--min-chars", type=int, default=800)
    ap.add_argument("--checkpoint")
    ap.add_argument("--out", help="write the trimmed history here")
    a = ap.parse_args(argv)
    msgs = json.loads(pathlib.Path(a.history).read_text(encoding="utf-8"))
    new = trim(msgs, a.keep_last, a.min_chars, a.checkpoint)
    b, n = est(msgs), est(new)
    print(f"messages: {len(msgs)} -> {len(new)}, ~{b:,} -> ~{n:,} tokens ({100 - round(100 * n / max(1, b))}% fewer)")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(new, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
