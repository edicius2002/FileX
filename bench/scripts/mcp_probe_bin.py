"""Sonda de ergonomia MCP para el CASO BINARIO.

Deriva de bench/salidas-mcp/mcp_probe.py (que se conserva intacto como
evidencia de lo ya medido sobre MCP documentales). La diferencia esta en
como se contabiliza la respuesta.

EL PROBLEMA QUE CORRIGE
-----------------------
El arnes original colapsaba todo contenido no textual a "<NombreDeClase>":

    partes.append(f"<{type(c).__name__}>")

Un ImageContent de 2 MB en base64 se contabilizaba asi como ~5 tokens. Para
MCP documentales daba igual (la salida es texto), pero es justo la medida que
decide el diseno de convert() en FileX: si un servidor devuelve la imagen como
contenido, hay que saber lo que cuesta DE VERDAD.

QUE MIDE AHORA, POR SEPARADO
----------------------------
  texto        -> TextContent: tokens reales (tiktoken/o200k_base)
  imagen/audio -> ImageContent/AudioContent: chars de base64, bytes decodificados,
                  mimeType, y su coste EQUIVALENTE en tokens si el cliente lo inyectara
  recurso      -> EmbeddedResource: text/ blob, con el mismo desglose
  enlace       -> ResourceLink: el patron de asa bien hecho
  otros        -> tipo declarado, sin perderlo de vista

Y produce un veredicto por llamada: patron ASA (ruta/clave/uri), patron
CONTENIDO (el binario viaja en la respuesta), MIXTO, o PROSA.

Uso:  python mcp_probe_bin.py <spec.json> <salida.json>

El formato de <spec.json> es el mismo que el del arnes original, incluido el
encadenamiento "@key:<id_paso>". Se anade una clave opcional por paso:
  "espera": "asa" | "contenido" | "mixto" | "prosa"
que se contrasta con lo observado y se reporta en coincide_con_lo_esperado.
"""

import asyncio
import base64
import json
import os
import re
import sys
import time

import tiktoken
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENC = tiktoken.get_encoding("o200k_base")

# Umbral por encima del cual una respuesta se considera inviable para el
# contexto de un modelo. 25 000 tokens = 12,5 % de una ventana de 200 K.
UMBRAL_INVIABLE = 25_000

# Racha minima de caracteres base64 para considerar que hay un binario colado
# dentro de un TextContent. 512 chars ~ 384 bytes: por debajo de eso es mas
# probable que sea un hash, un token o un identificador que un fichero.
UMBRAL_B64_CHARS = 512
RE_B64 = re.compile(r"[A-Za-z0-9+/=]{%d,}" % UMBRAL_B64_CHARS)

# Marcas que delatan que la respuesta lleva un asa reutilizable por el modelo.
MARCAS_ASA = (
    "path", "ruta", "output_file", "output_path", "file_path", "filepath",
    "document_key", "uri", "://", ":\\", "/mnt/", "saved to", "guardado en",
)


def ntok(s):
    return len(ENC.encode(s, disallowed_special=()))


def _bytes_de_b64(s):
    try:
        return len(base64.b64decode(s, validate=False))
    except Exception:
        return None


def _desglosar(c):
    """Desglosa UNA pieza de contenido sin perder su peso real."""
    tipo = getattr(c, "type", None) or type(c).__name__
    d = {"tipo": tipo}

    # --- texto ---
    t = getattr(c, "text", None)
    if t is not None:
        d.update(clase="texto", chars=len(t), tokens=ntok(t), texto=t)
        return d

    # --- imagen / audio en linea (base64) ---
    data = getattr(c, "data", None)
    if isinstance(data, str):
        d.update(
            clase="binario_en_linea",
            mimeType=getattr(c, "mimeType", None),
            chars_base64=len(data),
            bytes_decodificados=_bytes_de_b64(data),
            tokens_si_se_inyecta=ntok(data),
        )
        return d

    # --- recurso incrustado ---
    r = getattr(c, "resource", None)
    if r is not None:
        rt = getattr(r, "text", None)
        rb = getattr(r, "blob", None)
        d.update(
            clase="recurso",
            uri=str(getattr(r, "uri", "")),
            mimeType=getattr(r, "mimeType", None),
        )
        if rt is not None:
            d.update(subclase="texto", chars=len(rt), tokens=ntok(rt), texto=rt)
        elif isinstance(rb, str):
            d.update(
                subclase="blob",
                chars_base64=len(rb),
                bytes_decodificados=_bytes_de_b64(rb),
                tokens_si_se_inyecta=ntok(rb),
            )
        return d

    # --- enlace a recurso: el patron de asa bien hecho ---
    uri = getattr(c, "uri", None)
    if uri is not None:
        d.update(clase="enlace", uri=str(uri), mimeType=getattr(c, "mimeType", None))
        return d

    d.update(clase="desconocido", repr=repr(c)[:300])
    return d


