"""CGM rubrics, weights, evidence checklists, archetypes. Data only - no logic
beyond rubric_for(). Rubric text is verbatim from the sponsor scope document."""

COUNTRIES = ["US", "AE", "BR", "IN", "SG", "PH"]
COUNTRY_NAMES = {
    "US": "United States", "AE": "United Arab Emirates", "BR": "Brazil",
    "IN": "India", "SG": "Singapore", "PH": "Philippines",
}
DIMENSIONS = ["ai_policy", "permitting_standard", "permitting_fasttrack",
              "value_capture", "tech_stack", "workforce"]
# permitting_fasttrack is measured and published as context but carries ZERO
# headline weight (sponsor decision 2026-06-18). Folding fast-track delivery
# into the headline would double-count realized fast builds that CII (WS2)
# already captures as installed capacity / growth velocity. Division of labor:
# CII = "did they build it"; CGM = "how good is the system that must build it".
WEIGHTS = {
    "ai_policy": 0.25, "permitting_standard": 0.20, "permitting_fasttrack": 0.00,
    "value_capture": 0.20, "tech_stack": 0.20, "workforce": 0.15,
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
    # Default/ordinary approval path ONLY — a single time-band axis. No
    # fast-track language; that lives in permitting_fasttrack. This split
    # resolves the inter-rater divergence on dual-track countries (BR/IN/PH/SG),
    # where the old conflated scale let one rater grade the fast lane and the
    # other the slow lane, both correctly.
    "permitting_standard": {
        5: "Default (non-carve-out) approval in weeks-to-months; government actively facilitates the standard path",
        4: "Standard path streamlined, 3-12 months, clear pathway, limited opposition mechanisms",
        3: "Standard path 12-24 months, multiple agencies, some community opposition",
        2: "Standard path slow, 24-48 months, complex multi-stakeholder, frequent legal challenges",
        1: "Standard path gridlock, 48+ months, unpredictable, regulatory capture by incumbents",
    },
    # Fast-track / SEZ availability — graded on documented expedited OUTCOMES
    # and breadth of access, not the mere existence of an instrument.
    "permitting_fasttrack": {
        5: "Operating fast-track instrument with documented expedited outcomes, broadly accessible (not zone-/sector-restricted), weeks-to-months",
        4: "Operating fast-track/SEZ instrument with documented expedited outcomes, but access conditional on zone, sector, or investment threshold",
        3: "Fast-track instrument exists in limited zones; expedited outcomes only partially documented or uneven",
        2: "Fast-track announced but no documented expedited outcomes, or available only to a narrow set of incumbents",
        1: "No fast-track instrument; no expedited pathway available",
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
    # NB: checklist items double as Tavily search queries (cgm_evidence searches
    # "<country> <item>"), so they must read as clean search strings. The
    # standard-vs-fast-track scoping is enforced by the rubric + decision rules,
    # not by narrowing the search; both packs may surface overlapping evidence.
    "permitting_standard": [
        "average permitting timeline for data centers and power plants",
        "data center and power plant project completion rate vs announcements",
        "documented permitting delays or project cancellations for data centers",
    ],
    "permitting_fasttrack": [
        "special economic zone fast-track permitting for data centers",
        "fast-track approval timelines achieved in special economic zones",
        "special economic zone eligibility requirements for investors",
        "share of projects using fast-track versus standard permitting",
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


# Boundary decision rules (calibration round 2, 2026-06-10). Replaces round-1
# rules after round-1's conjunctive/tie-break pair manufactured new divergences
# on cells where neither adjacent level fully fits; two round-1 rules were also
# ambiguous. Rules below address 7 observed round-1 divergences.
# Per the sponsor spec, scorer disagreement = rubric under-specification.
GLOBAL_DECISION_RULES = [
    "Clause-majority matching: select the level whose clause set has the"
    " MOST explicitly evidenced clauses and NO directly contradicted clause;"
    " if two adjacent levels tie on evidenced-clause count, select the lower.",
    "Documented dysfunction dominates announced intent: strategies, funding,"
    " or frameworks that are announced but accompanied by cited evidence"
    " EXPLICITLY characterizing implementation as failed, delayed, or"
    " uncoordinated are scored at the level describing that reality."
    " The mere existence of multiple agencies or bodies is NOT dysfunction;"
    " a cited source must state the coordination problem.",
    "Projections do not count: market forecasts, announced or projected"
    " capacity, and growth-rate projections are not evidence of present"
    " capability; score on operating or contractually committed facts.",
]

DIMENSION_DECISION_RULES = {
    "ai_policy": [
        "The 'implementation uneven' cap to level 3 applies ONLY when a cited"
        " source explicitly characterizes implementation as uneven,"
        " fragmented, or uncoordinated (e.g., an external review finding).",
        "AI legislation still pending (proposed, under review, not yet law)"
        " is a 'mixed regulatory signal' consistent with level 3, not"
        " 'generally permissive regulation'.",
        "Level 5 requires all of: a national strategy with an explicit"
        " leadership goal; committed (not proposed) dedicated funding; and"
        " NO cited evidence of binding AI-specific regulatory obligations"
        " that delay deployment. Sectoral rules and voluntary frameworks do"
        " not count as regulatory friction.",
    ],
    "permitting_standard": [
        "Score the DEFAULT path only; ignore SEZ/fast-track evidence entirely"
        " (it belongs to permitting_fasttrack).",
        "When documented standard-path timelines span two rubric bands, score"
        " the band containing the MIDPOINT of the documented range. General"
        " infrastructure-quality rankings alone do not move the score below"
        " the timeline-derived band.",
        "A documented standard-path project completion ratio below 25% caps"
        " the score at 2.",
    ],
    "permitting_fasttrack": [
        "Score on documented EXPEDITED OUTCOMES, not the mere existence of an"
        " instrument; an announced instrument with no achieved timelines is at"
        " most level 2.",
        "Breadth of access moves the score: a fast-track open only to one zone"
        " or sector is at most level 4 even with strong documented outcomes.",
    ],
    "value_capture": [
        "Fiscal reserves count as 'large' when cited evidence shows reserve"
        " returns funding 10% or more of government spending, or documented"
        " drawdown capacity of comparable scale; 'demonstrated history of"
        " economic pivots' is satisfied by one or more cited historical"
        " structural transitions.",
        "A resource-taxation regime is 'unstable' ONLY when evidence"
        " documents enacted changes to taxation/royalty terms within the"
        " last five years, or active nationalization/expropriation risk."
        " Proposed-but-unenacted changes and rate variation across"
        " sub-national jurisdictions do not constitute instability.",
        "Absence of a sovereign wealth fund does not by itself force the"
        " score below 4; an SWF is required only at level 5.",
    ],
    "tech_stack": [
        "Level 5 requires ALL THREE elements with evidence: (a) deep"
        " integration with the leading stack, (b) secure advanced chip access"
        " (leading-edge allocation or domestic fabrication; import flows alone"
        " are insufficient), and (c) hosting critical AI infrastructure"
        " (operating frontier-scale compute). Missing any one means at most 4.",
        "The 'secure advanced chip access' requirement applies to level 5"
        " ONLY. For level 4, import dependency combined with documented"
        " technology-alliance participation and operating or contractually"
        " committed hyperscaler capacity qualifies as 'manageable'.",
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
