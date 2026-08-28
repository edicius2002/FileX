"""H2 — la campana de medicion del hito 2 y de B6.

Dos testigos de ruido (deriva monohilo + nivel por lanzamiento de proceso),
los dos con tope de 20 s; medianas de n>=9 donde el coste lo permite; el lock
de GPU tomado para TODA la tanda con el protocolo del arnes compartido.

Uso:  python medir_hito2.py [seccion ...]
      secciones: testigos vram suelta lote bitrate  (por defecto: todas)
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import gpu, motores  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(RAIZ, "corpus", "video")
TOPE_TESTIGO = 20.0


# ---------------------------------------------------------------- testigos
def testigo_deriva(ms_objetivo: float = 120.0) -> float:
    """Bucle monohilo. Detecta la DERIVA dentro de la tanda."""
    t0 = time.perf_counter()
    n = 0
    while (time.perf_counter() - t0) * 1000 < ms_objetivo:
        n += 1
        _ = sum(i * i for i in range(200))
    return round((time.perf_counter() - t0) * 1e3 / max(n, 1) * 1000, 3)


def testigo_proceso() -> tuple[float, bool]:
    """Lanzamiento de proceso. Detecta el NIVEL de carga de la maquina.

    Con TOPE PROPIO de 20 s: un testigo que puede tumbar la medicion no es un
    testigo (van tres casos en el proyecto, uno de ellos agotando 60 s).
    """
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=TOPE_TESTIGO)
    except subprocess.TimeoutExpired:
        return TOPE_TESTIGO * 1000, True
    except OSError:
        return -1.0, True
    return round((time.perf_counter() - t0) * 1000, 2), False


def sella(antes: dict, despues: dict) -> dict:
    """El veredicto limpia/SUCIA, con las dos razones separadas."""
    razones = []
    d_der = despues["deriva"] / antes["deriva"] if antes["deriva"] else 0
    if d_der > 1.5 or d_der < 0.67:
        razones.append(f"deriva x{d_der:.2f}")
    if antes["tope"] or despues["tope"]:
        razones.append("el testigo de proceso agoto su tope")
    peor = max(antes["proceso"], despues["proceso"])
    if peor > 150:
        razones.append(f"lanzamiento de proceso {peor:.0f} ms")
    return {"etiqueta": "SUCIA" if razones else "limpia", "razones": razones,
            "deriva_ratio": round(d_der, 3),
            "proceso_ms": [antes["proceso"], despues["proceso"]]}


def toma_testigos() -> dict:
    p, tope = testigo_proceso()
    return {"deriva": testigo_deriva(), "proceso": p, "tope": tope}


# ---------------------------------------------------------------------- VRAM
def vram_pico(fn, intervalo=0.2):
    """Pico de VRAM OCUPADA (total, nunca por PID: trampa 31) durante `fn`."""
    muestras = []
    parar = threading.Event()

    def vigila():
        while not parar.is_set():
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used",
                     "--format=csv,noheader,nounits"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, timeout=15)
                muestras.append(int(r.stdout.decode().strip().splitlines()[0]))
            except Exception:
                pass
            parar.wait(intervalo)

    base = gpu.vram_libre_mib()
    h = threading.Thread(target=vigila, daemon=True)
    h.start()
    try:
        out = fn()
    finally:
        parar.set()
        h.join(timeout=5)
    return out, {"muestras": len(muestras),
                 "pico_usado_mib": max(muestras) if muestras else None,
                 "min_usado_mib": min(muestras) if muestras else None,
                 "libre_antes_mib": base}


# --------------------------------------------------------------- utilidades
def mediana(fn, n=9):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        r = fn()
        xs.append((time.perf_counter_ns() - t0) / 1e6)
        if r is False:
            break
    return {"n": len(xs), "mediana_ms": round(statistics.median(xs), 1),
            "min_ms": round(min(xs), 1), "max_ms": round(max(xs), 1)}


def sonda_fichero(ruta):
    """Lo que el fichero de salida dice DE SI MISMO: bitrate real y el
    comentario que FileX le escribio."""
    argv = ["ffprobe", "-v", "error", "-show_entries",
            "format=duration,size,bit_rate:format_tags=comment:"
            "stream=codec_name,codec_type,bit_rate,width,height",
            "-of", "json", ruta]
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, timeout=60)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def tag(d, nombre):
    """El tag `nombre`, SIN distinguir mayusculas.

    MEDIDO: el mismo `-metadata comment=...` sale como `comment` en MP4 y como
    `COMMENT` en Matroska. Una lectura por la clave literal devuelve `None` en
    la mitad de los contenedores y se lee como «no se escribio el metadato».
    """
    tags = (d.get("format", {}) or {}).get("tags", {}) or {}
    for k, v in tags.items():
        if k.lower() == nombre.lower():
            return v
    return None


def bitrate_video_real(d):
    """bits/s del flujo de VIDEO. `bit_rate` por pista es N/A en Matroska, asi
    que se deriva de bytes*8/duracion menos lo que ocupa el audio declarado."""
    fmt = d.get("format", {})
    try:
        dur = float(fmt.get("duration"))
        tam = int(fmt.get("size"))
    except (TypeError, ValueError):
        return None
    audio = 0
    for s in d.get("streams", []):
        if s.get("codec_type") == "audio" and s.get("bit_rate"):
            audio += int(s["bit_rate"])
    return int(tam * 8 / dur) - audio


# ------------------------------------------------------------------ carpeta
def prepara_carpeta(destino, n=8):
    """Una carpeta REAL: trozos del corpus, con sus dos pistas de audio donde
    las hay. B6 se mide sobre una carpeta, no sobre un fichero repetido."""
    os.makedirs(destino, exist_ok=True)
    # Todos los clips salen en .mp4 y la conversion del lote va a .mkv: FileX
    # RECHAZA origen y destino del mismo formato ("origen y destino son el mismo
    # formato", `nucleo.convertir`), asi que una carpeta mixta no se puede
    # transcodificar entera. Es un hallazgo, no un accidente del arnes: queda
    # medido aparte en §6 y aqui se aparta para que el reloj mida el codec.
    #
    # Y se RECODIFICA en vez de copiar: un corte con `-c copy` cae en el
    # fotograma clave mas cercano y deja una duracion declarada que no es la
    # real, con lo que la regla A1/V1 del contrato marca `fallo` en la
    # conversion siguiente. El artefacto era del corte, no del hito.
    fuentes = [("tipico.mp4", 0, 5), ("tipico.mp4", 5, 5), ("tipico.mp4", 10, 5),
               ("tipico.mp4", 15, 5), ("trivial.mp4", 0, 5),
               ("patologico_2pistas.mkv", 0, 5), ("patologico_2pistas.mkv", 5, 5),
               ("fuente_4k.mp4", 0, 5)]
    hechos = []
    for i, (f, ini, dur) in enumerate(fuentes[:n]):
        src = os.path.join(CORPUS, f)
        out = os.path.join(destino, f"clip{i:02d}.mp4")
        if not os.path.exists(out):
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-ss", str(ini),
                 "-i", src, "-t", str(dur), "-map", "0",
                 "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                 "-c:a", "aac", "-b:a", "128k", out],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=600)
        hechos.append(out)
    return hechos


# ------------------------------------------------------------------ medidas
def mide_suelta(res, raiz_tmp):
    """Una conversion SUELTA por cada codec, punta a punta y con contrato."""
    ent = os.path.join(CORPUS, "tipico.mp4")
    fx = FileX(raices_lectura=[CORPUS, raiz_tmp], raices_escritura=[raiz_tmp])
    filas = []
    for etiqueta, pedido in (
            ("hevc_gpu", {"codec_video": "hevc", "bitrate_video": "2000k"}),
            ("hevc_cpu", {"codec_video": "hevc", "bitrate_video": "2000k",
                          "_forzar_cpu": True}),
            ("av1_pedido", {"codec_video": "av1", "bitrate_video": "2000k"})):
        sal = os.path.join(raiz_tmp, f"suelta_{etiqueta}.mkv")

        def una(s=sal, p=pedido, e=etiqueta):
            if os.path.exists(s):
                os.unlink(s)
            if p.get("_forzar_cpu"):
                gpu.olvidar()
                gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU por el arnes")
            c = fx.convertir(ent, s, {k: v for k, v in p.items()
                                      if not k.startswith("_")})
            if not c.ok:
                print(f"    [!] {e}: {c.motivo}")
                return False
            return True

        n = 9 if etiqueta != "hevc_cpu" else 9
        m = mediana(una, n)
        gpu.olvidar()
        d = sonda_fichero(sal) if os.path.exists(sal) else {}
        filas.append({"etiqueta": etiqueta, **m,
                      "bytes": os.path.getsize(sal) if os.path.exists(sal) else 0,
                      "comment": tag(d, "comment"),
                      "bitrate_video_real_bps": bitrate_video_real(d),
                      "codecs": [s.get("codec_name") for s in d.get("streams", [])],
                      "pistas": len(d.get("streams", []))})
        print(f"  {etiqueta:12s} n={m['n']} mediana={m['mediana_ms']:9.1f} ms  "
              f"{filas[-1]['bytes']:>10} B  pistas={filas[-1]['pistas']}")
        print(f"      comment={filas[-1]['comment']}")
    res["suelta"] = filas


def mide_lote(res, raiz_tmp):
    """B6 — el lote sobre una carpeta REAL. Es el unico caso donde el 8,39x
    de HEVC decide algo."""
    carpeta = os.path.join(raiz_tmp, "carpeta")
    entradas = prepara_carpeta(carpeta)
    total_b = sum(os.path.getsize(e) for e in entradas)
    print(f"  carpeta: {len(entradas)} ficheros, {total_b} B")
    fx = FileX(raices_lectura=[carpeta, raiz_tmp], raices_escritura=[raiz_tmp])
    filas = []
    for etiqueta, forzar_cpu in (("lote_gpu", False), ("lote_cpu", True)):
        destino = os.path.join(raiz_tmp, etiqueta)
        os.makedirs(destino, exist_ok=True)

        def uno():
            gpu.olvidar()
            if forzar_cpu:
                gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU por el arnes")
            hechos, fallos, detalle = 0, 0, []
            for e in entradas:
                s = os.path.join(destino,
                                 os.path.splitext(os.path.basename(e))[0] + ".mkv")
                if os.path.exists(s):
                    os.unlink(s)
                c = fx.convertir(e, s, {"codec_video": "hevc",
                                        "bitrate_video": "2000k"})
                if c.ok:
                    hechos += 1
                else:
                    fallos += 1
                    detalle.append((os.path.basename(e), c.motivo))
            uno.ultimo = (hechos, fallos, detalle)
            return True

        m = mediana(uno, 3)
        hechos, fallos, detalle = uno.ultimo
        pistas = {}
        for f in sorted(os.listdir(destino)):
            d = sonda_fichero(os.path.join(destino, f))
            pistas[f] = len(d.get("streams", []))
        filas.append({"etiqueta": etiqueta, **m, "convertidos": hechos,
                      "fallidos": fallos, "detalle_fallos": detalle,
                      "bytes_entrada": total_b,
                      "bytes_salida": sum(os.path.getsize(os.path.join(destino, f))
                                          for f in os.listdir(destino)),
                      "pistas_por_salida": pistas})
        print(f"  {etiqueta:9s} n={m['n']} mediana={m['mediana_ms']:10.1f} ms  "
              f"ok={hechos} fallos={fallos}")
        if detalle:
            for nom, mot in detalle:
                print(f"      [!] {nom}: {mot}")
    gpu.olvidar()
    if len(filas) == 2 and filas[1]["mediana_ms"]:
        res["b6_ganancia"] = round(filas[1]["mediana_ms"] / filas[0]["mediana_ms"], 3)
        print(f"  --> B6: GPU x{res['b6_ganancia']} sobre CPU en LOTE")
    res["lote"] = filas


def mide_vram(res, raiz_tmp):
    """Cuanta VRAM cuesta NVENC de verdad. El umbral de 6 000 MiB se calibro
    para modelos de OCR (+4 430 MiB); NVENC puede ser otro regimen."""
    ent = os.path.join(CORPUS, "tipico.mp4")
    sal = os.path.join(raiz_tmp, "vram.mkv")
    fx = FileX(raices_lectura=[CORPUS, raiz_tmp], raices_escritura=[raiz_tmp])

    def una():
        if os.path.exists(sal):
            os.unlink(sal)
        c = fx.convertir(ent, sal, {"codec_video": "hevc",
                                    "bitrate_video": "2000k"})
        return c.ok

    reposo = []
    for _ in range(5):
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=15)
        reposo.append(int(r.stdout.decode().strip().splitlines()[0]))
        time.sleep(0.2)
    ok, v = vram_pico(una)
    v["reposo_usado_mib"] = reposo
    v["coste_propio_mib"] = (v["pico_usado_mib"] - max(reposo)
                             if v["pico_usado_mib"] else None)
    v["ok"] = ok
    print(f"  reposo={reposo}  pico={v['pico_usado_mib']} MiB  "
          f"coste propio ~{v['coste_propio_mib']} MiB  ({v['muestras']} muestras)")
    res["vram"] = v


def mide_bitrate(res, raiz_tmp):
    """El desvio de bitrate: pedido, obtenido y donde queda registrado."""
    ent = os.path.join(CORPUS, "tipico.mp4")
    fx = FileX(raices_lectura=[CORPUS, raiz_tmp], raices_escritura=[raiz_tmp])
    filas = []
    for pedido_bps in (1000000, 2000000, 4000000, 8000000):
        for etiqueta, cpu in (("nvenc", False), ("cpu", True)):
            gpu.olvidar()
            if cpu:
                gpu._CACHE["hevc_nvenc"] = (False, 0, "forzado a CPU por el arnes")
            sal = os.path.join(raiz_tmp, f"br_{etiqueta}_{pedido_bps}.mkv")
            if os.path.exists(sal):
                os.unlink(sal)
            c = fx.convertir(ent, sal, {"codec_video": "hevc",
                                        "bitrate_video": pedido_bps})
            if not c.ok:
                print(f"    [!] {etiqueta} {pedido_bps}: {c.motivo}")
                continue
            d = sonda_fichero(sal)
            real = bitrate_video_real(d)
            desv = (real - pedido_bps) / pedido_bps if real else None
            filas.append({"via": etiqueta, "pedido_bps": pedido_bps,
                          "real_bps": real,
                          "desvio_pct": round(desv * 100, 2) if desv is not None else None,
                          "comment": tag(d, "comment"),
                          "veredicto": c.saltos[-1].veredicto if c.saltos else "?",
                          "hallazgos": [h.get("regla") for h in
                                        (c.saltos[-1].hallazgos if c.saltos else [])]})
            print(f"  {etiqueta:6s} pedido={pedido_bps:>8} real={real:>8} "
                  f"desvio={filas[-1]['desvio_pct']:+7.2f} %  "
                  f"veredicto={filas[-1]['veredicto']}")
            os.unlink(sal)
    gpu.olvidar()
    res["bitrate"] = filas


# ---------------------------------------------------------------------- main
def main():
    secciones = sys.argv[1:] or ["vram", "suelta", "bitrate", "lote"]
    raiz_tmp = tempfile.mkdtemp(prefix="h2-medir-")
    res = {"secciones": secciones, "tmp": raiz_tmp,
           "python": sys.version.split()[0],
           "cuando": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(f"[H2] desechable: {raiz_tmp}")
    print(f"[H2] R21 censo ANTES: {sorted(os.listdir(raiz_tmp))}")

    antes = toma_testigos()
    with gpu.Lock("H2-campana-hito2") as l:
        res["aviso_guardia"] = l.aviso
        res["lock"] = {"ruta": l.ruta, "dueno": gpu.dueno(),
                       "vram_libre_mib": gpu.vram_libre_mib()}
        print(f"[H2] lock tomado en {l.ruta} (dueno={gpu.dueno()}); "
              f"libre={res['lock']['vram_libre_mib']} MiB; aviso='{l.aviso}'")
        res["capacidad"] = {c: gpu.capacidad(c) for c in
                            ("hevc_nvenc", "h264_nvenc", "av1_nvenc")}
        print(f"[H2] capacidades sondeadas: {res['capacidad']}")
        gpu.olvidar()
        for s in secciones:
            print(f"\n=== {s} ===")
            {"vram": mide_vram, "suelta": mide_suelta, "lote": mide_lote,
             "bitrate": mide_bitrate}[s](res, raiz_tmp)
    despues = toma_testigos()
    res["ruido"] = sella(antes, despues)
    res["ruido"]["antes"], res["ruido"]["despues"] = antes, despues
    print(f"\n[H2] ruido: {res['ruido']['etiqueta']} {res['ruido']['razones']}")
    print(f"[H2] lock libre al terminar: {gpu.esta_libre()}")
    res["lock_libre_al_final"] = gpu.esta_libre()

    print(f"[H2] R21 censo DESPUES: {len(os.listdir(raiz_tmp))} entradas")
    salida = os.path.join(AQUI, "medicion_hito2.json")
    previo = {}
    if os.path.exists(salida):
        try:
            previo = json.load(open(salida, encoding="utf-8"))
        except Exception:
            previo = {}
    previo.update(res)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(previo, f, ensure_ascii=False, indent=1)
    print("->", salida)
    shutil.rmtree(raiz_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
