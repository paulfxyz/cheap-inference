"""Unit tests for the cheap-inference tools. Run:  python -m unittest discover -s tests -v"""
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "workflows"))

import batch_pack, lane_picker, preflight, repair_plan, singleflight, wave_plan, budget, cache_breakeven, cache_sim, cascade, edit_guard, eval_gate, fewshot_prune, history_trim, output_audit, payload_compact, prefilter, response_cache, schema_diet, token_calibrate, topk, waste_finder, wiki_roi, chunker, compact, costcalc, dedup, kb, ladder_log, prompt_lint, router, session_budget, tokens, usage_report  # noqa: E402


class TokenTests(unittest.TestCase):
    def test_estimate(self):
        r = tokens.estimate_tokens("a" * 400)
        self.assertEqual(r["tokens_by_chars"], 100)


class CostTests(unittest.TestCase):
    route = {"input_per_million": 1.0, "cached_input_per_million": 0.1, "output_per_million": 2.0}

    def test_no_cache(self):
        # 1M input at 1.0 + 1M output at 2.0 = 3.0
        self.assertAlmostEqual(costcalc.call_cost(self.route, 1_000_000, 1_000_000, 0.0), 3.0)

    def test_full_cache(self):
        self.assertAlmostEqual(costcalc.call_cost(self.route, 1_000_000, 0, 1.0), 0.1)

    def test_clamp_and_multiplier(self):
        r = dict(self.route, multiplier=0.5)
        self.assertAlmostEqual(costcalc.call_cost(r, 1_000_000, 0, 5.0), 0.05)  # 5.0 clamps to 1.0

    def test_sorted(self):
        table = {"routes": {"a": self.route, "b": dict(self.route, input_per_million=9.0)}}
        rows = costcalc.compare(table, 10, 1000, 100, 0.0)
        self.assertEqual(rows[0]["route"], "a")


class RouterTests(unittest.TestCase):
    def test_inline(self):
        self.assertEqual(router.pick_rung("what is a hash")["rung"], 0)

    def test_deep(self):
        self.assertEqual(router.pick_rung("deep research on markets")["rung"], 4)

    def test_size_pushes_up(self):
        self.assertEqual(router.pick_rung("look up the price", 100)["rung"], 4)


class DedupTests(unittest.TestCase):
    def test_identical(self):
        a = "the quick brown fox jumps over the lazy dog again and again"
        pairs = dedup.find_duplicates({"x": a, "y": a, "z": "totally unrelated words appear here instead of that"})
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0], 1.0)

    def test_empty(self):
        self.assertEqual(dedup.jaccard(set(), set()), 0.0)


class CacheTests(unittest.TestCase):
    def test_prefix_order(self):
        s = [("a", 10), ("b", 10)]
        self.assertEqual(cache_sim.common_prefix_tokens(s, [("a", 10), ("c", 5)]), 10)
        self.assertEqual(cache_sim.common_prefix_tokens(s, [("x", 10), ("b", 10)]), 0)


class BudgetTests(unittest.TestCase):
    def test_over(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "big.md").write_text("x" * 4000)  # ~1000 tokens
            rep = budget.audit({"total_limit_tokens": 500, "files": [{"path": "big.md", "limit_tokens": 500}]}, pathlib.Path(d))
            self.assertEqual(rep["total_status"], "OVER")


