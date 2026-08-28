"""Censo del cierre de llamadas de la huella: QUE entra hoy y que no.

No deduce nada del codigo: para cada nombre de nivel superior de
`verificador.py` MUTA su valor en el fuente y mira si `huella.de_alcance()`
se mueve. Una tabla que decide y no mueve la huella es un agujero MEDIDO.

Salida: bench/salidas-huella/censo_alcance.json
"""
from __future__ import annotations

import ast
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402

VERIF = os.path.join(RAIZ, "filex", "verificador.py")
TABLAS_49 = ["EXT_A_FIRMAS", "EXT_FAMILIA", "EXT_SIN_FIRMA", "FIRMAS",
             "MARCAS_FTYP", "EXT_TABULARES"]


def fuente() -> str:
    with open(VERIF, encoding="utf-8") as fh:
        return fh.read()


def clasifica(arbol: ast.Module) -> dict:
    """Nombres de nivel superior -> (clase de nodo, lineas)."""
    fuera = {}
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fuera[n.name] = ("funcion", n.end_lineno - n.lineno + 1)
        elif isinstance(n, ast.ClassDef):
            fuera[n.name] = ("clase", n.end_lineno - n.lineno + 1)
        elif isinstance(n, ast.Assign):
            for d in n.targets:
                if isinstance(d, ast.Name):
                    fuera[d.id] = ("asignacion", n.end_lineno - n.lineno + 1)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            fuera[n.target.id] = ("asignacion", n.end_lineno - n.lineno + 1)
    return fuera


def poblados_por_bucle(arbol: ast.Module) -> dict:
    """Nombres que un `for`/`if`/`while` de NIVEL SUPERIOR modifica.

    Son los que `_tabla()` registra con su nodo de asignacion INICIAL y cuyo
    contenido real vive fuera de ese nodo.
    """
    fuera: dict = {}
    for n in arbol.body:
        if not isinstance(n, (ast.For, ast.AsyncFor, ast.While, ast.If,
                              ast.With, ast.Try)):
            continue
        # Todo Name referenciado como objeto de un metodo mutador o como
        # destino de asignacion dentro del bloque.
        for m in ast.walk(n):
            if isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) \
                    and isinstance(m.func.value, ast.Name):
                fuera.setdefault(m.func.value.id, []).append(
                    f"{m.func.attr}() en linea {n.lineno}")
            if isinstance(m, ast.Subscript) and isinstance(m.value, ast.Name):
                fuera.setdefault(m.value.id, []).append(
                    f"subscript en linea {n.lineno}")
            if isinstance(m, ast.Delete):
                for t in m.targets:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                        fuera.setdefault(t.value.id, []).append(
                            f"del en linea {n.lineno}")
    return fuera


def muta_linea(src: str, linea: int, viejo: str, nuevo: str) -> str:
    """Sustituye en UNA linea (1-based). Devuelve '' si no encontro el texto."""
    ls = src.split("\n")
    if viejo not in ls[linea - 1]:
        return ""
    ls[linea - 1] = ls[linea - 1].replace(viejo, nuevo, 1)
    return "\n".join(ls)


