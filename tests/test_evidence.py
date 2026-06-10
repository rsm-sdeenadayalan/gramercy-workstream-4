import json
from unittest.mock import MagicMock, patch

import cgm_evidence
from cgm_evidence import (
    build_extract_prompt, coverage, parse_claims,
)

SEARCH_RESULTS = [
    {"title": "UAE National AI Strategy 2031", "url": "https://ai.gov.ae/strategy",
     "content": "The UAE launched its National AI Strategy 2031 with funding..."},
]

CLAIMS_JSON = json.dumps({"claims": [
    {"claim": "UAE has a funded national AI strategy (AI Strategy 2031)",
     "quote": "launched its National AI Strategy 2031 with funding",
     "source_url": "https://ai.gov.ae/strategy",
     "checklist_item": "national AI strategy document"},
]})


def test_build_extract_prompt_includes_sources_and_checklist():
    prompt = build_extract_prompt(
        "United Arab Emirates", "ai_policy",
        ["national AI strategy document"], SEARCH_RESULTS,
    )
    assert "https://ai.gov.ae/strategy" in prompt
    assert "national AI strategy document" in prompt
    assert "United Arab Emirates" in prompt


def test_parse_claims_validates_urls_against_sources():
    claims = parse_claims(CLAIMS_JSON, allowed_urls={"https://ai.gov.ae/strategy"})
    assert len(claims) == 1
    assert claims[0]["checklist_item"] == "national AI strategy document"


def test_parse_claims_drops_unknown_urls():
    bad = json.dumps({"claims": [{"claim": "x", "quote": "y",
                                  "source_url": "https://fabricated.example",
                                  "checklist_item": "item"}]})
    assert parse_claims(bad, allowed_urls={"https://ai.gov.ae/strategy"}) == []


def test_coverage():
    items = ["a", "b", "c", "d"]
    claims = [{"checklist_item": "a"}, {"checklist_item": "a"},
              {"checklist_item": "c"}]
    cov = coverage(items, claims)
    assert cov == {"covered": ["a", "c"], "missing": ["b", "d"], "ratio": 0.5}


def test_collect_evidence_skips_gap_and_ok_on_tavily_error():
    """When tavily_search raises, only one 'error' status log is recorded;
    add_gap must NOT be called and no INSERT INTO cgm_evidence must be executed."""
    # cursor context manager: fetchone returns (0,) so immutability check passes
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (0,)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cgm_db = MagicMock()

    with patch("cgm_evidence.tavily_search", side_effect=Exception("tavily down")), \
         patch("cgm_evidence.cgm_db", mock_cgm_db), \
         patch("cgm_evidence.COUNTRIES", ["AE"]), \
         patch("cgm_evidence.DIMENSIONS", ["ai_policy"]):
        cgm_evidence.collect_evidence(mock_conn, run_id="run-test-001",
                                      extract_model="test-model")

    # log_collection called exactly once with status='error'
    assert mock_cgm_db.log_collection.call_count == 1
    call_args = mock_cgm_db.log_collection.call_args
    assert call_args[0][3] == "error"

    # add_gap must NOT have been called
    mock_cgm_db.add_gap.assert_not_called()

    # no INSERT INTO cgm_evidence executed
    for call in mock_cursor.execute.call_args_list:
        sql = call[0][0] if call[0] else ""
        assert "INSERT INTO cgm_evidence" not in sql, \
            f"Unexpected INSERT found: {sql}"
