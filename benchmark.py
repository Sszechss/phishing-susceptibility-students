"""Measurement pipeline — Predictors of Phishing Susceptibility among University Students.

Usage:
    python src/benchmark.py --config configs/config.yaml

Steps: load config → load survey CSV → validate schema → apply quality filters →
score detection test → test hypotheses RQ1–RQ3 → check guardrail metrics →
write results/<run_id>/{metrics.json, respondent_scores.csv, exclusions.csv, run.log}.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import yaml

from analysis import holm, run_rq1, run_rq2, run_rq3
from guardrails import apply_exclusions, check_guardrails
from scoring import item_columns, score_respondents

ROOT = Path(__file__).resolve().parents[1]
BASE_COLUMNS = ["respondent_id", "consent", "major_group", "academic_year", "age", "prior_training",
                "training_hours", "digital_literacy", "self_confidence", "attention_check", "completion_seconds"]


def load_config(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text), hashlib.sha256(text.encode()).hexdigest()[:12]


def validate_schema(df: pd.DataFrame, cfg: dict) -> None:
    resp, conf = item_columns(list(cfg["items"].keys()))
    missing = [c for c in BASE_COLUMNS + resp + conf if c not in df.columns]
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")
    bad = df[resp].stack().pipe(lambda s: s[~s.isin([0, 1])])
    if len(bad):
        raise ValueError("Vignette responses (V01..V18) must be 0 = legitimate or 1 = phishing")


def setup_logging(log_file: Path) -> logging.Logger:
    log = logging.getLogger("benchmark")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
    for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, encoding="utf-8")):
        h.setFormatter(fmt)
        log.addHandler(h)
    return log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/config.yaml", help="path to config.yaml")
    ap.add_argument("--input", default=None, help="override paths.input_csv from the config")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    cfg_path = (ROOT / args.config) if not Path(args.config).is_absolute() else Path(args.config)
    cfg, cfg_hash = load_config(cfg_path)
    input_csv = ROOT / (args.input or cfg["paths"]["input_csv"])

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{cfg['experiment']['mode']}"
    out_dir = ROOT / cfg["paths"]["output_dir"] / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log = setup_logging(out_dir / "run.log")

    log.info("Run %s | experiment=%s v%s | config sha256=%s",
             run_id, cfg["experiment"]["name"], cfg["experiment"]["version"], cfg_hash)
    log.info("Input: %s", input_csv.relative_to(ROOT))

    raw = pd.read_csv(input_csv)
    validate_schema(raw, cfg)
    log.info("Loaded %d respondents, %d vignettes", len(raw), len(cfg["items"]))

    kept, excluded = apply_exclusions(raw, cfg)
    log.info("Quality filters: kept %d, excluded %d %s", len(kept), len(excluded),
             excluded["reason"].value_counts().to_dict() if len(excluded) else "")

    scores = score_respondents(kept, cfg)
    log.info("Mean detection accuracy = %.1f%% (chance baseline = %.0f%%)",
             100 * scores["accuracy"].mean(), 100 * cfg["analysis"]["chance_level"])

    chance = scipy.stats.ttest_1samp(scores["accuracy"], cfg["analysis"]["chance_level"], alternative="greater") \
        if len(scores) > 1 else None
    rq1, rq2, rq3 = run_rq1(scores, kept, cfg), run_rq2(scores, kept, cfg), run_rq3(scores, kept, cfg)
    adj = holm({"RQ1": rq1.get("p_value"), "RQ2": rq2.get("p_value"), "RQ3": rq3.get("p_value")})
    alpha = cfg["analysis"]["alpha"]
    decisions = {k: (None if p is None else ("reject H0" if p < alpha else "fail to reject H0")) for k, p in adj.items()}
    for k, rq in (("RQ1", rq1), ("RQ2", rq2), ("RQ3", rq3)):
        log.info("%s: status=%s p=%s p_holm=%s → %s", k, rq.get("status"), rq.get("p_value"), adj[k], decisions[k])

    runtime = time.perf_counter() - t0
    guard = check_guardrails(raw, kept, cfg, runtime)
    for name, g in guard.items():
        (log.info if g["status"] == "PASS" else log.warning)("Guardrail %-37s %s (value=%s, %s)",
                                                             name, g["status"], g["value"], g["threshold"])

    metrics = {
        "run_id": run_id,
        "config_sha256": cfg_hash,
        "mode": cfg["experiment"]["mode"],
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                        "scipy": scipy.__version__, "pyyaml": yaml.__version__, "os": platform.platform()},
        "sample": {"n_loaded": len(raw), "n_analysed": len(kept), "n_excluded": len(excluded)},
        "primary_metric": {"name": "detection_accuracy",
                           "mean": round(float(scores["accuracy"].mean()), 4),
                           "vs_chance_p_value": None if chance is None else round(float(chance.pvalue), 4)},
        "hypothesis_tests": {"RQ1_field_of_study": rq1, "RQ2_prior_training": rq2, "RQ3_confidence_gap": rq3},
        "holm_adjusted_p": adj,
        "decisions_at_alpha": {"alpha": alpha, **decisions},
        "guardrails": guard,
        "runtime_seconds": round(runtime, 3),
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    scores.round(4).to_csv(out_dir / "respondent_scores.csv", index=False)
    excluded.to_csv(out_dir / "exclusions.csv", index=False)
    log.info("Results written to %s (%.2f s)", out_dir.relative_to(ROOT), runtime)

    failed = [k for k, g in guard.items() if g["status"] == "FAIL"]
    if failed and cfg["guardrails"].get("fail_on_violation", False):
        log.error("Guardrail violation(s): %s", failed)
        return 2
    if failed:
        log.warning("Guardrail warnings in %s mode (expected for the 8-row sample): %s",
                    cfg["experiment"]["mode"], failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
