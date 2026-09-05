"""Delta de cobertura del carril de fidelidad, POR NOMBRE DE FUNCION.

Cruza la cobertura BASE (la que el maestro midio sobre `main` con la suite de
517 pruebas) con la que produce `pruebas/test_cob_fidelidad.py` por si solo.

**Por que por nombre y no por numero de linea, que es como estaba escrito
primero.** El arreglo de §5.1 mete 54 lineas en mitad del fichero, asi que la
linea 4826 de `main` y la 4826 de ahora NO son la misma sentencia. La primera
version de este script mapeaba las lineas ausentes de la BASE sobre los rangos
de funcion del fichero ACTUAL y publico `209 de 299`, que no era una regresion:
era el desfase. Es la trampa 62 en otro eje --preguntale a tu instrumento su
resolucion-- y la 59 en el suyo: **cuando compares dos versiones, no supongas
que sus coordenadas son las mismas**.

Cada lado usa el AST de SU PROPIA fuente:

* la base, la que devuelve `git show <ref>:filex/verificador.py`;
* la nueva, el fichero del arbol de trabajo.

Uso:
  python bench/salidas-cobertura-fidelidad/delta.py base.json nueva.json \\
         [--ref REF] [salida.json]
"""
import ast
import json
import os
import subprocess
import sys

MIAS = ("_num", "svg_textos", "png_tinta_cajas", "fidelidad_imagen",
        "fidelidad_video", "fidelidad_pdf", "fidelidad_vectorial")
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cobertura(ruta):
    d = json.load(open(ruta, encoding="utf-8"))
    k = [x for x in d["files"] if x.replace("\\", "/").endswith(
        "filex/verificador.py")][0]
    v = d["files"][k]
    return set(v["missing_lines"]), set(v.get("executed_lines", [])), v["summary"]


def _rangos(fuente):
    arbol = ast.parse(fuente)
    fuera = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name in MIAS:
            fuera[nodo.name] = set(range(nodo.lineno, nodo.end_lineno + 1))
    return fuera


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ref = "main"
    for i, a in enumerate(sys.argv):
        if a == "--ref":
            ref = sys.argv[i + 1]
    falt_base, _, res_base = _cobertura(args[0])
    falt_nueva, ejec_nueva, res_nueva = _cobertura(args[1])

    p = subprocess.run(["git", "show", "%s:filex/verificador.py" % ref],
                       cwd=RAIZ, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")[:300]
    rangos_base = _rangos(p.stdout.decode("utf-8"))
    with open(os.path.join(RAIZ, "filex", "verificador.py"), encoding="utf-8") as fh:
        rangos_ahora = _rangos(fh.read())
    # Control de identidad del instrumento: los dos lados tienen que traer las
    # siete funciones, o el mapeo por nombre esta mirando otra cosa.
    assert set(rangos_base) == set(MIAS), sorted(rangos_base)
    assert set(rangos_ahora) == set(MIAS), sorted(rangos_ahora)

    filas = []
    tot_antes = tot_quedan = 0
    for nombre in MIAS:
        antes = len(falt_base & rangos_base[nombre])
        quedan = sorted(falt_nueva & rangos_ahora[nombre])
        filas.append({"funcion": nombre,
                      "sin_ejecutar_en_la_base": antes,
                      "sin_ejecutar_ahora": len(quedan),
                      "lineas_que_quedan": quedan})
        tot_antes += antes
        tot_quedan += len(quedan)
        print("%-22s base %3d sin ejecutar -> ahora %3d  %s"
              % (nombre, antes, len(quedan), quedan[:8] if quedan else ""))
    print("-" * 72)
    print("TOTAL carril: %d sin ejecutar en la base -> %d ahora  (ganadas %d)"
          % (tot_antes, tot_quedan, tot_antes - tot_quedan))
    res = {"ref_base": ref, "por_funcion": filas,
           "sin_ejecutar_en_la_base": tot_antes,
           "sin_ejecutar_ahora": tot_quedan,
           "ganadas": tot_antes - tot_quedan,
           "resumen_base": res_base, "resumen_modulo_solo": res_nueva}
    if len(args) > 2:
        with open(args[2], "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
