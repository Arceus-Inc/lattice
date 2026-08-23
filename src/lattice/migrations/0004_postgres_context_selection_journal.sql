-- 0004_postgres_context_selection_journal — durable exact revisions shown during a beat.
-- Applied by the host application's migration runner; do not edit after deployment.

CREATE TABLE lattice_context_atom_selection (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    beat_run_id text NOT NULL,
    key text NOT NULL,
    revision integer NOT NULL,
    PRIMARY KEY (company_id, employee_id, beat_run_id, key),
    FOREIGN KEY (company_id, employee_id, key, revision)
        REFERENCES lattice_atom_revision (company_id, employee_id, key, version)
);

ALTER TABLE lattice_context_atom_selection ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_context_atom_selection FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_context_atom_selection_company_isolation ON lattice_context_atom_selection
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

CREATE FUNCTION lattice_reject_selection_after_applied() RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1 FROM lattice_atom_applied_beat
        WHERE company_id = NEW.company_id
          AND employee_id = NEW.employee_id
          AND beat_run_id = NEW.beat_run_id
    ) THEN
        RAISE EXCEPTION 'context selection is sealed by its APPLIED beat'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$function$;

CREATE TRIGGER lattice_context_atom_selection_reject_after_applied
    BEFORE INSERT ON lattice_context_atom_selection
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_selection_after_applied();

CREATE TRIGGER lattice_context_atom_selection_reject_mutation
    BEFORE UPDATE OR DELETE ON lattice_context_atom_selection
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_applied_mutation();