class KBTests(unittest.TestCase):
    def test_sample_is_clean(self):
        self.assertEqual(kb.KB(ROOT / "examples" / "sample-kb").lint(), [])

    def test_broken_is_caught(self):
        errs = "\n".join(kb.KB(ROOT / "examples" / "broken-kb").lint())
        for needle in ("broken link [[nonexistent-page]]", "QUOTE NOT IN SOURCE", "does not exist", "TODO", "lacks 'updated'", "orphan"):
            self.assertIn(needle, errs)

    def test_incremental_flow(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "raw").mkdir(); (root / "wiki").mkdir()
            (root / "raw" / "a.md").write_text("alpha")
            k = kb.KB(root)
            self.assertEqual(k.status(), [("NEW", "raw/a.md")])
            (root / "wiki" / "a.md").write_text("---\ntitle: A\nsources: raw/a.md\nupdated: 2026-01-01\n---\nx [[a]]")
            self.assertEqual(k.done("raw/a.md", ["wiki/a.md"]), 0)
            self.assertEqual(k.status(), [])
            (root / "raw" / "a.md").write_text("alpha changed")
            self.assertEqual(k.status(), [("CHANGED", "raw/a.md")])
            (root / "raw" / "a.md").unlink()
            self.assertEqual(k.status(), [("DELETED", "raw/a.md")])

    def test_stale_and_future(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / "wiki").mkdir()
            (root / "wiki" / "old.md").write_text("---\ntitle: O\nsources: \nupdated: 2020-01-01\n---\n")
            k = kb.KB(root)
            self.assertEqual(k.stale(90, dt.date(2026, 11, 26))[0][0], "wiki/old.md")
            (root / "wiki" / "old.md").write_text("---\ntitle: O\nsources: \nupdated: 2099-01-01\n---\n")
            self.assertTrue(any("future" in e for e in k.lint(dt.date(2026, 11, 26))))

    def test_hot_cache_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / "wiki").mkdir()
            (root / "wiki" / "hot.md").write_text("\n".join(f"line {i}" for i in range(40)))
            self.assertTrue(any("hot cache" in e for e in kb.KB(root).lint()))


class PromptLintTests(unittest.TestCase):
    def test_volatile_head(self):
        f = prompt_lint.lint_text("g", "Today is 2026-11-26.\nRules follow.")
        self.assertTrue(any("P1" in x for x in f))

    def test_filler_and_eager(self):
        text = "Please be good. Please do it. Kindly note this.\n@big-index.md\nmax 50 words"
        f = "\n".join(prompt_lint.lint_text("g", text))
        self.assertIn("P2", f); self.assertIn("P5", f)

    def test_clean(self):
        self.assertEqual(prompt_lint.lint_text("g", "Answer in a table, max 50 words."), [])

    def test_repeat(self):
        line = "Always run the linter after every wiki edit."
        self.assertTrue(any("P3" in x for x in prompt_lint.lint_text("g", line + "\n" + line)))


class CompactTests(unittest.TestCase):
    def test_collapse(self):
        self.assertEqual(compact.collapse_repeats(["a", "a", "a", "b"]), ["a  (x3)", "b"])

    def test_head_tail(self):
        text = "\n".join(f"line {i}" for i in range(500))
        out, st = compact.compact(text, head=5, tail=5)
        self.assertIn("490 lines omitted", out)
        self.assertLess(st["chars_after"], st["chars_before"])

    def test_grep_context(self):
        out, _ = compact.compact("a\nb\nERROR x\nc\nd\ne\nf", grep="error", context=1)
        self.assertIn("ERROR x", out); self.assertNotIn("f", out.split())


