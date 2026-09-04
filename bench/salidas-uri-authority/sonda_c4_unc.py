"""N37 — C4 medido de verdad: ¿confina FileX sobre una raíz UNC, y a qué precio?

En esta máquina SÍ hay recurso UNC (`sonda_unc.json`: `\\\\localhost\\D$` con 48
entradas), así que C4 —«traducir la *authority* a UNC»— se puede medir en vez de
descartarse por falta de material. Tres preguntas, en orden:

  1. **¿Funciona?** ¿`Confinamiento` construye sobre una raíz UNC, y `resolver()`
     concede dentro y deniega fuera?
  2. **¿Colapsa el ALIAS?** UNC es un segundo nombre del mismo objeto NTFS. El
     proyecto ya pagó esto con los nombres 8.3 (trampa 33: *`normcase(abspath)`
     NO identifica un destino… daba dos dueños del mismo fichero*). Si
     `realpath` no lleva la UNC a su forma local, C4 mete en el confinamiento un
     aliasing que el predicado léxico no puede ver.
  3. **¿Qué se cuela por el alias?** Con una raíz LOCAL declarada, ¿deniega la
     forma UNC del mismo fichero? ¿Y al revés?

La 2 y la 3 son las que deciden, porque la 1 puede salir que sí y aun así ser
mala idea.

Va en fichero por la TRAMPA 19 (el shell se come los backslashes).
"""

from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import confinamiento as _conf  # noqa: E402

UNC_REPO = "\\\\localhost\\D$\\Work\\research\\FileX"
LOCAL_REPO = "D:\\Work\\research\\FileX"
FICHERO = "CLAUDE.md"


def _intenta(fn, *a, **k):
    try:
        return {"ok": True, "valor": fn(*a, **k)}
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:160])}


def main() -> int:
    out: dict = {"python": sys.version.split()[0]}

    # ---- 1. ¿funciona una raíz UNC?
    p1: dict = {"raiz": UNC_REPO}
    p1["existe"] = os.path.exists(UNC_REPO)
    p1["tras_preparar"] = _conf.Confinamiento._preparar([UNC_REPO])
    c = None
    try:
        c = _conf.Confinamiento([UNC_REPO])
        p1["construye"] = True
        p1["lectura"] = c.lectura
        p1["resolver_dentro"] = _intenta(c.resolver, os.path.join(UNC_REPO, FICHERO))
        p1["resolver_fuera"] = _intenta(c.resolver, "D:\\Work\\research\\ASR")
        p1["puede_leer_la_forma_LOCAL_del_mismo_fichero"] = c.puede_leer(
            os.path.join(LOCAL_REPO, FICHERO))
    except Exception as e:
        p1["construye"] = False
        p1["error"] = "%s: %s" % (type(e).__name__, e)
    out["P1_funciona"] = p1

    # ---- 2. ¿colapsa el alias? (la pregunta que decide)
    p2 = {
        "realpath_de_la_UNC": _intenta(os.path.realpath, UNC_REPO),
        "realpath_de_la_LOCAL": _intenta(os.path.realpath, LOCAL_REPO),
    }
    ru = p2["realpath_de_la_UNC"].get("valor")
    rl = p2["realpath_de_la_LOCAL"].get("valor")
    p2["realpath_las_iguala"] = (ru is not None and rl is not None
                                 and _conf._norm(ru) == _conf._norm(rl))
    # Identidad NTFS: ¿son el MISMO objeto? (lo que el léxico no puede ver)
    try:
        su = os.stat(os.path.join(UNC_REPO, FICHERO))
        sl = os.stat(os.path.join(LOCAL_REPO, FICHERO))
        p2["mismo_objeto_ntfs"] = (su.st_dev, su.st_ino) == (sl.st_dev, sl.st_ino)
        p2["st_dev_ino_unc"] = [su.st_dev, su.st_ino]
        p2["st_dev_ino_local"] = [sl.st_dev, sl.st_ino]
    except Exception as e:
        p2["mismo_objeto_ntfs"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    out["P2_alias"] = p2

    # ---- 3. ¿qué se cuela por el alias, en las dos direcciones?
    p3: dict = {}
    try:
        cl = _conf.Confinamiento([LOCAL_REPO])
        p3["raiz_LOCAL_concede_forma_local"] = cl.puede_leer(
            os.path.join(LOCAL_REPO, FICHERO))
        p3["raiz_LOCAL_concede_forma_UNC"] = cl.puede_leer(
            os.path.join(UNC_REPO, FICHERO))
    except Exception as e:
        p3["raiz_LOCAL"] = "%s: %s" % (type(e).__name__, e)
    if c is not None:
        p3["raiz_UNC_concede_forma_unc"] = c.puede_leer(os.path.join(UNC_REPO, FICHERO))
        p3["raiz_UNC_concede_forma_local"] = c.puede_leer(os.path.join(LOCAL_REPO, FICHERO))
    # El caso que importa para la política: una raíz de SERVIDOR local y un
    # cliente que declara la misma carpeta por su nombre UNC.
    from filex import mcp as _mcp
    p3["interseca_local_con_unc"] = _mcp.Raices._interseca([LOCAL_REPO], [UNC_REPO])
    p3["interseca_unc_con_local"] = _mcp.Raices._interseca([UNC_REPO], [LOCAL_REPO])
    out["P3_cuela"] = p3

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
