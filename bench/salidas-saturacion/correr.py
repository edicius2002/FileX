#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Arnes del experimento C3: saturacion de catalogo de herramientas MCP.

Lanza Claude Code en modo headless (-p) contra un servidor MCP stub que
sirve un catalogo real (27 herramientas de video-audio-mcp, o 8 de
ffmpeg-mcp-lite) y registra QUE herramientas elige el modelo y con que
argumentos. No ejecuta ninguna conversion.

Uso:
  python correr.py --modelo haiku --reps 8 --salida runs_haiku.jsonl
"""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
import threading
import concurrent.futures as cf

BASE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.environ.get(
    "CLAUDE_CODE_EXECPATH",
    r"C:\Users\krato\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")

CATALOGOS = {
    "A": os.path.join(BASE, "catalogo_A_vam27.json"),
    "C": os.path.join(BASE, "catalogo_C_vam14.json"),
    "B": os.path.join(BASE, "catalogo_B_lite8.json"),
}
ORDEN = ("A", "C", "B")


def escribir_cfg(ruta_cfg, catalogo, log):
    cfg = {"mcpServers": {"mm": {
        "type": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE, "stub_mcp.py")],
        "env": {"STUB_CATALOG": catalogo, "STUB_NAME": "mm", "STUB_LOG": log},
    }}}
    with open(ruta_cfg, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)


def una_ejecucion(tmp, modelo, sistema, prompt, catalogo, timeout):
    uid = uuid.uuid4().hex[:10]
    log = os.path.join(tmp, "log_%s.jsonl" % uid)
    cfg = os.path.join(tmp, "cfg_%s.json" % uid)
    escribir_cfg(cfg, catalogo, log)

    cmd = [CLAUDE, "-p", prompt,
           "--model", modelo,
           "--system-prompt", sistema,
           "--tools", "",
           "--strict-mcp-config", "--mcp-config", cfg,
           "--setting-sources", "",
           "--disable-slash-commands",
           "--no-session-persistence",
           "--permission-mode", "bypassPermissions",
           "--output-format", "json"]

    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        salida, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        salida, err, rc = "", "TIMEOUT tras %ds" % timeout, -9
    dur = time.time() - t0

    meta = {}
    try:
        meta = json.loads(salida)
    except Exception:
        pass

    llamadas = []
    n_list = 0
    if os.path.exists(log):
        with open(log, "r", encoding="utf-8") as fh:
            for linea in fh:
                try:
                    ev = json.loads(linea)
                except Exception:
                    continue
                if ev.get("ev") == "tools/call":
                    llamadas.append({"tool": ev["tool"], "args": ev["args"]})
                elif ev.get("ev") == "tools/list":
                    n_list += 1

    return {
        "rc": rc,
        "dur_s": round(dur, 2),
        "llamadas": llamadas,
        "herramientas": [c["tool"] for c in llamadas],
        "n_tools_list": n_list,
        "texto": (meta.get("result") or "")[:600],
        "coste_usd": meta.get("total_cost_usd"),
        "turnos": meta.get("num_turns"),
        "is_error": meta.get("is_error"),
        "uso": meta.get("usage", {}),
        "stderr": (err or "")[:400],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="haiku")
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--tareas", default=None, help="ids separados por coma")
    ap.add_argument("--tmp", default=None)
    ap.add_argument("--hilos", type=int, default=1)
    args = ap.parse_args()

    spec = json.load(open(os.path.join(BASE, "tareas.json"), encoding="utf-8"))
    tareas = spec["tareas"]
    if args.tareas:
        pedidas = set(args.tareas.split(","))
        tareas = [t for t in tareas if t["id"] in pedidas]

    tmp = args.tmp or os.path.join(os.environ.get("TEMP", "."), "satrun")
    os.makedirs(tmp, exist_ok=True)

    ruta = os.path.join(BASE, args.salida)
    hechas = set()
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as fh:
            for l in fh:
                try:
                    r = json.loads(l)
                    hechas.add((r["catalogo"], r["tarea"], r["rep"]))
                except Exception:
                    pass

    pendientes = []
    for rep in range(args.reps):
        for t in tareas:
            for cat in ORDEN:
                if (cat, t["id"], rep) not in hechas:
                    pendientes.append((cat, t, rep))

    total = len(pendientes)
    lock = threading.Lock()
    cont = {"n": 0}
    out = open(ruta, "a", encoding="utf-8")

    def trabajo(item):
        cat, t, rep = item
        r = una_ejecucion(tmp, args.modelo, spec["sistema"],
                          t["prompt"], CATALOGOS[cat], args.timeout)
        r.update({"catalogo": cat, "tarea": t["id"],
                  "estrato": t["estrato"], "rep": rep, "modelo": args.modelo})
        with lock:
            cont["n"] += 1
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            print("[%d/%d] %s %s rep%d rc=%s -> %s" % (
                cont["n"], total, cat, t["id"], rep, r["rc"],
                ",".join(r["herramientas"]) or "(ninguna)"), flush=True)

    with cf.ThreadPoolExecutor(max_workers=args.hilos) as ex:
        list(ex.map(trabajo, pendientes))
    out.close()


if __name__ == "__main__":
    main()
