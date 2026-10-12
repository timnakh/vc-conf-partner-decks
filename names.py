"""Display names for the partner block: drop legal fluff, keep the readable core."""

from __future__ import annotations

import re

_SUFFIXES = (
    "limited liability company",
    "limited liability partnership",
    "incorporated",
    "corporation",
    "company",
    "limited",
    "l.l.c.",
    "llc",
    "l.l.p.",
    "llp",
    "ltd.",
    "ltd",
    "inc.",
    "inc",
    "corp.",
    "corp",
    "plc",
    "p.c.",
    "pc",
    "lp",
    "gmbh",
    "s.a.r.l.",
    "sarl",
    "sasu",
    "sas",
    "s.a.",
    "sa",
    "s.r.l.",
    "srl",
    "pty",
    "pte",
    "b.v.",
    "bv",
    "n.v.",
    "nv",
    "oy",
    "ab",
    "ag",
    "spa",
    "s.p.a.",
)

_SUFFIX_RE = re.compile(
    r"(?:,)?\s+(?:" + "|".join(re.escape(s) for s in _SUFFIXES) + r")\.?\s*$",
    re.I,
)
_PARENS_RE = re.compile(r"\s*\([^)]*\)\s*$")
_SPACE_RE = re.compile(r"\s+")


def normalize_company_name(raw: str) -> str:
    name = _SPACE_RE.sub(" ", (raw or "").strip())
    if not name:
        return ""
    # Keep accents; only flatten crazy whitespace / legal tails.
    for _ in range(4):
        nxt = _SUFFIX_RE.sub("", name)
        nxt = _PARENS_RE.sub("", nxt).strip(" ,-/")
        if nxt == name:
            break
        name = nxt
    name = _SPACE_RE.sub(" ", name).strip()
    return name or (raw or "").strip()


def display_name(raw: str) -> str:
    """People names pass through; company legal tails get stripped."""
    name = (raw or "").strip()
    if not name:
        return ""
    # If it looks like First Last (no legal suffix, 1–4 words, no Inc/LLC), keep.
    return normalize_company_name(name)
