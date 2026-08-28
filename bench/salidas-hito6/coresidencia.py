# -*- coding: utf-8 -*-
"""S6 / hito 6 — LA CORESIDENCIA, que es lo unico que faltaba para poder cerrar el hito.

`bench/ocr-produccion-sidecar.md` §9 lo declara con todas las letras:

    «Ni una sola medida con dos modelos residentes a la vez. El presupuesto de
     §6.1 SUMA cifras de informes distintos, y la suma es una hipotesis: los
     asignadores podrian compartir o estorbarse. PENDIENTE, y es lo que de verdad
     falta para cerrar el hito 6.»

Este arnes mide esa suma. Cuatro fases, **un proceso por corrida**:

    base          — solo el proceso de Python, sin cargar nada (control)
    solo_audio    — faster-whisper (distil-large-v3 o large-v3), carga + transcripcion
    solo_ocr      — RapidOCR ONNX PP-OCRv6 small + R6, carga + un folio de 8,88 Mpx
    solo_nvenc    — hevc_nvenc sobre el 4K del corpus
    coresidente   — LOS TRES A LA VEZ, en el mismo proceso y solapados

y la pregunta es una sola: **¿`coresidente` == `solo_audio` + `solo_ocr` +
`solo_nvenc`?** Si lo es, el presupuesto de §6.1 se puede seguir sumando; si no,
la reescritura propuesta del criterio no sirve como esta escrita y hay que decirlo.

Las cifras son SIEMPRE `delta` sobre la base del propio proceso, porque la base de
escritorio se mueve (3 292-3 448 MiB documentados; 1 175-1 864 en las tandas de G5).
El margen absoluto se calcula aparte, con la base documentada en su peor caso.

**AMPLIADO tras la tanda A.** La fase `coresidente` —los dos modelos en el MISMO
proceso— **muere en 10 de 10 corridas** con `rc=0xC0000409` y
`Could not load symbol cudnnGetLibConfig. Error code 127`. Por eso hay dos fases
mas, que son los dos intentos que quedaban:

    coresidente_inv — el mismo proceso, cargando el OCR PRIMERO y el audio
                      despues: si el orden lo arregla, el mecanismo es el orden
                      de carga de las DLL de cuDNN y no la coexistencia.
    dos_procesos    — la arquitectura que este informe propone: el audio en este
                      proceso y el OCR en un **trabajador** de `filex/sidecar.py`.
                      Es la unica de las tres que mide el presupuesto del hito.

uso: coresidencia.py <base|solo_audio|solo_ocr|solo_nvenc|coresidente|
                      coresidente_inv|dos_procesos> [etiqueta]
env: H6_WHISPER (distil-large-v3), H6_IMG, H6_AUDIO, H6_VIDEO, H6_OUT, H6_DISPOSITIVO
"""
import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from testigos import testigo_deriva, testigo_nivel, veredicto  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.join(RAIZ, "bench", "salidas-hito6")

FASE = sys.argv[1]
ETIQ = sys.argv[2] if len(sys.argv) > 2 else FASE

WHISPER = os.environ.get("H6_WHISPER", "distil-large-v3")
DISPOSITIVO = os.environ.get("H6_DISPOSITIVO", "cuda")   # trampa 11: fijado y declarado
IMG = os.environ.get("H6_IMG", os.path.join(SAL, "img", "escaneado_d4_r400.png"))
AUDIO = os.environ.get("H6_AUDIO", os.path.join(RAIZ, "corpus", "audio", "habla_jfk.flac"))
VIDEO = os.environ.get("H6_VIDEO", os.path.join(RAIZ, "corpus", "video", "fuente_4k.mp4"))
OUT = os.environ.get("H6_OUT", os.path.join(SAL, "json"))
os.makedirs(OUT, exist_ok=True)

#: Cadencia del muestreador de VRAM. `nvidia-smi` cuesta ~30-60 ms; a 250 ms el
#: muestreador consume <25 % de un nucleo y no falsea la medida que observa.
CADENCIA_S = 0.25

#: Segundos de video que codifica NVENC. El tope va DENTRO de la orden
#: (trampa 52): un tope que solo mata al cliente deja un ffmpeg vivo 9 minutos.
NVENC_S = 20

#: Tope del cliente, ademas del de dentro.
NVENC_TIMEOUT = 180


