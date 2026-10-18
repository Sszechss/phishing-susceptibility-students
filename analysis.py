"""Hypothesis tests for RQ1–RQ3.

RQ1  H1: IT majors have higher detection accuracy than non-IT majors   (Welch t, one-sided)
RQ2  H1: trained students have higher detection accuracy               (Welch t, one-sided + OLS with covariates)
RQ3  H1: mean item confidence differs from actual accuracy             (paired t, two-sided)
         + the gap differs by cue type (Friedman) and self-rated confidence vs accuracy (Spearman)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _r(x, nd: int = 4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd) + 0.0  # +0.0 removes "-0.0"


def _describe(x: pd.Series) -> dict:
    return {"n": int(x.count()), "mean": _r(x.mean()), "sd": _r(x.std(ddof=1)) if x.count() > 1 else None}


def hedges_g(a: pd.Series, b: pd.Series) -> float:
    na, nb = a.count(), b.count()
    pooled = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled == 0 or np.isnan(pooled):
        return float("nan")
    d = (a.mean() - b.mean()) / pooled
    return float(d * (1 - 3 / (4 * (na + nb) - 9)))


def two_group_test(scores: pd.DataFrame, data: pd.DataFrame, spec: dict, dv: str, min_n: int) -> dict:
    col = spec["column"]
    a = scores.loc[data[col] == spec["treatment"], dv].dropna()
    b = scores.loc[data[col] == spec["control"], dv].dropna()
    out = {"dv": dv, "treatment": _describe(a), "control (baseline)": _describe(b)}
    if a.count() < min_n or b.count() < min_n:
        out["status"] = "skipped: group too small"
        return out
    t = stats.ttest_ind(a, b, equal_var=False, alternative="greater")
    u = stats.mannwhitneyu(a, b, alternative="greater")
    out.update({
        "status": "ok",
        "test": "Welch t-test, one-sided (treatment > control)",
        "t": _r(t.statistic), "df": _r(t.df, 2), "p_value": _r(t.pvalue),
        "mean_difference": _r(a.mean() - b.mean()),
        "hedges_g": _r(hedges_g(a, b)),
        "robustness_mann_whitney_p": _r(u.pvalue),
    })
    return out


def ols(y: pd.Series, X: pd.DataFrame) -> dict:
    """Ordinary least squares with classical standard errors (numpy/scipy only)."""
    X = X.astype(float)
    Xc = np.column_stack([np.ones(len(X)), X.values])
    names = ["intercept"] + list(X.columns)
    n, k = Xc.shape
    if n <= k:
        return {"status": f"skipped: n={n} must exceed number of parameters k={k}"}
    beta, *_ = np.linalg.lstsq(Xc, y.values.astype(float), rcond=None)
    resid = y.values - Xc @ beta
    sigma2 = resid @ resid / (n - k)
    se = np.sqrt(np.diag(sigma2 * np.linalg.pinv(Xc.T @ Xc)))
    with np.errstate(divide="ignore", invalid="ignore"):
        tvals = beta / se
    p = 2 * stats.t.sf(np.abs(tvals), df=n - k)
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    return {
        "status": "ok", "n": n, "r_squared": _r(r2),
        "coefficients": {nm: {"b": _r(b), "se": _r(s), "p_value": _r(pv)} for nm, b, s, pv in zip(names, beta, se, p)},
    }


def run_rq1(scores, data, cfg) -> dict:
    return two_group_test(scores, data, cfg["groups"]["field_of_study"], "accuracy", cfg["analysis"]["min_n_per_group"])


def run_rq2(scores, data, cfg) -> dict:
    g = cfg["groups"]
    res = two_group_test(scores, data, g["training"], "accuracy", cfg["analysis"]["min_n_per_group"])
    X = pd.DataFrame({
        "prior_training": (data[g["training"]["column"]] == g["training"]["treatment"]).astype(int),
        "it_major": (data[g["field_of_study"]["column"]] == g["field_of_study"]["treatment"]).astype(int),
    })
    for cov in g["covariates"]:
        X[cov] = data[cov]
    res["adjusted_model"] = {"formula": "accuracy ~ prior_training + it_major + " + " + ".join(g["covariates"]),
                             **ols(scores["accuracy"], X)}
    return res


def run_rq3(scores, data, cfg) -> dict:
    conf, acc = scores["mean_item_confidence"], scores["accuracy"]
    out = {"mean_item_confidence": _describe(conf), "accuracy": _describe(acc),
           "overconfidence_pp": _r(100 * (conf - acc).mean(), 2)}
    if conf.count() < 2:
        out["status"] = "skipped: n < 2"
        return out
    t = stats.ttest_rel(conf, acc)
    out.update({"status": "ok", "test": "paired t-test, two-sided (confidence vs accuracy)",
                "t": _r(t.statistic), "p_value": _r(t.pvalue)})
    if (conf - acc).abs().sum() > 0:
        out["robustness_wilcoxon_p"] = _r(stats.wilcoxon(conf, acc).pvalue)

    cues = sorted({m["cue"] for m in cfg["items"].values()})
    by_cue = {c: _r(100 * scores[f"overconfidence_{c}"].mean(), 2) for c in cues}
    out["overconfidence_by_cue_pp"] = by_cue
    try:
        fr = stats.friedmanchisquare(*[scores[f"overconfidence_{c}"] for c in cues])
        out["cue_difference"] = {"test": "Friedman", "chi2": _r(fr.statistic), "p_value": _r(fr.pvalue)}
    except ValueError as e:
        out["cue_difference"] = {"status": f"skipped: {e}"}

    sr = data[cfg["confidence"]["self_rating_column"]]
    rho = stats.spearmanr(sr, acc)
    out["self_rating_vs_accuracy"] = {"test": "Spearman", "rho": _r(rho.statistic), "p_value": _r(rho.pvalue)}
    return out


def holm(pvals: dict) -> dict:
    """Holm–Bonferroni adjusted p-values for the family of primary tests."""
    valid = {k: v for k, v in pvals.items() if v is not None}
    ordered = sorted(valid.items(), key=lambda kv: kv[1])
    m, running, adj = len(ordered), 0.0, {}
    for i, (k, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = round(running, 4)
    return {k: adj.get(k) for k in pvals}
