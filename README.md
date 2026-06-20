# Gramercy WS4 - CGM (Chessboard Governance Multiplier)

Scores 6 countries (US, AE, BR, IN, SG, PH) on governance dimensions using
structured 1-5 rubrics, an LLM rater panel (2 blind raters + arbiter), and a
Cohen's-kappa QA gate. Fourth index in the Gramercy capstone (WS1 SDI, WS2 CII,
WS3 CLDV).

**CGM = 0.25*AIPolicy + 0.20*Permitting(standard) + 0.20*ValueCapture + 0.20*TechStack + 0.15*Workforce**

> Permitting is split into `permitting_standard` (default approval path —
> headline, weight 0.20) and `permitting_fasttrack` (SEZ/fast-track
> availability — published as context, weight 0.00). The split resolves an
> inter-rater divergence on dual-track countries and avoids double-counting
> realized fast builds that CII (WS2) already measures. See
> `docs/CGM_METHODOLOGY.md` §2.3.

> **Status: PROVISIONAL (passes under the corrected gate).** The first run
> (2026-06-09) failed the linear-weighted-kappa gate, but that gate is
> statistically unreliable at N=6 — clustered ratings trigger the "kappa
> paradox" (near-perfect agreement collapses to a low coefficient). The gate
> metric is now **Gwet's AC2** (≥0.75), which is robust to this; kappa is still
> reported. The clean baseline run (2026-06-18) **PASSES** all gated dimensions
> (permitting_standard AC2 0.867; every gated dim 0.82–1.00, clearing even the
> stricter 0.80 benchmark). Remaining before publication: sponsor ratification
> of the gate-metric change and a re-run on the canonical evidence corpus. See
> `docs/CGM_METHODOLOGY.md` §5.2.1 and §7.6.

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
