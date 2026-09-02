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

EL AGUJERO DE LAS TABLAS, Y DÓNDE ESTABA DE VERDAD LA FRONTERA
--------------------------------------------------------------

La trampa 49 lo denunció así: *«`EXT_A_FIRMAS`, `EXT_FAMILIA`, `EXT_SIN_FIRMA`,
`FIRMAS` y `MARCAS_FTYP` son tablas de módulo, no llamadas»*, y arreglar
`EXT_FAMILIA` movió 3 de las 53 salidas del patrón oro **sin caducar ni una
arista**. Y §2.3 de `bench/deuda-sondeo.md` decía lo contrario: *«el cierre
incluye las constantes de módulo»*, con `EXT_TABULARES` de ejemplo.

**Los dos tenían razón a medias, y la frontera no era la que ninguno decía —
MEDIDO** (`bench/huella-y-tablas.md` §2, mutando el fuente y mirando si la
huella se mueve, no deduciendo):

* **Las cinco tablas SÍ estaban en el cierre.** `_tabla()` registra los
  `Assign` de nivel superior desde el primer día, así que el problema nunca fue
  «tabla contra llamada».
* De las cinco, **`FIRMAS` y `MARCAS_FTYP` SÍ caducaban** —son literales
  completos, como `EXT_TABULARES`— y **`EXT_A_FIRMAS`, `EXT_FAMILIA` y
  `EXT_SIN_FIRMA` no**. El agujero era de **3 de 5**, no de 5 de 5.
* **La frontera es el SITIO DEL VALOR, no su tipo:** las tres ciegas se
  declaran vacías (`EXT_FAMILIA = set()`) y las puebla un ``for`` de nivel
  superior. `_tabla()` solo miraba `FunctionDef`, `ClassDef` y `Assign`, así
  que hasheaba el `set()` y **las 196 líneas de las cinco sentencias
  ejecutables de nivel superior de `verificador.py` eran invisibles**.

**Y el mismo agujero estaba en el componente `motor`, sin que nadie lo mirara**
(ídem §3): `cadena_de_clase()` hasheaba solo las `ClassDef`, así que `HILOS` en
`motores.py` y `MARGEN_TOPE`, `TIMEOUT_DENTRO`, `_HILO` y la función
`entorno()` en `motor_contenedor.py` —el tope que corre DENTRO del contenedor,
que decide el `rc` de toda arista documental— no movían nada.

**El arreglo es uno solo para los dos, y es el cierre de nombres:**

* `_tabla()` devuelve ahora **una lista de nodos por nombre**, y adjunta cada
  sentencia ejecutable de nivel superior (``for``, ``if``, ``while``, ``with``,
  ``try``) a **los nombres de módulo que MUTA** — conservador igual que
  `_referidos()`: destino de asignación, `del`, subíndice o receptor de un
  método.
* `cadena_de_clase()` hashea el **cierre desde el nombre de la clase**, no la
  `ClassDef` suelta. Es la misma maquinaria de `de_alcance()` con otra entrada.

**Y no cuesta granularidad — MEDIDO** (ídem §3.2): en `motores.py` cada motor
alcanza **3 de 8** nombres de nivel superior y los tres nativos siguen sin
verse entre sí; en `motor_contenedor.py` alcanzan **15 de 17**, pero los dos
que sobran son las clases hermanas y **los tres documentales ya compartían la
base entera por MRO**, así que ahí no había granularidad que perder.

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
   pueden cambiar bajo una medida sin mover la huella. **Esto NO cambia** con
   el arreglo de las tablas: una tabla en el código entra; un JSON de datos
   sigue fuera.
5. **Un fichero sin `huella` se aplica igual.** Es la regla de legado, y es
   deliberada: degradar por prudencia costaba 153 aristas medidas con este
   mismo código. Se aplica **y se declara** en `sondeo.diagnostico()`.
6. **Una sentencia ejecutable de nivel superior que no muta NINGÚN nombre de
   módulo sigue fuera** — y es a propósito. El único caso en `verificador.py`
   es `if __name__ == "__main__": main()`; meterlo caducaría las 215 aristas
   cada vez que se toque el CLI, que es ruido puro. Si algún día una de esas
   sentencias muta un objeto IMPORTADO, cae en la limitación 3.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import os
import sys
import textwrap

