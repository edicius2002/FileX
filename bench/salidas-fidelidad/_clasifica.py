# -*- coding: utf-8 -*-
"""Fase 3 - clasifica cada camino en INTEGRO / PERDIDA INEVITABLE / DEGRADADO / DESTRUIDO / FALLO.

El criterio decisivo es la CAPACIDAD DEL FORMATO DESTINO:
  - se pierde algo que el destino NO puede representar  -> PERDIDA INEVITABLE
  - se pierde algo que el destino SI puede representar  -> DESTRUIDO (semantico) o DEGRADADO (metrico)
Contrastado contra las 17 perdidas catalogadas de bench/salidas-referencia/referencia.json.
"""
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _sonda import md5_pcm

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-fidelidad\salidas")
RES = os.path.join(RAIZ, r"bench\salidas-fidelidad\resultados.json")

SOPORTA_TEXTO = {"pdf", "docx", "odt", "rtf", "txt", "html", "md", "epub", "xlsx", "csv", "ps", "eps", "svg"}
SOPORTA_ALFA = {"png", "webp", "tiff", "tif", "avif", "gif", "psd", "ico"}
SOPORTA_16BIT = {"png", "tiff", "tif", "psd", "pnm", "ppm"}
SOPORTA_MULTIPISTA = {"mp4", "mkv", "webm", "mov", "avi", "ts", "m4a"}
SOPORTA_AUDIO = SOPORTA_MULTIPISTA | {"mp3", "wav", "flac", "opus", "ogg", "aac"}
RASTER = {"png", "jpg", "jpeg", "webp", "gif", "tiff", "tif", "bmp", "avif", "ppm", "pnm", "pcx"}
SIN_PERDIDA = {"png", "tif", "tiff", "bmp", "ppm", "pnm", "wav", "flac", "psd"}

ORDEN = {"FALLO": 4, "DESTRUIDO": 3, "DEGRADADO": 2, "PERDIDA INEVITABLE": 1, "INTEGRO": 0}
INV = {v: k for k, v in ORDEN.items()}

import re, difflib
from _sonda import texto as _texto, n_imprimibles, identify

# formatos cuya unica razon de ser es transportar texto: si salen sin texto, la
# conversion no ha producido nada utilizable aunque el fichero exista
TEXTO_PURO = {"txt", "docx", "odt", "rtf", "md", "html", "csv"}
LOSSY = {"jpg", "jpeg", "mp3", "aac", "m4a", "opus", "ogg", "webm", "avif", "gif"}

def _norm(s):
    return re.sub(r"[^0-9a-zA-Z]", "", s).lower()

def similitud(a, b):
    """Similitud caracter a caracter del texto del origen frente al del destino.
    Detecta corrupciones silenciosas (ligaduras perdidas, guiones comidos) que un
    centinela sencillo no ve."""
    try:
        ta, tb = _norm(_texto(a)), _norm(_texto(b))
    except Exception:
        return None
    if not ta:
        return None
    # cobertura del texto ORIGEN dentro del destino: inmune a los metadatos que
    # anaden los motores (docxwrite mete 'Normal.dotm Microsoft Office Word ...')
    m = difflib.SequenceMatcher(None, ta, tb)
    return sum(b.size for b in m.get_matching_blocks()) / len(ta)

def orden_tabla(p):
    t = _norm(_texto(p))
    if "ax1128kg" in t or "ax1128" in t:
        return "filas"
    if "ax1bx2cx3" in t:
        return "columnas"
    return "no"


