# -*- coding: utf-8 -*-
"""C36: recuento reproducible del catálogo realmente cargado por FileX."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import tiktoken

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from filex import mcp as M  # noqa: E402
from filex.nucleo import FileX  # noqa: E402


def main():
    fx = FileX()
    herramientas = M.catalogo(fx)
    if herramientas and not isinstance(herramientas[0], dict):
        herramientas = [h.model_dump(exclude_none=True, by_alias=True) for h in herramientas]
    else:
        herramientas = [{k: v for k, v in h.items() if v is not None} for h in herramientas]
    cable = json.dumps(herramientas, ensure_ascii=False)
    enc = tiktoken.get_encoding("o200k_base")
    dato = {
        "metodo": "tiktoken/o200k_base sobre el catálogo cableado actual",
        "motores_disponibles": [m.nombre for m in fx.disponibles],
        "aristas_en_el_grafo": len(fx.grafo.aristas),
        "herramientas": [h["name"] for h in herramientas],
        "n_enum_origen": len(M._enum_origen(fx)),
        "n_enum_destino": len(M._enum_destino(fx)),
        "tokens_catalogo": len(enc.encode(cable, disallowed_special=())),
        "tokens_solo_nombres": len(enc.encode(" ".join(h["name"] for h in herramientas),
                                                disallowed_special=())),
    }
    salida = Path(__file__).with_name("c36_catalogo.json")
    salida.write_text(json.dumps(dato, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dato, ensure_ascii=False))


if __name__ == "__main__":
    main()
