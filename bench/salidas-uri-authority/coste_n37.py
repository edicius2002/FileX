"""N37 — el coste, y sobre todo DÓNDE no lo hay (trampa 28).

La trampa 28 avisa de que R1 y R4 están en tensión: denegar por lista blanca
cuesta 9,4 µs y «existe pero no» 193,3 µs, **×20,6**, y *igualar por arriba
convierte el rechazo en un amplificador de DoS*. Así que la pregunta no es
«¿cuánto cuesta el arreglo?» sino **«¿mete trabajo en el camino de
denegación?»**.

Respuesta corta, y se mide en vez de afirmarse: no. `_uri_a_ruta` corre **una
vez por root y una sola vez por sesión** (dentro de `Raices.asegurar`, que se
sella con `_resuelto`), y el camino que la trampa 28 mide —
`Confinamiento.resolver()`— no cambia ni una línea. Las dos cosas se miden
igual, porque «no cambia» es una afirmación como cualquier otra.

Las dos versiones de `_uri_a_ruta` se miden **PAREADAS en la misma tanda**
(trampas 59 y 79: una cifra histórica de otra tanda no es comparable), y la
vieja se saca del blob de git y se ejecuta tal cual — no se reescribe de
memoria, que sería medir una paráfrasis. Control de identidad incluido: si los
dos fuentes coinciden, la medida no vale nada.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import confinamiento as _conf  # noqa: E402
from filex import mcp as _mcp  # noqa: E402

COMMIT_VIEJO = "2498f4b"          # HEAD de `main` al empezar la ronda 17
N = 20000
N_RESOLVER = 4000


def _funcion_del_blob(commit: str, fichero: str, nombre: str):
    """Saca UNA función del blob y la ejecuta tal cual. Devuelve (fn, fuente)."""
    r = subprocess.run(["git", "show", "%s:%s" % (commit, fichero)],
                       cwd=RAIZ, capture_output=True, timeout=60,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:200])
    fuente = r.stdout.decode("utf-8")
    arbol = ast.parse(fuente)
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre:
            mod = ast.Module(body=[nodo], type_ignores=[])
            ns: dict = {"os": os}
            exec(compile(mod, "<blob %s>" % commit, "exec"), ns)
            return ns[nombre], ast.unparse(nodo)
    raise RuntimeError("no está %s en %s:%s" % (nombre, commit, fichero))


def _mide(fn, entradas, n) -> float:
    """Mediana de microsegundos por llamada, sobre `n` pasadas de la batería."""
    muestras = []
    for _ in range(9):
        t0 = time.perf_counter()
        for _ in range(n // 9):
            for e in entradas:
                fn(e)
        dt = time.perf_counter() - t0
        muestras.append(dt / max(1, (n // 9) * len(entradas)) * 1e6)
    return statistics.median(muestras)


def main() -> int:
    viejo, fuente_viejo = _funcion_del_blob(COMMIT_VIEJO, "filex/mcp.py", "_uri_a_ruta")
    import inspect
    fuente_nuevo = inspect.getsource(_mcp._uri_a_ruta)
    ident = {
        "sha_viejo": hashlib.sha256(fuente_viejo.encode()).hexdigest()[:16],
        "sha_nuevo": hashlib.sha256(fuente_nuevo.encode()).hexdigest()[:16],
    }
    ident["SON_DISTINTAS"] = ident["sha_viejo"] != ident["sha_nuevo"]

    # Batería: mezcla de lo que se acepta y de lo que se rechaza, porque el
    # coste del rechazo es justo lo que la trampa 28 vigila.
    ACEPTA = ["file:///D:/Work/research/FileX", "file://localhost/D:/Work"]
    RECHAZA = ["file://servidor/recurso", "file://", "file:///recurso",
               "http://x/y"]
    TODO = ACEPTA + RECHAZA

    r: dict = {"identidad": ident, "n_por_celda": N}
    for etiqueta, bateria in (("acepta", ACEPTA), ("rechaza", RECHAZA),
                              ("mezcla", TODO)):
        r["uri_a_ruta_us_" + etiqueta] = {
            "viejo": round(_mide(viejo, bateria, N), 4),
            "nuevo": round(_mide(_mcp._uri_a_ruta, bateria, N), 4),
        }
        a = r["uri_a_ruta_us_" + etiqueta]
        a["ratio_nuevo_sobre_viejo"] = round(a["nuevo"] / a["viejo"], 3)

    # ---- El camino que la trampa 28 mide DE VERDAD: `resolver()`.
    d = os.path.join(RAIZ, "bench", "salidas-uri-authority")
    c = _conf.Confinamiento([d])
    dentro = os.path.join(d, "MANIFIESTO.md")
    prohibido = "C:\\Windows\\win.ini"          # fuera de la lista blanca (R1)
    no_existe = os.path.join(d, "no-existe-jamas.bin")
    r["resolver_us"] = {}
    for etiqueta, ruta, espera_denegado in (("prohibido_R1", prohibido, True),
                                            ("no_existe", no_existe, True),
                                            ("existe", dentro, False)):
        def _f(x, _c=c):
            try:
                return _c.resolver(x)
            except _conf.Denegado:
                return None
        r["resolver_us"][etiqueta] = round(_mide(_f, [ruta], N_RESOLVER), 3)
    rr = r["resolver_us"]
    r["resolver_ratio_no_existe_sobre_prohibido"] = round(
        rr["no_existe"] / rr["prohibido_R1"], 2)
    r["nota_resolver"] = ("`Confinamiento.resolver` NO se toca en N37: se mide "
                          "para dejar constancia del orden de magnitud, no como "
                          "un antes/después.")

    # ---- Y el coste de la traza nueva, aislado (trampa 36: no por diferencia).
    r["podadas_us"] = round(
        _mide(lambda x: _conf.Confinamiento._podadas(x), [["", d]], 4000), 3)

    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