#: Desde dónde se calcula el cierre de llamadas del contrato. `verificar()` es
#: la única puerta de los cinco puntos; `sondear` entra porque `verificar` la
#: llama, y con ella todas las sondas de cabecera.
ENTRADAS_CONTRATO = ("verificar",)

#: Cuántos caracteres de `sha256` se guardan. 16 hex = 64 bits: de sobra para
#: detectar un cambio, y cabe en una línea de un JSON que lee un humano.
LARGO = 16

_PAQUETE = os.path.dirname(os.path.abspath(__file__))


# -------------------------------------------------------------- intérprete


def interprete_actual() -> str:
    """El intérprete que está calculando la huella AHORA mismo.

    `ast.dump` **no da la misma cadena entre versiones de Python** — MEDIDO
    con control positivo (trampa 105 de `CLAUDE.md`): el mismo commit, sobre
    los mismos bytes, sella `eec752a87e8927cf`/`c918f1be90ef0652` bajo 3.11.9
    y `16ddd8d13d61c4f1`/`605a04d57983eaa5` bajo 3.14.4 para
    `verificador.py`/`motores.py`, y los **siete motores caducan a la vez**
    bajo 3.13 — la firma de un fallo global, no de un cambio real.

    Esto no es una propiedad del CÓDIGO que se hashea: es una propiedad del
    PROCESO que hashea. No entra en `de_alcance()` ni en `de_clase()` —eso
    mezclaría dos cosas distintas dentro de un mismo número—, entra como
    campo declarado al lado de `huella`, igual que `build` ya declara la
    máquina. `sondeo.aplicar()` lo compara ANTES de comparar la huella: si no
    coincide, la comparación no dice nada y hay que negarse a hacerla, no
    hacerla y llamar al resultado «caducado» (decisión del 02/09, no
    reabrir).

    GRANULARIDAD — corregida en la ronda 7, y es la interacción con la propia
    CI del proyecto (`.github/workflows/suite.yml` fija `python: ['3.11']`,
    no un parche exacto). La versión original de C43 usaba
    `platform.python_version()` completo (el triple: mayor.menor.parche)
    porque era exactamente lo que medía la trampa 105 (3.11.9 frente a
    3.14.4, dos MENORES distintas). Eso funcionaba en la máquina del
    proyecto y habría fallado en el runner real: `.venv-mcp-filex` sella con
    **3.11.9** y el runner (`ubuntu-latest`, `actions/setup-python@v5` con
    `python-version: '3.11'`) resuelve a **3.11.16** — MEDIDO, `gh run view`
    sobre la ejecución más reciente de `suite.yml`. Sellar con el triple
    completo habría declarado esos cinco ficheros «no comparables» en CADA
    ejecución del runner, para siempre, aunque el código midiera lo mismo:
    el propio arreglo de `C43` habría bloqueado la fusión que vino a
    proteger.

    Se usa **`mayor.menor`** (`"3.11"`, no `"3.11.9"`) porque es la
    granularidad que la CI del proyecto YA se compromete a mantener estable
    en su matriz, y porque es la ÚNICA granularidad que no exige adivinar
    qué parche exacto tendrá el runner en la próxima ejecución —eso cambia
    solo con la caché de `actions/setup-python`, fuera del control de este
    repositorio—. Sigue protegiendo contra la trampa 105 real (3.11 frente a
    3.14 se siguen declarando distintos). **PENDIENTE, sin medir en esta
    máquina**: si `ast.dump` puede diferir entre dos versiones de
    MANTENIMIENTO de la misma menor (p. ej. 3.11.9 frente a 3.11.16) — se
    intentó comprobar con un segundo intérprete 3.11.x en esta máquina y no
    fue posible (§1 de `bench/acuerdo-y-cruce.md`: CPython 3.11 ya no
    publica binarios de Windows, solo fuente, y compilarlo estaba fuera de
    alcance de esta ronda). Sí se comprobó, leyendo el `ast.py` que trae esta
    instalación, que `dump()`/`parse()` no tienen ni una rama condicionada a
    `sys.platform` u `os.name`: la plataforma (Windows/Linux) no debería
    entrar en el resultado para el mismo intérprete, solo el parche podría —
    y CPython no suele tocar la gramática ni el volcado del AST en versiones
    de mantenimiento, por política, aunque eso no se ha medido aquí con dos
    intérpretes reales lado a lado.
    """
    return "%d.%d" % sys.version_info[:2]


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

    La huella de cada clase es la de su **cierre de nombres**, no la de su
    `ClassDef` suelta: si no, `MARGEN_TOPE` y `TIMEOUT_DENTRO` —el tope que
    corre DENTRO del contenedor, que decide el `rc` de toda arista
    documental— y la función `entorno()` cambian sin mover la huella (MEDIDO,
    §3 del informe). Es el mismo agujero de la trampa 49 en el otro
    componente, y se cierra con la misma maquinaria.

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
    tabla = _tabla(arbol)
    for n in arbol.body:
        if isinstance(n, ast.ClassDef):
            fuera[n.name] = _sello(tabla, _cierre(tabla, (n.name,)))
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
    tabla = _tabla(arbol)
    for n in arbol.body:
        if isinstance(n, ast.ClassDef) and n.name == nombre:
            return _sha(_sello(tabla, _cierre(tabla, (nombre,))))
    return "sin_clase"