def vram_usada() -> int:
    """MiB usados en la tarjeta, TOTAL. Por PID no es observable (trampa 31)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=20)
        return int(r.stdout.decode().strip().splitlines()[0])
    except Exception:
        return -1


class Muestreador(threading.Thread):
    """Hilo que registra el MAXIMO de VRAM usada. El pico ocurre DURANTE la
    inferencia, asi que una lectura puntual al terminar no lo ve."""

    def __init__(self):
        super().__init__(daemon=True)
        self.parar = threading.Event()
        self.pico = -1
        self.muestras = 0

    def run(self):
        while not self.parar.is_set():
            v = vram_usada()
            self.muestras += 1
            if v > self.pico:
                self.pico = v
            self.parar.wait(CADENCIA_S)


hitos = []
mu = Muestreador()


def hito(nombre: str, t0: float):
    v = vram_usada()
    if v > mu.pico:
        mu.pico = v
    e = {"hito": nombre, "t_s": round(time.perf_counter() - t0, 3),
         "vram_usada_MiB": v, "pico_MiB": mu.pico}
    hitos.append(e)
    print(json.dumps(e, ensure_ascii=False), flush=True)
    return e


# ---------------------------------------------------------------- NVENC
def lanzar_nvenc():
    """`hevc_nvenc` con el tope DENTRO de la orden. Devuelve el Popen."""
    argv = ["ffmpeg", "-hide_banner", "-nostdin", "-y",
            "-t", str(NVENC_S), "-i", VIDEO,
            "-map", "0",                      # explicito (regla de diseno)
            "-c:v", "hevc_nvenc", "-b:v", "8M",
            "-c:a", "copy",
            "-f", "null", os.devnull]
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def cargar_ocr(meta, t0):
    """RapidOCR ONNX, `PP-OCRv6 small` + R6: la configuracion vigente (B11).

    Esta en una funcion porque hay que poder cargarlo ANTES o DESPUES del modelo
    de audio: el orden de carga es la variable de la fase `coresidente_inv`.
    """
    t = time.perf_counter()
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import (EngineType, LangDet, LangRec, ModelType, OCRVersion,
                          RapidOCR)
    meta["import_ocr_s"] = round(time.perf_counter() - t, 3)
    meta["torch_cuda"] = torch.cuda.is_available()   # trampa 12
    t = time.perf_counter()
    params = {
        "EngineConfig.onnxruntime.use_cuda": DISPOSITIVO == "cuda",
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion("PP-OCRv6"),
        "Rec.ocr_version": OCRVersion("PP-OCRv6"),
        "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
        "Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
        "Det.thresh": 0.2, "Det.box_thresh": 0.45,
        "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000,
    }
    lector = RapidOCR(params=params)
    meta["construccion_ocr_s"] = round(time.perf_counter() - t, 3)
    try:   # trampa 13: get_providers(), NUNCA get_device()
        meta["providers"] = list(lector.text_det.session.session.get_providers())
    except Exception as ex:
        meta["providers"] = f"{type(ex).__name__}: {ex}"
    hito("ocr_cargado", t0)
    return lector


def main():
    reloj = time.get_clock_info("perf_counter")   # trampa 62: la resolucion, antes
    d_ini = testigo_deriva()
    n_ini, ag1 = testigo_nivel()

    base = vram_usada()
    mu.pico = base
    mu.start()
    t0 = time.perf_counter()

    meta = {"fase": FASE, "etiqueta": ETIQ, "dispositivo": DISPOSITIVO,
            "whisper": WHISPER, "img": IMG, "audio": AUDIO, "video": VIDEO,
            "vram_base_MiB": base, "cadencia_s": CADENCIA_S,
            "reloj_resolucion_s": reloj.resolution, "reloj": "perf_counter",
            "via_entrada_ocr": "ruta",           # trampa 30: declarada
            "python": sys.executable}
    print(json.dumps({"meta": meta}, ensure_ascii=False), flush=True)

    CORES = ("coresidente", "coresidente_inv", "dos_procesos")
    quiere_audio = FASE in ("solo_audio",) + CORES
    quiere_ocr = FASE in ("solo_ocr",) + CORES
    quiere_nvenc = FASE in ("solo_nvenc",) + CORES
    #: `coresidente_inv` carga el OCR ANTES que el audio; `dos_procesos` no carga
    #: el OCR en este proceso en absoluto.
    ocr_primero = FASE == "coresidente_inv"
    ocr_fuera = FASE == "dos_procesos"

    modelo = lector = trabajador = None
    salida = {}

    if quiere_ocr and ocr_fuera:
        # El OCR en un proceso aparte, con el trabajador de `filex/sidecar.py`.
        # `filex` no esta instalado en este venv: se importa por ruta, que es
        # legitimo porque el paquete no tiene dependencias.
        sys.path.insert(0, RAIZ)
        from filex.sidecar import Trabajador
        trabajador = Trabajador("rapidocr", DISPOSITIVO, python=sys.executable)
        trabajador.arrancar()
        meta["trabajador"] = trabajador.meta
        meta["trabajador_arranque_s"] = round(trabajador.arrancado_en, 3)
        hito("ocr_cargado_fuera", t0)

    if quiere_ocr and ocr_primero:
        lector = cargar_ocr(meta, t0)

    # ---- carga de los modelos. En `coresidente` los dos quedan residentes ----
    if quiere_audio:
        t = time.perf_counter()
        from faster_whisper import WhisperModel
        meta["import_audio_s"] = round(time.perf_counter() - t, 3)
        t = time.perf_counter()
        modelo = WhisperModel(WHISPER, device=DISPOSITIVO,
                              compute_type="float16" if DISPOSITIVO == "cuda" else "int8")
        meta["construccion_audio_s"] = round(time.perf_counter() - t, 3)
        hito("audio_cargado", t0)

    if quiere_ocr and not ocr_primero and not ocr_fuera:
        lector = cargar_ocr(meta, t0)

    # ---- el trabajo, solapado en `coresidente` ----
    proc = None
    if quiere_nvenc:
        proc = lanzar_nvenc()
        hito("nvenc_lanzado", t0)

    def ocr(destino_txt=None):
        """Una pasada de OCR, por el camino que toque en esta fase."""
        t = time.perf_counter()
        if trabajador is not None:
            r = trabajador.pedir({"orden": "ocr", "ruta": IMG}, timeout=600)
            texto = r.get("texto", "")
        else:
            r = lector(IMG)
            texto = " ".join(r.txts) if r and r.txts else ""
        ms = round((time.perf_counter() - t) * 1000, 1)
        if destino_txt:
            with open(destino_txt, "w", encoding="utf-8") as f:
                f.write(texto)                   # fila N17: el TEXTO se guarda
        return texto, ms

    if quiere_ocr:
        texto, ms = ocr(os.path.join(SAL, "texto", f"{ETIQ}__ocr.txt"))
        salida["ocr_ms"] = ms
        salida["ocr_chars"] = len(texto)
        hito("ocr_hecho", t0)

    if quiere_audio:
        t = time.perf_counter()
        segs, info = modelo.transcribe(AUDIO, language="en", beam_size=5)
        trans = " ".join(s.text for s in segs)
        salida["audio_ms"] = round((time.perf_counter() - t) * 1000, 1)
        salida["audio_chars"] = len(trans)
        salida["audio_duracion_s"] = round(info.duration, 2)
        with open(os.path.join(SAL, "texto", f"{ETIQ}__audio.txt"), "w",
                  encoding="utf-8") as f:
            f.write(trans)
        hito("audio_hecho", t0)

    if proc is not None:
        try:
            _, err = proc.communicate(timeout=NVENC_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, err = proc.communicate()
            salida["nvenc_timeout"] = True
        salida["nvenc_rc"] = proc.returncode      # trampa 25: el rc SIEMPRE
        salida["nvenc_ok"] = proc.returncode == 0
        hito("nvenc_hecho", t0)

    # Segunda pasada de OCR ya con todo residente: el pico de un sidecar real no
    # es el de la carga, es el del trabajo con los modelos ya dentro.
    if quiere_ocr:
        _, salida["ocr2_ms"] = ocr()
        hito("ocr_hecho_2", t0)

    if trabajador is not None:
        # Censo del desechable del trabajador ANTES de cerrarlo: el punto 5 del
        # contrato no se puede verificar a posteriori (R21).
        salida["sobrantes_trabajador"] = trabajador.sobrantes()
        trabajador.cerrar()
        hito("trabajador_cerrado", t0)

    mu.parar.set()
    mu.join(timeout=5)

    d_fin = testigo_deriva()
    n_fin, ag2 = testigo_nivel()
    ruido = veredicto(d_ini, d_fin, n_ini, n_fin, ag1 or ag2)

    fin = {"evento": "fin", "fase": FASE, "etiqueta": ETIQ,
           "vram_base_MiB": base, "vram_pico_MiB": mu.pico,
           "coste_propio_MiB": mu.pico - base,
           "muestras_vram": mu.muestras,
           "total_s": round(time.perf_counter() - t0, 2),
           "salida": salida, "ruido": ruido}
    print(json.dumps(fin, ensure_ascii=False), flush=True)

    with open(os.path.join(OUT, f"{ETIQ}.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "hitos": hitos, "fin": fin}, f,
                  ensure_ascii=False, indent=2)


if __name__ == "__main__":
    os.makedirs(os.path.join(SAL, "texto"), exist_ok=True)
    main()
