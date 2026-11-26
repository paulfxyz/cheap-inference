---
name: ingest
description: Compile new or changed files from raw/ into wiki pages. Use when the user says ingest, or when kb.py status lists pending files.
disable-model-invocation: true
---
1. Run `python tools/kb.py status`. Work ONLY on the files it lists.
2. Read each raw file fully, then create or update wiki pages.
3. Frontmatter on every page: title, sources, updated (YYYY-MM-DD).
4. Every concrete claim gets a quote line:  > "exact text" - raw/<file>
5. Link related pages with [[page-name]]. No orphans.
6. Run `python tools/kb.py lint` until it exits 0.
7. Run `python tools/kb.py done <raw file> <pages...>` then `python tools/kb.py index`.
8. Commit: `git add -A && git commit -m "ingest <source>"`.
