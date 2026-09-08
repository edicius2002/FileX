"""Construye C51 en CPU y exige el digest medido; no publica ni resella."""
import argparse
import json
from pathlib import Path
import subprocess

RAIZ = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default="filex-c13-repro")
    a = p.parse_args()
    lock = json.loads((RAIZ / "docker/c13.lock.json").read_text(encoding="utf-8"))
    subprocess.run([
        "docker", "buildx", "build", "--platform", lock["plataforma"],
        "--build-arg", f'SOURCE_DATE_EPOCH={lock["source_date_epoch"]}',
        "--provenance=false", "--no-cache", "--output",
        "type=image,unpack=false,rewrite-timestamp=true",
        "-f", "docker/Dockerfile.c13", "-t", a.tag, "docker/"],
        cwd=RAIZ, stdin=subprocess.DEVNULL, timeout=1200, check=True)
    from verificar_c13 import verificar
    verificar(a.tag)


if __name__ == "__main__":
    main()
