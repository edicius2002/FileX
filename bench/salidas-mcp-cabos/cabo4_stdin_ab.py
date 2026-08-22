"""Cabo 4 — A/B de `stdin` heredado vs `stdin=DEVNULL` DENTRO de una sesion MCP real."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cabo4_deadlock as C  # noqa: E402

SRV = Path(__file__).with_name("cabo4_srv_stdin.py")
N = 5


class SesionPropia(C.Sesion):
    def __init__(self, etiqueta):
        self.etiqueta = etiqueta
        self.errlog = open(C.SALIDA / f"cabo4_stderr_{etiqueta}.txt", "wb")
        self.p = subprocess.Popen(
            [str(C.PY), str(SRV)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errlog,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        import queue
        import threading
        self.cola = queue.Queue()
        self.hilo = threading.Thread(target=self._leer, daemon=True)
        self.hilo.start()


def ronda(herramienta, n=N):
    reg = {"herramienta": herramienta, "n": n, "colgadas": 0, "resultados": []}
    for i in range(n):
        s = SesionPropia(f"{herramienta}_{i}")
        try:
            s.enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "cabo4ab", "version": "0"}}})
            s.esperar(1, 60)
            s.enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
            t0 = time.time()
            s.enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": herramienta, "arguments": {"timeout": 20.0}}})
            r = s.esperar(2, 90)
            ms = round((time.time() - t0) * 1000, 1)
            if r is None or r.get("_MUERTO"):
                reg["colgadas"] += 1
                reg["resultados"].append({"ms": ms, "texto": "SESION SIN RESPUESTA"})
            else:
                try:
                    txt = r["result"]["content"][0]["text"]
                except Exception:  # noqa: BLE001
                    txt = json.dumps(r)[:300]
                if "COLGADA" in txt:
                    reg["colgadas"] += 1
                reg["resultados"].append({"ms": ms, "texto": txt[:220]})
        finally:
            s.cerrar()
            time.sleep(0.5)
        print(f"  {herramienta} #{i}: {reg['resultados'][-1]['texto'][:150]}", flush=True)
    return reg


def main():
    out = {}
    for h in ("conv_heredado", "conv_devnull"):
        print(f"== {h} ==", flush=True)
        out[h] = ronda(h)
        print(f"   colgadas: {out[h]['colgadas']}/{out[h]['n']}", flush=True)
    (C.SALIDA / "cabo4_stdin_ab.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
