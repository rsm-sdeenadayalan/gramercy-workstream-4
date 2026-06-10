# Gramercy WS4 - CGM (Chessboard Governance Multiplier)

Scores 6 countries (US, AE, BR, IN, SG, PH) on 5 governance dimensions using
structured 1-5 rubrics, an LLM rater panel (2 blind raters + arbiter), and a
Cohen's-kappa QA gate. Fourth index in the Gramercy capstone (WS1 SDI, WS2 CII,
WS3 CLDV).

**CGM = 0.25*AIPolicy + 0.20*Permitting + 0.20*ValueCapture + 0.20*TechStack + 0.15*Workforce**

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
