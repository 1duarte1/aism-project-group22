"""Sistema multiagente hierárquico (Manager -> Assessors -> Evidence Lister -> Compiler), baseline e ablação.

Coordenação: supervisor/hierárquico. O Manager é o único que lê o aviso inteiro; cada Assessor recebe
APENAS um critério + a ficha da empresa (mensagens diretas, registadas em `messages`).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .llm import Tracked, call_json

VERDICTS = ("met", "not_met", "needs_evidence")
OVERALL = ("ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_EVIDENCE")

MANAGER_SYS = ("You are the MANAGER of a tender-eligibility screening team. Read a funding notice and extract EVERY "
               "eligibility criterion that an applicant must (or is scored on) satisfy. Ignore objective, budget, "
               "deadlines and procedure. Keep each criterion's label exactly as written in the notice (e.g. 'a)'). "
               "Set mandatory=false only for criteria the notice explicitly says are non-eliminatory / merely valued. "
               'Answer ONLY with JSON: {"criteria":[{"label":"a)","text":"...","mandatory":true}]}')
ASSESSOR_SYS = ("You are an ASSESSOR. You judge ONE eligibility criterion for ONE company, using only the company sheet. "
                "met = the sheet proves the criterion is satisfied; not_met = the sheet proves it is violated; "
                "needs_evidence = the required information is missing or not enough to decide (never guess). "
                "Apply thresholds literally (e.g. 'at least N' means >= N; 'less than N' means < N). "
                'Answer ONLY with JSON: {"verdict":"met|not_met|needs_evidence","justification":"one line"}')
EVIDENCE_SYS = ("You are the EVIDENCE LISTER. For every assessment with verdict needs_evidence, say in one short line "
                "what document or information the applicant must provide. "
                'Answer ONLY with JSON: {"evidence":[{"label":"a)","needed":"..."}]}')
COMPILER_LLM_SYS = ("You are a COMPILER. Given criterion assessments, decide the overall eligibility: "
                    "ELIGIBLE, NOT_ELIGIBLE or NEEDS_EVIDENCE. "
                    'Answer ONLY with JSON: {"overall":"ELIGIBLE|NOT_ELIGIBLE|NEEDS_EVIDENCE","reason":"one line"}')
BASELINE_SYS = ("You are a tender-eligibility screener. Given a funding notice and a company sheet, assess EVERY eligibility "
                "criterion in the notice (keep labels like 'a)'), then give the overall result: ELIGIBLE, NOT_ELIGIBLE or "
                "NEEDS_EVIDENCE. Use needs_evidence when the sheet lacks the information (never guess); mark "
                "mandatory=false for criteria the notice says are non-eliminatory. "
                'Answer ONLY with JSON: {"criteria":[{"label":"a)","mandatory":true,"verdict":"met|not_met|needs_evidence",'
                '"justification":"..."}],"overall":"ELIGIBLE|NOT_ELIGIBLE|NEEDS_EVIDENCE","missing_evidence":["..."]}')


@dataclass
class Result:
    overall: str
    criteria: dict            # label -> verdict
    evidence: list = field(default_factory=list)
    messages: list = field(default_factory=list)   # (remetente, destinatário, tipo)
    notes: list = field(default_factory=list)      # degradações/erros tratados


def compile_verdict(items: list[dict]) -> str:
    """Compiler determinístico: um 'not_met' obrigatório prevalece; depois 'needs_evidence'; senão ELIGIBLE."""
    m = [i["verdict"] for i in items if i["mandatory"]]
    if "not_met" in m: return "NOT_ELIGIBLE"
    if "needs_evidence" in m: return "NEEDS_EVIDENCE"
    return "ELIGIBLE"


def _ok_manager(o):
    return isinstance(o["criteria"], list) and len(o["criteria"]) > 0 and all(
        isinstance(c["label"], str) and isinstance(c["text"], str) for c in o["criteria"])


def run_multiagent(tc: Tracked, notice: str, company: str, compiler: str = "deterministic") -> Result:
    msgs, notes = [], []
    msgs.append(("user", "manager", "notice"))
    plan = call_json(tc, "manager", MANAGER_SYS, f"NOTICE:\n{notice}", _ok_manager)
    if plan is None:  # erro do Manager: degrada para um único critério (o aviso inteiro)
        notes.append("manager_failed")
        criteria = [{"label": "?", "text": "Overall eligibility described in the notice", "mandatory": True}]
    else:
        criteria = [{"label": c["label"].strip(), "text": c["text"], "mandatory": bool(c.get("mandatory", True))}
                    for c in plan["criteria"]]
    items = []
    for c in criteria:
        msgs.append(("manager", "assessor", c["label"]))
        r = call_json(tc, "assessor", ASSESSOR_SYS,
                      f"CRITERION ({c['label']}): {c['text']}\n\nCOMPANY SHEET:\n{company}",
                      lambda o: o["verdict"] in VERDICTS)
        if r is None:  # erro do Assessor: conservador -> needs_evidence
            notes.append(f"assessor_failed:{c['label']}")
            r = {"verdict": "needs_evidence", "justification": "assessor failed"}
        msgs.append(("assessor", "manager", c["label"]))
        items.append({**c, "verdict": r["verdict"], "justification": r.get("justification", "")})
    evidence = []
    if any(i["verdict"] == "needs_evidence" for i in items):
        msgs.append(("manager", "evidence_lister", "assessments"))
        ev = call_json(tc, "evidence", EVIDENCE_SYS, "ASSESSMENTS:" + _dump(items), lambda o: isinstance(o["evidence"], list))
        evidence = ev["evidence"] if ev else []
        if ev is None: notes.append("evidence_failed")
        msgs.append(("evidence_lister", "manager", "evidence"))
    msgs.append(("manager", "compiler", "assessments"))
    if compiler == "deterministic":
        overall = compile_verdict(items)
    else:  # ablação: o Compiler passa a ser um LLM
        r = call_json(tc, "compiler_llm", COMPILER_LLM_SYS, "ASSESSMENTS:" + _dump(items), lambda o: o["overall"] in OVERALL)
        if r is None:
            notes.append("compiler_llm_failed"); overall = "NEEDS_EVIDENCE"
        else:
            overall = r["overall"]
    return Result(overall, {i["label"]: i["verdict"] for i in items}, evidence, msgs, notes)


def run_baseline(tc: Tracked, notice: str, company: str) -> Result:
    r = call_json(tc, "baseline", BASELINE_SYS, f"NOTICE:\n{notice}\n\nCOMPANY SHEET:\n{company}",
                  lambda o: o["overall"] in OVERALL and isinstance(o["criteria"], list))
    if r is None:
        return Result("NEEDS_EVIDENCE", {}, [], [("user", "baseline", "notice")], ["baseline_failed"])
    crit = {c["label"].strip(): c["verdict"] for c in r["criteria"] if c.get("verdict") in VERDICTS}
    return Result(r["overall"], crit, r.get("missing_evidence", []), [("user", "baseline", "notice")], [])


def _dump(items):
    import json
    return json.dumps([{"label": i["label"], "mandatory": i["mandatory"], "verdict": i["verdict"],
                        "justification": i.get("justification", "")} for i in items], ensure_ascii=False)


CONFIGS = {
    "baseline": lambda tc, n, c: run_baseline(tc, n, c),
    "multiagent": lambda tc, n, c: run_multiagent(tc, n, c, "deterministic"),
    "ablation_no_compiler": lambda tc, n, c: run_multiagent(tc, n, c, "llm"),
}