class ChunkerTests(unittest.TestCase):
    def test_splits_on_headings(self):
        text = "# A\n" + "word " * 600 + "\n# B\n" + "word " * 600
        self.assertGreaterEqual(len(chunker.chunk(text, 200)), 2)

    def test_write_pages(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "big.md"; src.write_text("# A\nhello\n\n# B\nworld " * 50)
            paths = chunker.write_pages(src, pathlib.Path(d) / "out", 50)
            self.assertTrue(paths and "sources:" in paths[0].read_text())


class UsageTests(unittest.TestCase):
    def test_rank(self):
        rows = [{"task": "a", "input": 100, "output": 10}, {"task": "b", "input": 1000, "output": 10, "cached": 900}]
        g = usage_report.aggregate(rows)
        self.assertEqual(g[0]["group"], "b"); self.assertAlmostEqual(g[0]["cache_hit"], 0.9)
        self.assertIn("b", usage_report.hint(g))


class LadderLogTests(unittest.TestCase):
    def test_floor(self):
        rows = [{"kind": "k", "rung": 1, "accepted": False}] * 3 + [{"kind": "k", "rung": 2, "accepted": True}] * 3
        self.assertEqual(ladder_log.floor(rows, "k")["floor"], 2)
        self.assertEqual(ladder_log.floor([], "k")["floor"], 0)


class SessionBudgetTests(unittest.TestCase):
    def test_split_beats_long(self):
        self.assertLess(session_budget.best_k(60, 700, 1500, 400)[1], session_budget.long_session(60, 700, 1500))

    def test_k_equals_turns_is_long(self):
        self.assertEqual(session_budget.split_sessions(10, 100, 50, 0, 10), session_budget.long_session(10, 100, 50))



class SchemaDietTests(unittest.TestCase):
    TOOLS = [{"name": "a", "description": "x" * 400, "parameters": {}}, {"type": "function", "function": {"name": "b", "description": "y", "parameters": {}}}]

    def test_unused_flagged(self):
        import collections
        r = schema_diet.analyse(self.TOOLS, collections.Counter({"b": 2}))
        self.assertEqual(r["unused"], 1); self.assertGreater(r["saved"], 50)
        self.assertEqual(schema_diet.tool_name(self.TOOLS[1]), "b")

    def test_no_usage_data(self):
        self.assertTrue(all(x["verdict"] == "no usage data" for x in schema_diet.analyse(self.TOOLS)["rows"]))


class CascadeTests(unittest.TestCase):
    def test_break_even(self):
        self.assertAlmostEqual(cascade.break_even(1, 10), 0.1)
        self.assertEqual(cascade.break_even(10, 10), 1.0)
        self.assertEqual(cascade.break_even(1, 0), 1.0)

    def test_escalates_and_pays_for_failures(self):
        routes = [("small", lambda p: "nope"), ("big", lambda p: "{}")]
        r = cascade.run_cascade("q", routes, cascade.is_json, {"small": 1, "big": 10})
        self.assertEqual(r["route"], "big"); self.assertEqual(r["spent"], 11)
        self.assertEqual(r["attempts"], ["small:rejected", "big:accepted"])

    def test_stops_at_first_accept(self):
        r = cascade.run_cascade("q", [("small", lambda p: "{}"), ("big", lambda p: "{}")], cascade.is_json, {"small": 1, "big": 10})
        self.assertEqual(r["spent"], 1)


class CacheBreakevenTests(unittest.TestCase):
    def test_min_requests(self):
        self.assertEqual(cache_breakeven.min_requests(1.25, 0.1), 2)
        self.assertEqual(cache_breakeven.min_requests(2.0, 0.5), 4)   # (2-.5)/(1-.5)=3 -> need 4
        self.assertEqual(cache_breakeven.min_requests(1.25, 1.0), 0)  # read not cheaper: never

    def test_ratio(self):
        self.assertAlmostEqual(cache_breakeven.cost_ratio(5, 1.25, 0.1), (1.25 + 0.4) / 5)


class OutputAuditTests(unittest.TestCase):
    def test_reasoning_heavy(self):
        r = output_audit.audit([{"task": "t", "output": 100, "reasoning": 900}])[0]
        self.assertIn("reasoning", r["suggestion"])

    def test_cap(self):
        r = output_audit.audit([{"task": "t", "output": 990, "max_output": 1000}] * 3)[0]
        self.assertIn("cap", r["suggestion"])


class EditGuardTests(unittest.TestCase):
    PATCH = "<<<<<<< SEARCH\nfoo = 1\n=======\nfoo = 2\n>>>>>>> REPLACE"

    def test_apply(self):
        new, rep = edit_guard.apply_blocks("a\nfoo = 1\nb", edit_guard.parse_blocks(self.PATCH))
        self.assertEqual(new, "a\nfoo = 2\nb")

    def test_refuses_missing_and_ambiguous(self):
        with self.assertRaises(ValueError):
            edit_guard.apply_blocks("nothing", edit_guard.parse_blocks(self.PATCH))
        with self.assertRaises(ValueError):
            edit_guard.apply_blocks("foo = 1\nfoo = 1", edit_guard.parse_blocks(self.PATCH))


class PrefilterTests(unittest.TestCase):
    def test_split_and_expand(self):
        rows = ["Hello  World", "hello world", "", "spam!!", "other"]
        plan = prefilter.split(rows, [{"pattern": r"^$", "label": "EMPTY"}, {"pattern": "spam", "label": "SPAM"}])
        self.assertEqual(plan["to_send"], [0, 4]); self.assertEqual(plan["rep_of"], {1: 0})
        out = prefilter.expand(plan, {0: "A", 4: "B"})
        self.assertEqual(out, ["A", "A", "EMPTY", "SPAM", "B"])


class TopkTests(unittest.TestCase):
    TEXT = "Refunds are issued within 14 days.\n\nThe weather is nice today.\n\nDelayed activation refund policy applies after 24 hours."

    def test_relevance(self):
        best = topk.pick(self.TEXT, "refund policy delayed activation", 200)[0][1]
        self.assertIn("Delayed activation", best)

    def test_budget_respected(self):
        self.assertEqual(topk.pick(self.TEXT, "refund", 1), [])


class HistoryTrimTests(unittest.TestCase):
    def test_trim(self):
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}, {"role": "tool", "content": "x" * 2000},
                {"role": "assistant", "content": "a"}, {"role": "tool", "content": "y" * 2000}, {"role": "user", "content": "last"}]
        out = history_trim.trim(msgs, keep_last=2, min_chars=500)
        self.assertIn("removed", out[2]["content"]); self.assertEqual(out[4]["content"], "y" * 2000)  # tail kept
        self.assertEqual(msgs[2]["content"], "x" * 2000)  # original untouched


