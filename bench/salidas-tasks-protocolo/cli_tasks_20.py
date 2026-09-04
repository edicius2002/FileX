"""Cliente de JSON-RPC CRUDO contra `srv_tasks_20.py`.

Crudo a proposito: si el cliente fuera el del SDK se mediria el SDK. Aqui la
pregunta es si un servidor `mcp 2.0.0` RESPONDE a `tasks/*` registrados a mano.

    .venv-mcp-filex\\Scripts\\python.exe bench/salidas-tasks-protocolo/cli_tasks_20.py
"""

import json
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(AQUI, "srv_tasks_20.py")
TOPE_S = 30  # tope DENTRO del arnes (trampa 52): el hijo se mata al salir


def main():
    R = {"tope_s": TOPE_S, "pasos": []}
    p = subprocess.Popen(
        [sys.executable, SRV],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1,
    )
    t0 = time.time()

    def envia(msg):
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()

    def lee():
        # No bloquea para siempre: el tope lo impone el `communicate` final.
        linea = p.stdout.readline()
        if not linea:
            return None
        return json.loads(linea)

    def paso(nombre, msg, espera_respuesta=True):
        envia(msg)
        r = lee() if espera_respuesta else None
        R["pasos"].append({
            "paso": nombre,
            "t_ms": round((time.time() - t0) * 1000, 2),
            "enviado": msg.get("method"),
            "respuesta": r,
        })
        return r

    try:
        paso("initialize", {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2025-11-25",
                                       "capabilities": {"tasks": {}},
                                       "clientInfo": {"name": "cli-sonda",
                                                      "version": "0.0.1"}}})
        envia({"jsonrpc": "2.0", "method": "notifications/initialized"})
        paso("tools/list", {"jsonrpc": "2.0", "id": 2, "method": "tools/list",
                            "params": {}})
        paso("tasks/get", {"jsonrpc": "2.0", "id": 3, "method": "tasks/get",
                           "params": {"taskId": "t-42"}})
        paso("tasks/list", {"jsonrpc": "2.0", "id": 4, "method": "tasks/list",
                            "params": {}})
        paso("tasks/cancel", {"jsonrpc": "2.0", "id": 5, "method": "tasks/cancel",
                              "params": {"taskId": "t-42"}})
    except Exception as e:
        R["error_arnes"] = "%s: %s" % (type(e).__name__, e)
    finally:
        try:
            p.stdin.close()
        except Exception:
            pass
        try:
            _, err = p.communicate(timeout=TOPE_S)
        except subprocess.TimeoutExpired:
            p.kill()
            _, err = p.communicate()
            R["tope_agotado"] = True
        R["rc_servidor"] = p.returncode
        R["stderr_servidor_cola"] = (err or "").strip().splitlines()[-6:]

    sal = os.path.join(AQUI, "r_tasks_20.json")
    with open(sal, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, ensure_ascii=False)
    print(json.dumps(R, indent=2, ensure_ascii=False))
    print("\n-> %s" % sal)


if __name__ == "__main__":
    main()
