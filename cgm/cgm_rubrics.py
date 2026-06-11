"""CGM rubrics, weights, evidence checklists, archetypes. Data only - no logic
beyond rubric_for(). Rubric text is verbatim from the sponsor scope document."""

COUNTRIES = ["US", "AE", "BR", "IN", "SG", "PH"]
COUNTRY_NAMES = {
    "US": "United States", "AE": "United Arab Emirates", "BR": "Brazil",
    "IN": "India", "SG": "Singapore", "PH": "Philippines",
}
DIMENSIONS = ["ai_policy", "permitting", "value_capture", "tech_stack", "workforce"]
WEIGHTS = {
    "ai_policy": 0.25, "permitting": 0.20, "value_capture": 0.20,
    "tech_stack": 0.20, "workforce": 0.15,
}
ARCHETYPE = {
    "US": "substrate", "AE": "substrate", "BR": "substrate",
    "SG": "processor", "IN": "processor", "PH": "processor",
}

RUBRICS = {
    "ai_policy": {
        5: "National AI strategy with dedicated funding, minimal regulatory friction, explicit goal of AI leadership",
        4: "Active strategy, moderate funding, generally permissive regulation, proactive investment incentives",
        3: "Strategy exists but implementation uneven, mixed regulatory signals, moderate compliance burden",
        2: "Heavy regulatory framework creating significant compliance costs and deployment delays",
        1: "Restrictive or punitive regulation, no coherent strategy, active barriers to deployment",
    },
    "permitting": {
        5: "Fast-track permitting, weeks-to-months cycles, government actively facilitates",
        4: "Streamlined, 3-12 months, clear pathway, limited opposition mechanisms",
        3: "Standard, 12-24 months, multiple agencies, some community opposition",
        2: "Slow, 24-48 months, complex multi-stakeholder, frequent legal challenges",
        1: "Gridlock, 48+ months, unpredictable, regulatory capture by incumbents",
    },
    "value_capture": {
        "substrate": {
            5: "Stable resource taxation; sovereign wealth fund; active conversion of resource revenue into compute; strong anti-corruption checks",
            4: "Generally stable regime; some safeguards; growing but uneven compute conversion",
            3: "Unstable regime; resource nationalism risk; corruption siphons value; compute conversion throttled by governance",
            2: "High corruption, opaque contracts, weak controls, minimal compute conversion despite endowment",
            1: "Conflict-affected extraction, kleptocratic governance, zero value capture",
        },
        "processor": {
            5: "Large fiscal reserves; active retraining at scale; demonstrated history of economic pivots; actively building compute to offset services decline",
            4: "Adequate fiscal position; some retraining; moderate diversification; some compute investment",
            3: "Limited fiscal buffer; unproven retraining; high services dependence; minimal compute",
            2: "Weak fiscal position; no transition strategy; very high concentration in vulnerable services",
            1: "No buffer, no plan, total dependence on single vulnerable sector",
        },
    },
    "tech_stack": {
        5: "Deep integration with leading stack; secure advanced chip access; hosting critical AI infrastructure",
        4: "Good access; some chip dependency but manageable; growing hyperscaler presence",
        3: "Dual-alignment with long-term uncertainty; or moderate access to one stack with limited depth",
        2: "Peripheral to both stacks; limited chip access; no hyperscaler presence",
        1: "Technology-denied or self-isolated; sanctioned; no AI infrastructure",
    },
    "workforce": {
        5: "World-class education, high digital literacy, extensive retraining, young demographics, English proficiency, strong STEM pipeline",
        4: "Good education, above-average digital literacy, functioning retraining, favorable demographics",
        3: "Average education, moderate digital literacy, limited retraining, mixed demographics",
        2: "Weak education, low digital literacy, minimal retraining, unfavorable demographics",
        1: "Education in crisis, very low digital literacy, no retraining, demographic headwinds",
    },
}

