"""
Análisis de OTs atrasadas desde el PDF OT.pdf

Lee la tabla del PDF (todas las páginas de datos) y calcula:
1. Tiempo en semanas de las horas atrasadas (Duración normal)
2. Distribución de horas por Clase de orden
3. Distribución de horas por Puesto trabajo (con conversión a semanas)

Todo agrupado por los dos valores de Ce.emplazam. (GSC e IENG).
"""

import pandas as pd
import pdfplumber
from datetime import datetime, timedelta

PDF_FILE = "OT.pdf"
HORAS_POR_SEMANA = 168  # Total horas en una semana (24h x 7 días)
DISCIPLINAS_VALIDAS = ["ELE", "INS", "MEC"]

# Campos usados en el análisis y los posibles nombres de encabezado del PDF.
# El export de SAP cambia los rótulos según la variante (p. ej. "InicTardío"
# vs "Inic.extr.", "PtoTrbRes" vs "PtoTbjoOp"), por eso se mapea por nombre.
HEADER_ALIASES = {
    "Clase de orden": ["Cl."],
    "Duración normal": ["DurNor", "Dur.normal", "DurNorm", "Dur. normal"],
    "FeInicMásTardía": ["InicTardío", "Inic.extr.", "Inic.Extr.", "InicExtr", "Inic.extrema"],
    "Txt.brv.oper.": ["Texto breve operac.", "Texto breve", "Txt.brv.oper."],
    "Puesto trabajo": ["PtoTrbRes", "PtoTbjoOp", "Pto.trab.", "PtoTrab"],
    "Estado sistema": ["Status del sistema", "Estado sistema"],
    "Un.dur.normal": ["Un.", "Un.dur.normal"],
    "Ubicac.técnica": ["Ubic.técn.", "Ubicac.técnica"],
    "Equipo": ["Equipo"],
    "Ce.emplazam.": ["Ce.", "Ce.emplazam."],
}


def _mapear_columnas(header) -> dict:
    """Dado el encabezado de la tabla, devuelve {campo_canónico: índice_columna}."""
    celdas = {i: (c or "").strip() for i, c in enumerate(header)}
    mapping = {}
    for campo, alias in HEADER_ALIASES.items():
        for i, txt in celdas.items():
            if txt in alias:
                mapping[campo] = i
                break
    return mapping


def leer_pdf(ruta: str) -> pd.DataFrame:
    """Lee las tablas del PDF y devuelve un DataFrame unificado.

    Mapea las columnas por nombre de encabezado (no por posición fija) para
    tolerar variantes del export. Si el PDF no incluye la columna de duración,
    se rellena vacía y se avisa al final.
    """
    pdf = pdfplumber.open(ruta)
    registros = []
    duracion_presente = False

    # Las tablas de datos están en las páginas 2 a N (índices 1+)
    for page in pdf.pages[1:]:
        tables = page.extract_tables()
        if not tables:
            continue
        table = tables[0]

        # Localizar la fila de encabezado (contiene "Orden" y "Cl.")
        header_idx = None
        for i, row in enumerate(table):
            celdas = [(c or "").strip() for c in row]
            if "Orden" in celdas and "Cl." in celdas:
                header_idx = i
                break
        if header_idx is None:
            continue

        colmap = _mapear_columnas(table[header_idx])
        if "Duración normal" in colmap:
            duracion_presente = True

        # La columna 0 trae TODOS los números de orden concatenados con \n,
        # en la primera fila de datos. Suele haber una fila vacía tras el
        # encabezado, así que se busca la primera fila con contenido en col0.
        data_start = None
        for i in range(header_idx + 1, len(table)):
            if table[i][0]:
                data_start = i
                break
        if data_start is None:
            continue

        ordenes = table[data_start][0].split("\n")

        def celda(fila, campo):
            j = colmap.get(campo)
            if j is None or j >= len(fila):
                return ""
            return (fila[j] or "").strip()

        for idx in range(len(ordenes)):
            row_idx = data_start + idx
            if row_idx >= len(table):
                break
            fila = table[row_idx]
            registro = {
                "Orden": ordenes[idx].strip(),
                "Clase de orden": celda(fila, "Clase de orden"),
                "Duración normal": celda(fila, "Duración normal"),
                "FeInicMásTardía": celda(fila, "FeInicMásTardía"),
                "Txt.brv.oper.": celda(fila, "Txt.brv.oper."),
                "Puesto trabajo": celda(fila, "Puesto trabajo"),
                "Estado sistema": celda(fila, "Estado sistema"),
                "Un.dur.normal": celda(fila, "Un.dur.normal"),
                "Ubicac.técnica": celda(fila, "Ubicac.técnica"),
                "Equipo": celda(fila, "Equipo"),
                "Ce.emplazam.": celda(fila, "Ce.emplazam."),
            }
            registros.append(registro)

    pdf.close()

    if not duracion_presente:
        print("  [ADVERTENCIA] El PDF no contiene la columna 'DurNor' (Duración normal).")
        print("                Las métricas de horas y semanas saldrán en 0.")
        print("                Vuelve a exportar el PDF incluyendo la columna 'DurNor'.")

    return pd.DataFrame(registros)


