"""La ganancia REAL del componente `motor` sobre la historia del repositorio.

`de_clase_en_fuente()` no recorre el MRO, asi que la tabla de `historia.py`
SOBRESTIMA la ganancia: en produccion `cadena_de_clase()` ya arrastraba las
bases. Aqui se reproduce la huella de PRODUCCION sobre el fuente historico
—cadena de bases dentro del mismo fichero, en orden— con los dos algoritmos.

Refutar la propia ganancia es parte del encargo.

Salida: bench/salidas-huella/historia_motor.json
"""
from __future__ import annotations

import ast
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
    src = _git("show", "HEAD:filex/huella.py")
    p = os.path.join(SAL, "_huella_head.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("_huella_head2", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VIEJA = _carga_vieja()


def _cadena(arbol: ast.Module, nombre: str) -> list:
    """Cadena de bases DENTRO del fichero, en orden de declaracion, como haria
    el MRO para una jerarquia lineal. `cadena_de_clase()` hace esto con
    `cls.__mro__`; aqui se aproxima sobre el AST, que es lo unico que hay de un
    commit historico."""
    porn = {n.name: n for n in arbol.body if isinstance(n, ast.ClassDef)}
    fuera, pend = [], [nombre]
    while pend:
        c = pend.pop(0)
        if c in fuera or c not in porn:
            continue
        fuera.append(c)
        for b in porn[c].bases:
            if isinstance(b, ast.Name):
                pend.append(b.id)
    return fuera


def _sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def huella_produccion(src: str, nombre: str, mod) -> str:
    """`cadena_de_clase()` + `de_clase()` reproducidos sobre un fuente."""
    arbol = ast.parse(src)
    if mod is NUEVA:
        tabla = mod._tabla(arbol)
        por_clase = {n.name: mod._sello(tabla, mod._cierre(tabla, (n.name,)))
                     for n in arbol.body if isinstance(n, ast.ClassDef)}
    else:
        por_clase = {n.name: _sha(ast.dump(mod._limpio(n), annotate_fields=True,
                                           include_attributes=False))
                     for n in arbol.body if isinstance(n, ast.ClassDef)}
    cad = _cadena(arbol, nombre)
    if not cad:
        return "sin_clase"
    return _sha("|".join(f"{n}={por_clase[n]}" for n in cad))


def main() -> None:
    res = {}
    for fichero, clases in (("filex/motores.py",
                             ["ImageMagick", "Ghostscript", "FFmpeg"]),
                            ("filex/motor_contenedor.py",
                             ["PandocEnContenedor", "LibreOfficeEnContenedor",
                              "CalibreEnContenedor"])):
        filas = []
        cs = [ln.split(" ", 1) for ln in
              _git("log", "--format=%h %s", "--", fichero).strip().split("\n")
              if ln.strip()]
        for sha, asunto in reversed(cs):
            src = _git("show", f"{sha}:{fichero}")
            if not src:
                continue
            f = {"commit": sha, "asunto": asunto[:60],
                 "crudo": hashlib.sha256(src.encode()).hexdigest()[:12]}
            for c in clases:
                try:
                    f[c] = {"viejo": huella_produccion(src, c, VIEJA),
                            "nuevo": huella_produccion(src, c, NUEVA)}
                except Exception as e:      # commit anterior a la clase
                    f[c] = {"viejo": f"err:{e}", "nuevo": f"err:{e}"}
            filas.append(f)
        res[fichero] = filas

        print(f"=== {fichero} — huella de PRODUCCION reproducida ===")
        prev = None
        for f in filas:
            t = []
            for c in clases:
                v = "V!" if prev and f[c]["viejo"] != prev[c]["viejo"] else "V="
                n = "N!" if prev and f[c]["nuevo"] != prev[c]["nuevo"] else "N="
                marca = "  <-- SOLO EL NUEVO" if v == "V=" and n == "N!" else ""
                t.append(f"{c[:14]:14s}:{v}/{n}{marca}")
            print(f"{f['commit']} | " + " ".join(t) + f" | {f['asunto']}")
            prev = f
        print()

    with open(os.path.join(SAL, "historia_motor.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
