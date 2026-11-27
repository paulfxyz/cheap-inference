"""Shared helpers for the workflow scripts: make `tools/` importable and print markdown sections.

Workflows are thin ORCHESTRATORS: each one chains several single-purpose tools from tools/
into a repeatable routine and writes a short Markdown report. They contain no new logic of
their own beyond wiring, so every number in a report can be traced to one tool.
"""
import io
import pathlib
import contextlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def capture(fn, *args) -> str:
    """Run a tool's main(argv) and return what it printed (stdout), ignoring its exit code."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            fn(list(args))
        except SystemExit:
            pass
    return buf.getvalue().rstrip()


def section(title: str, body: str) -> str:
    """One Markdown section with the tool output in a code block."""
    return f"## {title}\n\n```\n{body or '(no output)'}\n```\n"
