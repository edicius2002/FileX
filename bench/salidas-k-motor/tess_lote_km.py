# -*- coding: utf-8 -*-
"""M1 / B13 (+ B14) — la OCTAVA configuracion: Tesseract 5.5.0 nativo, en CPU.

Por que esta aqui. El `k = 1,50` de Tesseract que hoy figura en `CLAUDE.md` trampa 8
sale de UN punto de OTRO agente (`bench/invocacion-aristas.md` §9, P2, n=1, Tesseract
en contenedor sobre `escaneado_d2`), y el mismo informe mide que sobre `d4` le conviene
el nativo. Es la estimacion mas fragil de la tabla y es la que mas se cita.

Diferencias declaradas frente a la medida de P2, que hay que tener presentes al
comparar: **este Tesseract es el NATIVO de Windows** (`C:\\Program Files\\Tesseract-OCR`,
v5.5.0.20241111, leptonica 1.85.0), no el del contenedor Debian; y los datos de idioma
salen de `C:\\Program Files\\PDFgear\\tessdata` (16 idiomas, incluido `spa`), que
**los puso PDFgear, no este proyecto** (`CLAUDE.md` §2). No se instala nada: se apunta
`TESSDATA_PREFIX` a ese directorio en el entorno del hijo, solo de lectura.

Invocacion segun `CLAUDE.md` §5: proceso separado, sin shell, argumentos en array,
`stdin=DEVNULL` primero y timeout explicito.

uso: python tess_lote_km.py <glob> [lang]
env: REPS(9) SUFIJO IMGDIR TESS_PSM(3) TESS_BIN TESSDATA
"""
import glob as _glob
import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-k-motor")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_km import evaluar, ref_de_nombre  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

TESS = os.environ.get("TESS_BIN", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA = os.environ.get("TESSDATA", r"C:\Program Files\PDFgear\tessdata")
PSM = os.environ.get("TESS_PSM", "3")
patron = sys.argv[1] if len(sys.argv) > 1 else "k*__*.png"
LANG = sys.argv[2] if len(sys.argv) > 2 else "spa"
REPS = int(os.environ.get("REPS", "9"))
etiqueta = f"tesseract_cpu" + os.environ.get("SUFIJO", "")

FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"
TOPADO = {"si": False}


def testigo_monohilo(n=400000):
    """TESTIGO 1 — DERIVA. Ciego a la contencion multinucleo, a proposito."""
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    """TESTIGO 2 — NIVEL, CON TOPE DE 20 s (CLAUDE.md §3)."""
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
# CLAUDE.md trampa 18: -sOCRLanguage/`-l` NUNCA sale de la entrada del usuario.
# Aqui la lista blanca es explicita y se comprueba contra --list-langs.
BLANCA = {"spa", "eng"}
if LANG not in BLANCA:
    raise SystemExit(f"idioma fuera de la lista blanca: {LANG!r}")

p = subprocess.run([TESS, "--list-langs"], stdin=subprocess.DEVNULL,
                   capture_output=True, text=True, timeout=60, env=ENT)
disponibles = [x.strip() for x in p.stdout.splitlines()[1:] if x.strip()]
ver = subprocess.run([TESS, "--version"], stdin=subprocess.DEVNULL,
                     capture_output=True, text=True, timeout=60).stdout.splitlines()[0]
if LANG not in disponibles:
    raise SystemExit(f"{LANG} no esta en {TESSDATA}: {disponibles}")


def leer(ruta):
    q = subprocess.run([TESS, ruta, "stdout", "-l", LANG, "--psm", PSM],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600, env=ENT)
    if q.returncode != 0:
        raise RuntimeError(f"rc={q.returncode}")
    return q.stdout


mono_ini = testigo_monohilo()
proc_ini = testigo_proceso()
cab = {"etiqueta": etiqueta, "motor": "tesseract", "dispositivo": "cpu",
       "binario": TESS, "version": ver, "tessdata": TESSDATA, "lang": LANG,
       "psm": PSM, "idiomas_disponibles": disponibles, "patron": patron,
       "imgdir": IMG, "reps": REPS,
       "testigo_monohilo_ini_ms": mono_ini, "testigo_proceso_ini_ms": proc_ini}
print(json.dumps(cab, ensure_ascii=False), flush=True)

rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
res = {}
for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = ref_de_nombre(nom)
    try:
        texto = leer(ruta)              # calentamiento, fuera de la medicion
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{nom:44s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = leer(ruta)
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
    ev = evaluar(texto, ref)
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w",
         encoding="utf-8").write(texto)
    res[nom] = {
        "referencia": ref,
        "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
        "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
        "chars_ref_acentos": ev["chars_ref_acentos"], "chars": ev["chars_salida"],
        "lineas_exactas": ev["lineas_exactas"], "lineas_totales": ev["lineas_totales"],
        "acentos_ref": ev["acentos_ref"], "acentos_salida": ev["acentos_salida"],
        "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
        "normalizada_acentos": ev["normalizada_acentos"],
        "ms_mediana": round(statistics.median(s), 1), "ms_min": round(s[0], 1),
        "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1,
        "testigo_monohilo_ms": testigo_monohilo(),
    }
    print(f"{nom:44s} CERac={ev['cer_acentos_pct']:6.2f}%  "
          f"CERascii={ev['cer_ascii_pct']:6.2f}%  "
          f"lin={ev['lineas_exactas']}/{ev['lineas_totales']}  "
          f"bloques={res[nom]['bloques']}  {statistics.median(s):8.1f} ms  "
          f"det={'si' if len(textos) == 1 else 'NO'}", flush=True)

mono_fin = testigo_monohilo()
proc_fin = testigo_proceso()
fin = {"evento": "fin",
       "testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
       "deriva_monohilo": round(mono_fin / max(1e-9, mono_ini), 2),
       "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
       "nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),
       "testigo_topado": TOPADO["si"]}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
