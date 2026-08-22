# -*- coding: utf-8 -*-
"""K1 / hito 5 — genera `MANIFIESTO.md` desde `sonda.json` y `camino.json`.

`CLAUDE.md` §6: no se versionan salidas binarias regenerables. Se borran y queda
el manifiesto con nombre, `sha256`, tamaño **y la orden exacta que las
reproduce**. El manifiesto no se escribe a mano: se genera, para que no pueda
divergir de lo que se midió.

    python bench/salidas-hito5/_manifiesto.py
"""
from __future__ import annotations

import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    with open(os.path.join(AQUI, "sonda.json"), encoding="utf-8") as f:
        res = json.load(f)
    cam = {}
    p = os.path.join(AQUI, "camino.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            cam = json.load(f)

    L = []
    L.append("# MANIFIESTO — `bench/salidas-hito5/`")
    L.append("")
    L.append("**Generado por `_manifiesto.py`. No se edita a mano.**")
    L.append("")
    L.append("Las salidas binarias de este directorio **se han borrado**: son "
             "regenerables y el repositorio ya pagó una vez el error de "
             "versionarlas (986 MB de pack, 99,9 % binario). Lo que queda es "
             "esta tabla y los `.json` con las medidas.")
    L.append("")
    L.append("## Cómo se reproduce todo")
    L.append("")
    L.append("```")
    L.append("# 1. Docker Desktop arrancado y la imagen presente:")
    L.append("docker image inspect filex-c13 --format '{{.Id}}'")
    L.append("# 2. las 36 aristas candidatas (~400 s):")
    L.append("python bench/salidas-hito5/_sonda.py")
    L.append("# 3. las medianas de n=9 de las cuatro que deciden el hito (~500 s):")
    L.append("python bench/salidas-hito5/_medianas.py")
    L.append("# 4. las tablas de aristas que van en filex/motor_contenedor.py:")
    L.append("python bench/salidas-hito5/_tabla.py")
    L.append("# 5. la comparación de los dos caminos:")
    L.append("python bench/salidas-hito5/_camino.py")
    L.append("# 5b. que el tope DENTRO del contenedor no deja huérfanos:")
    L.append("python bench/salidas-hito5/_tope.py")
    L.append("# 6. este manifiesto:")
    L.append("python bench/salidas-hito5/_manifiesto.py")
    L.append("```")
    L.append("")
    L.append("Cada invocación de la sonda es un `docker run` construido por "
             "`argv_docker()` y lanzado por `filex.invocacion.ejecutar()`, en un "
             "`DirectorioDeTrabajo` desechable que se censa antes de borrarse.")
    L.append("")
    L.append("> **La sonda NO lleva el tope `timeout -k 5 N` dentro del "
             "contenedor, y el producto SÍ.** Está así a propósito: es el "
             "registro de lo que se midió, y lo que se midió incluye el fallo "
             "que ese tope arregla (`bench/hito5-documental.md` §4.4). Por eso "
             "las órdenes de esta tabla no coinciden con las que construye hoy "
             "`filex/motor_contenedor.py`.")
    L.append("")
    L.append("## Entradas (SÍ se versionan: 23 KB de texto)")
    L.append("")
    L.append("Copiadas de `bench/salidas-aristas/c8/in/`, que las generó el "
             "21/08. Todas llevan el centinela `FILEXSENTINELA7743` y la tabla "
             "`AX-1 / BX-2 / CX-3`.")
    L.append("")
    L.append("| fichero | bytes | sha256 |")
    L.append("|---|---:|---|")
    ent = os.path.join(AQUI, "entradas")
    if os.path.isdir(ent):
        import hashlib
        for n in sorted(os.listdir(ent)):
            r = os.path.join(ent, n)
            h = hashlib.sha256(open(r, "rb").read()).hexdigest()
            L.append(f"| `{n}` | {os.path.getsize(r)} | `{h}` |")
    L.append("")
    L.append("## Salidas de la sonda (BORRADAS — la tabla es el registro)")
    L.append("")
    L.append("`orden` es lo que se ejecuta **dentro** del contenedor; el "
             "`docker run` que lo envuelve es idéntico para todas y está en "
             "`_sonda.py::argv_docker`.")
    L.append("")
    L.append("| id | motor | arista | rc | ms | bytes | car. | centinela | sha256 | orden dentro del contenedor |")
    L.append("|---|---|---|---:|---:|---:|---:|:---:|---|---|")
    for r in res:
        argv = r.get("argv") or []
        # lo que va después del nombre de la imagen
        try:
            i = argv.index("filex-c13")
            dentro = " ".join(argv[i + 1:])
            ep = argv[argv.index("--entrypoint") + 1]
            dentro = f"{ep} {dentro}"
        except (ValueError, IndexError):
            dentro = " ".join(argv[-4:])
        L.append("| {id} | {m} | `{o}→{d}` | {rc} | {ms:.0f} | {b} | {c} | {ce} | `{s}` | `{dn}` |".format(
            id=r["id"], m=r["motor"], o=r["origen"], d=r["destino"],
            rc=r.get("rc"), ms=r.get("ms", 0), b=r.get("bytes", 0),
            c=r.get("caracteres", 0),
            ce="sí" if r.get("centinela") else "—",
            s=(r.get("sha256") or "—")[:16] or "—", dn=dentro))
    L.append("")
    if cam:
        L.append("## Los dos caminos (`_camino.py`, salidas borradas)")
        L.append("")
        L.append("| camino | ok | bytes | caracteres | centinela | contrato | sha256 |")
        L.append("|---|:---:|---:|---:|:---:|---|---|")
        for c in cam.get("caminos", []):
            L.append("| {n} | {ok} | {b} | {ca} | {ce} | {v} | `{s}` |".format(
                n=c["nombre"], ok="sí" if c["ok"] else "no", b=c["bytes"],
                ca=c["caracteres"], ce="sí" if c["centinela"] else "**no**",
                v=c["veredicto"], s=(c.get("sha256") or "—")[:16]))
        L.append("")
    L.append("## Ficheros que SÍ se quedan")
    L.append("")
    L.append("| fichero | qué es |")
    L.append("|---|---|")
    L.append("| `_sonda.py` | ejecuta las 36 aristas candidatas, una por directorio desechable, con censo |")
    L.append("| `_medianas.py` | medianas de n=9 con los dos testigos de ruido |")
    L.append("| `_tabla.py` | genera las tablas `_MEDIDAS`/`_MUERTAS` de `filex/motor_contenedor.py` |")
    L.append("| `_camino.py` | los dos caminos `docx→pdf`, por el núcleo |")
    L.append("| `_tope.py` | reproduce el cuelgue y comprueba que no queda contenedor vivo |")
    L.append("| `_manifiesto.py` | esto |")
    L.append("| `sonda.json` | rc, ms, bytes, sha256, censo del punto 5 y centinela de las 36 |")
    L.append("| `sonda-txt.json` | las tres reejecuciones del cuelgue de `docx→txt` |")
    L.append("| `medianas.json` | las cuatro medianas de n=9 y los testigos |")
    L.append("| `camino.json` | la comparación de los dos caminos |")
    L.append("| `tope.json` | el `rc=124` del tope de dentro y el censo de huérfanos |")
    L.append("| `entradas/` | 23 KB de documentos con centinela |")
    L.append("")

    with open(os.path.join(AQUI, "MANIFIESTO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("MANIFIESTO.md:", len(L), "líneas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
