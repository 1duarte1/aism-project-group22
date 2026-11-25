# aism-project-group22

**Tender Eligibility Screener** — sistema multiagente hierárquico que faz a triagem de elegibilidade de uma PME face a um aviso de apoios (estilo Portugal 2030). Projeto final de AISM, Grupo 22.

## 1. O que o projeto faz

Entrada: texto de um aviso + ficha da empresa. Saída: parecer global (`ELIGIBLE`, `NOT_ELIGIBLE`, `NEEDS_EVIDENCE`), veredicto por critério (`met`, `not_met`, `needs_evidence`) e evidência em falta.

- **Manager**: decompõe o aviso, em tempo de execução, num número variável de critérios (nenhum critério escrito à mão no código).
- **Assessors** (um por critério): avaliam o critério com uma justificação de uma linha.
- **Evidence Lister**: lista a evidência em falta.
- **Compiler**: lógica determinística; um critério obrigatório `not_met` prevalece sempre.

Comparamos com uma **baseline** (um único LLM) e com uma **ablação** (Compiler substituído por um LLM). Métricas: exatidão do parecer, exatidão por critério, taxa de falsa aprovação e chamadas ao LLM por caso. A orquestração é código Python próprio (ver `docs/seccao_3_4_framework.md`).

O dataset (30 casos) é **sintético**: avisos fictícios gerados por `scripts/build_dataset.py` com seed fixa; ver `data/README.md`.

## 2. Instalação

Requer Python 3.11 ou superior (desenvolvido com 3.12; o pandas 3 não suporta versões anteriores).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Variáveis de ambiente

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Preencher `OPENAI_API_KEY` no `.env` (e, se quiser, `MODEL_NAME`, por defeito `gpt-4o-mini`, e `TEMPERATURE`, por defeito `0`). O `.env` está no `.gitignore`: nunca o enviar para o GitHub.

## 4. Comandos

```bash
python -m unittest discover -s tests                      # testes (offline, sem chave)
python scripts/build_dataset.py                           # (re)gera data/cases.json
python scripts/run_system.py --case case_02               # sistema multiagente num caso
python scripts/run_baseline.py --case case_02             # baseline no mesmo caso
python scripts/run_experiments.py --backend openai --reps 1 --split dev    # (antes) ajustar prompts nos 6 casos dev
python scripts/run_experiments.py --backend openai --reps 5 --split test   # experiências completas
bash scripts/run_all.sh                                   # tudo, em sequência (dataset, testes, experiências)
```

Para experimentar **sem chave nem custos**, usar `--backend mock` (LLM falso, só para testar o código; os números **não são resultados** e `results/mock/` está no `.gitignore`):
`python scripts/run_experiments.py --backend mock --reps 3 --noise 0.05`.

Custo aproximado das experiências completas: 24 casos × 5 repetições × 3 configurações ≈ 2 500 chamadas a um modelo pequeno (da ordem de poucos euros ou menos). As experiências retomam de onde ficaram se forem interrompidas.

## 5. Saída esperada

`run_system.py` imprime os critérios extraídos com o veredicto e a verdade de referência, o parecer final, o número de chamadas ao LLM e de mensagens:

```
== case_02 | config=multiagent | backend=openai
Critérios (label -> veredicto | verdade):
  a)  met  | met
  ...
Parecer: ELIGIBLE   (verdade: ELIGIBLE)
Chamadas LLM: 7 | mensagens: 14 | ...
```

`run_experiments.py` cria em `results/openai/` o ficheiro `runs.csv` (uma linha por configuração, caso e repetição) e o `meta.json` (modelo, temperatura, seeds). As métricas agregadas estão em `src/aism/evaluation.py` (`summarize`, `error_table`).

## 6. Estrutura de pastas

```
aism-project-group22/
├── README.md  requirements.txt  .env.example  .gitignore
├── src/aism/        # dataset.py (gerador), llm.py (OpenAI + mock), system.py (agentes, baseline, ablação), evaluation.py (métricas)
├── data/            # cases.json (dataset sintético) e README.md
├── scripts/         # gerar dataset, executar o sistema/baseline, experiências
├── tests/           # testes unitários (offline)
├── results/         # CSV/JSON e figuras geradas
└── docs/            # ambiente, secção 3.4, checklist
```

## 7. Membros do grupo

- Duarte Dias
- Gabriel Ribeiro
- Dmytro Kravchuk
