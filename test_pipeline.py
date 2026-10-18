"""Smoke and unit tests (standard-library unittest, no extra dependencies).

Run:  python -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import benchmark  # noqa: E402
from analysis import holm  # noqa: E402
from guardrails import apply_exclusions  # noqa: E402
from scoring import kr20, score_respondents  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "config.yaml").read_text(encoding="utf-8"))
SAMPLE = pd.read_csv(ROOT / "data" / "sample" / "survey_sample.csv")


class TestScoring(unittest.TestCase):
    def test_perfect_respondent_scores_100(self):
        row = SAMPLE.iloc[[0]].copy()
        for item, meta in CFG["items"].items():
            row[item] = meta["is_phishing"]
        s = score_respondents(row, CFG).iloc[0]
        self.assertAlmostEqual(s["accuracy"], 1.0)
        self.assertAlmostEqual(s["hit_rate"], 1.0)
        self.assertAlmostEqual(s["false_alarm_rate"], 0.0)

    def test_answer_key_is_balanced_by_cue(self):
        for cue in ("urgency", "authority", "familiarity"):
            flags = [m["is_phishing"] for m in CFG["items"].values() if m["cue"] == cue]
            self.assertEqual((sum(flags), len(flags)), (4, 6))

    def test_kr20_range(self):
        from scoring import correctness_matrix
        r = kr20(correctness_matrix(SAMPLE, CFG["items"]))
        self.assertTrue(r != r or -1 <= r <= 1)  # NaN allowed for degenerate data


class TestQualityFilters(unittest.TestCase):
    def test_sample_exclusions(self):
        kept, excluded = apply_exclusions(SAMPLE, CFG)
        self.assertEqual(len(kept), 6)
        self.assertEqual(set(excluded["reason"]), {"failed_attention_check", "too_fast"})


class TestStats(unittest.TestCase):
    def test_holm_monotone(self):
        adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertEqual(adj, {"a": 0.03, "b": 0.06, "c": 0.06})


class TestEndToEnd(unittest.TestCase):
    def test_pipeline_writes_outputs(self):
        self.assertEqual(benchmark.main(["--config", "configs/config.yaml"]), 0)
        run = sorted((ROOT / "results").glob("*_sample"))[-1]
        for f in ("metrics.json", "respondent_scores.csv", "exclusions.csv", "run.log"):
            self.assertTrue((run / f).exists(), f)
        m = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(m["sample"]["n_analysed"], 6)
        self.assertIn("RQ3_confidence_gap", m["hypothesis_tests"])


if __name__ == "__main__":
    unittest.main()
