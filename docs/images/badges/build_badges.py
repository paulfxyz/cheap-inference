#!/usr/bin/env python3
"""
build_badges.py - generate the README badges as local SVG files.

WHY LOCAL BADGES
----------------
Badges fetched from a third-party service (and then proxied by GitHub's image
cache) can fail to load for reasons that have nothing to do with this repo:
rate limits, slow first fetches, outages. Files committed to the repository
cannot go offline. The trade-off: they do not update by themselves, so rerun
this script when a number changes (version, tools, tests...).

USAGE
    python docs/images/badges/build_badges.py
Standard library only. Output: one .svg per badge, next to this script.
"""
from __future__ import annotations

import pathlib

OR, DK, GREY = "#DA552F", "#1D1814", "#555"
CHAR_W = 7.9   # approximate advance of one uppercase glyph + letter-spacing at 10px
PAD = 12       # horizontal padding inside each half

# (file name, label, message, message colour)
BADGES = [
    ("tests", "tests", "89 in CI", OR),
    ("licence", "licence", "MIT", DK),
    ("version", "version", "2.1.0", DK),
    ("python", "python", "3.10+", OR),
    ("dependencies", "dependencies", "0", DK),
    ("tokens", "tokens spent on checks", "0", OR),
    ("tools", "tools", "34", DK),
    ("prompts", "prompts", "54", OR),
    ("tips", "tips", "154", DK),
    ("release", "release", "v2.1.0", OR),
    ("star", "github", "star it", DK),
]


def width(text: str) -> float:
    """Estimated pixel width of the uppercase text plus its padding."""
    return len(text) * CHAR_W + PAD * 2


def svg(label: str, message: str, colour: str) -> str:
    """Return a 'for-the-badge' style SVG: grey label half, coloured message half."""
    lw, mw = width(label), width(message)
    total = lw + mw
    esc = lambda s: s.upper().replace("&", "&amp;").replace("<", "&lt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.0f}" height="28" role="img" '
        f'aria-label="{esc(label)}: {esc(message)}"><title>{esc(label)}: {esc(message)}</title>'
        f'<g shape-rendering="crispEdges"><rect width="{lw:.0f}" height="28" fill="{GREY}"/>'
        f'<rect x="{lw:.0f}" width="{mw:.0f}" height="28" fill="{colour}"/></g>'
        f'<g fill="#fff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="10" letter-spacing="1" text-anchor="middle">'
        f'<text x="{lw/2:.1f}" y="17.5">{esc(label)}</text>'
        f'<text x="{lw + mw/2:.1f}" y="17.5" font-weight="bold">{esc(message)}</text></g></svg>\n'
    )


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    for name, label, message, colour in BADGES:
        (here / f"{name}.svg").write_text(svg(label, message, colour), encoding="utf-8")
    print(f"wrote {len(BADGES)} badges to {here}")
