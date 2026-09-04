"""Servidor MCP sonda de JSON-RPC CRUDO sobre stdio.

No usa el SDK a proposito: la pregunta es que negocia EL CLIENTE, y con el SDK
por medio se mide el SDK. Registra literalmente el `initialize` que llega y
responde declarando la capacidad `tasks` para ver si el cliente la tolera.

La era que ofrece el servidor se fija con FILEX_SONDA_PROTO (por defecto la que
el cliente pida). Todo lo recibido se vuelca a FILEX_SONDA_SALIDA.

Uso: lo lanza Claude Code via --mcp-config. Ver `medir_cliente.py`.
"""

import json
import os
import sys
import time

SALIDA = os.environ.get("FILEX_SONDA_SALIDA", "sonda_initialize.jsonl")
PROTO = os.environ.get("FILEX_SONDA_PROTO", "")
T0 = time.time()


def anota(clase, dato):
    with open(SALIDA, "a", encoding="utf-8") as f:
        f.write(json.dumps(
            {"t_ms": round((time.time() - T0) * 1000, 3), "clase": clase, "dato": dato},
            ensure_ascii=False) + "\n")


def responde(id_, resultado):
    sys.stdout.write(json.dumps(
        {"jsonrpc": "2.0", "id": id_, "result": resultado}) + "\n")
    sys.stdout.flush()


def main():
    anota("arranque", {"argv": sys.argv, "proto_ofrecido": PROTO or "(eco del cliente)"})
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            msg = json.loads(linea)
        except Exception as e:
            anota("ilegible", {"linea": linea[:400], "error": str(e)})
            continue
        metodo = msg.get("method")
        anota("recibido", msg)

        if metodo == "initialize":
            pedida = (msg.get("params") or {}).get("protocolVersion")
            usar = PROTO or pedida
            # Declaramos `tasks` a proposito: si el cliente la rechaza o la
            # ignora, se ve aqui y no en una deduccion.
            res = {
                "protocolVersion": usar,
                "serverInfo": {"name": "filex-sonda", "version": "0.0.1"},
                "capabilities": {
                    "tools": {},
                    "tasks": {"list": {}, "cancel": {},
                              "requests": {"tools": {"call": {}}}},
                },
            }
            anota("respondemos_initialize", res)
            responde(msg.get("id"), res)
        elif metodo == "tools/list":
            responde(msg.get("id"), {"tools": [{
                "name": "sonda_nula",
                "description": "No hace nada. Existe para que el catalogo no este vacio.",
                "inputSchema": {"type": "object", "properties": {}},
            }]})
        elif metodo in ("resources/list", "prompts/list"):
            clave = "resources" if metodo.startswith("resources") else "prompts"
            responde(msg.get("id"), {clave: []})
        elif metodo and metodo.startswith("notifications/"):
            pass  # las notificaciones no llevan respuesta
        elif "id" in msg:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": msg["id"],
                "error": {"code": -32601, "message": "no implementado en la sonda"},
            }) + "\n")
            sys.stdout.flush()
    anota("fin_stdin", {})


if __name__ == "__main__":
    main()
