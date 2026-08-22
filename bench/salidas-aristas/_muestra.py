# -*- coding: utf-8 -*-
"""E1 / Nivel 3 - MUESTREO ALEATORIO ESTRATIFICADO CON EJECUCION.

Poblacion: las 40.252 aristas del grafo instalado cuyas DOS semiaristas se han
ejecutado con exito (marco.json). Aqui se mide el residuo: aristas cuyas dos mitades
funcionan por separado y que aun asi no producen una conversion.

Criterio de NOMINAL (y solo estos tres; una degradacion NO es nominal):
  N1 el proceso falla, agota el timeout, o no deja fichero / deja 0 bytes;
  N2 el fichero existe pero su FIRMA REAL no es la del formato pedido
     (punto 1 del contrato de verificador.py);
  N3 el fichero existe y es del formato pedido pero esta VACIO DE CONTENIDO
     (0 flujos, 0 pixeles) o es un volcado absurdo (destino textual >100x la entrada).

Estratos: motor x (misma familia / distinta familia), familia deducida de la semilla
que consiguio escribir cada formato en el censo de semiaristas.

Uso: python _muestra.py <n_general> <n_pdf> <semilla_aleatoria>
Escribe muestra.json
"""
import os, sys, json, time, random, shutil, subprocess, hashlib

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
POOL = os.path.join(SAL, "pool")
PIN = os.path.join(POOL, "in")
TMP = os.path.join(SAL, "tmp5")
VERIF = os.path.join(SAL, "verificador_congelado.py")
sys.path.insert(0, SAL)
from _semi import corre, inv_ffmpeg, inv_magick, limpia
from _semi_in import corpus_por_ext

TEXTUAL = {"txt", "csv", "json", "xml", "html", "htm", "md", "srt", "vtt", "ass",
           "ssa", "sub", "ttml", "lrc", "scc"}


def familias_empiricas():
    s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
    fam = {}
    for k, v in s1.items():
        m, b = k.split("|")
        if v["vivo"]:
            fam.setdefault(b, v["intentos"][-1]["semilla"])
        elif s2.get(k, {}).get("vivo"):
            fam.setdefault(b, s2[k]["revivida_por"])
    norm = {"video": "video", "video_cif": "video", "audio": "audio", "audio48": "audio",
            "imagen": "imagen", "jpeg_exif": "imagen", "png_alfa": "imagen",
            "tif16": "imagen", "subtitulo": "subtitulo", "documento": "documento"}
    return {k: norm.get(v, "otro") for k, v in fam.items()}


def ruta_entrada(a, corp):
    p = os.path.join(PIN, "m." + a)
    if os.path.exists(p):
        return p
    import glob
    g = sorted(glob.glob(os.path.join(PIN, "m." + a + "*")))
    if g:
        return g[0]
    return corp.get(a)


import verificador_congelado as V   # el verificador se usa EN PROCESO (0,37 ms)

# --- N2 solo es evaluable en el vocabulario CERRADO de firmas que sabe leer el
# verificador: bmp flac gif gzip jpeg matroska mp3 ogg pdf png tiff zip webp wav
# avi + la familia ISO-BMFF + 'texto'. Fuera de el, N2 NO SE APLICA y se declara.
CLASE = {}
for _f, _v in (
    ("png", "png png8 png00 png24 png32 png48 png64"),
    ("gif", "gif gif87"),
    ("jpeg", "jpg jpeg jpe jfif jpg2"),
    ("tiff", "tif tiff tiff64 ptif group4 g3 g4 fax"),
    ("bmp", "bmp bmp2 bmp3 dib"),
    ("pdf", "pdf"),
    ("webp", "webp"),
    ("wav", "wav w64"),
    ("avi", "avi"),
    ("matroska", "mkv webm mka mks"),
    ("isobmff", "mp4 m4v m4a m4b mov 3gp 3g2 f4v ismv isma mj2 avif heic heif"),
    ("flac", "flac"),
    ("mp3", "mp3 mp2 m1a m2a mpa"),
    ("ogg", "ogg oga ogv opus spx ogx"),
    ("zip", "zip epub docx xlsx pptx odt ods odp cbz jar"),
    ("gzip", "gz tgz"),
    ("texto", "txt csv json xml html htm md srt vtt ass ssa ttml lrc ffmeta y4m "
               "svg tex rtf ps eps sub scc jss js chk"),
):
    for _e in _v.split():
        CLASE[_e] = _f
