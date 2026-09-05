"""Qué formas de `argv` cambian de veredicto con el arreglo de la forma corta.

    python bench/salidas-fix-superficies/argv.py

Mide **la detección, no la conversión**: qué `argv` sale de la reescritura y si
`parse_args` lo acepta. Así el alcance del cambio se publica entero —lo que
gana, lo que no cambia y lo que SIGUE roto— en vez de una lista de casos
felices.

El control positivo es el detector de ANTES, conservado a propósito (trampa
116): sin él, «el nuevo acepta estas ocho» no se distingue de un arnés que
acepta todo. Y el arnés declara `discrimina` sólo si el viejo y el nuevo
difieren en alguna fila.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import cli as _cli                      # noqa: E402


def _viejo(argv, _con_valor):
    """El detector de antes: filtra banderas y NO sus valores, y antepone
    `convertir` a todo el `argv`."""
    resto = [a for a in argv if not a.startswith("-")]
    if resto and resto[0] not in _cli._ORDENES and len(resto) == 2:
        return ["convertir", *argv]
    return list(argv)


def _nuevo(argv, con_valor):
    resto, primero = _cli._posicionales(argv, con_valor)
    if resto and resto[0] not in _cli._ORDENES and len(resto) == 2:
        return [*argv[:primero], "convertir", *argv[primero:]]
    return list(argv)


#: `a.png`/`b.webp` no se abren: `parse_args` no toca el disco.
CASOS = (
    ("forma corta desnuda", ["a.png", "b.webp"]),
    ("forma corta con --raiz", ["--raiz", "D", "a.png", "b.webp"]),
    ("forma corta con --raiz=D", ["--raiz=D", "a.png", "b.webp"]),
    ("forma corta con --params", ["a.png", "b.webp", "--params", "{}"]),
    ("forma corta con --json", ["a.png", "b.webp", "--json"]),
    ("forma corta con --timeout", ["a.png", "b.webp", "--timeout", "5"]),
    ("subcomando motores con --raiz", ["--raiz", "D", "motores"]),
    ("subcomando destinos con --raiz", ["--raiz", "D", "destinos", "png"]),
    ("subcomando plan con --raiz", ["--raiz", "D", "plan", "a.png", "b.webp"]),
    ("convertir explícito con --raiz", ["--raiz", "D", "convertir", "a.png", "b.webp"]),
    ("motores desnudo", ["motores"]),
    ("sin nada", []),
    ("un solo posicional", ["a.png"]),
    ("tres posicionales", ["a.png", "b.webp", "c.gif"]),
    ("--raiz DESPUÉS de los posicionales", ["a.png", "b.webp", "--raiz", "D"]),
)


def _analiza(argv):
    """¿`parse_args` lo acepta? Devuelve `(ok, orden)`; nunca imprime."""
    p = _cli.construir_parser()
    try:
        with contextlib.redirect_stderr(io.StringIO()), \
             contextlib.redirect_stdout(io.StringIO()):
            args = p.parse_args(argv)
    except SystemExit as e:
        return False, f"SystemExit({e.code})"
    return True, args.orden


def main() -> int:
    con_valor = _cli._banderas_con_valor(_cli.construir_parser())
    filas = []
    for etiqueta, argv in CASOS:
        v_argv = _viejo(argv, con_valor)
        n_argv = _nuevo(argv, con_valor)
        v_ok, v_orden = _analiza(v_argv)
        n_ok, n_orden = _analiza(n_argv)
        filas.append({
            "caso": etiqueta,
            "argv": argv,
            "viejo_reescribe_a": v_argv,
            "viejo": v_orden,
            "nuevo_reescribe_a": n_argv,
            "nuevo": n_orden,
            "cambia": (v_ok, v_orden) != (n_ok, n_orden),
            "gana": (not v_ok) and n_ok,
            "pierde": v_ok and not n_ok,
        })

    salida = {
        "banderas_con_valor": sorted(con_valor),
        "discrimina": any(f["cambia"] for f in filas),
        "ganan": [f["caso"] for f in filas if f["gana"]],
        "pierden": [f["caso"] for f in filas if f["pierde"]],
        "cambian_de_orden": [f["caso"] for f in filas
                             if f["cambia"] and not f["gana"] and not f["pierde"]],
        # OJO con el nombre: «rechazado» no es «roto». `["a.png"]` y los tres
        # posicionales NO son la forma corta —que es de exactamente dos— y su
        # `SystemExit(2)` es el error de USO correcto. La única LIMITACIÓN de
        # esta lista es `--raiz` detrás de los posicionales, y va aparte para
        # que nadie lea la etiqueta en vez del caso (trampa 44).
        "rechazados_en_los_dos": [f["caso"] for f in filas
                                  if f["viejo"] == f["nuevo"]
                                  and str(f["nuevo"]).startswith("SystemExit")],
        "limitacion_que_queda": [
            f["caso"] for f in filas
            if str(f["nuevo"]).startswith("SystemExit") and len(
                _cli._posicionales(f["argv"], con_valor)[0]) == 2],
        "filas": filas,
    }
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "argv.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in salida.items() if k != "filas"},
                     indent=1, ensure_ascii=False))
    return 0 if salida["discrimina"] and not salida["pierden"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
