"""Control: el arreglo 7 (V5) NO mueve la huella `contrato`, y los otros seis SI.

No se deduce de «fidelidad_video no esta en el cierre»: se MIDE, aplicando cada
mitad por separado sobre la fuente de PARTIDA (`git show <base>:filex/...`) y
calculando `huella.de_alcance` de las tres variantes.

Uso:  python bench/salidas-fix-verificador/control_huella_v5.py <commit-base>
"""

import ast
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402

# Las dos piezas del arreglo 7, tal y como quedan en el fichero de ahora.
V5_VIEJO = """                perdidas = []
                for i, x in enumerate(te):
                    if not (x["language"] or x["title"]):
                        continue
                    y = ts[i] if i < len(ts) else None"""


def _fuente(commit: str) -> str:
    p = subprocess.run(["git", "show", "%s:filex/verificador.py" % commit],
                       cwd=RAIZ, capture_output=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(p.stderr.decode("utf-8", "replace"))
    return p.stdout.decode("utf-8")


def main() -> int:
    base_commit = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    base = _fuente(base_commit)
    ahora = open(os.path.join(RAIZ, "filex", "verificador.py"),
                 encoding="utf-8").read()

    # (a) la fuente de partida + SOLO el arreglo 7. Se transplanta el bloque de
    #     V5 y la funcion nueva desde la fuente de ahora.
    arbol = ast.parse(ahora)
    nueva = next(n for n in arbol.body
                 if isinstance(n, ast.FunctionDef)
                 and n.name == "_emparejar_por_tipo")
    texto_nueva = ast.get_source_segment(ahora, nueva)
    v5_nuevo = """                perdidas = []
                parejas = _emparejar_por_tipo(te, ts)
                for i, x in enumerate(te):
                    if not (x["language"] or x["title"]):
                        continue
                    y = parejas[i]"""
    if V5_VIEJO not in base:
        raise SystemExit("el bloque V5 viejo no esta en la fuente de partida")
    solo_v5 = base.replace(V5_VIEJO, v5_nuevo)
    solo_v5 = solo_v5.replace("def _ffmpeg_psnr(salida: str, entrada: str):",
                              texto_nueva + "\n\n\ndef _ffmpeg_psnr(salida: str, entrada: str):",
                              1)
    # control de identidad (trampa 119): las tres fuentes son DISTINTAS
    assert base != solo_v5 != ahora and base != ahora

    r = {
        "base": huella.de_alcance(base),
        "base_mas_solo_el_arreglo_7": huella.de_alcance(solo_v5),
        "con_los_siete": huella.de_alcance(ahora),
        "interprete": huella.interprete_actual(),
        "commit_base": base_commit,
    }
    r["el_arreglo_7_mueve_la_huella"] = (
        r["base"] != r["base_mas_solo_el_arreglo_7"])
    r["los_otros_seis_mueven_la_huella"] = (
        r["base_mas_solo_el_arreglo_7"] != r["con_los_siete"])
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "control_huella_v5.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(json.dumps(r, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
