"""El contrato de verificación. **No reimplementa nada:** envuelve el núcleo.

HITO 3 — DEUDA CERRADA. Hasta el 22/08/2026 este módulo cargaba
`bench/scripts/verificador.py` con `importlib.util.spec_from_file_location`,
es decir **importaba por ruta un fichero de otro árbol**. Ya no: el verificador
—5.197 líneas, biblioteca estándar, cero dependencias, contrato de CINCO puntos,
15 reglas de fidelidad, la regla G6 y cuatro estados de cobertura— vive en
`filex/verificador.py` y aquí se importa con un `from . import` normal.

`bench/scripts/verificador.py` sigue existiendo como **envoltorio**, porque 19
arneses de `bench/` lo importan por esa ruta y varios informes publican su CLI
literal. El envoltorio aliasea en `sys.modules`, así que **hay un solo
objeto-módulo**: no existe la posibilidad de que las dos vías diverjan.

**Y la razón por la que la mudanza no se había hecho era falsa** (medido en
`bench/hito3-mudanza.md` §1): en todo el repositorio no hay ni una sola cita
`verificador.py:NNN`, y la única referencia con número de línea que existe ya
estaba caducada por el crecimiento del propio fichero. Aun así, la copia es
byte a byte, así que todo número de línea se conserva.

Lo que este módulo aporta encima del verificador es **la política del núcleo**,
que no es la misma que la del prototipo de laboratorio:

- devuelve `no_verificado` en vez de reventar cuando la pieza falta, y
- resume el veredicto en una línea para el humano, dejando el `dict` entero
  para el modelo.
"""

from __future__ import annotations

from . import verificador as _verificador


def verificador():
    """El módulo del verificador, o `None` si no está disponible.

    Se mantiene como FUNCIÓN, y no se sustituye por el módulo a secas, porque
    `filex/trabajo.py` la llama así para reutilizar `censar_dir` y no tener dos
    censos divergiendo. Cambiar la firma aquí rompería ese módulo, que es de
    otro agente.

    Devolver `None` en vez de reventar era deliberado cuando la carga podía
    fallar (fichero ausente en otro árbol). Ahora es un `import` del propio
    paquete y **no puede** devolver `None`: si `filex.verificador` no está,
    `filex` no está. Se conserva el contrato de la función —puede devolver
    `None`— para no obligar a `trabajo.py` a cambiar, y porque un núcleo que
    informa de la pieza que falta en vez de tumbar la CLI sigue siendo el
    criterio de aceptación del hito 1.
    """
    return _verificador


def verificar(salida: str, entrada: str | None, pedido: dict, censo: dict | None) -> dict:
    """Ejecuta los cinco puntos. Sin censo, el punto 5 se declara NO cubierto.

    Eso no es una laguna: es la única lectura honesta. El punto 5 no se puede
    verificar a posteriori, y darlo por bueno porque nadie miró es exactamente el
    fallo que el contrato existe para no cometer.
    """
    v = verificador()
    if v is None:  # pragma: no cover - hoy imposible; ver docstring de verificador()
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
