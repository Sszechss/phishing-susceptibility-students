"""Data-quality filters (respondent level) and guardrail metrics (study level)."""
from __future__ import annotations

import pandas as pd

from scoring import correctness_matrix, item_columns, kr20


def apply_exclusions(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (kept respondents, exclusion log with one reason per excluded row)."""
    qf = cfg["quality_filters"]
    item_ids = list(cfg["items"].keys())
    resp_cols, _ = item_columns(item_ids)

    reasons = pd.Series("", index=df.index, dtype="object")

    def flag(mask: pd.Series, reason: str) -> None:
        empty = reasons == ""
        reasons[mask & empty] = reason

    if qf.get("require_consent", True):
        flag(df["consent"].astype(str).str.lower() != "yes", "no_consent")
    ac = qf["attention_check"]
    flag(df[ac["column"]] != ac["expected"], "failed_attention_check")
    flag(df["completion_seconds"] < qf["min_completion_seconds"], "too_fast")
    flag(df["completion_seconds"] > qf["max_completion_seconds"], "too_slow")
    flag(df[resp_cols].isna().mean(axis=1) > qf["max_missing_item_share"], "too_many_missing")
    if qf.get("exclude_straightliners", True):
        flag(df[resp_cols].nunique(axis=1, dropna=True) <= 1, "straightlining")

    excluded = df.loc[reasons != "", ["respondent_id"]].assign(reason=reasons[reasons != ""])
    return df.loc[reasons == ""].copy(), excluded


def check_guardrails(raw: pd.DataFrame, kept: pd.DataFrame, cfg: dict, runtime_s: float) -> dict:
    g = cfg["guardrails"]
    grp = cfg["groups"]
    results = {}

    def record(name: str, value, threshold, ok: bool) -> None:
        results[name] = {"value": value, "threshold": threshold, "status": "PASS" if ok else "FAIL"}

    excl_rate = 1 - len(kept) / len(raw) if len(raw) else 1.0
    record("exclusion_rate", round(excl_rate, 3), f"<= {g['max_exclusion_rate']}", excl_rate <= g["max_exclusion_rate"])

    for key in ("field_of_study", "training"):
        col = grp[key]["column"]
        counts = kept[col].value_counts()
        smallest = int(min(counts.get(grp[key]["treatment"], 0), counts.get(grp[key]["control"], 0)))
        record(f"min_group_size_{key}", smallest, f">= {g['min_group_size']}", smallest >= g["min_group_size"])

    correct = correctness_matrix(kept, cfg["items"])
    rel = kr20(correct)
    record("reliability_kr20", None if pd.isna(rel) else round(rel, 3),
           f">= {g['min_reliability_kr20']}", (not pd.isna(rel)) and rel >= g["min_reliability_kr20"])

    lo, hi = g["item_difficulty_range"]
    difficulty = correct.mean(axis=0)
    bad_items = difficulty[(difficulty < lo) | (difficulty > hi)].round(2).to_dict()
    record("items_outside_difficulty_range", bad_items, f"share correct in [{lo}, {hi}]", len(bad_items) == 0)

    # Over-suspicion guardrail: a group "wins" on accuracy only if it is not simply flagging
    # everything as phishing, i.e. its false-alarm rate on legitimate items is not much higher.
    legit = [i for i, m in cfg["items"].items() if m["is_phishing"] == 0]
    fa = kept[legit].mean(axis=1)
    for key in ("field_of_study", "training"):
        col = grp[key]["column"]
        diff = fa[kept[col] == grp[key]["treatment"]].mean() - fa[kept[col] == grp[key]["control"]].mean()
        diff = None if pd.isna(diff) else round(float(diff), 3)
        record(f"false_alarm_increase_{key}", diff, f"<= {g['max_false_alarm_increase']}",
               diff is not None and diff <= g["max_false_alarm_increase"])

    record("runtime_seconds", round(runtime_s, 3), f"<= {g['max_runtime_seconds']}", runtime_s <= g["max_runtime_seconds"])
    return results
