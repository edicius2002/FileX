"""Sondeo de las 62 aristas `sin_sondear` de ImageMagick (agente S1).

No llama a `magick` por su cuenta: usa `filex.nucleo.FileX.convertir()`, de modo
que el contrato de cinco puntos, el directorio desechable y el censo del punto 5
entran solos. Lo unico que se fuerza es el GRAFO: se sustituye por uno de UNA
sola arista, porque si no el planificador elige otro camino (por ejemplo
`tif->png->pdf`, dos aristas reales a 2,2, en vez de `tif->pdf` sin sondear a
3,2) y la arista que se queria sondear no se ejecuta nunca.

Uso:  python bench/salidas-sondeo-im/sonda_im.py <dir_semillas> <dir_salidas> <json>
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = "C:/Users/krato/orca/workspaces/FileX/filex-cpu"
sys.path.insert(0, RAIZ)

from filex.grafo import Grafo  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

TIMEOUT = 120.0
N_A = 3          # mediana de 3 en la semilla principal
N_B = 1          # la segunda semilla es testigo de SEMILLA, no de tiempo


# ------------------------------------------------------------ testigos de ruido

def testigo_deriva(vueltas: int = 400_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel(tope: float = 20.0) -> tuple[float, bool]:
    """Lanzamiento de proceso. Con TOPE: un testigo que puede tumbar la
    medicion no es un testigo (CLAUDE.md §3)."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["magick", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=tope, check=False)
    except Exception:
        return tope * 1000, True
    return (time.perf_counter() - t0) * 1000, False


# ------------------------------------------------------------------- utilidades

def identifica(ruta: str) -> dict:
    """Que hay DE VERDAD en el fichero, segun el propio ImageMagick."""
    if not os.path.isfile(ruta):
        return {"existe": False}
    d = {"existe": True, "bytes": os.path.getsize(ruta)}
    try:
        r = subprocess.run(
            ["magick", "identify", "-quiet", "-format",
             "%m|%w|%h|%[bit-depth]|%[channels]|%A|%n\n", ruta],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=60, check=False)
    except Exception as e:
        d["identify"] = f"excepcion:{type(e).__name__}"
        return d
    if r.returncode != 0:
        d["identify"] = "rc!=0"
        d["identify_err"] = (r.stderr or "").strip().splitlines()[:1]
        return d
    lineas = [l for l in (r.stdout or "").strip().splitlines() if l.strip()]
    if not lineas:
        d["identify"] = "vacio"
        return d
    p = lineas[0].split("|")
    d.update({"formato_real": p[0], "w": p[1], "h": p[2], "profundidad": p[3],
              "canales": p[4], "alfa": p[5], "fotogramas": len(lineas)})
    return d


