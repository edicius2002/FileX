"""A/B del CONTRATO ENTERO sobre las 39 ordenes del patron oro.

Complementa `ab_sonda_alfa.py`: alli se comparan las dos funciones publicas que
los seis arreglos tocan; aqui se ejecuta `verificar()` de las dos versiones —la
de partida y la de ahora— sobre las mismas (entrada, salida) y se comparan
veredicto, reglas y estado del punto 1.

Sin censo, el punto 5 sale no cubierto en las dos: es la misma limitacion en los
dos lados del A/B, asi que la DIFERENCIA sigue siendo valida (que es lo que se
publica). Las salidas se remapean por nombre base (trampa 89).
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

BASE = "4333278"
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
    ruta = os.path.join(tempfile.mkdtemp(prefix="fixverif-ct-"), "vbase.py")
    with open(ruta, "wb") as f:
        f.write(p.stdout)
    spec = importlib.util.spec_from_file_location("vbase_ct", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(p.stdout).hexdigest()[:12]


def _resumen(r):
    """Lo que se compara: el veredicto y las reglas, no los milisegundos."""
    return {
        "veredicto": r.get("veredicto"),
        "reglas": sorted((h.get("regla"), h.get("severidad"))
                         for h in (r.get("hallazgos") or [])),
        "punto1": (r.get("puntos") or {}).get("1_firma"),
        "punto1_estado": r.get("punto1_estado"),
    }


def main() -> int:
    Vb, sha_b = _cargar(BASE)
    Va, sha_a = _cargar(None)
    if sha_b == sha_a:
        raise SystemExit("las dos versiones son la MISMA: el A/B no mide nada")

    ref = json.load(open(REF, encoding="utf-8"))
    oro = os.path.dirname(os.path.dirname(ref["salidas"][0]["ruta"]))
    indice = {}
    for raiz, _, ff in os.walk(oro):
        for f in ff:
            indice.setdefault(f, os.path.join(raiz, f))

    filas, faltan = [], []
    for o in ref["ordenes"]:
        nombre = os.path.basename(o["salida"])
        sal = indice.get(nombre)
        ent = os.path.join(RAIZ, o["entrada"].replace("/", os.sep))
        if not sal or not os.path.exists(ent):
            faltan.append(o["id"])
            continue
        pedido = {"destino": os.path.splitext(nombre)[1].lstrip(".")}
        rb = _resumen(Vb.verificar(sal, pedido, ent, alfa=True))
        ra = _resumen(Va.verificar(sal, pedido, ent, alfa=True))
        filas.append({"id": o["id"], "salida": nombre, "base": rb, "ahora": ra,
                      "cambia": rb != ra})

    r = {"base": BASE, "sha256_12_base": sha_b, "sha256_12_ahora": sha_a,
         "n_ordenes": len(ref["ordenes"]), "n_evaluadas": len(filas),
         "faltan": faltan,
         "n_cambian": sum(f["cambia"] for f in filas),
         "cambian": [f for f in filas if f["cambia"]],
         "veredictos_ahora": {},
         "filas": filas}
    for f in filas:
        v = f["ahora"]["veredicto"]
        r["veredictos_ahora"][v] = r["veredictos_ahora"].get(v, 0) + 1
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "ab_contrato_oro.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False, default=str)
    print("base=%s (%s)  ahora=%s" % (BASE, sha_b, sha_a))
    print("evaluadas=%d  faltan=%s" % (len(filas), faltan))
    print("veredictos (ahora): %s" % r["veredictos_ahora"])
    print("cambian: %d  %s" % (r["n_cambian"], [f["id"] for f in r["cambian"]]))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