# clase a la que pertenece cada FIRMA devuelta por el sondeo
FIRMA_CLASE = {"mp4": "isobmff", "mov": "isobmff", "m4a": "isobmff", "3gp": "isobmff",
               "avif": "isobmff", "heif": "isobmff", "isobmff": "isobmff",
               "riff": None, "desconocido": None, "vacio": None, "ilegible": None}
INDEF = {"desconocido", "riff", None, ""}


def juzga(rc, tam, tam_ent, destino, son, ver):
    """Devuelve (nominal, categoria, motivo, n2_evaluable). Criterio N1/N2/N3."""
    if rc != 0 or tam <= 0:
        return True, "FALLO", "rc=%d bytes=%d" % (rc, tam), False
    firma = (son.get("firma") or "").lower()
    esp = CLASE.get(destino)
    fcl = FIRMA_CLASE.get(firma, firma)
    n2 = (esp is not None) and (firma not in INDEF) and (fcl is not None)
    if n2 and fcl != esp:
        return True, "DESTRUIDO", "N2 firma real '%s' != formato pedido '%s' (clase %s vs %s)" % (
            firma, destino, fcl, esp), True
    cat = son.get("categoria")
    if cat == "av" and son.get("n_pistas", 1) == 0:
        return True, "DESTRUIDO", "N3 contenedor sin ninguna pista", n2
    if cat == "imagen" and (son.get("ancho", 1) == 0 or son.get("alto", 1) == 0):
        return True, "DESTRUIDO", "N3 imagen de 0 pixeles", n2
    if destino in TEXTUAL and tam_ent > 0 and tam > 100 * tam_ent:
        return True, "DESTRUIDO", "N3 volcado absurdo: %d B desde %d B" % (tam, tam_ent), n2
    avisos = [h for h in ver.get("hallazgos", []) if h.get("severidad") in ("fallo", "aviso")]
    marca = "" if n2 else " [N2 no evaluable: firma '%s' fuera del vocabulario]" % (firma or "-")
    if not avisos:
        return False, "INTEGRO", marca.strip(), n2
    return False, "DEGRADADO", ("; ".join(
        "%s:%s" % (h.get("regla", ""), h.get("mensaje", "")) for h in avisos)[:220]) + marca, n2


def ejecuta(lote, corp, etiqueta):
    limpia(TMP)
    out = []
    t0 = time.time()
    for i, (a, b, ms) in enumerate(lote):
        ent = ruta_entrada(a, corp)
        if ent is None:
            out.append({"a": a, "b": b, "motores": ms, "estado": "sin_semilla"})
            continue
        motor = "imagemagick" if "imagemagick" in ms.split(",") else ms.split(",")[0]
        inv = inv_magick if motor == "imagemagick" else inv_ffmpeg
        sal = os.path.join(TMP, "z%04d.%s" % (i, b))
        rc, err, msx = corre(inv(ent, b, sal), 45)
        cands = sorted(x for x in os.listdir(TMP) if x.startswith("z%04d" % i))
        tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
        real = os.path.join(TMP, cands[0]) if cands else None
        son, ver = {}, {}
        if rc == 0 and tam > 0 and real:
            try:
                son = V.sondear(real, "proceso")
            except Exception as e:
                son = {"error": str(e)[:150]}
            try:
                ver = V.verificar(real, {}, ent)
            except Exception as e:
                ver = {"error": str(e)[:150]}
        nom, cat, mot, n2ev = juzga(rc, tam, os.path.getsize(ent), b, son, ver)
        out.append({"a": a, "b": b, "motores": ms, "motor": motor, "estrato": etiqueta,
                    "rc": rc, "bytes": tam, "bytes_entrada": os.path.getsize(ent),
                    "ms": round(msx, 1), "nominal": nom, "categoria": cat,
                    "motivo": mot, "firma": son.get("firma"), "n2_evaluable": n2ev,
                    "veredicto_verif": ver.get("veredicto", ""),
                    "err": err.replace("\n", " ")[-200:] if rc != 0 else ""})
        for c in cands:
            try:
                os.remove(os.path.join(TMP, c))
            except OSError:
                pass
        if i % 25 == 0:
            print("   %s %d/%d (%.0fs)" % (etiqueta, i, len(lote), time.time() - t0), flush=True)
    return out


