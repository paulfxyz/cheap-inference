# Changelog

## 2.1.0 - 2026-11-27

Reviewed by four frontier models through OpenRouter, then extended.

### Added
- Chapter 15: the multi-model review (Claude Fable 5.2, Gemini 4 Neon, GPT 6.2 Astra, Grok 4.7): method, consensus, what was accepted and declined. Raw answers in `docs/reviews/`.
- Chapter 16 (advanced techniques) and chapter 17 (workflows).
- 21 tools: `schema_diet`, `payload_compact`, `fewshot_prune`, `history_trim`, `token_calibrate`, `prefilter`, `cascade`, `topk`, `batch_pack`, `repair_plan`, `response_cache`, `singleflight`, `cache_breakeven`, `wave_plan`, `output_audit`, `waste_finder`, `preflight`, `wiki_roi`, `edit_guard`, `eval_gate`, `lane_picker` (34 tools in total).
- 8 workflows in `workflows/`: weekly audit, safe downgrade, bulk job planner, session hygiene, context diet, long-document Q and A, repair failed fields, cache decision.
- GitHub Actions: `cost-gate.yml` (pull requests) and `weekly-audit.yml` (every Monday).
- Prompts 43 to 54, tips 101 to 154, recipes 13.11 to 13.13, checklist additions, new example data files.
- 59 new tests (89 in total), including a test that no tool imports a network or subprocess module.

### Changed
- Caching guidance now covers the write premium, expiry, minimum prefix and warm-up (chapter 8).
- The fixed "50 to 100 sources" wiki threshold is replaced by `wiki_roi.py`.
- `tokens.py` estimates by content kind and accepts a calibration file; `session_budget.py` models caching; `compact.py` keeps error lines from the cut region; `budget.py` counts requests and tool schemas; `ladder_log.py` can probe a lower rung; `kb.py` gained `lint --skip-stale` and tolerates curly quotes.
- Claim wording: the checks cost zero tokens; repairing findings costs what it costs. Documented limits of the quote check, the verifier and fan-out.

### Fixed
- Ingest loop ordering: lint ran before `done`, so a correct edit of a changed source could never pass rule R7.
- Nightly script no longer treats a failing `status` as zero pending; staging is limited to `wiki/` and `.brain/`.

## 2.0.0 - 2026-11-26

The toolkit grows from a starter kit into a full field guide.

### Added
- Six tools: `prompt_lint.py`, `compact.py`, `chunker.py`, `usage_report.py`, `ladder_log.py`, `session_budget.py` (13 tools in total, all standard library only).
- Chapter 11: 42 copy-paste prompts. Chapter 12: 100 tips and tweaks. Chapter 13: ten end-to-end recipes. Chapter 14: bold claims with a runnable receipt for each, and what is not claimed.
- Animated illustrations: hero, linter, ladder and always-loaded-context diet.
- 13 new unit tests (30 in total).
- Redesigned README: claim cards, flow diagram, starting points, FAQ.

### Changed
- Minimum Python is now 3.10.
- CI runs on Python 3.10 and 3.12.

## 1.0.0 - 2026-11-26

Initial release: `kb.py`, `tokens.py`, `budget.py`, `costcalc.py`, `router.py`, `dedup.py`, `cache_sim.py`, ten chapters, templates and examples.
