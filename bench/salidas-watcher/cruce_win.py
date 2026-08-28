#!/usr/bin/env python3
"""N4 — el CONTROL POSITIVO del cruce Windows <-> WSL2, en las dos direcciones.

P midió que el **candado** no cruza (`bench/cerrojo-unico.md`). Esto mide otra
cosa: si el **primitivo de detección** cruza. Son preguntas distintas —una es de
exclusión y la otra de observación— y la respuesta no se puede deducir de la
otra.

La trampa 36, tercer aviso, exige control positivo: un «no lo ve» solo significa
algo si el mismo primitivo SÍ lo ve cuando el tenedor está en su propio lado.
Aquí hay las cuatro celdas:

    tenedor Windows  ->  mira Windows   (control positivo de Windows)
    tenedor Windows  ->  mira WSL2      (el cruce)
    tenedor WSL2     ->  mira WSL2      (control positivo de POSIX)
    tenedor WSL2     ->  mira Windows   (el cruce, al revés)

Se corre desde Windows. Necesita `wsl.exe` en el PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
TENEDOR = os.path.join(AQUI, "tenedor.py")
SONDA = os.path.join(AQUI, "sonda_posix.py")


def a_wsl(ruta: str) -> str:
    """`D:\\x\\y` -> `/mnt/d/x/y`. Sin `wslpath`, que es otro proceso."""
    a = os.path.abspath(ruta)
    unidad, resto = a[0], a[2:]
    return "/mnt/" + unidad.lower() + resto.replace("\\", "/")


def mirar_windows(ruta: str) -> dict:
    """Los dos primitivos que el proyecto ya tiene medidos, en Windows."""
    out = {}
    try:
        os.replace(ruta, ruta)
        out["os.replace(p,p)"] = "libre"
    except OSError as e:
        out["os.replace(p,p)"] = "ocupado"
        out["_replace_err"] = f"WinError {getattr(e, 'winerror', '?')}"
    try:
        with open(ruta, "rb") as fh:
            fh.read(1)
        out["open(p,'rb')"] = "libre"
    except OSError:
        out["open(p,'rb')"] = "ocupado"
    return out


def mirar_wsl(ruta_win: str, salida: str, log: str) -> dict:
    r = subprocess.run(
        ["wsl.exe", "-e", "python3", a_wsl(SONDA), "--medir-ruta",
         a_wsl(ruta_win), "--salida", a_wsl(salida), "--log", a_wsl(log),
         "--etiqueta", "cruce"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    crudo = (r.stdout or "").replace("\x00", "").strip()
    try:
        return json.loads(crudo.splitlines()[-1])
    except (ValueError, IndexError):
        return {"_error": crudo[:400], "_stderr": (r.stderr or "")[:400]}


class TenedorWin:
    """Un proceso de Windows con el fichero abierto. Espera su marcador."""

    def __init__(self, ruta: str, modo: str, segundos: float):
        self.p = subprocess.Popen(
            [sys.executable, TENEDOR, "--ruta", ruta, "--modo", modo,
             "--segundos", str(segundos)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
        self.marcador = self.p.stdout.readline().strip()

    @property
    def ok(self) -> bool:
        return self.marcador.startswith("ABIERTO") and self.p.poll() is None

    def matar(self):
        try:
            self.p.kill()
            self.p.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass


class TenedorWsl:
    """Un proceso DENTRO de WSL2 con el mismo fichero abierto."""

    def __init__(self, ruta_win: str, modo: str, segundos: float):
        self.p = subprocess.Popen(
            ["wsl.exe", "-e", "python3", a_wsl(TENEDOR), "--ruta",
             a_wsl(ruta_win), "--modo", modo, "--segundos", str(segundos)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
        self.marcador = self.p.stdout.readline().replace("\x00", "").strip()

    @property
    def ok(self) -> bool:
        return self.marcador.startswith("ABIERTO") and self.p.poll() is None

    def matar(self):
        try:
            self.p.kill()
            self.p.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--origen", required=True)
    p.add_argument("--dir", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--segundos", type=float, default=25.0)
    a = p.parse_args(argv)

    os.makedirs(a.dir, exist_ok=True)
    ruta = os.path.join(a.dir, "cruce.bin")
    aux = os.path.join(a.dir, "cruce_aux.json")
    auxlog = os.path.join(a.dir, "cruce_aux.log")
    celdas = []

    with open(a.log, "w", encoding="utf-8") as log:
        # --- tenedor en Windows ------------------------------------------
        shutil.copyfile(a.origen, ruta)
        t = TenedorWin(ruta, "ab", a.segundos)
        cond = t.ok
        log.write(f"[tenedor=Windows] marcador={t.marcador!r} cond_ok={cond}\n")
        if cond:
            celdas.append({"tenedor": "Windows", "mira": "Windows",
                           "condicion_ok": True, "primitivos": mirar_windows(ruta)})
            celdas.append({"tenedor": "Windows", "mira": "WSL2",
                           "condicion_ok": True,
                           "primitivos": mirar_wsl(ruta, aux, auxlog)})
        else:
            celdas.append({"tenedor": "Windows", "condicion_ok": False})
        t.matar()
        time.sleep(0.5)

        # --- tenedor en WSL2 ---------------------------------------------
        t2 = TenedorWsl(ruta, "ab", a.segundos)
        cond2 = t2.ok
        log.write(f"[tenedor=WSL2] marcador={t2.marcador!r} cond_ok={cond2}\n")
        if cond2:
            celdas.append({"tenedor": "WSL2", "mira": "WSL2",
                           "condicion_ok": True,
                           "primitivos": mirar_wsl(ruta, aux, auxlog)})
            celdas.append({"tenedor": "WSL2", "mira": "Windows",
                           "condicion_ok": True, "primitivos": mirar_windows(ruta)})
        else:
            celdas.append({"tenedor": "WSL2", "condicion_ok": False})
        t2.matar()

        for c in celdas:
            log.write(json.dumps(c, ensure_ascii=False) + "\n")

    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump({"ruta": ruta, "celdas": celdas}, fh,
                  ensure_ascii=False, indent=1)
    for c in celdas:
        print(f"tenedor={c.get('tenedor'):8s} mira={str(c.get('mira')):8s} "
              f"cond_ok={c['condicion_ok']} {c.get('primitivos')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
