#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banco de medida del encargo P3 (C9 + C10 + C11 + C12).

COPIA ADAPTADA de bench/salidas-verificador-gs/medir_gs.py, que pertenece al
informe de V1 y no se toca (arnes compartido). Aqui solo hay lo que este
informe necesita.

Subcomandos:
  coste     coste del PUNTO 5: censo antes/despues, censo solo-despues (R18),
            mtime del directorio, y el contrato completo con y sin punto 5
  ordenes   re-ejecuta las 39 ordenes del patron oro en directorio DESECHABLE
            con censo, y aplica el punto 5: falsos positivos y multifichero
  fuga      reproduce los dos casos conocidos (DASH y magick->html)
  i9        coste y discriminacion de la regla I9 (el caso resvg)
  familia   sonda de la familia "el envase es correcto y el contenido no esta"
  p9        validacion de P9 contra capas OCR reales y textos legitimos cortos
  v2        la suite de fidelidad con y sin V2

Sin GPU y sin pedir su lock. Medianas de n>=9 con LOS DOS TESTIGOS DE RUIDO
(monohilo para la deriva, lanzamiento de proceso para el nivel): hay otros dos
agentes trabajando en paralelo, uno de ellos midiendo en CPU.
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))

import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402

REF = os.path.join(RAIZ, "bench", "salidas-referencia")
COPIA = {"2pistas_mkv-to-COPY.mp4", "tipico_mp4-to.mkv", "tipico_mp4-audio-copy.m4a"}
TMP = os.path.join(AQUI, "tmp")


def _testigo():
    """Testigo de CPU MONOHILO: detecta DERIVA dentro de la tanda."""
    t = time.perf_counter()
    s = 0
    for i in range(300000):
        s += i * i
    return (time.perf_counter() - t) * 1000


TESTIGO_SUB_BASE = None


def _testigo_sub():
    """Testigo de LANZAMIENTO DE PROCESO: detecta el NIVEL de carga. El
    monohilo es ciego a la contencion multinucleo (verificador-ghostscript.md
    §4: etiqueto `limpia` una tanda que salio x6,8)."""
    t = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-v", "quiet", "-version"], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=20)
    except subprocess.TimeoutExpired:
        # Ha pasado: con los otros dos agentes trabajando, `ffprobe -version`
        # llego a agotar 60 s. El testigo NO puede tumbar la tanda: devuelve el
        # tope y la tanda sale SUCIA, que es justo lo que hay que saber.
        return 20000.0
    return (time.perf_counter() - t) * 1000


def calibrar():
    global TESTIGO_SUB_BASE
    for _ in range(2):
        _testigo_sub()
    TESTIGO_SUB_BASE = min(_testigo_sub() for _ in range(5))
    print("# testigo de subproceso al empezar: %.1f ms  (reposo medido: 26,5-26,8)"
          % TESTIGO_SUB_BASE)
    return TESTIGO_SUB_BASE


def measure(etiqueta, n, fn, calentar=1):
    for _ in range(calentar):
        fn()
    antes = min(_testigo() for _ in range(3))
    sub_a = min(_testigo_sub() for _ in range(2))
    tiempos = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        tiempos.append((time.perf_counter() - t) * 1000)
    despues = min(_testigo() for _ in range(3))
    sub_d = min(_testigo_sub() for _ in range(2))
    desv = abs(despues - antes) / max(antes, 1e-9)
    sub = max(sub_a, sub_d)
    nivel = (sub / TESTIGO_SUB_BASE) if TESTIGO_SUB_BASE else None
    motivos = []
    if desv > 0.20:
        motivos.append("deriva cpu %+.0f%%" % (desv * 100))
    if nivel and nivel > 1.20:
        motivos.append("nivel sub x%.1f" % nivel)
    flag = "limpia" if not motivos else "SUCIA(%s)" % "; ".join(motivos)
    tiempos.sort()
    return {"etiqueta": etiqueta, "n": n,
            "mediana_ms": round(statistics.median(tiempos), 4),
            "min_ms": round(tiempos[0], 4), "max_ms": round(tiempos[-1], 4),
            "flag": flag, "testigo_ms": [round(antes, 2), round(despues, 2)],
            "testigo_sub_ms": [round(sub_a, 1), round(sub_d, 1)],
            "nivel_sub": round(nivel, 2) if nivel else None}


def guardar(nombre, obj):
    ruta = os.path.join(AQUI, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)
    print("-> %s" % ruta)


def limpio(d):
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


# ===========================================================================
def cmd_coste():
    """Cuanto cuesta el punto 5, y con que implementacion."""
    calibrar()
    res = {"censo": [], "contrato": []}
    base = limpio(os.path.join(TMP, "coste"))
    for n_ent in (1, 2, 10, 100, 1000):
        d = limpio(os.path.join(base, "d%d" % n_ent))
        for i in range(n_ent):
            with open(os.path.join(d, "f%04d.bin" % i), "wb") as fh:
                fh.write(b"x" * 16)
        for etq, fn in (
            ("censar_dir (1 scandir)", lambda d=d: V.censar_dir(d)),
            ("censo ANTES+DESPUES (2 scandir)",
             lambda d=d: (V.censar_dir(d), V.censar_dir(d))),
            ("mtime_dir (1 stat)", lambda d=d: V.mtime_dir(d)),
        ):
            r = measure("%s, %d entradas" % (etq, n_ent), 15, fn, calentar=3)
            r["entradas"] = n_ent
            res["censo"].append(r)
            print("  %-46s %d ent  %8.4f ms  %s"
                  % (etq, n_ent, r["mediana_ms"], r["flag"]))

    # ---- el contrato completo, con y sin punto 5 --------------------------
    tj = [t for t in trabajos()]
    sal = tj[0]["salida"]
    ent = tj[0]["entrada"]
    ped = tj[0]["pedido"]
    d = limpio(os.path.join(base, "r18"))
    shutil.copy(sal, d)
    sal_d = os.path.join(d, os.path.basename(sal))
    censo_r18 = {"antes": {os.path.abspath(d): {}}, "despues": V.censar([d])}
    censo_pre = {"antes": V.censar([d]), "despues": V.censar([d])}
    grande = os.path.join(base, "d1000")          # el dir de 1000 entradas
    fns = [
        ("contrato SIN punto 5 (censo=None)",
         lambda: V.verificar(sal_d, ped, ent)),
        ("contrato + punto 5 con censo YA HECHO (solo la logica)",
         lambda: V.verificar(sal_d, ped, ent, censo=censo_r18)),
        ("contrato + punto 5 COMPLETO con R18 (censar solo DESPUES)",
         lambda: V.verificar(sal_d, ped, ent,
                             censo={"antes": {os.path.abspath(d): {}},
                                    "despues": V.censar([d])})),
        ("contrato + punto 5 COMPLETO sin R18, dir de 2 (censar 2 veces)",
         lambda: V.verificar(sal_d, ped, ent,
                             censo={"antes": V.censar([d]),
                                    "despues": V.censar([d])})),
        ("contrato + punto 5 COMPLETO sin R18, dir de 1000 (censar 2 veces)",
         lambda: V.verificar(sal_d, ped, ent,
                             censo={"antes": V.censar([grande]),
                                    "despues": V.censar([grande])})),
    ]
    for etq, fn in fns:
        r = measure(etq, 15, fn, calentar=3)
        res["contrato"].append(r)
        print("  %-62s %8.4f ms  %s" % (etq, r["mediana_ms"], r["flag"]))

    # solo la logica del punto 5, aislada
    for etq, c in (("punto5_escritura, 0 ficheros nuevos", censo_pre),
                   ("punto5_escritura, 1 fichero nuevo (R18)", censo_r18)):
        r = measure(etq, 15, lambda c=c: V.punto5_escritura(sal_d, ped, c),
                    calentar=3)
        res["contrato"].append(r)
        print("  %-52s %8.4f ms  %s" % (etq, r["mediana_ms"], r["flag"]))
    guardar("coste_p5.json", res)


