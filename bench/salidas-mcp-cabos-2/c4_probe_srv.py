#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C4 — Servidor MCP de sonda (stdio, JSON-RPC 2.0, solo biblioteca estandar).

Derivado de bench/salidas-saturacion/stub_mcp.py (NO se modifica el original).
Anade lo que C4 necesita medir:
  - registra initialize (protocolo negociado, capacidades del cliente)  -> C4b
  - declara UN recurso y UN prompt, y registra resources/list, resources/read,
    prompts/list, prompts/get                                            -> C4c
  - sirve un catalogo de herramientas (name/description/inputSchema) cargado de
    STUB_CATALOG, para medir el coste de catalogo por tokens               -> C4d
  - registra tools/list con marca de tiempo relativa al arranque, para ver si el
    cliente lo pide y cuando.

Env:
  STUB_CATALOG : ruta al JSON con la lista de herramientas
  STUB_LOG     : ruta al JSONL de registro
  STUB_NAME    : nombre del servidor
"""
import json
import os
import sys
import time

CATALOG_PATH = os.environ["STUB_CATALOG"]
LOG_PATH = os.environ.get("STUB_LOG", "")
SERVER_NAME = os.environ.get("STUB_NAME", "filex-probe")
T0 = time.time()

with open(CATALOG_PATH, "r", encoding="utf-8") as fh:
    RAW = json.load(fh)

TOOLS = []
for t in RAW:
    entry = {"name": t["name"], "description": t.get("description") or "",
             "inputSchema": t["inputSchema"]}
    if t.get("annotations"):
        entry["annotations"] = t["annotations"]
    TOOLS.append(entry)
BY_NAME = {t["name"]: t for t in TOOLS}

RESOURCES = [{"uri": "filex://probe/nota", "name": "nota_filex",
              "title": "Nota de sonda FileX", "description": "Un recurso de prueba.",
              "mimeType": "text/plain"}]
PROMPTS = [{"name": "filex_probe_prompt", "title": "Prompt de sonda FileX",
            "description": "Un prompt de prueba de FileX.",
            "arguments": [{"name": "tema", "description": "tema", "required": True}]}]


def log(obj):
    obj["t"] = round(time.time() - T0, 3)
    if LOG_PATH:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def result(rid, payload):
    send({"jsonrpc": "2.0", "id": rid, "result": payload})


def error(rid, code, msg):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method")
        rid = req.get("id")

        if method == "initialize":
            params = req.get("params") or {}
            pv = params.get("protocolVersion") or "2024-11-05"
            log({"ev": "initialize", "protocolVersion_pedido": pv,
                 "client_capabilities": params.get("capabilities"),
                 "clientInfo": params.get("clientInfo")})
            result(rid, {
                "protocolVersion": pv,
                "capabilities": {"tools": {"listChanged": False},
                                 "resources": {"listChanged": False, "subscribe": False},
                                 "prompts": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": "0.0.0-probe"},
            })
        elif method in ("notifications/initialized", "notifications/cancelled"):
            log({"ev": method})
        elif method == "ping":
            result(rid, {})
        elif method == "tools/list":
            log({"ev": "tools/list", "n": len(TOOLS)})
            result(rid, {"tools": TOOLS})
        elif method == "resources/list":
            log({"ev": "resources/list", "n": len(RESOURCES)})
            result(rid, {"resources": RESOURCES})
        elif method == "resources/templates/list":
            log({"ev": "resources/templates/list"})
            result(rid, {"resourceTemplates": []})
        elif method == "resources/read":
            log({"ev": "resources/read", "uri": (req.get("params") or {}).get("uri")})
            result(rid, {"contents": [{"uri": (req.get("params") or {}).get("uri"),
                                       "mimeType": "text/plain",
                                       "text": "recurso servido por la sonda"}]})
        elif method == "prompts/list":
            log({"ev": "prompts/list", "n": len(PROMPTS)})
            result(rid, {"prompts": PROMPTS})
        elif method == "prompts/get":
            log({"ev": "prompts/get", "name": (req.get("params") or {}).get("name")})
            result(rid, {"messages": [{"role": "user", "content": {"type": "text",
                                       "text": "Habla del tema pedido."}}]})
        elif method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name")
            log({"ev": "tools/call", "tool": name, "args": params.get("arguments")})
            if name not in BY_NAME:
                result(rid, {"content": [{"type": "text",
                             "text": "Error: no existe %r" % name}], "isError": True})
            else:
                result(rid, {"content": [{"type": "text",
                             "text": "OK. sonda ejecutada."}], "isError": False})
        else:
            log({"ev": "metodo_desconocido", "method": method})
            if rid is not None:
                error(rid, -32601, "Method not found: %s" % method)


if __name__ == "__main__":
    main()
