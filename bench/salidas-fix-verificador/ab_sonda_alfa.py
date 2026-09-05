"""A/B ancho: qué mueven los seis arreglos del CIERRE sobre ficheros reales.

Compara `sondear_en_proceso` y `alfa_minimo` del codigo de PARTIDA contra el de
ahora, sobre (a) todo `corpus/` y (b) las 53 salidas del patron oro, remapeadas
por nombre base desde `referencia.json` (trampa 89).

Las dos versiones corren en la MISMA tanda y sobre los MISMOS ficheros, y el
fuente de cada una se identifica por `sha256` (control de identidad, trampa
119). Lo que se publica es la lista de campos que cambian, no un total.

Uso:  python bench/salidas-fix-verificador/ab_sonda_alfa.py [<dir patron oro>]
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

BASE = "4333278"       # el commit del que parte este carril
REF = os.path.join(RAIZ, "bench", "salidas-referencia", "referencia.json")


def _cargar(commit=None):
    if not commit:
        from filex import verificador as V
        crudo = open(os.path.join(RAIZ, "filex", "verificador.py"), "rb").read()
        return V, hashlib.sha256(crudo).hexdigest()[:12]
    p = subprocess.run(["git", "show", "%s:filex/verificador.py" % commit],
                       cwd=RAIZ, capture_output=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(p.stderr.decode("utf-8", "replace"))
    d = tempfile.mkdtemp(prefix="fixverif-ab-")
    ruta = os.path.join(d, "vbase.py")
    with open(ruta, "wb") as f:
        f.write(p.stdout)
    spec = importlib.util.spec_from_file_location("vbase_ab", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(p.stdout).hexdigest()[:12]


def _mide(V, ruta):
    fuera = {}
    try:
        fuera["sonda"] = V.sondear_en_proceso(ruta)
    except Exception as e:                       # noqa: BLE001
        fuera["sonda"] = {"_excepcion": "%s: %s" % (type(e).__name__, e)}
    try:
        fuera["alfa"] = V.alfa_minimo(ruta)
    except Exception as e:                       # noqa: BLE001
        fuera["alfa"] = {"_excepcion": "%s: %s" % (type(e).__name__, e)}
    return fuera


def _dif(a, b, prefijo):
    fuera = []
    for k in sorted(set(a) | set(b)):
        va, vb = a.get(k, "<ausente>"), b.get(k, "<ausente>")
        if isinstance(va, float) and isinstance(vb, float):
            if abs(va - vb) < 1e-12:
                continue
        elif va == vb:
            continue
        if k in ("ms", "ms_sonda"):
            continue                              # tiempos: no son el sujeto
        fuera.append({"campo": prefijo + "." + k, "base": va, "ahora": vb})
    return fuera


def main() -> int:
    Vb, sha_b = _cargar(BASE)
    Va, sha_a = _cargar(None)
    if sha_b == sha_a:
        raise SystemExit("las dos versiones son la MISMA: el A/B no mide nada")

    ficheros = []
    for raiz, _, fs in os.walk(os.path.join(RAIZ, "corpus")):
        for f in fs:
            if not f.endswith((".txt", ".md")):
                ficheros.append(os.path.join(raiz, f))
    ref = json.load(open(REF, encoding="utf-8"))
    dir_oro = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(ref["salidas"][0]["ruta"]))
    n_oro = 0
    for s in ref["salidas"]:
        cand = None
        for raiz, _, fs in os.walk(dir_oro):
            if s["nombre"] in fs:
                cand = os.path.join(raiz, s["nombre"])
                break
        if cand:
            ficheros.append(cand)
            n_oro += 1

    filas = []
    for ruta in ficheros:
        b = _mide(Vb, ruta)
        a = _mide(Va, ruta)
        d = _dif(b["sonda"], a["sonda"], "sonda") + _dif(b["alfa"], a["alfa"],
                                                         "alfa")
        if d:
            filas.append({"ruta": os.path.relpath(ruta, RAIZ)
                          if ruta.startswith(RAIZ) else ruta,
                          "diferencias": d})

    r = {
        "base": BASE, "sha256_12_base": sha_b, "sha256_12_ahora": sha_a,
        "n_ficheros": len(ficheros),
        "n_del_patron_oro": n_oro,
        "n_salidas_del_patron_oro_declaradas": len(ref["salidas"]),
        "n_ficheros_que_cambian": len(filas),
        "cambios": filas,
    }
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "ab_sonda_alfa.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False, default=str)
    print("base=%s (%s)  ahora=%s" % (BASE, sha_b, sha_a))
    print("ficheros medidos     : %d  (patron oro: %d de %d)"
          % (len(ficheros), n_oro, len(ref["salidas"])))
    print("ficheros que cambian : %d" % len(filas))
    for f in filas:
        print("  %s" % f["ruta"])
        for d in f["diferencias"]:
            print("      %-28s %r -> %r" % (d["campo"], d["base"], d["ahora"]))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
