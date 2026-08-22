# -*- coding: utf-8 -*-
"""G3 / paso 1 — generador de la familia d5.

COPIA ADAPTADA de bench/salidas-corpus-d4/gen_corpus_d4.py, que a su vez es copia
adaptada de bench/scripts/gen_corpus_ocr.sh. NINGUNO de los dos se toca.

Tres familias, tres huecos del corpus:

  * `escaneado_d5*`  (B15) — ppp NATIVOS de 60 a 90. Todo el corpus vive entre 100 y
    240 ppp, asi que el suelo de 100 de la regla `min(max(n,100), n*1,25)*k` nunca se
    ha probado con un original que lo necesite.
  * `patologico_d5*` (B19) — sustituto de `patologico_escaneado`, que NO discrimina
    (0,00 % de CER en 88 celdas de 99, bench/k-por-motor.md). Patologias de ESCANER,
    no de sintesis: iluminacion no uniforme (caida de lampara + vinieta), polvo
    (ruido de impulso), rayas de sensor.
  * `realista_d5*`   (B12) — la degradacion que `bench/corpus-d4.md` §5.3 dejo
    PENDIENTE: sombra de encuadernacion, curvatura de pagina y transparencia del
    papel (que el reverso se transparente).

Reglas que este generador respeta, y por que:
  1. `-seed` FIJO en toda orden con `+noise`. Sin el, el corpus no es reproducible
     (CLAUDE.md trampa 22).
  2. Se trabaja en un directorio DESECHABLE (`tmp/`) y se pasa `cwd=TMP` a cada
     subproceso: hay motores que escriben fuera del destino, en el cwd del proceso
     (trampa 21). El cwd se lista antes y despues.
  3. `stdin=DEVNULL` y `timeout` explicito en las 100 % de las invocaciones.
  4. Escrito en Python y no en shell: los heredocs de este entorno se comen los
     backslashes (trampa 19).

uso: python gen_corpus_d5.py [--corpus] [nombre ...]
     sin --corpus, los PDF van a tmp/ (cribado). Con --corpus, los que empiezan por
     `escaneado_`, `patologico_` o `realista_` van a corpus/pdf/.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d4_texto import ANCHO, ALTO, MARGEN_X, pt  # noqa: E402
from d5_texto import MAQUETAS  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d5")
TMP = os.path.join(BASE, "tmp")
OUT_PDF = os.path.join(RAIZ, r"corpus\pdf")
SEMILLA = 20260822          # semilla fija del ruido: reproducibilidad

TIMEOUT = 300


def run(args):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=TIMEOUT, cwd=TMP)
    if p.returncode != 0:
        raise SystemExit(f"magick fallo ({p.returncode}): {' '.join(args[:6])}\n"
                         f"{p.stderr[:500]}")
    return p.stdout.strip()


def ident(ruta, fmt="%wx%h"):
    return run([MAGICK, "identify", "-format", fmt, ruta])


# --------------------------------------------------------------- maestros
def render_maestro(maqueta, destino, flop=False):
    args = [MAGICK, "-size", f"{ANCHO}x{ALTO}", "xc:white", "-fill", "black",
            "-gravity", "NorthWest"]
    for _etq, fuente, tam, y0, inter, lineas in maqueta:
        args += ["-font", fuente, "-pointsize", str(pt(tam))]
        for k, linea in enumerate(lineas):
            args += ["-annotate", f"+{MARGEN_X}+{y0 + k * inter}", linea]
    if flop:
        args += ["-flop"]
    args += [destino]
    run(args)
    return ident(destino)


# --------------------------------------------------------------- mascaras
def mascara_vinieta(w, h, borde, destino):
    """Caida de lampara radial: blanco en el centro, `borde` en las esquinas."""
    run([MAGICK, "-size", f"{w}x{h}", f"radial-gradient:white-gray{borde}", destino])
    return destino


def mascara_lampara(w, h, extremo, destino):
    """Caida lateral de la lampara: blanco a la izquierda, `extremo` a la derecha."""
    run([MAGICK, "-size", f"1x256", f"gradient:white-gray{extremo}",
         "-rotate", "-90", "-resize", f"{w}x{h}!", destino])
    return destino


def mascara_encuadernacion(w, h, oscuro, frac, destino):
    """Sombra de encuadernacion: los `frac` primeros por ciento del ancho se oscurecen
    hasta `oscuro`; el resto, blanco. NO es un degradado de pagina entera: en un libro
    la sombra vive en el canto interior."""
    n = max(4, int(256 * frac))
    run([MAGICK,
         "(", "-size", f"1x{n}", f"gradient:gray{oscuro}-white", ")",
         "(", "-size", f"1x{256 - n}", "xc:white", ")",
         "-append", "-rotate", "-90", "-resize", f"{w}x{h}!", destino])
    return destino


# --------------------------------------------------------------- recetas
def receta_bajo_ppp(nom, cfg, pdf_dir):
    """B15 — pocos ppp nativos. Degradacion DELIBERADAMENTE SUAVE: lo que se quiere
    medir aqui es la resolucion, no el ruido. Si metiera la degradacion de `d4`, el
    documento seria una pared y no sabria cual de las dos cosas lo rompio."""
    ppp = cfg["ppp"]
    w = ANCHO * ppp // 600
    jpg = os.path.join(TMP, nom + ".jpg")
    args = [MAGICK, "-seed", str(SEMILLA), cfg["maestro"],
            "-background", "white", "-rotate", str(cfg["ang"]),
            "-resize", f"{w}x"]
    if cfg["blur"]:
        args += ["-blur", f"0x{cfg['blur']}"]
    args += ["-colorspace", "Gray"]
    if cfg["nivel"]:
        args += ["+level", cfg["nivel"]]
    if cfg["ruido"]:
        args += ["-attenuate", str(cfg["ruido"]), "+noise", "Gaussian"]
    args += ["-quality", str(cfg["jq"]), jpg]
    run(args)
    return jpg, ppp


def receta_patologico(nom, cfg, pdf_dir):
    """B19 — patologias de ESCANER. Orden, y por que:
       rotar -> reducir -> desenfocar -> gris -> ILUMINACION (vinieta x lampara)
       -> rayas de sensor -> +level -> POLVO (impulso) -> ruido gaussiano -> JPEG.
    La iluminacion va antes del +level porque un escaner primero ilumina mal y luego
    el conversor comprime el rango de lo que ya llego mal; y el polvo va despues,
    porque es suciedad sobre el cristal, no sobre el original."""
    ppp = cfg["ppp"]
    w = ANCHO * ppp // 600
    base = os.path.join(TMP, nom + "_base.png")
    args = [MAGICK, cfg["maestro"], "-background", "white",
            "-rotate", str(cfg["ang"]), "-resize", f"{w}x"]
    if cfg["blur"]:
        args += ["-blur", f"0x{cfg['blur']}"]
    args += ["-colorspace", "Gray", base]
    run(args)
    ww, hh = (int(x) for x in ident(base).split("x"))

    vin = mascara_vinieta(ww, hh, cfg["vinieta"], os.path.join(TMP, nom + "_vin.png"))
    lam = mascara_lampara(ww, hh, cfg["lampara"], os.path.join(TMP, nom + "_lam.png"))
    ilum = os.path.join(TMP, nom + "_ilum.png")
    run([MAGICK, base, vin, "-compose", "Multiply", "-composite",
         lam, "-compose", "Multiply", "-composite", ilum])

    # rayas de sensor: lineas horizontales de una fila, claras y oscuras
    jpg = os.path.join(TMP, nom + ".jpg")
    args = [MAGICK, "-seed", str(SEMILLA), ilum, "-strokewidth", "1"]
    for i, (yfrac, tono) in enumerate(cfg["rayas"]):
        y = int(hh * yfrac)
        args += ["-stroke", f"gray{tono}", "-draw", f"line 0,{y} {ww - 1},{y}"]
    args += ["-stroke", "none"]
    if cfg["nivel"]:
        args += ["+level", cfg["nivel"]]
    if cfg["impulso"]:
        args += ["-attenuate", str(cfg["impulso"]), "+noise", "Impulse"]
    if cfg["ruido"]:
        args += ["-attenuate", str(cfg["ruido"]), "+noise", "Gaussian"]
    args += ["-quality", str(cfg["jq"]), jpg]
    run(args)
    return jpg, ppp


def receta_realista(nom, cfg, pdf_dir):
    """B12 — las tres degradaciones que `bench/corpus-d4.md` §5.3 declara ausentes.
       1. TRANSPARENCIA DEL PAPEL: el reverso (el mismo maestro reflejado) se
          transparenta. Se compone ANTES de curvar y de reducir, porque el reverso
          esta en la misma hoja fisica y se curva con ella.
       2. CURVATURA DE PAGINA: `-wave` desplaza verticalmente en funcion de x, que es
          exactamente como se comba un renglon cerca del lomo. Se recorta despues,
          porque `-wave` crece en alto.
       3. SOMBRA DE ENCUADERNACION: mascara concentrada en el canto interior.
    """
    ppp = cfg["ppp"]
    w = ANCHO * ppp // 600
    # 1 · transparencia del papel
    st = os.path.join(TMP, nom + "_st.png")
    run([MAGICK, cfg["maestro"],
         "(", cfg["reverso"], "-blur", "0x6",
         "+level", f"{cfg['reverso_nivel']}%,100%", ")",
         "-compose", "Multiply", "-composite", st])
    # 2 · rotar, reducir  (en una orden; el tamaño resultante NO es deducible a
    #     priori porque `-rotate` agranda el lienzo, asi que se MIDE)
    pre = os.path.join(TMP, nom + "_pre.png")
    args = [MAGICK, st, "-background", "white",
            "-rotate", str(cfg["ang"]), "-resize", f"{w}x"]
    if cfg["blur"]:
        args += ["-blur", f"0x{cfg['blur']}"]
    args += ["-colorspace", "Gray", pre]
    run(args)
    pw, ph = (int(x) for x in ident(pre).split("x"))
    # 2b · curvar. `-wave` crece en alto: se recorta al alto de antes.
    curv = os.path.join(TMP, nom + "_curv.png")
    if cfg["onda"]:
        run([MAGICK, pre, "-background", "white", "-virtual-pixel", "background",
             "-wave", f"{cfg['onda']}x{cfg['onda_long']}",
             "-gravity", "Center", "-extent", f"{pw}x{ph}", curv])
    else:
        run([MAGICK, pre, curv])
    ww, hh = (int(x) for x in ident(curv).split("x"))
    # 3 · sombra de encuadernacion
    enc = mascara_encuadernacion(ww, hh, cfg["lomo"], cfg["lomo_frac"],
                                 os.path.join(TMP, nom + "_enc.png"))
    jpg = os.path.join(TMP, nom + ".jpg")
    args = [MAGICK, "-seed", str(SEMILLA), curv, enc,
            "-compose", "Multiply", "-composite"]
    if cfg["nivel"]:
        args += ["+level", cfg["nivel"]]
    if cfg["ruido"]:
        args += ["-attenuate", str(cfg["ruido"]), "+noise", "Gaussian"]
    args += ["-quality", str(cfg["jq"]), jpg]
    run(args)
    return jpg, ppp


RECETAS = {"bajo_ppp": receta_bajo_ppp, "patologico": receta_patologico,
           "realista": receta_realista}


# --------------------------------------------------------------- candidatas
def d5(nom, ppp, ang, blur, nivel, ruido, jq):
    return (nom, "bajo_ppp", "m72", dict(ppp=ppp, ang=ang, blur=blur, nivel=nivel,
                                         ruido=ruido, jq=jq))


def p5(nom, ang, blur, nivel, vin, lam, imp, ruido, jq, rayas):
    return (nom, "patologico", "m200",
            dict(ppp=200, ang=ang, blur=blur, nivel=nivel, vinieta=vin, lampara=lam,
                 impulso=imp, ruido=ruido, jq=jq, rayas=rayas))


def r5(nom, ang, onda, ol, rev, lomo, lf, blur, nivel, ruido, jq):
    return (nom, "realista", "m200",
            dict(ppp=200, ang=ang, onda=onda, onda_long=ol, reverso_nivel=rev,
                 lomo=lomo, lomo_frac=lf, blur=blur, nivel=nivel, ruido=ruido, jq=jq))


_RAYAS = [(0.31, 35), (0.62, 84)]

CANDIDATAS = [
    # --- B15: pocos ppp nativos. Control limpio + cuatro resoluciones -------
    # Los cuatro puntos NO son arbitrarios: son los cuatro regimenes que la regla
    # `ppp_ocr = min(max(n,100), n*1,25)*k` distingue por debajo de 100 ppp.
    #   60 ppp -> min(100, 75)    = 75    (manda el techo x1,25; el suelo NO actua)
    #   72 ppp -> min(100, 90)    = 90    (idem)
    #   80 ppp -> min(100, 100)   = 100   (EMPATAN exactamente)
    #   90 ppp -> min(100, 112,5) = 100   (manda el suelo; unico caso en que actua)
    d5("d5_limpio", 72, 0, 0.0, None, 0.00, 95),            # control, NO va al corpus
    d5("escaneado_d5", 72, 1, 0.3, "10%,92%", 0.15, 60),    # canonico B15
    d5("escaneado_d5a", 90, 0.5, 0.2, "6%,94%", 0.10, 70),  # el suelo SI muerde
    d5("escaneado_d5b", 60, 1, 0.3, "10%,92%", 0.15, 60),   # el techo x1,25 manda
    d5("escaneado_d5c", 80, 1, 0.3, "10%,92%", 0.15, 60),   # suelo y techo empatan
    # --- B19: patologico de verdad. La escalera la hace UNA SOLA perilla, el
    #     POLVO, con la iluminacion FIJA en 78/85. Por que asi y no de otra forma
    #     esta medido y contado en bench/corpus-d5.md §3: de las cinco patologias,
    #     la iluminacion es la mas potente (74,7 puntos) pero es un INTERRUPTOR y
    #     ademas NO monotona; las rayas de sensor no valen nada (1,3 puntos) y
    #     quitar ruido gaussiano EMPEORA. El polvo es la unica que sube gradual.
    p5("patologico_d5a", -2, 1.0, "24%,80%", 78, 85, 0.12, 0.25, 40, _RAYAS),
    p5("patologico_d5b", -2, 1.0, "24%,80%", 78, 85, 0.25, 0.25, 40, _RAYAS),
    p5("patologico_d5", -2, 1.0, "24%,80%", 78, 85, 0.35, 0.25, 40, _RAYAS),
    p5("patologico_d5e", -2, 1.0, "24%,80%", 78, 85, 0.50, 0.25, 40, _RAYAS),
    # --- B12: degradacion realista ------------------------------------------
    r5("realista_d5a", 0.5, 6, 2600, 88, 72, 0.18, 0.5, "10%,92%", 0.15, 60),
    r5("realista_d5b", 1, 12, 2600, 80, 58, 0.20, 0.9, "18%,86%", 0.25, 45),
    r5("realista_d5", -1.5, 20, 2600, 72, 45, 0.22, 1.2, "26%,80%", 0.35, 33),
    r5("realista_d5e", 2, 28, 2600, 64, 34, 0.24, 1.5, "32%,74%", 0.45, 25),
]

# --- ABLACION de un factor cada vez, partiendo de `patologico_d5b`, que en el
#     cribado fue la primera PARED (92,62 % con psm 3). No van al corpus: sirven
#     para saber QUE patologia rompe a Tesseract, que es lo que convierte el
#     barrido en una medida y no en una coleccion de imagenes feas.
_B = dict(ang=-2, blur=1.0, nivel="24%,80%", vin=58, lam=68, imp=0.10, ruido=0.25,
          jq=40, rayas=[(0.31, 35), (0.62, 84)])


def _abl(nom, **cambios):
    c = dict(_B)
    c.update(cambios)
    return p5(nom, c["ang"], c["blur"], c["nivel"], c["vin"], c["lam"], c["imp"],
              c["ruido"], c["jq"], c["rayas"])


ABLACION = [
    _abl("abl_p5b_imp02", imp=0.02),          # casi sin polvo
    _abl("abl_p5b_ilum", vin=85, lam=90),     # iluminacion casi uniforme
    _abl("abl_p5b_blur06", blur=0.6),         # menos desenfoque
    _abl("abl_p5b_jq60", jq=60),              # menos JPEG
    _abl("abl_p5b_niv12", nivel="12%,90%"),   # mas contraste
    _abl("abl_p5b_rui10", ruido=0.10),        # menos ruido gaussiano
    _abl("abl_p5b_sinray", rayas=[]),         # sin rayas de sensor
]

CANDIDATAS += ABLACION

# --- BARRIDO FINO de la unica perilla dominante -----------------------------
# Primer intento de escalera patologica: mover ILUMINACION y POLVO a la vez.
# Resultado MEDIDO: acantilado de 5,87 % a 91,78 % en un solo escalon (psm 3).
# Segundo intento: dejar el POLVO FIJO en 0,045 y mover SOLO la iluminacion.
# Una escalera con dos variables acopladas no es una escalera.
BARRIDO_ILUM = [
    p5(f"cand_p5_v{v}", -2, 1.0, "24%,80%", v, l, 0.045, 0.25, 40, _RAYAS)
    for v, l in ((78, 85), (74, 81), (70, 78), (66, 74), (62, 71), (56, 66), (50, 61))
]
CANDIDATAS += BARRIDO_ILUM

# --- BARRIDO DEL POLVO, con la iluminacion FIJA en el lado benigno ----------
# El barrido de iluminacion (7 puntos, 14 celdas) devolvio un INTERRUPTOR, no un
# gradiente: de 5,03 % a 72,82 % en un escalon de 4 puntos de gris (v74 -> v70), y
# despues NO monotono (72,8 / 79,4 / 82,2 / 78,4 / 54,9). Con umbral global de Otsu
# eso es lo esperable: la iluminacion no degrada el trazo, mueve el histograma
# entero hasta que la binarizacion colapsa de golpe.
# Asi que la iluminacion se fija en 78/85 —el lado bueno del acantilado, donde
# sigue siendo una patologia visible pero no un interruptor— y la escalera la hace
# el POLVO, que si borra trazo de forma gradual.
BARRIDO_POLVO = [
    p5(f"cand_p5_i{int(i * 1000):03d}", -2, 1.0, "24%,80%", 78, 85, i, 0.25, 40,
       _RAYAS)
    for i in (0.045, 0.08, 0.12, 0.18, 0.25, 0.35)
]
CANDIDATAS += BARRIDO_POLVO

# --- CONTROL de la sonda de curvatura ---------------------------------------
# `realista_d5` con TODO igual y `onda = 0`. Si la sonda de sonda_degradacion.py
# mide curvatura donde no la hay, no mide curvatura.
CANDIDATAS.append(
    r5("abl_r5_sinonda", -1.5, 0, 2600, 72, 45, 0.22, 1.2, "26%,80%", 0.35, 33))

AL_CORPUS = ("escaneado_", "patologico_", "realista_")


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def censo(d):
    return sorted(os.listdir(d))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(TMP, exist_ok=True)
    a_corpus = "--corpus" in sys.argv
    quiere = set(a for a in sys.argv[1:] if not a.startswith("--"))

    antes_raiz = censo(RAIZ)
    antes_tmp = censo(TMP)

    maestros = {}
    for etq, maq in MAQUETAS.items():
        m = os.path.join(TMP, f"maestro_{etq}.png")
        dim = render_maestro(maq, m)
        maestros[etq] = m
        print(f"maestro {etq}: {dim}  sha256={sha256(m)[:16]}")
    rev = os.path.join(TMP, "maestro_m200_reverso.png")
    render_maestro(MAQUETAS["m200"], rev, flop=True)

    filas = []
    for nom, receta, maq, cfg in CANDIDATAS:
        if quiere and nom not in quiere:
            continue
        cfg = dict(cfg)
        cfg["maestro"] = maestros[maq]
        cfg["reverso"] = rev
        jpg, ppp = RECETAS[receta](nom, cfg, None)
        va = a_corpus and nom.startswith(AL_CORPUS)
        pdf = os.path.join(OUT_PDF if va else TMP, nom + ".pdf")
        run([MAGICK, jpg, "-units", "PixelsPerInch", "-density", str(ppp), pdf])
        dim = ident(jpg)
        fila = {"nombre": nom, "receta": receta, "maqueta": maq, "ppp": ppp,
                "px": dim, "jpg_bytes": os.path.getsize(jpg),
                "jpg_sha256": sha256(jpg), "pdf": pdf,
                "pdf_bytes": os.path.getsize(pdf), "pdf_sha256": sha256(pdf),
                "cfg": {k: v for k, v in cfg.items()
                        if k not in ("maestro", "reverso")}}
        filas.append(fila)
        print(f"{nom:18s} {receta:11s} ppp={ppp:3d} px={dim:10s} "
              f"jpg={fila['jpg_bytes']:7d} pdf={fila['pdf_bytes']:7d} "
              f"jpgsha={fila['jpg_sha256'][:16]}")

    despues_raiz = censo(RAIZ)
    nuevos = [x for x in despues_raiz if x not in antes_raiz]
    nuevos_tmp = [x for x in censo(TMP) if x not in antes_tmp]
    print(f"\ncenso raiz — ficheros nuevos NO pedidos: {nuevos or 'ninguno'}")
    print(f"censo tmp  — {len(nuevos_tmp)} ficheros nuevos (todos esperados en un "
          f"directorio desechable)")

    out = os.path.join(BASE, "json", "candidatas_d5.json")
    prev = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else []
    prev = [f for f in prev if f["nombre"] not in {x["nombre"] for x in filas}]
    json.dump(prev + filas, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
