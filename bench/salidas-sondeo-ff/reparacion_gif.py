# -*- coding: utf-8 -*-
"""`-map 0` y el muxer `gif` se destruyen mutuamente. Cuánto cuesta y qué lo arregla.

`motores.FFmpeg.orden()` añade `-map 0` a todo destino que no sea de categoría
audio — GIF incluido. El muxer `gif` **no tiene códec de audio por defecto**,
así que arrastrar las pistas de audio de la entrada aborta la conversión con
`AVERROR_ENCODER_NOT_FOUND`. Las cuatro aristas vídeo→gif `sin_sondear` fallan,
y **`mp4→gif`, que el catálogo declara `real`, solo pasaba porque
`corpus/video/trivial.mp4` no tiene pista de audio**.

Este arnés mide las tres cosas sin tocar `filex/motores.py`:
  A) `mp4→gif` con un MP4 que sí tiene audio, con el código de hoy;
  B) las cinco aristas con `-map 0:v:0` en vez de `-map 0`;
  C) que el resto de destinos no cambia (el parche solo toca `d == "gif"`).

Uso:  python bench/salidas-sondeo-ff/reparacion_gif.py <dir_trabajo>
"""
import json
import os
import statistics
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import motores as M                        # noqa: E402
from filex.grafo import Grafo                         # noqa: E402
from filex.nucleo import FileX                        # noqa: E402

TIMEOUT = 300.0
_ORDEN = M.FFmpeg.orden


def orden_parcheada(self, entrada, salida, pedido, *, timeout=None):
    """La orden de hoy con UNA sustitución: `-map 0` -> `-map 0:v:0` para GIF."""
    argv = _ORDEN(self, entrada, salida, pedido, timeout=timeout)
    if os.path.splitext(salida)[1].lower() == ".gif":
        for i in range(len(argv) - 1):
            if argv[i] == "-map" and argv[i + 1] == "0":
                argv[i + 1] = "0:v:0"
    return argv


def pasada(fx, aristas, fuentes, dirsal, n=3, pedido=None):
    out = {}
    for clave, a in aristas.items():
        fx.grafo = Grafo([a])
        med, ultimo = [], None
        for _ in range(n):
            dst = os.path.join(dirsal, f"{a.origen}2{a.destino}.{a.destino}")
            if os.path.isfile(dst):
                os.remove(dst)
            conv = fx.convertir(fuentes[a.origen], dst, dict(pedido or {}),
                                timeout=TIMEOUT)
            s = conv.saltos[0] if conv.saltos else None
            if s:
                med.append(s.ms)
            ultimo = (conv, s, dst)
        conv, s, dst = ultimo
        ok = bool(conv.ok) and s is not None and s.rc == 0 and s.veredicto != "fallo"
        out[clave] = {"estado": "real" if ok else "nominal",
                      "rc": s.rc if s else None,
                      "veredicto": s.veredicto if s else "",
                      "ms": round(statistics.median(med), 1) if med else None,
                      "bytes": os.path.getsize(dst) if os.path.isfile(dst) else 0,
                      "motivo": "" if ok else (conv.motivo or "")[:160]}
        print("  %-11s %-8s rc=%-11s ver=%-10s %sms %s"
              % (clave, out[clave]["estado"], out[clave]["rc"],
                 out[clave]["veredicto"], out[clave]["ms"], out[clave]["motivo"][:60]),
              flush=True)
    return out


def main():
    trabajo = os.path.abspath(sys.argv[1])
    with open(os.path.join(trabajo, "fuentes", "fuentes.json"), encoding="utf-8") as fh:
        fuentes = json.load(fh)["fuentes"]
    dirsal = os.path.join(trabajo, "gif")
    os.makedirs(dirsal, exist_ok=True)

    fx = FileX()
    todas = {f"{a.origen}>{a.destino}": a for a in fx.grafo.aristas
             if a.motor == "ffmpeg" and a.destino == "gif"}
    print("aristas video-gif declaradas:", len(todas))
    print("--- A) con el código de hoy (`-map 0`), fuentes CON audio")
    antes = pasada(fx, todas, fuentes, dirsal)
    print("--- B) con `-map 0:v:0` solo para gif")
    M.FFmpeg.orden = orden_parcheada
    despues = pasada(fx, todas, fuentes, dirsal)

    # C) `-map 0:v:0` Y ADEMAS declarando la escala que el propio motor aplica.
    #    `orden()` mete `scale=320:-1` sin decírselo al contrato, y el punto 4
    #    lo atrapa como REDIMENSIONADO NO SOLICITADO — que es exactamente para
    #    lo que se escribió ese punto. Declararlo es la otra mitad del arreglo.
    print("--- C) `-map 0:v:0` + el pedido declara la escala (ancho 320)")
    declarado = pasada(fx, todas, fuentes, dirsal,
                       pedido={"ancho": 320, "params": {"ancho": 320}})
    M.FFmpeg.orden = _ORDEN

    # D) lo mismo, pero con la SONDA parcheada: dos de los «real» de B lo eran
    #    solo porque la sonda no sabe leer `.mov` ni `.avi` y por eso no podía
    #    comparar el tamaño. Un aprobado por ceguera no es un aprobado.
    print("--- D) C) + la sonda de MOV parcheada")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reparacion_verificador as R                 # noqa: E402
    from filex import verificador as V                 # noqa: E402
    orig = V.sondear_en_proceso
    V.sondear_en_proceso = R.sondear_parcheado
    M.FFmpeg.orden = orden_parcheada
    con_sonda = pasada(fx, todas, fuentes, dirsal,
                       pedido={"ancho": 320, "params": {"ancho": 320}})
    M.FFmpeg.orden = _ORDEN
    V.sondear_en_proceso = orig

    with open(os.path.join(trabajo, "gif.json"), "w", encoding="utf-8") as fh:
        json.dump({"A_hoy": antes, "B_map0v0": despues,
                   "C_mas_escala_declarada": declarado,
                   "D_mas_sonda_parcheada": con_sonda}, fh, indent=1,
                  ensure_ascii=False)
    for nom, t in (("A hoy", antes), ("B -map 0:v:0", despues),
                   ("C + escala declarada", declarado),
                   ("D + sonda parcheada", con_sonda)):
        print("%-24s real %d/%d" % (nom, sum(1 for v in t.values()
                                             if v["estado"] == "real"), len(t)))
    for f in os.listdir(dirsal):
        os.remove(os.path.join(dirsal, f))


if __name__ == "__main__":
    main()
