#!/usr/bin/env python3
"""
bulk_job_planner.py - plan a big model job so you only pay for what a model must do.

CHAINS: prefilter -> batch_pack -> costcalc

STEPS
    1. prefilter  : drop rows a rule can answer and collapse exact duplicates
    2. batch_pack : pack the remaining unique rows into micro-batches (instructions paid once per batch)
    3. costcalc   : price the plan on each route in YOUR price table, including a batch route

The planner does NOT call a model. It writes plan.json (what to send, in which batches, which rows
are ruled or duplicates) and a short Markdown summary. Your job runner executes the plan, then
`prefilter.expand` rebuilds one answer per original row.

USAGE
    python workflows/bulk_job_planner.py rows.txt --prices prices.json --rules rules.json \
        --instructions 300 --output-per-item 40
"""
import argparse
import json
import pathlib

from _common import capture, section
import batch_pack, costcalc, prefilter


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan a bulk model job.")
    ap.add_argument("rows")
    ap.add_argument("--prices", required=True)
    ap.add_argument("--rules")
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--instructions", type=int, default=300)
    ap.add_argument("--output-per-item", type=int, default=40)
    ap.add_argument("--out", default="bulk-plan.md")
    a = ap.parse_args(argv)

    rows = pathlib.Path(a.rows).read_text(encoding="utf-8").splitlines()
    rules = json.loads(pathlib.Path(a.rules).read_text()) if a.rules else []
    plan = prefilter.split(rows, rules)
    unique = [rows[i] for i in plan["to_send"]]
    batches = batch_pack.plan(unique, a.size)
    item_tokens = sum(round(len(x) / 4) for x in unique)
    n_calls = len(batches)
    in_per_call = a.instructions + item_tokens // max(1, n_calls)
    out_per_call = a.output_per_item * (len(unique) // max(1, n_calls) or 1)

    summary = (f"rows {len(rows)} -> ruled {len(plan['ruled'])}, duplicates {len(plan['rep_of'])}, "
               f"unique to send {len(unique)} -> {n_calls} batched call(s) instead of {len(rows)}")
    pathlib.Path("bulk-plan.json").write_text(json.dumps({"to_send": plan["to_send"], "batches": batches,
                                                          "ruled": {str(k): v for k, v in plan["ruled"].items()},
                                                          "rep_of": {str(k): v for k, v in plan["rep_of"].items()}}))
    md = ["# Bulk job plan\n", summary + "\n"]
    md.append(section("Cost by route (costcalc, your prices)", capture(costcalc.main, a.prices, "--calls", str(n_calls),
                                                                         "--input", str(in_per_call), "--output", str(out_per_call))))
    md.append("Next: run each batch, validate answers with a deterministic check, retry ONLY failed ids (batch_pack.retry_plan), "
              "then rebuild all rows with prefilter.expand.\n")
    pathlib.Path(a.out).write_text("\n".join(md), encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
