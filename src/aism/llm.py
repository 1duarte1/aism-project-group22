"""Camada de LLM: cliente OpenAI real + MockClient offline (apenas para testar a canalização)."""
from __future__ import annotations
import json, os, random, re, time
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class OpenAIClient:
    """Cliente real. Lê OPENAI_API_KEY, MODEL_NAME e TEMPERATURE do ambiente (.env)."""
    name = "openai"

    def __init__(self, model: str | None = None, temperature: float | None = None, seed: int | None = None):
        from dotenv import load_dotenv
        load_dotenv()
        from openai import OpenAI  # importação tardia: o mock não precisa do SDK
        self.client = OpenAI()
        self.model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.temperature = float(os.getenv("TEMPERATURE", "0")) if temperature is None else temperature
        self.seed = seed

    def complete(self, role: str, system: str, user: str) -> LLMResponse:
        r = self.client.chat.completions.create(
            model=self.model, temperature=self.temperature, seed=self.seed,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        u = r.usage
        return LLMResponse(r.choices[0].message.content or "", u.prompt_tokens, u.completion_tokens)


def parse_json(text: str):
    """Extrai o primeiro objeto JSON de um texto (tolera cercas ```json). Devolve None se falhar."""
    if not text: return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, flags=re.S)
        if m:
            try: return json.loads(m.group(0))
            except Exception: return None
    return None


@dataclass
class Stats:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    failures: int = 0  # respostas inválidas (JSON/esquema)


class Tracked:
    """Envolve um cliente e conta chamadas, tokens e tempo de UM caso."""
    def __init__(self, client):
        self.client, self.stats = client, Stats()

    def complete(self, role, system, user):
        t0 = time.perf_counter()
        r = self.client.complete(role, system, user)
        self.stats.seconds += time.perf_counter() - t0
        self.stats.calls += 1
        self.stats.prompt_tokens += r.prompt_tokens
        self.stats.completion_tokens += r.completion_tokens
        return r


def call_json(tc: Tracked, role: str, system: str, user: str, validate, retries: int = 2):
    """Chama o LLM e valida o JSON. Repete até `retries` vezes; devolve (obj|None)."""
    for _ in range(retries + 1):
        obj = parse_json(tc.complete(role, system, user).text)
        if obj is not None:
            try:
                if validate(obj): return obj
            except Exception:
                pass
        tc.stats.failures += 1
    return None


