# -*- coding: utf-8 -*-
"""G2 / B17-B18-B14 — barrido de Tesseract con `--psm` como EJE, no como constante.

Copia adaptada de bench/salidas-k-motor/tess_lote_km.py (M1). El original NO se toca.
Que cambia: `--psm` deja de ser una variable de entorno con un valor y pasa a ser una
LISTA que se barre dentro de la tanda, para que todas las celdas de una comparacion
`--psm` salgan del mismo proceso, la misma imagen y el mismo binario.

Invocacion segun CLAUDE.md §5: proceso separado, sin shell, argumentos en array,
`stdin=DEVNULL` primero, timeout explicito.
Idioma por LISTA BLANCA (CLAUDE.md trampa 18), comprobado contra `--list-langs`.
`TESSDATA_PREFIX` apunta a C:\\Program Files\\PDFgear\\tessdata, que **lo puso PDFgear,
no este proyecto** (CLAUDE.md §2): solo lectura, no se instala nada.

TESS_DPI: si se fija, se añade `-c user_defined_dpi=N`. Existe porque G2 midio que el
PNG de ImageMagick lleva `pHYs unit=0` (sin unidad) y por tanto NO declara resolucion:
Tesseract la ESTIMA. Esa estimacion, y no el rasterizador, es lo que produce los 33,22
puntos que `k-por-motor.md` §6.2 atribuyo al rasterizador. Con esta variable la
resolucion DECLARADA se convierte en un eje de medida independiente de los PIXELES.

uso: python tess_psm.py <glob> <psm,psm,...> <etiqueta> [lang]
env: REPS(9) IMGDIR TESS_BIN TESSDATA TESS_DPI
"""
import glob as _glob
import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-psm")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_psm import evaluar, ref_de_nombre  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

TESS = os.environ.get("TESS_BIN", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA = os.environ.get("TESSDATA", r"C:\Program Files\PDFgear\tessdata")
patron = sys.argv[1]
PSMS = [x.strip() for x in sys.argv[2].split(",")]
ETQ = sys.argv[3]
LANG = sys.argv[4] if len(sys.argv) > 4 else "spa"
REPS = int(os.environ.get("REPS", "9"))

FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"
TOPADO = {"si": False}


def testigo_monohilo(n=400000):
    """TESTIGO 1 — DERIVA dentro de la tanda. Ciego a la contencion multinucleo."""
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    """TESTIGO 2 — NIVEL de carga, CON TOPE de 20 s (CLAUDE.md §3)."""
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


ENT = dict(os.environ)
ENT["TESSDATA_PREFIX"] = TESSDATA
BLANCA = {"spa", "eng"}
if LANG not in BLANCA:
    raise SystemExit(f"idioma fuera de la lista blanca: {LANG!r}")
BLANCA_PSM = {str(i) for i in range(14)} - {"2"}   # psm 2 no esta implementado
for p_ in PSMS:
    if p_ not in BLANCA_PSM:
        raise SystemExit(f"psm fuera de la lista blanca: {p_!r}")

p = subprocess.run([TESS, "--list-langs"], stdin=subprocess.DEVNULL,
                   capture_output=True, text=True, timeout=60, env=ENT)
disponibles = [x.strip() for x in p.stdout.splitlines()[1:] if x.strip()]
ver = subprocess.run([TESS, "--version"], stdin=subprocess.DEVNULL,
                     capture_output=True, text=True, timeout=60).stdout.splitlines()[0]
if LANG not in disponibles:
    raise SystemExit(f"{LANG} no esta en {TESSDATA}: {disponibles}")


DPI = os.environ.get("TESS_DPI", "").strip()
if DPI and not (DPI.isdigit() and 1 <= int(DPI) <= 2400):
    raise SystemExit(f"TESS_DPI fuera de rango: {DPI!r}")
EXTRA = ["-c", f"user_defined_dpi={DPI}"] if DPI else []


def leer(ruta, psm):
    q = subprocess.run([TESS, ruta, "stdout", "-l", LANG, "--psm", psm] + EXTRA,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600, env=ENT)
    return q.returncode, q.stdout


mono_ini = testigo_monohilo()
proc_ini = testigo_proceso()
cab = {"etiqueta": ETQ, "motor": "tesseract", "dispositivo": "cpu", "binario": TESS,
       "version": ver, "tessdata": TESSDATA, "lang": LANG, "psms": PSMS, "user_defined_dpi": DPI or None,
       "idiomas_disponibles": disponibles, "patron": patron, "imgdir": IMG,
       "reps": REPS, "testigo_monohilo_ini_ms": mono_ini,
       "testigo_proceso_ini_ms": proc_ini}
print(json.dumps(cab, ensure_ascii=False), flush=True)

rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
if not rutas:
    raise SystemExit(f"sin imagenes para {patron!r} en {IMG}")
res = {}
for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = ref_de_nombre(nom)
    for psm in PSMS:
        clave = f"{nom}__psm{int(psm):02d}"
        try:
            rc, texto = leer(ruta, psm)          # calentamiento, fuera de la medicion
        except Exception as ex:
            res[clave] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            print(f"{clave:56s} ERROR {type(ex).__name__}", flush=True)
            continue
        ts, textos = [], set()
        for _ in range(REPS):
            t = time.time()
            rc, texto = leer(ruta, psm)
            ts.append((time.time() - t) * 1000)
            textos.add(texto)
        s = sorted(ts)
        ev = evaluar(texto, ref)
        open(os.path.join(OUT, f"{ETQ}__{clave}.txt"), "w",
             encoding="utf-8").write(texto)
        res[clave] = {
            "imagen": os.path.basename(ruta), "psm": psm, "referencia": ref, "rc": rc,
            "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
            "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
            "chars_ref_acentos": ev["chars_ref_acentos"],
            "bytes_salida": len(texto), "chars": ev["chars_salida"],
            "lineas_exactas": ev["lineas_exactas"],
            "lineas_totales": ev["lineas_totales"],
            "acentos_ref": ev["acentos_ref"], "acentos_salida": ev["acentos_salida"],
            "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
            "ms_mediana": round(statistics.median(s), 1), "ms_min": round(s[0], 1),
            "ms_max": round(s[-1], 1), "n": len(s),
            "determinista": len(textos) == 1,
        }
        print(f"{clave:56s} CERac={ev['cer_acentos_pct']:8.2f}%  "
              f"B={len(texto):5d}  lin={ev['lineas_exactas']}/{ev['lineas_totales']}  "
              f"{statistics.median(s):7.1f} ms  det={'si' if len(textos) == 1 else 'NO'}",
              flush=True)

mono_fin = testigo_monohilo()
proc_fin = testigo_proceso()
fin = {"evento": "fin", "celdas": len(res),
       "testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
       "deriva_monohilo": round(mono_fin / max(1e-9, mono_ini), 2),
       "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
       "nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),
       "testigo_topado": TOPADO["si"],
       "deterministas": sum(1 for v in res.values() if v.get("determinista")),
       "con_error": sum(1 for v in res.values() if "error" in v)}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{ETQ}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
