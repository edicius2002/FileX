"""R18 — un directorio de trabajo propio y DESECHABLE por conversión.

**Y no es higiene: es REQUISITO DE COSTE.** MEDIDO
(`bench/contrato-quinto-punto.md` §2.2): con R18 el quinto punto del contrato
cuesta **+11,0 %**; sin él, sobre un directorio de 1.000 ficheros, **×8,6 el
contrato entero**. R18 es lo que hace viable el punto 5.

Y el punto 5 es **el único del contrato que no se puede verificar a posteriori**:
hay que estar mirando cuando el motor escribe. Sin censo, **49 de las 53 salidas
del patrón oro bajan de `ok` a `ok_parcial`**. Por eso este módulo no es una
utilidad de limpieza: es el sitio donde la verificación entra dentro de la
conversión en vez de ser un paso posterior.

Lo que motivó la regla, MEDIDO (`bench/aristas-nominales.md` §5.2):

    ffmpeg -i trivial.mp4 DEST/t.mpd   -> t.mpd (1.234 B) en el destino
                                          y 528.447 B de segmentos DASH en el cwd
    magick trivial.png ... DEST/u.html -> u.html y u.png en el destino
                                          y u_map.shtml en el cwd

Aparecieron como **33 ficheros no pedidos en la raíz del repositorio**.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time

from . import cerrojo

_VERIFICADOR = None

#: El prefijo de los desechables. Es lo único que los identifica desde fuera, y
#: por eso el barrido no puede tocar nada que no empiece por aquí.
PREFIJO = "filex-"

#: Cuántos segundos tiene que llevar ahí un desechable **sin candado** para que
#: el barrido se atreva con él. Con candado la decisión es exacta y la edad no
#: pinta nada; sin candado —un `filex` viejo, o uno cuyo candado se degradó— la
#: edad es lo único que hay, y 24 h es holgado a propósito: el coste de dejar un
#: directorio un día más es unos megas, y el de borrar el de otro es la trampa
#: 26 con otro recurso.
EDAD_SIN_CANDADO = 24 * 3600.0

#: `FILEX_BARRER=0` lo apaga. Existe por el mismo motivo que
#: `FILEX_CERROJO_DESTINO`: medir el antes y el después en la misma tanda.
_VAR_BARRER = "FILEX_BARRER"

_ya_barrido = False


def _censar_dir(directorio: str) -> dict:
    """Censo {nombre: tamaño} de un directorio, un solo `scandir`, sin recursión.

    Se delega en `bench/scripts/verificador.py` si está importable, para no tener
    dos implementaciones del mismo censo divergiendo. Si no lo está, esta copia
    es equivalente.
    """
    global _VERIFICADOR
    if _VERIFICADOR is None:
        from . import contrato

        _VERIFICADOR = contrato.verificador()
    if _VERIFICADOR is not None and hasattr(_VERIFICADOR, "censar_dir"):
        return _VERIFICADOR.censar_dir(directorio)
    d = {}
    try:
        with os.scandir(directorio) as it:
            for e in it:
                try:
                    d[e.name] = e.stat(follow_symlinks=False).st_size if e.is_file() else -1
                except OSError:
                    d[e.name] = -1
    except OSError:
        return {}
    return d


def _nombre_candado(ruta: str) -> str:
    """El nombre del candado que declara vivo a un desechable.

    Se deriva de la ruta y **nada más**, para que quien encuentre el directorio
    huérfano pueda calcularlo sin saber nada del que lo creó — en particular,
    sin preguntar por su PID, que es lo que la trampa 31 declara imposible de
    automatizar en esta máquina.
    """
    return "dir:" + os.path.normcase(os.path.abspath(ruta))


def barrer_huerfanos(base: str | None = None, *,
                     edad_sin_candado: float = EDAD_SIN_CANDADO,
                     una_vez: bool = False) -> dict:
    """N14 — borra los desechables que dejó un `filex` MUERTO. Y solo esos.

    El fallo, MEDIDO de pasada por N-b (`bench/cerrojo-de-maquina.md` §4.1) y
    cuantificado aquí (`bench/watcher-y-desechables.md` §3): `cerrar()` vive en
    el `finally` de `convertir()`, y **un `taskkill /F` no ejecuta `finally`**.
    Cada `filex` matado a mitad deja **un directorio por salto en vuelo** en
    `%TEMP%`, con la salida a medias dentro. **El cerrojo se cura solo; R18 no.**

    **Y el remedio esconde exactamente la trampa 26 con otro recurso:** un
    barrido que borre el desechable de otro `filex` VIVO le quita el suelo a una
    conversión en curso — con el agravante ya medido de que, si ese directorio
    es el origen de un *bind mount*, Docker se queda respondiendo *«did not
    receive an exit event»* (`bench/hito5-documental.md` §1). Así que el barrido
    **tiene que saber si el dueño vive**, y lo sabe **sin preguntar por PID**:
    cada desechable toma un `cerrojo.Candado` con el nombre de su propia ruta, y
    el candado lo suelta el sistema operativo cuando el proceso muere.

    Tres respuestas, y las tres son decisiones:

    ================================  =========================================
    Estado del desechable             Qué se hace
    ================================  =========================================
    candado TOMADO                    **nada**: el dueño está vivo
    candado libre y su fichero existe  se borra: el dueño murió
    sin fichero de candado             se borra **solo** si tiene más de
                                      `edad_sin_candado` (un `filex` anterior a
                                      esto, o uno cuyo candado se degradó)
    ================================  =========================================

    Devuelve el parte: `{mirados, vivos, borrados, bytes, sin_candado_jovenes,
    errores, ms}`. Se devuelve y no se imprime: quien llama decide si lo enseña.
    """
    global _ya_barrido
    t0 = time.perf_counter()
    parte = {"mirados": 0, "vivos": 0, "borrados": 0, "bytes": 0,
             "sin_candado_jovenes": 0, "errores": 0, "ms": 0.0,
             "saltado": False}
    if (os.environ.get(_VAR_BARRER) or "1").strip() == "0":
        parte["saltado"] = True
        return parte
    if una_vez:
        if _ya_barrido:
            parte["saltado"] = True
            return parte
        _ya_barrido = True

    base = base or tempfile.gettempdir()
    ahora = time.time()
    try:
        entradas = list(os.scandir(base))
    except OSError:
        parte["errores"] += 1
        parte["ms"] = round((time.perf_counter() - t0) * 1000, 3)
        return parte

    # **El directorio de candados EMPIEZA POR `filex-`**, así que el barrido lo
    # veía como un desechable más — y lo habría borrado entero, llevándose por
    # delante los candados de todos los destinos en curso de la máquina. Es la
    # trampa 26 otra vez, cometida por el propio remedio, y salió en la primera
    # celda de la sonda (`bench/watcher-y-desechables.md` §3.3). Se excluye por
    # IDENTIDAD, no por nombre: quien mueva `FILEX_CERROJO_DIR` sigue protegido.
    try:
        prohibido = os.path.normcase(os.path.abspath(cerrojo.directorio()))
    except OSError:
        prohibido = ""

    for e in entradas:
        if not e.name.startswith(PREFIJO):
            continue
        if prohibido and os.path.normcase(os.path.abspath(e.path)) == prohibido:
            continue
        try:
            if not e.is_dir(follow_symlinks=False):
                continue
        except OSError:
            parte["errores"] += 1
            continue
        parte["mirados"] += 1
        nombre = _nombre_candado(e.path)
        # **El orden importa:** `esta_libre` toma y suelta el candado, y al
        # hacerlo CREA el fichero. Preguntar por él después daría siempre `True`
        # y el barrido perdería la distinción entre «murió su dueño» y «nunca
        # tuvo candado» — que es justo la que decide si se aplica la edad.
        hay_fichero = os.path.exists(cerrojo.fichero(nombre))
        if not cerrojo.esta_libre(nombre):
            parte["vivos"] += 1
            continue
        if not hay_fichero:
            # No lo creó su dueño: lo acaba de crear `esta_libre`. Se deshace,
            # o el barrido siguiente lo leería como «tenía candado y murió» y se
            # saltaría la edad. En Windows falla si alguien lo tiene abierto,
            # que es exactamente lo que hay que respetar.
            try:
                os.remove(cerrojo.fichero(nombre))
            except OSError:
                pass
            try:
                edad = ahora - os.stat(e.path).st_mtime
            except OSError:
                parte["errores"] += 1
                continue
            if edad < edad_sin_candado:
                parte["sin_candado_jovenes"] += 1
                continue
        tam = _tamano_arbol(e.path)
        shutil.rmtree(e.path, ignore_errors=True)
        if os.path.exists(e.path):
            parte["errores"] += 1
            continue
        parte["borrados"] += 1
        parte["bytes"] += tam
        # Y el fichero de candado del que se acaba de enterrar. Aquí SÍ es
        # seguro también en POSIX —donde borrar el candado de otro sería una
        # carrera— porque el nombre viene de un `mkdtemp` que no se repite:
        # nadie va a volver a tomar el candado de un directorio que ya no está.
        try:
            os.remove(cerrojo.fichero(nombre))
        except OSError:
            pass

    parte["ms"] = round((time.perf_counter() - t0) * 1000, 3)
    return parte


def _tamano_arbol(ruta: str) -> int:
    total = 0
    for raiz, _d, ficheros in os.walk(ruta):
        for f in ficheros:
            try:
                total += os.stat(os.path.join(raiz, f)).st_size
            except OSError:
                pass
    return total


class DirectorioDeTrabajo:
    """Un directorio desechable por conversión, con censo de salida.

    Uso::

        with DirectorioDeTrabajo() as t:
            argv = motor.orden(entrada, t.destino("salida.webp"), pedido)
            res = invocacion.ejecutar(argv, cwd=t.ruta)
            censo = t.censo()          # ANTES de salir: después ya no existe
            t.recoger("salida.webp", destino_real)

    El `cwd` del motor va DENTRO. Validar la ruta de salida no basta: R8 y R16
    asumen que el motor escribe donde se le dice, y hay motores que no.
    """

    def __init__(self, prefijo: str = PREFIJO) -> None:
        self.ruta = tempfile.mkdtemp(prefix=prefijo)
        self._censo_final: dict | None = None
        self._recogidos: list[str] = []
        # N14: la señal de vida. No es exclusión —nadie más va a pedir ESTE
        # `mkdtemp`, que es único por construcción—: es lo que le permite a
        # `barrer_huerfanos` distinguir «el dueño murió» de «el dueño está
        # convirtiendo ahora mismo», y lo hace **sin preguntar por PID**. Lo
        # suelta el sistema operativo si nos matan, que es justo el caso.
        self._vivo = cerrojo.Candado(_nombre_candado(self.ruta),
                                     metadatos=self.ruta)
        self._vivo.tomar()

    # ------------------------------------------------------------------ API

    def destino(self, nombre: str) -> str:
        """Ruta dentro del directorio de trabajo para un nombre de salida."""
        return os.path.join(self.ruta, nombre)

    def censo(self) -> dict:
        """Censo del punto 5, en el formato que espera `verificador.verificar`.

        Con R18 el directorio está **vacío antes**, así que basta el censo de
        DESPUÉS: todo lo que haya aquí lo escribió el motor. Ese es justo el
        ahorro que convierte el punto 5 de ×8,6 en +11,0 %.
        """
        if self._censo_final is None:
            self._censo_final = _censar_dir(self.ruta)
        clave = os.path.abspath(self.ruta)
        return {"antes": {clave: {}}, "despues": {clave: dict(self._censo_final)}}

    def sobrantes(self, declarados) -> dict:
        """Lo que el motor escribió y NADIE pidió. `{nombre: bytes}`.

        Es la lectura humana del punto 5. El veredicto formal lo da el contrato.
        """
        cen = self._censo_final if self._censo_final is not None else _censar_dir(self.ruta)
        dec = {os.path.basename(d) for d in declarados}
        return {n: t for n, t in cen.items() if n not in dec}

    def recoger(self, nombre: str, destino_final: str) -> str:
        """Mueve una salida real fuera del desechable, antes de borrarlo."""
        origen = self.destino(nombre)
        os.makedirs(os.path.dirname(os.path.abspath(destino_final)) or ".", exist_ok=True)
        shutil.move(origen, destino_final)
        self._recogidos.append(destino_final)
        return destino_final

    def cerrar(self) -> None:
        """Borra el directorio ENTERO. Lo que no se recogió, se pierde: es
        exactamente lo que se quiere de un desechable.

        El candado de vida se suelta **después** del `rmtree`: si se soltara
        antes, un barrido de otro proceso podría colarse entre las dos líneas y
        borrar el directorio por debajo — que es el fallo que este candado
        existe para impedir, cometido por su propio dueño.
        """
        shutil.rmtree(self.ruta, ignore_errors=True)
        try:
            self._vivo.soltar()
        except OSError:
            pass
        try:
            os.remove(cerrojo.fichero(_nombre_candado(self.ruta)))
        except OSError:
            pass

    # -------------------------------------------------------------- contexto

    def __enter__(self) -> "DirectorioDeTrabajo":
        return self

    def __exit__(self, *exc) -> None:
        # El censo se toma aquí si nadie lo pidió: el punto 5 no se recupera
        # después, y salir sin haber mirado es perderlo para siempre.
        if self._censo_final is None:
            self._censo_final = _censar_dir(self.ruta)
        self.cerrar()
