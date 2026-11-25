import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from aism.dataset import build_dataset
from aism.llm import MockClient, Tracked, parse_json
from aism.system import compile_verdict, run_multiagent, run_baseline
from aism.evaluation import score, summarize, run_experiments
import pandas as pd, tempfile

CASES = build_dataset(30, 42)


class T(unittest.TestCase):
    def test_dataset_reproducible(self):
        self.assertEqual(CASES, build_dataset(30, 42))
        self.assertEqual({c["split"] for c in CASES}, {"dev", "test"})

    def test_compiler_rules(self):
        m = lambda v, mand=True: {"verdict": v, "mandatory": mand}
        self.assertEqual(compile_verdict([m("met"), m("not_met"), m("needs_evidence")]), "NOT_ELIGIBLE")
        self.assertEqual(compile_verdict([m("met"), m("needs_evidence")]), "NEEDS_EVIDENCE")
        self.assertEqual(compile_verdict([m("met"), m("not_met", False)]), "ELIGIBLE")

    def test_parse_json(self):
        self.assertEqual(parse_json('```json\n{"a":1}\n```'), {"a": 1})
        self.assertEqual(parse_json('texto {"a":2} fim'), {"a": 2})
        self.assertIsNone(parse_json("sem json"))

    def test_mock_is_perfect_without_noise(self):
        for c in CASES:
            for fn in (run_multiagent, ):
                r = fn(Tracked(MockClient()), c["notice_text"], c["company_text"])
                s = score(c, r)
                self.assertEqual(s["correct"], 1, c["id"]); self.assertEqual(s["crit_correct"], s["crit_total"], c["id"])
            r = run_baseline(Tracked(MockClient()), c["notice_text"], c["company_text"])
            self.assertEqual(score(c, r)["correct"], 1, c["id"])

    def test_flaky_llm_does_not_crash(self):
        c = CASES[1]
        r = run_multiagent(Tracked(MockClient(flaky=1.0)), c["notice_text"], c["company_text"])
        self.assertIn("manager_failed", r.notes)
        self.assertIn(r.overall, ("NEEDS_EVIDENCE",))   # degradação conservadora
        r = run_baseline(Tracked(MockClient(flaky=1.0)), c["notice_text"], c["company_text"])
        self.assertIn("baseline_failed", r.notes)

    def test_experiment_resume(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "runs.csv"; cases = CASES[:3]
            run_experiments(lambda rep: MockClient(seed=rep), cases, ["baseline", "multiagent"], 2, out, log=lambda *_: None)
            n1 = len(pd.read_csv(out))
            run_experiments(lambda rep: MockClient(seed=rep), cases, ["baseline", "multiagent"], 2, out, log=lambda *_: None)
            self.assertEqual(n1, len(pd.read_csv(out))); self.assertEqual(n1, 12)
            s = summarize(pd.read_csv(out)); self.assertEqual(list(s.config), ["baseline", "multiagent"])


if __name__ == "__main__":
    unittest.main()
