-- Migration 005: SharePoint sites registry + sync log

-- ── Registered SharePoint sites ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sharepoint_sites (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name      TEXT    NOT NULL,
    site_url       TEXT,                        -- full https:// URL (blank for mock)
    graph_site_id  TEXT,                        -- Graph API siteId (blank for mock)
    dept_code      TEXT    NOT NULL,            -- maps to Huron departments
    is_active      INTEGER NOT NULL DEFAULT 1,
    last_synced_at TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (site_name)
);

-- ── SharePoint sync log ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sharepoint_sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id      TEXT    NOT NULL,
    site_name    TEXT    NOT NULL,
    dept_code    TEXT    NOT NULL,
    started_at   TEXT    NOT NULL,
    finished_at  TEXT,
    status       TEXT    NOT NULL DEFAULT 'success',  -- success | partial | error
    ingested     INTEGER NOT NULL DEFAULT 0,
    failed       INTEGER NOT NULL DEFAULT 0,
    error_detail TEXT,
    triggered_by TEXT    NOT NULL DEFAULT 'scheduler'
);

-- ── Seed demo sites (only inserted if table is empty) ────────────────────────
INSERT OR IGNORE INTO sharepoint_sites (site_name, site_url, dept_code)
VALUES
    ('HR Documents',       '', 'hr'),
    ('Legal Documents',    '', 'legal'),
    ('Clinical Documents', '', 'clinical'),
    ('Finance Documents',  '', 'finance');