class BatchPackTests(unittest.TestCase):
    def test_plan_covers_all_once(self):
        items = [f"item {i}" for i in range(45)]
        b = batch_pack.plan(items, size=10)
        self.assertEqual(sorted(i for x in b for i in x), list(range(45))); self.assertTrue(all(len(x) <= 10 for x in b))

    def test_retry_only_failed(self):
        items = [f"item {i}" for i in range(30)]
        self.assertEqual(sorted(i for x in batch_pack.retry_plan([3, 7, 21], items, 2) for i in x), [3, 7, 21])

    def test_gain(self):
        self.assertEqual(batch_pack.gain(400, 20, 300), (120000, 6000))


class WasteFinderTests(unittest.TestCase):
    def test_all_three(self):
        rows = [{"task": "d", "prompt_hash": "a", "input": 10, "output": 5, "t": i} for i in range(3)]
        rows += [{"task": "e", "prompt_hash": f"b{i}", "status": "error", "input": 10, "output": 5, "t": 100 + i} for i in range(3)]
        rows += [{"task": "loop", "prompt_hash": f"l{i}", "input": 1, "output": 1, "t": 200 + i} for i in range(8)]
        f = waste_finder.find(rows)
        self.assertEqual(len(f["repeats"]), 1); self.assertEqual(len(f["retries"]), 1); self.assertEqual(len(f["loops"]), 1)
        self.assertGreater(f["avoidable"], 0)


class EvalGateTests(unittest.TestCase):
    def test_wilson_bounds(self):
        lo, hi = eval_gate.wilson(9, 10)
        self.assertTrue(0 < lo < 0.9 < hi < 1)
        self.assertEqual(eval_gate.wilson(0, 0), (0.0, 1.0))

    def test_adopt_reject_inconclusive(self):
        self.assertEqual(eval_gate.verdict([1] * 200, [1] * 200)["verdict"], "ADOPT")
        self.assertEqual(eval_gate.verdict([1] * 100, [0] * 100)["verdict"], "REJECT")
        self.assertEqual(eval_gate.verdict([1] * 10, [1] * 9 + [0])["verdict"], "INCONCLUSIVE")

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            eval_gate.verdict([1], [1, 0])


