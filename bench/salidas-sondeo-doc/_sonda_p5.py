# -*- coding: utf-8 -*-
"""S3 — pendiente 5 de `bench/hito5-documental.md`: `xlsx`, `pptx`, `csv`, `svg`, `tex`.

**Estas aristas NO están en el grafo**, así que no se pueden sondear con
`FileX.convertir()`: `_EnContenedor.orden()` levanta `ValueError` para un par que
el motor no declara, y hace bien. Aquí se invoca el contenedor directamente —con
`filex.invocacion.ejecutar()`, que sigue siendo el único punto de invocación— y
se le pasa **el mismo contrato de cinco puntos** que aplica el núcleo, con el
censo tomado dentro del mismo `with`.

La diferencia con `bench/salidas-hito5/_sonda.py` (K1) es justo esa: K1 midió
`rc`, bytes y centinela; aquí además se pasa `filex.contrato.verificar()`.

    python bench/salidas-sondeo-doc/_sonda_p5.py [--solo ID,ID]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import contrato, invocacion  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

from _sonda23 import CENTINELA, ENT_K1, ENT_MIO, SAL, sha, texto_de  # noqa: E402

IMAGEN = os.environ.get("FILEX_IMAGEN_DOC", "filex-c13")

#: Tope de FUERA; el de DENTRO se le resta 10, igual que hace
#: `motor_contenedor.MARGEN_TOPE`. El de dentro tiene que disparar primero.
TIMEOUT = 100.0
TOPE_DENTRO = 90


def argv_docker(entrada_host: str, nombre_dentro: str, trabajo: str,
                orden: list[str]) -> list[str]:
    """Igual que `motor_contenedor._argv_docker`, con el tope DENTRO.

    K1 dejó su `_sonda.py` **sin** el tope de dentro a propósito (es el registro
    de lo que se midió, y lo que se midió incluye el fallo). Aquí sí va: tres
    `soffice` colgados sobrevivieron 37 minutos al `taskkill`.
    """
    return [
        "docker", "run", "--rm", "--init", "--network", "none",
        "--entrypoint", "timeout",
        "--mount", f"type=bind,source={entrada_host.replace(os.sep, '/')},"
                   f"target=/ent/{nombre_dentro},readonly",
        "--mount", f"type=bind,source={trabajo.replace(os.sep, '/')},target=/trabajo",
        "-w", "/trabajo",
        "-e", "HOME=/tmp",
        IMAGEN,
        "-k", "5", str(TOPE_DENTRO),
    ] + orden


def entrada_de(ext: str) -> str:
    a = os.path.join(ENT_MIO, f"entrada.{ext}")
    return a if os.path.isfile(a) else os.path.join(ENT_K1, f"entrada.{ext}")


# (id, motor, origen, destino, rasteriza, plantilla(ent_dentro, sal_dentro))
CASOS = [
    # --- semillas: producen entrada.xlsx y entrada.pptx, y son aristas de pleno
    #     derecho (el pendiente 5 pide `xlsx` y `pptx`, no solo consumirlos).
    ("Q01", "doc_libreoffice", "csv", "xlsx", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "xlsx",
                   "--outdir", "/trabajo", e]),
    ("Q02", "doc_pandoc", "md", "pptx", False,
     lambda e, s: ["pandoc", e, "-o", s]),

    # --- LibreOffice: hoja de cálculo -------------------------------------
    ("Q03", "doc_libreoffice", "xlsx", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
                   "--outdir", "/trabajo", e]),
    ("Q04", "doc_libreoffice", "xlsx", "csv", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "csv",
                   "--outdir", "/trabajo", e]),
    ("Q05", "doc_libreoffice", "xlsx", "html", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "html",
                   "--outdir", "/trabajo", e]),
    ("Q06", "doc_libreoffice", "csv", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
                   "--outdir", "/trabajo", e]),

    # --- LibreOffice: presentación ----------------------------------------
    ("Q07", "doc_libreoffice", "pptx", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
                   "--outdir", "/trabajo", e]),
    ("Q08", "doc_libreoffice", "pptx", "odp", False,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "odp",
                   "--outdir", "/trabajo", e]),
    # el que debería RASTERIZAR
    ("Q09", "doc_libreoffice", "pptx", "png", True,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "png",
                   "--outdir", "/trabajo", e]),

    # --- LibreOffice: SVG. `magick svg→png` es real en Windows y NOMINAL en
    #     este mismo Debian: la pregunta es si soffice lo salva.
    ("Q10", "doc_libreoffice", "svg", "pdf", True,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
                   "--outdir", "/trabajo", e]),
    ("Q11", "doc_libreoffice", "svg", "png", True,
     lambda e, s: ["soffice", "--headless", "--norestore", "--convert-to", "png",
                   "--outdir", "/trabajo", e]),

    # --- Pandoc: LaTeX ------------------------------------------------------
    ("Q12", "doc_pandoc", "md", "tex", False,
     lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("Q13", "doc_pandoc", "docx", "tex", False,
     lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("Q14", "doc_pandoc", "tex", "docx", False,
     lambda e, s: ["pandoc", e, "-o", s]),
    ("Q15", "doc_pandoc", "tex", "html", False,
     lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("Q16", "doc_pandoc", "tex", "pdf", False,
     lambda e, s: ["pandoc", e, "--pdf-engine=xelatex", "-o", s]),
    ("Q17", "doc_pandoc", "pptx", "md", False,
     lambda e, s: ["pandoc", e, "-o", s]),
]

#: Qué caso fabrica cada semilla que no viene escrita a mano.
SEMILLA_DE = {"xlsx": "Q01", "pptx": "Q02"}


def una(caso, out: str) -> dict:
    cid, motor, o, d, rast, plantilla = caso
    ent = entrada_de(o)
    reg = {"id": cid, "motor": motor, "origen": o, "destino": d,
           "rasteriza_esperado": rast}
    if not os.path.isfile(ent):
        reg.update({"rc": None, "motivo": f"falta la semilla entrada.{o}"})
        return reg

    t = DirectorioDeTrabajo(prefijo="filex-s3p5-")
    try:
        nombre_dentro = f"salida.{o}"     # el STEM decide el nombre de LibreOffice
        nombre_salida = f"salida.{d}"
        argv = argv_docker(ent, nombre_dentro, t.ruta,
                           plantilla(f"/ent/{nombre_dentro}", f"/trabajo/{nombre_salida}"))
        reg["argv"] = argv
        r = invocacion.ejecutar(argv, timeout=TIMEOUT, cwd=t.ruta)
        reg["rc"] = r.rc
        reg["ms"] = round(r.ms, 1)
        reg["agotado"] = r.agotado
        reg["motivo"] = r.motivo
        reg["err_cola"] = (r.err or "").strip()[-200:]

        # --- el punto 5, tomado AQUÍ: después ya no existe ------------------
        censo = t.censo()
        reg["censo"] = censo["despues"][os.path.abspath(t.ruta)]
        reg["sobrantes"] = t.sobrantes([nombre_salida])

        dst = t.destino(nombre_salida)
        if os.path.isfile(dst):
            res = contrato.verificar(dst, ent, {"destino": d}, censo)
            reg["contrato"] = res.get("veredicto")
            reg["cobertura"] = res.get("cobertura", {})
            reg["hallazgos"] = [{"regla": h.get("regla"), "sev": h.get("severidad"),
                                 "msg": h.get("mensaje")}
                                for h in (res.get("hallazgos") or [])]
            reg["bytes"] = os.path.getsize(dst)
            reg["sha256"] = sha(dst)
            txt = texto_de(dst)
            reg["caracteres"] = len(txt)
            reg["centinela"] = CENTINELA in txt
            reg["tabla_ax1"] = "AX-1" in txt
            os.makedirs(out, exist_ok=True)
            t.recoger(nombre_salida, os.path.join(out, f"{cid}_{o}2{d}.{d}"))
            # Las dos semillas se quedan también en `entradas/`.
            if SEMILLA_DE.get(d) == cid:
                import shutil
                shutil.copy2(os.path.join(out, f"{cid}_{o}2{d}.{d}"),
                             os.path.join(ENT_MIO, f"entrada.{d}"))
        else:
            reg.update({"contrato": "sin_salida", "bytes": 0, "caracteres": 0,
                        "centinela": False, "tabla_ax1": False})
    finally:
        t.cerrar()
    return reg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--salida", default=os.path.join(SAL, "sonda-p5.json"))
    ap.add_argument("--out", default=os.path.join(SAL, "out-p5"))
    a = ap.parse_args()
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    solo = {x.strip() for x in a.solo.split(",") if x.strip()}
    casos = [c for c in CASOS if not solo or c[0] in solo]
    os.makedirs(ENT_MIO, exist_ok=True)

    # Con `--solo`, los casos que no se repiten se CONSERVAN. Volcar solo los
    # seleccionados borraría el resto del fichero, que es una manera silenciosa
    # de perder medidas.
    previos = {}
    if os.path.isfile(a.salida):
        try:
            with open(a.salida, encoding="utf-8") as f:
                previos = {x["id"]: x for x in json.load(f)}
        except Exception:
            previos = {}

    t0 = time.time()
    for c in casos:
        reg = una(c, a.out)
        previos[reg["id"]] = reg
        res = [previos[k] for k in sorted(previos)]
        print(f"{reg['id']:<4} {reg['motor']:<16} {reg['origen']:>5}→{reg['destino']:<5} "
              f"rc={reg.get('rc')} {reg.get('ms', 0):>8.0f} ms "
              f"{reg.get('bytes', 0):>9} B car={reg.get('caracteres', 0):>6} "
              f"cent={'S' if reg.get('centinela') else 'n'} "
              f"contrato={str(reg.get('contrato')):<10} "
              f"sobra={len(reg.get('sobrantes') or {})}", flush=True)
        with open(a.salida, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\ntotal {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
