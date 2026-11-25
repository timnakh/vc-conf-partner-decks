"""Live MP counts from the CRM gateway (crm.vcconf.com), cached for a few minutes.

Needs env CRM_GATEWAY_KEY (a gateway API key). Without it, counts are not available
and the calendar keeps showing the numbers from the last agent snapshot.
"""
import json
import os
import re
import time
import urllib.request

GATEWAY = os.environ.get("CRM_GATEWAY_URL", "https://crm.vcconf.com/gateway").rstrip("/")
TTL = 600  # seconds

_cache = {"at": 0.0, "data": None, "error": ""}

RANK = {"confirmed": 3, "confirmed (with condition)": 2, "interested": 1}

SQL = (
    "select lead_uid, person_key, Full_Name, Company, Primary_Role, Secondary_Roles, Status, Manager "
    "from Leads where (Primary_Role in ('Media/Newsletter','Event Supporter') "
    "or Secondary_Roles like '%Media/Newsletter%' or Secondary_Roles like '%Event Supporter%') "
    "and Status in ('confirmed','confirmed (with condition)','interested') "
    "and (Manager like '%Tim%' or Secondary_Roles like '%Media/Newsletter%') limit 5000"
)


def configured() -> bool:
    return bool(os.environ.get("CRM_GATEWAY_KEY", "").strip())


def last_error() -> str:
    return _cache["error"]


def _query(sql: str) -> list:
    key = os.environ["CRM_GATEWAY_KEY"].strip()
    req = urllib.request.Request(
        GATEWAY + "/query",
        data=json.dumps({"sql": sql}).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("rows", [])


def _company_key(company: str, name: str) -> str:
    s = (company or name or "").lower()
    s = s.split("(")[0]
    s = re.sub(r"\b(venture capital|ventures|vc)\b", "", s)
    return re.sub(r"[^a-z0-9]+", "", s) or (name or "").lower()


def mp_counts() -> dict | None:
    """{'mp_confirmed': n, 'mp_confirmed_cond': n, 'mp_interested': n} — one per partner company/person."""
    if not configured():
        return None
    now = time.time()
    if _cache["data"] is not None and now - _cache["at"] < TTL:
        return _cache["data"]
    try:
        rows = _query(SQL)
    except Exception as e:  # keep the last good numbers
        _cache["error"] = str(e)[:200]
        return _cache["data"]
    best: dict[str, tuple] = {}
    person_seen: dict[str, str] = {}
    for r in rows:
        _uid, person, name, company, _p, _s, status, _m = r
        key = _company_key(company, name)
        # the same person under two companies counts once
        if person and person in person_seen and person_seen[person] != key:
            key = person_seen[person]
        if person:
            person_seen[person] = key
        if key not in best or RANK.get(status, 0) > RANK.get(best[key][6], 0):
            best[key] = r
    statuses = [r[6] for r in best.values()]
    data = {
        "mp_confirmed": sum(s in ("confirmed", "confirmed (with condition)") for s in statuses),
        "mp_confirmed_cond": statuses.count("confirmed (with condition)"),
        "mp_interested": statuses.count("interested"),
    }
    _cache.update(at=now, data=data, error="")
    return data
