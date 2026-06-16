-- Migration 004: Workday sync log + workday columns on users table
-- Safe to run multiple times (IF NOT EXISTS / ADD COLUMN guards)

-- ── Workday sync log ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workday_sync_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at          TEXT    NOT NULL,
    finished_at         TEXT,
    status              TEXT    NOT NULL DEFAULT 'success',  -- success | error
    records_created     INTEGER NOT NULL DEFAULT 0,
    records_updated     INTEGER NOT NULL DEFAULT 0,
    records_deactivated INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    triggered_by        TEXT    NOT NULL DEFAULT 'scheduler'  -- scheduler | manual_api | migration
);

-- ── Workday identity columns on users (IF NOT EXISTS via a try) ───────────────
-- SQLite does not support ADD COLUMN IF NOT EXISTS, so we use separate statements.
-- The migration runner should ignore "duplicate column name" errors for these.
ALTER TABLE users ADD COLUMN workday_id   TEXT;
ALTER TABLE users ADD COLUMN employee_id  TEXT;
