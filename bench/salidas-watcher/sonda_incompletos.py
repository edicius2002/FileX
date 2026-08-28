#!/usr/bin/env python3
"""N5 — «fichero incompleto» cuando el formato NO tiene suma de comprobación.

El pendiente que deja `bench/hito7-superficies.md` §3.3, con sus palabras:

    Las 5 conversiones incompletas del watcher ingenuo dieron `rc != 0` y
    veredicto `fallo` — ImageMagick rechaza un PNG truncado. **Pero eso es una
    propiedad de este par (formato, motor), no una garantía**: un CSV o un WAV
    truncados se convierten tan ricamente. **PENDIENTE**: repetir con un
    formato sin suma de comprobación ni longitud declarada.

Cuatro escenas:

  1. **El extremo a extremo**: el `Vigilante` de verdad sobre un WAV que se
     escribe despacio, en las tres configuraciones del hito 7. Se cuenta cuántas
     conversiones salen, de cuántos bytes, y **con qué veredicto** — que es la
     pregunta que quedó abierta.
  2. **La matriz de defensas**: tres formatos × varios puntos de truncado ×
     tres defensas (coherencia declarada, estructura de la última línea,
     reposo). Qué detecta cada una y qué se le escapa.
  3. **Los FALSOS POSITIVOS**, que es donde una defensa se cae: un WAV escrito a
     una tubería (cabecera con marcador de relleno) y un CSV con un salto de
     línea DENTRO de un campo entrecomillado.
  4. **El residuo**: el caso que ninguna defensa ve.

Trampa 38: cada celda registra `condicion_ok` — si el truncado que se dice
producir se produjo, y si el escritor seguía abierto cuando se midió.
R21: el directorio de trabajo se lista antes y después.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
ESCRITOR = os.path.join(AQUI, "escritor_lento.py")
sys.path.insert(0, RAIZ)


# ==========================================================================
# Las defensas candidatas
# ==========================================================================
def d_declarada(ruta: str) -> tuple[str, str]:
    """¿La cabecera declara un tamaño, y coincide con los bytes que hay?

    `completo` · `incompleto` · `sin_declaracion` · `error`. El tercer valor no
    es un aprobado: es *«esta defensa no aplica aquí»*, y hay que contarlo
    aparte o se cuela como éxito.
    """
    try:
        real = os.path.getsize(ruta)
        with open(ruta, "rb") as fh:
            cab = fh.read(64)
    except OSError as e:
        return "error", str(e)
    if len(cab) < 12:
        return "incompleto", f"solo {len(cab)} B: no cabe ni la cabecera"

    if cab[:4] == b"RIFF" and cab[8:12] in (b"WAVE", b"AVI ", b"WEBP"):
        decl = int.from_bytes(cab[4:8], "little") + 8
        if decl in (8, 0xFFFFFFFF + 8, 0x7FFFFFFF + 8):
            return "sin_declaracion", f"RIFF de relleno ({decl - 8})"
        if real < decl:
            return "incompleto", f"RIFF declara {decl} y hay {real}"
        return "completo", f"RIFF declara {decl}, hay {real}"

    if cab[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            with open(ruta, "rb") as fh:
                fh.seek(max(0, real - 12))
                cola = fh.read(12)
        except OSError as e:
            return "error", str(e)
        if cola[4:8] == b"IEND":
            return "completo", "IEND presente"
        return "incompleto", "sin trozo IEND"

    return "sin_declaracion", "el formato no declara su longitud"


def d_ultima_linea(ruta: str) -> tuple[str, str]:
    """¿La última línea es una fila entera? Solo para texto separado por comas.

    Se usa el módulo `csv`, que entiende las comillas: sin eso, un salto de
    línea DENTRO de un campo entrecomillado se cuenta como fin de fila y la
    defensa da un falso positivo. Es exactamente lo que hay en
    `corpus/datos/patologico_bom.csv`.
    """
    try:
        with open(ruta, "rb") as fh:
            crudo = fh.read()
    except OSError as e:
        return "error", str(e)
    if not crudo:
        return "incompleto", "0 bytes"
    if not crudo.endswith((b"\n", b"\r")):
        return "incompleto", "no termina en salto de línea"
    try:
        txt = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "incompleto", "el último carácter UTF-8 está cortado"
    filas = list(csv.reader(io.StringIO(txt)))
    if len(filas) < 2:
        return "sin_declaracion", "no hay cabecera + fila que comparar"
    n = len(filas[0])
    malas = [i for i, f in enumerate(filas) if len(f) != n]
    if malas:
        return "incompleto", f"filas con otro número de campos: {malas[:5]}"
    return "completo", f"{len(filas)} filas de {n} campos"


def d_reposo(ruta: str, segundos: float, intervalo: float = 0.2) -> tuple[str, str]:
    """El tiempo de reposo: `(tamaño, mtime_ns)` quieto durante N segundos.

    Es lo que el watcher ya hace con `estables × intervalo`. Se mide aquí para
    poder decir **qué añade** sobre las otras dos, no para sustituirlas.
    """
    def foto():
        try:
            st = os.stat(ruta)
            return (st.st_size, st.st_mtime_ns)
        except OSError:
            return None

    a = foto()
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        time.sleep(intervalo)
        b = foto()
        if b != a:
            return "incompleto", f"se movió: {a} -> {b}"
        a = b
    return "completo", f"quieto {segundos} s en {a}"


# ==========================================================================
# Utilidades
# ==========================================================================
def censo(d: str) -> dict:
    try:
        return {e.name: (e.stat().st_size if e.is_file() else -1)
                for e in os.scandir(d)}
    except OSError:
        return {}


def csv_semilla(ruta: str, filas: int = 4000) -> None:
    """Un CSV determinista y grande. La orden que lo reproduce va al MANIFIESTO."""
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "nombre", "ciudad", "importe"])
        for i in range(filas):
            w.writerow([i, f"cliente-{i:05d}", f"ciudad-{i % 97:02d}",
                        f"{(i * 7919) % 100000 / 100:.2f}"])


def truncar(origen: str, destino: str, n: int) -> int:
    with open(origen, "rb") as a, open(destino, "wb") as b:
        b.write(a.read(n))
    return os.path.getsize(destino)


def corte_en_linea(ruta: str, aprox: int) -> int:
    """El byte del PRIMER salto de línea a partir de `aprox`, incluido.

    Es el corte que hace indetectable un CSV a medias: la última fila está
    entera y el fichero termina en `\\n`. Sin este corte concreto, la matriz
    diría que la defensa de estructura acierta siempre.
    """
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    i = crudo.find(b"\n", aprox)
    return (i + 1) if i >= 0 else len(crudo)


# ==========================================================================
# Escena 1 — el extremo a extremo con el Vigilante de verdad
# ==========================================================================
def escena_extremo(tmp: str, origen: str, destino_fmt: str, log) -> list[dict]:
    from filex.nucleo import FileX
    from filex.watcher import Memoria, Vigilante

    fx = FileX()
    salidas = []
    configs = [
        ("ingenua (estables=1, sin cerrojo, sin coherencia)", 1, False, False),
        ("estabilidad sola (estables=2, sin cerrojo, sin coherencia)", 2, False, False),
        ("estables=1 + SOLO coherencia", 1, False, True),
        ("defecto hito 7 (estables=2 + cerrojo, sin coherencia)", 2, True, False),
        ("defecto NUEVO (estables=2 + cerrojo + coherencia)", 2, True, True),
    ]
    for i_cfg, (etiqueta, estables, cerrojo, coherencia) in enumerate(configs):
        ent = os.path.join(tmp, f"ent_{i_cfg}")
        sal = os.path.join(tmp, f"sal_{i_cfg}")
        os.makedirs(ent, exist_ok=True)
        os.makedirs(sal, exist_ok=True)
        sujeto = os.path.join(ent, "lento." + os.path.splitext(origen)[1].lstrip("."))

        h = subprocess.Popen(
            [sys.executable, ESCRITOR, "--origen", origen, "--destino", sujeto,
             "--trozos", "16", "--pausa", "0.15", "--pausa-larga", "3.0",
             "--en-trozo", "7"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)

        v = Vigilante(fx, [ent], sal, destino_fmt, intervalo=0.3,
                      estables=estables, cerrojo=cerrojo,
                      coherencia=coherencia, paciencia=1000,
                      memoria=Memoria(), timeout=120.0)
        vistos = []
        t0 = time.time()
        arranco = False
        while time.time() - t0 < 30:
            # `maduros()` y `atender()` por separado, no `paso()`: así se puede
            # registrar los BYTES DE ENTRADA que tenía el fichero cuando se le
            # dio por maduro, que es la columna que hace falta y la que el hito
            # 7 llama «tamaños vistos».
            for hu in v.maduros():
                vivo_antes = h.poll() is None
                r = v.atender(hu)
                tam = -1
                try:
                    tam = os.path.getsize(r.salida)
                except OSError:
                    pass
                vistos.append({
                    "estado": r.estado, "veredicto": r.veredicto,
                    "motivo": r.motivo, "bytes_salida": tam,
                    "bytes_entrada": hu.tamano, "ms": round(r.ms, 1),
                    "escritor_vivo": vivo_antes,
                    "entrada_completa": hu.tamano == os.path.getsize(origen),
                })
                # Se recoge la salida y se borra para que la siguiente no
                # choque con R9 («el destino ya existe») y el experimento mida
                # lo que dice medir y no la regla de sobrescritura.
                try:
                    os.remove(r.salida)
                except OSError:
                    pass
            if h.poll() is not None and not v._pendientes:
                break
            arranco = True
            time.sleep(0.3)
        lineas = []
        try:
            h.stdout.flush()
        except (OSError, ValueError):
            pass
        h.kill()
        try:
            resto, _ = h.communicate(timeout=10)
            lineas = (resto or "").split()
        except subprocess.TimeoutExpired:
            pass
        malas = [x for x in vistos if not x["entrada_completa"]]
        r = {"config": etiqueta, "estables": estables, "cerrojo": cerrojo,
             "coherencia": coherencia,
             "conversiones": len(vistos),
             "sobre_entrada_incompleta": len(malas),
             "ms_desperdiciados": round(sum(x["ms"] for x in malas), 1),
             "contadores": dict(v.contadores),
             "detalle": vistos,
             "condicion_ok": arranco and len(vistos) > 0,
             "condicion": "el watcher llegó a sondear con el escritor vivo",
             "lineas_escritor_restantes": lineas[:8]}
        log.write(json.dumps(r, ensure_ascii=False) + "\n")
        salidas.append(r)
    return salidas


# ==========================================================================
# Escena 1b — el tamaño real que vio cada conversión
# ==========================================================================
def escena_bytes_vistos(tmp: str, origen: str, log) -> dict:
    """Qué bytes tenía el fichero cuando cada configuración lo dio por maduro.

    Es la columna «tamaños vistos» del hito 7, que es la parte discreta y
    reproducible del experimento; las latencias no lo son.
    """
    from filex.watcher import _estable_en_disco

    res = {}
    for etiqueta, estables, cerrojo in (("ingenua", 1, False),
                                        ("estables=2", 2, False),
                                        ("defecto", 2, True)):
        ent = os.path.join(tmp, "b_" + etiqueta.replace("=", ""))
        os.makedirs(ent, exist_ok=True)
        sujeto = os.path.join(ent, "lento.wav")
        h = subprocess.Popen(
            [sys.executable, ESCRITOR, "--origen", origen, "--destino", sujeto,
             "--trozos", "16", "--pausa", "0.15", "--pausa-larga", "3.0",
             "--en-trozo", "7"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
        prev = None
        repes = 0
        vistos = []
        t0 = time.time()
        while time.time() - t0 < 25:
            try:
                st = os.stat(sujeto)
                foto = (st.st_size, st.st_mtime_ns)
            except OSError:
                time.sleep(0.3)
                continue
            repes = repes + 1 if foto == prev else 1
            prev = foto
            if repes >= estables:
                if cerrojo and not _estable_en_disco(sujeto):
                    time.sleep(0.3)
                    continue
                vistos.append({"bytes": st.st_size,
                               "escritor_vivo": h.poll() is None,
                               "declarada": d_declarada(sujeto)[0]})
                repes = 0
                prev = None
            if h.poll() is not None:
                break
            time.sleep(0.3)
        h.kill()
        try:
            h.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        res[etiqueta] = vistos
        log.write(f"[bytes_vistos:{etiqueta}] {vistos}\n")
    return res


# ==========================================================================
# Escena 2 — la matriz de defensas
# ==========================================================================
def escena_matriz(tmp: str, semillas: dict, log) -> list[dict]:
    filas = []
    for fmt, origen in semillas.items():
        total = os.path.getsize(origen)
        cortes = [("10 %", int(total * 0.10)), ("50 %", int(total * 0.50)),
                  ("90 %", int(total * 0.90)),
                  ("todo menos 1 B", total - 1), ("completo", total)]
        if fmt == "csv":
            cortes.insert(3, ("50 % + fin de línea", corte_en_linea(origen, int(total * 0.5))))
        for etiqueta, n in cortes:
            destino = os.path.join(tmp, f"m_{fmt}_{n}.{fmt}")
            real = truncar(origen, destino, n)
            cond = (real == min(n, total))
            f = {"formato": fmt, "corte": etiqueta, "bytes": real,
                 "de": total, "condicion_ok": cond,
                 "condicion": "el fichero quedó con los bytes pedidos",
                 "declarada": d_declarada(destino),
                 "ultima_linea": d_ultima_linea(destino) if fmt == "csv"
                                 else ("no_aplica", "no es texto delimitado"),
                 "reposo": d_reposo(destino, 0.6)}
            filas.append(f)
            log.write(json.dumps(f, ensure_ascii=False) + "\n")
    return filas


# ==========================================================================
# Escena 3 — los falsos positivos
# ==========================================================================
def escena_falsos(tmp: str, wav: str, log) -> list[dict]:
    casos = []

    # (a) WAV a una TUBERÍA: el mismo ffmpeg, salida no buscable.
    tuberia = os.path.join(tmp, "tuberia.wav")
    argv = ["ffmpeg", "-nostdin", "-y", "-i", wav, "-f", "wav", "pipe:1"]
    rc = None
    try:
        with open(tuberia, "wb") as fh:
            r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=fh,
                               stderr=subprocess.PIPE, timeout=120)
            rc = r.returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        rc = f"error: {e}"
    if isinstance(rc, int) and rc == 0 and os.path.getsize(tuberia) > 44:
        with open(tuberia, "rb") as fh:
            cab = fh.read(12)
        casos.append({
            "caso": "WAV completo escrito a una TUBERÍA (ffmpeg -f wav pipe:1)",
            "condicion_ok": True,
            "condicion": "ffmpeg rc=0 y el fichero tiene datos",
            "bytes": os.path.getsize(tuberia),
            "riff_declarado": int.from_bytes(cab[4:8], "little"),
            "declarada": d_declarada(tuberia),
            "es_completo_de_verdad": True})
    else:
        casos.append({"caso": "WAV a tubería", "condicion_ok": False,
                      "detalle": str(rc)})

    # (b) CSV con salto de línea DENTRO de un campo entrecomillado.
    patologico = os.path.join(RAIZ, "corpus", "datos", "patologico_bom.csv")
    if os.path.isfile(patologico):
        ingenua = "completo"
        with open(patologico, "rb") as fh:
            crudo = fh.read()
        # La versión INGENUA de la defensa: contar comas por línea física.
        lineas = [l for l in crudo.decode("utf-8-sig").splitlines() if l]
        n = lineas[0].count(",") + 1
        if any(l.count(",") + 1 != n for l in lineas[1:]):
            ingenua = "incompleto"
        casos.append({
            "caso": "CSV completo con salto de línea dentro de comillas",
            "condicion_ok": True,
            "condicion": "el fichero del corpus tiene el campo multilínea",
            "bytes": len(crudo),
            "defensa_ingenua_por_comas": ingenua,
            "ultima_linea": d_ultima_linea(patologico),
            "es_completo_de_verdad": True})

    # (c) CSV completo SIN salto de línea final.
    sin_salto = os.path.join(tmp, "sin_salto.csv")
    with open(sin_salto, "w", encoding="utf-8", newline="") as fh:
        fh.write("a,b,c\n1,2,3")
    casos.append({"caso": "CSV completo sin salto de línea final",
                  "condicion_ok": True,
                  "condicion": "escrito entero, sin \\n al final",
                  "bytes": os.path.getsize(sin_salto),
                  "ultima_linea": d_ultima_linea(sin_salto),
                  "es_completo_de_verdad": True})

    for c in casos:
        log.write(json.dumps(c, ensure_ascii=False) + "\n")
    return casos


# ==========================================================================
# Coste de las defensas
# ==========================================================================
def coste(rutas: dict, repes: int = 11) -> dict:
    out = {}
    for etiqueta, ruta in rutas.items():
        for nombre, fn in (("declarada", d_declarada),
                           ("ultima_linea", d_ultima_linea)):
            fn(ruta)
            ms = []
            for _ in range(repes):
                t0 = time.perf_counter()
                fn(ruta)
                ms.append((time.perf_counter() - t0) * 1000)
            out[f"{nombre}@{etiqueta}"] = {
                "mediana_ms": round(statistics.median(ms), 4),
                "bytes": os.path.getsize(ruta), "n": repes}
    return out


def testigo_deriva(n=300000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 20000.0
    return (time.perf_counter() - t0) * 1000


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tmp", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    a = p.parse_args(argv)

    os.makedirs(a.tmp, exist_ok=True)
    antes = censo(a.tmp)
    wav = os.path.join(RAIZ, "corpus", "audio", "trivial.wav")
    png = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    csv_grande = os.path.join(a.tmp, "semilla.csv")
    csv_semilla(csv_grande)

    res = {"antes": antes, "semillas": {
        "wav": {"ruta": wav, "bytes": os.path.getsize(wav)},
        "png": {"ruta": png, "bytes": os.path.getsize(png)},
        "csv": {"ruta": csv_grande, "bytes": os.path.getsize(csv_grande)}}}

    d0, n0 = testigo_deriva(), testigo_nivel()
    with open(a.log, "w", encoding="utf-8") as log:
        log.write(f"# sonda_incompletos — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"# antes: {len(antes)} ficheros en {a.tmp}\n")
        res["matriz"] = escena_matriz(a.tmp, {"wav": wav, "png": png,
                                              "csv": csv_grande}, log)
        res["falsos_positivos"] = escena_falsos(a.tmp, wav, log)
        res["bytes_vistos"] = escena_bytes_vistos(a.tmp, wav, log)
        res["extremo"] = escena_extremo(a.tmp, wav, "mp3", log)
        res["coste"] = coste({"wav_705KB": wav, "csv_200KB": csv_grande})
        d1, n1 = testigo_deriva(), testigo_nivel()
        res["testigos"] = {
            "deriva_ms": [round(d0, 2), round(d1, 2)],
            "nivel_ms": [round(n0, 2), round(n1, 2)],
            "deriva_ratio": round(d1 / d0, 3) if d0 else None,
            "nivel_ratio": round(n1 / n0, 3) if n0 else None}
        res["testigos"]["etiqueta"] = (
            "limpia" if res["testigos"]["deriva_ratio"] < 1.5
            and res["testigos"]["nivel_ratio"] < 3.0 else "SUCIA")
        log.write(f"# testigos: {json.dumps(res['testigos'])}\n")
        res["despues"] = censo(a.tmp)
        log.write(f"# despues: {len(res['despues'])} ficheros\n")

    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"extremo": [(e["config"], e["conversiones"],
                                   e["sobre_entrada_incompleta"],
                                   e["condicion_ok"]) for e in res["extremo"]],
                      "testigos": res["testigos"]["etiqueta"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
