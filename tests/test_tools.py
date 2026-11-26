"""Unit tests for the cheap-inference tools. Run:  python -m unittest discover -s tests -v"""
import datetime as dt
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import budget, cache_sim, chunker, compact, costcalc, dedup, kb, ladder_log, prompt_lint, router, session_budget, tokens, usage_report  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
