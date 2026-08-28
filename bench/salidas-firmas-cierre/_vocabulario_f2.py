"""F2 - El vocabulario despues del cierre, con TAMANO Y ELEMENTOS.

La trampa 48 pide exactamente esto: *«cuando publiques el tamano de una tabla,
publica tambien dos elementos de ella»*. `firmas-contrato.md` §4 publico
«EXT_FAMILIA: 28 extensiones» y la tabla contenia 28 CARACTERES.

Uso:  python bench/salidas-firmas-cierre/_vocabulario_f2.py
"""
import json
import os
import subprocess
import sys
import tempfile
import importlib.util

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)


def head():
    tmp = os.path.join(tempfile.gettempdir(), "f2_verificador_head.py")
    r = subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                       capture_output=True, cwd=RAIZ, timeout=60,
                       stdin=subprocess.DEVNULL)
    with open(tmp, "wb") as fh:
        fh.write(r.stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def foto(V):
    nombres = ({x[2] for x in V.FIRMAS} | set(V.MARCAS_FTYP.values())
               | {x[1] for x in V.MARCAS_TEXTO} | set(V.MIME_ZIP.values())
               | {x[1] for x in V.OOXML}
               | {x[2] for x in getattr(V, "FIRMAS_LARGAS", [])})
    return {
        "FIRMAS__n": len(V.FIRMAS),
        "FIRMAS__dos": [(d, m.decode("latin-1", "replace"), n)
                        for d, m, n in V.FIRMAS[:1] + V.FIRMAS[-1:]],
        "FIRMAS_LARGAS__n": len(getattr(V, "FIRMAS_LARGAS", [])),
        "FIRMAS_LARGAS__todas": [(d, m.decode("latin-1", "replace"), n)
                                 for d, m, n in getattr(V, "FIRMAS_LARGAS", [])],
        "MARCAS_FTYP__n": len(V.MARCAS_FTYP),
        "MARCAS_TEXTO__n": len(V.MARCAS_TEXTO),
        "EXT_A_FIRMAS__n": len(V.EXT_A_FIRMAS),
        "EXT_A_FIRMAS__dos": {k: sorted(V.EXT_A_FIRMAS[k])
                              for k in sorted(V.EXT_A_FIRMAS)[:2]},
        "EXT_SIN_FIRMA__n": len(V.EXT_SIN_FIRMA),
        "EXT_SIN_FIRMA__dos": {k: V.EXT_SIN_FIRMA[k][:60]
                               for k in sorted(V.EXT_SIN_FIRMA)[:2]},
        "EXT_FAMILIA__n": len(V.EXT_FAMILIA),
        "EXT_FAMILIA__dos": sorted(V.EXT_FAMILIA)[:2],
        "nombres_de_firma__n": len(nombres),
    }


def main():
    from filex import verificador as V
    a, b = foto(head()), foto(V)
    print(json.dumps({"antes_HEAD": a, "despues_F2": b,
                      "delta": {k: (b[k] - a[k]) for k in a
                                if k.endswith("__n")}},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
