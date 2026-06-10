# Gramercy WS4 - CGM (Chessboard Governance Multiplier)

Scores 6 countries (US, AE, BR, IN, SG, PH) on 5 governance dimensions using
structured 1-5 rubrics, an LLM rater panel (2 blind raters + arbiter), and a
Cohen's-kappa QA gate. Fourth index in the Gramercy capstone (WS1 SDI, WS2 CII,
WS3 CLDV).

**CGM = 0.25*AIPolicy + 0.20*Permitting + 0.20*ValueCapture + 0.20*TechStack + 0.15*Workforce**

> **Status: PROVISIONAL — first live run (2026-06-09) FAILED the inter-rater
> kappa gate on 3 of 5 dimensions** (ai_policy 0.571, tech_stack 0.500,
> permitting 0.455 vs the 0.7 gate; pooled kappa 0.741, adjacent agreement
> 100%). Scores exist in `v_cgm_latest` but are not publishable until rater
> calibration brings every dimension over the gate. See
> `docs/CGM_METHODOLOGY.md` §7.

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # fill POSTGRES_*, ANTHROPIC_API_KEY, TAVILY_API_KEY
.venv/bin/python cgm/setup_cgm.py
```

## Usage
```bash
cd cgm
python run_cgm.py               # full pipeline
python run_cgm.py --only rate   # one phase: anchors|evidence|rate|arbitrate|score|verify|gap
```

See `docs/CGM_METHODOLOGY.md` and `docs/superpowers/specs/2026-06-09-cgm-csi-design.md`.
