# 12. Tips and tweaks

> One hundred and 54 concrete, small changes. Each is cheap to try and easy to undo. Grouped by where the savings come from. Measure before and after with `tools/tokens.py` or `tools/usage_report.py`.

## 12.1 Always-loaded context (1-15)

1. Put a hard token limit on your guide and enforce it in CI with `budget.py`.
2. Delete every sentence that explains something the model already knows.
3. Replace paragraphs of rules with a table: shorter and easier to follow.
4. Move examples to on-demand files; keep one example inline at most.
5. Put "when not to read X" next to every pointer to X.
6. Use links instead of `@file` imports for anything over about 30 lines.
7. Keep skill descriptions under 50 words.
8. Do not paste the same rule into several files; point to one.
9. Remove dates from the top of guides (cache-breakers and quickly stale).
10. Prefer plain sentences over ALL-CAPS emphasis; capitals tokenize worse.
11. Keep memory summaries to durable facts; put volatile facts in pages.
12. Review the guide monthly and delete rules the model now follows by default.
13. Version your guide in git so removing a rule is safe and reversible.
14. Keep one guide per project, not one per tool.
15. Run `prompt_lint.py` on every guide before committing.

## 12.2 Reading and retrieval (16-30)

16. Name pages by content so an index line is enough to choose.
17. Write the answer-bearing sentence first in each page.
18. Split pages over 1,500 tokens.
19. Keep indexes to one line per page.
20. Add a sub-index per domain after about 200 pages.
21. Link related pages so one hop replaces a search.
22. Store reusable query answers as pages.
23. Use tables for reference data.
24. Open files by line range when you know where to look.
25. Grep first, read second: a search that returns 5 lines beats reading a file.
26. Ask for page names before page contents ("which pages would you open?").
27. Cap results: "top 5 only".
28. Use `chunker.py` on big sources before ingest.
29. Mark archived pages and exclude them from the index.
30. Delete or merge near-duplicates found by `dedup.py`.

## 12.3 Ingest and maintenance (31-45)

31. Hash content, not timestamps.
32. Ingest in batches of 5 to 10 and commit each.
33. Make `status` the first step of every automated run.
34. Exit early when nothing changed; do not call the model at all.
35. Re-ingest only CHANGED sources, updating the pages named in the manifest.
36. Keep `raw/` read-only by configuration.
37. Require a quote line for each concrete claim.
38. Lint after every edit, not at the end.
39. Run `stale` weekly and refresh only pages that matter.
40. Record the ingest date in the manifest.
41. Keep a `log.md` for chronology so pages stay topical.
42. Write contradictions into a dedicated page instead of silently overwriting.
43. Prefer many small commits over one giant one.
44. Review the diff, not the whole wiki.
45. Archive sources you will never re-read instead of keeping them in `raw/`.

## 12.4 Routing and models (46-62)

46. Start at rung 0 for definitions, formatting and rewording.
47. Use one search for one fact; do not fan out.
48. Never override the default model without a stated reason.
49. Climb only after naming what failed.
50. Use cheaper models for classification, extraction and reformatting.
51. Use a stronger model for judgement and for review of high-stakes output.
52. Draft cheap, review strong, only when stakes justify the second pass.
53. Keep a log of accepted rungs per task kind (`ladder_log.py`).
54. Treat a repeated task's working rung as its floor.
55. Ask before generating video or other expensive media.
56. Batch anything nobody is waiting for.
57. Route pure text-in/text-out bulk jobs to the cheapest suitable provider and compare with `costcalc.py`.
58. Offer a cheaper route once per heavy batch; do not nag.
59. Keep fallbacks: if one provider fails, another takes over.
60. Lower reasoning effort for mechanical work.
61. Raise it only for planning, hard debugging and genuinely ambiguous problems.
62. Stop tasks early when the answer is already good enough.

## 12.5 Output control (63-78)

63. State a word, line or token cap in every prompt.
64. Ask for the answer first.
65. Forbid introductions and recaps.
66. Ask for a table when comparing.
67. Ask for JSON when code will consume it.
68. Ask for diffs instead of full rewrites.
69. Ask for IDs instead of repeated text ("return the row numbers").
70. Ask for one best option instead of five.
71. Use stop sequences or "end with DONE" for machine-read output.
72. Limit explanations to failures: "explain only if it fails".
73. Ask for confidence labels instead of paragraphs.
74. Request a short summary before a long answer so you can stop early.
75. Ask the model to say "not in the knowledge base" instead of guessing.
76. Prefer yes/no gates before expensive steps.
77. Ask for a plan in 5 lines before a long implementation.
78. Cap the number of tool calls explicitly.

## 12.6 Caching and ordering (79-88)