def main() -> None:
    src = fuente()
    arbol = ast.parse(src)
    cls = clasifica(arbol)
    alcanzados = huella.nombres_alcanzados(src)
    bucles = poblados_por_bucle(arbol)
    base = huella.de_alcance(src)

    res = {
        "huella_base": base,
        "nombres_nivel_superior": len(cls),
        "en_cierre": len(alcanzados),
        "fuera_cierre": len(cls) - len([n for n in alcanzados if n in cls]),
        "constantes_en_cierre": sorted(
            n for n in alcanzados if cls.get(n, ("",))[0] == "asignacion"),
        "constantes_fuera_cierre": sorted(
            n for n, (k, _) in cls.items()
            if k == "asignacion" and n not in alcanzados),
        "poblados_por_bucle_nivel_superior": {
            k: v for k, v in sorted(bucles.items()) if k in cls},
        "tablas_49": {},
    }

    # --- la prueba que decide: mutar el CONTENIDO y ver si la huella se mueve
    mutaciones = {
        # nombre: (linea, texto viejo, texto nuevo, que se muta)
        "EXT_FAMILIA": (574, 'EXT_FAMILIA.add("." + _n)',
                        'EXT_FAMILIA.add(".ZZZ" + _n)', "el bucle que la puebla"),
        "EXT_A_FIRMAS": (556, "EXT_A_FIRMAS.update(_ext(_n, _f))",
                         "EXT_A_FIRMAS.update({}) or EXT_A_FIRMAS.update(_ext(_n, _f))",
                         "el bucle que la puebla"),
        "EXT_SIN_FIRMA": (615, 'EXT_SIN_FIRMA.setdefault("." + _e, _mot)',
                          'EXT_SIN_FIRMA.setdefault(".ZZZ" + _e, _mot)',
                          "el bucle que la puebla"),
    }
    for nombre, (ln, viejo, nuevo, que) in mutaciones.items():
        mutado = muta_linea(src, ln, viejo, nuevo)
        entrada = {"en_cierre": nombre in alcanzados,
                   "clase_nodo": cls.get(nombre, ("?", 0))[0],
                   "muta": que}
        if not mutado:
            entrada["error"] = f"texto no encontrado en linea {ln}"
        else:
            h = huella.de_alcance(mutado)
            entrada["huella_mutada"] = h
            entrada["caduca"] = h != base
        res["tablas_49"][nombre] = entrada

    # Tablas que son literales completos: se muta un elemento del literal.
    for nombre, ln, viejo, nuevo in [
            ("EXT_TABULARES", 1315, '".csv"', '".ZZZcsv"'),
            ("MARCAS_FTYP", 212, 'b"isom"', 'b"zzzm"'),
            ("FIRMAS", 80, "x89PNG", "x89ZZZ"),
    ]:
        mutado = muta_linea(src, ln, viejo, nuevo)
        entrada = {"en_cierre": nombre in alcanzados,
                   "clase_nodo": cls.get(nombre, ("?", 0))[0],
                   "muta": "un elemento del literal"}
        if not mutado:
            entrada["error"] = f"texto no encontrado en linea {ln}"
        else:
            h = huella.de_alcance(mutado)
            entrada["huella_mutada"] = h
            entrada["caduca"] = h != base
        res["tablas_49"][nombre] = entrada

    # Control positivo: mutar una funcion que SI esta en el cierre.
    for nombre in ("punto1_estado", "verificar"):
        if nombre in cls:
            nodo = next(n for n in arbol.body
                        if isinstance(n, ast.FunctionDef) and n.name == nombre)
            mutado = muta_linea(src, nodo.end_lineno, "    ", "    x_zzz = 1\n    ")
            if mutado:
                res.setdefault("control", {})[nombre] = {
                    "en_cierre": nombre in alcanzados,
                    "caduca": huella.de_alcance(mutado) != base}

    # --- control de RUIDO: lo que NO debe caducar nunca (deuda-sondeo sec.2.5)
    ruido = {}
    # a) un comentario nuevo
    ls = src.split("\n")
    ruido["comentario_nuevo"] = {
        "caduca": huella.de_alcance("\n".join(
            ls[:100] + ["# comentario de prueba, no cambia nada"] + ls[100:]))
        != base}
    # b) tocar `fidelidad_audio`, que esta FUERA del cierre
    nodo = next((n for n in arbol.body if isinstance(n, ast.FunctionDef)
                 and n.name == "fidelidad_audio"), None)
    if nodo is not None:
        c = list(ls)
        c.insert(nodo.lineno, "    x_zzz_no_usada = 1")
        ruido["tocar_fidelidad_audio"] = {
            "en_cierre": "fidelidad_audio" in alcanzados,
            "caduca": huella.de_alcance("\n".join(c)) != base}
    # c) el sha256 CRUDO del fichero, para tener el contraste de la tabla
    import hashlib
    ruido["sha256_crudo_base"] = hashlib.sha256(
        src.encode("utf-8")).hexdigest()[:16]
    res["control_ruido"] = ruido

    sal = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "censo_alcance.json")
    with open(sal, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
