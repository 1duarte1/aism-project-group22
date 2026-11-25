import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def load_cases(split=None):
    cases = json.loads((ROOT / "data" / "cases.json").read_text(encoding="utf-8"))
    return [c for c in cases if split in (None, "all", c["split"])]

def make_client_factory(backend, noise=0.0, flaky=0.0, base_seed=1000):
    from aism.llm import MockClient
    if backend == "mock":
        return lambda rep: MockClient(noise=noise, flaky=flaky, seed=base_seed + rep)
    from aism.llm import OpenAIClient
    return lambda rep: OpenAIClient(seed=base_seed + rep)
