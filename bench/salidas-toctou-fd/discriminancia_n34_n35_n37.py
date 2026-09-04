#!/usr/bin/env python3
"""Discriminancia de N34/N35/N37 con el cambio N38 presente.

Cada prueba tiene que ser VERDE con el código de hoy (mi cambio incluido) y
ROJA contra el defecto que su N cerró. Aquí se reintroduce el defecto EXACTO de
cada N por monkeypatch SOBRE el código actual —para probar que el cambio N38 no
las ha dejado vacuas— y se corre su clase. Es la A/B de las trampas 60/109/119:
verde con el arreglo, roja contra el de antes.

(N34 y N37-authority viven en `filex/mcp.py`, N35 y N37-raíz-vacía en
`filex/confinamiento._preparar`; N38 no toca ninguno de los dos —178 inserciones,
0 deleciones en confinamiento—, así que esto lo confirma ejecutándolo.)
"""
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import filex.confinamiento as conf
import filex.mcp as mcp


def corre(clase, metodos=None):
    suite = unittest.TestSuite()
    ld = unittest.TestLoader()
    if metodos:
        for m in metodos:
            suite.addTest(clase(m))
    else:
        suite.addTests(ld.loadTestsFromTestCase(clase))
    r = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return r.testsRun, len(r.failures) + len(r.errors)


def con_bug(modulo, nombre, funcion_buggy, clase, metodos=None):
    """Corre `clase` con `modulo.nombre` reemplazado por la versión con bug."""
    original = getattr(modulo, nombre)
    setattr(modulo, nombre, funcion_buggy)
    try:
        return corre(clase, metodos)
    finally:
        setattr(modulo, nombre, original)


# --- bugs reintroducidos, tal como los describe cada N -----------------------

def _preparar_bug_n35(raices):
    """N35 ANTES: lanzaba ValueError en cuanto UNA raíz no confinaba (en vez de
    podarla). Reintroducido sobre la lógica de hoy."""
    out = []
    for r in raices or []:
        if not r or not str(r).strip():
            continue
        a = conf._norm(os.path.abspath(r))
        padre = os.path.dirname(a)
        if padre == a:
            raise ValueError("una raíz no confina (comportamiento anterior a N35)")
        out.append(a)
    return out


def _preparar_bug_n37_vacia(raices):
    """N37 ANTES (raíz vacía): NO se saltaba la raíz vacía, así que
    `abspath('')` metía el `cwd` del proceso como lista blanca."""
    out = []
    for r in raices or []:
        # (sin el `if not r ...: continue` que N37 añadió)
        a = conf._norm(os.path.abspath(r))
        padre = os.path.dirname(a)
        if padre == a:
            continue
        out.append(a)
    return out


def _uri_a_ruta_bug_n37_authority(uri):
    """N37 ANTES (authority): se quedaba con `p.path` y tiraba el netloc, que lo
    SUSTITUÍA por la unidad del proceso vía abspath."""
    from urllib.parse import urlparse, unquote
    p = urlparse(uri)
    if p.scheme and p.scheme != "file":
        return unquote(p.path)
    ruta = unquote(p.path)
    if os.name == "nt" and ruta.startswith("/") and len(ruta) > 2 and ruta[2] == ":":
        ruta = ruta[1:]
    return os.path.normpath(ruta)


def main():
    import test_hito1 as t1  # noqa
    import test_hito4 as t4  # noqa

    resultados = []

    # ---- verde con el código de hoy ----
    for etiqueta, mod, clase in [
        ("N35 RaicesMixtasN35", t1, t1.RaicesMixtasN35),
        ("N34 RaicesEnConcurrencia", t4, t4.RaicesEnConcurrencia),
        ("N37 AuthorityDeUriN37", t4, t4.AuthorityDeUriN37),
        ("N37 RaizVaciaN37", t4, t4.RaizVaciaN37),
        ("N35 RaicesMixtasPorMCP", t4, t4.RaicesMixtasPorMCP),
    ]:
        n, fallos = corre(clase)
        resultados.append((f"HOY  {etiqueta}", n, fallos, "VERDE" if fallos == 0 else "ROJO"))

    # ---- rojo contra el defecto de cada N (con N38 presente) ----
    n, f = con_bug(conf.Confinamiento, "_preparar",
                   staticmethod(_preparar_bug_n35).__func__, t1.RaicesMixtasN35)
    resultados.append(("BUG-N35 _preparar-raise → RaicesMixtasN35", n, f,
                       "DISCRIMINA" if f > 0 else "NO DISCRIMINA"))

    n, f = con_bug(conf.Confinamiento, "_preparar",
                   staticmethod(_preparar_bug_n37_vacia).__func__, t4.RaizVaciaN37)
    resultados.append(("BUG-N37 _preparar-vacia → RaizVaciaN37", n, f,
                       "DISCRIMINA" if f > 0 else "NO DISCRIMINA"))

    n, f = con_bug(mcp, "_uri_a_ruta", _uri_a_ruta_bug_n37_authority,
                   t4.AuthorityDeUriN37)
    resultados.append(("BUG-N37 _uri_a_ruta-netloc → AuthorityDeUriN37", n, f,
                       "DISCRIMINA" if f > 0 else "NO DISCRIMINA"))

    print("=" * 74)
    for etiqueta, n, f, veredicto in resultados:
        print(f"{veredicto:14s} {etiqueta:52s} ({n} pruebas, {f} fallos)")
    print("=" * 74)


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "pruebas"))
    main()
