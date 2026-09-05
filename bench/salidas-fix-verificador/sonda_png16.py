"""Demuestra que las DOS vias de `_alfa_min_png` coinciden entre si y con el
oraculo, sobre un barrido de alfas de 16 bits que cruza el umbral 0xFF00.

El defecto 1 era una asimetria entre dos caminos del mismo modulo: la rama
Adam7 veia el alfa y la no entrelazada lo daba por opaco. El arreglo no inventa
una tercera semantica: hace que la no entrelazada coincida con la que ya
acertaba. Esto lo mide, con el oraculo del fixture (`F.referencia`) de arbitro.

Uso:
  python bench/salidas-fix-verificador/sonda_png16.py            # el codigo de ahora
  python bench/salidas-fix-verificador/sonda_png16.py <commit>   # el de ese commit

La segunda forma es el CONTROL: la misma sonda contra el codigo de partida, que
es lo unico que separa «mi arreglo cierra las discrepancias» de «esta sonda no
dispara» (trampa 119: se interroga al SUJETO, no al mandato que lo cambia).
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "pruebas"))

import fixtures_cob_png as F        # noqa: E402


def _modulo(commit=None):
    """Devuelve el modulo `verificador` de ahora o el de un commit."""
    if not commit:
        from filex import verificador as V
        return V, hashlib.sha256(
            open(os.path.join(RAIZ, "filex", "verificador.py"), "rb").read()
        ).hexdigest()[:12]
    p = subprocess.run(["git", "show", "%s:filex/verificador.py" % commit],
                       cwd=RAIZ, capture_output=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(p.stderr.decode("utf-8", "replace"))
    tmp = os.path.join(tempfile.mkdtemp(prefix="fixverif-base-"), "vbase.py")
    with open(tmp, "wb") as f:
        f.write(p.stdout)
    spec = importlib.util.spec_from_file_location("vbase", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(p.stdout).hexdigest()[:12]

# Barrido que cruza el umbral: por debajo de 0xFF00 el codigo viejo ya acertaba;
# de 0xFF00 (65280) hacia arriba es donde se perdia el alfa.
ALFAS = ([0, 1, 128, 1000, 32767, 60000, 65000, 65278, 65279]
         + list(range(65280, 65536, 17)) + [65534])
FILTROS = (0, 1, 2, 3, 4)


def main() -> int:
    commit = sys.argv[1] if len(sys.argv) > 1 else None
    V, sha = _modulo(commit)
    tmp = tempfile.mkdtemp(prefix="fixverif-png16-")
    filas = []
    for alfa in ALFAS:
        px = F.rgba_con_hueco(6, 4, 3, 2, alfa, bd=16)
        datos_p = F.png(px, 6, 16, filtros=FILTROS)
        datos_e = F.png(px, 6, 16, entrelazado=1, filtros=FILTROS)
        p = os.path.join(tmp, "p%d.png" % alfa)
        e = os.path.join(tmp, "e%d.png" % alfa)
        open(p, "wb").write(datos_p)
        open(e, "wb").write(datos_e)
        ora = F.referencia(datos_p)["alfa_min"]
        a = V.alfa_minimo(p, "png", exacto=True)
        b = V.alfa_minimo(e, "png", exacto=True)
        filas.append({
            "alfa": alfa,
            "oraculo": ora,
            "plano": a["alfa_min"],
            "entrelazado": b["alfa_min"],
            "plano_exacto": a["exacto"],
            "plano_primer": tuple(a["primer_transparente"] or ()),
            "entrelazado_primer": tuple(b["primer_transparente"] or ()),
            "coincide_plano": abs(a["alfa_min"] - ora) < 1e-12,
            "coincide_entrelazado": abs(b["alfa_min"] - ora) < 1e-12,
            "las_dos_vias_coinciden": a["alfa_min"] == b["alfa_min"],
        })
    r = {
        "sujeto": commit or "arbol de trabajo",
        "sha256_12_del_fuente": sha,     # control de identidad (trampa 119)
        "n": len(filas),
        "n_plano_coincide_con_el_oraculo": sum(f["coincide_plano"] for f in filas),
        "n_entrelazado_coincide_con_el_oraculo":
            sum(f["coincide_entrelazado"] for f in filas),
        "n_las_dos_vias_coinciden": sum(f["las_dos_vias_coinciden"] for f in filas),
        "n_plano_exacto": sum(f["plano_exacto"] for f in filas),
        "n_primer_transparente_igual":
            sum(f["plano_primer"] == f["entrelazado_primer"] for f in filas),
        "discrepancias": [f for f in filas if not f["coincide_plano"]],
        "filas": filas,
    }
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sonda_png16%s.json" % ("_base" if commit else ""))
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False, default=list)
    print("sujeto: %s  sha256[:12]=%s" % (r["sujeto"], sha))
    for k in ("n", "n_plano_coincide_con_el_oraculo",
              "n_entrelazado_coincide_con_el_oraculo",
              "n_las_dos_vias_coinciden", "n_plano_exacto",
              "n_primer_transparente_igual"):
        print("%-40s %s" % (k, r[k]))
    print("discrepancias: %d" % len(r["discrepancias"]))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
