#!/usr/bin/env python3
"""
token_calibrate.py - replace the chars/4 guess with ratios measured on YOUR data.

chars / 4 is a decent rule for English prose and a poor one for code, JSON,
logs and many non-Latin scripts, where one token covers far fewer characters.
Budgets built on a bad ratio silently let too much through.

HOW TO CALIBRATE
----------------
Your provider reports the real input token count for each request. Log, for a
sample of requests, the text KIND, the character count and the reported tokens:

    {"kind": "code", "chars": 4200, "tokens": 1500}

This tool computes chars-per-token per kind (total chars / total tokens, which
weights big samples properly) and writes a small JSON table. `tokens.py` can
then use it via --calibration, so every estimate reflects your own content.

If you have no log yet, it prints sensible STARTING ratios by kind and says so.
They are rules of thumb, not measurements; replace them as soon as you can.

WORKED EXAMPLE
--------------
    $ python tools/token_calibrate.py examples/calibration.sample.jsonl
    kind     samples   chars/token   (default guess)
    code           2          2.78   3.0
    prose          2          4.10   4.0
    wrote calibration.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

# Starting guesses only. Real values depend on the tokenizer: measure, do not trust these.
DEFAULTS = {"prose": 4.0, "code": 3.0, "json": 2.8, "logs": 3.0, "cjk": 1.5}


def calibrate(rows: list[dict]) -> dict:
    """Return {kind: {samples, chars_per_token}} from logged (chars, tokens) pairs."""
    chars = collections.Counter()
    toks = collections.Counter()
    n = collections.Counter()
    for r in rows:
        if r.get("tokens", 0) > 0:
            k = r.get("kind", "prose")
            chars[k] += r["chars"]
            toks[k] += r["tokens"]
            n[k] += 1
    return {k: {"samples": n[k], "chars_per_token": round(chars[k] / toks[k], 2)} for k in n}


def detect_kind(text: str) -> str:
    """Cheap content classifier used by tokens.py when no kind is given."""
    if not text:
        return "prose"
    cjk = sum(1 for c in text if "\u3040" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7a3")
    if cjk / len(text) > 0.2:
        return "cjk"
    stripped = text.lstrip()
    if stripped[:1] in "{[" and text.count('"') > len(text) / 20:
        return "json"
    symbols = sum(1 for c in text if c in "{}[]();=<>_/\\")
    if symbols / len(text) > 0.06:
        return "code"
    return "prose"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure chars-per-token by content kind.")
    ap.add_argument("log", nargs="?", help="JSONL of {kind, chars, tokens}")
    ap.add_argument("--out", default="calibration.json")
    a = ap.parse_args(argv)
    if not a.log:
        print("no log given: starting ratios (rules of thumb, NOT measured):")
        for k, v in DEFAULTS.items():
            print(f"  {k:<6} {v}")
        return 0
    rows = [json.loads(ln) for ln in pathlib.Path(a.log).read_text().splitlines() if ln.strip()]
    table = calibrate(rows)
    print(f"{'kind':<8}{'samples':>8}{'chars/token':>14}   (default guess)")
    for k, v in sorted(table.items()):
        print(f"{k:<8}{v['samples']:>8}{v['chars_per_token']:>14.2f}   {DEFAULTS.get(k, '-')}")
    pathlib.Path(a.out).write_text(json.dumps({k: v["chars_per_token"] for k, v in table.items()}, indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
