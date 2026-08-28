"""Anade a los cinco ficheros de sondeo la nota de por que se reservaron.

`CLAUDE.md` trampa 44: *un campo honesto al lado de una nota falsa se lee como
una respuesta honesta*. La `nota_huella` que traian dice *«resondeado y sellado
el 2026-08-28»* y sigue siendo cierta —las medidas son de ese resondeo—, pero
ya no explica los valores que hay escritos: esos son de un ALGORITMO nuevo.
Sin esta linea, quien lea el fichero deducira que se resondeo otra vez.
"""
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(RAIZ, "filex", "sondeo")

NOTA = ("Resellado el 2026-08-28 por CAMBIO DE ALGORITMO de la huella, NO por "
        "resondeo: `filex/huella.py` pasa a hashear tambien las tablas de "
        "modulo que un bucle de nivel superior puebla y las constantes de "
        "modulo que las clases de motor leen (trampa 49). El codigo medido es "
        "el mismo: antes de resellar, las huellas de aqui coincidian con las "
        "del algoritmo anterior sobre este mismo arbol, y esa comprobacion es "
        "la que autoriza el resellado. Ver `bench/huella-y-tablas.md` sec.5 y "
        "`bench/salidas-huella/resellado.json`.")

for f in sorted(os.listdir(DIR)):
    if not f.endswith(".json"):
        continue
    p = os.path.join(DIR, f)
    with open(p, encoding="utf-8", newline="") as fh:
        texto = fh.read()
    if "nota_resellado" in texto:
        print(f, "ya tiene la nota")
        continue
    marca = '  "nota_huella": '
    i = texto.index(marca)
    linea = json.dumps({"nota_resellado": NOTA}, ensure_ascii=False)[1:-1]
    texto = texto[:i] + "  " + linea + ",\n" + texto[i:]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(texto)
    json.load(open(p, encoding="utf-8"))
    print(f, "nota anadida")
