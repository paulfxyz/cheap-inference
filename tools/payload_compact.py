#!/usr/bin/env python3
"""
payload_compact.py - send tabular data in fewer tokens than JSON.

JSON repeats every key on every row: [{"name":"A","qty":1},{"name":"B","qty":2}]
pays for "name" and "qty" again and again, plus quotes and braces. For lists of
similarly shaped records a header line plus delimited rows carries the same
information in fewer tokens.

WHEN IT HELPS / HURTS
---------------------
Helps: many rows, few columns, simple values. Hurts: nested or ragged data,
values containing the delimiter, or tasks where the model must reproduce
exact JSON back. It is a trade-off, not a rule, so this tool PRINTS the saving
and you decide. Always test the answer quality on a few rows (eval_gate.py).

FORMAT: first line = column names; then one line per row; a tab separates
fields; tabs/newlines inside values are replaced by spaces.

WORKED EXAMPLE
--------------
    $ python tools/payload_compact.py rows.json
    json: ~212 tokens, tsv: ~74 tokens (65% fewer)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def to_tsv(rows: list[dict]) -> str:
    """Convert a list of flat dicts to header + tab-separated rows. Missing keys become empty."""
    cols: list[str] = []
    for r in rows:  # preserve first-seen column order across ragged rows
        for k in r:
            if k not in cols:
                cols.append(k)
    clean = lambda v: str(v if v is not None else "").replace("\t", " ").replace("\n", " ")
    lines = ["\t".join(cols)] + ["\t".join(clean(r.get(c, "")) for c in cols) for r in rows]
    return "\n".join(lines)


def from_tsv(text: str) -> list[dict]:
    """Inverse of to_tsv (values come back as strings)."""
    lines = text.split("\n")
    cols = lines[0].split("\t")
    return [dict(zip(cols, ln.split("\t"))) for ln in lines[1:]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare JSON vs TSV token cost for a list of records.")
    ap.add_argument("json_file")
    a = ap.parse_args(argv)
    rows = json.loads(pathlib.Path(a.json_file).read_text(encoding="utf-8"))
    j = len(json.dumps(rows, separators=(",", ":"))) // 4
    t = len(to_tsv(rows)) // 4
    print(f"json: ~{j} tokens, tsv: ~{t} tokens ({100 - round(100 * t / max(1, j))}% fewer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
