"""Neon Postgres pool. Cold start can take a few seconds; retry on wake."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS partner (
  id SERIAL PRIMARY KEY,
  company TEXT NOT NULL,
  code TEXT NOT NULL DEFAULT '',
  reg_url TEXT NOT NULL DEFAULT '',
  notion_page_url TEXT NOT NULL DEFAULT '',
  posting_dates_raw TEXT NOT NULL DEFAULT '',
  first_post_date TEXT NOT NULL DEFAULT '',
  confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS partner_notion_url_uidx
  ON partner (notion_page_url) WHERE notion_page_url <> '';
CREATE INDEX IF NOT EXISTS partner_company_idx ON partner (lower(company));

CREATE TABLE IF NOT EXISTS publication (
  id SERIAL PRIMARY KEY,
  partner_id INTEGER NOT NULL REFERENCES partner(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('newsletter', 'linkedin', 'other')),
  post_number INTEGER NOT NULL CHECK (post_number BETWEEN 1 AND 4),
  status TEXT NOT NULL DEFAULT 'planned'
    CHECK (status IN ('planned', 'reminded', 'published', 'missed', 'rescheduled')),
  needs_check BOOLEAN NOT NULL DEFAULT FALSE,
  url TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  reminded_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS publication_partner_idx ON publication (partner_id);
CREATE INDEX IF NOT EXISTS publication_date_idx ON publication (date);

ALTER TABLE partner ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS publication_change (
  id SERIAL PRIMARY KEY,
  publication_id INTEGER REFERENCES publication(id) ON DELETE SET NULL,
  partner_id INTEGER NOT NULL REFERENCES partner(id) ON DELETE CASCADE,
  field TEXT NOT NULL,
  old_value TEXT NOT NULL DEFAULT '',
  new_value TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS publication_change_pub_idx ON publication_change (publication_id);
CREATE INDEX IF NOT EXISTS publication_change_partner_idx ON publication_change (partner_id);

CREATE TABLE IF NOT EXISTS digest_log (
  sent_on DATE PRIMARY KEY,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telegram_action (
  token TEXT PRIMARY KEY,
  pub_ids TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telegram_wait (
  chat_id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_POOL = None
_SCHEMA_OK = False
MISSING = (
    "Нет DATABASE_URL. В Render → Environment вставь pooled-строку Neon "
    "(sslmode=require). Диск Render не держит данные."
)


def configured() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


def _conninfo() -> str:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError(MISSING)
    return raw


def _pool():
    global _POOL
    if _POOL is not None:
        return _POOL
    from psycopg_pool import ConnectionPool

    _POOL = ConnectionPool(
        conninfo=_conninfo(),
        min_size=0,
        max_size=4,
        timeout=60,
        max_waiting=8,
        kwargs={"connect_timeout": 20, "keepalives": 1, "keepalives_idle": 30},
        open=False,
    )
    last = None
    for i in range(5):
        try:
            _POOL.open()
            break
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    else:
        _POOL = None
        raise RuntimeError(f"Neon не открылся: {last}") from last
    return _POOL


def _ensure_schema() -> None:
    global _SCHEMA_OK
    if _SCHEMA_OK:
        return
    with _pool().connection() as conn:
        conn.execute(SCHEMA)
        conn.commit()
    _SCHEMA_OK = True


@contextmanager
def connect():
    global _SCHEMA_OK
    if not configured():
        raise RuntimeError(MISSING)
    last = None
    for i in range(5):
        try:
            with _pool().connection() as conn:
                if not _SCHEMA_OK:
                    conn.execute(SCHEMA)
                    conn.commit()
                    _SCHEMA_OK = True
                yield conn
                return
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Neon не отвечает: {last}") from last