def _base64_dentro_del_texto(txt):
    """Detecta un binario colado como base64 DENTRO de un TextContent.

    Hallazgo medido (bench/mcp-refs-multimedia.md): image-worker-mcp devuelve la
    imagen entera como base64 dentro de un string JSON en un TextContent normal.
    El protocolo MCP no se entera -- no hay ImageContent ni blob por ningun lado --
    asi que clasificar por tipo de contenido daba PROSA o incluso ASA para una
    respuesta de 6 218 tokens. Es justo el patron que FileX quiere prohibir, y era
    invisible.

    Leccion de diseno que se traslada a FileX: la regla se vigila sobre TOKENS DE
    RESPUESTA, no sobre tipos de contenido del protocolo.

    Devuelve (n_bytes_estimados, chars_de_base64_encontrados).
    """
    if not txt or len(txt) < UMBRAL_B64_CHARS:
        return 0, 0
    mejor = 0
    total = 0
    for m in RE_B64.finditer(txt):
        n = len(m.group(0))
        total += n
        mejor = max(mejor, n)
    if mejor < UMBRAL_B64_CHARS:
        return 0, 0
    return (total * 3) // 4, total


def analizar_respuesta(res):
    piezas = [_desglosar(c) for c in (getattr(res, "content", []) or [])]

    tokens_texto = sum(p.get("tokens", 0) for p in piezas)
    tokens_binario = sum(p.get("tokens_si_se_inyecta", 0) for p in piezas)
    bytes_binario = sum((p.get("bytes_decodificados") or 0) for p in piezas)

    texto_plano = "\n".join(p["texto"] for p in piezas if p.get("texto") is not None)

    # Binario camuflado en texto: se contabiliza aparte, sin tocar tokens_texto
    # (esos tokens YA estan contados; lo que faltaba era saber que son un binario).
    bytes_camuflados, chars_b64 = _base64_dentro_del_texto(texto_plano)
    hay_binario_en_texto = bytes_camuflados > 0

    hay_binario = any(
        p["clase"] == "binario_en_linea" or p.get("subclase") == "blob" for p in piezas
    ) or hay_binario_en_texto
    hay_asa = any(p["clase"] == "enlace" for p in piezas) or bool(
        texto_plano and any(m in texto_plano.lower() for m in MARCAS_ASA)
    )

    if hay_binario and hay_asa:
        patron = "MIXTO"
    elif hay_binario:
        patron = "CONTENIDO"
    elif hay_asa:
        patron = "ASA"
    else:
        patron = "PROSA"

    return {
        "piezas": piezas,
        "n_piezas": len(piezas),
        "tokens_texto": tokens_texto,
        "tokens_binario_si_se_inyecta": tokens_binario,
        "tokens_total": tokens_texto + tokens_binario,
        "bytes_binario": bytes_binario + bytes_camuflados,
        "binario_camuflado_en_texto": hay_binario_en_texto,
        "bytes_camuflados_en_texto": bytes_camuflados,
        "chars_base64_en_texto": chars_b64,
        "patron": patron,
        "inviable_para_contexto": (tokens_texto + tokens_binario) > UMBRAL_INVIABLE,
        "texto_plano": texto_plano,
    }