def limpiar_duracion(valor):
    """Convierte el valor de Duración normal a float."""
    if pd.isna(valor) or valor is None:
        return 0.0
    return float(str(valor).replace("\xa0", "").strip() or 0)


def analizar_grupo(df: pd.DataFrame, nombre_grupo: str, factor_pendiente: float):
    """Imprime el análisis completo para un grupo dado."""
    print(f"\n{'='*60}")
    print(f"  Ce.emplazam.: {nombre_grupo}")
    print(f"{'='*60}")

    # Considerar SOLO órdenes liberadas sin notificar:
    #   - prefijo "LIB" en Estado sistema (liberadas; excluye creadas CRTD y cerradas CERR)
    #   - sin el token "NOTI" (sin notificar)
    estado = df["Estado sistema"].astype(str).str.strip()
    es_liberada = estado.str.upper().str.startswith("LIB")
    sin_noti = ~estado.str.contains("NOTI", case=False, na=False)
    df_sin_noti = df[es_liberada & sin_noti]
    excluidos = len(df) - len(df_sin_noti)

    total_filas = len(df)
    print(f"\n  Total de registros: {total_filas}")
    print(f"  Excluidos (no liberadas o notificadas): {excluidos}")
    print(f"  Registros para cálculo (liberadas sin notificar): {len(df_sin_noti)}")

    # --- Órdenes individuales emitidas en la semana actual ---
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_semana = inicio_semana + timedelta(days=6, hours=23, minutes=59, seconds=59)

    df_fechas = df_sin_noti.copy()
    df_fechas["_fecha"] = pd.to_datetime(df_fechas["FeInicMásTardía"], format="%m/%d/%Y", errors="coerce")
    df_semana = df_fechas[(df_fechas["_fecha"] >= inicio_semana) & (df_fechas["_fecha"] <= fin_semana)]
    ordenes_semana = df_semana["Orden"].nunique()

    print(f"\n  Órdenes únicas con inicio más tardío en la semana actual ({inicio_semana.strftime('%d/%m/%Y')} - {fin_semana.strftime('%d/%m/%Y')}): {ordenes_semana}")

    # --- 1. Tiempo en semanas de las horas atrasadas (sin NOTI) ---
    horas_atrasadas = df_sin_noti["Duración normal"].sum()
    semanas_brutas = horas_atrasadas / HORAS_POR_SEMANA
    semanas_ajustadas = semanas_brutas * factor_pendiente

    print(f"\n  --- Horas atrasadas convertidas a semanas ---")
    print(f"  Total horas (liberadas sin notificar): {horas_atrasadas:,.1f} h")
    print(f"  Semanas brutas ({HORAS_POR_SEMANA}h/sem): {semanas_brutas:,.2f} semanas")
    print(f"  Semanas ajustadas (x{factor_pendiente:.2f}): {semanas_ajustadas:,.2f} semanas")

    # --- 2. Distribución por Clase de orden (liberadas sin notificar) ---
    print(f"\n  --- Distribución de horas por Clase de orden (liberadas sin notificar) ---")
    dist_clase = (
        df_sin_noti.groupby("Clase de orden")["Duración normal"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "Horas", "count": "Registros"})
        .sort_values("Horas", ascending=False)
    )
    total_horas_clase = dist_clase["Horas"].sum()
    if total_horas_clase:
        dist_clase["% Horas"] = (dist_clase["Horas"] / total_horas_clase * 100).round(1)
    else:
        dist_clase["% Horas"] = 0.0
    print(dist_clase.to_string(float_format=lambda x: f"{x:,.1f}"))

    # --- 3. Distribución por Puesto trabajo (sin NOTI) ---
    print(f"\n  --- Distribución por Puesto trabajo (en semanas, {HORAS_POR_SEMANA}h/sem) ---")
    dist_puesto = (
        df_sin_noti.groupby("Puesto trabajo")["Duración normal"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "Horas", "count": "Registros"})
        .sort_values("Horas", ascending=False)
    )
    dist_puesto["Sem. brutas"] = (dist_puesto["Horas"] / HORAS_POR_SEMANA).round(2)
    dist_puesto["Sem. ajustadas"] = (dist_puesto["Horas"] / HORAS_POR_SEMANA * factor_pendiente).round(2)
    total_horas_puesto = dist_puesto["Horas"].sum()
    if total_horas_puesto:
        dist_puesto["% Horas"] = (dist_puesto["Horas"] / total_horas_puesto * 100).round(1)
    else:
        dist_puesto["% Horas"] = 0.0
    print(dist_puesto.to_string(float_format=lambda x: f"{x:,.2f}"))
    print(f"\n  TOTAL Sem. brutas:    {dist_puesto['Sem. brutas'].sum():,.2f}")
    print(f"  TOTAL Sem. ajustadas: {dist_puesto['Sem. ajustadas'].sum():,.2f}")


