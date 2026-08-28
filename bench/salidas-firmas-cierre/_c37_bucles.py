"""C37 / paso 5 - ¿HAY MAS TABLAS CON EL DEFECTO DE LA TRAMPA 48?

`EXT_FAMILIA` se poblaba con `for _n in ("csv json ..."):` SIN `.split()`, asi
que contenia los CARACTERES de la cadena, y nadie lo vio porque el recuento
cuadraba. La trampa 48 lo cerro para esa tabla; **nadie ha comprobado si hay
mas**. Aqui se comprueba, y sobre el AST (trampa 42: una prueba estructural que
busca TEXTO no distingue una llamada de una mencion).

Se marcan los `for` de nivel de modulo que iteran sobre:
  (a) una cadena literal pelada  -> recorre caracteres, casi seguro un defecto;
  (b) una tupla/lista cuyos elementos son cadenas con espacios y el bucle
      interior no las parte -> el mismo defecto un nivel mas adentro.

Uso:  python bench/salidas-firmas-cierre/_c37_bucles.py [fichero.py ...]
"""
import ast
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POR_DEFECTO = ["filex/verificador.py", "filex/formatos.py", "filex/motores.py",
               "filex/invocacion.py", "filex/motor_contenedor.py",
               "filex/huella.py", "filex/grafo.py", "filex/nucleo.py"]


def es_split(nodo):
    """True si el iterable ya se parte con .split()."""
    return (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in ("split", "splitlines"))


def literales(nodo):
    """Cadenas literales que hay dentro del iterable, sin bajar a llamadas."""
    out = []
    for n in ast.walk(nodo):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def funciones_que_parten(arbol):
    """Nombres de funciones del modulo que hacen `.split()` en su cuerpo.

    Sin esto el detector marca `EXT_A_FIRMAS`, que SI parte -- pero dentro del
    ayudante `_ext(nombres, firmas)`, no en el cuerpo del bucle. Un detector que
    no sigue un nivel de llamada acusa a la tabla buena y calla la mala.
    """
    out = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.FunctionDef) and any(
                es_split(c) for c in ast.walk(n) if isinstance(c, ast.Call)):
            out.add(n.name)
    return out


def revisa(ruta):
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read(), ruta)
    parten = funciones_que_parten(arbol)
    sospechas = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.For):
            continue
        it = nodo.iter
        if es_split(it):
            continue
        # (a) cadena literal pelada: `for x in ("a b c"):`  -> caracteres
        if isinstance(it, ast.Constant) and isinstance(it.value, str):
            sospechas.append({"linea": nodo.lineno, "clase": "cadena_pelada",
                              "muestra": it.value[:60]})
            continue
        # (b) tupla/lista de cadenas con espacios que el cuerpo no parte
        if isinstance(it, (ast.Tuple, ast.List)):
            cads = [c for c in literales(it) if " " in c and len(c) > 12]
            if not cads:
                continue
            parte = False
            for n in ast.walk(nodo):
                if not isinstance(n, ast.Call):
                    continue
                if es_split(n):
                    parte = True
                    break
                # un nivel de llamada: `_ext(nombres, firmas)` parte por dentro
                if isinstance(n.func, ast.Name) and n.func.id in parten:
                    parte = True
                    break
            if not parte:
                sospechas.append({"linea": nodo.lineno,
                                  "clase": "tupla_de_cadenas_sin_split",
                                  "muestra": cads[0][:60]})
    return sospechas


# CONTROL POSITIVO. Un «no detecta nada» no significa nada sin el (trampa 36):
# esta es la forma EXACTA que tenia `EXT_FAMILIA` hasta la trampa 48, y el
# detector tiene que marcarla. Si el control falla, el cero de arriba es mudo.
CONTROL = (
    "EXT_FAMILIA = set()\n"
    "for _n in (\"csv json yaml yml toml txt text md markdown tab tsv srt\"):\n"
    "    EXT_FAMILIA.add('.' + _n)\n"
)


def revisa_fuente(src):
    import tempfile
    d = tempfile.mkdtemp(prefix="f2-bucles-")
    p = os.path.join(d, "control.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(src)
    return revisa(p)


def main():
    ficheros = sys.argv[1:] or POR_DEFECTO
    res = {"_control_positivo": revisa_fuente(CONTROL)}
    for f in ficheros:
        p = os.path.join(RAIZ, f)
        if os.path.exists(p):
            res[f] = revisa(p)
    res["_total"] = sum(len(v) for k, v in res.items()
                        if k not in ("_total", "_control_positivo"))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