class ResponseCacheTests(unittest.TestCase):
    def test_hit_miss_ttl_and_key(self):
        with tempfile.TemporaryDirectory() as d:
            c = response_cache.ResponseCache(d, ttl_seconds=100)
            self.assertIsNone(c.get("m", "hello  world", {"t": 0}, "v1", now=0))
            c.put("m", "hello world", {"t": 0}, "v1", "A", now=0)
            self.assertEqual(c.get("m", "hello   world", {"t": 0}, "v1", now=50), "A")      # whitespace-insensitive
            self.assertIsNone(c.get("m", "hello world", {"t": 1}, "v1", now=50))            # params change the key
            self.assertIsNone(c.get("m", "hello world", {"t": 0}, "v2", now=50))            # prompt version changes the key
            self.assertIsNone(c.get("m", "hello world", {"t": 0}, "v1", now=500))           # expired
            self.assertAlmostEqual(c.stats()["hit_rate"], 0.2)


class PayloadCompactTests(unittest.TestCase):
    def test_roundtrip_and_smaller(self):
        rows = [{"name": f"n{i}", "qty": str(i)} for i in range(20)]
        t = payload_compact.to_tsv(rows)
        self.assertEqual(payload_compact.from_tsv(t), rows)
        self.assertLess(len(t), len(json.dumps(rows)))

    def test_ragged_and_tabs(self):
        t = payload_compact.to_tsv([{"a": "x\ty"}, {"b": 1}])
        self.assertEqual(t.split("\n")[0], "a\tb")


class WikiRoiTests(unittest.TestCase):
    def test_break_even(self):
        r = wiki_roi.compare(200, 6000, 1500, 20, 12000)
        self.assertTrue(r["wins"]); self.assertEqual(r["break_even"], 54)
        self.assertFalse(wiki_roi.compare(5, 6000, 1500, 20, 12000)["wins"])
        self.assertIsNone(wiki_roi.compare(5, 1000, 1000, 1, 1)["break_even"])


class TokenCalibrateTests(unittest.TestCase):
    def test_calibrate(self):
        t = token_calibrate.calibrate([{"kind": "code", "chars": 300, "tokens": 100}, {"kind": "code", "chars": 600, "tokens": 200}])
        self.assertEqual(t["code"]["chars_per_token"], 3.0)

    def test_detect(self):
        self.assertEqual(token_calibrate.detect_kind("Hello there, this is plain English prose."), "prose")
        self.assertEqual(token_calibrate.detect_kind('{"a": "b", "c": "d", "e": "f"}'), "json")
        self.assertEqual(token_calibrate.detect_kind("日本語のテキストです。これはテストです。"), "cjk")
        self.assertEqual(token_calibrate.detect_kind("def f(x):\n    return {x: [1, 2]}; y = (x_1)"), "code")

    def test_tokens_use_kind(self):
        self.assertGreater(tokens.estimate_tokens("日本語のテキストです。" * 10)["tokens_by_kind"], tokens.estimate_tokens("日本語のテキストです。" * 10)["tokens_by_chars"])


class FewshotTests(unittest.TestCase):
    def test_greedy(self):
        chosen, cov = fewshot_prune.greedy_cover({"ex1": [1, 2], "ex2": [2], "ex3": [1, 2, 3, 4]}, 3)
        self.assertEqual(chosen, ["ex3"]); self.assertEqual(cov, {1, 2, 3, 4})

    def test_max(self):
        chosen, _ = fewshot_prune.greedy_cover({"a": [1], "b": [2], "c": [3]}, 2)
        self.assertEqual(len(chosen), 2)


