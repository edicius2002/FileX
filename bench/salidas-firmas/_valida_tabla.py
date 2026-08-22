# -*- coding: utf-8 -*-
"""F1 / paso 4b - ¿LA TABLA NUEVA MARCA COMO FALLO ALGO QUE ESTA BIEN?

Las 53 del patron oro son un liston imprescindible pero corto: solo tocan 17
extensiones. La tabla nueva tiene 340. Aqui se escribe CADA formato de salida que
los motores locales saben escribir, con la invocacion de ConvertX, y se pasa el
punto 1 del contrato sobre la salida. Todo lo que salga `fallo` es un candidato a
FALSO POSITIVO y hay que mirarlo uno a uno: o el motor entrego otro formato (y es
un acierto) o la tabla se equivoca (y hay que quitar la entrada).

Uso: python _valida_tabla.py
Escribe valida_tabla.json
"""
import os, sys, json, time, shutil, subprocess
from collections import Counter

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
BASE = os.environ.get("F1_TMP") or os.path.join(os.environ.get("TEMP", "."), "f1")
TMP = os.path.join(BASE, "val")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, SAL)
import verificador as V
from _censo_firmas import semillas, escribe, limpia


def main():
    F = json.load(open(os.path.join(SAL, "formatos.json"), encoding="utf-8"))
    pa = F["por_adaptador"]
    sem = semillas()
    trabajos = ([("ffmpeg", b, ["video", "audio", "imagen", "subtitulo"])
                 for b in sorted(set(pa["ffmpeg"]["to"]))] +
                [("imagemagick", b, ["imagen"])
                 for b in sorted(set(pa["imagemagick"]["to"]))])
    limpia(TMP)
    res = []
    t0 = time.time()
    for k, (motor, b, mods) in enumerate(trabajos):
        hecho = False
        for mod in mods:
            sub = os.path.join(TMP, "w")
            limpia(sub)
            sal = os.path.join(sub, "v%d.%s" % (k, b))
            ent = sem[mod][0]
            rc, err, tam, cab = escribe(motor, ent, b, sal, sub)
            if rc != 0 or not cab:
                continue
            reales = [f for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f))]
            real = os.path.join(sub, sorted(reales)[0])
            son = {}
            try:
                son = V.sondear(real, "proceso")
            except Exception as e:
                son = {"firma": V.firma_real(real), "bytes": tam, "error": str(e)[:100]}
            son_ent = {"ruta": ent, "firma": V.firma_real(ent)}
            h = V.punto1_firma(real, son, {"destino": b, "rc": 0}, son_ent)
            res.append({"motor": motor, "formato": b, "modalidad": mod,
                        "firma": V.firma_real(real),
                        "aceptables": sorted(V.EXT_A_FIRMAS.get(
                            os.path.splitext("x." + b)[1].lower(), [])),
                        "estado": V.punto1_estado(real),
                        "sev": [x["severidad"] for x in h],
                        "reglas": [x["regla"] for x in h],
                        "msg": [x["mensaje"][:110] for x in h]})
            hecho = True
            break
        if not hecho:
            res.append({"motor": motor, "formato": b, "estado": "no_escribible"})
        if k % 40 == 0:
            print("   %d/%d (%.0fs)" % (k, len(trabajos), time.time() - t0), flush=True)
    limpia(TMP)

    esc = [r for r in res if r.get("estado") != "no_escribible"]
    fallos = [r for r in esc if "fallo" in r.get("sev", [])]
    avisos = [r for r in esc if "aviso" in r.get("sev", [])]
    print("\nescritos %d de %d" % (len(esc), len(res)))
    print("estados :", dict(Counter(r["estado"] for r in esc)))
    print("\nFALLOS del punto 1 sobre salidas legitimas: %d" % len(fallos))
    for r in fallos:
        print("   %-14s %-13s firma=%-12s espera=%s" % (r["motor"], r["formato"],
                                                        r["firma"], r["aceptables"][:6]))
    print("\nAVISOS G6 (la salida tiene la firma de la entrada): %d" % len(avisos))
    for r in avisos:
        print("   %-14s %-13s firma=%-12s %s" % (r["motor"], r["formato"], r["firma"],
                                                 r["reglas"]))
    json.dump(res, open(os.path.join(SAL, "valida_tabla.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    print("\nescrito valida_tabla.json")


if __name__ == "__main__":
    main()
