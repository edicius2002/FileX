"""N35 — el coste, con las DOS versiones en la MISMA tanda.

La trampa 28 obliga a esto: «denegar por lista blanca cuesta 9,4 us y "existe
pero no" cuesta 193,3 us —x20,6, porque el predicado lexico de R1 corta antes
del realpath— e igualar por arriba convierte el rechazo en un amplificador de
DoS». Asi que si el arreglo de N35 mete trabajo en el camino de denegacion,
hay que decirlo con numero.

PREDICCION, registrada antes de medir: el camino de denegacion NO se mueve,
porque N35 solo toca `_preparar` y el `__init__` —que corren UNA vez al
construir— y no toca `resolver()` ni `_resolver_sin_ecualizar()` ni una linea.
Lo que si puede moverse es el CONSTRUCTOR.

COMO se mide, y por que asi:

  * Las dos versiones se cargan en EL MISMO PROCESO y se miden INTERCALADAS.
    Comparar dos corridas separadas seria comparar dos tandas, que CLAUDE.md §3
    prohibe —«las cifras absolutas de tandas distintas no son comparables»— y
    la trampa 59 vuelve a prohibir para el caso concreto de comparar contra
    una version historica.
  * La version vieja NO es una reimplementacion mia: se extrae del blob de git
    del commit anterior y se carga como modulo aparte, asi que es literalmente
    el codigo que habia (trampa 79: comprobar que lo que mides es lo que el
    codigo ejecuta).
  * Se mide el TROZO AISLADO, no la diferencia entre dos totales que lo
    contienen (trampa 36).
  * Dos testigos de ruido: deriva dentro de la tanda y nivel de carga de la
    maquina.

Salida: bench/salidas-raices-mixtas/coste.json
"""

from __future__ import annotations

import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

COMMIT_VIEJO = "aab61bb"          # el commit anterior al arreglo de N35
N_TANDAS = 9
N_REPS = 2000


