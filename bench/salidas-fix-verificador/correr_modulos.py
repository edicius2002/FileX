"""Corre SOLO los modulos de prueba afectados por el carril `fix/verificador`.

No lanza la suite entera a proposito (`CLAUDE.md`: hay otro carril en la
maquina). Escribe el resumen en el fichero que se le pase.

Uso:  python bench/salidas-fix-verificador/correr_modulos.py <destino.txt>
"""

import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULOS = ("test_cob_png", "test_cob_tiffgif", "test_cob_webp",
           "test_cob_fidelidad", "test_contrato_v", "test_a7_ciego",
           "test_sondeo")
PAT = re.compile(r"^(FAIL|ERROR): |^Ran |^FAILED|^OK|^NO SUELTES")


def main() -> int:
    destino = sys.argv[1] if len(sys.argv) > 1 else None
    modulos = sys.argv[2:] or MODULOS
    lineas = []
    for m in modulos:
        lineas.append("===== %s =====" % m)
        p = subprocess.run([sys.executable, "-m", "unittest", "pruebas." + m],
                           cwd=RAIZ, capture_output=True, timeout=1800)
        txt = (p.stderr or b"").decode("utf-8", "replace")
        for l in txt.splitlines():
            if PAT.match(l.strip()) or PAT.match(l):
                lineas.append(l.rstrip())
        lineas.append("rc=%d" % p.returncode)
    salida = "\n".join(lineas)
    print(salida)
    if destino:
        with open(destino, "w", encoding="utf-8") as f:
            f.write(salida + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
