# -*- coding: utf-8 -*-
"""C50 / worker10 - Genera el cuerpo del MANIFIESTO.md antes de podar las muestras.

Regla sec.6: borra los bytes, deja el `sha256`, el tamano y la orden que los
reproduce. Las 53 muestras son ~31 MB y son REGENERABLES (tres ordenes, 35 s), asi
que se podan; lo que se versiona es el `.json` con el `rc` de cada celda, que es la
medida.
"""
import os, json, hashlib

AQUI = os.path.dirname(os.path.abspath(__file__))
MUESTRAS = os.path.join(AQUI, "muestras")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    p1 = json.load(open(os.path.join(AQUI, "escritura_ff.json"), encoding="utf-8"))["res"]
    p2 = json.load(open(os.path.join(AQUI, "remedios_ff.json"), encoding="utf-8"))
    p3 = json.load(open(os.path.join(AQUI, "remedios2_ff.json"), encoding="utf-8"))
    lec = json.load(open(os.path.join(AQUI, "lectura.json"), encoding="utf-8"))["res"]

    filas = []
    for f in sorted(os.listdir(MUESTRAS)):
        tok = f[2:]
        ruta = os.path.join(MUESTRAS, f)
        if p3.get(tok, {}).get("materializado"):
            orden = " ".join(p3[tok]["celdas"][-1]["argv"])
            pasada = "3"
        elif p2.get(tok, {}).get("materializado"):
            orden = " ".join(p2[tok]["celdas"][-1]["argv"])
            pasada = "2"
        else:
            orden = " ".join(p1[tok]["celdas"][-1]["argv"])
            pasada = "1"
        filas.append({"fichero": f, "token": tok, "bytes": os.path.getsize(ruta),
                      "sha256": sha(ruta), "pasada": pasada, "orden": orden,
                      "lectura_nominal": lec[tok]["nominal"]["vivo"],
                      "lectura_forzada": lec[tok]["demuxer_forzado"]["vivo"],
                      "estado_grafoA": lec[tok]["estado_grafoA"]})
    json.dump({"n": len(filas), "bytes_totales": sum(f["bytes"] for f in filas),
               "filas": filas},
              open(os.path.join(AQUI, "muestras_manifiesto.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("| fichero | bytes | sha256 (12) | pasada | lectura nominal | estado |")
    print("|---|---:|---|:--:|:--:|---|")
    for f in filas:
        print("| `%s` | %d | `%s` | %s | %s | %s |"
              % (f["fichero"], f["bytes"], f["sha256"][:12], f["pasada"],
                 "sí" if f["lectura_nominal"] else "no", f["estado_grafoA"]))
    print("\n%d muestras, %d bytes" % (len(filas), sum(f["bytes"] for f in filas)))
