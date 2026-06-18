from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "cgm" / "cgm_schema.sql").read_text()

REQUIRED_TABLES = [
    "cgm_runs", "cgm_collection_log", "cgm_raw_anchors", "cgm_evidence",
    "cgm_rater_scores", "cgm_arbitrations", "cgm_kappa_results",
    "cgm_score_final", "cgm_score_methodology", "cgm_data_gaps",
]

def test_all_required_tables_present():
    for t in REQUIRED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {t}" in SCHEMA, t

def test_latest_view_present():
    assert "CREATE OR REPLACE VIEW v_cgm_latest" in SCHEMA

def test_idempotent_only():
    assert "DROP TABLE" not in SCHEMA.upper()

def test_rater_unique_constraint():
    assert "UNIQUE (country_iso, dimension, rater_model)" in SCHEMA

def test_score_final_unique_constraint():
    assert "UNIQUE (run_id, country_iso)" in SCHEMA

def test_latest_view_only_finished_runs():
    assert "finished_at IS NOT NULL" in SCHEMA

def test_latest_view_exposes_integration_columns():
    view = SCHEMA[SCHEMA.index("CREATE OR REPLACE VIEW v_cgm_latest"):]
    for col in ("country_iso", "ai_policy", "permitting_standard",
                "permitting_fasttrack", "value_capture",
                "tech_stack", "workforce", "cgm_score", "rank", "computed_at"):
        assert col in view, col

def test_enum_checks_present():
    assert "CHECK (status IN ('ok','error','skipped'))" in SCHEMA
    assert "CHECK (archetype IN ('substrate','processor'))" in SCHEMA
    assert "CHECK (severity IN ('warn','blocker'))" in SCHEMA
