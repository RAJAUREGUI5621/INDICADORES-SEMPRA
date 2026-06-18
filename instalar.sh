#!/usr/bin/env bash
# Preparación del entorno (ejecutar solo la primera vez).
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo
echo "Entorno listo. Ahora ejecuta:  bash ejecutar.sh 30 10"
