"""Coste en catalogo de migrar `job` a Tasks nativas (SEP-1686).

Metodo IDENTICO al de `bench/salidas-hito4/h4_tokens_catalogo.py` para que la
cifra sea comparable: `tiktoken`/`o200k_base` sobre el catalogo serializado
**como viaja por el cable** (`model_dump(exclude_none=True, by_alias=True)`).

Mide tres escenarios, no uno:

  E0  hoy                      — las 5 herramientas, `job` incluida
  E1  migracion completa       — se retira `job`; el asa la lleva el protocolo
  E2  soporte doble            — `job` se queda y las herramientas largas se
                                 anotan `execution.taskSupport`, como hacia el
                                 SDK 1.23-1.29

Determinista y sin modelo: no hay ruido que declarar.

    .venv-mcp-filex\\Scripts\\python.exe bench/salidas-tasks-protocolo/coste_catalogo_tasks.py
"""

from __future__ import annotations

import copy
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ)

import tiktoken                                                   # noqa: E402

from filex import mcp as M                                        # noqa: E402
from filex.nucleo import FileX                                    # noqa: E402

ENC = tiktoken.get_encoding("o200k_base")
# Las herramientas que tardan y que serian candidatas a tarea nativa.
LARGAS = ("convert", "batch")


def ntok(s: str) -> int:
    return len(ENC.encode(s, disallowed_special=()))


def serie(herr) -> str:
    return json.dumps(herr, ensure_ascii=False)


def como_cable(fx):
    out = []
    for h in M.catalogo(fx):
        out.append(h if isinstance(h, dict)
                   else h.model_dump(exclude_none=True, by_alias=True))
    return out


def main():
    fx = FileX()
    base = como_cable(fx)

    R = {"metodo": "tiktoken o200k_base sobre el catalogo serializado como cable",
         "n_aristas": None}
    try:
        R["n_aristas"] = len(fx.grafo.aristas())
    except Exception:
        try:
            R["n_aristas"] = sum(len(v) for v in fx.grafo.adyacencia.values())
        except Exception:
            R["n_aristas"] = "no sondeable por esta via"

    # ---------------------------------------------------------------- E0 hoy
    e0 = {"herramientas": [h["name"] for h in base],
          "n_herramientas": len(base),
          "tokens_total": ntok(serie(base)),
          "tokens_por_herramienta": {h["name"]: ntok(serie(h)) for h in base}}
    R["E0_hoy"] = e0

    # ------------------------------------------- E1 migracion: fuera `job`
    sin_job = [copy.deepcopy(h) for h in base if h["name"] != "job"]
    e1 = {"herramientas": [h["name"] for h in sin_job],
          "n_herramientas": len(sin_job),
          "tokens_total": ntok(serie(sin_job))}
    e1["ahorro_tokens"] = e0["tokens_total"] - e1["tokens_total"]
    e1["ahorro_pct"] = round(100.0 * e1["ahorro_tokens"] / e0["tokens_total"], 2)
    R["E1_migracion"] = e1

    # --------------------------------- E2 doble: `job` + anotacion execution
    # Forma exacta que autorregistraba el SDK 1.23-1.29 (sdk-mcp-capacidades §3.1).
    doble = [copy.deepcopy(h) for h in base]
    tocadas = []
    for h in doble:
        if h["name"] in LARGAS:
            h["execution"] = {"taskSupport": "optional"}
            tocadas.append(h["name"])
    e2 = {"anotadas": tocadas,
          "n_herramientas": len(doble),
          "tokens_total": ntok(serie(doble))}
    e2["sobrecoste_tokens"] = e2["tokens_total"] - e0["tokens_total"]
    e2["sobrecoste_pct"] = round(100.0 * e2["sobrecoste_tokens"] / e0["tokens_total"], 2)
    R["E2_doble"] = e2

    # ------------------- control: coste de UNA anotacion execution, aislado
    # Trampa 36: se mide el trozo aislado, no la diferencia entre dos totales.
    R["control_anotacion_aislada"] = {
        "fragmento": '"execution": {"taskSupport": "optional"}',
        "tokens": ntok(serie({"execution": {"taskSupport": "optional"}})),
    }

    sal = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "coste_catalogo_tasks.json")
    with open(sal, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, ensure_ascii=False)
    print(json.dumps(R, indent=2, ensure_ascii=False))
    print("\n-> %s" % sal)


if __name__ == "__main__":
    main()
