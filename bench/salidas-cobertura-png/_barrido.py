"""Barrido del oraculo contra `alfa_minimo` sobre una matriz amplia de PNG
generados. Busca discrepancias; no publica tiempos."""
import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

rnd = random.Random(20260905)
tmp = tempfile.mkdtemp(prefix="cobpng-barrido-")
filas = []

def caso(nombre, datos):
    p = os.path.join(tmp, "%03d.png" % len(filas))
    with open(p, "wb") as fh:
        fh.write(datos)
    ref = F.referencia(datos)
    got = V.alfa_minimo(p, "png", exacto=True)
    disc = (got.get("alfa_min") is None
            or abs(got["alfa_min"] - ref["alfa_min"]) > 1e-12)
    disc_pt = tuple(got["primer_transparente"]) != ref["primer_transparente"] \
        if got.get("primer_transparente") is not None else ref["primer_transparente"] is not None
    filas.append({"caso": nombre, "ref": ref["alfa_min"], "ref_crudo": ref["crudo"],
                  "got": got.get("alfa_min"), "exacto": got.get("exacto"),
                  "pt_ref": ref["primer_transparente"],
                  "pt_got": got.get("primer_transparente"),
                  "discrepa_alfa": bool(disc), "discrepa_pt": bool(disc_pt),
                  "motivo": got.get("motivo")})

TODOS = (0, 1, 2, 3, 4)

# --- 16 bits: barrido del valor de alfa, incluido el tramo hi == 255 --------
for a in (0, 1, 254, 255, 256, 32768, 65024, 65279, 65280, 65281, 65407,
          65534, 65535):
    for ent in (0, 1):
        caso("rgba16 a=%d ent=%d" % (a, ent),
             F.png(F.rgba_con_hueco(6, 4, 3, 2, a, bd=16), 6, 16,
                   entrelazado=ent, filtros=TODOS))
        caso("ga16 a=%d ent=%d" % (a, ent),
             F.png(F.gris_alfa_con_hueco(6, 4, 3, 2, a, bd=16), 4, 16,
                   entrelazado=ent, filtros=TODOS))

# --- 8 bits: alfa aleatorio por pixel ---------------------------------------
for k in range(24):
    an, al = rnd.randint(1, 17), rnd.randint(1, 11)
    ct = rnd.choice((4, 6))
    can = 2 if ct == 4 else 4
    px = [[tuple(rnd.randrange(256) for _ in range(can - 1))
           + (rnd.choice((255, 255, 255, rnd.randrange(256))),)
           for _ in range(an)] for _ in range(al)]
    ent = k % 2
    caso("azar8 ct=%d %dx%d ent=%d" % (ct, an, al, ent),
         F.png(px, ct, 8, entrelazado=ent, filtros=TODOS))

# --- 16 bits: alfa aleatorio por pixel --------------------------------------
for k in range(24):
    an, al = rnd.randint(1, 13), rnd.randint(1, 9)
    ct = rnd.choice((4, 6))
    can = 2 if ct == 4 else 4
    px = [[tuple(rnd.randrange(65536) for _ in range(can - 1))
           + (rnd.choice((65535, 65535, rnd.randrange(65280, 65536),
                          rnd.randrange(65536))),)
           for _ in range(an)] for _ in range(al)]
    ent = k % 2
    caso("azar16 ct=%d %dx%d ent=%d" % (ct, an, al, ent),
         F.png(px, ct, 16, entrelazado=ent, filtros=TODOS))

# --- paleta: todas las profundidades, tRNS corto y largo --------------------
for bd in (1, 2, 4, 8):
    n = 1 << bd
    pal = [(i * 17 % 256, i * 29 % 256, i * 43 % 256) for i in range(n)]
    for corte in (n, max(1, n // 2)):
        for an in (1, 3, 7, 8, 9, 16, 17):
            trns = [255] * corte
            trns[min(1, corte - 1)] = 90
            px = F.indices(an, 4, lambda x, y: (x * 3 + y) % n)
            for ent in (0, 1):
                caso("pal bd=%d an=%d trns=%d ent=%d" % (bd, an, corte, ent),
                     F.png(px, 3, bd, plte=pal, trns=trns, entrelazado=ent,
                           filtros=TODOS))

json.dump(filas, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "barrido.json"), "w"), indent=1)
mal = [f for f in filas if f["discrepa_alfa"]]
malpt = [f for f in filas if f["discrepa_pt"]]
print("casos:", len(filas))
print("discrepan en alfa_min:", len(mal))
for f in mal[:20]:
    print("   ", f["caso"], "ref", f["ref_crudo"], "->", f["ref"], "got", f["got"],
          "exacto", f["exacto"])
print("discrepan en primer_transparente:", len(malpt))
for f in malpt[:20]:
    print("   ", f["caso"], "pt_ref", f["pt_ref"], "pt_got", f["pt_got"])
