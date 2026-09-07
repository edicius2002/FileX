"""Campaña N38: cada intento cuenta, sin reintentar ni ocultar fallos."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filex import trabajo


def medir(n):
    intentos = []
    with tempfile.TemporaryDirectory(prefix="campana-n38-") as base:
        for i in range(n):
            d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=base)
            joven = trabajo.barrer_huerfanos(base=base)
            delta = time.time() - os.stat(d).st_mtime
            parte = trabajo.barrer_huerfanos(base=base, edad_sin_candado=0)
            fallo = os.path.exists(d) or joven["sin_candado_jovenes"] != 1
            intentos.append(dict(intento=i + 1, fallo=fallo, delta_s=delta,
                                 joven=joven, barrido=parte))
            if os.path.exists(d):
                os.rmdir(d)
    return dict(python=sys.version, plataforma=platform.platform(),
                head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                n=n, fallos=sum(x["fallo"] for x in intentos), intentos=intentos)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--json", required=True)
    args = p.parse_args()
    if args.n < 1:
        p.error("n debe ser positivo")
    resultado = medir(args.n)
    Path(args.json).write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(f'{resultado["fallos"]}/{resultado["n"]} fallos')
    sys.exit(bool(resultado["fallos"]))
