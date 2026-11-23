"""Speaker lineup for media-partner posts.

Edit this list to change who is named. Posts read it; the post copy does not
hardcode names. `role` is the job title. `note` is an optional extra inside
the newsletter parenthesis (Justin Stebbins → Northgate, $5B+ AUM). LinkedIn
lines use `fund` only. `top` marks the five named in posts 1, 3 and 4.
Post 2 names everyone, in this order.
"""

from __future__ import annotations

SPEAKERS: list[dict] = [
    {"name": "David Cohen", "role": "", "fund": "Techstars", "top": True},
    {"name": "Carolin Wais", "role": "", "fund": "Plug and Play", "top": True},
    {"name": "Ray Wu", "role": "", "fund": "Alumni Ventures", "top": True},
    {"name": "Amit Patel", "role": "", "fund": "Owl Ventures", "top": True},
    {"name": "Edward Keelan", "role": "", "fund": "Octopus Ventures", "top": False},
    {"name": "Yaron Valler", "role": "", "fund": "Target Global", "top": False},
    {"name": "Haley Bryant", "role": "", "fund": "Hustle Fund", "top": True},
    {"name": "Justin Stebbins", "role": "", "fund": "Northgate", "note": "$5B+ AUM", "top": False},
]


def _rows(post: int) -> list[dict]:
    if post == 2:
        return list(SPEAKERS)
    return [s for s in SPEAKERS if s.get("top")]


def _paren(row: dict) -> str:
    fund = (row.get("fund") or "").strip()
    note = (row.get("note") or "").strip()
    inside = f"{fund}, {note}" if note else fund
    return f"{row['name']} ({inside})"


def _and(items) -> str:
    parts = [p for p in items if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _amp(items) -> str:
    parts = [p for p in items if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} & {parts[1]}"
    return ", ".join(parts[:-1]) + " & " + parts[-1]


def _lead_and_funds(rows: list[dict]) -> str:
    if not rows:
        return ""
    if len(rows) == 1:
        return _paren(rows[0])
    return _paren(rows[0]) + ", " + _and(s["fund"] for s in rows[1:])


def for_post(post: int, kind: str) -> str:
    """Fill a speaker slot. kind is names, funds, or stage.

    Posts 1, 3 and 4 name everyone flagged top. Post 2 names the full list.
    """
    rows = _rows(post)
    if kind == "names":
        return _and(_paren(s) for s in rows)
    if kind == "stage":
        return _lead_and_funds(rows)
    if kind == "funds" and post == 2:
        return ", ".join(s["fund"] for s in rows)
    if kind == "funds" and post == 4:
        return _amp(s["fund"] for s in rows)
    if kind == "funds":
        return _and(s["fund"] for s in rows)
    raise ValueError(f"unknown speaker phrase: post {post} {kind}")
