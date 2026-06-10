import math

from cgm_kappa import agreement_stats, linear_weighted_kappa


def test_perfect_agreement_with_variance():
    a = [1, 2, 3, 4, 5, 5]
    assert math.isclose(linear_weighted_kappa(a, a), 1.0)


def test_hand_computed_moderate_case():
    a = [3, 3, 4, 4, 5, 5]
    b = [3, 4, 4, 4, 5, 4]
    assert math.isclose(linear_weighted_kappa(a, b), 4 / 7)


def test_degenerate_identical_constant_returns_none():
    # both raters give every country a 4: perfect agreement, zero variance
    assert linear_weighted_kappa([4] * 6, [4] * 6) is None


def test_constant_but_different_is_zero_not_none():
    # A all 4s, B all 3s: kappa defined and 0 (observed == expected disagreement)
    assert math.isclose(linear_weighted_kappa([4] * 6, [3] * 6), 0.0)


def test_agreement_stats():
    a = [3, 3, 4, 4, 5, 5]
    b = [3, 4, 4, 4, 5, 2]
    stats = agreement_stats(a, b)
    assert math.isclose(stats["raw_agreement"], 4 / 6)
    assert math.isclose(stats["adjacent_agreement"], 5 / 6)  # |5-2|=3 fails ±1
    assert stats["n"] == 6


def test_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        linear_weighted_kappa([1, 2], [1])
