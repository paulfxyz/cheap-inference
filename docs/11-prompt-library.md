# 11. Prompt library

> Forty-two copy-paste prompts, grouped by the job they do. Each is written to be short, to constrain the output, and to avoid reading more than necessary. Replace `{braces}`.

Conventions used everywhere:

- **Constrain the output.** Output tokens are usually the most expensive. Every prompt says how long or in what shape the answer must be.
- **Name the stop condition.** "Stop at the first tier that answers" is a cost control.
- **Put stable text first.** Rules and formats come before the changing `{input}` so caching can work (chapter 8).

## 11.1 Setup and guides

**P01. Guide interview**
```text
Interview me one question at a time to write AGENTS.md: who I am, this year's goals,
how to talk to me, my projects. Wait for each answer. When done, write AGENTS.md
under 700 tokens, with a "when NOT to read the knowledge base" line.
```

**P02. Guide diet**
```text
Rewrite this guide to under {700} tokens. Keep every rule that changes behaviour.
Delete explanations of things you already know. Move reference detail into
linked files. Show a before/after token estimate.
```

**P03. Hot cache refresh**
```text
Rewrite wiki/hot.md in at most 12 lines: current focus, last change, open
questions, one "do not forget". Replace the file; do not append.
```

**P04. Project charter**
```text
Create projects/{name}/AGENTS.md: what it is, its one goal, what "done" looks like,
and the reading order (hot, index, sub-index, pages). Max 15 lines.
```

## 11.2 Ingest

**P05. Standard ingest**
```text
Run `python tools/kb.py status`. Work only on listed files. For each: read fully,
create or update pages (frontmatter: title, sources, updated), add a quote line
per concrete claim, link related pages, flag contradictions. Run lint until clean,
then `done` and `index`. Summarise in 3 sentences.
```

**P06. Contradiction hunt on ingest**
```text
For the new source {file}, list claims that contradict existing pages.
Output a table: new claim | existing page | existing claim | which is newer.
Do not edit anything.
```

**P07. Split a big source**
```text
Split {file} into single-topic notes of about 800 tokens. One H1 each, a one-line
summary first, links between neighbours. Output only the file list.
```

**P08. Source triage**
```text
Rate each file in raw/ as keep / skim / ignore for the goal "{goal}". One line each:
file | rating | 8-word reason. Do not read more than the first 40 lines of each.
```

## 11.3 Query

**P09. Tiered query**
```text
Answer using the knowledge base. Read hot.md first; stop if it answers. Otherwise
index.md, then one sub-index, then the minimum pages. Name the pages you opened.
If the answer is reusable, save it as a page with sources.
```

**P10. "Do I even need the wiki?"**
```text
Before opening anything: does this question need project-specific knowledge?
Answer YES or NO in one word. If NO, answer directly.
```

**P11. Evidence-only answer**
```text
Answer only from the pages you opened. Quote the line for each claim.
If the pages do not contain it, say "not in the knowledge base".
```

**P12. Compare two things cheaply**
```text
Compare {A} and {B} in a table with at most 6 rows. Each cell max 8 words.
Cite the page for each row.
```

## 11.4 Lint and review

**P13. Report-only audit**
```text
List contradictions, superseded claims, orphan pages and concepts that deserve
their own page. Report only, max 20 lines. Fix nothing.
```

**P14. Review a diff**
```text
Here is the git diff of the last ingest. For each changed claim, does it follow
from its quoted source? Answer per claim: OK / MISREAD / UNSUPPORTED. No prose.
```

**P15. Staleness triage**
```text
From `kb.py stale --days 90` output, mark each page: refresh / archive / fine.
One line each with a reason under 10 words.
```

**P16. Explain a lint error**
```text
Explain this lint error to a newcomer in two sentences and give the one-line fix:
{error}
```

## 11.5 Routing and effort

**P17. Pick the rung**
```text
Task: {task}. Which rung (0-5) is the lowest that can plausibly do it, and why
in one sentence? Do not do the task.
```

**P18. Failure analysis before escalating**
```text
The last attempt failed. In one sentence, name what was wrong (wrong / shallow /
missing source / too big). Then say whether climbing one rung would fix that.
```

**P19. Cheap draft, strong review**
```text
Draft: write {deliverable} in at most {300} words.
(then, on a stronger route) Review: list at most 5 concrete defects. No rewrite.
```

**P20. Decide batch vs live**
```text
Job: {job}. Does anyone wait for the result? If no, recommend batch and name
what to check on the provider's pricing page. Max 4 lines.
```

## 11.6 Fan-out

**P21. Worker brief**
```text
Read only {file}. Return exactly: Claim (1 sentence) | Quote | Where | Confidence
(high/medium/low). Max 80 words. Nothing else.
```

**P22. Synthesis from summaries**
```text
You have {n} worker summaries. Merge into 8 bullets, one per distinct claim.
Mark claims supported by 2+ sources. Do not open the sources.
```

