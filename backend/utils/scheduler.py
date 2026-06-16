"""
APScheduler background jobs for Huron.

Jobs:
  workday_nightly_sync   — 02:00 UTC daily   (Workday employee sync)
  sharepoint_weekly_sync — 03:00 UTC Sundays  (SharePoint document ingestion)

Import register_jobs() and call it from the FastAPI lifespan startup hook.
"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ── Job implementations ───────────────────────────────────────────────────────

def _workday_sync_job():
    """Sync Workday employees.  Runs synchronously — APScheduler calls it in a thread."""
    try:
        from backend.utils.workday_sync import run_sync
        result = run_sync(triggered_by="apscheduler")
        logger.info("Workday nightly sync: %s", result)
    except Exception:
        logger.exception("Workday nightly sync job failed")


async def _sharepoint_sync_job():
    """Sync SharePoint documents.  Async job run directly on the event loop."""
    try:
        from backend.utils.sharepoint_connector import sync_all_sites
        results = await sync_all_sites(triggered_by="apscheduler")
        logger.info("SharePoint weekly sync: %d sites processed", len(results))
        for r in results:
            logger.info("  Site %s (%s): ingested=%d failed=%d",
                        r["site_name"], r["dept_code"], r["ingested"], r["failed"])
    except Exception:
        logger.exception("SharePoint weekly sync job failed")


# ── Public API ────────────────────────────────────────────────────────────────

def register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Attach all background jobs to the provided scheduler instance."""
    scheduler.add_job(
        _workday_sync_job,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="workday_nightly_sync",
        name="Workday nightly employee sync",
        replace_existing=True,
        misfire_grace_time=1800,  # retry up to 30 min after missed fire
    )
    scheduler.add_job(
        _sharepoint_sync_job,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
        id="sharepoint_weekly_sync",
        name="SharePoint weekly document ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduler jobs registered: workday_nightly_sync, sharepoint_weekly_sync")


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance, creating it if necessary."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> AsyncIOScheduler:
    """Create, configure, and start the scheduler.  Call once at startup."""
    sched = get_scheduler()
    register_jobs(sched)
    sched.start()
    logger.info("APScheduler started")
    return sched


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler.  Call once at shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    _scheduler = None
