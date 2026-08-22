#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""¿Discriminan V2 y V5, o solo salen 'informativo'?

Sobre las 53 salidas del patron oro las dos reglas dicen siempre que todo esta
bien, y eso no demuestra que sirvan: puede que no sepan fallar. Aqui se
fabrican los dos fallos que cada regla debe atrapar, y su control.

V5: patologico_2pistas.mkv NO trae etiquetas (lo dice la nota de la propia
    regla en referencia.json), asi que primero hay que ponerselas.
V2: se pide un remux normal y se entrega un video truncado, que es el fallo
    real de un motor que se queda sin espacio o sin tiempo.

Salidas en tmp/, que se borran al terminar.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
import verificador as V                                     # noqa: E402

MKV = os.path.join(RAIZ, "corpus", "video", "patologico_2pistas.mkv")


def ff(args, timeout=300):
    return subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error"] + args,
                          capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def main():
    tmp = tempfile.mkdtemp(prefix="filex_v2v5_")
    res = []
    try:
        etiquetado = os.path.join(tmp, "etiquetado.mkv")
        ff(["-i", MKV, "-map", "0", "-c", "copy",
            "-metadata:s:a:0", "language=spa", "-metadata:s:a:0", "title=Castellano",
            "-metadata:s:a:1", "language=eng", "-metadata:s:a:1", "title=English",
            "-metadata:s:v:0", "language=und", etiquetado])

        casos = []
        # --- V5 ---
        bien = os.path.join(tmp, "v5_bien.mkv")
        ff(["-i", etiquetado, "-map", "0", "-c", "copy", bien])
        casos.append(("V5 control: remux que conserva las etiquetas", bien,
                      etiquetado, {"destino": "mkv", "params": {"copia": True}},
                      "sin aviso"))
        mal = os.path.join(tmp, "v5_mal.mkv")
        ff(["-i", etiquetado, "-map", "0", "-c", "copy", "-map_metadata", "-1",
            "-map_metadata:s:a", "-1", "-map_metadata:s:v", "-1", mal])
        casos.append(("V5 fallo: remux que PIERDE las etiquetas", mal,
                      etiquetado, {"destino": "mkv", "params": {"copia": True}},
                      "aviso"))
        # --- V2 ---
        v2b = os.path.join(tmp, "v2_bien.mp4")
        ff(["-i", MKV, "-map", "0:v:0", "-c", "copy", v2b])
        casos.append(("V2 control: remux con todos los fotogramas", v2b, MKV,
                      {"destino": "mp4", "params": {"copia": True}}, "sin fallo"))
        v2m = os.path.join(tmp, "v2_mal.mp4")
        ff(["-i", MKV, "-map", "0:v:0", "-frames:v", "150", "-c", "copy", v2m])
        casos.append(("V2 fallo: entrega la mitad de los fotogramas", v2m, MKV,
                      {"destino": "mp4", "params": {"copia": True}}, "fallo"))
        v2f = os.path.join(tmp, "v2_fps.mp4")
        ff(["-i", MKV, "-map", "0:v:0", "-r", "15", v2f])
        casos.append(("V2 excepcion: se PIDIO cambiar el fps (no debe fallar)",
                      v2f, MKV, {"destino": "mp4", "params": {"fps": 15}},
                      "sin fallo"))

        for nombre, sal, ent, ped, esperado in casos:
            r = V.verificar_fidelidad(sal, ped, ent)
            hs = [h for h in r["hallazgos"] if h["regla"] in ("V2", "V5")]
            sev = {h["regla"]: h["severidad"] for h in hs}
            fila = {"caso": nombre, "esperado": esperado,
                    "veredicto": r["veredicto"], "severidades": sev,
                    "bytes": os.path.getsize(sal) if os.path.exists(sal) else 0,
                    "hallazgos": [{"regla": h["regla"], "severidad": h["severidad"],
                                   "mensaje": h["mensaje"][:180]} for h in hs]}
            res.append(fila)
            print("%-52s -> %-11s %s" % (nombre[:52], r["veredicto"], sev))
            for h in hs:
                print("      [%s %s] %s" % (h["regla"], h["severidad"],
                                            h["mensaje"][:130]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(AQUI, "discriminacion_v2_v5.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("-> discriminacion_v2_v5.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
