import json
from unittest.mock import MagicMock, patch

from cgm_evidence import (
    EXTRACT_SYSTEM, build_extract_prompt, coverage, parse_claims,
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
