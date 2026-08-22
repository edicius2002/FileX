"""Cabo 1 — anade/quita el servidor de prueba en la `.mcp.json` DEL PROYECTO.

Nunca toca `~/.claude.json`. Uso:
    python cabo1_escribir_mcpjson.py add
    python cabo1_escribir_mcpjson.py restore
"""

import json
import shutil
import sys
from pathlib import Path

RAIZ = Path("D:/Work/research/FileX")
MCPJSON = RAIZ / ".mcp.json"
BAK = RAIZ / "bench/salidas-mcp-cabos/mcp.json.bak"
PY2X = RAIZ / ".venv-mcp-sdk-2x/Scripts/python.exe"
SRV = RAIZ / "bench/salidas-mcp-cabos/cabo1_srv_2x.py"

ENTRADA = {
    "type": "stdio",
    "command": str(PY2X).replace("/", "\\"),
    "args": [str(SRV).replace("/", "\\")],
    "env": {
        "FILEX_RAICES": "D:\\Work\\research\\FileX\\corpus",
        "CABO1_LOG": str(RAIZ / "bench/salidas-mcp-cabos/cabo1_srv_log.jsonl").replace("/", "\\"),
        "PYTHONUNBUFFERED": "1",
    },
}


def main():
    accion = sys.argv[1] if len(sys.argv) > 1 else "add"
    if accion == "restore":
        shutil.copyfile(BAK, MCPJSON)
        print("RESTAURADA desde", BAK)
        print(MCPJSON.read_text(encoding="utf-8"))
        return
    if not BAK.exists():
        shutil.copyfile(MCPJSON, BAK)
    d = json.loads(BAK.read_text(encoding="utf-8"))
    d["mcpServers"]["filex-cabo1"] = ENTRADA
    MCPJSON.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    print("ANADIDO filex-cabo1 a", MCPJSON)
    print(MCPJSON.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