# ===========================================================================
def _correr(orden, cwd, timeout=180):
    t = time.perf_counter()
    p = subprocess.run(orden, cwd=cwd, shell=True, capture_output=True,
                       stdin=subprocess.DEVNULL, text=True, timeout=timeout)
    return p.returncode, (time.perf_counter() - t) * 1000, (p.stderr or "")[-300:]


def cmd_ordenes():
    """Re-ejecuta las 39 ordenes del patron oro en un directorio DESECHABLE y
    aplica el punto 5. Es la unica forma de medir sus falsos positivos: el
    punto 5 no se puede evaluar sobre un fichero que ya existe."""
    ref = json.load(open(os.path.join(REF, "referencia.json"), encoding="utf-8"))
    base = limpio(os.path.join(TMP, "ordenes"))
    res = []
    for i, o in enumerate(ref["ordenes"]):
        orden = o["orden"]
        if not orden.split()[0] in ("magick", "gswin64c", "ffmpeg"):
            res.append({"id": o["id"], "saltada": "no es una orden de motor",
                        "orden": orden})
            continue
        d = limpio(os.path.join(base, "o%02d" % i))
        ent = os.path.join(RAIZ, o["entrada"].replace("salidas/", "bench/salidas-referencia/"))
        if not os.path.exists(ent):
            res.append({"id": o["id"], "saltada": "falta la entrada %s" % ent})
            continue
        shutil.copy(ent, d)
        # R18: el directorio esta vacio salvo la entrada -> el censo de ANTES
        # es el de la entrada; el de DESPUES lo dice todo.
        antes = V.censar([d])
        rc, ms, err = _correr(orden, d)
        despues = V.censar([d])
        nuevos = sorted(set(despues[os.path.abspath(d)]) - set(antes[os.path.abspath(d)]))
        # ¿cual es el fichero declarado? el nombre que la orden nombra como salida
        decl = _declarado(orden, nuevos)
        censo = {"antes": antes, "despues": despues}
        ped = {"destino": os.path.splitext(decl or "")[1].lstrip(".") or None,
               "params": {}}
        hall = V.punto5_escritura(os.path.join(d, decl or "?"), ped, censo) if decl else []
        res.append({"id": o["id"], "orden": orden, "rc": rc, "ms": round(ms, 1),
                    "declarado": decl, "nuevos": nuevos,
                    "n_nuevos": len(nuevos),
                    "multifichero": len(nuevos) > 1,
                    "tam": {n: despues[os.path.abspath(d)][n] for n in nuevos},
                    "hallazgos": hall,
                    "sev": sorted({h["severidad"] for h in hall}),
                    "stderr": err.strip()[-160:] if rc else ""})
        print("  %-22s rc=%d  nuevos=%-2d %-38s %s"
              % (o["id"], rc, len(nuevos), ",".join(nuevos[:3]),
                 ";".join(h["regla"] + ":" + h["severidad"] for h in hall
                          if h["severidad"] != "informativo") or "-"))
    guardar("ordenes39.json", res)
    fp = [r for r in res if r.get("sev") and
          ({"fallo", "aviso"} & set(r["sev"]))]
    multi = [r for r in res if r.get("n_nuevos", 0) > 1]
    print("\n  ordenes ejecutadas: %d" % sum(1 for r in res if "rc" in r))
    print("  con hallazgo de severidad fallo/aviso en el punto 5: %d" % len(fp))
    for r in fp:
        print("    - %s: %s" % (r["id"], [h["mensaje"][:90] for h in r["hallazgos"]
                                          if h["severidad"] != "informativo"]))
    print("  ordenes que producen MAS DE UN fichero: %d" % len(multi))
    for r in multi:
        print("    - %s: %s" % (r["id"], r["nuevos"]))


def _declarado(orden, nuevos):
    """Cual de los ficheros nuevos es el que la orden DECLARA como salida."""
    import re
    m = re.search(r"-sOutputFile=(\S+)", orden)
    if m:
        n = m.group(1)
        if "%d" in n:
            cand = [x for x in nuevos
                    if x.endswith(os.path.splitext(n)[1])]
            return sorted(cand)[0] if cand else None
        return n if n in nuevos else (nuevos[0] if nuevos else None)
    ult = orden.split()[-1]
    if ult in nuevos:
        return ult
    return nuevos[0] if len(nuevos) == 1 else (sorted(nuevos)[0] if nuevos else None)


# ===========================================================================
def cmd_fuga():
    """Los dos casos reproducidos por E1, ahora con el punto 5 puesto."""
    base = limpio(os.path.join(TMP, "fuga"))
    trabajo = limpio(os.path.join(base, "trabajo"))   # cwd del motor
    destino = limpio(os.path.join(base, "destino"))   # DEST/
    shutil.copy(os.path.join(RAIZ, "corpus", "video", "trivial.mp4"), trabajo)
    shutil.copy(os.path.join(RAIZ, "corpus", "imagen", "trivial.png"), trabajo)
    res = []
    casos = [
        ("ffmpeg -> DASH .mpd",
         'ffmpeg -y -nostdin -threads 4 -i trivial.mp4 "%s"' %
         os.path.join(destino, "t.mpd"), os.path.join(destino, "t.mpd"), "mpd"),
        ("magick -> .html",
         'magick trivial.png -auto-orient "%s"' % os.path.join(destino, "u.html"),
         os.path.join(destino, "u.html"), "html"),
        ("magick -> .map (control: un solo fichero)",
         'magick trivial.png -auto-orient "%s"' % os.path.join(destino, "v.map"),
         os.path.join(destino, "v.map"), "map"),
        ("control sano: magick -> .webp",
         'magick trivial.png -quality 80 "%s"' % os.path.join(destino, "w.webp"),
         os.path.join(destino, "w.webp"), "webp"),
    ]
    for etq, orden, decl, dest in casos:
        antes = V.censar([trabajo, destino])
        rc, ms, err = _correr(orden, trabajo)
        despues = V.censar([trabajo, destino])
        censo = {"antes": antes, "despues": despues}
        ped = {"destino": dest, "params": {}}
        r4 = V.verificar(decl, ped, None)
        r5 = V.verificar(decl, ped, None, censo=censo)
        res.append({"caso": etq, "orden": orden, "rc": rc, "ms": round(ms, 1),
                    "bytes_declarado": os.path.getsize(decl) if os.path.exists(decl) else None,
                    "veredicto_4_puntos": r4["veredicto"],
                    "veredicto_5_puntos": r5["veredicto"],
                    "hallazgos_p5": [h for h in r5["hallazgos"] if h["punto"] == 5],
                    "stderr": err.strip()[-200:]})
        print("  %-42s rc=%d  4 puntos=%-10s  5 puntos=%s"
              % (etq, rc, r4["veredicto"], r5["veredicto"]))
        for h in res[-1]["hallazgos_p5"]:
            print("      [%s %s] %s" % (h["regla"], h["severidad"], h["mensaje"][:120]))
    guardar("fuga.json", res)


