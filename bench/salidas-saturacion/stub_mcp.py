#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Servidor MCP stub (stdio, JSON-RPC 2.0, solo biblioteca estandar).

Sirve un catalogo de herramientas identico al de un servidor real
(name / description / inputSchema tal cual se capturaron en
bench/salidas-mcp-refs/multimedia/cat_*.json) pero NO ejecuta nada:
devuelve un resultado de exito sintetico y registra la llamada.

Motivo: el experimento mide QUE herramienta elige el modelo y con que
argumentos. Ejecutar de verdad video-audio-mcp cuelga la sesion en toda
conversion que reencodifica (deadlock documentado en bench/mcp-refs-multimedia.md).

Variables de entorno:
  STUB_CATALOG : ruta al JSON con la lista de herramientas
  STUB_LOG     : ruta al JSONL donde se registra cada tools/call
  STUB_NAME    : nombre del servidor anunciado en serverInfo
"""
import json
import os
import sys
import datetime

CATALOG_PATH = os.environ["STUB_CATALOG"]
LOG_PATH = os.environ.get("STUB_LOG", "")
SERVER_NAME = os.environ.get("STUB_NAME", "stub")

with open(CATALOG_PATH, "r", encoding="utf-8") as fh:
    RAW = json.load(fh)

# Solo los tres campos que el protocolo expone al modelo.
TOOLS = []
for t in RAW:
    entry = {
        "name": t["name"],
        "description": t.get("description") or "",
        "inputSchema": t["inputSchema"],
    }
    if t.get("annotations"):
        entry["annotations"] = t["annotations"]
    TOOLS.append(entry)

BY_NAME = {t["name"]: t for t in TOOLS}


def log(obj):
    if not LOG_PATH:
        return
    obj["ts"] = datetime.datetime.now().isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def result(rid, payload):
    send({"jsonrpc": "2.0", "id": rid, "result": payload})


def error(rid, code, msg):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}})


def fake_output(name, args):
    """Salida sintetica plausible: devuelve una ruta, nunca contenido."""
    for key in ("output_path", "output_video_path", "output_audio_path",
                "output_media_path", "output_file", "output"):
        if isinstance(args.get(key), str):
            return args[key]
    if name in ("ffmpeg_get_info",):
        return ('{"duration": 123.4, "width": 1920, "height": 1080, '
                '"video_codec": "h264", "audio_codec": "aac", "audio_bitrate": "320k"}')
    return "/salida/resultado.out"


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
            pv = (req.get("params") or {}).get("protocolVersion") or "2024-11-05"
            result(rid, {
                "protocolVersion": pv,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": "0.0.0-stub"},
            })
        elif method in ("notifications/initialized", "notifications/cancelled"):
            pass  # notificacion: sin respuesta
        elif method == "ping":
            result(rid, {})
        elif method == "tools/list":
            log({"ev": "tools/list", "n": len(TOOLS)})
            result(rid, {"tools": TOOLS})
        elif method == "resources/list":
            result(rid, {"resources": []})
        elif method == "resources/templates/list":
            result(rid, {"resourceTemplates": []})
        elif method == "prompts/list":
            result(rid, {"prompts": []})
        elif method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            log({"ev": "tools/call", "tool": name, "args": args})
            if name not in BY_NAME:
                result(rid, {
                    "content": [{"type": "text",
                                 "text": "Error: no existe la herramienta %r." % name}],
                    "isError": True,
                })
            else:
                result(rid, {
                    "content": [{"type": "text",
                                 "text": "OK. Operacion completada. Salida: %s"
                                         % fake_output(name, args)}],
                    "isError": False,
                })
        else:
            if rid is not None:
                error(rid, -32601, "Method not found: %s" % method)


if __name__ == "__main__":
    main()
