"""
Workday Employee Sync
=====================
Syncs employee records into the Huron users table.

  WORKDAY_MOCK_MODE=true  → reads backend/data/demo_workday_workers.json
  WORKDAY_MOCK_MODE=false → calls real Workday REST v1 with client-credentials OAuth2

Both paths share the same _process_workers() normalisation so behaviour is
identical; only the data source differs.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MOCK_DATA = Path(__file__).parent.parent / "data" / "demo_workday_workers.json"

# ── env ──────────────────────────────────────────────────────────────────────
_MOCK_MODE    = os.getenv("WORKDAY_MOCK_MODE", "false").lower() == "true"
_BASE_URL     = os.getenv("WORKDAY_BASE_URL", "")
_TENANT       = os.getenv("WORKDAY_TENANT", "")
_CLIENT_ID    = os.getenv("WORKDAY_CLIENT_ID", "")
_CLIENT_SEC   = os.getenv("WORKDAY_CLIENT_SECRET", "")

# ── dept_code → Huron dept lookup ────────────────────────────────────────────
_DEPT_MAP: dict[str, str] = {
    "hr":        "hr",
    "human resources": "hr",
    "clinical":  "clinical",
    "clinical operations": "clinical",
    "finance":   "finance",
    "legal":     "legal",
    "it":        "it",
    "information technology": "it",
    "marketing": "marketing",
    "operations": "operations",
    "company":   "company",
}


# ── Workday OAuth2 (real mode only) ──────────────────────────────────────────

def _workday_token() -> str:
    token_url = f"{_BASE_URL.rstrip('/')}/ccx/oauth2/{_TENANT}/token"
    r = httpx.post(
        token_url,
        data={"grant_type": "client_credentials"},
        auth=(_CLIENT_ID, _CLIENT_SEC),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _fetch_real_workers() -> list[dict]:
    token = _workday_token()
    url   = (
        f"{_BASE_URL.rstrip('/')}/ccx/api/v1/{_TENANT}/workers"
        "?format=json&limit=200&offset=0"
    )
    workers: list[dict] = []
    while url:
        r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        r.raise_for_status()
        data    = r.json()
        workers.extend(data.get("data", []))
        url      = data.get("next", {}).get("href") if data.get("next") else None
    return workers


def _normalise_real(w: dict) -> dict:
    """Map Workday REST v1 fields to our internal shape."""
    person   = w.get("person", {})
    name     = person.get("preferredName", {})
    dept_raw = w.get("primaryJob", {}).get("businessSite", {}).get(
        "descriptor", ""
    ).lower()
    dept_code = _DEPT_MAP.get(dept_raw, "company")
    return {
        "workday_id":        w.get("id", ""),
        "employee_id":       w.get("employeeID", ""),
        "first_name":        name.get("firstName", ""),
        "last_name":         name.get("lastName", ""),
        "email":             person.get("primaryEmail", ""),
        "title":             w.get("primaryJob", {}).get("businessTitle", ""),
        "dept_code":         dept_code,
        "employment_status": w.get("activeStatus", "Active"),
        "termination_date":  w.get("terminationDate", None),
        "hire_date":         w.get("hireDate", ""),
    }


# ── Core processing (shared by both modes) ───────────────────────────────────

def _process_workers(
    conn: sqlite3.Connection,
    workers_raw: list[dict],
    *,
    mock: bool,
) -> dict[str, int]:
    created = updated = deactivated = 0

    for w in workers_raw:
        if mock:
            rec = w                       # already in our shape
        else:
            rec = _normalise_real(w)

        email  = (rec.get("email") or "").strip().lower()
        if not email:
            continue

        dept_raw  = (rec.get("dept_code") or rec.get("department", "")).strip().lower()
        dept_code = _DEPT_MAP.get(dept_raw, "company")
        full_name = f"{rec.get('first_name', '')} {rec.get('last_name', '')}".strip()
        active    = rec.get("employment_status", "Active") == "Active"

        existing = conn.execute(
            "SELECT id, is_active FROM users WHERE LOWER(email) = ?", (email,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE users SET full_name=?, department=?, is_active=?,
                   workday_id=?, employee_id=? WHERE id=?""",
                (
                    full_name,
                    dept_code,
                    1 if active else 0,
                    rec.get("workday_id"),
                    rec.get("employee_id"),
                    existing["id"],
                ),
            )
            if not active and existing["is_active"]:
                deactivated += 1
            else:
                updated += 1
        else:
            if not active:
                continue  # don't provision terminated employees who never existed
            username = email.split("@")[0]
            conn.execute(
                """INSERT INTO users
                   (username, email, full_name, password_hash, role, department,
                    is_active, auth_method, created_by, workday_id, employee_id)
                   VALUES (?, ?, ?, '', 'user', ?, 1, 'workday', 'workday_sync', ?, ?)""",
                (username, email, full_name, dept_code,
                 rec.get("workday_id"), rec.get("employee_id")),
            )
            created += 1

    conn.commit()
    return {"created": created, "updated": updated, "deactivated": deactivated}


# ── Public entry points ───────────────────────────────────────────────────────

def run_sync(db_path: str | None = None, triggered_by: str = "scheduler") -> dict:
    """
    Execute a full Workday sync.  Returns a summary dict.
    Writes a row to workday_sync_log on completion.
    """
    from backend.core.config import DB_PATH

    conn_path = db_path or str(DB_PATH)
    conn      = sqlite3.connect(conn_path)
    conn.row_factory = sqlite3.Row

    started = datetime.now(timezone.utc).isoformat()
    status  = "success"
    summary: dict[str, Any] = {}
    error   = ""

    try:
        if _MOCK_MODE:
            logger.info("Workday sync: MOCK mode — loading %s", _MOCK_DATA)
            workers_raw = json.loads(_MOCK_DATA.read_text())
        else:
            logger.info("Workday sync: LIVE mode — fetching from %s", _BASE_URL)
            workers_raw = _fetch_real_workers()

        summary = _process_workers(conn, workers_raw, mock=_MOCK_MODE)
        logger.info("Workday sync complete: %s", summary)
    except Exception as exc:
        status = "error"
        error  = str(exc)
        logger.exception("Workday sync failed: %s", exc)
    finally:
        finished = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """INSERT INTO workday_sync_log
                   (started_at, finished_at, status, records_created,
                    records_updated, records_deactivated, error_message, triggered_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    started, finished, status,
                    summary.get("created", 0),
                    summary.get("updated", 0),
                    summary.get("deactivated", 0),
                    error,
                    triggered_by,
                ),
            )
            conn.commit()
        except Exception:
            logger.exception("Could not write sync log row")
        conn.close()

    return {"status": status, "summary": summary, "error": error,
            "started_at": started, "finished_at": finished}
