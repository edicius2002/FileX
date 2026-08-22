# -*- coding: utf-8 -*-
"""G3 / sonda — comprobar EN EL PIXEL que las tres degradaciones "realistas" existen.

Un generador puede escribir `-wave 20x2600` y que el efecto no llegue a la imagen.
Declarar una patologia sin medirla es exactamente el error que hace inutil a
`patologico_escaneado`. Asi que las tres se miden:

  1. SOMBRA DE ENCUADERNACION -> cociente de luminancia entre la franja izquierda
     (20 % del ancho) y la derecha. 1,00 = no hay sombra.
  2. CURVATURA DE PAGINA -> se busca, en cuatro franjas verticales, la fila mas
     oscura dentro de una banda que contiene un renglon. Si la pagina esta combada,
     esa fila se mueve con x. El estadistico es (max - min) en pixeles.
  3. TRANSPARENCIA DEL PAPEL -> luminancia media de una zona que en el maestro esta
     EN BLANCO. Si el reverso se transparenta, esa zona deja de ser blanca.

Se comparan siempre contra `escaneado_d4`, que no tiene ninguna de las tres.
"""
import json
import os
import subprocess
import sys

import numpy as np

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
BASE = r"D:\Work\research\FileX\bench\salidas-corpus-d5"
IMG = os.path.join(BASE, "img")
TMP = os.path.join(BASE, "tmp")

DOCS = ["realista_d5a", "realista_d5b", "realista_d5", "realista_d5e",
        "abl_r5_sinonda",
        "patologico_d5a", "patologico_d5", "patologico_d5e", "escaneado_d4"]


def gris(png):
    w, h = subprocess.run([MAGICK, "identify", "-format", "%w %h", png],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          timeout=300, cwd=TMP).stdout.split()
    p = subprocess.run([MAGICK, png, "-depth", "8", "gray:-"],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=300,
                       cwd=TMP)
    return np.frombuffer(p.stdout, dtype=np.uint8).reshape(int(h), int(w)) / 255.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    filas = []
    for d in DOCS:
        png = os.path.join(IMG, f"magick_ppp200__{d}.png")
        if not os.path.exists(png):
            print(f"[falta] {d}")
            continue
        a = gris(png)
        h, w = a.shape
        # 1 · sombra de encuadernacion
        izq = float(a[:, :w // 5].mean())
        der = float(a[:, -w // 5:].mean())
        # 2 · curvatura. Buscar "la fila mas oscura" no vale: con ruido el argmin
        #     salta y da 200 px de falso positivo en un documento SIN curvar
        #     (medido: `escaneado_d4` daba 200). Lo que si vale es CORRELACION
        #     CRUZADA del perfil de tinta por filas entre franjas verticales: el
        #     desplazamiento que mejor alinea dos franjas es el combado entre ellas.
        #     Y hay un segundo falso positivo: la ROTACION tambien desplaza el
        #     renglon linealmente con x (a -4 grados y 900 px de recorrido son 63 px),
        #     asi que el desplazamiento crudo mide sobre todo el giro. La curvatura
        #     es lo que QUEDA despues de quitarle la recta: el RESIDUO.
        banda = 1.0 - a[280:760, :]          # tinta = 1
        xs = [120, 300, 480, 660, 840, 1020]
        ref = banda[:, xs[0]:xs[0] + 120].mean(axis=1)
        ref = ref - ref.mean()
        ys = []
        for x in xs:
            pr = banda[:, x:x + 120].mean(axis=1)
            pr = pr - pr.mean()
            mejor, mejorc = 0, -9e9
            for lag in range(-60, 61):
                b = np.roll(pr, lag)
                c = float((ref[60:-60] * b[60:-60]).sum())
                if c > mejorc:
                    mejorc, mejor = c, lag
            ys.append(mejor)
        pend, cte = np.polyfit(np.array(xs, dtype=float), np.array(ys, dtype=float), 1)
        resid = np.array(ys) - (pend * np.array(xs) + cte)
        # 3 · transparencia: franja blanca del maestro (bajo el bloque pequeño)
        blanco = float(a[int(h * 0.72):int(h * 0.80), w // 5:w * 4 // 5].mean())
        import math
        f = {"doc": d, "sombra_izq_der": round(izq / der, 4),
             "lum_izq": round(izq, 4), "lum_der": round(der, 4),
             "desplaz_crudo_px": max(ys) - min(ys), "lags": ys,
             "giro_medido_grados": round(math.degrees(math.atan(float(pend))), 2),
             "curvatura_residuo_px": round(float(np.abs(resid).max()), 1),
             "zona_blanca_lum": round(blanco, 4)}
        filas.append(f)
        print(f"{d:16s} sombra(izq/der)={f['sombra_izq_der']:.4f}  "
              f"giro={f['giro_medido_grados']:+5.2f} grados  "
              f"curvatura(residuo)={f['curvatura_residuo_px']:5.1f} px  "
              f"zona_blanca={f['zona_blanca_lum']:.4f}")
    json.dump(filas, open(os.path.join(BASE, "json", "sonda_degradacion.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n-> json/sonda_degradacion.json")


if __name__ == "__main__":
    main()