def clasifica(r):
    motivos = []
    if not r.get("ok"):
        p = r.get("pasos", [{}])[-1] if r.get("pasos") else {}
        return "FALLO", [f"paso {p.get('n','?')} ({p.get('motor','?')}->{p.get('destino','?')}) "
                         f"rc={p.get('rc')} {p.get('stderr','')[:160]}"], {}
    ent, fin = r["car_entrada"], r["final"]
    dext = fin["ext"]
    cat = 0
    dim = {}
    fin_path = os.path.join(SAL, r["pasos"][-1]["salida"])
    if dext in ("docx", "odt", "xlsx", "epub", "txt", "md", "html", "rtf", "csv"):
        fin["chars"] = n_imprimibles(_texto(fin_path))   # recalculado sin metadatos del generador
        fin["texto"] = fin["chars"] >= 10

    # --- G3: la firma corresponde al formato pedido
    fam_firma = {"jpg": "jpg", "jpeg": "jpg", "tif": "tiff", "tiff": "tiff", "htm": "html",
                 "docx": "zip(ooxml/odf/epub)", "xlsx": "zip(ooxml/odf/epub)",
                 "odt": "zip(ooxml/odf/epub)", "epub": "zip(ooxml/odf/epub)",
                 "mkv": "mkv/webm", "webm": "mkv/webm", "mp4": "mp4/mov", "mov": "mp4/mov",
                 "m4a": "mp4/mov", "opus": "ogg", "ogg": "ogg", "txt": None, "md": None,
                 "csv": None, "html": None, "rtf": None}
    esperada = fam_firma.get(dext, dext)
    if esperada and fin["firma"] != esperada:
        return "FALLO", [f"firma {fin['firma']} != formato pedido {dext} (regla G3)"], {}

    # --- texto
    if ent.get("texto"):
        dim["texto_entrada"] = ent.get("chars")
        if dext in SOPORTA_TEXTO:
            sim = similitud(os.path.join(RAIZ, r["entrada"]),
                            os.path.join(SAL, r["pasos"][-1]["salida"]))
            dim["similitud_texto"] = sim
            dim["orden_tabla"] = orden_tabla(os.path.join(SAL, r["pasos"][-1]["salida"]))
            if not fin.get("texto"):
                cat = max(cat, 3); motivos.append(
                    f"TEXTO DESTRUIDO: la entrada tenia {ent['chars']} caracteres, la salida {fin.get('chars',0)} "
                    f"y {dext} SI admite capa de texto")
            elif ent.get("centinela") and not fin.get("centinela"):
                cat = max(cat, 3); motivos.append(
                    "TEXTO DESTRUIDO: hay caracteres pero el centinela no sobrevive (texto corrupto)")
            elif sim is not None and sim < 0.80:
                cat = max(cat, 3); motivos.append(
                    f"TEXTO DESTRUIDO: solo el {sim:.0%} del texto coincide con el original")
            elif sim is not None and sim < 0.98:
                cat = max(cat, 2); motivos.append(
                    f"texto alterado: similitud {sim:.1%} con el original (caracteres perdidos o cambiados)")
            else:
                motivos.append(f"texto conservado ({fin.get('chars')} caracteres, similitud {sim:.1%})")
            if ent.get("tabla"):
                ot = dim["orden_tabla"]
                if ot == "columnas":
                    cat = max(cat, 2); motivos.append(
                        "la tabla sale en orden de COLUMNAS, no de filas: la estructura tabular se pierde")
                elif ot == "no":
                    cat = max(cat, 2); motivos.append("la tabla no se recupera del texto extraido")
            dim["texto_salida"] = fin.get("chars")
        else:
            cat = max(cat, 1); motivos.append(
                f"capa de texto perdida: {dext} no puede representarla (perdida inevitable)")

    # --- imagen
    ei, fi = ent.get("img"), fin.get("img")
    if ei and fi:
        if (ei["w"], ei["h"]) != (fi["w"], fi["h"]):
            cat = max(cat, 2); motivos.append(f"geometria {ei['w']}x{ei['h']} -> {fi['w']}x{fi['h']} (regla I1)")
        if ei["prof"] > fi["prof"]:
            if dext in SOPORTA_16BIT:
                culpable = next((p["destino"] for p in r["pasos"]
                                 if p.get("car", {}).get("img") and p["car"]["img"]["prof"] < ei["prof"]), "?")
                cat = max(cat, 2); motivos.append(
                    f"profundidad {ei['prof']}->{fi['prof']} bits y {dext} admite {ei['prof']}: la pierde el "
                    f"salto intermedio a {culpable} (regla I4, evitable con otro intermedio)")
            else:
                cat = max(cat, 1); motivos.append(
                    f"profundidad {ei['prof']}->{fi['prof']} bits, inevitable en {dext} (regla I5)")
        if ei["espacio"] != fi["espacio"]:
            cat = max(cat, 2); motivos.append(f"espacio de color {ei['espacio']} -> {fi['espacio']} (regla I9)")
        dim["colores"] = (ei["colores"], fi["colores"])
        if ei["colores"] <= 256 and fi["colores"] > ei["colores"]:
            cat = max(cat, 2); motivos.append(
                f"grafismo: {ei['colores']} colores -> {fi['colores']} (regla I8, el codificador inventa tonos)")
    # alfa
    am = ent.get("alfa_min")
    if am is not None and am < 0.999:
        fam = fin.get("alfa_min")
        if dext in SOPORTA_ALFA:
            if fam is None or fam > 0.999:
                cat = max(cat, 3); motivos.append(
                    f"ALFA DESTRUIDO: alfa no trivial (min {am:.3f}) y {dext} lo admite (regla I2)")
            else:
                motivos.append(f"alfa no trivial conservado (min {fam:.3f})")
        else:
            cat = max(cat, 1); motivos.append(f"alfa perdido: {dext} no lo admite (perdida inevitable)")

    # --- audio / video
    ea, fa = ent.get("av"), fin.get("av")
    if ea:
        if ea["n_a"] > 0:
            n_fin = fa["n_a"] if fa else 0
            if dext in SOPORTA_AUDIO:
                if n_fin == 0:
                    cat = max(cat, 3); motivos.append(
                        f"AUDIO DESTRUIDO: {ea['n_a']} pista(s) -> 0 y {dext} admite audio")
                elif n_fin < ea["n_a"]:
                    cat = max(cat, 3); motivos.append(
                        f"PISTAS DESTRUIDAS: {ea['n_a']} -> {n_fin} y {dext} admite varias (perdida 12 del catalogo)")
            else:
                cat = max(cat, 1); motivos.append(f"audio perdido: {dext} no lo admite (perdida inevitable)")
        if fa and ea.get("n_v", 0) > 0 and fa.get("n_v", 0) > 0:
            if (ea["w"], ea["h"]) != (fa["w"], fa["h"]):
                cat = max(cat, 2); motivos.append(f"resolucion {ea['w']}x{ea['h']} -> {fa['w']}x{fa['h']}")
        recorta = any("-t" in (p.get("args", {}).get("extra") or []) for p in r["pasos"])
        if fa and ea.get("dur") and fa.get("dur") and not recorta:
            d = abs(ea["dur"] - fa["dur"])
            dim["delta_dur_ms"] = round(d * 1000, 1)
            if d > 0.05 and dext != "gif":
                cat = max(cat, 2); motivos.append(f"duracion {ea['dur']:.3f} -> {fa['dur']:.3f} s")
        elif recorta:
            motivos.append("duracion recortada a proposito con -t (parametro de la prueba, no perdida)")
        # PCM: generacion perdida evitable cuando el destino es sin perdida
        if ea.get("n_a") and fa and fa.get("n_a") and dext in ("wav", "flac"):
            ent_p = os.path.join(RAIZ, r["entrada"])
            fin_p = os.path.join(SAL, r["pasos"][-1]["salida"])
            a1, a2 = md5_pcm(ent_p), md5_pcm(fin_p)
            dim["pcm"] = (a1, a2)
            if a1 and a2 and a1 != a2:
                cat = max(cat, 2); motivos.append(
                    f"PCM distinto ({a1} -> {a2}) con destino sin perdida ({dext}): "
                    f"un salto intermedio con perdida introdujo una generacion evitable")
            elif a1 and a1 == a2:
                motivos.append(f"PCM identico ({a1}): la cadena es exacta")
        if fa and ea.get("sr") and fa.get("sr") and ea["sr"] != fa["sr"]:
            if dext in ("opus", "ogg"):
                cat = max(cat, 1); motivos.append(f"frecuencia {ea['sr']} -> {fa['sr']} Hz (Opus obliga a 48 kHz)")
            else:
                cat = max(cat, 2); motivos.append(f"frecuencia {ea['sr']} -> {fa['sr']} Hz")

    # --- el destino existe para llevar texto y no lleva ninguno
    if dext in TEXTO_PURO and not fin.get("texto"):
        if fin["bytes"] < 64:
            cat = max(cat, 4); motivos.insert(0,
                f"el destino {dext} solo sirve para transportar texto y la salida esta vacia "
                f"({fin['bytes']} bytes): no hay conversion")
        else:
            cat = max(cat, 3); motivos.insert(0,
                f"DESTRUIDO: {dext} de {fin['bytes']} bytes SIN una sola linea de texto del documento "
                f"(solo metadatos del generador)")

    # --- paleta intermedia
    exts_i = [p["destino"] for p in r["pasos"]][:-1]
    if "gif" in exts_i and dext not in ("gif",):
        cat = max(cat, 2)
        motivos.append("paso intermedio por GIF: paleta de <=256 colores por fotograma, irreversible")

    # --- destino con perdida: lo que se pierda ahi es inevitable
    if dext in LOSSY and cat == 0:
        cat = max(cat, 1)
        motivos.append(f"destino {dext} es un formato con perdida: la recodificacion es inevitable")

    # --- imagen -> PDF: caja de pagina (regla P7)
    if dext == "pdf" and ent.get("img"):
        info, _e = identify(fin_path)
        if info:
            mm_w = info["w"] * 25.4 / 72
            dim["pagina_mm"] = round(mm_w, 1)
            if mm_w > 500:
                cat = max(cat, 2)
                motivos.append(f"caja de pagina de {mm_w:.0f} mm de ancho: ImageMagick mapeo 1 px -> 1 pt "
                               f"por no declararse densidad (regla P7)")

    # --- rasterizacion intermedia
    exts = [p["destino"] for p in r["pasos"]]
    inter = exts[:-1]
    r["rasteriza_intermedio"] = any(x in RASTER for x in inter)
    if r["rasteriza_intermedio"] and ent.get("texto") and dext in SOPORTA_TEXTO:
        motivos.append("el camino rasteriza en un paso intermedio pudiendo no hacerlo")

    if not motivos:
        motivos.append("sin perdida detectable en las sondas aplicadas")
    return INV[cat], motivos, dim


