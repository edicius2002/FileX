"""C4a — Exhaustividad del deadlock sobre las 20 herramientas de `video-audio-mcp`
que `mcp-cabos-sueltos.md` §4 clasifico por AST pero NO ejecuto.

Reutiliza el diseno defensivo de `bench/salidas-mcp-cabos/cabo4_deadlock.py`
(JSON-RPC crudo, lector demonio, timeout duro, taskkill /F /T del arbol, sesion nueva
por caso, inventario de ffmpeg.exe). NO modifica el original: es una copia adaptada.

Objetivo: confirmar o REFUTAR que las 20 restantes cuelgan con la salida preexistente.
Una herramienta que NO cuelgue es el resultado interesante. Por eso se distingue:
  DEADLOCK            -> sin respuesta en el timeout (mecanismo confirmado)
  RESPONDE(exito)     -> ffmpeg escribio pese a la salida preexistente (REFUTARIA)
  RESPONDE(error-ff)  -> ffmpeg fallo ANTES del prompt de sobrescritura (inputs no
                         validos para esta herramienta): NO refuta el mecanismo, es
                         un fallo temprano; se marca aparte.
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
SALIDA = RAIZ / "bench/salidas-mcp-cabos-2"
TRABAJO = SALIDA / "c4a_trabajo"
PY = RAIZ / ".venv-mcp-vam/Scripts/python.exe"
SERVIDOR = RAIZ / "repos/mcp-refs/video-audio-mcp/server.py"
TIMEOUT_LLAMADA = float(os.environ.get("C4A_TIMEOUT", "18"))
TIMEOUT_ARRANQUE = 60.0

VID = str(RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")      # solo video
VIDA = str(RAIZ / "corpus/video/tipico.mp4").replace("\\", "/")      # video + audio aac
AUD = str(RAIZ / "corpus/audio/tipico.mp3").replace("\\", "/")       # audio pequeno
IMG = str(RAIZ / "corpus/imagen/trivial.png").replace("\\", "/")


def pids_ffmpeg():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=20)
        out = []
        for linea in r.stdout.splitlines():
            partes = [p.strip('"') for p in linea.split('","')]
            if len(partes) > 1 and partes[0].lower().startswith("ffmpeg"):
                out.append(int(partes[1]))
        return sorted(out)
    except Exception:
        return []


def matar_arbol(pid):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=30)
    except Exception:
        pass


class Sesion:
    def __init__(self, etiqueta):
        self.errlog = open(SALIDA / f"c4a_stderr_{etiqueta}.txt", "wb")
        self.p = subprocess.Popen(
            [str(PY), str(SERVIDOR)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errlog,
            cwd=str(SERVIDOR.parent),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        self.cola = queue.Queue()
        self.hilo = threading.Thread(target=self._leer, daemon=True)
        self.hilo.start()

    def _leer(self):
        try:
            for linea in self.p.stdout:
                self.cola.put(linea)
        except Exception:
            pass
        self.cola.put(None)

    def enviar(self, obj):
        self.p.stdin.write((json.dumps(obj) + "\n").encode())
        self.p.stdin.flush()

    def esperar(self, id_esperado, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                linea = self.cola.get(timeout=0.25)
            except queue.Empty:
                continue
            if linea is None:
                return {"_MUERTO": True}
            try:
                m = json.loads(linea.decode("utf-8", "replace"))
            except Exception:
                continue
            if m.get("id") == id_esperado:
                return m
        return None

    def cerrar(self):
        matar_arbol(self.p.pid)
        try:
            self.p.wait(timeout=10)
        except Exception:
            pass
        self.errlog.close()


def clasificar_respuesta(txt):
    t = (txt or "").lower()
    # senales de que ffmpeg fallo antes del prompt (fallo temprano, no cuelga)
    errores = ["error", "failed", "no such file", "invalid", "does not contain",
               "matches no streams", "traceback", "exception"]
    exito = ["success", "successfully", "saved", "created", "completed", "done"]
    if any(e in t for e in exito) and not any(e in t for e in errores):
        return "RESPONDE(exito)"
    if any(e in t for e in errores):
        return "RESPONDE(error-ff)"
    return "RESPONDE(?)"


def caso(etiqueta, herramienta, args, salida_key):
    TRABAJO.mkdir(parents=True, exist_ok=True)
    salida = args[salida_key]
    reg = {"caso": etiqueta, "herramienta": herramienta, "salida_preexistente": True}
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_bytes(b"BASURA-PREEXISTENTE" * 8)
    reg["bytes_preexistentes"] = Path(salida).stat().st_size

    ff_antes = pids_ffmpeg()
    s = Sesion(etiqueta)
    t0 = time.time()
    try:
        s.enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "c4a", "version": "0"}}})
        ini = s.esperar(1, TIMEOUT_ARRANQUE)
        if ini is None or ini.get("_MUERTO"):
            reg["veredicto"] = "NO ARRANCA"
            return reg
        s.enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
        t1 = time.time()
        s.enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": herramienta, "arguments": args}})
        r = s.esperar(2, TIMEOUT_LLAMADA)
        reg["ms_llamada"] = round((time.time() - t1) * 1000, 1)
        if r is None:
            reg["veredicto"] = f"DEADLOCK (sin respuesta en {TIMEOUT_LLAMADA}s)"
        elif r.get("_MUERTO"):
            reg["veredicto"] = "SESION MUERTA"
        else:
            txt = ""
            try:
                txt = r["result"]["content"][0]["text"]
            except Exception:
                txt = json.dumps(r)[:400]
            reg["isError"] = r.get("result", {}).get("isError")
            reg["respuesta"] = txt[:300]
            reg["veredicto"] = clasificar_respuesta(txt)
            # bytes de salida: si sigue siendo la basura, no la reescribio
            if Path(salida).exists():
                reg["bytes_salida"] = Path(salida).stat().st_size
    finally:
        s.cerrar()
        time.sleep(0.8)
        ff_despues = pids_ffmpeg()
        reg["ffmpeg_huerfanos"] = sorted(set(ff_despues) - set(ff_antes))
        for pid in reg["ffmpeg_huerfanos"]:
            matar_arbol(pid)
    return reg


def main():
    if TRABAJO.exists():
        shutil.rmtree(TRABAJO, ignore_errors=True)
    TRABAJO.mkdir(parents=True, exist_ok=True)
    t = str(TRABAJO).replace("\\", "/")

    # SRT minimo para add_subtitles
    srt = TRABAJO / "sub.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
    srtp = str(srt).replace("\\", "/")

    # (grupo, etiqueta, herramienta, args, salida_key)
    casos = [
        # --- G1 restantes (6): via _run_ffmpeg_with_fallback ---
        ("G1", "set_video_bitrate", {"input_video_path": VID, "output_video_path": f"{t}/g1_vbr.mp4", "video_bitrate": "500k"}, "output_video_path"),
        ("G1", "set_video_frame_rate", {"input_video_path": VID, "output_video_path": f"{t}/g1_fps.mp4", "frame_rate": 24}, "output_video_path"),
        ("G1", "set_video_audio_track_codec", {"input_video_path": VIDA, "output_video_path": f"{t}/g1_atc.mp4", "audio_codec": "aac"}, "output_video_path"),
        ("G1", "set_video_audio_track_bitrate", {"input_video_path": VIDA, "output_video_path": f"{t}/g1_atb.mp4", "audio_bitrate": "128k"}, "output_video_path"),
        ("G1", "set_video_audio_track_sample_rate", {"input_video_path": VIDA, "output_video_path": f"{t}/g1_ats.mp4", "audio_sample_rate": 44100}, "output_video_path"),
        ("G1", "set_video_audio_track_channels", {"input_video_path": VIDA, "output_video_path": f"{t}/g1_atch.mp4", "audio_channels": 2}, "output_video_path"),
        # --- G2 restantes (13): ffmpeg-python en el cuerpo ---
        ("G2", "convert_video_format", {"input_video_path": VID, "output_video_path": f"{t}/g2_cvf.mkv", "target_format": "mkv"}, "output_video_path"),
        ("G2", "change_aspect_ratio", {"video_path": VID, "output_video_path": f"{t}/g2_ar.mp4", "target_aspect_ratio": "1:1"}, "output_video_path"),
        ("G2", "change_video_speed", {"video_path": VID, "output_video_path": f"{t}/g2_spd.mp4", "speed_factor": 2.0}, "output_video_path"),
        ("G2", "add_text_overlay", {"video_path": VID, "output_video_path": f"{t}/g2_txt.mp4", "text_elements": [{"text": "Hola", "start_time": "0", "end_time": "1"}]}, "output_video_path"),
        ("G2", "add_image_overlay", {"video_path": VID, "output_video_path": f"{t}/g2_img.mp4", "image_path": IMG}, "output_video_path"),
        ("G2", "add_subtitles", {"video_path": VID, "srt_file_path": srtp, "output_video_path": f"{t}/g2_sub.mp4"}, "output_video_path"),
        ("G2", "add_basic_transitions", {"video_path": VID, "output_video_path": f"{t}/g2_trn.mp4", "transition_type": "fade_in", "duration_seconds": 0.5}, "output_video_path"),
        ("G2", "extract_audio_from_video", {"video_path": VIDA, "output_audio_path": f"{t}/g2_ext.mp3"}, "output_audio_path"),
        ("G2", "convert_audio_format", {"input_audio_path": AUD, "output_audio_path": f"{t}/g2_caf.wav", "target_format": "wav"}, "output_audio_path"),
        ("G2", "convert_audio_properties", {"input_audio_path": AUD, "output_audio_path": f"{t}/g2_cap.mp3", "target_format": "mp3", "bitrate": "128k"}, "output_audio_path"),
        ("G2", "set_audio_bitrate", {"input_audio_path": AUD, "output_audio_path": f"{t}/g2_abr.mp3", "bitrate": "128k"}, "output_audio_path"),
        ("G2", "set_audio_sample_rate", {"input_audio_path": AUD, "output_audio_path": f"{t}/g2_asr.mp3", "sample_rate": 44100}, "output_audio_path"),
        ("G2", "set_audio_channels", {"input_audio_path": AUD, "output_audio_path": f"{t}/g2_ach.mp3", "channels": 2}, "output_audio_path"),
        ("G2", "remove_silence", {"media_path": AUD, "output_media_path": f"{t}/g2_sil.mp3"}, "output_media_path"),
        # --- G3 restante (1): add_b_roll ---
        ("G3", "add_b_roll", {"main_video_path": VIDA, "broll_clips": [{"clip_path": VID, "insert_at_timestamp": "0"}], "output_video_path": f"{t}/g3_broll.mp4"}, "output_video_path"),
    ]

    res = []
    for grupo, herr, args, sk in casos:
        etiqueta = f"{grupo}_{herr}"
        print(f"[c4a] {etiqueta} ...", flush=True)
        r = caso(etiqueta, herr, args, sk)
        r["grupo"] = grupo
        print(f"       -> {r['veredicto']} ({r.get('ms_llamada')} ms) huerf={r.get('ffmpeg_huerfanos')}", flush=True)
        res.append(r)

    (SALIDA / "c4a_resultados.json").write_text(
        json.dumps({"timeout_por_llamada_s": TIMEOUT_LLAMADA,
                    "n": len(res), "casos": res}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # resumen
    from collections import Counter
    c = Counter(r["veredicto"].split(" ")[0] for r in res)
    print("RESUMEN:", dict(c), flush=True)


if __name__ == "__main__":
    main()
