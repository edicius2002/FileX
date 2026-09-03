# -*- coding: utf-8 -*-
"""C36-4 -- "medir el catalogo con el registro completo del hito 5 (Gotenberg
+ sidecar dentro)".

Verificado ANTES de medir (Docker levantado, `docker ps -a` -- ver el
informe): ni Gotenberg ni el sidecar de OCR son subclases de
`filex.motores.Motor`, asi que `fx.grafo.aristas` no los incluye y no hay
manera de "medir con ellos dentro" del registro REAL sin escribirles una
clase de motor -- que es DISENO NUEVO, lo que el encargo pide evitar aqui.

Lo que SI se puede medir sin diseno nuevo es una PROYECCION: anadir al grafo,
solo en este script (nunca en `filex/motores.py`), las aristas que Gotenberg
YA demostro que cubre (`bench/gotenberg-y-mcp.md` C35, HOY, 6/7: docx, html,
md, odt, rtf, txt -> pdf; epub->pdf da HTTP 500 y NO se cuenta) y volver a
pedir el catalogo. Se re-verifica Gotenberg vivo con Docker levantado antes
de proyectar (no se asume el 6/7 de otro informe sin comprobar que el
servicio sigue arriba).

El sidecar de OCR se deja FUERA de la proyeccion, a proposito: no tiene un
conjunto origen/destino unico que "medir" sin decidir antes CUAL de los
cuatro motores (RapidOCR/PaddleOCR/EasyOCR/Tesseract) entra al catalogo y
que aristas expone -- decidir eso es la mitad de diseno que este encargo no
pide. Se declara PENDIENTE, con la razon.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-suelo-n32/medir_catalogo_proyectado.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

import tiktoken  # noqa: E402
from filex import mcp as M  # noqa: E402
from filex.grafo import Arista  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

GOTENBERG_URL = "http://localhost:3200/health"
# C35, HOY (`bench/gotenberg-y-mcp.md`): 6/7 buenos. epub->pdf da HTTP 500 y
# se EXCLUYE a proposito -- proyectar una arista que el propio motor no
# cumple seria inventar cobertura, lo que la trampa 72 ya nombra.
GOTENBERG_ORIGENES_A_PDF = ["docx", "html", "md", "odt", "rtf", "txt"]


def _gotenberg_vivo() -> bool:
    try:
        with urllib.request.urlopen(GOTENBERG_URL, timeout=5) as r:
            return r.status == 200
    except Exception as e:
        print("Gotenberg no responde: %r" % e)
        return False


def _contar(fx: FileX, etiqueta: str) -> dict:
    herramientas = M.catalogo(fx)
    if herramientas and not isinstance(herramientas[0], dict):
        herramientas = [h.model_dump(exclude_none=True, by_alias=True) for h in herramientas]
    else:
        herramientas = [{k: v for k, v in h.items() if v is not None} for h in herramientas]
    cable = json.dumps(herramientas, ensure_ascii=False)
    enc = tiktoken.get_encoding("o200k_base")
    dato = {
        "etiqueta": etiqueta,
        "aristas_en_el_grafo": len(fx.grafo.aristas),
        "n_enum_origen": len(M._enum_origen(fx)),
        "n_enum_destino": len(M._enum_destino(fx)),
        "tokens_catalogo": len(enc.encode(cable, disallowed_special=())),
    }
    print("%-30s aristas=%-4d origen=%-3d destino=%-3d tokens=%d"
          % (etiqueta, dato["aristas_en_el_grafo"], dato["n_enum_origen"],
             dato["n_enum_destino"], dato["tokens_catalogo"]))
    return dato


def main():
    vivo = _gotenberg_vivo()
    print("Gotenberg (%s) vivo: %s" % (GOTENBERG_URL, vivo))

    fx = FileX()
    resultado = {"gotenberg_vivo_hoy": vivo}
    resultado["real_actual"] = _contar(fx, "real (6 motores del hito 5)")

    if vivo:
        antes = len(fx.grafo.aristas)
        for o in GOTENBERG_ORIGENES_A_PDF:
            fx.grafo.añadir(Arista(origen=o, destino="pdf", motor="gotenberg_proyectado"))
        resultado["aristas_gotenberg_anadidas"] = len(fx.grafo.aristas) - antes
        resultado["proyectado_con_gotenberg"] = _contar(fx, "proyectado (+ Gotenberg, 6 aristas)")
        resultado["incremento_tokens_por_gotenberg"] = (
            resultado["proyectado_con_gotenberg"]["tokens_catalogo"]
            - resultado["real_actual"]["tokens_catalogo"])
        print("\nincremento de tokens por anadir Gotenberg (proyectado): +%d"
              % resultado["incremento_tokens_por_gotenberg"])
    else:
        resultado["proyectado_con_gotenberg"] = None
        print("Gotenberg no esta vivo hoy: no se proyecta sobre un servicio no verificado.")

    resultado["sidecar_ocr"] = "PENDIENTE, a proposito: no hay un origen/destino unico que " \
        "proyectar sin decidir antes que motor(es) de los cuatro (RapidOCR/PaddleOCR/" \
        "EasyOCR/Tesseract) entran al catalogo -- decidir eso es diseno, no medida."
    print("\nsidecar OCR: %s" % resultado["sidecar_ocr"])

    with open(os.path.join(os.path.dirname(__file__), "resultado_catalogo_proyectado.json"),
              "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