# ----------------------------------------------------------------------------- MOCK
@dataclass
class MockClient:
    """LLM FALSO e determinístico, só para testar o código sem rede nem chave de API.
    NÃO é um modelo de linguagem: aplica regras às mesmas frases do dataset sintético.
    Resultados obtidos com ele NÃO podem ser usados no relatório.
    `noise`: prob. de trocar o veredicto de um critério; `flaky`: prob. de devolver texto não-JSON."""
    noise: float = 0.0
    flaky: float = 0.0
    seed: int = 0
    name: str = "mock"
    _n: int = field(default=0, repr=False)

    def complete(self, role: str, system: str, user: str) -> LLMResponse:
        self._n += 1
        rng = random.Random(f"{self.seed}|{role}|{user}|{self._n}")
        if rng.random() < self.flaky:
            return LLMResponse("desculpe, não consegui produzir JSON", 10, 5)
        out = getattr(self, f"_{role}")(user, rng)
        txt = json.dumps(out, ensure_ascii=False)
        return LLMResponse(txt, len(user) // 4, len(txt) // 4)

    # --- helpers de leitura do texto
    @staticmethod
    def _ficha(txt):
        d = {}
        for ln in txt.splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1); v = v.strip()
                d[k.strip()] = None if v.lower() == "não indicado" or not v else v
        return d

    @staticmethod
    def _num(v):
        return None if v is None else float(re.search(r"[\d.]+", v).group(0))

    def _eval(self, text: str, ficha: dict):
        g = lambda k: ficha.get(k)
        n = self._num
        MET, NOT, NE = "met", "not_met", "needs_evidence"
        if "250" in text:
            h, t, b = n(g("N.º de trabalhadores")), n(g("Volume de negócios anual (M€)")), n(g("Balanço total anual (M€)"))
            if h is not None and h >= 250: return NOT
            if h is None or (t is None and b is None): return NE
            if (t is not None and t <= 50) or (b is not None and b <= 43): return MET
            return NOT if (t is not None and b is not None) else NE
        if "regiões" in text:
            r = g("Região da sede (NUTS II)")
            if r is None: return NE
            return MET if re.search(r"\b" + re.escape(r) + r"\b", text) else NOT
        if "contributiva" in text:
            v = g("Situação perante a AT e a Segurança Social")
            return NE if v is None else (MET if v == "regularizada" else NOT)
        if "CAE" in text:
            v = g("CAE principal (secção)")
            if v is None: return NE
            return MET if re.search(r"\b" + v[0] + r" \(", text) else NOT
        if "dificuldade" in text:
            v = g("Empresa em dificuldade (Reg. UE 651/2014)")
            return NE if v is None else (MET if v == "não" else NOT)
        if "atividade" in text and "ano" in text:
            v = n(g("Anos de atividade")); k = int(re.search(r"(\d+) anos?", text).group(1))
            return NE if v is None else (MET if v >= k else NOT)
        if "mil euros" in text:
            v = n(g("Investimento previsto (k€)")); k = int(re.search(r"(\d+) mil euros", text).group(1))
            return NE if v is None else (MET if v >= k else NOT)
        if "posto" in text:
            v = n(g("Novos postos de trabalho a criar")); k = int(re.search(r"(\d+) postos?", text).group(1))
            return NE if v is None else (MET if v >= k else NOT)
        if "iniciad" in text:
            v = g("Despesas do projeto já iniciadas antes da candidatura")
            return NE if v is None else (MET if v == "não" else NOT)
        if "exportações" in text:
            v = n(g("Peso das exportações no volume de negócios (%)")); k = int(re.search(r"(\d+)%", text).group(1))
            return NE if v is None else (MET if v >= k else NOT)
        return "needs_evidence"

    def _flip(self, v, rng):
        if rng.random() < self.noise:
            return rng.choice([x for x in ("met", "not_met", "needs_evidence") if x != v])
        return v

    @staticmethod
    def _extract(notice: str):
        crit, optional = [], False
        for ln in notice.splitlines():
            if "não eliminatórios" in ln: optional = True
            m = re.match(r"^([a-j]\))\s+(.*)$", ln.strip())
            if m: crit.append({"label": m.group(1), "text": m.group(2), "mandatory": not optional})
        return crit

    @staticmethod
    def _rule(items):
        m = [i["verdict"] for i in items if i["mandatory"]]
        return "NOT_ELIGIBLE" if "not_met" in m else ("NEEDS_EVIDENCE" if "needs_evidence" in m else "ELIGIBLE")

    # --- papéis
    def _manager(self, user, rng):
        return {"criteria": self._extract(user.split("NOTICE:", 1)[1])}

    def _assessor(self, user, rng):
        crit = re.search(r"CRITERION \((.*?)\): (.*?)\n\nCOMPANY SHEET:\n(.*)", user, flags=re.S)
        v = self._flip(self._eval(crit.group(2), self._ficha(crit.group(3))), rng)
        return {"verdict": v, "justification": f"(mock) {v}"}

    def _evidence(self, user, rng):
        items = json.loads(user.split("ASSESSMENTS:", 1)[1])
        return {"evidence": [{"label": i["label"], "needed": "(mock) documento comprovativo"} for i in items
                             if i["verdict"] == "needs_evidence"]}

    def _compiler_llm(self, user, rng):
        items = json.loads(user.split("ASSESSMENTS:", 1)[1])
        return {"overall": self._rule(items), "reason": "(mock)"}

    def _baseline(self, user, rng):
        notice, comp = user.split("NOTICE:", 1)[1].split("COMPANY SHEET:", 1)
        ficha = self._ficha(comp); items = []
        for c in self._extract(notice):
            items.append({"label": c["label"], "mandatory": c["mandatory"],
                          "verdict": self._flip(self._eval(c["text"], ficha), rng), "justification": "(mock)"})
        return {"criteria": items, "overall": self._rule(items), "missing_evidence": []}
