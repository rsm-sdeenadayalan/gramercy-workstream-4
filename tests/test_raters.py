from unittest.mock import MagicMock, patch

import pytest

from cgm_raters import (
    RATER_A_SYSTEM, RATER_B_SYSTEM, build_rater_prompt, validate_rating,
)

EVIDENCE_ROWS = [
    {"evidence_id": 11, "checklist_item": "national AI strategy document",
     "claim": "UAE has a funded national AI strategy", "quote": "q",
     "source_url": "https://ai.gov.ae/strategy"},
]
ANCHOR_ROWS = [
    {"metric": "gdp_usd", "value": 500000000000.0, "unit": "USD", "year": 2025},
]


def test_prompts_are_structurally_different():
    # decorrelation: A is rubric-clause-first, B is evidence-first
    assert "level 5 down" in RATER_A_SYSTEM
    assert "summarize what the evidence establishes" in RATER_B_SYSTEM
    assert RATER_A_SYSTEM != RATER_B_SYSTEM


def test_build_rater_prompt_contains_rubric_evidence_anchors():
    prompt = build_rater_prompt("AE", "ai_policy", EVIDENCE_ROWS, ANCHOR_ROWS)
    assert "[11]" in prompt                      # evidence cited by ID
    assert "National AI strategy" in prompt      # rubric level text
    assert "gdp_usd" in prompt                   # anchors present
    assert "United Arab Emirates" in prompt


def test_validate_rating_accepts_good():
    rating = {"score": 5, "rubric_clause": "National AI strategy with...",
              "evidence_ids": [11], "rationale": "r"}
    assert validate_rating(rating, allowed_ids={11}) is None


@pytest.mark.parametrize("bad,msg", [
    ({"score": 6, "rubric_clause": "x", "evidence_ids": [11], "rationale": "r"},
     "score"),
    ({"score": 4, "rubric_clause": "x", "evidence_ids": [], "rationale": "r"},
     "evidence"),
    ({"score": 4, "rubric_clause": "x", "evidence_ids": [99], "rationale": "r"},
     "evidence"),
    ({"rubric_clause": "x", "evidence_ids": [11], "rationale": "r"}, "score"),
])
def test_validate_rating_rejects_bad(bad, msg):
    err = validate_rating(bad, allowed_ids={11})
    assert err is not None and msg in err


def test_validate_rating_rejects_boolean_score():
    """Fix B: isinstance(True, int) is True — booleans must be rejected."""
    err = validate_rating(
        {"score": True, "rubric_clause": "x", "evidence_ids": [11], "rationale": "r"},
        allowed_ids={11},
    )
    assert err is not None and "score" in err


def test_rater_prompt_includes_decision_rules():
    prompt = build_rater_prompt("AE", "ai_policy", EVIDENCE_ROWS, ANCHOR_ROWS)
    assert "DECISION RULES" in prompt
    assert "Adjacent-boundary tie-break" in prompt
    assert "implementation uneven" in prompt   # ai_policy-specific rule present


def test_run_raters_skips_llm_when_evidence_empty():
    """Fix A: empty evidence pack must short-circuit — no LLM calls, NULL row upserted,
    blocker gap added once per rater."""
    import cgm_raters

    # cursor mock: fetchone returns None (no cached row)
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = mock_cursor

    mock_cgm_db = MagicMock()

    with (
        patch("cgm_raters.rate_one") as mock_rate_one,
        patch("cgm_raters.cgm_db", mock_cgm_db),
        patch("cgm_raters.load_pack", return_value=([], [])),
        patch("cgm_raters.COUNTRIES", ["AE"]),
        patch("cgm_raters.DIMENSIONS", ["ai_policy"]),
    ):
        run_raters_fn = cgm_raters.run_raters
        run_raters_fn(conn, "rid")

    mock_rate_one.assert_not_called()
    # One INSERT/upsert per rater (2 raters) — cursor.execute called for cache-check
    # and upsert per rater; count just the upsert calls via INSERT keyword
    insert_calls = [
        c for c in mock_cursor.execute.call_args_list
        if "INSERT" in str(c)
    ]
    assert len(insert_calls) == 2, f"Expected 2 upsert calls, got {len(insert_calls)}"
    # add_gap called twice (once per rater) with severity="blocker"
    assert mock_cgm_db.add_gap.call_count == 2
    for call in mock_cgm_db.add_gap.call_args_list:
        assert call.kwargs.get("severity") == "blocker" or call.args[-1] == "blocker"
