"""Ítem 5 de C36 — la prueba de subsunción automática del catálogo.

`PLAN-ORQUESTADOR.md` §4.4 la enuncia así:

    «si el esquema de la herramienta A es un subconjunto estricto del de B
     **con la misma semántica**, A sobra.»

**La regla tiene DOS conjuntos y sólo el primero es automatizable.** Este módulo
implementa el primero —el esquema— y mide lo que ese medio predicado atrapa y lo
que se le escapa **contra un caso donde la respuesta ya se conoce**: las 27
herramientas de `video-audio-mcp`, de las que `RESULTADOS-MCP.md` §4 midió que
**13 son casos particulares de 2**.

Un comprobador que sólo se ejecuta sobre el catálogo de FileX —cinco
herramientas con nombres de parámetro disjuntos— devolvería **0 siempre**, con
el arreglo y sin él: es la trampa 60/109 (un `assert` que nunca se puede
evaluar a falso es indistinguible de uno que se cumple). Por eso el control
positivo no es un adorno: es la mitad que hace que el 0 signifique algo.

    python bench/salidas-mcp-cabos-techos/subsuncion.py
"""
from __future__ import annotations

import ast
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, _RAIZ)

OUT = os.path.join(_AQUI, "subsuncion.json")

#: El servidor de referencia. Vive en `repos/`, que está en `.gitignore`: por eso
#: el control positivo de `pruebas/test_hito4.py` es SINTÉTICO y hermético, y la
#: medida contra el servidor real vive aquí, en `bench/`.
REF = os.path.join("D:", os.sep, "Work", "research", "FileX", "repos",
                   "mcp-refs", "video-audio-mcp", "server.py")

#: Las 13 que `RESULTADOS-MCP.md` §4 declara casos particulares de 2, con su
#: subsumidor. Es el patrón contra el que se mide el recall del medio predicado.
#: No se deduce del código: se copia del informe, y luego se compara.
CONOCIDAS = {
    "convert_video_format": "convert_video_properties",
    "set_video_resolution": "convert_video_properties",
    "set_video_codec": "convert_video_properties",
    "set_video_bitrate": "convert_video_properties",
    "set_video_frame_rate": "convert_video_properties",
    "set_video_audio_track_codec": "convert_video_properties",
    "set_video_audio_track_bitrate": "convert_video_properties",
    "set_video_audio_track_sample_rate": "convert_video_properties",
    "set_video_audio_track_channels": "convert_video_properties",
    "convert_audio_format": "convert_audio_properties",
    "set_audio_bitrate": "convert_audio_properties",
    "set_audio_sample_rate": "convert_audio_properties",
    "set_audio_channels": "convert_audio_properties",
}


# ==========================================================================
# El predicado
# ==========================================================================

def _tipo(esq: dict) -> str:
    """El tipo comparable de una propiedad. `object` sin `type` cuenta como tal."""
    t = esq.get("type")
    if isinstance(t, list):
        return "|".join(sorted(str(x) for x in t))
    return str(t) if t else "?"


def normalizar(herr: list[dict]) -> dict:
    """`[{name, inputSchema}]` -> `{nombre: {"props": {p: tipo}, "req": set}}`."""
    out = {}
    for h in herr:
        esq = h.get("inputSchema") or {}
        props = {k: _tipo(v) for k, v in (esq.get("properties") or {}).items()}
        out[h["name"]] = {"props": props, "req": set(esq.get("required") or [])}
    return out