**P23. Verifier**
```text
Fresh context. For each statement, does it follow from its cited source text?
Reply per statement: FOLLOWS / DOES NOT FOLLOW / CANNOT TELL. No explanations
unless DOES NOT FOLLOW (one sentence).
```

**P24. Disagreement finder**
```text
Across these summaries, list only the points where sources disagree.
Format: topic | source A says | source B says. Max 10 rows.
```

## 11.7 Output shaping

**P25. Force a format**
```text
Return JSON only, matching: {"title": str, "tags": [str], "summary": str<=40 words}.
No markdown fences, no commentary.
```

**P26. Hard length cap**
```text
Answer in at most {N} words. If it needs more, give the most important {N} and
list what you left out as a single line.
```

**P27. Answer first**
```text
Give the answer in the first sentence. Then at most 3 supporting bullets.
No introduction, no recap.
```

**P28. Diff, not rewrite**
```text
Return only the changed lines as a unified diff. Do not reprint unchanged text.
```

**P29. Table over prose**
```text
Return a table: item | verdict | reason (max 8 words). No text outside the table.
```

**P30. Yes/no gate**
```text
Reply only YES or NO: {condition}? If NO, stop.
```

## 11.8 Context hygiene

**P31. Session handoff summary**
```text
Summarise this session for a fresh start in at most 200 words: goal, decisions
made, files changed, open questions, next step. Nothing else.
```

**P32. Log triage**
```text
From the compacted log below, give: the first error, the likely cause, and the
one command to confirm. Max 5 lines.
```

**P33. Reduce a tool output**
```text
Extract only the fields {a, b, c} from this output as a table. Ignore the rest.
```

**P34. Trim a skill description**
```text
Rewrite this skill description to at most 40 words: what it does, the request
shapes that should load it, one adjacent request that should not.
```

## 11.9 Translation and bulk text

**P35. Bulk translation, cheap**
```text
Translate the values of this JSON into {language}. Keep keys, placeholders like
{name} and HTML tags unchanged. Return JSON only.
```

**P36. Idiom check**
```text
List strings in this translation that read as literal or untranslated.
Format: key | problem | suggested fix. Max 15 rows.
```

**P37. Classification at scale**
```text
Classify each line into exactly one of {labels}. Output: id,label per line.
No explanations.
```

## 11.10 Meta

**P38. Find waste in a prompt**
```text
Mark every sentence in this prompt that does not change the model's behaviour.
Output the prompt without them.
```

**P39. Ask for the cheaper route**
```text
Is any part of this task pure text-in/text-out that a cheaper model could do?
List those parts and keep the rest here. Max 5 lines.
```

**P40. Post-mortem**
```text
This task cost more than expected. From the transcript, list the 3 biggest
token sinks and the one change that would have avoided each.
```

**P41. Weekly savings review**
```text
From this usage report, name the top 3 groups by tokens and propose one change
per group. Each proposal: change | expected effect | risk.
```

**P42. Rule extraction from feedback**
```text
From this correction, write one rule in the form "Always/Never X when Y".
Max 20 words.
```

## 11.11 Tuning your own prompts

1. Run `python tools/prompt_lint.py your-prompts/` first: it is free.
2. Keep a before/after token count in the commit message.
3. Test on 5 real inputs, not one. A prompt that is short and wrong is not cheap.
4. Keep the version in the file name or a comment; changing a prompt invalidates cached results.

## 11.12 Added in 2.1.0 (43-54)

**P43. Patch, not rewrite**
```text
Return only SEARCH/REPLACE blocks. Each SEARCH block must quote the existing
lines exactly. Do not repeat unchanged code.
```

**P44. Batch items with IDs**
```text
For each item below return one line: ID<TAB>label. Skip items you cannot
label and write ID<TAB>?. No explanations.
```

**P45. Repair only these fields**
```text
Below are records with invalid fields only. Return JSON: {id: {field: value}}.
Do not return fields that are not listed.
```

**P46. Decide, then stop**
```text
Answer in one line, then stop. If you need more input, ask one question.
```

**P47. Quote-bounded answer**
```text
Answer using only the passages below. After each claim give the passage number.
If no passage supports it, say "not in the passages".
```

**P48. Output budget**
```text
Maximum 120 words. No introduction, no recap, no closing offer.
```

**P49. Reasoning budget**
```text
Think briefly. Do not enumerate alternatives you reject. Give the answer first.
```

**P50. Checkpoint**
```text
Summarise the work so far as: decisions made | open questions | next step |
files touched. Max 12 lines. This replaces the history.
```

**P51. Tool diet review**
```text
Here are my tool descriptions. Rewrite each to at most 20 words that still
tell you when to call it. Keep the parameter names unchanged.
```

**P52. Example selection**
```text
From these 10 examples choose the 3 that together cover the most different
cases. Say which case each one covers.
```

**P53. Escalation note**
```text
You could not finish. In 5 lines say what you tried, what blocked you, and the
smallest extra input that would let a cheaper retry succeed.
```

**P54. Cache-friendly layout**
```text
Rewrite this prompt so the fixed text comes first and the changing text comes
last, with one clear boundary line between them. Do not change the wording.
```
