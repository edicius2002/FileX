"""Valida la huella contra la HISTORIA REAL del repositorio, como hizo D1.

Recorre los commits que tocaron cada fichero, saca su fuente con `git show` y
calcula la huella con el algoritmo VIEJO (el de HEAD) y con el NUEVO (el del
arbol de trabajo). Una huella sirve si se mueve CUANDO TOCA y no cuando no.

Salida: bench/salidas-huella/historia.json
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from filex import huella as NUEVA  # noqa: E402


def _git(*a) -> str:
    return subprocess.run(["git", "-C", RAIZ, *a], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=120).stdout


def _carga_vieja():
    """`filex/huella.py` tal como esta en HEAD, importado como modulo aparte."""
    src = _git("show", "HEAD:filex/huella.py")
    p = os.path.join(SAL, "_huella_head.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("_huella_head", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VIEJA = _carga_vieja()


def commits(fichero: str) -> list:
    out = _git("log", "--format=%h %s", "--", fichero)
    return [ln.split(" ", 1) for ln in out.strip().split("\n") if ln.strip()]


def sha_crudo(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def contrato(sha: str) -> dict:
    src = _git("show", f"{sha}:filex/verificador.py")
    if not src:
        return {}
    return {"crudo": sha_crudo(src),
            "viejo": VIEJA.de_alcance(src, VIEJA.ENTRADAS_CONTRATO),
            "nuevo": NUEVA.de_alcance(src, NUEVA.ENTRADAS_CONTRATO)}


def motores(sha: str, fichero: str, clases: list) -> dict:
    src = _git("show", f"{sha}:{fichero}")
    if not src:
        return {}
    fuera = {"crudo": sha_crudo(src)}
    for c in clases:
        fuera[c] = {"viejo": VIEJA.de_clase_en_fuente(src, c),
                    "nuevo": NUEVA.de_clase_en_fuente(src, c)}
    return fuera


def main() -> None:
    res = {"contrato": [], "motores": [], "motor_contenedor": []}

    cs = commits("filex/verificador.py")
    for sha, asunto in reversed(cs):
        h = contrato(sha)
        if h:
            res["contrato"].append({"commit": sha, "asunto": asunto[:64], **h})

    for clave, fichero, clases in (
            ("motores", "filex/motores.py",
             ["ImageMagick", "Ghostscript", "FFmpeg"]),
            ("motor_contenedor", "filex/motor_contenedor.py",
             ["_EnContenedor", "PandocEnContenedor"])):
        for sha, asunto in reversed(commits(fichero)):
            h = motores(sha, fichero, clases)
            if h:
                res[clave].append({"commit": sha, "asunto": asunto[:64], **h})

    with open(os.path.join(SAL, "historia.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)

    # ------------------------------------------------------------ informe
    for clave in ("contrato",):
        print(f"=== {clave} (filex/verificador.py) ===")
        prev = None
        for f in res[clave]:
            mv = lambda k: ("" if prev is None else
                            ("CAMBIA" if f[k] != prev[k] else "  =   "))
            print(f"{f['commit']}  crudo {f['crudo']} {mv('crudo'):7s}"
                  f" | viejo {f['viejo']} {mv('viejo'):7s}"
                  f" | NUEVO {f['nuevo']} {mv('nuevo'):7s} | {f['asunto']}")
            prev = f

    for clave, clases in (("motores", ["ImageMagick", "Ghostscript", "FFmpeg"]),
                          ("motor_contenedor",
                           ["_EnContenedor", "PandocEnContenedor"])):
        print(f"\n=== {clave} ===")
        prev = None
        for f in res[clave]:
            trozos = []
            for c in clases:
                v = "V!" if prev and f[c]["viejo"] != prev[c]["viejo"] else "V ="
                n = "N!" if prev and f[c]["nuevo"] != prev[c]["nuevo"] else "N ="
                trozos.append(f"{c[:12]}:{v}/{n}")
            crudo = "CAMBIA" if prev and f["crudo"] != prev["crudo"] else "  =   "
            print(f"{f['commit']} crudo {crudo} " + " ".join(trozos)
                  + f" | {f['asunto']}")
            prev = f


if __name__ == "__main__":
    main()
