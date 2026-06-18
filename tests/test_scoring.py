import math

import pytest

from cgm_scoring import combine_scores, composite, perturb_weights, sensitivity
from cgm_rubrics import WEIGHTS


def test_resolve_arbitration_passthrough():
    from cgm_scoring import resolve_arbitration
    assert resolve_arbitration([2, 5], (2, 5, 4)) == 4
    assert resolve_arbitration([2, 5], None) is None


def test_resolve_arbitration_stale_raises():
    from cgm_scoring import resolve_arbitration
    with pytest.raises(ValueError, match="stale arbitration"):
        resolve_arbitration([3, 5], (2, 5, 4))


def test_combine_equal():
    assert combine_scores(4, 4, None) == 4.0


def test_combine_adjacent_means():
    assert combine_scores(3, 4, None) == 3.5


def test_combine_divergent_uses_arbiter():
    assert combine_scores(2, 5, 4) == 4.0


def test_combine_divergent_without_arbiter_raises():
    with pytest.raises(ValueError):
        combine_scores(2, 5, None)


def test_composite_weighted():
    dims = {"ai_policy": 5, "permitting_standard": 4, "permitting_fasttrack": 2,
            "value_capture": 4, "tech_stack": 5, "workforce": 3}
    # permitting_fasttrack has weight 0.00, so it must not affect the composite
    expected = 0.25 * 5 + 0.20 * 4 + 0.00 * 2 + 0.20 * 4 + 0.20 * 5 + 0.15 * 3
    assert math.isclose(composite(dims), expected)


def test_perturb_weights_renormalizes():
    w = perturb_weights(WEIGHTS, "ai_policy", +0.10)
    assert math.isclose(sum(w.values()), 1.0)
    assert w["ai_policy"] > WEIGHTS["ai_policy"]


def test_sensitivity_detects_rank_change():
    # two countries, one dimension dominant: shifting weight flips ranking
    scores = {
        "AA": {"ai_policy": 5, "permitting_standard": 1, "permitting_fasttrack": 3,
               "value_capture": 3, "tech_stack": 3, "workforce": 3},
        "BB": {"ai_policy": 1, "permitting_standard": 5, "permitting_fasttrack": 3,
               "value_capture": 3, "tech_stack": 3, "workforce": 3},
    }
    report = sensitivity(scores)
    assert any(item["ranking_changed"] for item in report)
    assert {i["dimension"] for i in report} == set(WEIGHTS)
    assert {i["delta"] for i in report} == {0.10, -0.10}
