"""
SharePoint Document Connector
==============================
Crawls SharePoint sites and ingests documents into Huron's vector store.

  SHAREPOINT_MOCK_MODE=true  → reads files from backend/data/demo_sharepoint/
  SHAREPOINT_MOCK_MODE=false → calls Microsoft Graph API with client-credentials OAuth2

Both paths call IngestionService.ingest_document() so chunking/embedding is
identical regardless of source.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MOCK_MODE  = os.getenv("SHAREPOINT_MOCK_MODE", "false").lower() == "true"
_TENANT_ID  = os.getenv("AZURE_TENANT_ID", os.getenv("OIDC_AUTHORITY", "").rstrip("/").split("/")[-1])
_CLIENT_ID  = os.getenv("AZURE_CLIENT_ID", os.getenv("OIDC_CLIENT_ID", ""))
_CLIENT_SEC = os.getenv("AZURE_CLIENT_SECRET", os.getenv("OIDC_CLIENT_SECRET", ""))

_DEMO_ROOT  = Path(__file__).parent.parent / "data" / "demo_sharepoint"

# Supported extensions for ingestion
_INGEST_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".csv", ".pptx"}


# ── Graph API token (real mode) ───────────────────────────────────────────────

def _graph_token() -> str:
    url = f"https://login.microsoftonline.com/{_TENANT_ID}/oauth2/v2.0/token"
    r   = httpx.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SEC,
        "scope":         "https://graph.microsoft.com/.default",
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


# ── Real SharePoint via Graph API ─────────────────────────────────────────────

def _list_graph_files(site_id: str, token: str) -> list[dict]:
    """Return flat list of {name, download_url, dept_code} for a SharePoint site."""
    base   = "https://graph.microsoft.com/v1.0"
    files: list[dict] = []

    def _walk(drive_id: str, item_id: str, dept: str):
        url = f"{base}/drives/{drive_id}/items/{item_id}/children"
        while url:
            r    = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
            r.raise_for_status()
            data = r.json()
            for item in data.get("value", []):
                if "folder" in item:
                    _walk(drive_id, item["id"], dept)
                elif "file" in item:
                    ext = Path(item["name"]).suffix.lower()
                    if ext in _INGEST_EXTS:
                        files.append({
                            "name":         item["name"],
                            "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                            "dept_code":    dept,
                            "item_id":      item["id"],
                            "site_id":      site_id,
                        })
            url = data.get("@odata.nextLink")

    # get drives for this site
    dr = httpx.get(f"{base}/sites/{site_id}/drives",
                   headers={"Authorization": f"Bearer {token}"}, timeout=15)
    dr.raise_for_status()
    for drive in dr.json().get("value", []):
        _walk(drive["id"], "root", site_id.split(",")[1] if "," in site_id else "company")

    return files


def _download_graph_file(download_url: str) -> bytes:
    r = httpx.get(download_url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return r.content


# ── Mock mode: read local demo files ─────────────────────────────────────────

def _list_mock_files(dept_filter: str | None = None) -> list[dict]:
    files: list[dict] = []
    if not _DEMO_ROOT.exists():
        logger.warning("Demo SharePoint root not found: %s", _DEMO_ROOT)
        return files
    for dept_dir in _DEMO_ROOT.iterdir():
        if not dept_dir.is_dir():
            continue
        dept_code = dept_dir.name
        if dept_filter and dept_code != dept_filter:
            continue
        for f in dept_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in _INGEST_EXTS:
                files.append({
                    "name":      f.name,
                    "path":      str(f),
                    "dept_code": dept_code,
                })
    return files


# ── Shared ingestion logic ────────────────────────────────────────────────────

async def _ingest_file(
    name:       str,
    content:    bytes,
    dept_code:  str,
    site_name:  str,
    triggered_by: str,
) -> dict[str, Any]:
    from backend.utils.ingestion_service import IngestionService
    from backend.utils.tenant_context import TenantContext

    ctx = TenantContext(
        tenant_id="huron",
        dept_id=dept_code,
        username=triggered_by,
        role="root",
    )
    svc    = IngestionService()
    result = await svc.ingest_document(
        file_content=content,
        file_name=name,
        tenant_context=ctx,
        sensitivity_level="internal",
    )
    return {
        "file":    name,
        "dept":    dept_code,
        "site":    site_name,
        "success": result.success,
        "doc_id":  result.document_id,
        "chunks":  result.parent_chunks,
    }


# ── Public entry points ───────────────────────────────────────────────────────

async def sync_site(
    site_id: str,
    site_name: str,
    dept_code: str,
    triggered_by: str = "scheduler",
) -> dict[str, Any]:
    """
    Sync a single SharePoint site (or its mock equivalent).
    Returns a result summary suitable for storing in sharepoint_sync_log.
    """
    ingested = 0
    failed   = 0
    errors: list[str] = []
    started  = datetime.now(timezone.utc).isoformat()

    try:
        if _MOCK_MODE:
            files = _list_mock_files(dept_filter=dept_code)
        else:
            token = _graph_token()
            files = _list_graph_files(site_id, token)

        for f in files:
            try:
                if _MOCK_MODE:
                    content = Path(f["path"]).read_bytes()
                else:
                    content = _download_graph_file(f["download_url"])

                await _ingest_file(
                    name=f["name"],
                    content=content,
                    dept_code=f.get("dept_code", dept_code),
                    site_name=site_name,
                    triggered_by=triggered_by,
                )
                ingested += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{f['name']}: {exc}")
                logger.warning("Failed to ingest %s: %s", f["name"], exc)

    except Exception as exc:
        errors.append(f"Site fetch failed: {exc}")
        logger.exception("SharePoint sync error for site %s: %s", site_id, exc)

    finished = datetime.now(timezone.utc).isoformat()
    return {
        "site_id":      site_id,
        "site_name":    site_name,
        "dept_code":    dept_code,
        "ingested":     ingested,
        "failed":       failed,
        "errors":       errors,
        "started_at":   started,
        "finished_at":  finished,
        "status":       "success" if not errors else "partial" if ingested else "error",
    }


async def sync_all_sites(triggered_by: str = "scheduler") -> list[dict]:
    """
    Sync all registered SharePoint sites from the DB.
    Falls back to scanning all demo_sharepoint/* dirs in mock mode.
    """
    import sqlite3
    from backend.core.config import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    sites = conn.execute(
        "SELECT id, site_name, dept_code FROM sharepoint_sites WHERE is_active=1"
    ).fetchall()
    conn.close()

    if _MOCK_MODE and not sites:
        # auto-discover from demo folder structure
        if _DEMO_ROOT.exists():
            sites = [
                type("Row", (), {"id": d.name, "site_name": d.name.title(), "dept_code": d.name})()
                for d in _DEMO_ROOT.iterdir() if d.is_dir()
            ]

    results = []
    for site in sites:
        result = await sync_site(
            site_id=str(site.id if hasattr(site, "id") else site["id"]),
            site_name=site.site_name if hasattr(site, "site_name") else site["site_name"],
            dept_code=site.dept_code if hasattr(site, "dept_code") else site["dept_code"],
            triggered_by=triggered_by,
        )
        results.append(result)
    return results
