#!/usr/bin/env bash
# Genera el reporte analisis_ot_resultado.txt
# Uso: bash ejecutar.sh <avance_GSC> <avance_IENG>
# Ejemplo: bash ejecutar.sh 30 10
set -e
cd "$(dirname "$0")"

GSC="${1:-30}"
IENG="${2:-10}"

# Activa el entorno virtual si existe
[ -f .venv/bin/activate ] && source .venv/bin/activate

printf '%s\n%s\n' "$GSC" "$IENG" | python analisis_ot.py > analisis_ot_resultado.txt
echo "Reporte generado en analisis_ot_resultado.txt  (GSC=${GSC}%, IENG=${IENG}%)"
