# -*- coding: utf-8 -*-
"""E1 / C8 - prepara las entradas, las mete en el contenedor y lanza el guion."""
import os, shutil, subprocess, sys

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
C8 = os.path.join(SAL, "c8")
IN = os.path.join(C8, "in")
DEVNULL = subprocess.DEVNULL

SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect width="400" height="200" fill="#ffffff"/>
  <circle cx="60" cy="60" r="40" fill="#3366cc" opacity="0.7"/>
  <path d="M120 150 L200 40 L280 150 Z" fill="none" stroke="#cc3333" stroke-width="4"/>
  <text x="20" y="180" font-family="DejaVu Sans, sans-serif" font-size="22"
        font-weight="bold" fill="#111111">FILEXSENTINELA7743 ancho</text>
  <text x="20" y="196" font-family="serif" font-size="12" font-style="italic"
        fill="#444444">tipografia: fi fl ti ligaduras, tildes aeiou</text>
</svg>
"""


def main():
    os.makedirs(IN, exist_ok=True)
    ent = os.path.join(RAIZ, r"bench\salidas-fidelidad\entradas")
    for f in os.listdir(ent):
        shutil.copy(os.path.join(ent, f), os.path.join(IN, f))
    shutil.copy(os.path.join(RAIZ, r"corpus\pdf\tipico_texto.pdf"), IN)
    shutil.copy(os.path.join(RAIZ, r"corpus\imagen\tipico.png"), IN)
    with open(os.path.join(IN, "e1.svg"), "w", encoding="utf-8") as f:
        f.write(SVG)
    # el guion tiene que ir con saltos LF
    g = os.path.join(SAL, "c8_dentro.sh")
    d = open(g, "rb").read().replace(b"\r\n", b"\n")
    open(os.path.join(C8, "c8_dentro.sh"), "wb").write(d)

    def dk(*a, t=900):
        p = subprocess.run(["docker"] + list(a), stdin=DEVNULL, capture_output=True,
                           text=True, timeout=t, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    print(dk("exec", "filex-convertx", "rm", "-rf", "/tmp/e1"))
    print(dk("exec", "filex-convertx", "mkdir", "-p", "/tmp/e1"))
    print(dk("cp", IN, "filex-convertx:/tmp/e1/in"))
    print(dk("cp", os.path.join(C8, "c8_dentro.sh"), "filex-convertx:/tmp/e1/c8.sh"))
    rc, out = dk("exec", "filex-convertx", "sh", "/tmp/e1/c8.sh", t=1800)
    print("rc guion:", rc)
    print(out[-3000:])
    os.makedirs(os.path.join(C8, "out"), exist_ok=True)
    print(dk("cp", "filex-convertx:/tmp/e1/resultado.tsv", os.path.join(C8, "resultado.tsv")))
    print(dk("cp", "filex-convertx:/tmp/e1/out", os.path.join(C8, "out")))


if __name__ == "__main__":
    main()
