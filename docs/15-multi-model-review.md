# 15. Multi-model review: what four frontier models found

> For version 2.1.0 the whole repository was handed to four frontier models through OpenRouter, with one instruction: be a sceptical reviewer, list what is wrong, and propose cost-saving ideas the repository does not cover. This chapter records what they said, what we accepted, what we declined, and what changed.

## 15.1 Method

| | |
| --- | --- |
| **Models** | `anthropic/claude-fable-5.2`, `google/gemini-4-neon`, `openai/gpt-6.2-astra` (the three top-tier models), plus `x-ai/grok-4.7` as a fourth opinion |
| **Input** | README, chapters 1 to 10 and 14, and the tool list of version 2.0.0 (about 16,000 tokens) |
| **Task A** | Audit: quote every claim, number or recommendation that is wrong, outdated, overstated or missing a caveat; list the ideas worth keeping |
| **Task B** | Extend: propose techniques and workflows not already covered, each with a concrete standard-library Python tool |
| **Output** | JSON only, stored verbatim in [`docs/reviews/`](reviews/) together with [the exact prompt](reviews/prompt.md) |

Honest notes about the process:

- Each model received the same repository text and the same questions. GPT-6.2 astra and Grok 4.7 got a tighter output cap (fewer items, terse algorithms): their first attempts at the larger size were cut off by the connection before finishing, and `gpt-6.2-astra-pro` failed the same way three times, so it was dropped. Their lists are therefore shorter, which is a property of the process, not of the models.
- Models can be wrong or flatter. Every finding below was checked against the code or the text before being accepted. Gemini ran with its default reasoning settings; the other three ran with reasoning effort set to low, because a first attempt without that setting spent its whole output budget on hidden reasoning and returned nothing (the very problem `output_audit.py` looks for). The answers are not a benchmark of the models.
- Four opinions are evidence, not proof. Counts show agreement, not truth.

## 15.2 Numbers

| Model | Problems found | Ideas to keep | New techniques | New workflows |
| --- | :-: | :-: | :-: | :-: |
| claude-fable-5.2 | 31 | 5 | 14 | 8 |
| gemini-4-neon | 10 | 5 | 12 | 6 |
| gpt-6.2-astra | 10 | 0 | 5 | 3 |
| grok-4.7 | 10 | 0 | 8 | 4 |
| **Total** | **61** | | **39** | **21** |

## 15.3 Where they agreed

Findings raised by two or more models are the strongest signal. All of them were accepted, in whole or in part.

| Finding | Raised by | What changed in 2.1.0 |
| --- | :-: | --- |
| Caching has caveats: cache WRITES can cost more than normal input, caches expire, small prefixes are not cached, so trimming and caching pull against each other | 4 of 4 | Chapter 8 section 8.2b; new `cache_breakeven.py`, `wave_plan.py`, `cache_decision` workflow |
| The "50 to 100 sources" threshold for a wiki is arbitrary and unsourced | 4 of 4 | Threshold removed from the prose; new `wiki_roi.py` computes the break-even from your numbers (chapters 3 and 9) |
| The quote check proves a string exists, not that the claim is supported | 4 of 4 | Chapter 4.3 now states exactly what R6 proves and what it does not; punctuation-insensitive matching added so curly quotes cannot cause false alarms |
| The session-split saving (82%) ignores caching, so it is overstated | 3 of 4 | `session_budget.py` gained `--cached-share` and `--cache-price`; the output with caching shows a much smaller gain |
| `chars / 4` under-counts code, JSON and non-Latin text | 3 of 4 | `tokens.py` detects the kind of text and uses per-kind ratios; new `token_calibrate.py` measures your own ratios |
| Always-loaded text is billed on every REQUEST, not once per session, and tool schemas are a big hidden part | 2 of 4 | `budget.py` supports `requests_per_session` and `tool_schema_tokens`; new `schema_diet.py` and `context_diet` workflow |
| Head/tail log compaction can drop a root cause in the middle | 2 of 4 | `compact.py` now rescues error-like lines from the cut region |
| "Zero tokens" is overstated: the lint hook's feedback makes the model spend tokens fixing | 2 of 4 | Claim reworded: the CHECK costs zero tokens; repairing costs what it costs. A test now proves the tools import no network or subprocess modules |
| The ladder mixes two axes (machinery vs model tier) and escalation is not free | 2 of 4 | Chapter 6 sections 6.1b and 6.6; `ladder_log.py` gained `should_probe` |
| A verifier that sees only summaries cannot recover omitted qualifications; a fresh context removes anchoring, not model bias | 2 of 4 | Chapter 7 section 7.4b |
| A cached model answer freezes one sample; the key must include sampling settings; concurrent writers can corrupt a file | 2 of 4 | New `response_cache.py` with TTL, full keys and atomic writes |

