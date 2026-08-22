"""Cabo 4 — diagnostico del cuelgue INTERMITENTE de `concatenate_videos` (2 videos).

Todas sus invocaciones pasan `-y`, y aun asi la llamada no vuelve 2 de cada 3 veces.
Este script deja la llamada corriendo y, a intervalos, fotografia el arbol de procesos
para ver QUIEN esta vivo cuando la sesion esta colgada.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cabo4_deadlock as C  # noqa: E402


def arbol(pid_raiz):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True, timeout=60)
    try:
        procs = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        return []
    porpadre = {}
    for p in procs:
        porpadre.setdefault(p["ParentProcessId"], []).append(p)
    salida, pila = [], [pid_raiz]
    while pila:
        pid = pila.pop()
        for h in porpadre.get(pid, []):
            salida.append({"pid": h["ProcessId"], "padre": h["ParentProcessId"],
                           "nombre": h["Name"],
                           "cmd": (h.get("CommandLine") or "")[:260]})
            pila.append(h["ProcessId"])
    return salida


def main():
    C.TRABAJO.mkdir(parents=True, exist_ok=True)
    ent = str(C.RAIZ / "corpus/video/trivial.mp4").replace("\\", "/")
    sal = str(C.TRABAJO / "g3diag.mp4").replace("\\", "/")
    Path(sal).write_bytes(b"BASURA" * 32)

    s = C.Sesion("G3_diagnostico")
    reg = {"muestras": []}
    try:
        s.enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "cabo4diag", "version": "0"}}})
        s.esperar(1, 60)
        s.enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
        t0 = time.time()
        s.enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "concatenate_videos",
            "arguments": {"video_paths": [ent, ent], "output_video_path": sal}}})
        respondio = False
        for _ in range(6):
            r = s.esperar(2, 10)
            m = {"t": round(time.time() - t0, 1), "hijos": arbol(s.p.pid)}
            reg["muestras"].append(m)
            print(json.dumps(m, ensure_ascii=False)[:900], flush=True)
            if r is not None:
                respondio = True
                reg["respuesta"] = json.dumps(r)[:400]
                break
        reg["respondio"] = respondio
        reg["segundos"] = round(time.time() - t0, 1)
    finally:
        s.cerrar()
    Path(__file__).with_name("cabo4_g3_diagnostico.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("respondio:", reg.get("respondio"), reg.get("segundos"))


if __name__ == "__main__":
    main()
