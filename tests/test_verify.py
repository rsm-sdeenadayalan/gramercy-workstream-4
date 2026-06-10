from cgm_verify import (
    check_arbitrations, check_completeness, check_evidence_citations,
    check_kappa_gate, check_score_ranges,
)


def kappa_row(dim, kappa, raw, degenerate=False):
    return {"dimension": dim, "kappa_linear": kappa, "degenerate": degenerate,
            "raw_agreement": raw}


def test_kappa_gate_passes_at_07():
    rows = [kappa_row(d, 0.7, 0.8) for d in
            ("ai_policy", "permitting", "value_capture", "tech_stack", "workforce")]
    assert check_kappa_gate(rows) == []


def test_kappa_gate_fails_below_07():
    rows = [kappa_row("ai_policy", 0.69, 0.8)]
    fails = check_kappa_gate(rows)
    assert len(fails) == 1 and "ai_policy" in fails[0]


def test_kappa_gate_degenerate_perfect_agreement_passes():
    assert check_kappa_gate([kappa_row("permitting", None, 1.0,
                                       degenerate=True)]) == []


def test_kappa_gate_degenerate_imperfect_fails():
    fails = check_kappa_gate([kappa_row("permitting", None, 0.5,
                                        degenerate=True)])
    assert len(fails) == 1


def test_completeness():
    full = [(c, d) for c in ("US", "AE", "BR", "IN", "SG", "PH")
            for d in ("ai_policy", "permitting", "value_capture",
                      "tech_stack", "workforce")]
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
