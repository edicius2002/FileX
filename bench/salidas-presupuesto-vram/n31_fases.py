# -*- coding: utf-8 -*-
"""N31 -- conductor: toma el lock de GPU UNA vez para toda la tanda (cabe en
un turno: 2 imagenes x 3 repeticiones, cada una un proceso fresco de
`n31_fases_child.py`) y lanza el proceso HIJO reiniciado en cada repeticion
(trampas 67/100: el asignador no libera memoria, asi que cada medida de "coste
de tocar esta imagen por primera vez" tiene que partir de un proceso limpio).

uso: python n31_fases.py
"""
import json
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: E402

PY = r"D:\Work\research\FileX\.venv-ai\Scripts\python.exe"
IMG = os.path.join(AQUI, "img")
JS = os.path.join(AQUI, "json")
os.makedirs(JS, exist_ok=True)

CASOS = [("escaneado_d4_r200.png", "sin_recorte_2.221Mpx"),
         ("escaneado_d4_r280.png", "recortado_4.352Mpx"),
         ("escaneado_d4_r400.png", "recortado_8.882Mpx")]
REPS = 3


def main():
    with gpu.Lock("N31-fases") as lk:
        todas = []
        for nombre, etiqueta in CASOS:
            for i in range(REPS):
                ruta_img = os.path.join(IMG, nombre)
                ruta_out = os.path.join(AQUI, f"_tmp_{etiqueta}_{i}.json")
                t0 = time.time()
                p = subprocess.run([PY, os.path.join(AQUI, "n31_fases_child.py"),
                                    ruta_img, ruta_out],
                                   stdin=subprocess.DEVNULL, capture_output=True,
                                   text=True, timeout=120)
                seg = round(time.time() - t0, 1)
                if p.returncode != 0 or not os.path.exists(ruta_out):
                    print(f"[FALLO] {etiqueta} rep{i} rc={p.returncode} "
                          f"stderr={p.stderr[-500:]}")
                    todas.append({"etiqueta": etiqueta, "rep": i, "rc": p.returncode,
                                  "error": p.stderr[-500:]})
                    continue
                r = json.load(open(ruta_out, encoding="utf-8"))
                r["etiqueta"] = etiqueta
                r["rep"] = i
                r["segundos_proceso"] = seg
                todas.append(r)
                os.remove(ruta_out)
                print(f"{etiqueta} rep{i} ({seg}s, {r['n_boxes']} cajas): " +
                      " ".join(f"{f['fase']}={f['vram_mib']}" for f in r["fases"]))

    json.dump(todas, open(os.path.join(JS, "n31_fases.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
    print(f"\n-> {JS}/n31_fases.json ({len(todas)} corridas)")


if __name__ == "__main__":
    main()
