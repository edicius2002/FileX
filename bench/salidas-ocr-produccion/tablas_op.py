# -*- coding: utf-8 -*-
"""G5 — tablas del informe `bench/ocr-produccion-sidecar.md` a partir de los .json.

uso: tablas_op.py <dir_salidas> [seccion]
     secciones: veneno | criterio | frio | todo
"""
import glob
import json
import os
import re
import statistics
import sys

D = sys.argv[1]
QUE = sys.argv[2] if len(sys.argv) > 2 else "todo"
J = os.path.join(D, "json")


def carga(patron):
    out = {}
    for f in sorted(glob.glob(os.path.join(J, patron))):
        out[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8"))
    return out


def seccion_veneno():
    print("\n## Fase A/B/C/D — el atasco, con y sin el folio grande\n")
    for etq, d in carga("A_*.json").items():
        m, fin = d["meta"], d["fin"]
        print(f"\n### {etq}  ({m['motor']} / {m['dispositivo']} / fase {m['fase']})")
        print(f"base {m['vram_base_MiB']} MiB · tras cargar "
              f"{m['vram_tras_carga_MiB']} MiB · arranque en frio "
              f"{m['arranque_frio_s']} s · tanda {fin['tanda']} "
              f"(deriva {fin['deriva']}, nivel {fin['nivel']})")
        print("\n| paso | imagen | Mpx | nota | ms | chars | VRAM tras (MiB) "
              "| delta base | libre | err |")
        print("|---:|---|---:|---|---:|---:|---:|---:|---:|---|")
        for c in d["celdas"]:
            print(f"| {c['paso']} | {c['img']} | {c['mpx']} | {c['nota']} | "
                  f"{c['ms']} | {c['chars']} | {c['vram_despues_MiB']} | "
                  f"{c['delta_sobre_base_MiB']} | {c['vram_libre_MiB']} | "
                  f"{'-' if not c['error'] else c['error'][:40]} |")


def seccion_criterio():
    print("\n## Con que variable crece la VRAM retenida\n")
    for etq, d in carga("D_*.json").items():
        m = d["meta"]
        print(f"\n### {etq}  (fase {m['fase']})")
        print("| paso | Mpx pagina | Mpx acum. | Mpx max | VRAM delta (MiB) | ms |")
        print("|---:|---:|---:|---:|---:|---:|")
        for c in d["celdas"]:
            print(f"| {c['paso']} | {c['mpx']} | {c['mpx_acumulados']} | "
                  f"{c['mpx_maximo']} | {c['delta_sobre_base_MiB']} | {c['ms']} |")


def _leer_log_frio(ruta):
    """Cada corrida escribio dos/tres lineas JSON. Se emparejan por orden."""
    cargados, pasos = [], []
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        linea = linea.strip()
        if not linea.startswith("{"):
            continue
        try:
            o = json.loads(linea)
        except Exception:
            continue
        if o.get("evento") == "cargado":
            cargados.append(o)
        elif "paso" in o:
            pasos.append(o)
    return cargados, pasos


def seccion_frio():
    print("\n## Arranque en frio — un proceso por repeticion\n")
    print("| configuracion | n | import s | construccion s | **frio s** | "
          "1a pagina ms | frio+pagina s |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for ruta in sorted(glob.glob(os.path.join(D, "logs", "C_*.log"))):
        etq = os.path.basename(ruta)[2:-4]
        cargados, pasos = _leer_log_frio(ruta)
        if len(cargados) < 2:
            print(f"| {etq} | {len(cargados)} | (insuficiente) | | | | |")
            continue
        # la PRIMERA corrida se descarta: Windows Defender infla el primer
        # arranque (trampa 7)
        c, p = cargados[1:], pasos[1:]
        imp = statistics.median(x["import_s"] for x in c)
        con = statistics.median(x["carga_modelo_s"] for x in c)
        fri = statistics.median(x["arranque_frio_s"] for x in c)
        pag = statistics.median(x["ms"] for x in p) if p else float("nan")
        print(f"| {etq} | {len(c)} | {imp:.3f} | {con:.3f} | **{fri:.3f}** | "
              f"{pag:.1f} | {fri + pag/1000:.3f} |")


if QUE in ("veneno", "todo"):
    seccion_veneno()
if QUE in ("criterio", "todo"):
    seccion_criterio()
if QUE in ("frio", "todo"):
    seccion_frio()
