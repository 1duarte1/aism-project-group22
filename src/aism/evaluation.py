"""Métricas, execução das experiências e agregação (tudo a partir de CSV)."""
from __future__ import annotations
import csv, json, time
from pathlib import Path
import pandas as pd
from .llm import Tracked
from .system import CONFIGS

RUN_COLS = ["config", "case", "rep", "truth", "pred", "correct", "false_approval", "crit_correct", "crit_total",
            "calls", "messages", "prompt_tokens", "completion_tokens", "seconds", "failures", "notes", "crit_pred"]


def score(case: dict, res) -> dict:
    truth = {c["label"]: c["truth"] for c in case["criteria"]}
    ok = sum(1 for k, v in truth.items() if res.criteria.get(k) == v)
    return {"truth": case["truth_overall"], "pred": res.overall,
            "correct": int(res.overall == case["truth_overall"]),
            "false_approval": int(res.overall == "ELIGIBLE" and case["truth_overall"] != "ELIGIBLE"),
            "crit_correct": ok, "crit_total": len(truth), "crit_pred": json.dumps(res.criteria, ensure_ascii=False)}


def run_experiments(make_client, cases, configs, reps, out_csv: Path, resume=True, log=print):
    """make_client(rep)->cliente LLM (permite fixar uma seed por repetição). Escreve linha a linha."""
    done = set()
    if resume and out_csv.exists():
        d = pd.read_csv(out_csv); done = set(zip(d.config, d.case, d.rep))
    new = not out_csv.exists() or not resume
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w" if new else "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RUN_COLS)
        if new: w.writeheader()
        for rep in range(reps):
            client = make_client(rep)
            for cfg in configs:
                for case in cases:
                    if (cfg, case["id"], rep) in done: continue
                    tc = Tracked(client)
                    try:
                        res = CONFIGS[cfg](tc, case["notice_text"], case["company_text"])
                    except Exception as e:  # erro de rede/API: regista e continua
                        from .system import Result
                        res = Result("NEEDS_EVIDENCE", {}, notes=[f"exception:{type(e).__name__}:{e}"][:1])
                    s = score(case, res)
                    w.writerow({"config": cfg, "case": case["id"], "rep": rep, **s, "calls": tc.stats.calls,
                                "messages": len(res.messages), "prompt_tokens": tc.stats.prompt_tokens,
                                "completion_tokens": tc.stats.completion_tokens, "seconds": round(tc.stats.seconds, 3),
                                "failures": tc.stats.failures, "notes": ";".join(res.notes)})
                    f.flush()
            log(f"rep {rep + 1}/{reps} concluída")


def summarize(runs: pd.DataFrame) -> pd.DataFrame:
    """Métricas por (config, rep) e depois média e desvio-padrão entre repetições."""
    rows = []
    for (cfg, rep), g in runs.groupby(["config", "rep"]):
        ne = g[g.truth != "ELIGIBLE"]
        rows.append({"config": cfg, "rep": rep,
                     "verdict_accuracy": g.correct.mean(),
                     "false_approval_rate": ne.false_approval.mean() if len(ne) else float("nan"),
                     "criterion_accuracy": g.crit_correct.sum() / g.crit_total.sum(),
                     "llm_calls_per_case": g.calls.mean(), "messages_per_case": g.messages.mean(),
                     "tokens_per_case": (g.prompt_tokens + g.completion_tokens).mean(),
                     "seconds_per_case": g.seconds.mean(), "failed_parses_per_case": g.failures.mean()})
    per_rep = pd.DataFrame(rows)
    cols = [c for c in per_rep.columns if c not in ("config", "rep")]
    mean = per_rep.groupby("config")[cols].mean().add_suffix("_mean")
    std = per_rep.groupby("config")[cols].std(ddof=1).fillna(0).add_suffix("_std")
    n = per_rep.groupby("config").size().rename("reps")
    order = [c for c in ("baseline", "multiagent", "ablation_no_compiler") if c in mean.index]
    return pd.concat([n, mean, std], axis=1).loc[order].reset_index()


def error_table(runs: pd.DataFrame, cases) -> pd.DataFrame:
    """Casos errados com causa provável automática (taxonomia simples, a rever à mão)."""
    truth = {c["id"]: {x["label"]: x["truth"] for x in c["criteria"]} for c in cases}
    rows = []
    for r in runs[runs.correct == 0].itertuples():
        pred = json.loads(r.crit_pred) if isinstance(r.crit_pred, str) else {}
        t = truth[r.case]
        wrong = sorted(k for k in t if pred.get(k) is not None and pred[k] != t[k])
        missing = sorted(k for k in t if k not in pred)
        if "manager_failed" in str(r.notes) or "baseline_failed" in str(r.notes): cause = "falha de formato/JSON"
        elif missing: cause = "critério não extraído"
        elif wrong: cause = "critério avaliado incorretamente"
        else: cause = "agregação final errada"
        rows.append({"config": r.config, "case": r.case, "rep": r.rep, "truth": r.truth, "pred": r.pred, "cause": cause,
                     "wrong_criteria": " ".join(wrong), "missing_criteria": " ".join(missing)})
    return pd.DataFrame(rows, columns=["config", "case", "rep", "truth", "pred", "cause", "wrong_criteria", "missing_criteria"])
