-- Migration: split `permitting` -> `permitting_standard` + `permitting_fasttrack`
-- on cgm_score_final, for DBs created BEFORE the split. Idempotent.
--
-- Fresh databases get the new columns directly from cgm_schema.sql and do NOT
-- need this migration. Existing databases need it because cgm_schema.sql uses
-- CREATE TABLE IF NOT EXISTS, which will not alter a table that already exists.
--
-- After running this, RE-SCORE (run_cgm.py --only score) to populate the new
-- columns, then re-apply cgm_schema.sql (e.g. setup_cgm.py) to rebuild the view.
BEGIN;

-- The view depends on the permitting column, so drop it before altering.
DROP VIEW IF EXISTS v_cgm_latest;

ALTER TABLE cgm_score_final DROP COLUMN IF EXISTS permitting;
ALTER TABLE cgm_score_final ADD COLUMN IF NOT EXISTS permitting_standard  NUMERIC;
ALTER TABLE cgm_score_final ADD COLUMN IF NOT EXISTS permitting_fasttrack NUMERIC;

COMMIT;

-- Recreate v_cgm_latest with the new columns.
CREATE OR REPLACE VIEW v_cgm_latest AS
SELECT f.country_iso, f.archetype,
       f.ai_policy, f.permitting_standard, f.permitting_fasttrack,
       f.value_capture, f.tech_stack, f.workforce,
       f.cgm_score,
       RANK() OVER (ORDER BY f.cgm_score DESC) AS rank,
       f.computed_at
FROM cgm_score_final f
WHERE f.run_id = (SELECT f2.run_id FROM cgm_score_final f2
                  JOIN cgm_runs r ON r.run_id = f2.run_id
                  WHERE r.finished_at IS NOT NULL
                  ORDER BY f2.computed_at DESC LIMIT 1);
