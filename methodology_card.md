# Methodology Passport Card — Task 2

## 1. Project information

| | |
|---|---|
| **Title** | Predictors of Phishing and Social-Engineering Susceptibility Among University Students: The Role of Field of Study, Prior Training, and Self-Confidence |
| **Authors (pair)** | Alexander Grankin · Kenzhebaiuly Yerzhan |
| **Course** | SCOM3001-ENG-10 |
| **Repository** | https://github.com/Sszechss/phishing-susceptibility-students |
| **Builds on** | Task 1 report (research proposal, related-work matrix, literature synthesis, LitMap) |

## 2. Research type

**Quantitative** — cross-sectional survey with an embedded, objectively scored performance test
(18 simulated phishing / legitimate message vignettes), analysed as a **quasi-experimental group comparison**.

*Why quantitative:* all three research questions are stated as testable, directional hypotheses about
differences and gaps between numeric scores; the gap identified in Task 1 is precisely that existing student
studies rely on self-report and attitudes instead of an *objective, scored* detection measure; and the target
sample (n ≥ 80–100) is suited to inferential statistics, not to thematic analysis.

*Week-5 refinement:* field of study and prior training are **not randomly assigned**, so the design is
quasi-experimental. RQ2 was phrased as causal in Task 1; it is now tested as an *association adjusted for
covariates* (major, academic year, digital literacy). Causal language is avoided in the conclusions.

## 3. Hypotheses

| RQ | Null hypothesis (H0) | Alternative hypothesis (H1) | Test |
|---|---|---|---|
| **RQ1** Field of study | Mean detection accuracy of IT/security majors is **not higher** than that of non-IT majors (μ_IT ≤ μ_NonIT). | IT/security majors have **higher** mean detection accuracy than non-IT majors (μ_IT > μ_NonIT). | Welch t-test, one-sided; Mann–Whitney U as robustness check; Hedges g |
| **RQ2** Prior training | Students with prior cybersecurity training do **not** have higher accuracy than untrained students (μ_T ≤ μ_U); adjusted coefficient b_training ≤ 0. | Trained students have **higher** accuracy (μ_T > μ_U); b_training > 0 after controlling for major, year and digital literacy. | Welch t-test, one-sided + OLS regression with covariates |
| **RQ3a** Confidence gap | Mean per-item confidence **equals** actual accuracy (mean gap = 0, perfect calibration). | Mean confidence **differs** from accuracy (expected direction: over-confidence, gap > 0). | Paired t-test, two-sided; Wilcoxon signed-rank as robustness check |
| **RQ3b** Gap by cue | The over-confidence gap is the **same** for urgency, authority and familiarity cues. | The gap **differs** between at least two cue types. | Friedman test (within-subject); Spearman ρ for self-rated confidence vs accuracy |

Significance level α = 0.05; Holm–Bonferroni correction across the three primary tests (RQ1, RQ2, RQ3a).

## 4. Variable matrix

| Type | Variable | Operationalisation | Levels / scale |
|---|---|---|---|
| **Independent** | Field of study (RQ1) | Self-reported major, recoded | IT/security vs Non-IT (between-subject) |
| **Independent** | Prior cybersecurity training (RQ2) | "Have you completed any cybersecurity / phishing-awareness training?" + hours | Yes / No; hours as dose |
| **Independent** | Self-reported confidence (RQ3) | Pre-test rating "How confident are you that you can recognise phishing?" | Likert 1–7 |
| **Independent** | Social-engineering cue type (RQ3b) | Fixed by vignette design | Urgency / Authority / Familiarity (within-subject, 6 items each) |
| **Dependent** | **Detection accuracy** (primary) | % of 18 vignettes correctly classified as phishing / legitimate | 0–100 % |
| **Dependent** | Hit rate · False-alarm rate · d′ | Phishing items flagged · legitimate items wrongly flagged · signal-detection sensitivity | 0–1 · 0–1 · z-units |
| **Dependent** | Mean item confidence | "How sure are you?" after each vignette | 50–100 % |
| **Dependent** | Over-confidence gap | Mean item confidence − accuracy, overall and per cue | percentage points |
| **Controlled (held constant)** | Instrument | Same 18 vignettes, same answer key (`configs/config.yaml`, v0.1), randomised order, same online form | fixed |
| **Controlled (held constant)** | Data collection | Anonymous, voluntary, same instructions, one collection window (Week 7), no time pressure | fixed |
| **Controlled (held constant)** | Analysis environment | Python 3.13, pinned libraries (`requirements.txt`), Docker image, config SHA-256 logged per run | fixed |
| **Controlled (statistical)** | Academic year, age, digital literacy (and major in RQ2, training in RQ1 sensitivity check) | Entered as covariates | 1–4; years; 1–5 |

## 5. Metrics and baseline

**Primary metric — Detection accuracy (% correct on 18 vignettes).**
It is objective (scored against a fixed answer key rather than self-reported), directly answers RQ1–RQ2, and is
the basis of the RQ3 gap. Because each cue type contains both phishing (4) and legitimate (2) items, accuracy
rewards correct discrimination, not suspicion of everything.

**Secondary metrics:** hit rate, false-alarm rate, d′, per-cue accuracy, over-confidence gap (pp), effect sizes
(Hedges g, regression b), Holm-adjusted p-values.

**Guardrail metrics** (results are reported as valid only if these hold; checked automatically by `src/guardrails.py`):

| Guardrail | Threshold | Why |
|---|---|---|
| Attention check passed | must equal 5 | removes careless responders |
| Completion time | ≥ 180 s and ≤ 3600 s | < 10 s per vignette = scenarios not read |
| Missing vignette answers | ≤ 10 % per respondent | stable accuracy score |
| Straight-lining | not all 18 answers identical | removes non-discriminating responders |
| Overall exclusion rate | ≤ 20 % | sample stays representative |
| Group size per comparison | ≥ 30 per group | statistical power (see below) |
| Test reliability (KR-20) | ≥ 0.60 | the 18-item test measures one ability consistently |
| Item difficulty | 0.20–0.95 share correct | no item is trivial or impossible |
| False-alarm increase vs baseline group | ≤ 10 pp | higher accuracy must not come from flagging everything |
| Ethics | no names / e-mails / student IDs collected; no real phishing sent | anonymity and no harm to participants |

**Baselines:**

1. **Chance level = 50 %** — a respondent guessing on a binary phishing/legitimate judgement. Mean accuracy is
   first tested against this floor.
2. **Control groups** — *Non-IT majors* are the baseline for RQ1; *students without prior training* are the
   baseline for RQ2. These are naturally occurring groups, so differences are adjusted for covariates.
3. **Perfect calibration (gap = 0)** — the baseline for RQ3: a well-calibrated respondent's average confidence
   equals their accuracy.

**Power:** with α = 0.05 (one-sided) and 80 % power, a two-group comparison detects Hedges g ≈ 0.65 at 30 per
group, ≈ 0.57 at 40 per group (n = 80) and 0.50 at ≈ 51 per group (n ≈ 100). The paired RQ3 test with n = 80
detects d_z ≈ 0.32 (two-sided).

## 6. Measurement tool (repository)

`python src/benchmark.py --config configs/config.yaml` loads the survey CSV, applies the quality filters,
scores the vignettes, runs RQ1–RQ3, checks every guardrail and writes `metrics.json`, `respondent_scores.csv`,
`exclusions.csv` and `run.log` to `results/<run_id>/`. It has been tested on the 8-row synthetic sample in
`data/sample/` (2 rows deliberately fail quality filters) and is ready for the Week 7 data collection.
