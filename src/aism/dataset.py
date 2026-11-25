"""Gerador do dataset SINTÉTICO de casos (aviso + ficha de empresa + verdade de referência).

Os avisos NÃO são textos oficiais: são avisos fictícios, com a estrutura típica dos avisos do
Portugal 2030 (objeto, dotação, condições de elegibilidade, critérios valorizados, prazos).
A verdade de referência é construída por regras determinísticas, logo é reprodutível (seed fixa).
"""
from __future__ import annotations
import random

REGIONS = ["Norte", "Centro", "Lisboa", "Alentejo", "Algarve", "Açores", "Madeira"]
CAE = {"C": "indústrias transformadoras", "F": "construção", "G": "comércio por grosso e a retalho",
       "H": "transportes e armazenagem", "I": "alojamento e restauração", "J": "informação e comunicação",
       "M": "atividades de consultoria, científicas e técnicas", "Q": "saúde humana e apoio social"}
MET, NOT_MET, NE = "met", "not_met", "needs_evidence"
ELIG, NOT_ELIG, NEED = "ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_EVIDENCE"

FICHA = [  # (campo, rótulo na ficha)
    ("nome", "Empresa"), ("regiao", "Região da sede (NUTS II)"), ("trabalhadores", "N.º de trabalhadores"),
    ("vn", "Volume de negócios anual (M€)"), ("balanco", "Balanço total anual (M€)"),
    ("contrib", "Situação perante a AT e a Segurança Social"), ("cae", "CAE principal (secção)"),
    ("dificuldade", "Empresa em dificuldade (Reg. UE 651/2014)"), ("anos", "Anos de atividade"),
    ("invest", "Investimento previsto (k€)"), ("postos", "Novos postos de trabalho a criar"),
    ("iniciado", "Despesas do projeto já iniciadas antes da candidatura"),
    ("export", "Peso das exportações no volume de negócios (%)"),
]
LABELS = [f"{c})" for c in "abcdefghij"]


def _pick(rng, seq):
    return seq[rng.randrange(len(seq))]


# ---------------------------------------------------------------- tipos de critério
# Cada tipo: render(params, rng)->texto ; evaluate(params, c)->veredicto ; fabricate(params, target, c, rng)
class PME:
    name = "pme"
    @staticmethod
    def params(rng): return {}
    @staticmethod
    def render(p, rng):
        return _pick(rng, [
            "Ser micro, pequena ou média empresa, isto é, empregar menos de 250 pessoas e ter um volume de negócios anual não superior a 50 milhões de euros ou um balanço total anual não superior a 43 milhões de euros;",
            "Enquadrar-se na definição de PME, com menos de 250 trabalhadores e volume de negócios anual até 50 milhões de euros ou balanço total anual até 43 milhões de euros;"])
    @staticmethod
    def evaluate(p, c):
        h, t, b = c.get("trabalhadores"), c.get("vn"), c.get("balanco")
        if h is not None and h >= 250: return NOT_MET
        if h is None: return NE
        if t is None and b is None: return NE
        if (t is not None and t <= 50) or (b is not None and b <= 43): return MET
        return NOT_MET if (t is not None and b is not None) else NE
    @staticmethod
    def fabricate(p, target, c, rng):
        bnd = rng.random() < 0.3
        if target == MET:
            c["trabalhadores"] = _pick(rng, [249]) if bnd else rng.randint(4, 230)
            c["vn"] = 50.0 if bnd else round(rng.uniform(0.3, 30), 1)
            c["balanco"] = round(rng.uniform(0.2, 60), 1)
        elif target == NOT_MET:
            if rng.random() < 0.5:
                c["trabalhadores"] = 250 if bnd else rng.randint(251, 900)
                c["vn"] = round(rng.uniform(5, 120), 1); c["balanco"] = round(rng.uniform(5, 90), 1)
            else:
                c["trabalhadores"] = rng.randint(30, 240)
                c["vn"] = 50.1 if bnd else round(rng.uniform(51, 120), 1)
                c["balanco"] = 43.1 if bnd else round(rng.uniform(44, 90), 1)
        else:
            c["trabalhadores"] = None if rng.random() < 0.6 else rng.randint(20, 200)
            c["vn"] = None; c["balanco"] = None


