"""Que valida el SDK en ImageContent.data. Se ejecuta con cualquiera de las 3 ramas."""

import base64
import json
import sys

import mcp.types as types

SDK = __import__("importlib.metadata", fromlist=["x"]).version("mcp")
DOS = SDK.startswith("2.")
CAMPO_MIME = "mime_type" if DOS else "mimeType"

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
PURO = base64.b64encode(PNG).decode()

CASOS = {
    "base64_puro": PURO,
    "prefijo_data_uri": f"data:image/png;base64,{PURO}",
    "no_es_base64": "esto no es base64 !!!! @@@@",
    "cadena_vacia": "",
    "padding_roto": PURO.rstrip("="),
    "con_saltos_de_linea": PURO[:20] + "\n" + PURO[20:],
    "bytes_en_vez_de_str": PNG,
    "int": 12345,
    "none": None,
}

out = {"sdk_mcp": SDK, "campo_mime": CAMPO_MIME, "construccion": {}, "ida_y_vuelta_json": {}}

for nombre, dato in CASOS.items():
    r = {}
    try:
        ic = types.ImageContent(**{"type": "image", "data": dato, CAMPO_MIME: "image/png"})
        r["acepta"] = True
        r["tipo_data_resultante"] = type(ic.data).__name__
        r["len"] = len(ic.data) if isinstance(ic.data, str) else None
        r["identico_a_la_entrada"] = (ic.data == dato)
    except Exception as e:  # noqa: BLE001
        r["acepta"] = False
        r["error"] = type(e).__name__
        r["mensaje"] = str(e).replace("\n", " | ")[:400]
    out["construccion"][nombre] = r

# ida y vuelta por el alambre (serializar + revalidar), que es lo que hace el cliente
for nombre, dato in CASOS.items():
    if not out["construccion"][nombre]["acepta"]:
        continue
    try:
        ic = types.ImageContent(**{"type": "image", "data": dato, CAMPO_MIME: "image/png"})
        crudo = ic.model_dump_json(by_alias=True, exclude_none=True)
        vuelta = types.ImageContent.model_validate_json(crudo)
        out["ida_y_vuelta_json"][nombre] = {
            "ok": True, "json_recorte": crudo[:90],
            "data_intacta": vuelta.data == ic.data}
    except Exception as e:  # noqa: BLE001
        out["ida_y_vuelta_json"][nombre] = {"ok": False, "error": type(e).__name__,
                                            "mensaje": str(e).replace("\n", " | ")[:400]}

# ¿hay algun validador de base64 en el modelo?
out["validadores_del_campo_data"] = str(
    getattr(types.ImageContent.model_fields.get("data"), "metadata", None))
out["mime_obligatorio"] = types.ImageContent.model_fields[CAMPO_MIME].is_required()

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
if len(sys.argv) > 1:
    open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2, default=str))
