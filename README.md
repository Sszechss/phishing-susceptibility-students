# Predictors of Phishing and Social-Engineering Susceptibility Among University Students

**The Role of Field of Study, Prior Training, and Self-Confidence**

**Authors:** Alexander Grankin · Kenzhebaiuly Yerzhan
**Course:** SCOM3001-ENG-10 — Research Methods (Task 2: Methodology Card & Research Repository)
**Status:** measurement pipeline tested on a synthetic sample; full data collection planned for Week 7.

---

## Overview

Phishing studies of university students mostly report *self-reported* knowledge or attitudes, while
objective-performance models are built for corporate employees. This project measures students' **actual
detection accuracy** on 18 simulated phishing / legitimate messages and tests which individual factors predict it.

### Research questions

| | Question | Primary test |
|---|---|---|
| **RQ1** | Does phishing detection accuracy differ between IT/security majors and non-IT majors? | Welch t-test (one-sided) |
| **RQ2** | Is prior cybersecurity training associated with higher detection accuracy, after controlling for major, year and digital literacy? | Welch t-test + OLS with covariates |
| **RQ3** | Is there a gap between students' confidence and their actual accuracy, and does it differ by cue type (urgency, authority, familiarity)? | Paired t-test + Friedman test |

Full hypotheses, variable matrix, metrics and baselines: [`docs/methodology_card.md`](docs/methodology_card.md).
Survey items and answer key: [`docs/survey_instrument.md`](docs/survey_instrument.md), [`configs/config.yaml`](configs/config.yaml).

## Repository structure

```
phishing-susceptibility-students/
├── .github/workflows/ci.yml     # builds the Docker image and runs tests + pipeline on every push
├── configs/
│   └── config.yaml              # ALL experiment parameters: IV groups, answer key, filters, guardrails
├── data/
│   ├── raw/                     # full survey export (git-ignored, never committed)
│   └── sample/
│       └── survey_sample.csv    # 8 synthetic respondents for pipeline testing
├── docs/
│   ├── methodology_card.md      # Methodology Passport Card
│   └── survey_instrument.md     # questionnaire + 18 vignettes
├── notebooks/                   # exploratory analysis (Week 8+)
├── results/                     # run outputs, one folder per run (git-ignored)
├── scripts/
│   └── run.sh                   # one-command local run without Docker
├── src/
│   ├── benchmark.py             # entry point: load → filter → score → test → guardrails → write
│   ├── scoring.py               # accuracy, hit / false-alarm rate, d′, confidence gap, KR-20
│   ├── analysis.py              # RQ1–RQ3 statistical tests, Holm correction
│   └── guardrails.py            # respondent filters + study-level guardrail metrics
├── tests/
│   └── test_pipeline.py         # unit + end-to-end tests (stdlib unittest)
├── Dockerfile
├── requirements.txt             # exact pins of the full dependency tree
├── LICENSE                      # MIT
└── README.md
```

## Planned benchmarks (analyses)

| ID | Comparison | Primary metric | Baseline | Statistic | Decision rule |
|---|---|---|---|---|---|
| B0 | All students vs guessing | Detection accuracy | 50 % chance level | one-sample t | p < .05 |
| B1 (RQ1) | IT vs Non-IT majors | Detection accuracy | Non-IT majors | Welch t (one-sided), Hedges g | Holm-adj. p < .05 |
| B2 (RQ2) | Trained vs untrained | Detection accuracy; b_training | Untrained students | Welch t + OLS (major, year, digital literacy) | Holm-adj. p < .05 |
| B3 (RQ3a) | Confidence vs accuracy | Over-confidence gap (pp) | Perfect calibration (gap = 0) | paired t, Wilcoxon | Holm-adj. p < .05 |
| B4 (RQ3b) | Urgency vs authority vs familiarity | Gap per cue (pp) | Equal gaps | Friedman χ² | p < .05 |
| B5 | Self-rating vs accuracy | Spearman ρ | ρ = 0 | Spearman | p < .05 |

**Guardrails** (checked on every run, reported in `metrics.json`): exclusion rate ≤ 20 %, ≥ 30 respondents per group,
KR-20 ≥ 0.60, item difficulty 0.20–0.95, false-alarm increase vs baseline ≤ 10 pp, runtime ≤ 60 s.

## System requirements

* **Option A:** Docker ≥ 20.10 (any OS) — nothing else needed.
* **Option B:** Python 3.13 and `pip` (Linux, macOS or Windows).
* ~200 MB disk space for the image / virtual environment; no GPU, no internet access during the run.

## Quickstart

**Docker (recommended)**

```bash
git clone https://github.com/Sszechss/phishing-susceptibility-students.git && cd phishing-susceptibility-students
docker build -t phishing-study .
docker run --rm -v "$(pwd)/results:/app/results" phishing-study
```

> Windows PowerShell: replace `$(pwd)` with `${PWD}`.

**Python (without Docker)**

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --no-deps -r requirements.txt
python src/benchmark.py --config configs/config.yaml
```

or simply `bash scripts/run.sh` (creates the venv, runs the tests and the pipeline).

**Expected output** — a new folder `results/<timestamp>_sample/` containing:

| File | Content |
|---|---|
| `run.log` | step-by-step log: exclusions, accuracy, RQ1–RQ3 p-values, guardrail PASS/FAIL |
| `metrics.json` | all test statistics, effect sizes, Holm-adjusted p-values, guardrails, environment versions, config hash |
| `respondent_scores.csv` | per-respondent accuracy, hit / false-alarm rate, d′, confidence and gap by cue |
| `exclusions.csv` | excluded respondents and the reason |

On the 8-row sample 2 respondents are excluded (attention check, too fast) and several guardrails report
`FAIL` (group size, reliability). This is expected: the sample only verifies that the pipeline runs end to end;
the guardrails are meant for the full dataset (`mode: full`, `fail_on_violation: true`).

**Tests:** `python -m unittest discover -s tests -v`

## Running on the full dataset (Week 7)

1. Export the form responses to `data/raw/survey_responses.csv` using the column names in `docs/survey_instrument.md`.
2. In `configs/config.yaml` set `mode: full`, `input_csv: data/raw/survey_responses.csv`, `fail_on_violation: true`.
3. Run the same Quickstart command. Raw data stays local — `data/raw/` is git-ignored.

## Ethics

Participation is anonymous and voluntary with an informed-consent item; no names, e-mail addresses or student IDs
are collected. Vignettes are mock-ups of fictitious organisations shown inside the questionnaire — **no real
phishing messages are sent to anyone.** The sample file contains synthetic data only.

## Citation

```bibtex
@misc{grankin_kenzhebaiuly_2026_phishing,
  author = {Grankin, Alexander and Kenzhebaiuly, Yerzhan},
  title  = {Predictors of Phishing and Social-Engineering Susceptibility Among University Students},
  year   = {2026},
  howpublished = {\url{https://github.com/Sszechss/phishing-susceptibility-students}},
  note   = {SCOM3001-ENG-10 research project}
}
```

## License

Code and documentation are released under the [MIT License](LICENSE).
