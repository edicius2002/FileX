# -*- coding: utf-8 -*-
"""¿Cuántas `nominal` recupera arreglar EL VERIFICADOR, sin tocar el motor?

El sondeo deja aristas en `nominal` cuyo `rc` es 0 y cuyo fichero de salida es
correcto para `ffprobe`: lo que falla es la SONDA EN PROCESO del verificador.
Este arnés mide exactamente cuántas, parcheando **en memoria** las dos lecturas
defectuosas —no se toca `filex/verificador.py`, que es de otro agente— y
volviendo a pasar las mismas aristas por el mismo `FileX.convertir()`.

Los dos defectos, MEDIDOS:

1. **`.mov` → 0 pistas.** `_isobmff` se queda con el ÚLTIMO `hdlr` de cada
   `trak`. QuickTime escribe un SEGUNDO `hdlr` dentro de `minf` con el
   manejador de DATOS (`url `), así que las tres pistas de un `.mov` de ffmpeg
   se clasifican como «otro» y `n_pistas` sale 0. MP4 no lleva ese segundo
   `hdlr` y por eso el mismo fichero remuxado a `.mp4` se lee bien.

2. **`.ogg` de Vorbis → duración ×0,91875.** `_ogg` divide el gránulo por
   48000 siempre. Es correcto para Opus (que siempre entrega a 48 kHz) y falso
   para Vorbis, cuyo gránulo va a la frecuencia del propio flujo: un Vorbis de
   8,000 s a 44,1 kHz se lee como 7,350 s (= 8 × 44100/48000).

Uso:  python bench/salidas-sondeo-ff/reparacion_verificador.py <dir_trabajo>
"""
import json
import os
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import verificador as V                    # noqa: E402
from filex.grafo import Grafo                         # noqa: E402
from filex.nucleo import FileX                        # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sondear_ff import pedido_de, sonda_ffprobe       # noqa: E402

TIMEOUT = 300.0
_ORIGINAL = V.sondear_en_proceso


# --------------------------------------------------------------- parche MOV
def _isobmff_parcheado(fh, ruta):
    """`filex/verificador.py:_isobmff` COPIADO CON UN SOLO CAMBIO.

    El cambio son las tres líneas marcadas con `# <<< PARCHE` en la rama
    `hdlr`: se conserva el PRIMER `hdlr` del `trak` en vez del último. Todo lo
    demás es literal, para que lo que se mide sea el efecto de ese cambio y no
    el de una reimplementación.
    """
    d = {"categoria": "av", "pistas": [], "n_video": 0, "n_audio": 0,
         "n_subtitulo": 0}
    estado = {"handler": None, "timescale": 1000, "dur_mov": 0}

    def recorre(ini, fin, prof=0):
        if prof > 6:
            return
        fh.seek(ini)
        for tipo, di, df in V._cajas(fh, fin, prof):
            if tipo == b"mvhd":
                fh.seek(di)
                c = fh.read(min(df - di, 120))
                ver = c[0]
                if ver == 1:
                    ts, dur = V._u32(c, 20), struct.unpack_from(">Q", c, 24)[0]
                else:
                    ts, dur = V._u32(c, 12), V._u32(c, 16)
                if ts:
                    d["duracion_s"] = round(dur / ts, 4)
            elif tipo == b"trak":
                estado["handler"] = None
                estado["pista"] = {}
                recorre(di, df, prof + 1)
                p = estado.get("pista") or {}
                h = estado["handler"]
                if h == b"vide":
                    p["tipo"] = "video"
                    d["n_video"] += 1
                elif h == b"soun":
                    p["tipo"] = "audio"
                    d["n_audio"] += 1
                elif h in (b"subt", b"sbtl", b"text"):
                    p["tipo"] = "subtitulo"
                    d["n_subtitulo"] += 1
                else:
                    p["tipo"] = "otro"
                if p.get("tipo") != "otro":
                    d["pistas"].append(p)
            elif tipo == b"tkhd":
                fh.seek(di)
                c = fh.read(min(df - di, 92))
                ver = c[0]
                o = 84 if ver == 1 else 72
                if len(c) >= o + 8:
                    an = V._u32(c, o) / 65536.0
                    al = V._u32(c, o + 4) / 65536.0
                    if an > 0 and al > 0:
                        estado.setdefault("pista", {})["ancho"] = int(round(an))
                        estado["pista"]["alto"] = int(round(al))
            elif tipo == b"mdhd":
                fh.seek(di)
                c = fh.read(min(df - di, 40))
                ver = c[0]
                if ver == 1:
                    ts, dur = V._u32(c, 20), struct.unpack_from(">Q", c, 24)[0]
                else:
                    ts, dur = V._u32(c, 12), V._u32(c, 16)
                if ts:
                    estado.setdefault("pista", {})["duracion_s"] = round(dur / ts, 4)
                    estado["pista"]["sample_rate_mdhd"] = ts
            elif tipo == b"hdlr":
                if estado.get("handler") is None:            # <<< PARCHE
                    fh.seek(di + 8)                          # <<< PARCHE
                    estado["handler"] = fh.read(4)           # <<< PARCHE
            elif tipo == b"stsd":
                fh.seek(di + 8)
                c = fh.read(min(df - di - 8, 200))
                if len(c) >= 12:
                    codec = c[4:8].decode("latin-1").strip()
                    p = estado.setdefault("pista", {})
                    p["codec"] = codec
                    if estado["handler"] == b"vide" and len(c) >= 40:
                        p["ancho"] = V._u16(c, 32)
                        p["alto"] = V._u16(c, 34)
                        p["profundidad_bits"] = V._u16(c, 74) if len(c) >= 76 else None
                    elif estado["handler"] == b"soun" and len(c) >= 32:
                        p["canales"] = V._u16(c, 24)
                        p["profundidad_bits"] = V._u16(c, 26)
                        p["sample_rate"] = V._u32(c, 32) >> 16
            elif tipo in V.CONTENEDORAS:
                recorre(di, df, prof + 1)

    tam = os.path.getsize(ruta)
    recorre(0, tam)
    d["n_pistas"] = len(d["pistas"])
    d["formato"] = "mp4"
    d["bitrate_bps"] = int(tam * 8 / d["duracion_s"]) if d.get("duracion_s") else None
    return d