def cargar_version_vieja(destino_py: str):
    """Extrae `filex/confinamiento.py` del commit viejo y lo carga aparte."""
    src = subprocess.run(
        ["git", "-C", RAIZ, "show", "%s:filex/confinamiento.py" % COMMIT_VIEJO],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout
    with open(destino_py, "w", encoding="utf-8") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("conf_viejo", destino_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, src


def mediana_us(fn, reps: int) -> float:
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t0) / reps * 1e6


def testigo_nivel() -> float:
    """Lanzamiento de proceso: mide el NIVEL de carga de la maquina."""
    t0 = time.perf_counter()
    try:
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True,
                       timeout=20)
    except subprocess.TimeoutExpired:
        return 20_000.0
    return (time.perf_counter() - t0) * 1e3


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-coste-")
    legit = os.path.join(base, "legit")
    os.makedirs(legit, exist_ok=True)
    dentro = os.path.join(legit, "dentro.txt")
    open(dentro, "w").close()
    hermano = os.path.join(base, "hermano")
    os.makedirs(hermano, exist_ok=True)
    existe_fuera = os.path.join(hermano, "existe.txt")
    open(existe_fuera, "w").close()

    from filex import confinamiento as nuevo
    viejo, src_viejo = cargar_version_vieja(os.path.join(base, "conf_viejo.py"))

    # Control de que las dos versiones son de verdad distintas (trampa 66: una
    # sonda que devuelve lo mismo para dos configuraciones distintas esta rota).
    control = {
        "vieja_rechaza": "raise ValueError(\"una raíz no puede ser" in src_viejo,
        "nueva_poda": "continue" in open(
            os.path.join(RAIZ, "filex", "confinamiento.py"),
            encoding="utf-8").read().split("def _preparar")[1].split("def ")[0],
        "commit_viejo": COMMIT_VIEJO,
    }
    if not (control["vieja_rechaza"] and control["nueva_poda"]):
        print("ABORTA: las dos versiones no se distinguen. %s" % control)
        return 2

    cn = nuevo.Confinamiento([legit])
    cv = viejo.Confinamiento([legit])

    # `prohibido` corta en el predicado lexico R1; `existe_pero_no` paga el
    # `realpath`. Son los dos caminos que la trampa 28 separa.
    prohibido = os.path.join(base, *(["x"] * 80), "y.txt")   # supera MAX_COMPONENTES
    casos = {
        "denegar_prohibido_R1": (lambda c: (lambda: c.puede_leer(prohibido))),
        "denegar_existe_pero_no": (lambda c: (lambda: c.puede_leer(existe_fuera))),
        "permitir_ruta_valida": (lambda c: (lambda: c.puede_leer(dentro))),
    }

    medidas = {k: {"nueva": [], "vieja": []} for k in casos}
    medidas["construir_raiz_simple"] = {"nueva": [], "vieja": []}
    medidas["construir_MIXTA"] = {"nueva": [], "vieja": []}
    testigos_nivel, derivas = [], []

    for _t in range(N_TANDAS):
        testigos_nivel.append(testigo_nivel())
        t_der0 = time.perf_counter()
        for caso, hacer in casos.items():
            # INTERCALADAS dentro de la tanda: nueva, vieja, nueva, vieja.
            medidas[caso]["nueva"].append(mediana_us(hacer(cn), N_REPS))
            medidas[caso]["vieja"].append(mediana_us(hacer(cv), N_REPS))
        medidas["construir_raiz_simple"]["nueva"].append(
            mediana_us(lambda: nuevo.Confinamiento([legit]), 200))
        medidas["construir_raiz_simple"]["vieja"].append(
            mediana_us(lambda: viejo.Confinamiento([legit]), 200))

        # La MIXTA: la vieja LANZA, asi que su coste incluye construir la
        # excepcion. Se mide lo que cada version hace de verdad, no una
        # version amputada para que se parezcan.
        def _mixta_nueva():
            nuevo.Confinamiento(["C:\\", legit])

        def _mixta_vieja():
            try:
                viejo.Confinamiento(["C:\\", legit])
            except ValueError:
                pass

        medidas["construir_MIXTA"]["nueva"].append(mediana_us(_mixta_nueva, 200))
        medidas["construir_MIXTA"]["vieja"].append(mediana_us(_mixta_vieja, 200))
        derivas.append((time.perf_counter() - t_der0) * 1e3)

    res = {"plataforma": sys.platform, "python": sys.version.split()[0],
           "n_tandas": N_TANDAS, "n_reps": N_REPS, "control": control,
           "testigo_nivel_ms": {"mediana": statistics.median(testigos_nivel),
                                "max": max(testigos_nivel)},
           "testigo_deriva_ms": {"primera": derivas[0], "ultima": derivas[-1],
                                 "ratio": derivas[-1] / derivas[0]},
           "casos": {}}
    for caso, d in medidas.items():
        mn, mv = statistics.median(d["nueva"]), statistics.median(d["vieja"])
        res["casos"][caso] = {
            "nueva_us": round(mn, 3), "vieja_us": round(mv, 3),
            "delta_us": round(mn - mv, 3), "ratio": round(mn / mv, 4) if mv else None,
            "nueva_todas": [round(x, 3) for x in d["nueva"]],
            "vieja_todas": [round(x, 3) for x in d["vieja"]],
        }

    # Suelo de ruido: la dispersion DENTRO de cada version (trampa 36). Una
    # diferencia mas pequena que esto no es una medida.
    for caso, c in res["casos"].items():
        disp = max(max(c["nueva_todas"]) - min(c["nueva_todas"]),
                   max(c["vieja_todas"]) - min(c["vieja_todas"]))
        c["dispersion_intra_us"] = round(disp, 3)
        c["delta_supera_el_ruido"] = abs(c["delta_us"]) > disp

    destino = os.path.join(AQUI, "coste.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    print("testigo NIVEL  (lanzar proceso): %.1f ms de mediana, max %.1f" % (
        res["testigo_nivel_ms"]["mediana"], res["testigo_nivel_ms"]["max"]))
    print("testigo DERIVA (1a vs ultima tanda): x%.3f\n" % (
        res["testigo_deriva_ms"]["ratio"]))
    print("%-26s %10s %10s %10s %8s  %s" % (
        "caso", "nueva us", "vieja us", "delta", "ratio", "¿supera el ruido?"))
    for caso, c in res["casos"].items():
        print("%-26s %10.3f %10.3f %10.3f %8s  %s (ruido %.3f)" % (
            caso, c["nueva_us"], c["vieja_us"], c["delta_us"],
            c["ratio"], c["delta_supera_el_ruido"], c["dispersion_intra_us"]))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
