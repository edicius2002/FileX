#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Las tres conversiones de datos del patron oro, reimplementadas literalmente.

referencia.json las describe en prosa ("csv.reader sobre utf-8-sig; json.dump
con ensure_ascii=False") en lugar de dar una orden ejecutable, porque el motor
es Python. Se reproducen aqui para poder cronometrarlas igual que las demas.
"""
import csv
import json
import sys

oid, entrada, salida = sys.argv[1], sys.argv[2], sys.argv[3]

if oid == "dat.csv2json":
    with open(entrada, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.reader(fh))
    cab, cuerpo = filas[0], filas[1:]
    obj = [dict(zip(cab, f)) for f in cuerpo]
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
elif oid == "dat.csv2csv":
    with open(entrada, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.reader(fh))
    with open(salida, "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(filas)
elif oid == "dat.json2csv":
    with open(entrada, encoding="utf-8") as fh:
        obj = json.load(fh)
    filas = obj["items"] if isinstance(obj, dict) and "items" in obj else obj
    if filas and isinstance(filas[0], dict):
        cab = list(filas[0].keys())
        datos = [[f.get(k, "") for k in cab] for f in filas]
    else:
        cab, datos = ["valor"], [[x] for x in filas]
    with open(salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cab)
        w.writerows(datos)
else:
    sys.exit("orden de datos desconocida: %s" % oid)
