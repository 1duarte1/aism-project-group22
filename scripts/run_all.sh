#!/usr/bin/env bash
# Reproduz TUDO com o modelo real (precisa de .env com OPENAI_API_KEY). Uso: bash scripts/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/build_dataset.py
python -m unittest discover -s tests
python scripts/run_experiments.py --backend openai --reps 5 --split test

