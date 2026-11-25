"""Gera data/cases.json (dataset sintético, seed fixa). Uso: python scripts/build_dataset.py"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from aism.dataset import build_dataset

cases = build_dataset(30, 42)
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(cases), "casos;", dict(collections.Counter(c["split"] for c in cases)),
      dict(collections.Counter(c["truth_overall"] for c in cases)))