# ===========================================================================
def cmd_multi():
    """Salidas LEGITIMAMENTE multifichero. El patron oro no tiene ni una, asi
    que sin estos casos el '0 falsos positivos' no probaria nada en la
    dimension que mas importa para el punto 5."""
    base = limpio(os.path.join(TMP, "multi"))
    trabajo = limpio(os.path.join(base, "trabajo"))
    destino = limpio(os.path.join(base, "destino"))
    shutil.copy(os.path.join(RAIZ, "corpus", "video", "trivial.mp4"), trabajo)
    # un PDF de DOS paginas, para que el patron %d de gs produzca dos ficheros
    dos = os.path.join(trabajo, "dos.pdf")
    uno = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
    _correr('gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite '
            '-sOutputFile="%s" "%s" "%s"' % (dos, uno, uno), trabajo)
    casos = [
        ("HLS: ffmpeg -> .m3u8 (segmentos EN EL DESTINO)",
         'ffmpeg -y -nostdin -threads 4 -i trivial.mp4 -c:v libx264 -crf 30 '
         '-hls_time 1 -hls_segment_filename "%s" "%s"'
         % (os.path.join(destino, "h%03d.ts"), os.path.join(destino, "h.m3u8")),
         os.path.join(destino, "h.m3u8"), "m3u8", {}),
        ("secuencia: ffmpeg -> f%03d.png",
         'ffmpeg -y -nostdin -threads 4 -i trivial.mp4 -vf fps=4 "%s"'
         % os.path.join(destino, "f%03d.png"),
         os.path.join(destino, "f%03d.png"), "png", {}),
        ("secuencia: gs -sOutputFile=%d.png sobre un PDF de 2 paginas",
         'gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r72 '
         '-sOutputFile="%s" "%s"' % (os.path.join(destino, "p%d.png"), dos),
         os.path.join(destino, "p%d.png"), "png", {}),
        ("DASH declarado como multifichero en el PEDIDO",
         'ffmpeg -y -nostdin -threads 4 -i trivial.mp4 "%s"'
         % os.path.join(destino, "d.mpd"),
         os.path.join(destino, "d.mpd"), "mpd", {"multifichero": True}),
    ]
    res = []
    for etq, orden, decl, dest, extra in casos:
        antes = V.censar([trabajo, destino])
        rc, ms, err = _correr(orden, trabajo)
        despues = V.censar([trabajo, destino])
        censo = {"antes": antes, "despues": despues}
        ped = dict({"destino": dest, "params": {}}, **extra)
        hall = V.punto5_escritura(decl, ped, censo)
        nuevos = sorted(set(despues[os.path.abspath(destino)])
                        - set(antes[os.path.abspath(destino)]))
        fuera = sorted(set(despues[os.path.abspath(trabajo)])
                       - set(antes[os.path.abspath(trabajo)]))
        res.append({"caso": etq, "orden": orden, "rc": rc, "ms": round(ms, 1),
                    "nuevos_en_destino": nuevos[:8],
                    "n_en_destino": len(nuevos),
                    "nuevos_en_trabajo": fuera,
                    "hallazgos": hall,
                    "sev": sorted({h["severidad"] for h in hall}),
                    "stderr": err.strip()[-200:] if rc else ""})
        print("  %-52s rc=%d  destino=%-3d trabajo=%d  %s"
              % (etq[:52], rc, len(nuevos), len(fuera),
                 ";".join("%s:%s" % (h["regla"], h["severidad"]) for h in hall)))
        for h in hall:
            print("      [%s %s] %s" % (h["regla"], h["severidad"], h["mensaje"][:120]))
    guardar("multi.json", res)


