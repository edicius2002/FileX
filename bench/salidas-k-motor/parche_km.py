# -*- coding: utf-8 -*-
"""M1 / B13 — parcheador de las dos copias del arnes.

Aplica sobre `ocr_lote_km.py` y `docling_lote_km.py` (copias byte a byte de
`bench/salidas-ppp-norm/`) los TRES cambios de este encargo, y deja constancia
exacta de cuales son. Los originales de P1 no se tocan.

  1. BASE -> bench/salidas-k-motor, e import de `ocr_eval_km`.
  2. TESTIGO DE PROCESO CON TOPE. CLAUDE.md §3: «Ponle tope al propio testigo
     (20 s, devolviendo el tope y marcando SUCIA): un testigo que puede tumbar la
     medicion no es un testigo». El de P1 lanza 5 ffprobe con timeout=60 cada uno:
     puede consumir 300 s por invocacion (le paso a P3, x94,6).
  3. GUARDIA DE VRAM por imagen. ppp-y-normalizacion.md §7: PaddleOCR llego a
     11 942 y EasyOCR a 12 037 de 12 288 MiB SIN dar error. Antes de cada imagen se
     consulta la VRAM (una vez, no por repeticion) y si pasa del tope se omite la
     celda y se registra `omitido_vram`.
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

TESTIGO_NUEVO = '''def testigo_proceso(n=5, tope_s=20.0):
    """TESTIGO 2 — NIVEL, CON TOPE. Lanzamiento de proceso; detecta la carga real de
    la maquina (planificador, E/S, contencion multinucleo), que es justo lo que el
    monohilo no ve. Calibracion en reposo del proyecto: ffprobe -version 26,5-26,8 ms.

    CAMBIO DE M1 respecto a la version de P1: TOPE DE 20 s AL TESTIGO ENTERO.
    CLAUDE.md §3 — «un testigo que puede tumbar la medicion no es un testigo»: a P3 se
    le comio un timeout de 60 s por lanzamiento (x94,6). Si se agota el presupuesto se
    devuelve el TOPE (20 000 ms) en negativo-por-convencion NO: se devuelve el tope y
    se marca el flag `testigo_topado`, que sube la tanda a SUCIA."""
    ms = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            TOPADO["si"] = True
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=restante)
        except Exception:
            TOPADO["si"] = True
            return round(tope_s * 1000, 2)
        ms.append((time.perf_counter() - t) * 1000)
    if not ms:
        TOPADO["si"] = True
        return round(tope_s * 1000, 2)
    return round(statistics.median(ms), 2)


TOPADO = {"si": False}
# Tope de VRAM: por encima de aqui no se lanza una celda mas. Medido en
# ppp-y-normalizacion.md §7: los dos motores caros terminaron a menos de 350 MiB de
# agotar la tarjeta sin dar ningun error.
VRAM_TOPE = int(os.environ.get("VRAM_TOPE", "11500"))
'''


def parchear(nombre, cambios):
    ruta = os.path.join(BASE, nombre)
    s = io.open(ruta, encoding="utf-8").read()
    for viejo, nuevo, obligatorio in cambios:
        if viejo not in s:
            if obligatorio:
                raise SystemExit(f"{nombre}: no encontrado -> {viejo[:70]!r}")
            print(f"  [aviso] {nombre}: patron opcional ausente: {viejo[:50]!r}")
            continue
        s = s.replace(viejo, nuevo, 1)
    io.open(ruta, "w", encoding="utf-8", newline="\n").write(s)
    print(f"  parcheado {nombre}")


COMUN = [
    (r'BASE = os.path.join(RAIZ, r"bench\salidas-ppp-norm")',
     r'BASE = os.path.join(RAIZ, r"bench\salidas-k-motor")', True),
    ('''def testigo_proceso(n=5):
    """TESTIGO 2 — NIVEL. Lanzamiento de proceso. Detecta la carga real de la maquina
    (planificador, E/S, contencion multinucleo), que es justo lo que el monohilo no ve.
    Calibracion en reposo del proyecto: ffprobe -version 26,5-26,8 ms."""
    ms = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except Exception:
            return -1.0
        ms.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ms), 2)
''', TESTIGO_NUEVO, False),
    ('''def testigo_proceso(n=5):
    ms = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except Exception:
            return -1.0
        ms.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ms), 2)
''', TESTIGO_NUEVO, False),
    ('"nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),',
     '"nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),\n'
     '       "testigo_topado": TOPADO["si"], "vram_tope_MiB": VRAM_TOPE,', True),
]

LOTE = COMUN + [
    ('from ocr_eval_pn import evaluar, ref_de_nombre  # noqa: E402',
     'from ocr_eval_km import evaluar, ref_de_nombre  # noqa: E402', True),
    ('''    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = REF_FORZADA or ref_de_nombre(nom)
    pico_ini = mu.pico''',
     '''    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = REF_FORZADA or ref_de_nombre(nom)
    pico_ini = mu.pico
    # GUARDIA DE VRAM — una consulta por imagen, no por repeticion.
    v_ahora = vram()
    if v_ahora > VRAM_TOPE:
        res[nom] = {"omitido_vram": v_ahora, "tope": VRAM_TOPE}
        print(f"{nom:44s} OMITIDO por VRAM: {v_ahora} > {VRAM_TOPE} MiB", flush=True)
        continue''', True),
]

DOCLING = COMUN + [
    ('from ocr_eval_pn import evaluar, ref_de_nombre  # noqa: E402',
     'from ocr_eval_km import evaluar, ref_de_nombre  # noqa: E402', True),
    ('''    nat = ppp_nativos(ruta)
    lista = ([nat] if modo_ppp == "nativo" else
             [None] if modo_ppp == "defecto" else
             [float(x) for x in modo_ppp.split(",")])''',
     '''    nat = ppp_nativos(ruta)
    # M1: modo `f<lista>` = FACTORES sobre el raster nativo, que es la unidad del `k`.
    if modo_ppp.startswith("f"):
        lista = [round(nat * float(x), 4) for x in modo_ppp[1:].split(",")]
    elif modo_ppp == "nativo":
        lista = [nat]
    elif modo_ppp == "defecto":
        lista = [None]
    else:
        lista = [float(x) for x in modo_ppp.split(",")]''', True),
    ('''        clave = (f"ppp{int(round(ppp_efectivo)):04d}__{d}" if ppp is not None
                 else f"pppDEF__{d}")''',
     '''        fac = round(ppp_efectivo / nat, 3) if (nat and ppp is not None) else None
        clave = (f"k{int(round(fac * 1000)):04d}__{d}" if fac is not None
                 else f"kDEF__{d}")''', True),
    ('''        pico_ini = mu.pico
        try:
            texto = conv.convert(ruta).document.export_to_markdown()''',
     '''        pico_ini = mu.pico
        v_ahora = vram()
        if v_ahora > VRAM_TOPE:
            res[clave] = {"omitido_vram": v_ahora, "tope": VRAM_TOPE}
            print(f"{clave:40s} OMITIDO por VRAM: {v_ahora} > {VRAM_TOPE}", flush=True)
            continue
        try:
            texto = conv.convert(ruta).document.export_to_markdown()''', True),
    ('''            "referencia": ref, "ppp_nativos": nat, "escala": round(escala, 4),''',
     '''            "referencia": ref, "ppp_nativos": nat, "factor": fac,
            "escala": round(escala, 4),''', True),
]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parchear("ocr_lote_km.py", LOTE)
    parchear("docling_lote_km.py", DOCLING)
    print("listo")