## 15.4 Found by one model, verified, and fixed

These single-model findings were real bugs or gaps.

- **A sequencing bug in the ingest loop** (GPT-6.2 astra). The documented loop ran `lint` before `done`, but rule R7 compares the raw file with the manifest that `done` updates. A correct edit of a CHANGED file could never pass lint. Fix: `kb.py lint --skip-stale` for the mid-ingest pass, a strict lint after `done`, and a regression test.
- **A quiet-night script that hides failures** (GPT-6.2 astra). `status | wc -l` turns a crashed `status` into a "zero pending" success. Fix: `set -eo pipefail` and an explicit failure branch in chapter 5 and recipe 13.2.
- **Over-broad staging** (GPT-6.2 astra). `git add -A` in an unattended job can commit unrelated files or secrets. Fix: stage `wiki/` and `.brain/` only.
- **"Models do not forget cross-references"** (Grok 4.7). False, and it encourages unattended runs. The sentence was rewritten.
- **"Everything is tested"** (Claude Fable 5.2). 30 tests over 13 tools was thin. There are now 89 tests, and the claim says what is covered.
- **JSON is not always shorter** (Claude Fable 5.2). Caveat added; `payload_compact.py` measures the difference.
- **Repair cost** (Gemini 4 neon): "cheap draft, strong review" can cost more than the strong model when the cheap one fails often. `cascade.py` computes the break-even acceptance rate.

## 15.5 Declined or only partly accepted

- "Seconds is more realistic than milliseconds for linting a thousand pages" (Fable). Plausible for large vaults on slow disks; the text now says "a small vault takes well under a second" instead of promising a figure. It has not been benchmarked.
- "Use a flat model tier ladder" or "start higher for hard tasks" (several). Kept as guidance, but the repository does not claim a universal ordering; see 6.1b.
- Suggestions that need provider-specific features (exact cache control headers, particular tool-call formats) were not turned into code, because the tools are provider-agnostic on purpose.

## 15.6 What the models liked

Ideas at least two reviewers explicitly said to keep: tiered loading with a "when not to read" line; manifest and hash based incremental ingest; deterministic checks instead of model self-review; honest limits and a refusal to ship invented prices; a price table the user fills in.

## 15.7 The new ideas, merged

The reviewers proposed 39 techniques. Many overlapped. The merged set that became tools is in [chapter 16](16-advanced-techniques.md); the workflows are in [chapter 17](17-workflows.md).

| Idea (proposed by) | Became |
| --- | --- |
| Tool and MCP schema pruning (Gemini, Fable) | `schema_diet.py` |
| Model cascade with a validator gate, and its break-even (Gemini, Fable, Grok) | `cascade.py` |
| Cache-write break-even and warm-up waves (Fable, Gemini) | `cache_breakeven.py`, `wave_plan.py` |
| Output and reasoning token audit (Gemini, Fable, Grok) | `output_audit.py` |
| Search-and-replace patches instead of whole files (Gemini, Fable, GPT) | `edit_guard.py` |
| Rule pre-filter and exact-duplicate collapse (Gemini, Fable) | `prefilter.py` |
| Lexical passage selection (Fable, Grok) | `topk.py` |
| Stale tool-output eviction (Gemini, Fable, Grok) | `history_trim.py` |
| Micro-batch packing with partial retry (Gemini, Fable) | `batch_pack.py` |
| Retry and loop waste finder (Fable, Grok) | `waste_finder.py` |
| A quality gate for every cost change (Fable, Gemini) | `eval_gate.py` |
| Few-shot example pruning (Fable) | `fewshot_prune.py` |
| JSON to delimited payload (Gemini) | `payload_compact.py` |
| Coalesce concurrent misses and debounce superseded requests (GPT) | `singleflight.py` |
| Repair failed fields, not whole records (GPT) | `repair_plan.py` |
| Lane and flex-tier picker (Grok) | `lane_picker.py` |
| Retry pre-flight checks (Grok) | `preflight.py` |
