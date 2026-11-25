# Registo do ambiente

Valores a registar no relatório (Tabela do ambiente). Confirmar à mão:

| Item | Como confirmar |
|---|---|
| Python | `python --version` |
| Bibliotecas | `pip freeze` (copiar para `requirements.txt`) |
| Sistema operativo | `winver` ou `uname -a` |
| Modelo / temperatura | `.env` (`MODEL_NAME`, `TEMPERATURE`); gravados em `results/openai/meta.json` |
| Seeds | `1000 + n.º da repetição` (em `meta.json`) |
| Chaves | só no `.env` (não versionado) |

Nota: a API do OpenAI aceita `seed`, mas a reprodutibilidade exata não é garantida; por isso há repetições e desvio-padrão.

Testar num ambiente limpo (dia 24):

```bash
python -m venv .venv_test && source .venv_test/bin/activate   # Windows: .venv_test\Scripts\activate
pip install -r requirements.txt && python -m unittest discover -s tests
```

Se uma chave tiver sido enviada para o GitHub: revogá-la no fornecedor e criar outra (apagar o ficheiro não a remove do histórico).