if __name__ == "__main__":
    ng = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    npdf = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    sem = int(sys.argv[3]) if len(sys.argv) > 3 else 20260821
    random.seed(sem)

    marco = [tuple(r.split("|")[0].split(">")) + (r.split("|")[1],)
             for r in json.load(open(os.path.join(SAL, "marco.json"), encoding="utf-8"))["marco"]]
    fam = familias_empiricas()
    corp = corpus_por_ext()

    def estrato(t):
        a, b, ms = t
        motor = "imagemagick" if "imagemagick" in ms.split(",") else ms.split(",")[0]
        misma = fam.get(a, "?") == fam.get(b, "?") and fam.get(a, "?") != "?"
        return "%s|%s" % (motor, "misma-familia" if misma else "distinta-familia")

    porestrato = {}
    for t in marco:
        porestrato.setdefault(estrato(t), []).append(t)
    print("ESTRATOS DEL MARCO (%d aristas)" % len(marco))
    for k in sorted(porestrato):
        print("   %-32s %6d  (%.1f %%)" % (k, len(porestrato[k]), 100 * len(porestrato[k]) / len(marco)))

    # asignacion proporcional, minimo 12 por estrato
    plan = {}
    for k, v in porestrato.items():
        plan[k] = max(12, round(ng * len(v) / len(marco)))
    plan = {k: min(v, len(porestrato[k])) for k, v in plan.items()}
    print("\nPLAN DE MUESTREO (n objetivo %d -> %d):" % (ng, sum(plan.values())))
    for k in sorted(plan):
        print("   %-32s n=%d" % (k, plan[k]))

    lote = []
    asign = {}
    for k, n in plan.items():
        sel = random.sample(porestrato[k], n)
        asign[k] = sel
        lote += sel

    pdfs = [t for t in marco if t[0] == "pdf" or t[1] == "pdf"]
    lpdf = random.sample(pdfs, min(npdf, len(pdfs)))
    print("\nestrato PDF (prioritario): %d de %d aristas que tocan pdf" % (len(lpdf), len(pdfs)))

    testigo = os.path.join(SAL, "_testigo.py")
    subprocess.run([sys.executable, testigo, "antes-muestra"], stdin=subprocess.DEVNULL)
    res = ejecuta(lote, corp, "general")
    for k, sel in asign.items():
        for t in sel:
            for r in res:
                if (r.get("a"), r.get("b"), r.get("motores")) == t:
                    r["estrato"] = k
    res_pdf = ejecuta(lpdf, corp, "pdf")
    subprocess.run([sys.executable, testigo, "despues-muestra"], stdin=subprocess.DEVNULL)

    json.dump({"semilla_aleatoria": sem, "plan": plan,
               "tam_estratos": {k: len(v) for k, v in porestrato.items()},
               "marco": len(marco), "general": res, "pdf": res_pdf,
               "pdf_poblacion": len(pdfs)},
              open(os.path.join(SAL, "muestra.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)

    for nom, r in (("GENERAL", res), ("PDF", res_pdf)):
        n = len([x for x in r if "nominal" in x])
        k = sum(1 for x in r if x.get("nominal"))
        print("\n%s: %d/%d nominales = %.1f %%" % (nom, k, n, 100 * k / max(1, n)))
        from collections import Counter
        print("   ", dict(Counter(x.get("categoria") for x in r)))
