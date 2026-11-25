"""Corre o sistema multiagente (ou a baseline / ablação) num caso e mostra o parecer.
Uso: python scripts/run_system.py --case case_02 [--config multiagent] [--backend openai|mock]"""
import argparse
from _common import load_cases, make_client_factory
from aism.llm import Tracked
from aism.system import CONFIGS
from aism.evaluation import score

ap = argparse.ArgumentParser()
ap.add_argument("--case", default="case_02"); ap.add_argument("--config", default="multiagent", choices=list(CONFIGS))
ap.add_argument("--backend", default="openai", choices=["openai", "mock"]); ap.add_argument("--noise", type=float, default=0.0)
a = ap.parse_args()
case = next(c for c in load_cases("all") if c["id"] == a.case)
tc = Tracked(make_client_factory(a.backend, a.noise)(0))
res = CONFIGS[a.config](tc, case["notice_text"], case["company_text"])
print(f"== {case['id']} | config={a.config} | backend={a.backend}")
print("Critérios (label -> veredicto | verdade):")
truth = {c["label"]: c["truth"] for c in case["criteria"]}
for k, v in res.criteria.items():
    print(f"  {k:3} {v:15} | {truth.get(k, '?')}")
print(f"Parecer: {res.overall}   (verdade: {case['truth_overall']})")
if res.evidence: print("Evidência em falta:", res.evidence)
print(f"Chamadas LLM: {tc.stats.calls} | mensagens: {len(res.messages)} | tempo: {tc.stats.seconds:.2f}s | notas: {res.notes or '-'}")
print("Resultado do score:", {k: v for k, v in score(case, res).items() if k != 'crit_pred'})
