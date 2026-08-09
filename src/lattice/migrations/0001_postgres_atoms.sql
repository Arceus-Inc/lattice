-- 0001_postgres_atoms — immutable semantic-atom head rows and revision history.
-- Applied by the host application's migration runner; do not edit after deployment.

CREATE TABLE lattice_atom (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    value text NOT NULL,
    created_at timestamptz NOT NULL,
    invalid_at timestamptz,
    activation double precision NOT NULL,
    alpha_own double precision,
    beta_own double precision,
    tier text,
    version integer NOT NULL DEFAULT 1,
    PRIMARY KEY (company_id, employee_id, key),
    CHECK (
        (alpha_own IS NULL AND beta_own IS NULL AND tier IS NULL)
        OR (alpha_own IS NOT NULL AND beta_own IS NOT NULL AND tier IN ('hint', 'rule'))
    )
);

ALTER TABLE lattice_atom ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_company_isolation ON lattice_atom
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));
CREATE INDEX lattice_atom_active_idx
    ON lattice_atom (company_id, employee_id, created_at DESC, key)
    WHERE invalid_at IS NULL;

CREATE TABLE lattice_atom_source_run (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    position integer NOT NULL,
    run_id text NOT NULL,
    PRIMARY KEY (company_id, employee_id, key, position),
    FOREIGN KEY (company_id, employee_id, key)
        REFERENCES lattice_atom (company_id, employee_id, key) ON DELETE CASCADE
);

ALTER TABLE lattice_atom_source_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_source_run FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_source_run_company_isolation ON lattice_atom_source_run
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE TABLE lattice_atom_key_file (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    position integer NOT NULL,
    path text NOT NULL,
    PRIMARY KEY (company_id, employee_id, key, position),
    FOREIGN KEY (company_id, employee_id, key)
        REFERENCES lattice_atom (company_id, employee_id, key) ON DELETE CASCADE
);

ALTER TABLE lattice_atom_key_file ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_key_file FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_key_file_company_isolation ON lattice_atom_key_file
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE TABLE lattice_atom_revision (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    version integer NOT NULL,
    value text NOT NULL,
    created_at timestamptz NOT NULL,
    invalid_at timestamptz,
    activation double precision NOT NULL,
    alpha_own double precision,
    beta_own double precision,
    tier text,
    PRIMARY KEY (company_id, employee_id, key, version),
    FOREIGN KEY (company_id, employee_id, key)
        REFERENCES lattice_atom (company_id, employee_id, key),
    CHECK (
        (alpha_own IS NULL AND beta_own IS NULL AND tier IS NULL)
        OR (alpha_own IS NOT NULL AND beta_own IS NOT NULL AND tier IN ('hint', 'rule'))
    )
);

ALTER TABLE lattice_atom_revision ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_revision FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_revision_company_isolation ON lattice_atom_revision
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE TABLE lattice_atom_revision_source_run (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    version integer NOT NULL,
    position integer NOT NULL,
    run_id text NOT NULL,
    PRIMARY KEY (company_id, employee_id, key, version, position),
    FOREIGN KEY (company_id, employee_id, key, version)
        REFERENCES lattice_atom_revision (company_id, employee_id, key, version) ON DELETE CASCADE
);

ALTER TABLE lattice_atom_revision_source_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_revision_source_run FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_revision_source_run_company_isolation ON lattice_atom_revision_source_run
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE TABLE lattice_atom_revision_key_file (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    version integer NOT NULL,
    position integer NOT NULL,
    path text NOT NULL,
    PRIMARY KEY (company_id, employee_id, key, version, position),
    FOREIGN KEY (company_id, employee_id, key, version)
        REFERENCES lattice_atom_revision (company_id, employee_id, key, version) ON DELETE CASCADE
);

ALTER TABLE lattice_atom_revision_key_file ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_revision_key_file FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_revision_key_file_company_isolation ON lattice_atom_revision_key_file
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));
