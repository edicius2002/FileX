"""Presupuesto de tokens del catálogo MCP de FileX — MEDIDO, no estimado.

Método idéntico al de `bench/scripts/mcp_probe_bin.py:262` para que la cifra sea
comparable con las **7.964 / 5.280 / 2.322 / 79** tokens de `RESULTADOS-MCP.md`
§4: `tiktoken`/`o200k_base` sobre el catálogo **serializado como viaja por el
cable** (`model_dump(exclude_none=True, by_alias=True)`, es decir `inputSchema`
en camelCase, que es lo que el cliente recibe).

**No mide una cifra: mide una curva.** El presupuesto de ≤1.200 tokens y las dos
reglas de cobertura (`enum` generados del registro, `description` en cada
parámetro) tiran en direcciones opuestas, y lo que hace falta para decidir es
saber cuánto cuesta exactamente cada una.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_tokens_catalogo.py

Escribe `h4_tokens_catalogo.json` al lado. **Determinista y sin modelo**: no hay
ruido que declarar, la cifra no depende de la tanda.
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


def ntok(s: str) -> int:
    return len(ENC.encode(s, disallowed_special=()))


def serie(herr: list[dict]) -> str:
    return json.dumps(herr, ensure_ascii=False)


def como_cable(fx) -> list[dict]:
    out = []
    for h in M.catalogo(fx):
        out.append(h if isinstance(h, dict)
                   else h.model_dump(exclude_none=True, by_alias=True))
    return out


# ---------------------------------------------------------------- variantes


def sin_anotaciones(herr):
    h = copy.deepcopy(herr)
    for x in h:
        x.pop("annotations", None)
    return h


def sin_descripciones_de_parametro(herr):
    """El estilo FastMCP: **0 de 193** parámetros con `description` (§4)."""
    h = copy.deepcopy(herr)

    def limpia(nodo):
        if isinstance(nodo, dict):
            for k, v in list(nodo.items()):
                if k == "properties" and isinstance(v, dict):
                    for prop in v.values():
                        if isinstance(prop, dict):
                            prop.pop("description", None)
                            limpia(prop)
                else:
                    limpia(v)
        elif isinstance(nodo, list):
            for v in nodo:
                limpia(v)

    for x in h:
        limpia(x.get("inputSchema"))
        # la `description` del objeto `parametros` es de nivel de parámetro
        p = (x.get("inputSchema") or {}).get("properties", {}).get("parametros")
        if isinstance(p, dict):
            p.pop("description", None)
    return h


def sin_enums(herr):
    """Sin los `enum` generados del registro: se pierde la cobertura declarada."""
    h = copy.deepcopy(herr)

    def limpia(nodo):
        if isinstance(nodo, dict):
            nodo.pop("enum", None)
            for v in nodo.values():
                limpia(v)
        elif isinstance(nodo, list):
            for v in nodo:
                limpia(v)

    for x in h:
        limpia(x.get("inputSchema"))
    return h


def sin(herr, *nombres):
    return [x for x in herr if x["name"] not in nombres]


def main() -> int:
    fx = FileX()
    base = como_cable(fx)

    detalle = []
    for x in base:
        esq = x.get("inputSchema") or {}
        props = esq.get("properties", {})
        detalle.append({
            "nombre": x["name"],
            "tokens": ntok(json.dumps(x, ensure_ascii=False)),
            "tokens_nombre": ntok(x["name"]),
            "tokens_description": ntok(x["description"]),
            "tokens_inputSchema": ntok(json.dumps(esq, ensure_ascii=False)),
            "tokens_annotations": (ntok(json.dumps(x["annotations"], ensure_ascii=False))
                                   if x.get("annotations") else 0),
            "n_parametros": len(props),
            "n_parametros_con_description": sum(
                1 for p in props.values() if isinstance(p, dict) and p.get("description")),
        })

    variantes = {
        "A_vigente_5_herramientas": base,
        "B_sin_anotaciones": sin_anotaciones(base),
        "C_sin_description_por_parametro": sin_descripciones_de_parametro(base),
        "D_sin_enums_del_registro": sin_enums(base),
        "E_cuatro_del_plan_sin_job": sin(base, "job"),
        "F_cuatro_sin_job_sin_anotaciones": sin_anotaciones(sin(base, "job")),
        "G_minimo_estilo_FastMCP": sin_enums(
            sin_descripciones_de_parametro(sin_anotaciones(base))),
    }

    res = {
        "metodo": "tiktoken/o200k_base sobre model_dump(exclude_none, by_alias) "
                  "serializado con json.dumps(ensure_ascii=False) — igual que "
                  "bench/scripts/mcp_probe_bin.py:262",
        "motores_disponibles": [m.nombre for m in fx.disponibles],
        "motores_ausentes": [m.nombre for m in fx.ausentes],
        "aristas_en_el_grafo": len(fx.grafo.aristas),
        "n_enum_origen": len(M._enum_origen(fx)),
        "n_enum_destino": len(M._enum_destino(fx)),
        "presupuesto_declarado": M.PRESUPUESTO_CATALOGO,
        "por_herramienta": detalle,
        "tokens_solo_nombres": ntok(" ".join(x["name"] for x in base)),
        "variantes": {k: ntok(serie(v)) for k, v in variantes.items()},
        "n_herramientas": len(base),
        "referencia_del_sector": {
            "video-audio-mcp_27": 7964, "docling-mcp_19": 5280,
            "kordoc_15": 7759, "servers_filesystem_14": 3360,
            "ffmpeg-mcp-lite_8": 2322, "image-worker-mcp_2": 1177,
            "markitdown-mcp_1": 79,
        },
    }
    res["tokens_catalogo"] = res["variantes"]["A_vigente_5_herramientas"]
    res["dentro_del_presupuesto"] = res["tokens_catalogo"] <= M.PRESUPUESTO_CATALOGO

    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "h4_tokens_catalogo.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    print(f"catálogo vigente: {res['tokens_catalogo']} tokens "
          f"({res['n_herramientas']} herramientas) · presupuesto "
          f"{M.PRESUPUESTO_CATALOGO} · nombres {res['tokens_solo_nombres']}")
    for d in detalle:
        print(f"  {d['nombre']:<13} {d['tokens']:>5}  desc {d['tokens_description']:>4} "
              f"esq {d['tokens_inputSchema']:>4}  anot {d['tokens_annotations']:>3} "
              f"· {d['n_parametros_con_description']}/{d['n_parametros']} parám. descritos")
    print("  --- variantes ---")
    a = res["variantes"]["A_vigente_5_herramientas"]
    for k, v in res["variantes"].items():
        print(f"  {k:<34} {v:>5}   ({v - a:+d})")
    print(f"  -> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
