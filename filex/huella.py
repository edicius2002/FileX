"""La huella del CÓDIGO que decide una arista. La sexta dimensión.

`grafo.py` fija que la arista mínima viable es
`(origen, destino, motor, parametrización, build)`. **Faltaba una, y su
ausencia costó 20 medidas falsas de 21** —MEDIDO el 22/08: 21 aristas que un
agente midió `nominal` quedaron obsoletas en cuanto se arreglaron la sonda y la
invocación, y al resondearlas 20 salieron `real`—. El `build` protege contra
cambiar de MÁQUINA; nada protegía contra cambiar de CÓDIGO.

QUÉ SE HASHEA, Y POR QUÉ NO EL FICHERO
--------------------------------------

Un `sha256` del fichero es **demasiado sensible**: arreglar una falta de
ortografía en un comentario de `motores.py` caducaría las 133 aristas de
ImageMagick y ffmpeg. Una huella que caduca por todo se acaba desactivando, y
entonces no protege nada. Aquí se hashea el **AST normalizado**:

* `ast.dump(..., include_attributes=False)` — sin números de línea: **mover una
  función de sitio no caduca nada**.
* Sin docstrings, en módulo, clase y función.
* Los comentarios ya no existen en un AST.

Y se hashea con **granularidad**, en tres componentes que se comparan por
separado:

``motor``
    El AST de la CLASE del motor y de sus bases dentro de `filex`, en orden de
    MRO. Granularidad **por motor**: tocar `ImageMagick.orden` no caduca
    ffmpeg. Las bases entran porque `PandocEnContenedor` es un cascarón —la
    lógica vive en `_EnContenedor`— y una huella que solo mirase la subclase no
    vería el cambio.

``invocacion``
    El AST de `filex/invocacion.py` entero. Es **global** —cualquier cambio
    caduca los seis motores— y aun así compensa: son 200 líneas, decide el
    `rc` de TODA arista (`stdin=DEVNULL`, el tope, matar el árbol,
    `arrancado`), y **MEDIDO sobre el historial del repositorio: ha cambiado 0
    veces desde el commit inicial**. El coste esperado en falsos positivos es
    cero y el agujero que tapa es real.

``contrato``
    El AST de las funciones de `filex/verificador.py` **alcanzables desde
    `verificar()`**, no del fichero. `verificador.py` tiene 5.241 líneas, y el
    encargo lo dice bien: *un cambio en la regla de fidelidad de audio no
    debería caducar las aristas de imagen*. La respuesta no necesita un mapa a
    mano —que se queda obsoleto en silencio, que es el fallo que estamos
    arreglando—: **la fidelidad no decide la arista**, `verificar()` no la
    llama, y el cierre de llamadas lo dice solo.

LO QUE ESTA HUELLA **NO** PROTEGE — declararlo es parte del diseño
-----------------------------------------------------------------

1. **No es por CATEGORÍA.** El cierre de `verificar()` incluye todas las sondas
   —`_wav` y `_png` viven las dos ahí—, así que tocar la sonda de audio caduca
   también las aristas de imagen. Separarlo exigiría un mapa categoría→funciones
   mantenido a mano, y un mapa que se queda obsoleto sin avisar es peor que un
   falso positivo que se paga resondeando.
2. **El cierre es ESTÁTICO.** Una llamada por `getattr`, por tabla de despacho
   construida en ejecución o por `importlib` no se ve. Se compensa siendo
   conservador: entra todo nombre de módulo REFERENCIADO, se llame o no.
3. **No ve fuera de `filex`.** Una versión distinta de Python o de una
   biblioteca cambia el resultado y la huella no se entera. Para eso está el
   `build`, y `build` es del MOTOR, no del intérprete: **queda PENDIENTE**.
4. **No ve los DATOS.** `bench/salidas-referencia/referencia.json` y el corpus
   pueden cambiar bajo una medida sin mover la huella.
5. **Un fichero sin `huella` se aplica igual.** Es la regla de legado, y es
   deliberada: degradar por prudencia costaba 153 aristas medidas con este
   mismo código. Se aplica **y se declara** en `sondeo.diagnostico()`.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import textwrap

#: Desde dónde se calcula el cierre de llamadas del contrato. `verificar()` es
#: la única puerta de los cinco puntos; `sondear` entra porque `verificar` la
#: llama, y con ella todas las sondas de cabecera.
ENTRADAS_CONTRATO = ("verificar",)

#: Cuántos caracteres de `sha256` se guardan. 16 hex = 64 bits: de sobra para
#: detectar un cambio, y cabe en una línea de un JSON que lee un humano.
LARGO = 16

_PAQUETE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- normalizar


def _sin_docstring(nodo: ast.AST) -> None:
    cuerpo = getattr(nodo, "body", None)
    if not cuerpo:
        return
    p = cuerpo[0]
    if (isinstance(p, ast.Expr) and isinstance(p.value, ast.Constant)
            and isinstance(p.value.value, str)):
        nodo.body = cuerpo[1:] or [ast.Pass()]


def _limpio(arbol: ast.AST) -> ast.AST:
    for n in ast.walk(arbol):
        if isinstance(n, (ast.Module, ast.ClassDef,
                          ast.FunctionDef, ast.AsyncFunctionDef)):
            _sin_docstring(n)
    return arbol


def normalizar(fuente: str) -> str:
    """El AST sin docstrings, sin comentarios y **sin números de línea**."""
    return ast.dump(_limpio(ast.parse(textwrap.dedent(fuente))),
                    annotate_fields=True, include_attributes=False)


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:LARGO]


def de_fuente(fuente: str) -> str:
    """Huella de un texto de Python.

    Una fuente que no compila **no revienta el registro** —misma regla que un
    JSON ilegible o un binario que falta— pero tampoco puede dar la huella de
    nadie: devuelve un valor propio que NUNCA coincidirá con el de una fuente
    válida, así que el sondeo se degrada en vez de aplicarse a ciegas.
    """
    try:
        return _sha(normalizar(fuente))
    except SyntaxError:
        return "nocompila:" + _sha(fuente)


def de_fichero(ruta: str) -> str:
    try:
        with open(ruta, encoding="utf-8") as fh:
            return de_fuente(fh.read())
    except OSError:
        return "ilegible"


def de_modulo(mod) -> str:
    ruta = getattr(mod, "__file__", None)
    return de_fichero(ruta) if ruta else "sin_fichero"


# ------------------------------------------------------------------- clases


def _clases_de_fichero(ruta: str) -> dict:
    """`{nombre: huella}` de las clases de nivel superior de un módulo.

    Se parsea el FICHERO una vez y se cachea. `inspect.getsource` por clase
    vuelve a barrer el fichero entero cada vez, y con seis motores repartidos en
    dos módulos eso se notaba en el arranque.
    """
    k = ("fichero", ruta)
    if k in _CACHE:
        return _CACHE[k]
    fuera: dict = {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
    except (OSError, SyntaxError):
        _CACHE[k] = fuera
        return fuera
    for n in arbol.body:
        if isinstance(n, ast.ClassDef):
            fuera[n.name] = _sha(ast.dump(_limpio(n), annotate_fields=True,
                                          include_attributes=False))
    _CACHE[k] = fuera
    return fuera


def cadena_de_clase(cls) -> list[tuple[str, str]]:
    """`[(nombre, huella)]` de la clase y sus bases DENTRO de `filex`, en MRO.

    `object` y todo lo que venga de fuera del paquete quedan fuera: no es
    código de este proyecto y el `build` no lo cubre (limitación 3).
    """
    out = []
    for c in cls.__mro__:
        try:
            fichero = inspect.getsourcefile(c)
        except (TypeError, OSError):
            continue
        if not fichero or not os.path.abspath(fichero).startswith(_PAQUETE):
            continue
        h = _clases_de_fichero(os.path.abspath(fichero)).get(c.__name__)
        if h is None:      # clase anidada: se cae al camino lento
            try:
                h = de_fuente(inspect.getsource(c))
            except (OSError, TypeError):
                continue
        out.append((c.__name__, h))
    return out


def de_clase(cls) -> str:
    """Se cachea por clase: `sondear_todos()` la pide una vez por motor y
    `inspect.getsource` + `ast.parse` cuestan ~11 ms cada vez. Una clase no
    cambia a mitad de un proceso; quien recargue módulos llama a `olvidar()`."""
    k = ("clase", cls.__module__, cls.__qualname__)
    if k not in _CACHE:
        _CACHE[k] = _sha("|".join(f"{n}={h}" for n, h in cadena_de_clase(cls)))
    return _CACHE[k]


def de_clase_en_fuente(fuente: str, nombre: str) -> str:
    """La misma huella, sobre un texto en vez de sobre un objeto importado.

    Sin esto no se puede PROBAR la granularidad: haría falta editar
    `motores.py` a mitad de una prueba.
    """
    arbol = ast.parse(textwrap.dedent(fuente))
    for n in arbol.body:
        if isinstance(n, ast.ClassDef) and n.name == nombre:
            return _sha("|".join([
                f"{nombre}=" + _sha(ast.dump(_limpio(n), annotate_fields=True,
                                             include_attributes=False))]))
    return "sin_clase"


# ------------------------------------------------- cierre de llamadas (alcance)


def _tabla(arbol: ast.Module) -> dict:
    """Nombres de nivel superior → nodo. Funciones, clases **y constantes**.

    Las constantes entran porque deciden: `EXT_TABULARES` es una constante de
    módulo nueva, y su llegada cambió el veredicto de 8 aristas (commit
    9f99cae).
    """
    t = {}
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            t[n.name] = n
        elif isinstance(n, ast.Assign):
            for d in n.targets:
                if isinstance(d, ast.Name):
                    t[d.id] = n
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            t[n.target.id] = n
    return t


def _referidos(nodo: ast.AST) -> set:
    return {n.id for n in ast.walk(nodo) if isinstance(n, ast.Name)}


def nombres_alcanzados(fuente: str, entradas=ENTRADAS_CONTRATO) -> set:
    """Cierre transitivo de los nombres de módulo que `entradas` puede tocar.

    **Conservador a propósito:** entra todo nombre REFERENCIADO, se llame o no.
    Un cierre que se queda corto deja pasar un cambio que sí decide, y ése es
    justo el fallo que este módulo existe para no cometer.
    """
    try:
        tabla = _tabla(ast.parse(textwrap.dedent(fuente)))
    except SyntaxError:
        return set()
    return _cierre(tabla, entradas)


def _cierre(tabla: dict, entradas) -> set:
    vistos: set = set()
    pila = [e for e in entradas if e in tabla]
    while pila:
        n = pila.pop()
        if n in vistos:
            continue
        vistos.add(n)
        for ref in _referidos(tabla[n]):
            if ref in tabla and ref not in vistos:
                pila.append(ref)
    return vistos


def de_alcance(fuente: str, entradas=ENTRADAS_CONTRATO) -> str:
    """Huella del cierre. En orden de NOMBRE, no de aparición: reordenar el
    fichero no caduca nada.

    Se parsea UNA vez: `verificador.py` son 5.241 líneas y hacerlo dos veces
    —una aquí y otra en `nombres_alcanzados`— doblaba el arranque.
    """
    try:
        tabla = _tabla(ast.parse(textwrap.dedent(fuente)))
    except SyntaxError:
        return "nocompila:" + _sha(fuente)
    nombres = sorted(_cierre(tabla, entradas))
    if not nombres:
        return "sin_alcance"
    trozos = []
    for n in nombres:
        nodo = _limpio(tabla[n])
        trozos.append(f"{n}=" + _sha(ast.dump(nodo, annotate_fields=True,
                                              include_attributes=False)))
    return _sha("|".join(trozos))


def de_contrato() -> str:
    return de_alcance(_leer(os.path.join(_PAQUETE, "verificador.py")),
                      ENTRADAS_CONTRATO)


def _leer(ruta: str) -> str:
    try:
        with open(ruta, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- la huella


_CACHE: dict = {}


def de_motor(motor_o_cls) -> dict:
    """Los tres componentes. Se cachea lo GLOBAL: el fichero no cambia a mitad
    de una ejecución, y parsear 5.241 líneas por motor sí se nota."""
    cls = motor_o_cls if isinstance(motor_o_cls, type) else type(motor_o_cls)
    if "invocacion" not in _CACHE:
        _CACHE["invocacion"] = de_fichero(os.path.join(_PAQUETE, "invocacion.py"))
        _CACHE["contrato"] = de_contrato()
    return {"motor": de_clase(cls),
            "invocacion": _CACHE["invocacion"],
            "contrato": _CACHE["contrato"]}


def de_motor_por_nombre(nombre: str) -> dict:
    """La huella de un motor del que solo se sabe el nombre.

    `sondeo.aplicar` solo recibe el nombre, y **no se le cambia la firma a los
    dos sitios que ya la llaman**: la importación va aquí dentro, diferida, para
    que `motores` pueda seguir importando `sondeo` sin ciclo.

    Si el motor no se encuentra —un fichero de sondeo huérfano, un motor que se
    borró— se devuelven las dos componentes globales y NINGUNA de motor. Con eso
    `diferencias()` no compara `motor`, y el fichero se aplica: es lo mismo que
    hacía antes de existir la huella, y no hay motivo para castigarlo más.
    """
    if "clases" not in _CACHE:
        from . import motores
        _CACHE["clases"] = {}
        for cls in list(motores.MOTORES) + motores._descubrir():
            try:
                _CACHE["clases"][cls().nombre] = cls
            except Exception:
                continue
    cls = _CACHE["clases"].get(nombre)
    if cls is None:
        h = de_motor(_Vacia)
        h.pop("motor", None)
        return h
    return de_motor(cls)


class _Vacia:
    """Portadora de las componentes globales cuando no hay clase de motor."""


def olvidar() -> None:
    """Tira la caché. Para las pruebas y para quien recargue módulos."""
    _CACHE.clear()


def diferencias(guardada: dict | None, actual: dict) -> list:
    """Componentes que el fichero DECLARA y ya no coinciden.

    Lo que el fichero no declara no se compara: un sondeo escrito antes de que
    existiera un componente no se tira por un campo que su autor no pudo
    escribir. Lo que no lleva `huella` **ninguna** es cosa de `sondeo.aplicar`,
    no de aquí.
    """
    if not isinstance(guardada, dict):
        return []
    return sorted(k for k, v in guardada.items()
                  if k in actual and v != actual[k])


__all__ = ["ENTRADAS_CONTRATO", "cadena_de_clase", "de_alcance", "de_clase",
           "de_clase_en_fuente", "de_contrato", "de_fichero", "de_fuente",
           "de_modulo", "de_motor", "diferencias", "nombres_alcanzados",
           "normalizar", "olvidar"]