# ------------------------------------------------- cierre de llamadas (alcance)


#: Sentencias de nivel superior que NO aportan valor a ningún nombre: nunca se
#: adjuntan a nadie. El docstring del módulo es un `Expr`.
_INERTES = (ast.Import, ast.ImportFrom, ast.Expr, ast.Pass)


def _mutados(nodo: ast.AST) -> set:
    """Nombres que una sentencia de nivel superior puede MUTAR.

    Conservador a propósito, igual que `_referidos()`: todo `Name` que aparezca
    como destino de asignación o de `del` (contextos `Store`/`Del`), y todo
    `X` que reciba una llamada a método (`X.add(...)`, `X.update(...)`) o un
    subíndice. Sobra alguno —la variable de un `for` de módulo entra— y eso no
    hace daño: un nombre de más solo puede añadir sensibilidad, y un nombre de
    menos deja pasar un cambio que sí decide, que es el fallo que este módulo
    existe para no cometer.
    """
    fuera: set = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            fuera.add(n.id)
        elif isinstance(n, (ast.Attribute, ast.Subscript)):
            if isinstance(n.value, ast.Name):
                fuera.add(n.value.id)
    return fuera


def _tabla(arbol: ast.Module) -> dict:
    """Nombres de nivel superior → **lista** de nodos que los definen.

    Funciones, clases, constantes **y las sentencias ejecutables de nivel
    superior que las pueblan**. Lo tercero es el arreglo de la trampa 49: sin
    ello `EXT_FAMILIA = set()` se hasheaba vacío y el `for` que la llena —42
    extensiones que deciden el punto 1— no movía nada (MEDIDO, §2 del informe).

    Es una lista y no un nodo porque un nombre puede tener varias: la
    asignación inicial más cada bucle que lo modifica. `EXT_SIN_FIRMA` tiene
    tres.
    """
    t: dict = {}
    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            t.setdefault(n.name, []).append(n)
        elif isinstance(n, ast.Assign):
            for d in n.targets:
                if isinstance(d, ast.Name):
                    t.setdefault(d.id, []).append(n)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            t.setdefault(n.target.id, []).append(n)
        elif not isinstance(n, _INERTES):
            for nombre in _mutados(n):
                t.setdefault(nombre, []).append(n)
    return t


def _referidos(nodos: list) -> set:
    return {n.id for nodo in nodos for n in ast.walk(nodo)
            if isinstance(n, ast.Name)}


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
    return _sello(tabla, _cierre(tabla, entradas))


def _sello(tabla: dict, nombres) -> str:
    """`sha` de los nodos de `nombres`, por nombre y en orden de NOMBRE.

    Dentro de un nombre los nodos van en su orden de aparición en el fichero,
    que es el orden en que se ejecutan y por tanto el que decide el valor
    final: `EXT_SIN_FIRMA` se llena en un bucle y se poda en el siguiente, y
    permutarlos cambiaría la tabla.
    """
    nombres = sorted(nombres)
    if not nombres:
        return "sin_alcance"
    trozos = []
    for n in nombres:
        partes = [_sha(ast.dump(_limpio(nodo), annotate_fields=True,
                                include_attributes=False))
                  for nodo in tabla[n]]
        trozos.append(f"{n}=" + ",".join(partes))
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
           "de_modulo", "de_motor", "diferencias", "interprete_actual",
           "nombres_alcanzados", "normalizar", "olvidar"]
