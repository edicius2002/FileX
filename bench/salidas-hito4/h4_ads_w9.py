"""W9 reproducido DENTRO de FileX: el confinamiento del núcleo concede un ADS.

`RESULTADOS-MCP.md` §5 midió que la referencia oficial deniega **28 de 29**
vectores, y que **el único concedido son los flujos de datos alternativos**:
`«raíz»\\dentro.txt:oculto` devuelve bytes **distintos de los del fichero que se
validó**, dentro de la raíz permitida. De ahí sale **R12**.

**El núcleo de FileX tiene el predicado y no lo llama.** `nombre_seguro()`
(`filex/confinamiento.py:51`) devuelve `False` para `dentro.png:oculto`, pero
`Confinamiento.resolver()` **nunca lo consulta**: solo está pensado para el
nombre de SALIDA. Resultado: el mismo hueco que W9, en las dos direcciones.

Este script (a) lo demuestra, (b) prueba el parche propuesto **sin tocar el
fichero de otro agente** —lo aplica en memoria— y (c) comprueba que el parche no
rompe nada, reejecutando `pruebas/test_hito1.py` y `pruebas/test_hito4.py`.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_ads_w9.py

**No arregla nada en disco.** La corrección vive en el núcleo (R10) y va como
«cambio que pido» en `bench/hito4-mcp.md` §8, con el diff exacto.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

from filex import confinamiento as C                              # noqa: E402
from filex.mcp import Servicio, Trabajos                          # noqa: E402
from filex.nucleo import FileX                                    # noqa: E402


# ------------------------------------------------------- el parche propuesto


def _lexico_ok_parcheado(self, ruta: str) -> bool:
    """`Confinamiento._lexico_ok` + R12 sobre **cada componente** de la ruta."""
    if not ruta or len(ruta) > C.MAX_LONGITUD:
        return False
    if ruta.count(os.sep) + (ruta.count(os.altsep) if os.altsep else 0) > C.MAX_COMPONENTES:
        return False
    if "\x00" in ruta:
        return False
    resto = os.path.splitdrive(os.path.abspath(ruta))[1]
    if os.altsep:
        resto = resto.replace(os.altsep, os.sep)
    for comp in resto.split(os.sep):
        if comp in ("", ".", ".."):
            continue
        if not C.nombre_seguro(comp):
            return False
    return True


def _resolver_parcheado(self, entrada: str, salida: str):
    """`FileX._resolver` + R12 sobre el NOMBRE DE SALIDA.

    El parche de `_lexico_ok` cierra la LECTURA y **no la escritura**, porque
    `_resolver` valida el *directorio* del destino y **el nombre del fichero de
    salida no lo mira nadie**. `nombre_seguro()` existe para esto exacto y en
    todo el paquete solo lo llama... `pruebas/test_hito1.py`.
    """
    if not C.nombre_seguro(os.path.basename(os.path.abspath(salida))):
        raise C.Denegado()
    if self.confinamiento is None:
        return os.path.abspath(entrada), os.path.abspath(salida)
    ent = self.confinamiento.resolver(entrada)
    dsal = os.path.dirname(os.path.abspath(salida)) or "."
    self.confinamiento.resolver(dsal, escritura=True)
    return ent, os.path.abspath(salida)


def escenario(etiqueta: str) -> dict:
    raiz = tempfile.mkdtemp(prefix="h4-w9-")
    origen = os.path.join(raiz, "e.png")
    shutil.copyfile(os.path.join(RAIZ, "corpus", "imagen", "trivial.png"), origen)

    lectura = os.path.join(raiz, "dentro.png")
    shutil.copyfile(origen, lectura)
    ads_lectura = lectura + ":oculto"
    try:
        with open(ads_lectura, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + b"SECRETO!" * 8)
    except OSError:
        return {"etiqueta": etiqueta, "error": "el sistema no admite ADS"}

    victima = os.path.join(raiz, "victima.txt")
    with open(victima, "w", encoding="utf-8") as fh:
        fh.write("contenido legitimo")

    sv = Servicio(FileX(raices_lectura=[raiz]),
                  Trabajos(tempfile.mkdtemp(prefix="h4-w9t-")))

    leer = sv.despachar("inspect", {"ruta": ads_lectura})
    escribir = sv.despachar("convert", {"entrada": origen,
                                        "salida": victima + ":carga.webp"})
    fin = None
    if "job_id" in escribir:
        for _ in range(100):
            time.sleep(0.15)
            fin = sv.despachar("job", {"job_id": escribir["job_id"],
                                       "accion": "resultado"})
            if fin["estado"] != "working":
                break
    ads_escrito = os.path.exists(victima + ":carga.webp")

    d = {
        "etiqueta": etiqueta,
        "LECTURA_ads_concedida": "error" not in leer,
        "LECTURA_bytes_devueltos": leer.get("bytes"),
        "ESCRITURA_ads_aceptada": "error" not in escribir,
        "ESCRITURA_veredicto": (fin or {}).get("veredicto"),
        "ESCRITURA_ads_existe_en_disco": ads_escrito,
        "victima_visible_intacta": open(victima, encoding="utf-8").read(),
        # controles: el parche no puede romper el caso legítimo
        "CONTROL_lectura_normal_ok": "error" not in sv.despachar(
            "inspect", {"ruta": lectura}),
        "CONTROL_fuera_denegado": "error" in sv.despachar(
            "inspect", {"ruta": "C:/Windows/win.ini"}),
    }
    shutil.rmtree(raiz, ignore_errors=True)
    return d


def main() -> int:
    antes = escenario("SIN parche (núcleo tal como está hoy)")

    orig_lex = C.Confinamiento._lexico_ok
    C.Confinamiento._lexico_ok = _lexico_ok_parcheado
    try:
        medio = escenario("CON media corrección (solo _lexico_ok)")
    finally:
        C.Confinamiento._lexico_ok = orig_lex

    orig_res = FileX._resolver
    C.Confinamiento._lexico_ok = _lexico_ok_parcheado
    FileX._resolver = _resolver_parcheado
    try:
        despues = escenario("CON la corrección COMPLETA (lectura + escritura)")
    finally:
        C.Confinamiento._lexico_ok = orig_lex
        FileX._resolver = orig_res

    # Regresión: el parche no puede romper las suites existentes.
    py = os.path.join(RAIZ, ".venv-mcp-filex", "Scripts", "python.exe")
    guion = os.path.join(AQUI, "_h4_w9_regresion.py")
    with open(guion, "w", encoding="utf-8") as fh:
        fh.write(
            "import sys, os, unittest\n"
            f"sys.path.insert(0, {RAIZ!r})\n"
            f"sys.path.insert(0, {AQUI!r})\n"
            "from h4_ads_w9 import _lexico_ok_parcheado, _resolver_parcheado\n"
            "from filex import confinamiento as C\n"
            "from filex.nucleo import FileX\n"
            "C.Confinamiento._lexico_ok = _lexico_ok_parcheado\n"
            "FileX._resolver = _resolver_parcheado\n"
            "sys.path.insert(0, os.path.join(sys.path[1], 'pruebas'))\n"
            "l = unittest.TestLoader()\n"
            "s = unittest.TestSuite([l.discover('pruebas', pattern='test_hito1*'),\n"
            "                        l.discover('pruebas', pattern='test_hito4*')])\n"
            "r = unittest.TextTestRunner(verbosity=0).run(s)\n"
            "print('REGRESION', r.testsRun, len(r.failures), len(r.errors))\n"
        )
    try:
        p = subprocess.run([py, "-X", "utf8", guion], cwd=RAIZ,
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=1800, check=False)
        linea = [x for x in (p.stdout or "").splitlines() if x.startswith("REGRESION")]
        regresion = linea[-1] if linea else f"no concluyó (rc={p.returncode})"
    except subprocess.TimeoutExpired:
        regresion = "tiempo agotado"
    finally:
        try:
            os.remove(guion)
        except OSError:
            pass

    res = {"antes": antes, "media_correccion": medio, "despues": despues,
           "regresion_test_hito1_y_4": regresion,
           "formato_regresion": "REGRESION <pruebas> <fallos> <errores>"}
    salida = os.path.join(AQUI, "h4_ads_w9.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
