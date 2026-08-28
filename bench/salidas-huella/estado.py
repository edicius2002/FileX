"""Estado del sondeo y del grafo. Se ejecuta ANTES y DESPUES del arreglo."""
import hashlib
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella, sondeo  # noqa: E402


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


d = sondeo.diagnostico()
print("== diagnostico() ==")
print(json.dumps(d, indent=1, ensure_ascii=False, default=str))

print("\n== huella almacenada vs calculada, por fichero ==")
dire = os.path.join(RAIZ, "filex", "sondeo")
for f in sorted(os.listdir(dire)):
    if not f.endswith(".json"):
        continue
    p = os.path.join(dire, f)
    with open(p, encoding="utf-8") as fh:
        j = json.load(fh)
    g = j.get("huella")
    nombre = j.get("motor") or f[:-5]
    a = huella.de_motor_por_nombre(nombre)
    print(f"{f:22s} sha256={sha(p)}  motor={nombre}")
    print(f"   guardada  {g}")
    print(f"   actual    {a}")
    print(f"   diferencias {huella.diferencias(g, a)}")

try:
    from filex.grafo import Grafo  # noqa: F401
except Exception as e:
    print("grafo:", e)
