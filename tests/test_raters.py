import json
from unittest.mock import patch

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