def subsume(a: dict, b: dict, exigir_rellenable: bool = True) -> tuple[bool, str]:
    """¿Toda llamada válida a `a` se puede expresar como una llamada a `b`?

    Tres condiciones, y la segunda es la que hace falta y nadie escribe:

    1. **`props(a) ⊆ props(b)`, con el mismo tipo.** Si `a` acepta algo que `b`
       no acepta, `a` no sobra.
    2. **`req(b) ⊆ props(a)`.** Si `b` exige un parámetro que `a` ni siquiera
       tiene, quien llame a `a` no sabe con qué rellenarlo: `b` no puede
       sustituir a `a`. Sin esta condición, una herramienta SIN parámetros
       (`health_check`) sale subsumida por todas, que es falso.
    3. **Estricto.** Con esquemas idénticos no hay «A sobra»: hay un empate, y
       la decisión es de otra clase.

    Devuelve `(veredicto, motivo)`. El motivo se guarda también cuando el
    veredicto es `False`: un «no» sin motivo no se puede auditar.
    """
    pa, pb = a["props"], b["props"]
    # 0. Una herramienta SIN parámetros no es un caso particular de nada: su
    # superficie de llamada no restringe la de nadie. Sin esta línea,
    # `health_check` sale subsumida por las 26 restantes de `video-audio-mcp`
    # —MEDIDO— y el generador de candidatas se vuelve inservible.
    if not pa:
        return False, "a_no_tiene_parametros"
    ajenas = sorted(set(pa) - set(pb))
    if ajenas:
        return False, "a_tiene_props_que_b_no: " + ",".join(ajenas)
    choque = sorted(k for k in pa if pa[k] != pb.get(k))
    if choque:
        return False, "tipos_incompatibles: " + ",".join(choque)
    huerfanos = sorted(b["req"] - set(pa))
    if huerfanos and exigir_rellenable:
        return False, "b_exige_lo_que_a_no_tiene: " + ",".join(huerfanos)
    if set(pa) == set(pb) and a["req"] == b["req"]:
        return False, "esquemas_identicos_no_es_estricto"
    return True, "props(a) subset props(b) y req(b) subset props(a)"


def parejas(cat: dict, exigir_rellenable: bool = True) -> list[dict]:
    """Todas las parejas ordenadas `(a, b)` con `a` subsumida por `b`."""
    out = []
    for na, a in cat.items():
        for nb, b in cat.items():
            if na == nb:
                continue
            ok, motivo = subsume(a, b, exigir_rellenable)
            if ok:
                out.append({"sobra": na, "cubierta_por": nb, "motivo": motivo})
    return out


def _saldo(cat: dict, exigir: bool) -> dict:
    """Qué atrapa y qué rompe una variante del predicado, sobre la referencia.

    Trampa 51: *antes de elegir un umbral, tabula qué atrapa y qué rompe en cada
    valor candidato*. Aquí el «umbral» es la condición 2 del predicado.
    """
    par = parejas(cat, exigir)
    hallado: dict[str, list[str]] = {}
    for p in par:
        hallado.setdefault(p["sobra"], []).append(p["cubierta_por"])
    aciertos = sorted(k for k, v in CONOCIDAS.items()
                      if k in hallado and v in hallado[k])
    return {
        "exigir_rellenable": exigir,
        "n_parejas": len(par),
        "n_herramientas_que_sobran": len(hallado),
        "aciertos_sobre_las_13": len(aciertos),
        "aciertos": aciertos,
        "escapadas": sorted(set(CONOCIDAS) - set(hallado)),
        # No declaradas por el informe: candidatas que hay que arbitrar a mano.
        # No son «falsos positivos» por definición —el informe no dice que NO
        # sobren— pero son el coste de auditoría que la variante impone.
        "no_declaradas": sorted(set(hallado) - set(CONOCIDAS)),
        "n_no_declaradas": len(set(hallado) - set(CONOCIDAS)),
    }


# ==========================================================================
# Extracción del catálogo de referencia (AST, no ejecución)
# ==========================================================================

#: FastMCP deriva el esquema de las anotaciones de tipo. Por eso el catálogo de
#: `video-audio-mcp` se puede reconstruir sin arrancarlo — cosa necesaria,
#: porque `.venv-mm-vamcp` se borró en la limpieza del 31/08 (`CLAUDE.md` §2).
_TIPOS = {"str": "string", "int": "integer", "float": "number",
          "bool": "boolean", "dict": "object", "list": "array",
          "list[str]": "array", "list[dict]": "array"}


def _anot(nodo) -> str:
    if nodo is None:
        return "?"
    try:
        s = ast.unparse(nodo)
    except Exception:                                        # pragma: no cover
        return "?"
    return _TIPOS.get(s, s)


def catalogo_fastmcp(ruta: str) -> list[dict]:
    """Las herramientas de un servidor FastMCP, por AST del fichero fuente."""
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    herr = []
    for n in ast.walk(arbol):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tool = False
        for d in n.decorator_list:
            f = d.func if isinstance(d, ast.Call) else d
            if isinstance(f, ast.Attribute) and f.attr == "tool":
                tool = True
        if not tool:
            continue
        args = n.args.args
        ndef = len(n.args.defaults)
        obliga = args[:len(args) - ndef] if ndef else args
        props = {a.arg: _anot(a.annotation) for a in args}
        herr.append({"name": n.name,
                     "inputSchema": {
                         "type": "object",
                         "properties": {k: {"type": v} for k, v in props.items()},
                         "required": [a.arg for a in obliga]}})
    return herr


