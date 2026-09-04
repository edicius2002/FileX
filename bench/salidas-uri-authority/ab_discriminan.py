"""N37 — el A/B que decide si las pruebas DISCRIMINAN, y si N34 y N35 siguen vivos.

Ésta es la tercera ronda seguida sobre la lista blanca: N34 cerró una fuga que
**abría de más**, N35 la que **cerraba de más**, y las dos vivían en el mismo
`except`. El riesgo dominante ya no es equivocarse: es **deshacer sin querer**
uno de los dos arreglos anteriores. Que la suite pase no lo demuestra — lo
demuestra que las pruebas de aquellos arreglos sigan **ROJAS contra el código de
antes de aquellos arreglos**.

Cinco disciplinas, todas de trampas pagadas:

* **119** — `git stash push` sobre un fichero YA COMMITEADO no hace nada,
  devuelve 0 y el A/B corre dos veces contra el código nuevo dando «todo OK»,
  que es la pinta exacta de «mis pruebas no discriminan». Aquí se revierte con
  `git show <commit>:<fichero>` y **se comprueba la identidad**: si dos
  versiones tienen el mismo sha256, la celda se marca `SIN_CONTRASTE` y no
  cuenta.
* **84** — no se edita el código bajo medición: cada versión se monta en una
  COPIA del árbol, y el árbol vivo no se toca en ningún momento.
* **25 / 38** — un rojo no basta: se registra **por qué** falla. Un
  `AttributeError` al cargar el módulo no es la misma evidencia que la aserción
  que se quería ver caer, y desde fuera se parecen.
* **60** — antes de comparar dos versiones de una fuente hay que comprobar que
  las dos COMPILAN; si no, el rojo puede venir del intérprete y no del cambio.

Uso:
    .venv-mcp-filex\\Scripts\\python.exe bench/salidas-uri-authority/ab_discriminan.py
"""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Las tres versiones del código que hay que contrastar. Los hashes son de
#: `main`, no de esta rama: sobreviven al `--squash` (trampa 115).
VERSIONES = {
    # HEAD de `main` al empezar la ronda 17 = mi código de partida, ya con N34 y
    # N35 dentro. Es el «antes» de N37.
    "antes_de_N37": ("2498f4b", ["filex/mcp.py", "filex/confinamiento.py"]),
    # Antes de la ronda 15: sin el candado asíncrono de N34.
    "antes_de_N34": ("82cf1f3", ["filex/mcp.py"]),
    # Antes de la ronda 16: `_preparar` invalidaba el conjunto en vez de podar.
    "antes_de_N35": ("a4dc3f3", ["filex/mcp.py", "filex/confinamiento.py"]),
}

#: Qué se corre en cada versión, y qué se espera.
SELECCIONES = {
    "N37 (mías)": ("pruebas/test_hito4.py", "AuthorityDeUriN37 or RaizVaciaN37"),
    "N34": ("pruebas/test_hito4.py", "RaicesEnConcurrencia"),
    "N35 por MCP": ("pruebas/test_hito4.py", "RaicesMixtasPorMCP"),
    "N35 en el núcleo": ("pruebas/test_hito1.py", "RaicesMixtasN35"),
}