class AuditFixTests(unittest.TestCase):
    """Behaviour added after the multi-model review (v2.1.0)."""

    def test_compact_keeps_mid_log_errors(self):
        text = "\n".join(["ok"] * 50 + ["ERROR root cause here"] + [f"noise {i}" for i in range(50)])
        out, _ = compact.compact(text, head=3, tail=3)
        self.assertIn("ERROR root cause here", out)

    def test_kb_quote_punctuation(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / "raw").mkdir(); (root / "wiki").mkdir()
            (root / "raw" / "a.md").write_text("It\u2019s a \u201cquoted\u201d phrase \u2014 really.")
            (root / "wiki" / "a.md").write_text('---\ntitle: A\nsources: raw/a.md\nupdated: 2026-01-01\n---\n[[a]]\n> "It\'s a \"quoted\" phrase - really." - raw/a.md\n')
            self.assertFalse([e for e in kb.KB(root).lint() if "QUOTE" in e])

    def test_budget_counts_requests_and_schemas(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "g.md").write_text("x" * 400)  # 100 tokens
            r = budget.audit({"sessions_per_month": 10, "requests_per_session": 5, "tool_schema_tokens": 50, "files": [{"path": "g.md"}]}, pathlib.Path(d))
            self.assertEqual(r["monthly_loading_tokens"], 150 * 10 * 5)

    def test_session_budget_effective(self):
        self.assertAlmostEqual(session_budget.effective(100, 0.9, 0.1), 19.0)

    def test_ladder_probe(self):
        rows = [{"kind": "k", "rung": 1, "accepted": True}] * 10
        self.assertTrue(ladder_log.should_probe(rows, "k")); self.assertFalse(ladder_log.should_probe(rows[:9], "k"))