# ==========================================================================

def main() -> int:
    r: dict = {"interprete": sys.version.split()[0]}

    # --- (1) El sujeto: el catálogo de FileX -------------------------------
    from filex import mcp as M
    from filex.nucleo import FileX
    herr = M.catalogo(FileX())
    if herr and not isinstance(herr[0], dict):
        herr = [h.model_dump(exclude_none=True, by_alias=True) for h in herr]
    cat_fx = normalizar(herr)
    par_fx = parejas(cat_fx)
    r["filex"] = {
        "n_herramientas": len(cat_fx),
        "herramientas": {k: {"props": sorted(v["props"]),
                             "req": sorted(v["req"])} for k, v in cat_fx.items()},
        "subsumidas": par_fx,
        "n_subsumidas": len(par_fx),
    }

    # --- (2) El control positivo: video-audio-mcp -------------------------
    if not os.path.exists(REF):
        r["referencia"] = {"error": "no está " + REF,
                           "nota": "repos/ está en .gitignore"}
    else:
        cat_ref = normalizar(catalogo_fastmcp(REF))
        par_ref = parejas(cat_ref)
        hallado = {p["sobra"]: p["cubierta_por"] for p in par_ref}
        aciertos = {k: v for k, v in CONOCIDAS.items() if hallado.get(k) == v}
        # Atrapada por el esquema, pero por OTRO subsumidor que el informe:
        otro = {k: hallado[k] for k in CONOCIDAS
                if k in hallado and hallado[k] != CONOCIDAS[k]}
        escapadas = sorted(set(CONOCIDAS) - set(hallado))
        extra = sorted(set(hallado) - set(CONOCIDAS))
        r["referencia"] = {
            "fichero": REF,
            "n_herramientas": len(cat_ref),
            "n_parejas_subsumidas": len(par_ref),
            "n_herramientas_que_sobran": len(hallado),
            "conocidas_del_informe": len(CONOCIDAS),
            "aciertos_mismo_subsumidor": sorted(aciertos),
            "n_aciertos": len(aciertos),
            "atrapadas_con_otro_subsumidor": otro,
            "escapadas": escapadas,
            "candidatas_no_declaradas_en_el_informe": extra,
            "parejas": par_ref,
            # Las dos variantes del predicado, tabuladas como pide la trampa 51.
            "variantes": [_saldo(cat_ref, True), _saldo(cat_ref, False)],
        }
        # Y la variante relajada sobre FileX: si también da 0, el 0 del sujeto
        # no depende de haber elegido el predicado más estricto.
        r["filex"]["subsumidas_relajado"] = parejas(cat_fx, False)
        r["filex"]["n_subsumidas_relajado"] = len(r["filex"]["subsumidas_relajado"])

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=2)

    print("FileX: %d herramientas, %d parejas subsumidas"
          % (r["filex"]["n_herramientas"], r["filex"]["n_subsumidas"]))
    if "error" not in r["referencia"]:
        d = r["referencia"]
        print("video-audio-mcp: %d herramientas, %d parejas, %d herramientas "
              "que sobran" % (d["n_herramientas"], d["n_parejas_subsumidas"],
                              d["n_herramientas_que_sobran"]))
        print("  aciertos sobre las 13 del informe: %d" % d["n_aciertos"])
        print("  con otro subsumidor: %s" % d["atrapadas_con_otro_subsumidor"])
        print("  escapadas: %s" % d["escapadas"])
        print("  no declaradas en el informe: %s"
              % d["candidatas_no_declaradas_en_el_informe"])
        print("  --- variantes del predicado ---")
        for v in d["variantes"]:
            print("  exigir_rellenable=%-5s parejas=%-3d sobran=%-3d "
                  "aciertos=%2d/13 escapadas=%2d no_declaradas=%d"
                  % (v["exigir_rellenable"], v["n_parejas"],
                     v["n_herramientas_que_sobran"], v["aciertos_sobre_las_13"],
                     len(v["escapadas"]), v["n_no_declaradas"]))
        print("  FileX con el predicado relajado: %d parejas"
              % r["filex"]["n_subsumidas_relajado"])
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
