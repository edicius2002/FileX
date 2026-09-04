"""Servidor MCP sonda de JSON-RPC CRUDO: qué URI emite el cliente en `roots/list`.

Copia adaptada de `bench/salidas-tasks-protocolo/srv_sonda_initialize.py`
(worker4, ronda 16) — `CLAUDE.md` §1 manda copiar el arnés compartido antes de
tocarlo. Lo que se añade: tras `notifications/initialized`, el servidor EMITE
una petición `roots/list` (que es servidor -> cliente) y registra la respuesta
literal.

La pregunta que contesta es la de `CLAUDE.md` §5 —*sondear capacidades en
ejecución, no deducirlas*—: la decisión de N37 depende de qué FORMA de `file://`
emiten los clientes reales, no de lo que RFC 8089 permita emitir.

No usa el SDK a propósito: con el SDK por medio se mide el SDK.

Lo lanza Claude Code vía `--mcp-config`; ver el MANIFIESTO para la orden exacta.
"""

import json
import os
import sys
import time

SALIDA = os.environ.get("FILEX_SONDA_SALIDA", "r_roots.jsonl")
PROTO = os.environ.get("FILEX_SONDA_PROTO", "")
T0 = time.time()

#: id de la petición que hacemos NOSOTROS al cliente. Alto para no chocar.
ID_ROOTS = 9001


def anota(clase, dato):
    with open(SALIDA, "a", encoding="utf-8") as f:
        f.write(json.dumps(
            {"t_ms": round((time.time() - T0) * 1000, 3), "clase": clase, "dato": dato},
            ensure_ascii=False) + "\n")


def envia(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def responde(id_, resultado):
    envia({"jsonrpc": "2.0", "id": id_, "result": resultado})


def pide_roots():
    """Petición servidor -> cliente. Su respuesta llega por stdin con este id."""
    p = {"jsonrpc": "2.0", "id": ID_ROOTS, "method": "roots/list"}
    anota("pedimos_roots", p)
    envia(p)


def main():
    anota("arranque", {
        "argv": sys.argv,
        "cwd_del_servidor": os.getcwd(),
        "proto_ofrecido": PROTO or "(eco del cliente)",
    })
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

        # --- la respuesta a NUESTRA petición: no lleva `method`, lleva nuestro id
        if metodo is None and msg.get("id") == ID_ROOTS:
            anota("RESPUESTA_ROOTS", msg)
            continue

        if metodo == "initialize":
            pedida = (msg.get("params") or {}).get("protocolVersion")
            # Trampa 117: se hace ECO de la era que el cliente pide. Ofrecer una
            # superior hace que el cliente descarte el servidor EN SILENCIO.
            usar = PROTO or pedida
            caps = (msg.get("params") or {}).get("capabilities") or {}
            anota("capacidades_del_cliente", caps)
            res = {
                "protocolVersion": usar,
                "serverInfo": {"name": "filex-sonda-roots", "version": "0.0.1"},
                "capabilities": {"tools": {}},
            }
            anota("respondemos_initialize", res)
            responde(msg.get("id"), res)
        elif metodo == "notifications/initialized":
            # Ya se puede preguntar. Es el único momento válido.
            pide_roots()
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
            envia({"jsonrpc": "2.0", "id": msg["id"],
                   "error": {"code": -32601, "message": "no implementado en la sonda"}})
    anota("fin_stdin", {})


if __name__ == "__main__":
    main()
