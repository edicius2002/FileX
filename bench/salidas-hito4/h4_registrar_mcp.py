"""Da de alta el servidor de FileX en la `.mcp.json` **del proyecto**.

Nunca `~/.claude.json`: configuración MCP **solo de proyecto** (`CLAUDE.md` §1).

Se escribe desde un script de Python con **barras normales**, no desde el shell:
los heredocs y las cadenas de este entorno se comen los backslashes (trampa
nº 19) — y no en teoría: el primer intento de esta misma tarea produjo
`D:\\Work\\research\\FileX` convertido en `D:\\Work` + un retorno de carro,
porque `\\r` se interpretó. Python normaliza con `os.path.normpath`.

**Aviso operativo MEDIDO** (`bench/mcp-cabos-sueltos.md` §1.6): cualquier cambio
en la `.mcp.json` del proyecto deja el servidor en `⏸ Pending approval`, y la
aprobación es **interactiva**. Un `filex init` que escriba la `.mcp.json` **no
deja el servidor conectado**: hace falta un paso humano.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_registrar_mcp.py
"""

from __future__ import annotations

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = os.path.join(RAIZ, ".mcp.json")
PY = os.path.join(RAIZ, ".venv-mcp-filex", "Scripts", "python.exe")

with open(CFG, encoding="utf-8") as fh:
    d = json.load(fh)

d.setdefault("mcpServers", {})["filex"] = {
    "type": "stdio",
    "command": os.path.normpath(PY),
    # `--raiz` es la lista blanca del SERVIDOR. Se INTERSECA con los roots que
    # mande el cliente (R13), no se reemplaza. Sin ninguna de las dos, no se
    # opera (R6: denegar por defecto).
    "args": ["-m", "filex.mcp", "--raiz", os.path.normpath(RAIZ)],
    "env": {"PYTHONPATH": os.path.normpath(RAIZ), "PYTHONUTF8": "1"},
}

with open(CFG, "w", encoding="utf-8") as fh:
    json.dump(d, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

print(open(CFG, encoding="utf-8").read())
