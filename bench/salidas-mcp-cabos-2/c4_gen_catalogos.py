#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera dos catalogos MCP con los MISMOS 6 nombres y esquemas, y descripciones
de tamano muy distinto (pesado vs ligero), mas los .mcp.json que los sirven.

El par pesado/ligero es el discriminador de C4d: si Claude Code inyecta el catalogo
ENTERO en el contexto del modelo (carga ansiosa), el catalogo pesado costara ~1.800
tokens mas por peticion; si solo inyecta los NOMBRES y difiere el resto (carga
diferida), el coste sera casi identico entre los dos.
"""
import json
from pathlib import Path

D = Path("D:/Work/research/FileX/bench/salidas-mcp-cabos-2")
SRV = str((D / "c4_probe_srv.py")).replace("/", "\\")
PY2X = "D:\\Work\\research\\FileX\\.venv-mcp-sdk-2x\\Scripts\\python.exe"

# Relleno unico y verboso, del estilo de una descripcion real de herramienta.
RELLENO = (
    "Esta herramienta forma parte del banco de sonda de FileX y su descripcion se ha "
    "inflado a proposito para medir el coste de catalogo en tokens. Convierte, transforma "
    "y verifica ficheros aplicando el motor correspondiente como proceso separado sin shell, "
    "con los argumentos en un array y stdin apuntando al dispositivo nulo, comprobando siempre "
    "la firma real de la salida, sus flujos, las propiedades declaradas, las propiedades "
    "pedidas frente a las obtenidas y que el motor no haya escrito nada fuera de lo declarado. "
    "Acepta rutas absolutas dentro de la lista blanca de raices y deniega por defecto cualquier "
    "otra, resolviendo los enlaces simbolicos en cada llamada y copiando la entrada a un area de "
    "trabajo privada antes de entregarsela a un motor externo. Devuelve unicamente la ruta de la "
    "salida y sus metadatos, nunca el contenido, y jamas el stderr crudo del motor. "
) * 3  # ~ 1.900 caracteres

NOMBRES = ["probe_convert", "probe_inspect", "probe_transcode", "probe_thumbnail",
           "probe_extract", "probe_package"]

ESQUEMA = {
    "type": "object",
    "properties": {
        "input_path": {"type": "string", "description": "ruta de entrada absoluta"},
        "output_path": {"type": "string", "description": "ruta de salida absoluta"},
        "target_format": {"type": "string", "description": "formato de destino"},
    },
    "required": ["input_path", "output_path"],
}


def catalogo(pesado):
    out = []
    for n in NOMBRES:
        desc = (f"[{n}] " + RELLENO) if pesado else f"{n}."
        out.append({"name": n, "description": desc, "inputSchema": dict(ESQUEMA)})
    return out


def mcp_config(catalog_path, log_path, nombre):
    return {"mcpServers": {nombre: {
        "type": "stdio", "command": PY2X, "args": [SRV],
        "env": {"STUB_CATALOG": str(catalog_path).replace("/", "\\"),
                "STUB_LOG": str(log_path).replace("/", "\\"),
                "STUB_NAME": nombre}}}}


def main():
    cat_pesado = D / "c4_cat_pesado.json"
    cat_ligero = D / "c4_cat_ligero.json"
    cat_pesado.write_text(json.dumps(catalogo(True), ensure_ascii=False, indent=2), encoding="utf-8")
    cat_ligero.write_text(json.dumps(catalogo(False), ensure_ascii=False, indent=2), encoding="utf-8")

    (D / "c4_mcp_pesado.json").write_text(json.dumps(
        mcp_config(cat_pesado, D / "c4_log_pesado.jsonl", "filexpesado"), indent=2), encoding="utf-8")
    (D / "c4_mcp_ligero.json").write_text(json.dumps(
        mcp_config(cat_ligero, D / "c4_log_ligero.jsonl", "filexligero"), indent=2), encoding="utf-8")

    # tamano aproximado del catalogo servido, en caracteres
    for etq, cat in (("pesado", catalogo(True)), ("ligero", catalogo(False))):
        s = json.dumps(cat, ensure_ascii=False)
        print(f"catalogo {etq}: {len(cat)} herramientas, {len(s)} chars de serializacion")


if __name__ == "__main__":
    main()
