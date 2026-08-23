# -*- coding: utf-8 -*-
"""G4 / B19 — CONTROL con Tesseract sobre LOS MISMOS FICHEROS.

Copia adaptada de `bench/salidas-psm/tess_psm.py` (G2). El original NO se toca.

Que cambia, y por que importa
-----------------------------
G2 movio la resolucion declarada con la bandera `-c user_defined_dpi=N`. Aqui la
variable es LA CABECERA DEL FICHERO, no una bandera: los PNG son los que produce
`preparar_pm.py`, con los MISMOS IDAT y distinto `pHYs`. Sin esta tanda, «los tres
motores GPU no cambian» no significa nada: podria ser que mis ficheros no llevaran
el efecto. Con ella, la comparacion es del mismo fichero contra el mismo fichero.

Se registra ademas la linea `Estimating resolution as N` del `stderr` — el mecanismo,
sondeado en ejecucion (`CLAUDE.md` §5) — y el `rc` de cada celda, que es lo unico que
separa «no leyo» de «no arranco» (`CLAUDE.md` trampa 25).

`stderr` NO se devuelve crudo a ningun modelo: se extrae con una expresion regular
cerrada y se guarda en el JSON.

uso: python tess_pm.py <glob> <psm,psm,...> <etiqueta> [lang]
env: REPS(9) IMGDIR TESS_BIN TESSDATA
"""
import glob as _glob
import json
import os
import re
import statistics
import subprocess
import sys
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_pm import evaluar, ref_de_doc  # noqa: E402

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
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
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
BLANCA_PSM = {str(i) for i in range(14)} - {"2"}
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

RE_EST = re.compile(r"Estimating resolution as (\d+)")
RE_DIA = re.compile(r"Detected (\d+) diacritics")


def leer(ruta, psm):
    q = subprocess.run([TESS, ruta, "stdout", "-l", LANG, "--psm", psm],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600, env=ENT)
    est = RE_EST.search(q.stderr or "")
    dia = RE_DIA.search(q.stderr or "")
    return (q.returncode, q.stdout,
            int(est.group(1)) if est else None,
            int(dia.group(1)) if dia else None)


mono_ini = testigo_monohilo()
proc_ini = testigo_proceso()
cab = {"etiqueta": ETQ, "motor": "tesseract", "dispositivo": "cpu", "binario": TESS,
       "version": ver, "tessdata": TESSDATA, "lang": LANG, "psms": PSMS,
       "user_defined_dpi": None, "nota": "la resolucion sale de la CABECERA del PNG",
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
    raiz, variante = nom.rsplit("__", 1)
    doc = raiz.split("__")[0]
    ref = ref_de_doc(doc)
    for psm in PSMS:
        clave = f"{nom}__psm{int(psm):02d}"
        try:
            rc, texto, est, dia = leer(ruta, psm)   # calentamiento, fuera de medida
        except Exception as ex:
            res[clave] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            print(f"{clave:58s} ERROR {type(ex).__name__}", flush=True)
            continue
        ts, textos, rcs = [], set(), set()
        for _ in range(REPS):
            t = time.time()
            rc, texto, est, dia = leer(ruta, psm)
            ts.append((time.time() - t) * 1000)
            textos.add(texto)
            rcs.add(rc)
        s = sorted(ts)
        ev = evaluar(texto, ref)
        open(os.path.join(OUT, f"{ETQ}__{clave}.txt"), "w",
             encoding="utf-8").write(texto)
        import hashlib
        res[clave] = {
            "imagen": os.path.basename(ruta), "doc": doc, "raiz": raiz,
            "variante": variante, "psm": psm, "referencia": ref,
            "rc": rc, "rcs_unicos": sorted(rcs),
            "estimating_resolution": est, "diacritics": dia,
            "md5_texto": hashlib.md5(texto.encode("utf-8")).hexdigest(),
            "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
            "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
            "chars_ref_acentos": ev["chars_ref_acentos"],
            "bytes_salida": len(texto), "chars": ev["chars_salida"],
            "lineas_exactas": ev["lineas_exactas"],
            "lineas_totales": ev["lineas_totales"],
            "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
            "ms_mediana": round(statistics.median(s), 1), "ms_min": round(s[0], 1),
            "ms_max": round(s[-1], 1), "n": len(s),
            "determinista": len(textos) == 1,
        }
        print(f"{clave:58s} CERac={ev['cer_acentos_pct']:8.2f}%  "
              f"B={len(texto):5d}  rc={rc}  est={est}  dia={dia}  "
              f"{statistics.median(s):7.1f} ms  "
              f"det={'si' if len(textos) == 1 else 'NO'}", flush=True)

mono_fin = testigo_monohilo()
proc_fin = testigo_proceso()
fin = {"evento": "fin", "celdas": len(res),
       "testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
       "deriva_monohilo": round(mono_fin / max(1e-9, mono_ini), 2),
       "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
       "nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),
       "testigo_topado": TOPADO["si"],
       "deterministas": sum(1 for v in res.values() if v.get("determinista")),
       "rc_distinto_de_cero": sum(1 for v in res.values() if v.get("rc") not in (0, None)),
       "con_error": sum(1 for v in res.values() if "error" in v)}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{ETQ}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
