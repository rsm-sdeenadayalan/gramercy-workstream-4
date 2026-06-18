import math

from cgm_kappa import (
    agreement_stats, gwet_ac1, gwet_ac2, linear_weighted_kappa,
)


def test_ac2_perfect_agreement_is_one():
    assert math.isclose(gwet_ac2([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)


def test_ac2_unweighted_reduces_to_ac1():
    a, b = [2, 3, 2, 2, 3, 2], [2, 2, 3, 2, 2, 2]
    assert math.isclose(gwet_ac2(a, b, weighted=False), gwet_ac1(a, b))


def test_ac2_constant_agreement_is_one_not_none():
    # where linear_weighted_kappa is degenerate (None), AC2 is a clean 1.0
    assert linear_weighted_kappa([4] * 6, [4] * 6) is None
    assert math.isclose(gwet_ac2([4] * 6, [4] * 6), 1.0)


def test_ac2_robust_to_clustering_where_kappa_collapses():
    # The empirical permitting_standard case: 4/6 exact, 2 one-point splits,
    # scores clustered at 2-3. Kappa collapses (~0.57) but AC2 reflects the
    # real near-perfect agreement and clears 0.70.
    a = [2, 4, 3, 2, 3, 2]
    b = [2, 4, 2, 2, 2, 2]
    assert linear_weighted_kappa(a, b) < 0.7
    assert gwet_ac2(a, b) > 0.7
    assert gwet_ac2(a, b) > linear_weighted_kappa(a, b)


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