# ===========================================================================
def cmd_i9():
    """La regla que atrapa a resvg: discriminacion y coste real."""
    calibrar()
    c8 = os.path.join(RAIZ, "bench", "salidas-aristas", "c8")
    svg = os.path.join(c8, "in", "e1.svg")
    casos = [
        ("Inkscape 1.x (contenedor)", os.path.join(c8, "out", "out", "s_ink.png"), svg, "ok"),
        ("resvg 0.46.0 (contenedor)", os.path.join(c8, "out", "out", "s_resvg.png"), svg, "fallo"),
        ("magick 7.1.2 (Windows)", os.path.join(c8, "out", "s_magick_win.png"), svg, "ok"),
    ]
    # controles fabricados: SVG sin texto, y SVG con texto invisible
    fx = limpio(os.path.join(AQUI, "fixtures"))
    sin_texto = os.path.join(fx, "sin_texto.svg")
    open(sin_texto, "w", encoding="utf-8").write(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" '
        'viewBox="0 0 400 200"><rect width="400" height="200" fill="#fff"/>'
        '<circle cx="200" cy="100" r="80" fill="#3366cc"/></svg>\n')
    corto = os.path.join(fx, "texto_corto.svg")
    open(corto, "w", encoding="utf-8").write(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" '
        'viewBox="0 0 200 100"><rect width="200" height="100" fill="#fff"/>'
        '<text x="10" y="60" font-size="30" fill="#000">Ab</text></svg>\n')
    medio = os.path.join(fx, "texto_medio.svg")
    open(medio, "w", encoding="utf-8").write(
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120" '
        'viewBox="0 0 300 120"><rect width="300" height="120" fill="#fff"/>'
        '<text x="150" y="60" font-size="20" text-anchor="middle" fill="#000">'
        'centrado y largo</text></svg>\n')
    for nombre, fuente in (("sin_texto", sin_texto), ("texto_corto", corto),
                           ("texto_medio", medio)):
        png = os.path.join(fx, nombre + ".png")
        rc, _, err = _correr('magick "%s" "%s"' % (fuente, png), fx)
        casos.append(("control magick: " + nombre, png, fuente,
                      "ok" if rc == 0 else "rc=%d" % rc))
    res = {"casos": [], "coste": []}
    for etq, png, fuente, esperado in casos:
        if not os.path.exists(png):
            res["casos"].append({"caso": etq, "error": "no existe %s" % png})
            continue
        r = V.verificar_fidelidad(png, {"destino": "png", "params": {}}, fuente)
        tx = V.svg_textos(fuente)
        ti = V.png_tinta_cajas(png, tx["cajas"],
                               *(_escala(png, tx)))if tx["cajas"] else {}
        h9 = [x for x in r["hallazgos"] if x["regla"] == "I9"]
        res["casos"].append({"caso": etq, "png": os.path.relpath(png, RAIZ),
                             "svg": os.path.relpath(fuente, RAIZ),
                             "n_textos": tx["n_textos"], "esperado": esperado,
                             "veredicto": r["veredicto"],
                             "hallazgos": h9,
                             "tinta": ti.get("cajas"),
                             "ms": {k: round(v, 3) for k, v in r["ms"].items()}})
        print("  %-34s textos=%d  %-10s  %s"
              % (etq, tx["n_textos"], r["veredicto"],
                 (h9[0]["mensaje"][:80] if h9 else "-")))
    # ¿como escala con el tamaño del raster? Se rasteriza el MISMO SVG grande.
    for w, h in ((800, 400), (1920, 960)):
        g = os.path.join(fx, "e1_%d.png" % w)
        _correr('magick -density %d "%s" -resize %dx%d "%s"'
                % (72 * w // 400, svg, w, h, g), fx)
        if os.path.exists(g):
            casos.append(("escala: e1.svg rasterizado a %dx%d" % (w, h),
                          g, svg, "ok"))
    # coste, mediana n=9, desglosado. La escala se precalcula FUERA del
    # cronometro: si no, cada medida incluiria un sondeo que no es de la regla.
    for etq, png, fuente, _ in casos[:3] + casos[-2:]:
        tx = V.svg_textos(fuente)
        esc = _escala(png, tx)
        r = measure("I9 completa: " + etq, 9,
                    lambda p=png, f=fuente: V.verificar_fidelidad(
                        p, {"destino": "png", "params": {}}, f))
        res["coste"].append(r)
        print("  coste %-44s %8.3f ms  %s" % (etq[:44], r["mediana_ms"], r["flag"]))
        r = measure("I9 solo el ORIGEN (xml.etree): " + etq, 9,
                    lambda f=fuente: V.svg_textos(f))
        res["coste"].append(r)
        print("  coste %-44s %8.3f ms  %s"
              % ("  origen (xml.etree)", r["mediana_ms"], r["flag"]))
        r = measure("I9 solo la SALIDA (tinta en proceso): " + etq, 9,
                    lambda p=png, t=tx, e=esc: V.png_tinta_cajas(p, t["cajas"], *e))
        res["coste"].append(r)
        print("  coste %-44s %8.3f ms  %s"
              % ("  salida (tinta, en proceso)", r["mediana_ms"], r["flag"]))
        # LA COMPARACION QUE HAY QUE HACER: la misma medida con `magick`, que
        # es C. En proceso el coste crece con el area; en magick, no.
        c = tx["cajas"][0]["caja"]
        x0, y0, x1, y1 = [int(round(c[0] * esc[0])), int(round(c[1] * esc[1])),
                          int(round(c[2] * esc[0])), int(round(c[3] * esc[1]))]
        orden = ('magick "%s" -crop %dx%d+%d+%d +repage -colorspace Gray '
                 '-threshold 60%%%% -format "%%%%[fx:100*(1-mean)]" info:'
                 % (png, max(x1 - x0, 1), max(y1 - y0, 1), x0, y0))
        r = measure("I9 salida con MAGICK (subproceso): " + etq, 9,
                    lambda o=orden: _correr(o, fx))
        res["coste"].append(r)
        print("  coste %-44s %8.3f ms  %s"
              % ("  salida (tinta, con magick)", r["mediana_ms"], r["flag"]))
    guardar("i9.json", res)


def _escala(png, tx):
    s = V.sondear(png)
    if not (s.get("ancho") and tx.get("ancho_usuario")):
        return (1.0, 1.0)
    return (s["ancho"] / tx["ancho_usuario"], s["alto"] / tx["alto_usuario"])


# ===========================================================================
# C11 — validacion de P9
# ===========================================================================
TESSDATA = r"C:\Program Files\PDFgear\tessdata"   # trae eng y spa. NO es del
# proyecto: lo instalo PDFgear. El coste de distribucion es real (2-4 MB por
# idioma) y esta contado en verificador-ghostscript.md §5.1.


def pdf_minimo(ruta, lineas, tam=12):
    """Escribe un PDF de UNA pagina con una capa de texto REAL. Biblioteca
    estandar: hace falta para fabricar textos legitimos CORTOS, que son donde
    P9 puede dar un falso positivo, y no hay ningun motor de autoria en esta
    maquina."""
    flujo = ["BT", "/F1 %d Tf" % tam, "14 TL", "72 720 Td"]
    for ln in lineas:
        esc = ln.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        flujo.append("(%s) Tj T*" % esc)
    flujo.append("ET")
    cont = "\n".join(flujo).encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(cont) + cont + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    buf = bytearray(b"%PDF-1.4\n")
    pos = []
    for i, o in enumerate(objs, 1):
        pos.append(len(buf))
        buf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(buf)
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for p in pos:
        buf += b"%010d 00000 n \n" % p
    buf += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref))
    with open(ruta, "wb") as fh:
        fh.write(buf)
    return ruta


VOCALES = set("aeiouáéíóúüàèìòùâêîôûAEIOUÁÉÍÓÚÜ")


def señales(texto):
    """Candidatas a señal contra la alucinacion, TODAS en proceso y sobre el
    texto que P6 ya extrajo: no lanzan ni un proceso."""
    tk = texto.split()
    n = len(tk)
    if not n:
        return {"tokens": 0}
    letras = sum(1 for c in texto if c.isalpha())
    utiles = sum(1 for c in texto if not c.isspace())
    sin_vocal = sum(1 for t in tk if not (set(t) & VOCALES) and
                    any(c.isalpha() for c in t))
    return {
        "tokens": n,
        "long_media": sum(len(t) for t in tk) / n,
        "pct_1letra": 100.0 * sum(1 for t in tk if len(t) == 1) / n,
        "pct_no_alfa": 100.0 * (utiles - letras) / max(utiles, 1),
        "pct_sin_vocal": 100.0 * sin_vocal / n,
    }


def _similitud(a, b):
    """Similitud 0-1 entre dos cadenas (SequenceMatcher, biblioteca estandar)."""
    import difflib
    a = " ".join(a.split()).lower()
    b = " ".join(b.split()).lower()
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _cer(ref, obt, acentos=True):
    """CER = distancia de edicion / len(referencia). Puede pasar de 100 %: es
    lo que significa cuando el motor INVENTA."""
    import unicodedata
    import re

    def norm(t):
        t = " ".join(t.split()).lower()
        if not acentos:
            t = unicodedata.normalize("NFKD", t)
            t = "".join(c for c in t if not unicodedata.combining(c))
            t = re.sub(r"[^a-z0-9 ]+", " ", t)
            t = " ".join(t.split())
        return t

    a, b = norm(ref), norm(obt)
    if not a:
        return None
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return 100.0 * prev[-1] / len(a)


