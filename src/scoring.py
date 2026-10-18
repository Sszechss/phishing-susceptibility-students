"""Scoring of the 18-vignette phishing detection test.

Input  : one row per respondent with
         V01..V18  — judgement, 1 = "this is phishing", 0 = "this is legitimate"
         C01..C18  — confidence in that judgement, 50–100 (%)
Output : per-respondent dependent variables (accuracy, hit / false-alarm rate,
         d-prime, confidence, over-confidence) overall and by social-engineering cue.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def item_columns(item_ids: list[str]) -> tuple[list[str], list[str]]:
    """Map V-item ids to their matching confidence columns (V01 -> C01)."""
    resp_cols = list(item_ids)
    conf_cols = ["C" + i[1:] for i in item_ids]
    return resp_cols, conf_cols


def correctness_matrix(df: pd.DataFrame, items: dict) -> pd.DataFrame:
    """1 if the respondent's judgement matches the answer key, 0 if not, NaN if missing."""
    out = {}
    for item_id, meta in items.items():
        resp = df[item_id]
        out[item_id] = np.where(resp.isna(), np.nan, (resp == meta["is_phishing"]).astype(float))
    return pd.DataFrame(out, index=df.index)


def _dprime(hit_rate: pd.Series, fa_rate: pd.Series, n_signal: int, n_noise: int) -> pd.Series:
    """Signal-detection sensitivity with log-linear correction (Hautus, 1995)
    so that hit / false-alarm rates of 0 or 1 do not produce infinite values."""
    h = (hit_rate * n_signal + 0.5) / (n_signal + 1)
    f = (fa_rate * n_noise + 0.5) / (n_noise + 1)
    return pd.Series(norm.ppf(h) - norm.ppf(f), index=hit_rate.index)


def score_respondents(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    items: dict = cfg["items"]
    item_ids = list(items.keys())
    _, conf_cols = item_columns(item_ids)
    lo, hi = cfg["confidence"]["item_scale"]

    correct = correctness_matrix(df, items)
    conf = df[conf_cols].astype(float).clip(lo, hi) / 100.0
    conf.columns = item_ids

    phish = [i for i, m in items.items() if m["is_phishing"] == 1]
    legit = [i for i, m in items.items() if m["is_phishing"] == 0]

    scores = pd.DataFrame(index=df.index)
    scores["respondent_id"] = df["respondent_id"]
    # ---- Primary DV
    scores["accuracy"] = correct.mean(axis=1)
    # ---- Secondary DVs (signal detection)
    scores["hit_rate"] = df[phish].mean(axis=1)            # phishing correctly flagged
    scores["false_alarm_rate"] = df[legit].mean(axis=1)    # legitimate wrongly flagged
    scores["d_prime"] = _dprime(scores["hit_rate"], scores["false_alarm_rate"], len(phish), len(legit))
    # ---- Confidence / calibration (RQ3)
    scores["mean_item_confidence"] = conf.mean(axis=1)
    scores["overconfidence"] = scores["mean_item_confidence"] - scores["accuracy"]

    for cue in sorted({m["cue"] for m in items.values()}):
        ids = [i for i, m in items.items() if m["cue"] == cue]
        scores[f"accuracy_{cue}"] = correct[ids].mean(axis=1)
        scores[f"confidence_{cue}"] = conf[ids].mean(axis=1)
        scores[f"overconfidence_{cue}"] = scores[f"confidence_{cue}"] - scores[f"accuracy_{cue}"]

    return scores


def kr20(correct: pd.DataFrame) -> float:
    """Kuder–Richardson 20 reliability of a dichotomously scored test."""
    c = correct.dropna()
    k = c.shape[1]
    if len(c) < 2 or k < 2:
        return float("nan")
    p = c.mean(axis=0)
    total_var = c.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return float(k / (k - 1) * (1 - (p * (1 - p)).sum() / total_var))
