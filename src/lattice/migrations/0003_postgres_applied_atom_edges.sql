-- 0003_postgres_applied_atom_edges — immutable exact atom-revision outcome edges.
-- Applied by the host application's migration runner; do not edit after deployment.

CREATE TABLE lattice_atom_applied_beat (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    beat_run_id text NOT NULL,
    outcome_phase text NOT NULL CHECK (outcome_phase IN (
        'cancelled',
        'delegated',
        'terminal_pass',
        'terminal_fail',
        'needs_rework',
        'stranded'
    )),
    landed_at timestamptz NOT NULL,
    selected_count integer NOT NULL CHECK (selected_count > 0),
    selected_digest bytea NOT NULL CHECK (octet_length(selected_digest) = 32),
    PRIMARY KEY (company_id, employee_id, beat_run_id),
    UNIQUE (company_id, employee_id, beat_run_id, outcome_phase, landed_at)
);

ALTER TABLE lattice_atom_applied_beat ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_applied_beat FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_applied_beat_company_isolation ON lattice_atom_applied_beat
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE TABLE lattice_atom_applied_edge (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    key text NOT NULL,
    revision integer NOT NULL,
    beat_run_id text NOT NULL,
    outcome_phase text NOT NULL,
    landed_at timestamptz NOT NULL,
    PRIMARY KEY (company_id, employee_id, key, revision, beat_run_id),
    FOREIGN KEY (company_id, employee_id, beat_run_id, outcome_phase, landed_at)
        REFERENCES lattice_atom_applied_beat (
            company_id, employee_id, beat_run_id, outcome_phase, landed_at
        ),
    FOREIGN KEY (company_id, employee_id, key, revision)
        REFERENCES lattice_atom_revision (company_id, employee_id, key, version)
);

ALTER TABLE lattice_atom_applied_edge ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_atom_applied_edge FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_atom_applied_edge_company_isolation ON lattice_atom_applied_edge
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE FUNCTION lattice_reject_applied_mutation() RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'lattice APPLIED rows are immutable'
        USING ERRCODE = '55000';
END
$function$;

CREATE TRIGGER lattice_atom_applied_beat_reject_mutation
    BEFORE UPDATE OR DELETE ON lattice_atom_applied_beat
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_applied_mutation();

CREATE TRIGGER lattice_atom_applied_edge_reject_mutation
    BEFORE UPDATE OR DELETE ON lattice_atom_applied_edge
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_applied_mutation();

CREATE INDEX lattice_atom_applied_edge_run_idx
    ON lattice_atom_applied_edge (company_id, employee_id, beat_run_id, key, revision);
