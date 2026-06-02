-- ─────────────────────────────────────────────────────────────────────────────
-- Migration 003: SSO / OIDC support
-- ─────────────────────────────────────────────────────────────────────────────

-- Track which auth method each user account uses
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_method TEXT NOT NULL DEFAULT 'local';
-- Values: 'local' (username/password), 'oidc' (Azure AD / Okta SSO)

-- Map Azure AD / Okta group IDs → Huron roles and departments
CREATE TABLE IF NOT EXISTS oidc_role_mappings (
    id          SERIAL PRIMARY KEY,
    provider    TEXT NOT NULL DEFAULT 'azure',
    ad_group    TEXT NOT NULL,
    huron_role  TEXT NOT NULL,
    dept_code   TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, ad_group)
);

CREATE INDEX IF NOT EXISTS idx_oidc_role_mappings_group
    ON oidc_role_mappings(provider, ad_group);

-- ── Example mappings (replace group IDs with real Azure Object IDs) ───────────
-- INSERT INTO oidc_role_mappings (provider, ad_group, huron_role, dept_code, description)
-- VALUES
--   ('azure', '<HR-Team-Group-ObjectID>',      'user',       'hr',       'HR department users'),
--   ('azure', '<HR-Managers-Group-ObjectID>',  'dept_admin', 'hr',       'HR managers'),
--   ('azure', '<Legal-Team-Group-ObjectID>',   'user',       'legal',    'Legal department'),
--   ('azure', '<Finance-Team-Group-ObjectID>', 'user',       'finance',  'Finance department'),
--   ('azure', '<Clinical-Group-ObjectID>',     'user',       'clinical', 'Clinical team'),
--   ('azure', '<IT-Team-Group-ObjectID>',      'dept_admin', 'it',       'IT engineers'),
--   ('azure', '<Huron-Admins-ObjectID>',       'root',       NULL,       'System administrators'),
--   ('okta',  '<Okta-HR-Group-Name>',          'user',       'hr',       'HR via Okta');
