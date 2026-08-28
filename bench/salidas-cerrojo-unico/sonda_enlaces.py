"""b4: *«un destino que sea un ENLACE a otro fichero sigue dando dos claves»*.

Es el pendiente 4 de `cerrojo-de-maquina.md` §12, y no es un caso de laboratorio:
dos claves son **dos dueños del mismo fichero**, que es exactamente el agujero
que el cerrojo viene a tapar. N-b lo dejó abierto por una razón buena, y hay que
respetarla: `realpath` de la ruta ENTERA cerraría el enlace, pero **el destino
puede no existir al reservar y sí existir al soltar**, y una clave que se mueve
entre las dos llamadas deja el candado tomado hasta que muera el proceso.

Se reproducen los TRES alias que Windows da sin privilegios ni trucos, y se mide
qué remedio cierra cada uno:

  * **enlace duro** (`mklink /H`) — no necesita privilegio ninguno.
  * **enlace simbólico** (`mklink`) — necesita privilegio o modo desarrollador:
    si no se puede crear, eso también es un resultado.
  * **unión de directorio** (`mklink /J`) — no necesita privilegio.

Y se mide el candidato a remedio: la **identidad de fichero de NTFS**
(`st_dev`, `st_ino`), que es lo único que iguala un enlace duro, porque un
enlace duro **no tiene «destino» que resolver**: los dos nombres son igual de
reales.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

from filex import nucleo  # noqa: E402


def mklink(args: list[str], cwd: str) -> tuple[int, str]:
    r = subprocess.run(["cmd", "/c", "mklink", *args], cwd=cwd,
                       capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def identidad(ruta: str):
    try:
        st = os.stat(ruta)
        return (st.st_dev, st.st_ino)
    except OSError:
        return None


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S")}
    base = tempfile.mkdtemp(prefix="filex-enlaces-")
    print(f"desechable: {base}")
    antes = sorted(os.listdir(base))          # R21: listar antes y despues

    real_dir = os.path.join(base, "real")
    os.makedirs(real_dir)
    real = os.path.join(real_dir, "salida.webp")
    with open(real, "wb") as f:
        f.write(b"RIFF....WEBP" + b"\0" * 100)

    casos = []

    # --- 1. enlace duro ------------------------------------------------------
    duro = os.path.join(base, "duro.webp")
    rc, sal = mklink(["/H", duro, real], base)
    casos.append(("enlace duro (mklink /H)", duro, rc == 0, sal))

    # --- 2. enlace simbólico -------------------------------------------------
    sim = os.path.join(base, "sim.webp")
    rc, sal = mklink([sim, real], base)
    casos.append(("enlace simbolico (mklink)", sim, rc == 0, sal))

    # --- 3. unión de directorio ---------------------------------------------
    union_dir = os.path.join(base, "union")
    rc, sal = mklink(["/J", union_dir, real_dir], base)
    por_union = os.path.join(union_dir, "salida.webp")
    casos.append(("union de directorio (mklink /J)", por_union, rc == 0, sal))

    clave_real = nucleo._clave_destino(real)
    id_real = identidad(real)
    print(f"real : {real}")
    print(f"clave: {clave_real}")
    print(f"ident: {id_real}")

    filas = []
    for etiqueta, alias, creado, sal in casos:
        fila = {"caso": etiqueta, "alias": alias, "creado": creado,
                "salida_mklink": sal}
        if not creado:
            print(f"-- {etiqueta}: NO SE PUDO CREAR -> {sal}")
            filas.append(fila)
            continue
        ck = nucleo._clave_destino(alias)
        idn = identidad(alias)
        fila["clave"] = ck
        fila["misma_clave_lexica"] = ck == clave_real
        fila["misma_identidad_ntfs"] = idn is not None and idn == id_real
        fila["identidad"] = str(idn)

        # ¿DOS DUEÑOS? Es la prueba que importa, y se hace con el cerrojo real.
        r1 = nucleo._reservar_destino(real)
        r2 = nucleo._reservar_destino(alias)
        fila["reserva_real"] = r1
        fila["reserva_alias"] = r2
        fila["dos_duenos"] = bool(r1 and r2)
        nucleo._soltar_destino(alias)
        nucleo._soltar_destino(real)

        print(f"-- {etiqueta}")
        print(f"   clave alias  : {ck}")
        print(f"   MISMA CLAVE (lexica) : {fila['misma_clave_lexica']}")
        print(f"   MISMA IDENTIDAD NTFS : {fila['misma_identidad_ntfs']}  {idn}")
        print(f"   reserva real={r1} alias={r2}  -> DOS DUENOS: {fila['dos_duenos']}")
        filas.append(fila)
    res["casos"] = filas

    # --- 4. lo que cuesta el remedio ----------------------------------------
    print("== 4. coste de la identidad NTFS (os.stat) ==")
    for _ in range(200):
        identidad(real)
    m_ex, m_no = [], []
    inexistente = os.path.join(base, "no-existe.webp")
    for _ in range(20000):
        t = time.perf_counter()
        identidad(real)
        m_ex.append((time.perf_counter() - t) * 1e6)
    for _ in range(20000):
        t = time.perf_counter()
        identidad(inexistente)
        m_no.append((time.perf_counter() - t) * 1e6)
    res["coste_us"] = {
        "stat_destino_que_existe": round(statistics.median(m_ex), 1),
        "stat_destino_que_no_existe": round(statistics.median(m_no), 1),
        "n": len(m_ex),
    }
    print(f"  os.stat sobre destino que existe   : "
          f"{res['coste_us']['stat_destino_que_existe']} us")
    print(f"  os.stat sobre destino que NO existe: "
          f"{res['coste_us']['stat_destino_que_no_existe']} us  "
          f"(el caso normal: el destino aun no esta)")

    despues = sorted(os.listdir(base))
    res["R21"] = {"antes": antes, "despues": despues}
    print(f"== R21: antes={antes}  despues={despues} ==")

    with open(os.path.join(AQUI, "sonda_enlaces.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

    # el desechable entero, incluido lo que dejaron los `mklink`
    subprocess.run(["cmd", "/c", "rmdir", "/S", "/Q", base],
                   capture_output=True, timeout=60)
    print(f"desechable borrado: {not os.path.exists(base)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
