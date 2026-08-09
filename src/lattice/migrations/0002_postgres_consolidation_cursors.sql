-- 0002_postgres_consolidation_cursors — immutable company-scoped consolidation watermarks.
-- Applied by the host application's migration runner; do not edit after deployment.

CREATE TABLE lattice_consolidation_cursor (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    last_run_id text NOT NULL,
    episodes_seen integer NOT NULL CHECK (episodes_seen >= 0),
    consolidated_at timestamptz NOT NULL,
    PRIMARY KEY (company_id, employee_id)
);

ALTER TABLE lattice_consolidation_cursor ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_consolidation_cursor FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_consolidation_cursor_company_isolation ON lattice_consolidation_cursor
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));
