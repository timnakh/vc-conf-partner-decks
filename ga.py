"""GA4 visits per partner ref (vcconf.com?NNN), read with a service account.

Env: GA4_PROPERTY_ID (numeric), GA4_SA_JSON (the service-account key JSON, whole file
contents). Without them everything returns {} and the page just hides the visits column.
"""

from __future__ import annotations

import json
import os
import re
import time

_CACHE: dict = {"at": 0.0, "data": {}, "error": ""}
TTL = 3600
START = os.environ.get("GA4_START_DATE", "2026-10-01")


def configured() -> bool:
    return bool(os.environ.get("GA4_PROPERTY_ID") and os.environ.get("GA4_SA_JSON"))


def _fetch() -> dict:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
    from google.oauth2 import service_account

    info = json.loads(os.environ["GA4_SA_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{os.environ['GA4_PROPERTY_ID'].strip()}",
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        date_ranges=[DateRange(start_date=START, end_date="today")],
        limit=10000,
    )
    out: dict[str, dict] = {}
    for row in client.run_report(req).rows:
        page = row.dimension_values[0].value or ""
        m = re.search(r"\?(?:[^#]*&)?(\d{1,5})(?:[&=#]|$)", page)
        if not m:
            continue
        ref = m.group(1)
        cur = out.setdefault(ref, {"sessions": 0, "users": 0})
        cur["sessions"] += int(row.metric_values[0].value or 0)
        cur["users"] += int(row.metric_values[1].value or 0)
    return out


def visits_by_ref(force: bool = False) -> dict:
    """{ref: {"sessions": n, "users": n}}; cached for an hour."""
    if not configured():
        return {}
    if not force and time.time() - _CACHE["at"] < TTL:
        return _CACHE["data"]
    try:
        _CACHE["data"] = _fetch()
        _CACHE["error"] = ""
    except Exception as e:  # keep the page working if GA is down or misconfigured
        _CACHE["error"] = str(e)[:300]
    _CACHE["at"] = time.time()
    return _CACHE["data"]


def last_error() -> str:
    return _CACHE["error"]
