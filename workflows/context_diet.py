#!/usr/bin/env python3
"""
context_diet.py - audit EVERYTHING sent on every request: guide, tools and prompts.

CHAINS: tokens -> schema_diet -> prompt_lint -> budget

Always-sent payload = guide + memory summary + tool schemas + fixed instructions. Tool schemas
are the part people forget, and they are often the biggest. This workflow measures each part,
flags unused tools and wasteful phrasing, and computes the monthly bill including requests per
session.

USAGE
    python workflows/context_diet.py --guide AGENTS.md --tools tools.json --tool-calls calls.jsonl \
        --sessions 300 --requests 12
"""
import argparse
import collections
import json
import pathlib

from _common import capture
import prompt_lint, schema_diet, tokens


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Always-sent payload audit.")
    ap.add_argument("--guide", nargs="*", default=[], help="always-loaded text files")
    ap.add_argument("--tools", help="JSON list of tool definitions")
    ap.add_argument("--tool-calls", help="JSONL of {'tool': name} calls")
    ap.add_argument("--sessions", type=int, default=300)
    ap.add_argument("--requests", type=int, default=1, help="requests per session")
    a = ap.parse_args(argv)

    guide_tokens = sum(tokens.estimate_tokens(pathlib.Path(f).read_text(encoding="utf-8"))["tokens_by_kind"] for f in a.guide)
    schema_tokens = saved = 0
    if a.tools:
        calls = None
        if a.tool_calls:
            calls = collections.Counter(json.loads(ln)["tool"] for ln in pathlib.Path(a.tool_calls).read_text().splitlines() if ln.strip())
        rep = schema_diet.analyse(json.loads(pathlib.Path(a.tools).read_text()), calls)
        schema_tokens, saved = rep["total"], rep["saved"]
        print(capture(schema_diet.main, a.tools, *(["--calls", a.tool_calls] if a.tool_calls else [])))
    if a.guide:
        print(capture(prompt_lint.main, *a.guide))
    per_request = guide_tokens + schema_tokens
    monthly = per_request * a.sessions * a.requests
    print(f"\nalways-sent per request: ~{per_request:,} tokens (guide {guide_tokens:,} + tool schemas {schema_tokens:,})")
    print(f"monthly loading bill: ~{monthly:,} tokens over {a.sessions} sessions x {a.requests} requests")
    if saved:
        print(f"dropping unused tools would save ~{saved * a.sessions * a.requests:,} tokens/month")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
