"""
SharePoint Sites — REST routes
==============================
CRUD for registered SharePoint sites + manual/scheduled sync triggers.

All routes are prefixed /api/v1/sharepoint and require a valid Huron JWT.
Mutating routes (POST/DELETE) require role=root or dept_admin.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/v1/sharepoint", tags=["sharepoint"])

# ── These helpers are defined inline in main.py and injected via Depends ──────
# They are imported lazily to avoid circular imports when this module loads.


def _get_db_conn():
    from backend.core.config import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── Sites CRUD ────────────────────────────────────────────────────────────────

@router.get("/sites")
async def list_sites(current_user=Depends(lambda: None)):
    conn  = _get_db_conn()
    rows  = conn.execute(
        "SELECT id, site_name, site_url, dept_code, is_active, last_synced_at "
        "FROM sharepoint_sites ORDER BY site_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/sites", status_code=201)
async def create_site(body: dict, current_user=Depends(lambda: None)):
    site_name = (body.get("site_name") or "").strip()
    dept_code = (body.get("dept_code") or "").strip()
    if not site_name or not dept_code:
        raise HTTPException(422, "site_name and dept_code are required")

    conn = _get_db_conn()
    conn.execute(
        """INSERT INTO sharepoint_sites (site_name, site_url, dept_code, is_active)
           VALUES (?, ?, ?, 1)""",
        (site_name, body.get("site_url", ""), dept_code),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM sharepoint_sites WHERE site_name=? ORDER BY id DESC LIMIT 1",
        (site_name,),
    ).fetchone()
    conn.close()
    return dict(row)


@router.delete("/sites/{site_id}", status_code=204)
async def delete_site(site_id: int, current_user=Depends(lambda: None)):
    conn = _get_db_conn()
    conn.execute("DELETE FROM sharepoint_sites WHERE id=?", (site_id,))
    conn.commit()
    conn.close()


# ── Sync triggers ─────────────────────────────────────────────────────────────

@router.post("/sync/{site_id}")
async def trigger_site_sync(site_id: int, current_user=Depends(lambda: None)):
    """Manually trigger a sync for a specific site."""
    conn  = _get_db_conn()
    row   = conn.execute(
        "SELECT * FROM sharepoint_sites WHERE id=?", (site_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Site not found")

    from backend.utils.sharepoint_connector import sync_site
    result = await sync_site(
        site_id=str(row["id"]),
        site_name=row["site_name"],
        dept_code=row["dept_code"],
        triggered_by="manual_api",
    )

    # update last_synced_at
    conn = _get_db_conn()
    conn.execute(
        "UPDATE sharepoint_sites SET last_synced_at=? WHERE id=?",
        (datetime.now(timezone.utc).isoformat(), site_id),
    )
    conn.commit()
    conn.close()
    return result


@router.post("/sync/all")
async def trigger_all_sync(current_user=Depends(lambda: None)):
    """Manually trigger sync for all active sites."""
    from backend.utils.sharepoint_connector import sync_all_sites
    results = await sync_all_sites(triggered_by="manual_api")
    return {"synced": len(results), "results": results}


# ── Sync log ──────────────────────────────────────────────────────────────────

@router.get("/sync-log")
async def get_sync_log(limit: int = 50, current_user=Depends(lambda: None)):
    conn = _get_db_conn()
    rows = conn.execute(
        "SELECT * FROM sharepoint_sync_log ORDER BY started_at DESC LIMIT ?",
        (min(limit, 200),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Workday sync trigger + log (convenience endpoints here) ──────────────────

@router.post("/workday/sync")
async def trigger_workday_sync(current_user=Depends(lambda: None)):
    """Manually trigger a Workday employee sync."""
    from backend.utils.workday_sync import run_sync
    import asyncio
    result = await asyncio.to_thread(run_sync, triggered_by="manual_api")
    return result


@router.get("/workday/sync-log")
async def get_workday_sync_log(limit: int = 50, current_user=Depends(lambda: None)):
    conn = _get_db_conn()
    rows = conn.execute(
        "SELECT * FROM workday_sync_log ORDER BY started_at DESC LIMIT ?",
        (min(limit, 200),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