PLAN = [
    # (version, seleccion, lo_que_se_exige)
    ("ACTUAL", "N37 (mías)", "verde"),
    ("ACTUAL", "N34", "verde"),
    ("ACTUAL", "N35 por MCP", "verde"),
    ("ACTUAL", "N35 en el núcleo", "verde"),
    ("antes_de_N37", "N37 (mías)", "rojo"),
    ("antes_de_N34", "N34", "rojo"),
    ("antes_de_N35", "N35 por MCP", "rojo"),
    ("antes_de_N35", "N35 en el núcleo", "rojo"),
    # Control cruzado: mi cambio no puede ser lo que pone rojo a N34/N35.
    ("antes_de_N37", "N34", "verde"),
    ("antes_de_N37", "N35 por MCP", "verde"),
]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def _blob(commit: str, fichero: str) -> bytes:
    r = subprocess.run(["git", "show", "%s:%s" % (commit, fichero)],
                       cwd=RAIZ, capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError("git show %s:%s -> %s" % (commit, fichero,
                                                     r.stderr.decode()[:200]))
    return r.stdout


def monta(destino: str, version: str, identidades: dict) -> None:
    """Copia el árbol y, si toca, sustituye los ficheros por su versión vieja."""
    for sub in ("filex", "pruebas"):
        shutil.copytree(os.path.join(RAIZ, sub), os.path.join(destino, sub),
                        ignore=shutil.ignore_patterns("__pycache__"))
    if version == "ACTUAL":
        for f in ("filex/mcp.py", "filex/confinamiento.py"):
            with open(os.path.join(RAIZ, f), "rb") as fh:
                identidades.setdefault(f, {})["ACTUAL"] = _sha(fh.read())
        return
    commit, ficheros = VERSIONES[version]
    for f in ficheros:
        b = _blob(commit, f)
        identidades.setdefault(f, {})[version] = _sha(b)
        with open(os.path.join(destino, f), "wb") as fh:
            fh.write(b)


def corre(destino: str, fichero: str, k: str) -> dict:
    # Trampa 60: que las dos fuentes COMPILEN antes de comparar nada.
    compila = {}
    for f in ("filex/mcp.py", "filex/confinamiento.py"):
        p = os.path.join(destino, f)
        try:
            py_compile.compile(p, doraise=True, cfile=p + "c")
            compila[f] = True
        except Exception as e:
            compila[f] = "%s: %s" % (type(e).__name__, str(e)[:120])
    r = subprocess.run(
        [sys.executable, "-m", "pytest", fichero, "-k", k, "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=destino, capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": destino})
    salida = (r.stdout or "") + (r.stderr or "")
    # Trampa 25/38: por qué falla, no sólo que falla.
    motivos = sorted({ln.split(" ")[0] for ln in salida.splitlines()
                      if ln.startswith("E   ") or ln.startswith("FAILED")})
    ultimas = [ln for ln in salida.strip().splitlines() if ln.strip()][-3:]
    tipos = sorted({w for ln in salida.splitlines() if ln.startswith("E   ")
                    for w in [ln[4:].split(":")[0].strip()] if w})
    return {
        "rc": r.returncode,
        "veredicto": "verde" if r.returncode == 0 else "rojo",
        "compila": compila,
        "clases_de_error": tipos[:6],
        "cola": ultimas,
        "n_failed": salida.count("FAILED"),
    }


def main() -> int:
    identidades: dict = {}
    montados: dict = {}
    resultados = []
    base = tempfile.mkdtemp(prefix="n37-ab-")
    try:
        for version in ["ACTUAL"] + list(VERSIONES):
            d = os.path.join(base, version)
            os.makedirs(d, exist_ok=True)
            monta(d, version, identidades)
            montados[version] = d

        # --- Control de IDENTIDAD (trampa 119): ¿son distintas de verdad?
        contraste = {}
        for f, porv in identidades.items():
            act = porv.get("ACTUAL")
            for v, s in porv.items():
                if v == "ACTUAL":
                    continue
                contraste["%s @ %s" % (f, v)] = {
                    "sha_actual": act, "sha_vieja": s,
                    "SON_DISTINTAS": act != s,
                }

        for version, sel, exige in PLAN:
            fichero, k = SELECCIONES[sel]
            r = corre(montados[version], fichero, k)
            r.update({"version": version, "seleccion": sel, "se_exige": exige})
            r["CUMPLE"] = (r["veredicto"] == exige)
            resultados.append(r)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    ok = all(r["CUMPLE"] for r in resultados)
    print(json.dumps({
        "nota": "A/B de N37: ¿discriminan mis pruebas y siguen vivos N34 y N35?",
        "python": sys.version.split()[0],
        "control_de_identidad": contraste,
        "todas_las_versiones_contrastan": all(
            c["SON_DISTINTAS"] for c in contraste.values()),
        "TODAS_LAS_CELDAS_CUMPLEN": ok,
        "celdas": resultados,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
