"""Campaña N38: cada intento cuenta, sin reintentar ni ocultar fallos."""
import argparse
import hashlib
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


def medir(n, guardar=None):
    intentos = []
    resultado = dict(python=sys.version, plataforma=platform.platform(),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        trabajo_sha256=hashlib.sha256(Path(trabajo.__file__).read_bytes()).hexdigest(),
        run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        n=n, completados=0, estado="en_curso", fallos=0, intentos=intentos)
    if guardar:
        guardar(resultado)
    with tempfile.TemporaryDirectory(prefix="campana-n38-") as base:
        for i in range(n):
            intento = dict(intento=i + 1, fallo=True)
            try:
                # Cada intento tiene su propia base: un fallo no contamina el
                # denominador de los siguientes ni se convierte en un rerun.
                with tempfile.TemporaryDirectory(dir=base) as aislado:
                    d = tempfile.mkdtemp(prefix=trabajo.PREFIJO, dir=aislado)
                    joven = trabajo.barrer_huerfanos(base=aislado)
                    delta = time.time() - os.stat(d).st_mtime
                    parte = trabajo.barrer_huerfanos(base=aislado, edad_sin_candado=0)
                    fallo = os.path.exists(d) or joven["sin_candado_jovenes"] != 1
                    intento.update(fallo=fallo, delta_s=delta, joven=joven, barrido=parte)
            except Exception as exc:
                intento.update(fallo=True, error=f"{type(exc).__name__}: {exc}")
            intentos.append(intento)
            resultado.update(completados=len(intentos), fallos=sum(x["fallo"] for x in intentos))
            if guardar:
                guardar(resultado)
    resultado["estado"] = "completa"
    if guardar:
        guardar(resultado)
    return resultado


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--json", required=True)
    args = p.parse_args()
    if args.n < 1:
        p.error("n debe ser positivo")
    destino = Path(args.json)
    diario = destino.with_suffix(".jsonl")
    if destino.exists() or diario.exists():
        p.error("la campaña ya existe; usa otro nombre para conservar el historial")
    # Mantener un único handle y AÑADIR registros evita el replace continuo que
    # Windows rechazó con WinError 5. Si el proceso muere, cada intento ya
    # completado queda en el diario; la ausencia de resumen no equivale a éxito.
    with diario.open("x", encoding="utf-8") as registro:
        def guardar(datos):
            if datos["estado"] == "completa":
                fila = dict(tipo="fin", n=datos["n"], completados=datos["completados"], fallos=datos["fallos"])
            elif datos["intentos"]:
                fila = dict(tipo="intento", **datos["intentos"][-1])
            else:
                fila = dict(tipo="inicio", **{k: v for k, v in datos.items() if k != "intentos"})
            registro.write(json.dumps(fila) + "\n")
            registro.flush()
        resultado = medir(args.n, guardar=guardar)
    with destino.open("x", encoding="utf-8") as resumen:
        json.dump(resultado, resumen, indent=2)
    print(f'{resultado["fallos"]}/{resultado["n"]} fallos')
    sys.exit(bool(resultado["fallos"]))
