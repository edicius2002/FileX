"""Cabo 4 — Arnes ACOTADO de deadlock contra `video-audio-mcp`.

Diseno defensivo (regla 4 del encargo):
  - JSON-RPC crudo por stdio: sin SDK, sin hilos del cliente que puedan colgarse.
  - lector de stdout en un hilo DEMONIO con cola: si el servidor no responde, el hilo
    muere con el proceso y no bloquea la salida.
  - TIMEOUT DURO por llamada; al vencer, `taskkill /F /T /PID` mata el ARBOL entero.
  - una sesion NUEVA por caso: un caso colgado nunca contamina al siguiente.
  - inventario de procesos `ffmpeg.exe` antes y despues, para detectar huerfanos.

Cada caso se ejecuta en un servidor recien arrancado. Nada se reutiliza.
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
SALIDA = RAIZ / "bench/salidas-mcp-cabos"
TRABAJO = SALIDA / "cabo4_trabajo"
PY = RAIZ / ".venv-mcp-vam/Scripts/python.exe"
SERVIDOR = RAIZ / "repos/mcp-refs/video-audio-mcp/server.py"
TIMEOUT_LLAMADA = float(os.environ.get("CABO4_TIMEOUT", "45"))
TIMEOUT_ARRANQUE = 60.0


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
    except Exception:  # noqa: BLE001
        return []


def matar_arbol(pid):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=30)
    except Exception:  # noqa: BLE001
        pass


class Sesion:
    def __init__(self, etiqueta):
        self.etiqueta = etiqueta
        self.errlog = open(SALIDA / f"cabo4_stderr_{etiqueta}.txt", "wb")
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
        except Exception:  # noqa: BLE001
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
            except Exception:  # noqa: BLE001
                continue
            if m.get("id") == id_esperado:
                return m
        return None  # TIMEOUT

    def cerrar(self):
        matar_arbol(self.p.pid)
        try:
            self.p.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        self.errlog.close()


def caso(etiqueta, herramienta, args, preexistente=None):
    """Ejecuta UN caso en su propia sesion. Devuelve el registro."""
    TRABAJO.mkdir(parents=True, exist_ok=True)
    reg = {"caso": etiqueta, "herramienta": herramienta, "args": args,
           "salida_preexistente": bool(preexistente)}
    if preexistente:
        Path(preexistente).parent.mkdir(parents=True, exist_ok=True)
        Path(preexistente).write_bytes(b"BASURA-PREEXISTENTE" * 8)
        reg["bytes_preexistentes"] = Path(preexistente).stat().st_size

    ff_antes = pids_ffmpeg()
    s = Sesion(etiqueta)
    t0 = time.time()
    try:
        s.enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "cabo4", "version": "0"}}})
        ini = s.esperar(1, TIMEOUT_ARRANQUE)
        if ini is None or ini.get("_MUERTO"):
            reg["veredicto"] = "NO ARRANCA"
            return reg
        reg["ms_arranque"] = round((time.time() - t0) * 1000, 1)
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
            except Exception:  # noqa: BLE001
                txt = json.dumps(r)[:400]
            reg["isError"] = r.get("result", {}).get("isError")
            reg["respuesta"] = txt[:500]
            reg["veredicto"] = "RESPONDE"
    finally:
        s.cerrar()
        time.sleep(1.0)
        ff_despues = pids_ffmpeg()
        reg["ffmpeg_huerfanos"] = sorted(set(ff_despues) - set(ff_antes))
        for pid in reg["ffmpeg_huerfanos"]:
            matar_arbol(pid)
        sal = args.get("output_video_path") or args.get("output_audio_path") \
            or args.get("output_media_path")
        if sal and Path(sal).exists():
            reg["bytes_salida"] = Path(sal).stat().st_size
    return reg


def main():
    if TRABAJO.exists():
        shutil.rmtree(TRABAJO, ignore_errors=True)
    TRABAJO.mkdir(parents=True, exist_ok=True)
    ent = str(RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")
    t = str(TRABAJO).replace("\\", "/")

    casos = []

    # --- G4: no toca ffmpeg (control positivo) ---
    casos.append(("G4_health_check", "health_check", {}, None))

    # --- G1: los 9 del helper `_run_ffmpeg_with_fallback` (server.py:332-348).
    #     Con la salida YA EXISTENTE, el prompt salta en el intento PRIMARIO.
    casos.append(("G1_set_video_resolution_preexistente", "set_video_resolution",
                  {"input_video_path": ent, "output_video_path": f"{t}/g1_res.mkv",
                   "resolution": "320x240"}, f"{t}/g1_res.mkv"))
    casos.append(("G1_set_video_codec_preexistente", "set_video_codec",
                  {"input_video_path": ent, "output_video_path": f"{t}/g1_cod.mp4",
                   "video_codec": "libx264"}, f"{t}/g1_cod.mp4"))
    #     Control: el MISMO G1 sin salida preexistente y con formato que admite copia.
    casos.append(("G1_set_video_resolution_control", "set_video_resolution",
                  {"input_video_path": ent, "output_video_path": f"{t}/g1_ctl.mkv",
                   "resolution": "320x240"}, None))

    # --- G2: los 15 con ffmpeg-python en el cuerpo. Solo disparan si la salida existe.
    casos.append(("G2_convert_video_properties_preexistente", "convert_video_properties",
                  {"input_video_path": ent, "output_video_path": f"{t}/g2b_pre.mp4",
                   "target_format": "mp4", "resolution": "320x240"},
                  f"{t}/g2b_pre.mp4"))
    casos.append(("G2_trim_video_preexistente", "trim_video",
                  {"video_path": ent, "output_video_path": f"{t}/g2c_pre.mp4",
                   "start_time": "0", "end_time": "1"}, f"{t}/g2c_pre.mp4"))
    #     Control: la misma herramienta SIN salida preexistente.
    casos.append(("G2_convert_video_properties_control", "convert_video_properties",
                  {"input_video_path": ent, "output_video_path": f"{t}/g2b_ctl.mp4",
                   "target_format": "mp4", "resolution": "320x240"}, None))

    # --- G3: mixtas. La via `subprocess` lleva -y; la via ffmpeg-python no.
    #     (a) 2 videos -> rama subprocess (server.py:891-1016), lleva -y
    casos.append(("G3_concatenate_2videos_preexistente", "concatenate_videos",
                  {"video_paths": [ent, ent], "output_video_path": f"{t}/g3_pre.mp4"},
                  f"{t}/g3_pre.mp4"))
    #     (b) 1 solo video -> rama ffmpeg-python (server.py:851), SIN overwrite_output
    casos.append(("G3_concatenate_1video_preexistente", "concatenate_videos",
                  {"video_paths": [ent], "output_video_path": f"{t}/g3b_pre.mp4"},
                  f"{t}/g3b_pre.mp4"))

    res = []
    for etiqueta, herr, args, pre in casos:
        print(f"[cabo4] {etiqueta} …", flush=True)
        r = caso(etiqueta, herr, args, pre)
        print(f"        -> {r['veredicto']} ({r.get('ms_llamada')} ms) "
              f"huerfanos={r.get('ffmpeg_huerfanos')}", flush=True)
        res.append(r)

    (SALIDA / "cabo4_resultados.json").write_text(
        json.dumps({"timeout_por_llamada_s": TIMEOUT_LLAMADA, "casos": res},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