class Sede:
    name = "sede"
    @staticmethod
    def params(rng): return {"regioes": sorted(rng.sample(REGIONS, rng.randint(2, 4)))}
    @staticmethod
    def render(p, rng):
        r = ", ".join(p["regioes"])
        return _pick(rng, [f"Ter sede ou estabelecimento permanente numa das seguintes regiões NUTS II: {r};",
                           f"Estar sediada numa das regiões abrangidas pelo aviso, a saber: {r};"])
    @staticmethod
    def evaluate(p, c):
        r = c.get("regiao")
        return NE if r is None else (MET if r in p["regioes"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        if target == MET: c["regiao"] = _pick(rng, p["regioes"])
        elif target == NOT_MET: c["regiao"] = _pick(rng, [r for r in REGIONS if r not in p["regioes"]])
        else: c["regiao"] = None


class Contrib:
    name = "contrib"
    @staticmethod
    def params(rng): return {}
    @staticmethod
    def render(p, rng):
        return _pick(rng, ["Ter a situação contributiva regularizada perante a Autoridade Tributária e a Segurança Social;",
                           "Possuir a situação tributária e contributiva regularizada perante a AT e a Segurança Social;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("contrib")
        return NE if v is None else (MET if v == "regularizada" else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        c["contrib"] = {MET: "regularizada", NOT_MET: "dívida não regularizada", NE: None}[target]


class Cae:
    name = "cae"
    @staticmethod
    def params(rng): return {"secoes": sorted(rng.sample(list(CAE), rng.randint(2, 4)))}
    @staticmethod
    def render(p, rng):
        lst = ", ".join(f"{s} ({CAE[s]})" for s in p["secoes"])
        return _pick(rng, [f"Ter como atividade principal (CAE Rev.3) uma das seguintes secções: {lst};",
                           f"O CAE principal da empresa deve estar abrangido por uma das secções: {lst};"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("cae")
        return NE if v is None else (MET if v in p["secoes"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        if target == MET: c["cae"] = _pick(rng, p["secoes"])
        elif target == NOT_MET: c["cae"] = _pick(rng, [s for s in CAE if s not in p["secoes"]])
        else: c["cae"] = None


class Dificuldade:
    name = "dificuldade"
    @staticmethod
    def params(rng): return {}
    @staticmethod
    def render(p, rng):
        return _pick(rng, ["Não se encontrar em situação de empresa em dificuldade, nos termos do Regulamento (UE) n.º 651/2014;",
                           "Não ser classificada como empresa em dificuldade, de acordo com o Regulamento (UE) n.º 651/2014;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("dificuldade")
        return NE if v is None else (MET if v == "não" else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        c["dificuldade"] = {MET: "não", NOT_MET: "sim", NE: None}[target]


class Antiguidade:
    name = "antiguidade"
    @staticmethod
    def params(rng): return {"n": rng.randint(1, 3)}
    @staticmethod
    def render(p, rng):
        n = p["n"]; a = "ano" if n == 1 else "anos"
        return _pick(rng, [f"Ter, à data da candidatura, pelo menos {n} {a} de atividade;",
                           f"Exercer atividade há um mínimo de {n} {a} à data de submissão da candidatura;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("anos")
        return NE if v is None else (MET if v >= p["n"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        n = p["n"]; bnd = rng.random() < 0.4
        if target == MET: c["anos"] = n if bnd else rng.randint(n, n + 25)
        elif target == NOT_MET: c["anos"] = n - 1 if bnd else rng.randint(0, n - 1)
        else: c["anos"] = None


class Investimento:
    name = "invest"
    @staticmethod
    def params(rng): return {"k": _pick(rng, [50, 75, 100, 150, 200])}
    @staticmethod
    def render(p, rng):
        k = p["k"]
        return _pick(rng, [f"Apresentar um investimento total elegível igual ou superior a {k} mil euros;",
                           f"O projeto deve ter um investimento elegível mínimo de {k} mil euros;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("invest")
        return NE if v is None else (MET if v >= p["k"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        k = p["k"]; bnd = rng.random() < 0.4
        if target == MET: c["invest"] = k if bnd else rng.randint(k, k * 6)
        elif target == NOT_MET: c["invest"] = k - 5 if bnd else rng.randint(5, k - 10)
        else: c["invest"] = None


class Emprego:
    name = "postos"
    @staticmethod
    def params(rng): return {"n": rng.randint(1, 3)}
    @staticmethod
    def render(p, rng):
        n = p["n"]; s = "posto" if n == 1 else "postos"
        return _pick(rng, [f"Comprometer-se a criar, no mínimo, {n} {s} de trabalho líquido(s) até ao fim do projeto;",
                           f"Criar pelo menos {n} {s} de trabalho adicional(is) em resultado do projeto;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("postos")
        return NE if v is None else (MET if v >= p["n"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        n = p["n"]
        if target == MET: c["postos"] = rng.randint(n, n + 8)
        elif target == NOT_MET: c["postos"] = rng.randint(0, n - 1)
        else: c["postos"] = None


class NaoIniciado:
    name = "iniciado"
    @staticmethod
    def params(rng): return {}
    @staticmethod
    def render(p, rng):
        return _pick(rng, ["Não ter iniciado despesas do projeto antes da data da candidatura;",
                           "Garantir que o projeto não foi iniciado antes da submissão da candidatura;"])
    @staticmethod
    def evaluate(p, c):
        v = c.get("iniciado")
        return NE if v is None else (MET if v == "não" else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        c["iniciado"] = {MET: "não", NOT_MET: "sim", NE: None}[target]


class Exportacao:
    name = "export"
    @staticmethod
    def params(rng): return {"pct": _pick(rng, [10, 20, 30])}
    @staticmethod
    def render(p, rng):
        return f"Empresas com exportações iguais ou superiores a {p['pct']}% do volume de negócios;"
    @staticmethod
    def evaluate(p, c):
        v = c.get("export")
        return NE if v is None else (MET if v >= p["pct"] else NOT_MET)
    @staticmethod
    def fabricate(p, target, c, rng):
        x = p["pct"]
        if target == MET: c["export"] = rng.randint(x, 90)
        elif target == NOT_MET: c["export"] = rng.randint(0, x - 1)
        else: c["export"] = None


MANDATORY_TYPES = [PME, Sede, Contrib, Cae, Dificuldade, Antiguidade, Investimento, Emprego, NaoIniciado]
OPTIONAL_TYPES = [Exportacao]
PROGRAMS = ["Competir+ PME", "Norte Inovação Digital", "Centro Empresas 2030", "Alentejo Produtivo",
            "Digitalizar PME", "Transição Verde PME", "Emprego Qualificado", "Indústria 4.0 Regional"]
NAMES = ["Alfa", "Beta", "Cedro", "Delta", "Estrela", "Fénix", "Gaia", "Horizonte", "Íris", "Jade", "Kappa",
         "Luz", "Mar", "Nova", "Ouro", "Pinhal", "Quinta", "Rio", "Sol", "Tejo", "Urze", "Vale", "Zênite"]


def overall(criteria):
    m = [c["truth"] for c in criteria if c["mandatory"]]
    if NOT_MET in m: return NOT_ELIG
    if NE in m: return NEED
    return ELIG


def build_case(idx: int, rng: random.Random) -> dict:
    target_overall = rng.choices([ELIG, NOT_ELIG, NEED], weights=[3, 4, 3])[0]
    n_mand = rng.randint(4, 7)
    types = rng.sample(MANDATORY_TYPES, n_mand)
    opt = rng.sample(OPTIONAL_TYPES, rng.randint(0, 1))
    # alvo por critério obrigatório
    tg = [MET] * n_mand
    if target_overall == NOT_ELIG:
        for i in rng.sample(range(n_mand), rng.randint(1, 2)): tg[i] = NOT_MET
        for i in range(n_mand):
            if tg[i] == MET and rng.random() < 0.2: tg[i] = NE
    elif target_overall == NEED:
        for i in rng.sample(range(n_mand), rng.randint(1, 2)): tg[i] = NE
    company: dict = {}
    crit = []
    for t, target in zip(types, tg):
        p = t.params(rng); t.fabricate(p, target, company, rng)
        crit.append({"type": t.name, "mandatory": True, "params": p, "cls": t})
    for t in opt:
        p = t.params(rng); t.fabricate(p, rng.choice([MET, NOT_MET, NE]), company, rng)
        crit.append({"type": t.name, "mandatory": False, "params": p, "cls": t})
    company["nome"] = f"{rng.choice(NAMES)} {rng.choice(['Lda', 'S.A.', 'Unipessoal Lda'])}"
    # ordem: obrigatórios primeiro (artigo 3.º), depois valorizados (artigo 4.º)
    mand = [c for c in crit if c["mandatory"]]; rng.shuffle(mand)
    opts = [c for c in crit if not c["mandatory"]]
    ordered = mand + opts
    for lab, c in zip(LABELS, ordered):
        c["label"] = lab
        c["text"] = c["cls"].render(c["params"], rng)
        c["truth"] = c["cls"].evaluate(c["params"], company)
    prog = rng.choice(PROGRAMS)
    lines = [f"AVISO DE ABERTURA N.º {idx:02d}/2026 — Programa «{prog}» (Portugal 2030) [TEXTO FICTÍCIO]", "",
             "Artigo 1.º — Objeto",
             "1. O presente aviso destina-se a apoiar projetos de investimento produtivo e de modernização de empresas, "
             "contribuindo para a competitividade e a criação de emprego.",
             "", "Artigo 2.º — Dotação e taxa de apoio",
             f"1. A dotação indicativa é de {rng.choice([5, 8, 12, 20])} milhões de euros.",
             f"2. A taxa de apoio é de {rng.choice([30, 40, 45, 50])}% das despesas elegíveis, com um limite de "
             f"{rng.choice([150, 250, 400])} mil euros por projeto.",
             "", "Artigo 3.º — Condições de elegibilidade dos beneficiários",
             "Podem candidatar-se as entidades que cumpram, cumulativamente, os seguintes requisitos:"]
    for c in mand: lines.append(f"{c['label']} {c['text']}")
    if opts:
        lines += ["", "Artigo 4.º — Critérios valorizados (não eliminatórios)",
                  "Sem prejuízo do disposto no artigo anterior, a falta destes requisitos não determina a exclusão da "
                  "candidatura, sendo apenas valorizadas as empresas que cumpram:"]
        for c in opts: lines.append(f"{c['label']} {c['text']}")
    lines += ["", f"Artigo {5 if opts else 4}.º — Prazos e documentos",
              f"1. As candidaturas decorrem de {rng.randint(1, 9)} de março a {rng.randint(10, 28)} de abril de 2026.",
              "2. A candidatura é instruída com a documentação comprovativa dos requisitos acima referidos."]
    ficha = {k: company.get(k) for k, _ in FICHA}
    return {
        "id": f"case_{idx:02d}", "split": "dev" if idx % 5 == 0 else "test",
        "notice_text": "\n".join(lines), "company": ficha, "company_text": render_ficha(ficha, rng),
        "criteria": [{"label": c["label"], "type": c["type"], "mandatory": c["mandatory"], "truth": c["truth"]} for c in ordered],
        "truth_overall": overall(ordered), "target_overall": target_overall,
    }


def render_ficha(ficha: dict, rng: random.Random) -> str:
    out = []
    for k, lab in FICHA:
        v = ficha.get(k)
        if v is None:
            if rng.random() < 0.6: out.append(f"{lab}: não indicado")
            continue
        if k == "cae": v = f"{v} ({CAE[v]})"
        out.append(f"{lab}: {v}")
    return "\n".join(out)


def build_dataset(n: int = 30, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    cases = [build_case(i + 1, rng) for i in range(n)]
    for c in cases:
        assert c["truth_overall"] == c["target_overall"], c["id"]
    return cases
