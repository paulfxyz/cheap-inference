#!/bin/bash
# Prints a SHORT briefing into context at session start: the hot cache and the
# pending-ingest list. Anything printed here is paid for in tokens, so keep it brief.
[ -f wiki/hot.md ] && { echo "--- wiki/hot.md ---"; cat wiki/hot.md; }
echo "--- pending ingest ---"
python3 tools/kb.py status 2>&1
exit 0
