"""H2 — cuántas aristas caduca este cambio, y de qué motores. NO se resondea.

`huella.py` hashea el AST de la CLASE del motor y sus bases, así que la
granularidad prometida es POR MOTOR. Aquí se comprueba que se cumple: tocar
`FFmpeg` no puede mover ni `ImageMagick` ni `Ghostscript` ni los de contenedor.
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import huella, motores, sondeo  # noqa: E402

out = {"motores": {}, "totales": {}}
tot_r = tot_n = tot_cad = 0
for cls in list(motores.MOTORES) + motores._descubrir():
    m = cls()
    d = sondeo.cargar(m.nombre)
    if not d:
        continue
    dif = huella.diferencias(d.get("huella", {}), huella.de_motor(m)) if d.get("huella") else ["sin_huella"]
    aristas = d.get("aristas", d.get("resultados", []))
    n = len(aristas) if isinstance(aristas, (list, dict)) else 0
    reales = sum(1 for a in (aristas.values() if isinstance(aristas, dict) else aristas)
                 if isinstance(a, dict) and a.get("estado") == "real")
    out["motores"][m.nombre] = {"componentes_caducados": dif,
                                "aristas_en_fichero": n, "reales": reales,
                                "caducan": n if dif else 0}
    tot_r += reales
    tot_n += n
    tot_cad += n if dif else 0
    print(f"{m.nombre:16s} caduca={dif!s:16s} aristas={n:4d} reales={reales:4d}")
out["totales"] = {"aristas_en_ficheros": tot_n, "reales": tot_r,
                  "caducadas_por_este_cambio": tot_cad}
print(f"\nTOTAL en ficheros de sondeo: {tot_n} ({tot_r} reales)")
print(f"CADUCADAS por este cambio:   {tot_cad}")
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "huella_impacto.json")
with open(salida, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("->", salida)