if __name__ == "__main__":
    res = json.load(open(RES, encoding="utf-8"))
    orden = {c: i for i, c in enumerate(["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"])}
    res.sort(key=lambda r: r["id"])
    cuenta = {}
    filas = []
    for r in res:
        cat, mot, dim = clasifica(r)
        r["categoria"] = cat
        r["motivos"] = mot
        r["dim"] = dim
        cuenta[cat] = cuenta.get(cat, 0) + 1
        cadena = " -> ".join([r["car_entrada"]["ext"]] + [p["destino"] for p in r.get("pasos", [])])
        motores = "+".join(p["motor"] for p in r.get("pasos", []))
        ms = sum(p.get("ms", 0) for p in r.get("pasos", []))
        filas.append((r["id"], r["estrato"], cadena, motores, len(r.get("pasos", [])), cat, ms, "; ".join(mot)))
        print(f"{r['id']:4} {cat:19} {cadena:38} {motores:22} {'; '.join(mot)[:150]}")
    print()
    tot = len(res)
    for c in ["INTEGRO", "PERDIDA INEVITABLE", "DEGRADADO", "DESTRUIDO", "FALLO"]:
        n = cuenta.get(c, 0)
        print(f"{c:20} {n:3}  {100*n/tot:5.1f} %")
    print("total", tot)
    json.dump(res, open(os.path.join(RAIZ, r"bench\salidas-fidelidad\clasificado.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
