#!/usr/bin/env python3
"""
repair_plan.py - when a model fills in records, re-ask ONLY for the broken fields.

THE PROBLEM
-----------
A batch job asks a model to return 500 JSON records. 12 records have a missing or
invalid field. The wasteful fix re-sends all 500. The cheap fix re-sends the 12
bad records, and only asks for the fields that failed.

WHAT THIS TOOL DOES (no model call)
-----------------------------------
  validate(record, schema)   returns the list of failing fields for one record
  plan(records, schema)      returns the minimal repair requests: for each bad record,
                             the original input plus the exact fields to redo
  merge(records, repairs)    merges repaired fields back, leaving good fields untouched

SCHEMA (dict of field -> rule). A rule is one of:
    "str"  non-empty string      "int"  integer      "float"  number
    ["a","b"]  value must be one of the listed choices
    "regex:^[A-Z]{2}$"  value must match the regular expression

WORKED EXAMPLE
--------------
    >>> schema = {"country": "regex:^[A-Z]{2}$", "plan": ["basic", "pro"], "gb": "int"}
    >>> recs = [{"id": 1, "country": "PT", "plan": "pro", "gb": 5}, {"id": 2, "country": "Portugal", "plan": "pro", "gb": "x"}]
    >>> plan(recs, schema)
    [{'id': 2, 'redo_fields': ['country', 'gb']}]
"""
from __future__ import annotations

import re


def field_ok(value, rule) -> bool:
    """Does one value satisfy one rule? Unknown rules fail closed (return False)."""
    if isinstance(rule, list):
        return value in rule
    if rule == "str":
        return isinstance(value, str) and value.strip() != ""
    if rule == "int":
        return isinstance(value, int) and not isinstance(value, bool)  # bool is an int subclass: reject it
    if rule == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(rule, str) and rule.startswith("regex:"):
        return isinstance(value, str) and re.search(rule[6:], value) is not None
    return False


def validate(record: dict, schema: dict) -> list[str]:
    """Names of fields that are missing or invalid in this record."""
    return [f for f, rule in schema.items() if f not in record or not field_ok(record[f], rule)]


def plan(records: list[dict], schema: dict, id_key: str = "id") -> list[dict]:
    """Minimal repair requests: only bad records, only failing fields."""
    out = []
    for r in records:
        bad = validate(r, schema)
        if bad:
            out.append({id_key: r.get(id_key), "redo_fields": bad})
    return out


def merge(records: list[dict], repairs: dict, id_key: str = "id") -> list[dict]:
    """Apply repaired fields ({id: {field: value}}) without touching fields that were already good."""
    # JSON object keys are always strings, so a repairs file loaded from disk has "2", not 2.
    # Look the record up by its own id first, then by the string form of it.
    def fix(r):
        rid = r.get(id_key)
        return {**r, **repairs.get(rid, repairs.get(str(rid), {}))}
    return [fix(r) for r in records]