def main():
    # Leer datos del PDF
    df = leer_pdf(PDF_FILE)

    # Limpiar columna Duración normal
    df["Duración normal"] = df["Duración normal"].apply(limpiar_duracion)

    # Limpiar espacios en columnas de texto relevantes
    for col in ["Puesto trabajo", "Clase de orden", "Ce.emplazam."]:
        df[col] = df[col].astype(str).str.strip()

    # Filtrar solo disciplinas válidas (ELE, INS, MEC)
    total_antes = len(df)
    df = df[df["Puesto trabajo"].isin(DISCIPLINAS_VALIDAS)].copy()
    print(f"  Fuente: {PDF_FILE}")
    print(f"  Total registros leídos: {total_antes}")
    print(f"  Registros con disciplinas válidas ({', '.join(DISCIPLINAS_VALIDAS)}): {len(df)}")
    print(f"  Registros descartados: {total_antes - len(df)}")

    # Solicitar porcentaje de avance por planta
    avance_gsc_str = input("\n  Ingrese el porcentaje de avance para GSC (0-100): ")
    avance_gsc = float(avance_gsc_str.strip().replace("%", ""))
    factor_gsc = 1 - (avance_gsc / 100)

    avance_ieng_str = input("  Ingrese el porcentaje de avance para IENG (0-100): ")
    avance_ieng = float(avance_ieng_str.strip().replace("%", ""))
    factor_ieng = 1 - (avance_ieng / 100)

    factores = {"GSC": factor_gsc, "IENG": factor_ieng}

    print(f"\n  Avance GSC:  {avance_gsc:.0f}% → Factor pendiente: {factor_gsc:.2f}")
    print(f"  Avance IENG: {avance_ieng:.0f}% → Factor pendiente: {factor_ieng:.2f}")

    # Factor global = promedio ponderado por cantidad de registros de las plantas con avance definido
    n_gsc = len(df[df["Ce.emplazam."] == "GSC"])
    n_ieng = len(df[df["Ce.emplazam."] == "IENG"])
    n_ponderado = n_gsc + n_ieng
    factor_global = (n_gsc * factor_gsc + n_ieng * factor_ieng) / n_ponderado if n_ponderado else 1

    # ---- Análisis global ----
    print("\n" + "#" * 60)
    print("  ANÁLISIS GLOBAL (todas las plantas)")
    print(f"  Factor pendiente global (promedio ponderado): {factor_global:.2f}")
    print("#" * 60)
    analizar_grupo(df, "TODAS", factor_global)

    # ---- Análisis agrupado por Ce.emplazam. ----
    print("\n\n" + "#" * 60)
    print("  ANÁLISIS POR Ce.emplazam.")
    print("#" * 60)

    grupos = df["Ce.emplazam."].unique()
    for grupo in sorted(grupos):
        df_grupo = df[df["Ce.emplazam."] == grupo]
        f = factores.get(grupo, 1.0)
        avance_grupo = (1 - f) * 100
        print(f"\n  >> Avance {grupo}: {avance_grupo:.0f}% — Factor pendiente: {f:.2f}")
        analizar_grupo(df_grupo, grupo, f)

    print()


if __name__ == "__main__":
    main()