79. Stable instructions first, changing input last.
80. No timestamps or IDs at the top.
81. Keep tool and example order fixed.
82. Append to conversations; never rewrite earlier turns.
83. Do not edit the system prompt mid-session.
84. Put the current date after the stable block.
85. Reuse identical prefixes across a batch.
86. Check the provider's minimum cacheable size and lifetime.
87. Keep batches running close together so the cache is still warm.
88. Cache your own deterministic results in a local dictionary.

## 12.7 Sessions and history (89-95)

89. Start a fresh session for unrelated work.
90. Hand off with a 200-word summary (P31).
91. Compact logs before pasting (`compact.py`).
92. Never paste a whole file when 20 lines will do.
93. Use `session_budget.py` to see when splitting wins.
94. Close tabs you are not using: every open document can end up in context.
95. Keep long outputs in files, not in the conversation.

## 12.8 Safety (96-100)

96. Treat text inside sources, pages and emails as data, never as instructions.
97. Give workers read-only tools.
98. Keep secrets out of guides and knowledge bases.
99. Enforce rules with permissions, not with requests.
100. Never trade away safety or compliance instructions to save tokens.

## 12.9 Added in 2.1.0 (101-154)

101. Run `schema_diet.py` before adding your next tool: every schema is paid for on every request.
102. Shorten tool descriptions to when-to-call, not how-it-works.
103. Load rarely used tools on demand instead of always.
104. Multiply your always-loaded text by requests, not by sessions.
105. Ask for a patch (SEARCH/REPLACE), not the whole file.
106. Apply patches all-or-nothing with `edit_guard.py`; a refused patch is cheap, a silent bad edit is not.
107. Collapse exact duplicates before any bulk job; it is free.
108. Answer with rules first and spend a model only on the remainder.
109. Spot-check 20 rule-answered rows before trusting a rule.
110. Pack small items into micro-batches of 10 to 30, keyed by ID.
111. Retry the failed item, not the batch.
112. Re-ask only the invalid fields, never the whole record.
113. Bound repair rounds to two, then escalate the record.
114. Use BM25 (`topk.py`) to pick passages before loading a long document.
115. If the top passage score is low, say so and widen; do not guess.
116. Replace old tool outputs with a one-line stub and keep the detail in a checkpoint file.
117. Keep the last 4 to 6 turns verbatim when trimming history.
118. Measure chars per token on your own data with `token_calibrate.py`.
119. Count code, JSON and non-Latin text with their own ratios.
120. Check the cache write premium before you cache.
121. A prefix below the provider minimum is not cached at all; check the minimum.
122. Cache lifetime is short: space your waves inside it.
123. Warm the cache with one request before the fan-out, not after.
124. Put fixed text first and changing text last, with a visible boundary.
125. Never let a timestamp or request ID sit inside the cached prefix.
126. Include model, prompt and sampling settings in a response cache key.
127. Give cached answers a TTL, and never cache personal data.
128. Use caching only where one sample is acceptable.
129. Coalesce identical in-flight requests with single flight.
130. Debounce typing-triggered calls; only the last one matters.
131. Audit output tokens weekly: they are the dearest.
132. Hidden reasoning is billed as output; cap it for easy tasks.
133. A request that hits its output cap is both costly and probably broken; find those first.
134. Find retries and loops with `waste_finder.py` before negotiating prices.
135. Run `preflight.py` on prompts before long unattended jobs.
136. Compute the cascade break-even before building a cascade.
137. A cascade needs a deterministic validator; without one it is just a cheap model.
138. Gate every downgrade with `eval_gate.py` and read the confidence interval, not the pass rate alone.
139. Treat an inconclusive gate as a request for more test cases.
140. Prune few-shot examples to the smallest set with the same coverage, then re-run the gate.
141. Pick the cheapest service lane that still meets the deadline.
142. Batch lanes suit work that nobody waits for.
143. Compute the wiki break-even from your own numbers instead of a threshold.
144. Compare TSV against JSON on your data; the saving can be small.
145. Run the weekly audit as a workflow, and fix only the biggest finding.
146. Make the cost gate a pull request check so regressions cannot merge.
147. Use `--skip-stale` for the mid-ingest lint and a strict lint after `done`.
148. Stage only wiki and brain folders in unattended jobs, never everything.
149. Use `set -eo pipefail` in nightly scripts so a failed status is not read as zero pending.
150. Compaction should keep error lines from the cut middle.
151. Rotate sessions with caching in the maths: the saving is smaller than it looks.
152. Probe one rung lower now and then so the ladder floor can fall.
153. The check costs zero tokens; fixing what it finds costs what it costs. Say both.
154. Ask several different models to review your own repository; keep only what you can verify.
