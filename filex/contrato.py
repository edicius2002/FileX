"""Puente al contrato de verificación. **No reimplementa nada.**

El hito 3 está escrito: `bench/scripts/verificador.py`, 5.197 líneas, biblioteca
estándar y cero dependencias, con el contrato de CINCO puntos, 15 reglas de
fidelidad, la regla G6 y cuatro estados de cobertura. Este módulo solo lo hace
importable desde el núcleo mientras siga viviendo en `bench/`.

**Deuda declarada:** el verificador debería MUDARSE aquí, no importarse desde
`bench/`. Se deja como está a propósito, porque moverlo ahora rompería las citas
`bench/scripts/verificador.py:NNN` de doce informes y del patrón oro. La mudanza
es trabajo del hito 3.
"""

from __future__ import annotations

import importlib.util
import os
import sys

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bench", "scripts", "verificador.py",
)

_mod = None
_intentado = False


def verificador():
    """El módulo del verificador, o `None` si no está disponible.

    Devolver `None` en vez de reventar es deliberado: el criterio de aceptación
    del hito 1 dice que una pieza que falta **se informa**, no tumba la CLI.
    """
    global _mod, _intentado
    if _intentado:
        return _mod
    _intentado = True
    if not os.path.isfile(_RUTA):
        return None
    try:
        spec = importlib.util.spec_from_file_location("filex_verificador", _RUTA)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["filex_verificador"] = mod
        spec.loader.exec_module(mod)
        _mod = mod
    except Exception:
        _mod = None
    return _mod


def verificar(salida: str, entrada: str | None, pedido: dict, censo: dict | None) -> dict:
    """Ejecuta los cinco puntos. Sin censo, el punto 5 se declara NO cubierto.

    Eso no es una laguna: es la única lectura honesta. El punto 5 no se puede
    verificar a posteriori, y darlo por bueno porque nadie miró es exactamente el
    fallo que el contrato existe para no cometer.
    """
    v = verificador()
    if v is None:
        return {
            "veredicto": "no_verificado",
            "motivo": "el verificador no está disponible",
            "cobertura": {},
            "hallazgos": [],
        }
    return v.verificar(salida, pedido=pedido, entrada=entrada, censo=censo)


def resumen(res: dict) -> str:
    """Una línea legible. Para el humano; para un modelo va el dict entero."""
    v = res.get("veredicto", "?")
    h = res.get("hallazgos") or []
    if not h:
        return v
    peor = [x for x in h if x.get("severidad") == "fallo"] or h
    x = peor[0]
    return f"{v} · {x.get('regla', '?')}: {x.get('mensaje', '')}"
