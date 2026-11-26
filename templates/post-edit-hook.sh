#!/bin/bash
# Run after every file edit by an agent that supports post-tool hooks.
# Reads the hook payload on stdin, extracts the edited path with jq, and lints
# the knowledge base only when a wiki page changed.
# Exit code 2 sends the stderr text back to the model so it can fix the page in the same turn.
f=$(jq -r '.tool_input.file_path // empty')
case "$f" in
  */wiki/*) python3 tools/kb.py lint >&2 || exit 2 ;;
esac
exit 0
