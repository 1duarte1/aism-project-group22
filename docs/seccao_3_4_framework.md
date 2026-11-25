# Secção 3.4 — Justificação da framework (rascunho)

A orquestração foi implementada diretamente em Python (versão ver `docs/ambiente.md`), sem framework multiagente externo. Os papéis (Manager, Assessors, Evidence Lister, Compiler) são funções com contratos de entrada/saída em JSON validado, o que:

1. torna o fluxo explícito e permite contar chamadas ao LLM e mensagens por caso (métricas do projeto);
2. garante um Compiler determinístico e testável (testes em `tests/`);
3. permite trocar o LLM (OpenAI ou mock offline) sem alterar os agentes.

**Atenção:** o enunciado menciona frameworks (LangGraph, CrewAI, AutoGen, SPADE). Se o docente exigir uma, os agentes de `src/aism/system.py` mapeiam diretamente para agentes/tarefas dessa framework (o ficheiro `scripts/` e as métricas não mudam). Nesse caso reescrever este texto com a versão e a justificação da framework.