def rmse(a: str, b: str) -> float | None:
    try:
        r = subprocess.run(["magick", "compare", "-quiet", "-metric", "RMSE",
                            a, b, "null:"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=120, check=False)
    except Exception:
        return None
    txt = (r.stderr or "").strip()
    if "(" in txt and ")" in txt:
        try:
            return float(txt[txt.index("(") + 1:txt.index(")")])
        except ValueError:
            return None
    return None


def limpia_hallazgos(hs) -> list:
    out = []
    for h in hs or []:
        out.append({"regla": h.get("regla"), "sev": h.get("severidad"),
                    "msg": (h.get("mensaje") or "")[:160]})
    return out


def motivo_corto(err: str, rc, motivo: str) -> str:
    """Una linea, sin `stderr` crudo: se extrae SOLO el texto del error de
    ImageMagick, sin rutas ni volcados."""
    if err:
        for l in err.splitlines():
            l = l.strip()
            if not l:
                continue
            # "magick.exe: mensaje `fichero' @ error/x.c/Func/123."
            if ":" in l:
                l = l.split(":", 1)[1].strip()
            if "`" in l:
                l = l.split("`")[0].strip()
            if " @ " in l:
                l = l.split(" @ ")[0].strip()
            if l:
                return f"rc={rc}: {l}"[:180]
    return f"rc={rc}: {motivo}"[:180]


# ------------------------------------------------------------------ el barrido

def main() -> int:
    sem, out_dir, destino_json = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)

    fx = FileX()
    im = fx.motores["imagemagick"]
    build = im.build
    grafo_completo = fx.grafo

    aristas = {(a.origen, a.destino): a for a in grafo_completo.aristas
               if a.motor == "imagemagick" and a.estado == "sin_sondear"}
    pares = sorted(aristas)

    semillas = {
        "A": {"png": "A.png", "jpg": "A.jpg", "webp": "A.webp", "avif": "A.avif",
              "gif": "A.gif", "bmp": "A.bmp", "tif": "A.tif", "ico": "C.ico",
              "svg": "svg_A.svg"},
        "B": {"png": "B.png", "jpg": "B.jpg", "webp": "B.webp", "avif": "B.avif",
              "gif": "B.gif", "bmp": "B.bmp", "tif": "B.tif", "ico": "B.ico",
              "svg": "svg_B.svg"},
    }

    # Calentamiento (trampa 7): Windows Defender infla el primer arranque.
    for _ in range(3):
        subprocess.run(["magick", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60, check=False)

    d0 = testigo_deriva()
    n0, n0_tope = testigo_nivel()

    filas = []
    t_ini = time.time()
    for (o, d) in pares:
        arista = aristas[(o, d)]
        fx.grafo = Grafo([arista])
        for etiqueta, mapa in semillas.items():
            src = os.path.join(sem, mapa[o])
            if not os.path.isfile(src):
                filas.append({"origen": o, "destino": d, "semilla": etiqueta,
                              "error": "sin semilla"})
                continue
            n = N_A if etiqueta == "A" else N_B
            tiempos, ultimo = [], None
            salida = os.path.join(out_dir, f"{o}2{d}_{etiqueta}.{d}")
            for k in range(n):
                if os.path.isfile(salida):
                    os.remove(salida)
                c = fx.convertir(src, salida, timeout=TIMEOUT)
                ultimo = c
                if c.saltos and c.saltos[0].ms:
                    tiempos.append(c.saltos[0].ms)
            s = ultimo.saltos[0] if ultimo and ultimo.saltos else None
            fila = {
                "origen": o, "destino": d, "semilla": etiqueta,
                "src": os.path.basename(src),
                "rc": s.rc if s else None,
                "ms": round(statistics.median(tiempos), 1) if tiempos else None,
                "n": len(tiempos),
                "ok": bool(ultimo and ultimo.ok),
                "veredicto": ultimo.veredicto if ultimo else "?",
                "veredicto_salto": s.veredicto if s else "",
                "hallazgos": limpia_hallazgos(s.hallazgos if s else []),
                "cobertura": (s.cobertura if s else {}),
                "sobrantes": (s.sobrantes if s else {}),
                "motivo": motivo_corto(s.err if s else "", s.rc if s else None,
                                       (ultimo.motivo if ultimo else "")),
                "salida": identifica(salida),
            }
            if fila["ok"] and os.path.isfile(salida):
                fila["rmse_vs_origen"] = rmse(src, salida)
            filas.append(fila)
        print(f"  {o}->{d} listo ({time.time()-t_ini:.0f}s)", flush=True)

    fx.grafo = grafo_completo
    d1 = testigo_deriva()
    n1, n1_tope = testigo_nivel()

    doc = {
        "build": build,
        "fecha": time.strftime("%Y-%m-%d"),
        "segundos_totales": round(time.time() - t_ini, 1),
        "testigos": {"deriva_ms": [round(d0, 1), round(d1, 1)],
                     "deriva_ratio": round(d1 / d0, 3) if d0 else None,
                     "nivel_ms": [round(n0, 1), round(n1, 1)],
                     "nivel_en_tope": [n0_tope, n1_tope]},
        "filas": filas,
    }
    with open(destino_json, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"escrito {destino_json}: {len(filas)} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