EVIDENCE_CHECKLIST = {
    "ai_policy": [
        "national AI strategy document",
        "dedicated AI budget (USD and % of GDP)",
        "estimated time from AI system development to legal deployment",
        "tax incentives/disincentives",
        "regulatory sandbox count and scope",
        "national AI coordinating body existence and mandate",
    ],
    "permitting": [
        "average permitting timeline for data centers and power generation",
        "announced vs. completed projects (3-year completion ratio)",
        "special economic zones or fast-track frameworks",
        "documented delays or cancellations",
    ],
    "value_capture": {
        "substrate": [
            "resource taxation regime stability",
            "sovereign wealth fund existence and mandate",
            "conversion of resource revenue into compute infrastructure",
            "anti-corruption controls in extractive sector",
        ],
        "processor": [
            "fiscal reserves and budget position",
            "workforce retraining programs at scale",
            "history of economic pivots and diversification",
            "compute investment to offset services decline",
        ],
    },
    "tech_stack": [
        "chip import access by generation",
        "hyperscaler commitments (list and USD)",
        "technology alliance participation",
        "bilateral tech agreements",
        "domestic AI model capability",
    ],
    "workforce": [
        "education quality (PISA or equivalent)",
        "digital literacy and ICT development",
        "retraining program scale",
        "demographic projections",
        "STEM pipeline and English proficiency",
    ],
}


# Boundary decision rules (calibration round 1, 2026-06-10). Added after the
# first live run produced 8 one-point rater divergences; each rule below
# resolves a recurring boundary ambiguity found in the stored rationales.
# Per the sponsor spec, scorer disagreement = rubric under-specification.
GLOBAL_DECISION_RULES = [
    "Conjunctive clauses: select a level only if EVERY clause of that level's"
    " text is supported by cited evidence; if any clause lacks evidence,"
    " consider the next level down.",
    "Adjacent-boundary tie-break: when the evidence supports clauses of two"
    " adjacent levels (a mixed picture), select the LOWER level unless every"
    " clause of the higher level is explicitly evidenced.",
    "Documented dysfunction dominates announced intent: strategies, funding,"
    " or frameworks that are announced but accompanied by cited evidence of"
    " fragmentation, delay, or non-implementation are scored at the level"
    " describing the implementation reality.",
    "Projections do not count: market forecasts, announced or projected"
    " capacity, and growth-rate projections are not evidence of present"
    " capability; score on operating or contractually committed facts.",
]

DIMENSION_DECISION_RULES = {
    "ai_policy": [
        "Any cited evidence of uneven implementation, inter-agency"
        " fragmentation, or lack of policy coordination caps the score at 3"
        " (that is what 'implementation uneven' means).",
        "AI legislation still pending (proposed, under review, not yet law)"
        " is a 'mixed regulatory signal' consistent with level 3, not"
        " 'generally permissive regulation'.",
    ],
    "permitting": [
        "Score the GENERAL/national permitting environment. Special economic"
        " zones and fast-track carve-outs are valid evidence, but when the"
        " evidence covers ONLY carve-outs, score the general environment one"
        " level below what the carve-out alone would suggest (carve-outs"
        " exist because the default path is slower).",
        "A documented project completion ratio below 25% (e.g. flagship or"
        " 3-year completion data) caps the score at 2.",
        "Level 5 requires quantitative cycle-time evidence (weeks-to-months)"
        " for the general environment, or an operating national fast-track"
        " instrument with documented expedited outcomes; a fast-track"
        " instrument without cycle-time evidence is level 4.",
    ],
    "value_capture": [],
    "tech_stack": [
        "Level 5 requires ALL THREE elements with evidence: (a) deep"
        " integration with the leading stack, (b) secure advanced chip access"
        " (leading-edge allocation or domestic fabrication; import flows alone"
        " are insufficient), and (c) hosting critical AI infrastructure"
        " (operating frontier-scale compute). Missing any one means at most 4.",
        "Semiconductor assembly/test/packaging activity evidences electronics"
        " industry presence, NOT advanced compute chip access; without"
        " evidence of advanced-chip availability for AI compute or operating"
        " hyperscaler capacity, cap the score at 3.",
    ],
    "workforce": [],
}


def decision_rules_for(dimension):
    return GLOBAL_DECISION_RULES + DIMENSION_DECISION_RULES[dimension]


def rubric_for(dimension, country_iso):
    rubric = RUBRICS[dimension]
    if dimension == "value_capture":
        return rubric[ARCHETYPE[country_iso]]
    return rubric


def checklist_for(dimension, country_iso):
    items = EVIDENCE_CHECKLIST[dimension]
    if dimension == "value_capture":
        return items[ARCHETYPE[country_iso]]
    return items
