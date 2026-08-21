"""Sonda de ergonomia para servidores MCP (stdio).

Mide, para un servidor MCP arrancado por stdio:
  - latencia de arranque en frio (spawn -> initialize completo)
  - catalogo de herramientas (nombres, descripciones, anotaciones) y su coste en tokens
  - por cada llamada: latencia, isError, y TOKENS DEL TEXTO QUE LLEGA AL MODELO

El contador de tokens es tiktoken/o200k_base (el tokenizador de la familia
GPT-4o/o200k; sirve como patron de medida estable y reproducible; para Claude
la cifra difiere en un margen pequeno pero el orden de magnitud es el mismo).

Uso:  python mcp_probe.py <spec.json> <salida.json>
"""

import asyncio
import json
import os
import sys
import time

import tiktoken
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ENC = tiktoken.get_encoding("o200k_base")


def ntok(s: str) -> int:
    return len(ENC.encode(s, disallowed_special=()))


def texto_del_resultado(res) -> str:
    """El texto que un cliente MCP inyecta en el contexto del modelo."""
    partes = []
    for c in getattr(res, "content", []) or []:
        t = getattr(c, "text", None)
        if t is not None:
            partes.append(t)
        else:
            partes.append(f"<{type(c).__name__}>")
    return "\n".join(partes)


async def main(spec_path: str, out_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    env = dict(os.environ)
    env.update(spec.get("env", {}))
    # PYTHONIOENCODING evita que un UnicodeEncodeError en stdio rompa el servidor
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
                "protocolVersion": getattr(init, "protocolVersion", None) or getattr(init, "protocol_version", None),
                "instructions": getattr(init, "instructions", None),
            }

            t0 = time.perf_counter()
            tools = await session.list_tools()
            out["list_tools_ms"] = round((time.perf_counter() - t0) * 1000, 1)

            inv = []
            for t in tools.tools:
                d = t.model_dump(exclude_none=True)
                anot = d.get("annotations") or {}
                inv.append(
                    {
                        "name": d.get("name"),
                        "title": d.get("title") or anot.get("title"),
                        "description": (d.get("description") or "").strip(),
                        "annotations": anot,
                        "tokens_descripcion": ntok(json.dumps(d, ensure_ascii=False)),
                        "inputSchema": d.get("inputSchema"),
                        "outputSchema": d.get("outputSchema"),
                    }
                )
            out["n_herramientas"] = len(inv)
            out["herramientas"] = inv
            # Coste fijo del catalogo: lo que ocupa el listado completo en el prompt
            out["tokens_catalogo"] = ntok(
                json.dumps([t.model_dump(exclude_none=True) for t in tools.tools], ensure_ascii=False)
            )

            # prompts y recursos (superficie adicional)
            for etiqueta, fn in (("prompts", session.list_prompts), ("recursos", session.list_resources)):
                try:
                    r = await fn()
                    items = getattr(r, etiqueta if etiqueta == "prompts" else "resources", [])
                    out["n_" + etiqueta] = len(items)
                    out[etiqueta] = [getattr(i, "name", str(i)) for i in items]
                except Exception as e:  # capability ausente
                    out["n_" + etiqueta] = None
                    out[etiqueta] = f"{type(e).__name__}: {e}"

            claves: dict[str, str] = {}  # id_paso -> document_key devuelto

            for paso in spec["pasos"]:
                # sustitucion "@key:<id_paso>" por la clave de cache devuelta antes
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
                }
                t0 = time.perf_counter()
                try:
                    res = await asyncio.wait_for(
                        session.call_tool(paso["tool"], args),
                        timeout=paso.get("timeout", 900),
                    )
                    ms = (time.perf_counter() - t0) * 1000
                    txt = texto_del_resultado(res)
                    reg.update(
                        {
                            "ok": True,
                            "isError": bool(getattr(res, "isError", None) if getattr(res, "isError", None) is not None else getattr(res, "is_error", False)),
                            "ms": round(ms, 1),
                            "chars_respuesta": len(txt),
                            "tokens_respuesta": ntok(txt),
                            "respuesta_recorte": txt[: paso.get("recorte", 1200)],
                            "respuesta_completa_en": None,
                        }
                    )
                    sc = getattr(res, "structuredContent", None)
                    if sc is None:
                        sc = getattr(res, "structured_content", None)
                    if sc is not None:
                        s = json.dumps(sc, ensure_ascii=False)
                        reg["structuredContent"] = s[:600]
                        reg["tokens_structured"] = ntok(s)
                        dk = sc.get("document_key") if isinstance(sc, dict) else None
                        if dk:
                            claves[paso["id"]] = dk
                    if paso["id"] not in claves:
                        # fallback: extraer document_key del texto JSON devuelto
                        try:
                            j = json.loads(txt)
                            if isinstance(j, dict) and j.get("document_key"):
                                claves[paso["id"]] = j["document_key"]
                        except Exception:
                            pass
                    if paso.get("volcar"):
                        p = os.path.join(os.path.dirname(out_path), paso["volcar"])
                        with open(p, "w", encoding="utf-8", errors="replace") as f:
                            f.write(txt)
                        reg["respuesta_completa_en"] = p
                except Exception as e:
                    ms = (time.perf_counter() - t0) * 1000
                    msg = f"{type(e).__name__}: {e}"
                    reg.update(
                        {
                            "ok": False,
                            "isError": None,
                            "ms": round(ms, 1),
                            "excepcion": msg,
                            "chars_respuesta": len(msg),
                            "tokens_respuesta": ntok(msg),
                            "respuesta_recorte": msg[: paso.get("recorte", 1200)],
                        }
                    )
                out["llamadas"].append(reg)
                print(f"  [{paso['id']}] {reg['ms']} ms  tokens={reg['tokens_respuesta']}  "
                      f"isError={reg.get('isError')} ok={reg.get('ok')}", flush=True)

    errlog.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("escrito", out_path)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
