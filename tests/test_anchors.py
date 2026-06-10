from unittest.mock import MagicMock, patch

from cgm_anchors import WB_INDICATORS, fetch_indicator, parse_wb_response

WB_SAMPLE = [
    {"page": 1, "pages": 1},
    [{"indicator": {"id": "SE.ADT.LITR.ZS"}, "country": {"id": "BR"},
      "value": 94.0, "date": "2022"}],
]


def test_indicator_map_covers_workforce_and_gdp():
    metrics = {name for name, _unit in WB_INDICATORS.values()}
    assert "human_capital_index" in metrics
    assert "gdp_usd" in metrics
    assert len(WB_INDICATORS) >= 5


def test_parse_wb_response():
    parsed = parse_wb_response(WB_SAMPLE)
    assert parsed == {"value": 94.0, "year": 2022}


def test_parse_wb_response_empty_returns_none():
    assert parse_wb_response([{"page": 1}, []]) is None
    assert parse_wb_response([{"message": "err"}]) is None


@patch("cgm_anchors.requests.get")
def test_fetch_indicator_builds_url_and_parses(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200, json=MagicMock(return_value=WB_SAMPLE)
    )
    row = fetch_indicator("BR", "SE.ADT.LITR.ZS")
    assert row["value"] == 94.0 and row["year"] == 2022
    assert "BR" in row["source_url"] and "SE.ADT.LITR.ZS" in row["source_url"]
