#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sonda de VRAM: la recta `ordenada + pendiente x Mpx` de CADA motor, medida
IR DIRECTO (un proceso fresco por punto, trampa 67: llegar a un tamano en
escalera cuesta x2,25 mas que ir directo, asi que una serie medida dentro de
un solo proceso mide el camino, no el punto).

Por que hace falta y no se hereda: `bench/ocr-produccion-sidecar.md` §5.1
publica la recta de EasyOCR (641 + 1 080, r2=0,957), PaddleOCR (202 + 719) y
RapidOCR (643 + 109, tope 1 526). **Docling+RapidOCR con backend torch no
tiene recta publicada.** Prestarle la de EasyOCR como cota superior parecia
conservador y NO lo es en el sentido que importa: rechaza celdas que el motor
si puede servir, y por tanto RECORTA LA REJILLA que este informe viene a
extender -- que es exactamente el defecto que el informe denuncia, cometido
por el instrumento. Ademas la trampa 85 obliga a tabular el residuo de un
modelo heredado antes de presupuestar con el.

`coste` = VRAM libre TOTAL antes de importar el motor menos VRAM libre TOTAL
despues de procesar la pagina. Es una cota SUPERIOR del coste del motor (le
suma cualquier movimiento del escritorio durante la ventana), y es lo unico
observable: la VRAM por PID devuelve [N/A] en esta maquina (trampa 31).

uso: python sonda_vram_b26.py <easyocr|docling-r6> <doc> <factor>
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-k-borde-rejilla")
sys.path.insert(0, BASE)
sys.path.insert(0, ROOT)


def libre():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free",
                            "--format=csv,noheader,nounits"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20)
        return int(r.stdout.decode("utf-8", "replace").strip().splitlines()[0])
    except Exception:
        return -1


def main():
    config, doc, factor = sys.argv[1], sys.argv[2], float(sys.argv[3])
    import b26_borde as B
    from filex import gpu

    native = dict((d[0], d[1]) for d in B.DOCS)[doc]
    area = dict((d[0], d[2]) for d in B.DOCS)[doc]
    m = B.mpx(area, native, factor)
    ppp = int(round(native * factor))

    l0 = libre()
    out = {"config": config, "doc": doc, "factor": factor, "ppp": ppp,
           "mpx": round(m, 3), "libre_antes": l0}
    if l0 >= 0 and l0 < 6000:
        out["abortado"] = "GPU_GUARD: %d MiB libres < 6000" % l0
        print(json.dumps(out, ensure_ascii=False), flush=True)
        return

    with gpu.Lock("B26sonda-" + config) as lk:
        out["lock_aviso"] = lk.aviso
        t0 = time.perf_counter()
        leer, meta = B.build(config)
        l1 = libre()
        if config == "docling-r6":
            entrada = os.path.join(ROOT, "corpus", "pdf", doc + ".pdf")
        else:
            entrada, _ = B.raster(doc, factor, native, meta["declarado"])
        texto, rc = leer(entrada, ppp)
        l2 = libre()
        out.update({"libre_tras_construir": l1, "libre_tras_pagina": l2,
                    "coste_construir_mib": (l0 - l1) if l1 >= 0 else None,
                    "coste_total_mib": (l0 - l2) if l2 >= 0 else None,
                    "rc": rc, "bytes_texto": len(texto),
                    "segundos": round(time.perf_counter() - t0, 1)})
    print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
