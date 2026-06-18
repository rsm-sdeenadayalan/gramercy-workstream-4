import math

from cgm_rubrics import (
    ARCHETYPE, COUNTRIES, DIMENSIONS, EVIDENCE_CHECKLIST, WEIGHTS, rubric_for,
)


def test_weights_sum_to_one():
    assert math.isclose(sum(WEIGHTS.values()), 1.0)
    assert set(WEIGHTS) == set(DIMENSIONS)


def test_every_dimension_has_five_levels():
    for dim in DIMENSIONS:
        for country in COUNTRIES:
            rubric = rubric_for(dim, country)
            assert sorted(rubric) == [1, 2, 3, 4, 5], (dim, country)
            assert all(len(text) > 20 for text in rubric.values())


def test_archetype_routing():
    assert {c: ARCHETYPE[c] for c in COUNTRIES} == {
        "US": "substrate", "AE": "substrate", "BR": "substrate",
        "SG": "processor", "IN": "processor", "PH": "processor",
    }
    # value_capture rubric differs by archetype; others identical
    assert rubric_for("value_capture", "US") != rubric_for("value_capture", "SG")
    assert rubric_for("ai_policy", "US") == rubric_for("ai_policy", "SG")


def test_checklists_nonempty():
    for dim in DIMENSIONS:
        for country in COUNTRIES:
            items = EVIDENCE_CHECKLIST[dim] if dim != "value_capture" \
                else EVIDENCE_CHECKLIST[dim][ARCHETYPE[country]]
            assert len(items) >= 3, dim


def test_decision_rules_per_dimension():
    from cgm_rubrics import decision_rules_for, GLOBAL_DECISION_RULES
    for dim in DIMENSIONS:
        rules = decision_rules_for(dim)
        assert rules[:len(GLOBAL_DECISION_RULES)] == GLOBAL_DECISION_RULES
    assert any("DEFAULT path" in r for r in decision_rules_for("permitting_standard"))
    assert any("EXPEDITED OUTCOMES" in r for r in decision_rules_for("permitting_fasttrack"))
    assert any("ALL THREE" in r for r in decision_rules_for("tech_stack"))