def cmd_p9():
    """P9 esta calibrada sobre 5 puntos y declarada NO VALIDADA. Aqui se valida
    contra capas OCR REALES (buenas y alucinadas) y contra textos legitimos
    CORTOS, que es donde puede dar falso positivo."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-corpus-d4"))
    from d4_texto import REFERENCIA as REF_D4     # noqa: E402
    REF_D123 = ("DOCUMENTO ESCANEADO Texto que solo existe como pixeles. "
                "Debe recuperarse con OCR.")
    base = limpio(os.path.join(TMP, "p9"))
    env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
    docs = [("patologico_escaneado", 200, REF_D123),
            ("escaneado_d1", 150, REF_D123),
            ("escaneado_d2", 100, REF_D123),
            ("escaneado_d3", 100, REF_D123),
            ("escaneado_d4", 200, REF_D4),
            ("escaneado_d4c", 200, REF_D4),
            ("escaneado_d4e", 200, REF_D4),
            ("escaneado_d4f", 240, REF_D4)]
    res = {"ocr": [], "legitimos": []}
    for nombre, ppp, ref in docs:
        src = os.path.join(RAIZ, "corpus", "pdf", nombre + ".pdf")
        if not os.path.exists(src):
            continue
        for lang in ("spa", "eng"):
            for factor in (1.0, 2.0):
                r = int(ppp * factor)
                out = os.path.join(base, "%s_%s_%d.pdf" % (nombre, lang, r))
                orden = ["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                         "-sDEVICE=pdfocr8", "-r%d" % r,
                         "-sOCRLanguage=%s" % lang,
                         "-sOutputFile=" + out, src]
                t0 = time.perf_counter()
                try:
                    p = subprocess.run(orden, capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL, env=env,
                                       timeout=300)
                    rc = p.returncode
                except subprocess.TimeoutExpired:
                    rc = -9
                ms = (time.perf_counter() - t0) * 1000
                if rc != 0 or not os.path.exists(out):
                    res["ocr"].append({"doc": nombre, "lang": lang, "ppp": r,
                                       "rc": rc, "error": "gs fallo"})
                    continue
                ts, err = V._gs_texto(out)
                ts = ts or ""
                ns = len("".join(ts.split()))
                sen = V.senal_alucinacion(ts)
                cer = _cer(ref, ts, True)
                cer_a = _cer(ref, ts, False)
                sg = señales(ts)
                txt_dir = os.path.join(AQUI, "texto")
                os.makedirs(txt_dir, exist_ok=True)
                nom_txt = "%s_%s_%d.txt" % (nombre, lang, r)
                with open(os.path.join(txt_dir, nom_txt), "w",
                          encoding="utf-8") as fh:
                    fh.write(ts)
                res["ocr"].append({
                    "doc": nombre, "lang": lang, "ppp": r, "rc": rc,
                    "ms": round(ms, 1), "chars": ns,
                    "cer_tildes": round(cer, 1) if cer is not None else None,
                    "cer_ascii": round(cer_a, 1) if cer_a is not None else None,
                    "tokens": sen["tokens"],
                    "long_media": round(sen["long_media"], 2),
                    "pct_1letra": round(sen["pct_una_letra"], 1),
                    "pct_no_alfa": round(sg.get("pct_no_alfa", 0), 1),
                    "pct_sin_vocal": round(sg.get("pct_sin_vocal", 0), 1),
                    "P9_alucinacion": sen["alucinacion"],
                    "motivo": sen["motivo"],
                    "texto_rel": "texto/" + nom_txt,
                    "muestra": ts.strip()[:70]})
                print("  %-22s %-3s %4d ppp  %4d chars  CER %7.1f %%  "
                      "lm %5.2f  1L %5.1f %%  P9=%s"
                      % (nombre, lang, r, ns, cer if cer is not None else -1,
                         sen["long_media"], sen["pct_una_letra"],
                         "ALUCINA" if sen["alucinacion"] else "ok"))
                os.remove(out)

    # ---- textos legitimos: los reales del repositorio... -------------------
    reales = [
        ("corpus/pdf/tipico_texto.pdf", "PDF de texto del corpus"),
        ("bench/salidas-referencia/pdf/tipico_texto_pdf-to-gs.pdf", "gs pdfwrite"),
        ("bench/salidas-aristas/c8/out/out/s_ink.pdf", "Inkscape SVG->PDF (78 chars)"),
        ("bench/salidas-aristas/c8/out/out/c_epub.pdf", "Calibre EPUB->PDF"),
        ("bench/salidas-aristas/c8/out/out/p_docx.pdf", "Pandoc+xelatex DOCX->PDF"),
        ("bench/salidas-aristas/c8/out/out/entrada.pdf", "LibreOffice DOCX->PDF"),
        ("bench/salidas-aristas/c8/out/out/o/entrada.pdf", "LibreOffice ODT->PDF"),
        ("bench/salidas-aristas/c8/out/out/x/entrada.pdf", "LibreOffice XLSX->PDF"),
        ("bench/salidas-referencia/pdf/alpha_png-to.pdf", "SIN texto: la basura 'FX'"),
    ]
    # ...y los CORTOS fabricados, que son el caso dificil
    cortos = [
        ("ok", ["OK"]),
        ("figura", ["Fig. 1"]),
        ("tabla_2x3", ["Col A   Col B   Col C", "1   2   3", "4   5   6"]),
        ("factura", ["Factura 2026-A/17", "Total: 1.240,50 EUR", "IVA 21 %"]),
        ("formula", ["f(x) = a x^2 + b x + c", "y = m x + n"]),
        ("iniciales", ["J. R. R. T. y C. S. L.", "Ed. 3.a, vol. II"]),
        ("una_letra", ["a b c d e f g h i j k l"]),
        ("lista_corta", ["Uno", "Dos", "Tres", "Cuatro", "Cinco"]),
        ("titular", ["INFORME DE DIGITALIZACION"]),
        ("mixto_corto", ["Anexo B", "Ref. 4/9", "pag. 2 de 3"]),
    ]
    for nom, lineas in cortos:
        p = pdf_minimo(os.path.join(base, "leg_%s.pdf" % nom), lineas)
        reales.append((os.path.relpath(p, RAIZ), "FABRICADO: " + nom))
    for rel, etq in reales:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            res["legitimos"].append({"pdf": rel, "error": "no existe"})
            continue
        ts, err = V._gs_texto(ruta)
        ts = ts or ""
        ns = len("".join(ts.split()))
        sen = V.senal_alucinacion(ts)
        sg = señales(ts)
        res["legitimos"].append({
            "pdf": rel, "etiqueta": etq, "chars": ns, "tokens": sen["tokens"],
            "long_media": round(sen["long_media"], 2),
            "pct_1letra": round(sen["pct_una_letra"], 1),
            "pct_no_alfa": round(sg.get("pct_no_alfa", 0), 1),
            "pct_sin_vocal": round(sg.get("pct_sin_vocal", 0), 1),
            "P9_alucinacion": sen["alucinacion"], "motivo": sen["motivo"],
            "supera_P6": ns >= V.TEXTO_MIN_CHARS,
            "texto": ts.strip()[:400],
            "muestra": ts.strip()[:70]})
        print("  LEG %-34s %4d chars %3d tk  lm %5.2f  1L %5.1f %%  P9=%s %s"
              % (etq[:34], ns, sen["tokens"], sen["long_media"],
                 sen["pct_una_letra"],
                 "ALUCINA" if sen["alucinacion"] else "ok",
                 "(%s)" % sen["motivo"] if sen["motivo"] else ""))
    guardar("p9.json", res)

    # ---- matriz de confusion ----------------------------------------------
    vp = fp = vn = fn = 0
    for r in res["ocr"]:
        if r.get("cer_tildes") is None:
            continue
        ruido = r["cer_tildes"] > 50.0
        if ruido and r["P9_alucinacion"]:
            vp += 1
        elif ruido:
            fn += 1
        elif r["P9_alucinacion"]:
            fp += 1
        else:
            vn += 1
    fpl = sum(1 for r in res["legitimos"]
              if r.get("P9_alucinacion") and r.get("supera_P6"))
    print("\n  CAPAS OCR (verdad = CER con tildes > 50 %%):")
    print("    verdaderos positivos %d · falsos negativos %d · "
          "verdaderos negativos %d · FALSOS POSITIVOS %d" % (vp, fn, vn, fp))
    print("  TEXTOS LEGITIMOS: falsos positivos %d de %d"
          % (fpl, len(res["legitimos"])))

    # ---- señal alternativa: ¿coinciden dos OCR con idiomas distintos? ------
    # Si el motor RECONOCE, spa y eng entregan casi lo mismo; si INVENTA, cada
    # idioma inventa una cosa distinta. Cuesta un segundo pase de OCR.
    por_clave = {}
    for r in res["ocr"]:
        if r.get("texto_rel"):
            por_clave.setdefault((r["doc"], r["ppp"]), {})[r["lang"]] = r
    ac = []
    for (doc, ppp), d in sorted(por_clave.items()):
        if "spa" not in d or "eng" not in d:
            continue
        ta = open(os.path.join(AQUI, d["spa"]["texto_rel"]), encoding="utf-8").read()
        tb = open(os.path.join(AQUI, d["eng"]["texto_rel"]), encoding="utf-8").read()
        s = _similitud(ta, tb)
        cer = d["spa"]["cer_tildes"]
        ac.append({"doc": doc, "ppp": ppp, "acuerdo": round(s, 3),
                   "cer_spa": cer, "cer_eng": d["eng"]["cer_tildes"],
                   "ruido": cer is not None and cer > 50.0})
        print("  ACUERDO spa/eng  %-22s %4d ppp  %.3f   CER spa %7.1f %%  %s"
              % (doc, ppp, s, cer if cer is not None else -1,
                 "RUIDO" if ac[-1]["ruido"] else "ok"))
    res["acuerdo_spa_eng"] = ac
    guardar("p9.json", res)


# ===========================================================================
def cmd_contrato53():
    """El contrato sobre las 53 salidas del patron oro, ahora con CINCO puntos.
    Sin censo el punto 5 no es evaluable: la pregunta es si eso añade FALSOS
    POSITIVOS (no: añade `ok_parcial`, que es otra cosa)."""
    res = []
    for motor in ("proceso", "subproceso"):
        for etq, censo in (("sin censo", None), ("censo vacio (R18 ideal)", "r18")):
            cuenta = {"ok": 0, "aviso": 0, "ok_parcial": 0, "fallo": 0}
            fp = []
            for t in trabajos():
                ped = dict(t["pedido"])
                ped["params"] = dict(ped["params"])
                if os.path.basename(t["salida"]) in COPIA:
                    ped["params"]["copia"] = True
                c = None
                if censo == "r18":
                    d = os.path.dirname(os.path.abspath(t["salida"]))
                    c = {"antes": {d: {}},
                         "despues": {d: {os.path.basename(t["salida"]):
                                         os.path.getsize(t["salida"])}}}
                r = V.verificar(t["salida"], ped, t["entrada"], motor,
                                alfa=True, censo=c)
                cuenta[r["veredicto"]] = cuenta.get(r["veredicto"], 0) + 1
                if r["veredicto"] in ("fallo", "aviso") and t["esperado"] == "ok":
                    fp.append({"salida": os.path.basename(t["salida"]),
                               "veredicto": r["veredicto"],
                               "hallazgos": [h for h in r["hallazgos"]
                                             if h["severidad"] in ("fallo", "aviso")]})
            res.append({"motor": motor, "censo": etq, "cuenta": cuenta,
                        "n_avisos_o_fallos": len(fp), "detalle": fp})
            print("  %-11s %-24s %s   avisos/fallos: %d"
                  % (motor, etq, cuenta, len(fp)))
    guardar("contrato53.json", res)


# ===========================================================================
def cmd_fallos5():
    """Los 5 fallos documentados siguen atrapados con el contrato de CINCO
    puntos. Es una COPIA del caso de medir_gs.py (arnes de V1, que no se toca),
    con el JSON escrito aqui."""
    r = lambda *p: os.path.join(RAIZ, *p)
    tmp = limpio(os.path.join(TMP, "fallos5"))
    f1 = os.path.join(tmp, "falso.avif")
    shutil.copyfile(r("corpus", "imagen", "tipico.png"), f1)
    f5 = os.path.join(tmp, "vacio.mp4")
    open(f5, "wb").close()
    f2 = r("bench", "salidas-referencia", "video", "2pistas_mkv-to-DEFAULT.mp4")
    f3 = r("bench", "salidas-referencia", "imagen", "16bit_tif-to-d8.png")
    f4 = os.path.join(tmp, "redim.png")
    _correr('magick "%s" -resize 800x600 -background black -gravity center '
            '-extent 800x600 "%s"' % (r("corpus", "imagen", "tipico.png"), f4), tmp)
    f4b = os.path.join(tmp, "control.png")
    _correr('magick "%s" "%s"' % (r("corpus", "imagen", "tipico.jpg"), f4b), tmp)
    casos = [
        ("1 PNG con extension .avif", f1, r("corpus", "imagen", "tipico.png"),
         {"destino": "avif", "params": {}}, "fallo"),
        ("2 pierde una pista de audio", f2,
         r("corpus", "video", "patologico_2pistas.mkv"),
         {"destino": "mp4", "params": {}}, "fallo"),
        ("3 degradacion 16 -> 8 bits no pedida", f3,
         r("corpus", "imagen", "patologico_16bit.tif"),
         {"destino": "png", "params": {}}, "fallo"),
        ("4a redimensionado no solicitado", f4, r("corpus", "imagen", "tipico.png"),
         {"destino": "png", "params": {}}, "fallo"),
        ("4b control: mismo JPEG -> PNG sin tocar geometria", f4b,
         r("corpus", "imagen", "tipico.jpg"), {"destino": "png", "params": {}}, "ok"),
        ("5 fichero de 0 bytes como exito", f5, r("corpus", "video", "tipico.mp4"),
         {"destino": "mp4", "params": {}}, "fallo"),
    ]
    res = []
    for motor in ("proceso", "subproceso"):
        for nombre, sal, ent, ped, esp in casos:
            d = os.path.dirname(os.path.abspath(sal))
            censo = {"antes": {d: {}},
                     "despues": {d: {os.path.basename(sal):
                                     os.path.getsize(sal)}}}
            t0 = time.perf_counter()
            v = V.verificar(sal, ped, ent, motor, alfa=True, censo=censo)
            ms = (time.perf_counter() - t0) * 1000
            ok = (v["veredicto"] == "fallo") == (esp == "fallo")
            res.append({"caso": nombre, "motor": motor, "esperado": esp,
                        "veredicto": v["veredicto"], "correcto": ok,
                        "ms": round(ms, 2),
                        "cobertura_completa": all(v["cobertura"].values()),
                        "hallazgos": [h for h in v["hallazgos"]
                                      if h["severidad"] == "fallo"]})
            print("  %-9s %-46s %-8s %s %8.2f ms"
                  % (motor, nombre, v["veredicto"], "OK" if ok else "*** MAL", ms))
    mal = sum(1 for x in res if not x["correcto"])
    print("  discrepancias: %d de %d" % (mal, len(res)))
    guardar("fallos5.json", {"n_mal": mal, "casos": res})


# ===========================================================================
def cmd_familia():
    """¿Es resvg un caso aislado o la punta de una FAMILIA?

    Familia = 'el envase es correcto y el contenido no esta'. Se fabrica un
    miembro por modalidad y se anota QUE lo atrapa: los 5 puntos del contrato,
    alguna regla de fidelidad, o NADA."""
    base = limpio(os.path.join(TMP, "familia"))
    corpus = os.path.join(RAIZ, "corpus")
    res = []

    def anota(nombre, salida, entrada, ped, nota):
        rc4 = V.verificar(salida, ped, entrada)
        rcf = V.verificar_fidelidad(salida, ped, entrada)
        at_c = [h for h in rc4["hallazgos"] if h["severidad"] in ("fallo", "aviso")]
        at_f = [h for h in rcf["hallazgos"] if h["severidad"] in ("fallo", "aviso")]
        res.append({"miembro": nombre, "salida": os.path.relpath(salida, RAIZ),
                    "nota": nota,
                    "contrato": rc4["veredicto"], "fidelidad": rcf["veredicto"],
                    "atrapa_contrato": [h["regla"] + ":" + h["severidad"] for h in at_c],
                    "atrapa_fidelidad": [h["regla"] + ":" + h["severidad"] for h in at_f],
                    "cubierto": bool(at_c or at_f),
                    "hallazgos_contrato": at_c, "hallazgos_fidelidad": at_f})
        print("  %-46s contrato=%-10s %-16s fidelidad=%-10s %s"
              % (nombre[:46], rc4["veredicto"],
                 ",".join(res[-1]["atrapa_contrato"]) or "-",
                 rcf["veredicto"], ",".join(res[-1]["atrapa_fidelidad"]) or "-"))

    # 1. SVG con <text> -> PNG sin fuentes (resvg). EL CASO ORIGINAL.
    c8 = os.path.join(RAIZ, "bench", "salidas-aristas", "c8")
    anota("1. SVG con <text> -> PNG sin fuentes (resvg)",
          os.path.join(c8, "out", "out", "s_resvg.png"),
          os.path.join(c8, "in", "e1.svg"), {"destino": "png", "params": {}},
          "rc=0, PNG valido, 400x200 exacto, cero letras")
    anota("1c. control: el mismo SVG con Inkscape",
          os.path.join(c8, "out", "out", "s_ink.png"),
          os.path.join(c8, "in", "e1.svg"), {"destino": "png", "params": {}},
          "control sano")

    # 2. video con duracion, geometria y codec correctos y TODO NEGRO
    neg = os.path.join(base, "negro.mp4")
    _correr('ffmpeg -y -nostdin -threads 4 -i "%s" -vf "lut=y=0:u=128:v=128" '
            '-c:v libx264 -crf 23 -c:a copy "%s"'
            % (os.path.join(corpus, "video", "trivial.mp4"), neg), base)
    anota("2. video con duracion/geometria correctas y TODO NEGRO",
          neg, os.path.join(corpus, "video", "trivial.mp4"),
          {"destino": "mp4", "params": {}}, "lut=y=0: cada fotograma en negro")

    # 3. PDF de texto -> PDF rasterizado (pierde la capa de texto)
    anota("3. PDF con texto -> PDF rasterizado (pierde el texto)",
          os.path.join(REF, "pdf", "tipico_texto_rasterizado.pdf"),
          os.path.join(corpus, "pdf", "tipico_texto.pdf"),
          {"destino": "pdf", "params": {}}, "del propio patron oro")

    # 4. CSV -> JSON que pierde una COLUMNA
    import csv as _csv
    src = os.path.join(corpus, "datos", "patologico_bom.csv")
    filas = list(_csv.reader(open(src, encoding="utf-8-sig")))
    jso = os.path.join(base, "sin_columna.json")
    cab = filas[0][:-1]
    json.dump([dict(zip(cab, f[:-1])) for f in filas[1:]],
              open(jso, "w", encoding="utf-8"), ensure_ascii=False)
    anota("4. CSV -> JSON que PIERDE la ultima columna",
          jso, src, {"destino": "json", "params": {}},
          "mismas filas, un campo menos")
    jso2 = os.path.join(base, "sin_fila.json")
    json.dump([dict(zip(filas[0], f)) for f in filas[1:-1]],
              open(jso2, "w", encoding="utf-8"), ensure_ascii=False)
    anota("4b. control: CSV -> JSON que pierde una FILA",
          jso2, src, {"destino": "json", "params": {}}, "control")

    # 5. audio estereo con el canal derecho SILENCIADO, a un destino con perdida
    # (la entrada tiene que ser ESTEREO de verdad: con una entrada mono el
    # contrato dispara A2 por cambio de canales y no mide lo que se quiere)
    est = os.path.join(corpus, "audio", "habla_jfk.flac")
    mudo = os.path.join(base, "mudo.mp3")
    _correr('ffmpeg -y -nostdin -threads 4 -i "%s" '
            '-af "pan=stereo|c0=c0|c1=0*c1" -c:a libmp3lame -b:a 192k "%s"'
            % (est, mudo), base)
    anota("5. audio estereo: canal derecho SILENCIADO (destino con perdida)",
          mudo, est, {"destino": "mp3", "params": {"bitrate_bps": 192000}},
          "duracion, canales (2) y frecuencia correctos")
    sano = os.path.join(base, "sano.mp3")
    _correr('ffmpeg -y -nostdin -threads 4 -i "%s" -c:a libmp3lame -b:a 192k "%s"'
            % (est, sano), base)
    anota("5c. control: el mismo estereo sin silenciar nada",
          sano, est, {"destino": "mp3", "params": {"bitrate_bps": 192000}},
          "control sano")
    # el mismo fallo a un destino SIN PERDIDA, donde A4 si tiene con que
    mudo_f = os.path.join(base, "mudo.flac")
    _correr('ffmpeg -y -nostdin -threads 4 -i "%s" '
            '-af "pan=stereo|c0=c0|c1=0*c1" -c:a flac "%s"' % (est, mudo_f), base)
    anota("5b. el MISMO fallo a un destino SIN PERDIDA (flac)",
          mudo_f, est, {"destino": "flac", "params": {}},
          "aqui A4 si puede comparar el PCM")

    # 6. PDF con ANOTACION -> pdfwrite (¿sobrevive la anotacion?)
    anot = os.path.join(base, "con_anotacion.pdf")
    _pdf_con_anotacion(anot)
    sal = os.path.join(base, "sin_anotacion.pdf")
    _correr('gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite '
            '-sOutputFile="%s" "%s"' % (sal, anot), base)
    tiene = {"entrada": b"/Annots" in open(anot, "rb").read(),
             "salida": b"/Annots" in open(sal, "rb").read()
             if os.path.exists(sal) else None}
    print("     /Annots en la entrada: %s · en la salida: %s"
          % (tiene["entrada"], tiene["salida"]))
    anota("6. PDF con anotacion -> gs pdfwrite",
          sal, anot, {"destino": "pdf", "params": {}},
          "/Annots entrada=%s salida=%s" % (tiene["entrada"], tiene["salida"]))
    res[-1]["annots"] = tiene

    guardar("familia.json", res)
    n = len(res)
    cub = sum(1 for r in res if r["cubierto"])
    solo_c = sum(1 for r in res if r["atrapa_contrato"])
    print("\n  miembros probados: %d · atrapados por ALGO: %d · "
          "atrapados por el CONTRATO: %d" % (n, cub, solo_c))
    for r in res:
        if not r["cubierto"]:
            print("    NO ATRAPADO: %s" % r["miembro"])


def _pdf_con_anotacion(ruta):
    """PDF de una pagina con texto y una anotacion /Text. A mano: no hay motor
    de autoria de PDF en esta maquina."""
    cont = b"BT /F1 14 Tf 72 720 Td (Cuerpo del documento) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R "
        b"/Annots [6 0 R] >>",
        b"<< /Length %d >>\nstream\n" % len(cont) + cont + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Annot /Subtype /Text /Rect [200 700 220 720] "
        b"/Contents (NOTA IMPORTANTE FILEXSENTINELA) /Name /Comment >>",
    ]
    buf = bytearray(b"%PDF-1.4\n")
    pos = []
    for i, o in enumerate(objs, 1):
        pos.append(len(buf))
        buf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(buf)
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for p in pos:
        buf += b"%010d 00000 n \n" % p
    buf += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref))
    open(ruta, "wb").write(buf)
    return ruta


# ===========================================================================
def cmd_txtvacio():
    """`gs -sDEVICE=txtwrite` devuelve VACIO de vez en cuando. V1 lo observo
    (verificador-ghostscript.md §5.9) y NO lo reprodujo en 20 intentos. Aqui ha
    vuelto a aparecer solo, en dos ficheros distintos y en dos tandas. Se mide
    la tasa, y se compara la sonda por TUBERIA (-sOutputFile=-, que es la del
    verificador) con la sonda por FICHERO."""
    base = limpio(os.path.join(TMP, "txt"))
    casos = [("fabricado corto",
              pdf_minimo(os.path.join(base, "corto.pdf"),
                         ["Anexo B", "Ref. 4/9", "pag. 2 de 3"])),
             ("corpus tipico_texto.pdf",
              os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")),
             ("patron oro tipico_texto_pdf-to-gs.pdf",
              os.path.join(REF, "pdf", "tipico_texto_pdf-to-gs.pdf"))]
    N = 60
    res = []
    for etq, pdf in casos:
        vac_t = long_t = 0
        vac_f = long_f = 0
        largos_t, largos_f = [], []
        for i in range(N):
            ts, _ = V._gs_texto(pdf)
            n = len("".join((ts or "").split()))
            largos_t.append(n)
            if n == 0:
                vac_t += 1
            long_t = max(long_t, n)
            sal = os.path.join(base, "t%d.txt" % i)
            subprocess.run(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                            "-sDEVICE=txtwrite", "-sOutputFile=" + sal, pdf],
                           capture_output=True, stdin=subprocess.DEVNULL,
                           timeout=120)
            t2 = open(sal, encoding="utf-8", errors="replace").read() \
                if os.path.exists(sal) else ""
            n2 = len("".join(t2.split()))
            largos_f.append(n2)
            if n2 == 0:
                vac_f += 1
            long_f = max(long_f, n2)
            if os.path.exists(sal):
                os.remove(sal)
        res.append({"caso": etq, "n": N,
                    "vacios_tuberia": vac_t, "max_tuberia": long_t,
                    "vacios_fichero": vac_f, "max_fichero": long_f,
                    "distintos_tuberia": sorted(set(largos_t)),
                    "distintos_fichero": sorted(set(largos_f))})
        print("  %-40s tuberia: %d/%d vacios (max %d)   fichero: %d/%d vacios (max %d)"
              % (etq, vac_t, N, long_t, vac_f, N, long_f))
    guardar("txtvacio.json", res)


# ===========================================================================
def cmd_v2():
    """C12: la suite de fidelidad completa, con y sin V2."""
    calibrar()
    tj = []
    for t in trabajos():
        t = dict(t)
        t["pedido"] = dict(t["pedido"])
        t["pedido"]["params"] = dict(t["pedido"]["params"])
        if os.path.basename(t["salida"]) in COPIA:
            t["pedido"]["params"]["copia"] = True
        tj.append(t)
    res = {}
    for etq, activa in (("con V2", True), ("sin V2", False)):
        V.v2(activa)
        t0 = time.perf_counter()
        det = []
        for t in tj:
            r = V.verificar_fidelidad(t["salida"], t["pedido"], t["entrada"])
            det.append({"salida": os.path.basename(t["salida"]),
                        "veredicto": r["veredicto"],
                        "cobertura": r["cobertura"],
                        "ms": {k: round(v, 2) for k, v in r["ms"].items()},
                        "hallazgos": [h for h in r["hallazgos"]
                                      if h["severidad"] != "informativo"]})
        total = (time.perf_counter() - t0) * 1000
        ms_v2 = sum(d["ms"].get("V2", 0) for d in det)
        ver = {}
        for d in det:
            ver[d["veredicto"]] = ver.get(d["veredicto"], 0) + 1
        res[etq] = {"total_ms": round(total, 1), "v2_ms": round(ms_v2, 1),
                    "veredictos": ver,
                    "avisos": sum(1 for d in det if d["hallazgos"]),
                    "detalle": det}
        print("  %-8s suite %9.1f ms   V2 %8.1f ms   veredictos %s"
              % (etq, total, ms_v2, ver))
    a, b = res["con V2"]["total_ms"], res["sin V2"]["total_ms"]
    print("  el interruptor ahorra %.1f ms (%.1f %% de la suite)"
          % (a - b, 100.0 * (a - b) / a))
    V.v2(True)
    guardar("v2.json", res)


# ===========================================================================
def main():
    cmds = {"coste": cmd_coste, "ordenes": cmd_ordenes, "fuga": cmd_fuga,
            "multi": cmd_multi, "i9": cmd_i9, "p9": cmd_p9, "v2": cmd_v2, "txtvacio": cmd_txtvacio, "familia": cmd_familia, "contrato53": cmd_contrato53, "fallos5": cmd_fallos5}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        print("subcomandos: %s" % ", ".join(cmds))
        return 2
    cmds[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    sys.exit(main())



