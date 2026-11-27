#!/usr/bin/env python3
"""
repair_failed_fields.py - after a model fills records, re-ask ONLY for what failed.

CHAINS: repair_plan (validate -> plan -> merge)

THE LOOP
    1. a model returned records.json (list of dicts with an "id")
    2. this script validates every record against schema.json (see repair_plan.py for rule syntax)
    3. it writes repair-requests.jsonl: one line per bad record, naming ONLY the failing fields
    4. your runner sends those small requests, saves {"<id>": {"field": value}} as repairs.json
    5. run again with --repairs repairs.json to merge them; anything still failing is reported

WHY: re-sending 500 records to fix 12 pays 40x too much, and risks changing the 488 good ones.
Exit code 0 when every record is valid, 1 when some still need repair.
"""
import argparse
import json
import pathlib

from _common import capture
import repair_plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan or merge field-level repairs.")
    ap.add_argument("records")
    ap.add_argument("schema")
    ap.add_argument("--repairs", help="JSON {id: {field: value}} to merge before re-validating")
    ap.add_argument("--max-attempts", type=int, default=2, help="stop asking after this many rounds (stored in repair-state.json)")
    ap.add_argument("--out", default="repair-requests.jsonl")
    a = ap.parse_args(argv)

    records = json.loads(pathlib.Path(a.records).read_text())
    schema = json.loads(pathlib.Path(a.schema).read_text())
    if a.repairs:
        records = repair_plan.merge(records, json.loads(pathlib.Path(a.repairs).read_text()))
        pathlib.Path(a.records).write_text(json.dumps(records, indent=1))
    state_file = pathlib.Path("repair-state.json")
    state = json.loads(state_file.read_text()) if state_file.exists() else {"rounds": 0}
    todo = repair_plan.plan(records, schema)
    total = len(records)
    if not todo:
        print(f"all {total} record(s) valid")
        state_file.unlink(missing_ok=True)
        return 0
    state["rounds"] += 1
    state_file.write_text(json.dumps(state))
    if state["rounds"] > a.max_attempts:
        print(f"{len(todo)} record(s) still invalid after {a.max_attempts} repair round(s): stop paying, escalate or review by hand")
        return 1
    pathlib.Path(a.out).write_text("\n".join(json.dumps(t) for t in todo) + "\n")
    fields = sum(len(t["redo_fields"]) for t in todo)
    print(f"{len(todo)} of {total} record(s) need repair ({fields} field(s)); wrote {a.out} (round {state['rounds']})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