class NoNetworkTests(unittest.TestCase):
    """Receipt for the claim 'the tools never call a network or a model' (a real check, not a grep)."""

    FORBIDDEN = {"urllib", "http", "requests", "httpx", "socket", "ssl", "aiohttp", "subprocess", "ftplib", "smtplib"}

    def test_tools_import_no_network_modules(self):
        import ast
        for f in (ROOT / "tools").glob("*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module else []
                for n in names:
                    # tiktoken is the only optional, lazily imported third-party module (never required).
                    self.assertNotIn(n, self.FORBIDDEN, f"{f.name} imports {n}")



class WorkflowSmokeTests(unittest.TestCase):
    """Each workflow must run end to end on the bundled examples and produce its report."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = pathlib.Path.cwd()
        import os
        os.chdir(self.tmp.name)

    def tearDown(self):
        import os
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def ex(self, name):
        return str(ROOT / "examples" / name)

    def test_weekly_audit(self):
        import weekly_audit
        self.assertEqual(weekly_audit.main(["--log", self.ex("usage.sample.jsonl"), "--budget", self.ex("budget.json"), "--base", str(ROOT), "--kb", self.ex("sample-kb"), "--out", "r.md"]), 0)
        text = pathlib.Path("r.md").read_text()
        for needle in ("usage_report", "output_audit", "waste_finder", "budget", "kb stale", "dedup"):
            self.assertIn(needle, text)

    def test_safe_downgrade(self):
        import safe_downgrade
        pathlib.Path("b.json").write_text(json.dumps([1] * 100)); pathlib.Path("c.json").write_text(json.dumps([1] * 100))
        rc = safe_downgrade.main(["--baseline", "b.json", "--candidate", "c.json", "--prices", self.ex("prices.example.json"), "--old", "premium-model", "--new", "small-model", "--calls", "1000", "--input", "2000", "--output", "300"])
        self.assertEqual(rc, 0); self.assertIn("Switch to", pathlib.Path("downgrade-decision.md").read_text())

    def test_bulk_job_planner(self):
        import bulk_job_planner
        pathlib.Path("rows.txt").write_text("\n".join(["same row"] * 50 + [f"row {i}" for i in range(30)] + [""] * 5))
        pathlib.Path("rules.json").write_text(json.dumps([{"pattern": "^$", "label": "EMPTY"}]))
        self.assertEqual(bulk_job_planner.main(["rows.txt", "--prices", self.ex("prices.example.json"), "--rules", "rules.json"]), 0)
        plan = json.loads(pathlib.Path("bulk-plan.json").read_text())
        self.assertEqual(len(plan["to_send"]), 31); self.assertEqual(len(plan["ruled"]), 4)  # splitlines drops the final empty line

    def test_session_hygiene(self):
        import session_hygiene
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}] + [{"role": "tool", "content": "x" * 5000}] * 20 + [{"role": "user", "content": "end"}] * 6
        pathlib.Path("h.json").write_text(json.dumps(msgs))
        self.assertEqual(session_hygiene.main(["h.json", "--soft", "5000"]), 0)

    def test_context_diet(self):
        import context_diet
        self.assertEqual(context_diet.main(["--guide", str(ROOT / "templates" / "AGENTS.md"), "--tools", self.ex("tools.sample.json"), "--tool-calls", self.ex("tool-calls.sample.jsonl"), "--requests", "3"]), 0)

    def test_long_doc_qa(self):
        import long_doc_qa
        pathlib.Path("d.md").write_text("Refund policy: money back within 14 days.\n\n" + "Filler paragraph about nothing. " * 40 + "\n\nShipping takes a week.")
        self.assertEqual(long_doc_qa.main(["d.md", "refund policy money back"]), 0)
        self.assertEqual(long_doc_qa.main(["d.md", "zzzz qqqq"]), 1)



class SingleflightTests(unittest.TestCase):
    def test_coalesces_concurrent_calls(self):
        import time
        g, calls = singleflight.Group(), []
        def work():
            calls.append(1); time.sleep(0.2); return "answer"
        res = singleflight.parallel(lambda: g.do("q", work), n=6)
        self.assertEqual(res, ["answer"] * 6); self.assertEqual(len(calls), 1)

    def test_key_forgotten_after_completion(self):
        g, calls = singleflight.Group(), []
        g.do("q", lambda: calls.append(1)); g.do("q", lambda: calls.append(1))
        self.assertEqual(len(calls), 2)  # sequential calls each run: this is not a cache

    def test_error_shared(self):
        import time
        g = singleflight.Group()
        def boom():
            time.sleep(0.1); raise RuntimeError("x")
        def call():
            try: return g.do("k", boom)
            except RuntimeError as e: return "err"
        self.assertEqual(singleflight.parallel(call, n=3), ["err"] * 3)

    def test_debounce_runs_last_only(self):
        import time
        d, ran = singleflight.Debouncer(0.1), []
        for i in range(5): d.schedule("k", lambda i=i: ran.append(i))
        time.sleep(0.4)
        self.assertEqual(ran, [4])


class RepairPlanTests(unittest.TestCase):
    SCHEMA = {"country": "regex:^[A-Z]{2}$", "plan": ["basic", "pro"], "gb": "int", "name": "str", "ratio": "float"}

    def test_validate_rules(self):
        good = {"country": "PT", "plan": "pro", "gb": 5, "name": "x", "ratio": 1.5}
        self.assertEqual(repair_plan.validate(good, self.SCHEMA), [])
        bad = {"country": "Portugal", "plan": "gold", "gb": True, "name": " ", "ratio": "n"}
        self.assertEqual(sorted(repair_plan.validate(bad, self.SCHEMA)), ["country", "gb", "name", "plan", "ratio"])

    def test_missing_field_and_unknown_rule(self):
        self.assertEqual(repair_plan.validate({}, {"a": "str"}), ["a"])
        self.assertFalse(repair_plan.field_ok("x", "mystery"))  # fails closed

    def test_plan_and_merge(self):
        recs = [{"id": 1, "gb": 5}, {"id": 2, "gb": "x"}]
        self.assertEqual(repair_plan.plan(recs, {"gb": "int"}), [{"id": 2, "redo_fields": ["gb"]}])
        merged = repair_plan.merge(recs, {2: {"gb": 7}})
        self.assertEqual(merged[1]["gb"], 7); self.assertEqual(merged[0]["gb"], 5)


class WavePlanTests(unittest.TestCase):
    def test_schedule_sums(self):
        for n in (1, 2, 21, 200):
            self.assertEqual(sum(wave_plan.schedule(n, 20)), n)
        self.assertEqual(wave_plan.schedule(0, 20), [])
        self.assertEqual(wave_plan.schedule(41, 20), [1, 20, 20])

    def test_warming_cheaper_when_cache_works(self):
        self.assertLess(wave_plan.prefix_cost(200, 6000, 1.25, 0.1, True), wave_plan.prefix_cost(200, 6000, 1.25, 0.1, False))


class LanePickerTests(unittest.TestCase):
    LANES = [{"name": "rt", "price_multiplier": 1.0, "max_latency_minutes": 0.1}, {"name": "std", "price_multiplier": 0.8, "max_latency_minutes": 5}, {"name": "batch", "price_multiplier": 0.5, "max_latency_minutes": 1440}]

    def test_picks_cheapest_that_fits(self):
        self.assertEqual(lane_picker.pick(self.LANES, 600)["name"], "std")
        self.assertEqual(lane_picker.pick(self.LANES, 2000)["name"], "batch")
        self.assertIsNone(lane_picker.pick(self.LANES, 0.01))


class PreflightTests(unittest.TestCase):
    def test_each_check(self):
        self.assertTrue(any("F1" in p for p in preflight.run_all("   ")))
        self.assertTrue(any("F2" in p for p in preflight.run_all("x" * 40000, context=8000, max_tokens=1000)))
        self.assertTrue(any("F3" in p for p in preflight.run_all("Hi {name} and {{user}}")))
        self.assertTrue(any("F4" in p for p in preflight.run_all("ok", max_tokens=0)))
        self.assertTrue(any("F5" in p for p in preflight.run_all("the same long repeated line here\n" * 6)))
        self.assertTrue(any("F6" in p for p in preflight.run_all("key -----BEGIN RSA PRIVATE KEY----- x")))

    def test_clean(self):
        self.assertEqual(preflight.run_all("Summarise this text.", context=8000, max_tokens=500), [])


class KbSkipStaleTests(unittest.TestCase):
    def test_changed_raw_blocks_strict_lint_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root / "raw").mkdir(); (root / "wiki").mkdir()
            (root / "raw" / "a.md").write_text("alpha")
            (root / "wiki" / "a.md").write_text("---\ntitle: A\nsources: raw/a.md\nupdated: 2026-01-01\n---\n[[a]]\n")
            k = kb.KB(root); k.done("raw/a.md", ["wiki/a.md"])
            (root / "raw" / "a.md").write_text("alpha changed")
            self.assertTrue(any("changed since ingest" in e for e in k.lint()))
            self.assertEqual([e for e in k.lint(skip_stale=True) if "changed since ingest" in e], [])


class RepairWorkflowTests(unittest.TestCase):
    def test_round_trip(self):
        import os, repair_failed_fields
        cwd = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                pathlib.Path("r.json").write_text(json.dumps([{"id": 1, "gb": "x"}, {"id": 2, "gb": 3}]))
                pathlib.Path("s.json").write_text(json.dumps({"gb": "int"}))
                self.assertEqual(repair_failed_fields.main(["r.json", "s.json"]), 1)
                self.assertIn('"redo_fields": ["gb"]', pathlib.Path("repair-requests.jsonl").read_text())
                pathlib.Path("fix.json").write_text(json.dumps({"1": {"gb": 9}}))  # string keys, as real JSON files have
                self.assertEqual(repair_failed_fields.main(["r.json", "s.json", "--repairs", "fix.json"]), 0)
            finally:
                os.chdir(cwd)

    def test_stops_after_max_attempts(self):
        import os, repair_failed_fields
        cwd = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                pathlib.Path("r.json").write_text(json.dumps([{"id": 1, "gb": "x"}])); pathlib.Path("s.json").write_text(json.dumps({"gb": "int"}))
                for _ in range(2): repair_failed_fields.main(["r.json", "s.json", "--max-attempts", "2"])
                self.assertEqual(repair_failed_fields.main(["r.json", "s.json", "--max-attempts", "2"]), 1)
                self.assertFalse(pathlib.Path("repair-requests.jsonl").read_text() == "" )
            finally:
                os.chdir(cwd)


class CacheDecisionTests(unittest.TestCase):
    def test_skip_small_prefix_and_use_big(self):
        import os, cache_decision
        cwd = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                pathlib.Path("small.md").write_text("tiny")
                self.assertEqual(cache_decision.main(["--prefix", "small.md", "--requests", "50"]), 1)
                pathlib.Path("big.md").write_text("word " * 3000)
                self.assertEqual(cache_decision.main(["--prefix", "big.md", "--requests", "50"]), 0)
                self.assertEqual(cache_decision.main(["--prefix", "big.md", "--requests", "1"]), 1)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
