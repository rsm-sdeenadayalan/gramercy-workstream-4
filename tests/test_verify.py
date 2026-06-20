from cgm_verify import (
    check_agreement_gate, check_arbitrations, check_completeness,
    check_evidence_citations, check_score_ranges,
)


def kappa_row(dim, ac2, raw, kappa=None, degenerate=False):
    # The gate reads gwet_ac2; kappa is reported only.
    return {"dimension": dim, "gwet_ac2": ac2, "kappa_linear": kappa,
            "degenerate": degenerate, "raw_agreement": raw}


def test_agreement_gate_passes_at_threshold():
    # AC2 gate is 0.75; values at/above it pass.
    rows = [kappa_row(d, 0.75, 0.8) for d in
            ("ai_policy", "permitting_standard", "permitting_fasttrack",
             "value_capture", "tech_stack", "workforce")]
    assert check_agreement_gate(rows) == []


def test_agreement_gate_fails_just_below_threshold():
    # 0.74 < 0.75 must fail (boundary check for the stricter AC2 gate)
    fails = check_agreement_gate([kappa_row("ai_policy", 0.74, 0.8)])
    assert len(fails) == 1 and "ai_policy" in fails[0]


def test_agreement_gate_pooled_not_gated():
    assert check_agreement_gate([kappa_row("pooled", 0.40, 0.6)]) == []


def test_agreement_gate_exempts_zero_weight_context_dimension():
    # permitting_fasttrack has weight 0.00 - reported but never gated, so a low
    # AC2 on it must not block publication of the weighted headline.
    assert check_agreement_gate([kappa_row("permitting_fasttrack", 0.40, 0.6)]) == []


def test_agreement_gate_still_fails_weighted_dimension_below_gate():
    # sanity: the exemption is weight-scoped, not a blanket pass
    fails = check_agreement_gate([kappa_row("permitting_standard", 0.40, 0.6)])
    assert len(fails) == 1 and "permitting_standard" in fails[0]


def test_agreement_gate_missing_ac2_fails():
    fails = check_agreement_gate([kappa_row("ai_policy", None, 0.6)])
    assert len(fails) == 1


def test_completeness():
    full = [(c, d) for c in ("US", "AE", "BR", "IN", "SG", "PH")
            for d in ("ai_policy", "permitting_standard", "permitting_fasttrack",
                      "value_capture", "tech_stack", "workforce")]
    assert check_completeness(full) == []
    fails = check_completeness(full[:-1])
    assert len(fails) == 1 and "PH" in fails[0] and "workforce" in fails[0]


def test_evidence_citations():
    assert check_evidence_citations([("US", "ai_policy", [1, 2])]) == []
    fails = check_evidence_citations([("US", "ai_policy", None)])
    assert len(fails) == 1


def test_score_ranges():
    assert check_score_ranges([("US", 4.5)]) == []
    assert len(check_score_ranges([("US", 5.5)])) == 1


def test_arbitrations():
    # divergence >1 must have an arbitration row
    assert check_arbitrations([("US", "ai_policy", 2, 4)],
                              arbitrated={("US", "ai_policy")}) == []
    fails = check_arbitrations([("US", "ai_policy", 2, 4)], arbitrated=set())
    assert len(fails) == 1


def test_check_weights():
    from cgm_verify import check_weights
    assert check_weights({"a": 0.5, "b": 0.5}) == []
    fails = check_weights({"a": 0.5, "b": 0.4})
    assert len(fails) == 1 and "0.9" in fails[0]
