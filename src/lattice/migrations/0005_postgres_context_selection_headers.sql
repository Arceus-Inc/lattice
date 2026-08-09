-- 0005_postgres_context_selection_headers — complete beat-level capture markers.
-- Applied by the host application's migration runner; do not edit after deployment.

ALTER TABLE lattice_atom_applied_beat
    DROP CONSTRAINT lattice_atom_applied_beat_selected_count_check;
ALTER TABLE lattice_atom_applied_beat
    ADD CONSTRAINT lattice_atom_applied_beat_selected_count_check CHECK (selected_count >= 0);

CREATE TABLE lattice_context_selection_beat (
    company_id uuid NOT NULL DEFAULT (NULLIF(current_setting('app.company_id', true), ''))::uuid,
    employee_id text NOT NULL,
    beat_run_id text NOT NULL,
    selected_count integer NOT NULL CHECK (selected_count >= 0),
    selected_digest bytea NOT NULL CHECK (octet_length(selected_digest) = 32),
    complete boolean NOT NULL,
    PRIMARY KEY (company_id, employee_id, beat_run_id)
);

ALTER TABLE lattice_context_selection_beat ENABLE ROW LEVEL SECURITY;
ALTER TABLE lattice_context_selection_beat FORCE ROW LEVEL SECURITY;
CREATE POLICY lattice_context_selection_beat_company_isolation ON lattice_context_selection_beat
    USING (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid))
    WITH CHECK (company_id = (SELECT (NULLIF(current_setting('app.company_id', true), ''))::uuid));

-- Rows installed by 0004 predate completeness tracking. Preserve them as explicitly
-- incomplete and therefore unsealable; a zero digest is a migration sentinel only.
INSERT INTO lattice_context_selection_beat (
    company_id,
    employee_id,
    beat_run_id,
    selected_count,
    selected_digest,
    complete
)
SELECT
    company_id,
    employee_id,
    beat_run_id,
    count(*),
    decode(repeat('00', 32), 'hex'),
    false
FROM lattice_context_atom_selection
GROUP BY company_id, employee_id, beat_run_id;

ALTER TABLE lattice_context_atom_selection
    ADD CONSTRAINT lattice_context_atom_selection_beat_fkey
    FOREIGN KEY (company_id, employee_id, beat_run_id)
    REFERENCES lattice_context_selection_beat (company_id, employee_id, beat_run_id);

CREATE FUNCTION lattice_reject_selection_header_after_applied() RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1 FROM lattice_atom_applied_beat
        WHERE company_id = NEW.company_id
          AND employee_id = NEW.employee_id
          AND beat_run_id = NEW.beat_run_id
    ) THEN
        RAISE EXCEPTION 'context selection header is sealed by its APPLIED beat'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$function$;

CREATE TRIGGER lattice_context_selection_beat_reject_after_applied
    BEFORE INSERT OR UPDATE ON lattice_context_selection_beat
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_selection_header_after_applied();

CREATE TRIGGER lattice_context_selection_beat_reject_delete
    BEFORE DELETE ON lattice_context_selection_beat
    FOR EACH ROW EXECUTE FUNCTION lattice_reject_applied_mutation();