async def main(spec_path, out_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    env = dict(os.environ)
    env.update(spec.get("env", {}))
    env.setdefault("PYTHONIOENCODING", "utf-8")

    params = StdioServerParameters(
        command=spec["command"],
        args=spec.get("args", []),
        env=env,
        cwd=spec.get("cwd"),
    )

    out = {"spec": spec_path, "servidor": spec.get("nombre"), "llamadas": []}
    errlog = open(spec.get("stderr_log", os.devnull), "w", encoding="utf-8", errors="replace")

    t_spawn = time.perf_counter()
    async with stdio_client(params, errlog=errlog) as (read, write):
        t_proc = time.perf_counter()
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            si = getattr(init, "serverInfo", None) or getattr(init, "server_info", None)
            t_init = time.perf_counter()
            out["arranque_frio_ms"] = round((t_init - t_spawn) * 1000, 1)
            out["spawn_proceso_ms"] = round((t_proc - t_spawn) * 1000, 1)
            out["handshake_ms"] = round((t_init - t_proc) * 1000, 1)
            out["server_info"] = {
                "name": getattr(si, "name", None),
                "version": getattr(si, "version", None),
                "protocolVersion": getattr(init, "protocolVersion", None)
                or getattr(init, "protocol_version", None),
                "instructions": getattr(init, "instructions", None),
            }

            t0 = time.perf_counter()
            tools = await session.list_tools()
            out["list_tools_ms"] = round((time.perf_counter() - t0) * 1000, 1)

            inv = []
            for t in tools.tools:
                d = t.model_dump(exclude_none=True)
                anot = d.get("annotations") or {}
                inv.append({
                    "name": d.get("name"),
                    "description": (d.get("description") or "").strip(),
                    "annotations": anot,
                    "tiene_readOnlyHint": "readOnlyHint" in anot,
                    "tiene_destructiveHint": "destructiveHint" in anot,
                    "tokens_declaracion": ntok(json.dumps(d, ensure_ascii=False)),
                    "inputSchema": d.get("inputSchema"),
                    "outputSchema": d.get("outputSchema"),
                })
            out["n_herramientas"] = len(inv)
            out["herramientas"] = inv
            out["tokens_catalogo"] = ntok(
                json.dumps([t.model_dump(exclude_none=True) for t in tools.tools], ensure_ascii=False)
            )
            out["n_anotadas"] = sum(1 for h in inv if h["annotations"])

            for etiqueta, fn, attr in (
                ("prompts", session.list_prompts, "prompts"),
                ("recursos", session.list_resources, "resources"),
            ):
                try:
                    r = await fn()
                    items = getattr(r, attr, [])
                    out["n_" + etiqueta] = len(items)
                    out[etiqueta] = [getattr(i, "name", str(i)) for i in items]
                except Exception as e:
                    out["n_" + etiqueta] = None
                    out[etiqueta] = "{}: {}".format(type(e).__name__, e)

            claves = {}

            for paso in spec["pasos"]:
                args = {}
                for k, v in paso["args"].items():
                    if isinstance(v, str) and v.startswith("@key:"):
                        args[k] = claves.get(v[5:], "<CLAVE_NO_DISPONIBLE>")
                    else:
                        args[k] = v
                reg = {
                    "id": paso["id"],
                    "tool": paso["tool"],
                    "args": args,
                    "nota": paso.get("nota", ""),
                    "espera": paso.get("espera"),
                }
                t0 = time.perf_counter()
                try:
                    res = await asyncio.wait_for(
                        session.call_tool(paso["tool"], args),
                        timeout=paso.get("timeout", 900),
                    )
                    ms = (time.perf_counter() - t0) * 1000
                    a = analizar_respuesta(res)
                    is_err = getattr(res, "isError", None)
                    if is_err is None:
                        is_err = getattr(res, "is_error", False)
                    reg.update({
                        "ok": True,
                        "isError": bool(is_err),
                        "ms": round(ms, 1),
                        "patron": a["patron"],
                        "n_piezas": a["n_piezas"],
                        "tokens_texto": a["tokens_texto"],
                        "tokens_binario_si_se_inyecta": a["tokens_binario_si_se_inyecta"],
                        "tokens_total": a["tokens_total"],
                        "bytes_binario": a["bytes_binario"],
                        "inviable_para_contexto": a["inviable_para_contexto"],
                        "piezas": [
                            {k: v for k, v in p.items() if k != "texto"} for p in a["piezas"]
                        ],
                        "respuesta_recorte": a["texto_plano"][: paso.get("recorte", 1500)],
                    })
                    if paso.get("espera"):
                        reg["coincide_con_lo_esperado"] = (
                            a["patron"].lower() == paso["espera"].lower()
                        )

                    sc = getattr(res, "structuredContent", None)
                    if sc is None:
                        sc = getattr(res, "structured_content", None)
                    if sc is not None:
                        s = json.dumps(sc, ensure_ascii=False)
                        reg["structuredContent"] = s[:800]
                        reg["tokens_structured"] = ntok(s)
                        # Duplicacion: pagar dos veces por lo mismo
                        reg["duplica_contenido"] = a["tokens_texto"] > 0 and ntok(s) > 0
                        dk = sc.get("document_key") if isinstance(sc, dict) else None
                        if dk:
                            claves[paso["id"]] = dk
                    if paso["id"] not in claves:
                        try:
                            j = json.loads(a["texto_plano"])
                            if isinstance(j, dict) and j.get("document_key"):
                                claves[paso["id"]] = j["document_key"]
                        except Exception:
                            pass
                    if paso.get("volcar"):
                        p = os.path.join(os.path.dirname(out_path), paso["volcar"])
                        with open(p, "w", encoding="utf-8", errors="replace") as f:
                            f.write(a["texto_plano"])
                        reg["respuesta_completa_en"] = p
                except Exception as e:
                    ms = (time.perf_counter() - t0) * 1000
                    msg = "{}: {}".format(type(e).__name__, e)
                    reg.update({
                        "ok": False,
                        "isError": None,
                        "ms": round(ms, 1),
                        "excepcion": msg,
                        "tokens_texto": ntok(msg),
                        "tokens_total": ntok(msg),
                        "patron": "EXCEPCION",
                        "respuesta_recorte": msg[: paso.get("recorte", 1500)],
                    })
                out["llamadas"].append(reg)
                print(
                    "  [{}] {} ms  patron={}  tok_txt={}  tok_bin={}  bytes={}  isError={}".format(
                        paso["id"], reg["ms"], reg.get("patron"),
                        reg.get("tokens_texto"), reg.get("tokens_binario_si_se_inyecta", 0),
                        reg.get("bytes_binario", 0), reg.get("isError"),
                    ),
                    flush=True,
                )

    errlog.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("escrito", out_path)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
