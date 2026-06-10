import json
from unittest.mock import patch

from cgm_arbiter import build_arbiter_prompt, needs_arbitration, parse_resolution


def test_needs_arbitration():
    assert needs_arbitration(2, 4) is True
    assert needs_arbitration(5, 2) is True
    assert needs_arbitration(3, 4) is False
    assert needs_arbitration(4, 4) is False


def test_build_arbiter_prompt_shows_both_raters():
    prompt = build_arbiter_prompt(
        "AE", "ai_policy",
        {"score": 5, "rationale": "ra", "rubric_clause": "c5"},
        {"score": 3, "rationale": "rb", "rubric_clause": "c3"},
        evidence_rows=[{"evidence_id": 1, "checklist_item": "i", "claim": "c",
                        "quote": "q", "source_url": "u"}],
        anchor_rows=[],
    )
    assert "Rater A" in prompt and "Rater B" in prompt
    assert "5" in prompt and "3" in prompt and "[1]" in prompt


def test_parse_resolution():
    out = parse_resolution(json.dumps(
        {"resolved_score": 4, "reasoning": "Rater A overweighted ..."}
    ))
    assert out == (4, "Rater A overweighted ...")


def test_parse_resolution_rejects_out_of_range():
    import pytest
    with pytest.raises(ValueError):
        parse_resolution(json.dumps({"resolved_score": 7, "reasoning": "x"}))
