"""Reproduz as experiências: baseline vs multiagente vs ablação, com repetições.
Uso: python scripts/run_experiments.py --backend openai --reps 5 --split test
Escreve results/<backend>/runs.csv (uma linha por config/caso/repetição). Retoma se interrompido."""
import argparse, json
from pathlib import Path
from _common import ROOT, load_cases, make_client_factory
from aism.evaluation import run_experiments

ap = argparse.ArgumentParser()
ap.add_argument("--backend", default="openai", choices=["openai", "mock"])
ap.add_argument("--reps", type=int, default=5); ap.add_argument("--split", default="test")
ap.add_argument("--configs", default="baseline,multiagent,ablation_no_compiler")
ap.add_argument("--noise", type=float, default=0.0, help="(só mock) prob. de erro por critério")
ap.add_argument("--flaky", type=float, default=0.0, help="(só mock) prob. de resposta não-JSON")
ap.add_argument("--limit", type=int, default=0, help="usar só os N primeiros casos (testes rápidos)")
ap.add_argument("--fresh", action="store_true", help="ignorar resultados anteriores")
a = ap.parse_args()
cases = load_cases(a.split)[: a.limit or None]
out = ROOT / "results" / (a.backend if a.split == "test" else f"{a.backend}_{a.split}")  # dev nunca se mistura com teste
out.mkdir(parents=True, exist_ok=True)
run_experiments(make_client_factory(a.backend, a.noise, a.flaky), cases, a.configs.split(","), a.reps,
                out / "runs.csv", resume=not a.fresh)
meta = {"backend": a.backend, "reps": a.reps, "split": a.split, "n_cases": len(cases), "configs": a.configs.split(","),
        "noise": a.noise, "flaky": a.flaky, "base_seed": 1000}
if a.backend == "openai":
    import os; from dotenv import load_dotenv; load_dotenv()
    meta.update(model=os.getenv("MODEL_NAME", "gpt-4o-mini"), temperature=float(os.getenv("TEMPERATURE", "0")))
(out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print("Concluído:", out / "runs.csv")
