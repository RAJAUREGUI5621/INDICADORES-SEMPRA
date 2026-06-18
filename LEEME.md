# Análisis de OTs atrasadas — paquete para ejecutar

Contiene todo lo necesario para generar el reporte `analisis_ot_resultado.txt`.

## Archivos
- `analisis_ot.py` — script de análisis.
- `requirements.txt` — dependencias de Python.
- `OT.pdf` — datos de entrada. **Reemplázalo por tu export más reciente**
  (debe incluir la columna **`DurNor`**; si no, las horas saldrán en 0).
- `instalar.sh` — preparación del entorno (solo la primera vez).
- `ejecutar.sh` — ejecuta el reporte (las veces que quieras).

## Primera vez (preparar el entorno)
```bash
bash instalar.sh
```
Esto crea el entorno virtual `.venv` e instala las dependencias.

## Cada vez que quieras generar el reporte
```bash
bash ejecutar.sh 30 10
```
Donde `30` y `10` son los % de avance de GSC e IENG (cámbialos según el caso).
El resultado queda en `analisis_ot_resultado.txt`.

## Equivalente manual (sin scripts)
```bash
python3 -m venv .venv && source .venv/bin/activate   # solo la primera vez
pip install -r requirements.txt                       # solo la primera vez

source .venv/bin/activate
printf '30\n10\n' | python analisis_ot.py > analisis_ot_resultado.txt
```
