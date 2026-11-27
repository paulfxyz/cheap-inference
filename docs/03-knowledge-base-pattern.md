# 3. The LLM-maintained knowledge base

> Goal: understand the folder layout, the three operations, and why a model should do the bookkeeping that humans abandon.

## 3.1 The problem with starting cold

Every new session starts without memory of the last. You re-explain the project, the decisions, the people, what you tried. A common workaround is retrieval over raw files: for each question, find fragments and let the model rediscover the answer. It works, but nothing accumulates, and the same synthesis is paid for again each time.

The alternative is to let the model build a small set of linked, plain-text pages that capture what it learned, and to read those pages first next time. Synthesis is paid for once, at ingest, and then reused.

## 3.2 Why a model does the maintenance

People stop maintaining wikis because upkeep grows faster than value: every new source should touch a dozen pages, every claim should be cross-referenced, every contradiction reconciled. A model does not get bored and can edit fifteen files in one pass. It does still drop links, invent pages and skip contradictions, which is exactly why the checks in chapter 4 exist; treat unattended ingest as something to review, not to trust. The cost is tokens, which is exactly why the rest of this repository exists: keep the model's work small, incremental and checked by code.

## 3.3 Layout

```
knowledge/
├── raw/                  sources: articles, notes, exports (humans add; model reads, never edits)
├── wiki/
│   ├── index.md          one line per page (generated)
│   ├── hot.md            short cache of what matters now
│   └── <topic>.md        pages the model writes and maintains
├── .brain/manifest.json  which raw file was ingested into which pages, at which hash
├── AGENTS.md             rules for the model (conventions, workflows, cost rules)
└── tools/kb.py           the deterministic checker
```

A complete working example is in [`examples/sample-kb`](../examples/sample-kb), and a deliberately broken one in [`examples/broken-kb`](../examples/broken-kb).

## 3.4 The three operations

| Operation | Trigger | What happens | Cost driver |
| --- | --- | --- | --- |
| Ingest | New or changed file in `raw/` | Model reads the source and updates 5 to 15 pages | Size of the changed source only |
| Query | A question | Model walks the tiers, answers, may save a good answer as a new page | Tiers opened |
| Lint | After every edit, and on a schedule | Script checks structure, links, quotes, staleness | Zero tokens |

## 3.5 Page format

Every content page carries frontmatter and linked, quoted claims:

```markdown
---
title: Memex and associative trails
sources: raw/memex.md
updated: 2026-11-20
---
# Memex

An early idea for linking documents. See [[associative-trails]].

> "The essential feature of the memex is the association of ideas" - raw/memex.md
```

The quote line is the key trust device: each hard claim is accompanied by the exact words from the source it came from, and a script (not a model) verifies the words really appear there. See chapter 4.

## 3.6 Naming rules that decide whether it survives

1. One file, one topic.
2. Name the file for what it contains, lower-case with hyphens.
3. Link generously with `[[page-name]]`; an unlinked page is lost.
4. Dates are ISO (`YYYY-MM-DD`).
5. Never let a page become a diary. Diaries go in `log.md`, which is exempt from content rules.

## 3.7 Per-project folders

For project work, add a small folder per project with four parts, plus its own guide that says what the project is, its single goal and what "done" looks like:

```
projects/launch/
├── inputs/      what you were given
├── process/     notes while working
├── outputs/     deliverables
└── feedback/    corrections and decisions
```

Feedback is the part people skip and the part that makes the next run better.

## 3.8 Prompts that work

These are plain-language starting points; adapt freely.

**Setup interview** (write the guide by asking you questions):

```text
You are setting up my knowledge base. Interview me one question at a time about
who I am and what I do, my goals this year, how I want you to communicate, and
my current projects. Wait for each answer. When finished, write everything into
AGENTS.md with clear headers.
```

**Ingest**:

```text
Run `python tools/kb.py status`. For each listed file, read it fully, create or
update wiki pages, add a quote line for each concrete claim, link related pages,
flag contradictions with existing pages, then run `python tools/kb.py lint`
until it passes. Summarise what changed in three sentences.
```

**Query**:

```text
Read wiki/hot.md first. Open only the pages you need and name them in your
answer. If the answer is worth keeping, save it as a new page with sources.
```

**Lint review (report only)**:

```text
Report contradictions, claims a newer source has superseded, orphan pages and
concepts mentioned in several places without a page of their own. Fix nothing yet.
```

## 3.9 When not to build one

Earlier versions of this guide said "below roughly 50 to 100 sources, don't bother". Reviewers rightly called that arbitrary: source COUNT predicts neither cost nor value. Ten dense specifications queried 500 times a month can justify a wiki; two thousand rarely-read notes cannot. Use arithmetic instead:

```bash
python tools/wiki_roi.py --questions 200 --raw-per-q 6000 --wiki-per-q 1500 --changed 20 --ingest 12000
```

It compares monthly tokens with and without a wiki and prints the break-even number of questions. The inputs are your own measurements; `kb.py stats` still prints a `dead_zone` flag below 50 sources, as a prompt to run the calculation, not as a verdict.