def sondear_parcheado(ruta):
    d = _ORIGINAL(ruta)
    # --- 1. ISO-BMFF con 0 pistas (es lo que le pasa a TODO `.mov`) ---------
    if (d.get("firma") in ("mov", "mp4", "m4a") and d.get("categoria") == "av"
            and d.get("n_pistas") == 0):
        try:
            with open(ruta, "rb") as fh:
                nuevo = _isobmff_parcheado(fh, ruta)
        except Exception:
            nuevo = None
        if nuevo and nuevo["n_pistas"]:
            d.update(nuevo)
    # --- 2. OGG de Vorbis: el gránulo NO va a 48 kHz ------------------------
    if d.get("formato") == "ogg" and d.get("duracion_s"):
        p = (d.get("pistas") or [{}])[0]
        if p.get("codec") == "vorbis" and p.get("sample_rate"):
            d["duracion_s"] = round(d["duracion_s"] * 48000.0 / p["sample_rate"], 4)
            if d.get("bitrate_bps"):
                d["bitrate_bps"] = int(os.path.getsize(ruta) * 8 / d["duracion_s"])
    return d


def main():
    trabajo = os.path.abspath(sys.argv[1])
    with open(os.path.join(trabajo, "resultados.json"), encoding="utf-8") as fh:
        previo = json.load(fh)["aristas"]
    with open(os.path.join(trabajo, "fuentes", "fuentes.json"), encoding="utf-8") as fh:
        fuentes = json.load(fh)["fuentes"]

    nominales = [k for k, v in previo.items() if v["estado"] == "nominal"]
    salidas = os.path.join(trabajo, "reparadas")
    os.makedirs(salidas, exist_ok=True)

    fx = FileX()
    aristas = {f"{a.origen}>{a.destino}": a for a in fx.grafo.aristas
               if a.motor == "ffmpeg"}

    V.sondear_en_proceso = sondear_parcheado          # el parche, en memoria
    out = {}
    for clave in nominales:
        a = aristas[clave]
        fx.grafo = Grafo([a])
        dst = os.path.join(salidas, f"{a.origen}2{a.destino}.{a.destino}")
        if os.path.isfile(dst):
            os.remove(dst)
        conv = fx.convertir(fuentes[a.origen], dst, pedido_de(a.destino),
                            timeout=TIMEOUT)
        s = conv.saltos[0] if conv.saltos else None
        ok = bool(conv.ok) and s is not None and s.rc == 0 and s.veredicto != "fallo"
        out[clave] = {
            "antes": previo[clave]["veredicto"] or ("rc=%s" % previo[clave]["rc"]),
            "ahora": s.veredicto if s else "",
            "rc": s.rc if s else None,
            "recuperada": ok,
            "reglas": [h.get("regla") for h in (s.hallazgos if s else [])
                       if h.get("severidad") == "fallo"],
            "ms": round(s.ms, 1) if s else None,
        }
        print("%-11s %-10s -> %-10s %s" % (clave, out[clave]["antes"],
                                           out[clave]["ahora"],
                                           "RECUPERADA" if ok else ""), flush=True)
        if os.path.isfile(dst):
            os.remove(dst)
    V.sondear_en_proceso = _ORIGINAL

    with open(os.path.join(trabajo, "reparacion.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("recuperadas %d de %d" % (sum(1 for v in out.values() if v["recuperada"]),
                                    len(out)))


if __name__ == "__main__":
    main()
