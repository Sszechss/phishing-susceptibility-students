"""Data ingestion, warm-up filtering and statistical aggregation.

Mapping of the benchmark vocabulary onto the phishing-susceptibility study:
    latency            -> response time of a student to one message (seconds)
    load               -> social-engineering cue type (urgency / authority / familiarity)
    error rate         -> share of wrong answers (guardrail metric)
    warm-up            -> the two practice messages at the start (phase == "warmup")
    baseline/proposed  -> students without / with prior cybersecurity training
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42          # fixed seed: every bootstrap below is reproducible
N_BOOT = 2000      # bootstrap resamples
BASELINE = "Untrained (baseline)"
PROPOSED = "Trained (proposed)"


# --------------------------------------------------------------------------- #
# 1. Ingestion and warm-up filtering
# --------------------------------------------------------------------------- #
def load_jsonl(path: str | Path) -> pd.DataFrame:
    """Read the raw .jsonl log (one answer per line) into a DataFrame."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    if "source" not in df:
        df["source"] = "real"
    df["source"] = df["source"].fillna("real")
    df["response_time_s"] = df["response_time_ms"] / 1000.0
    df["error"] = (~df["correct"].astype(bool)).astype(int)
    df["group"] = np.where(df["prior_training"] == 1, PROPOSED, BASELINE)
    df["confidence"] = df["confidence_pct"] / 100.0   # 0.5-1.0, same scale as accuracy
    return df


MIN_RT_S = 1.0   # pre-stated rule: answers faster than 1 s are treated as accidental clicks


def apply_quality_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop failed attention checks and implausibly fast answers; report what was dropped."""
    n0, r0 = len(df), df["respondent"].nunique()
    bad = df.loc[df["attention_check"] != 5, "respondent"].unique()
    df = df[~df["respondent"].isin(bad)]
    n1 = len(df)
    df = df[df["response_time_s"] >= MIN_RT_S]
    info = dict(rows_in=n0, respondents_in=r0, respondents_failed_attention=len(bad),
                rows_too_fast=n1 - len(df), rows_out=len(df),
                respondents_out=df["respondent"].nunique())
    return df, info


def split_warmup(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (warm-up rows, evaluation rows). Only evaluation rows are analysed."""
    return df[df["phase"] == "warmup"].copy(), df[df["phase"] == "eval"].copy()


# --------------------------------------------------------------------------- #
# 2. Statistics
# --------------------------------------------------------------------------- #
def cluster_bootstrap_ci(df: pd.DataFrame, value: str, stat_fn,
                         n_boot: int = N_BOOT, seed: int = SEED,
                         alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI, resampling whole respondents (cluster bootstrap).

    One student answers several e-mails, so single answers are not independent;
    we therefore resample students, not rows. Returns (nan, nan) for < 2 students.
    """
    arrays = [g[value].to_numpy() for _, g in df.groupby("respondent")]
    k = len(arrays)
    if k < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, k, k)
        stats[b] = stat_fn(np.concatenate([arrays[i] for i in idx]))
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def summarize(df_eval: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Aggregate evaluation rows by the given columns."""
    out = []
    for key, g in df_eval.groupby(by):
        key = key if isinstance(key, tuple) else (key,)
        rt = g["response_time_s"].to_numpy()
        m_lo, m_hi = cluster_bootstrap_ci(g, "response_time_s", np.median)
        e_lo, e_hi = cluster_bootstrap_ci(g, "error", np.mean)
        acc = 1 - g["error"].mean()
        conf = g["confidence"].mean()
        row = dict(zip(by, key))
        row.update(
            n_respondents=g["respondent"].nunique(),
            n_answers=len(g),
            median_s=np.median(rt),
            p25_s=np.percentile(rt, 25),
            p75_s=np.percentile(rt, 75),
            p95_s=np.percentile(rt, 95),
            p99_s=np.percentile(rt, 99),
            median_ci_lo=m_lo,
            median_ci_hi=m_hi,
            mean_s=rt.mean(),
            sd_s=rt.std(ddof=1) if len(rt) > 1 else np.nan,
            error_rate=g["error"].mean(),
            error_ci_lo=e_lo,
            error_ci_hi=e_hi,
            accuracy=acc,
            mean_confidence=conf,
            # confidence 0.5-1.0 (share), accuracy 0-1: positive gap = overconfident
            overconfidence_gap=conf - acc,
        )
        out.append(row)
    return pd.DataFrame(out)


def baseline_vs_proposed(df_eval: pd.DataFrame) -> pd.DataFrame:
    """Compact table for the README: baseline vs proposed (median p25-p75, mean +- SD)."""
    s = summarize(df_eval, ["group"]).set_index("group")
    rows = []
    for name in (BASELINE, PROPOSED):
        if name not in s.index:
            continue
        r = s.loc[name]
        rows.append({
            "Group": name,
            "Students": int(r.n_respondents),
            "Answers": int(r.n_answers),
            "Response time, median (p25-p75), s": f"{r.median_s:.1f} ({r.p25_s:.1f}-{r.p75_s:.1f})",
            "Response time, mean +- SD, s": f"{r.mean_s:.1f} +- {r.sd_s:.1f}",
            "p95 / p99, s": f"{r.p95_s:.1f} / {r.p99_s:.1f}",
            "Median 95% CI, s": f"[{r.median_ci_lo:.1f}; {r.median_ci_hi:.1f}]",
            "Error rate (guardrail), %": f"{100 * r.error_rate:.1f}",
            "Error 95% CI, %": f"[{100 * r.error_ci_lo:.1f}; {100 * r.error_ci_hi:.1f}]",
        })
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame) -> str:
    """Tiny DataFrame -> GitHub markdown table (no extra dependencies)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Aggregate raw survey log into metrics_summary.csv")
    ap.add_argument("--raw", default="data/raw/test_run.jsonl")
    ap.add_argument("--out", default="data/processed/metrics_summary.csv")
    ap.add_argument("--exclude-synthetic", action="store_true")
    a = ap.parse_args()
    data = load_jsonl(a.raw)
    if a.exclude_synthetic:
        data = data[data["source"] != "synthetic"]
    _, ev = split_warmup(data)
    ev, info = apply_quality_filters(ev)
    print("quality filters:", info)
    res = pd.concat([summarize(ev, ["group", "cue_type"]).assign(channel="all"),
                     summarize(ev, ["group", "channel"]).assign(cue_type="all")],
                    ignore_index=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(a.out, index=False)
    print(f"saved {a.out}: {len(res)} rows")
