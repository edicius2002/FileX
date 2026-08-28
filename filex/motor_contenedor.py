"""Hito 5 — el motor documental: LibreOffice, Pandoc y Calibre, en contenedor.

**Este fichero no se importa desde ningún sitio: se DESCUBRE.** `motores.py`
recorre los `filex/motor_*.py` y recoge las subclases de `Motor`. Un motor nuevo
no toca el registro, y por eso este módulo puede añadir 36 aristas al grafo sin
editar una línea de nadie.

Sin él, el estrato ofimático de FileX **no existe**: ni `docx→*`, ni `epub→*`,
ni `md→*`. Y el hito 1 se queda con un criterio de aceptación que no se puede
demostrar (`PLAN-ORQUESTADOR.md` §7, recuadro amarillo):

    «Resuelve 2 saltos **y explica por qué rechaza un camino que rasteriza**.»
    Con ffmpeg, ImageMagick y Ghostscript **no existe ningún par de formatos
    donde compitan un camino que conserva el texto y otro que lo rasteriza.»

Aquí sí existe, y con **el mismo binario a los dos lados**, que es la versión
fuerte del caso — MEDIDO (`bench/hito5-documental.md` §5):

    soffice --convert-to pdf  docx →  22 820 B, 456 caracteres, centinela OK
    soffice --convert-to png  docx →  38 798 B,   0 caracteres

La diferencia no está en la calidad del motor: **está en el camino**.

---

## Tres motores, tres clases, y por qué no una

El submotor lo elige **el grafo**, no este fichero. `Motor.orden()` no recibe la
`Arista` que se eligió, así que un solo motor con tres binarios dentro tendría
que volver a derivar la elección a partir del par de formatos — y entonces la
decisión estaría escrita dos veces, en el grafo y aquí, con la garantía de que
un día divergen. Con **una clase por submotor**, `docx→pdf` entra tres veces en
el grafo (LibreOffice 6,5 s con n=9; Pandoc 7,2 y Calibre 10,2 con n=1), el
grafo compara y `orden()` no tiene nada que adivinar.

La clase base **no hereda de `Motor` a propósito**: si heredara, `_descubrir()`
la recogería e intentaría sondear un motor abstracto.

## Por qué `docker run` y no `docker exec`

`docker exec` sobre el contenedor de ConvertX ya levantado obligaría a
`docker cp` de ida y de vuelta —tres procesos por conversión— y, sobre todo,
**mataría el quinto punto del contrato**: `docker cp` trae lo que se le nombra,
así que lo que el motor escribiera de más dentro del contenedor **no se vería
nunca**. Con `docker run` y un bind mount, **el directorio desechable del
anfitrión ES el `/trabajo` del contenedor**: el censo de `trabajo.py` ve lo que
el motor escribió, esté el motor donde esté. El punto 5 sobrevive a la frontera
del contenedor porque la frontera se cruza con un montaje y no con una copia.

**Y no es teórico** (`bench/hito5-documental.md` §4): `soffice --convert-to
txt:Text` sobre un DOCX **se cuelga y escribe un `.tmp` que crece a ~1,5 MB/s**
—471 859 200 B en los 240 s que tardó el timeout en matarlo— más un
`.~lock.salida.txt#`. **Ninguno de los dos ficheros se llama como la salida**, y
con `docker cp` no se habría visto ninguno. Con `docker run` los ve el censo, y
R18 los borra con el desechable.

## Las cuatro decisiones de invocación, y por qué

1. **La entrada se monta fichero a fichero y de solo lectura.** Montar su
   directorio padre le enseñaría al contenedor todo lo que hubiera al lado.
   Comprobado en ejecución: escribir en `/ent` da `Read-only file system`.
2. **`--mount` y no `-v`.** Una ruta de Windows lleva `D:` y `-v` parte por `:`.
3. **`--entrypoint` explícito.** La imagen trae `ENTRYPOINT ["bun","run",
   "dist/src/index.js"]` y `WorkingDir /app`: sin sustituirlo, la orden se le
   pasa **como argumentos a la aplicación web de ConvertX** y sale
   `Module not found: dist/src/index.js`. Sondeado en ejecución, no deducido.
4. **`--network none`.** Ninguno de los tres motores necesita red para convertir
   un documento local. Lo que no se necesita, no se concede.

## Y la que decide el hito: Calibre para `epub→pdf`, no LibreOffice

MEDIDO dos veces, por dos agentes distintos, con dos invocaciones distintas
(`docker exec` el 21/08, `docker run` el 22/08) y el mismo resultado:

| Vía | Resultado |
|---|---|
| `soffice --headless --convert-to pdf entrada.epub` | **rc=1**, sin salida, `Error: source file could not be loaded` |
| `ebook-convert entrada.epub salida.pdf` | **rc=0**, **26 817 B** —el mismo byte a byte que el 21/08—, 456 caracteres, centinela y tabla `AX-1` |

**LibreOffice exporta EPUB y no lo importa.** La arista existe; lo que fallaba
era la elección de motor — el bug de `ConvertX/src/converters/main.ts:213-229`.
Por eso `epub→pdf` está `REAL` en `CalibreEnContenedor` y `NOMINAL` en
`LibreOfficeEnContenedor`: una arista `nominal` **sale del grafo**
(`grafo._coste_paso` le suma infinito), así que el orquestador no puede
elegirla ni por accidente.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading

from . import formatos, invocacion
from .grafo import NOMINAL, REAL, SIN_SONDEAR, Arista
from .motores import Motor
from . import sondeo

#: **REFUTADO: `filex-convertx` no es una imagen, es un CONTENEDOR.**
#: `CLAUDE.md` §2 y `bench/aristas-nominales.md` §8 hablan de «la imagen
#: `filex-convertx`»; `docker image inspect filex-convertx` responde
#: **`No such image`**. La imagen es `ghcr.io/c4illin/convertx:latest` y
#: `filex-c13` es esa misma con `qpdf` y `tesseract` encima
#: (`bench/salidas-invocacion/Dockerfile.c13`). Se prueban en orden y se usa la
#: primera que exista: **sondear, no deducir**, también para el nombre.
IMAGENES = tuple(x for x in (os.environ.get("FILEX_IMAGEN_DOC"),
                             "filex-c13",
                             "ghcr.io/c4illin/convertx:latest") if x)

#: Topes. `CLAUDE.md` §3: ninguna invocación sin tope.
TIMEOUT_SONDA = 45.0
TIMEOUT_SONDA_IMAGEN = 120.0

#: **El tope de la conversión va DENTRO del contenedor, y esto es lo más
#: importante de este fichero después del bind mount. MEDIDO**
#: (`bench/hito5-documental.md` §4.4):
#:
#:     Matar el `docker run` NO mata el contenedor. Tres `soffice` colgados
#:     sobrevivieron **37 minutos** a `taskkill /F /T` sobre el cliente y al
#:     `--rm`. El cliente es un cliente de la API; el proceso vive en el demonio.
#:
#: Y hay una segunda mitad peor: cuando R18 borra el desechable, **el origen del
#: bind mount desaparece bajo un contenedor vivo** y este queda en un estado del
#: que `docker rm -f` responde *«tried to kill container, but did not receive an
#: exit event»*. El orden importa: **parar el contenedor y después borrar**.
#:
#: `timeout -k 5 N` de coreutils (9.10, comprobado dentro de la imagen) mata el
#: motor **desde dentro**, el contenedor sale con `rc=124` y `--rm` lo limpia.
#: El tope de `invocacion.ejecutar()` deja de ser la primera línea de defensa y
#: pasa a ser la segunda, que es donde debe estar.
#:
#: 110 s está **por debajo** de `invocacion.TIMEOUT_POR_DEFECTO` (120) a
#: propósito: el de dentro tiene que disparar primero. La arista documental más
#: lenta medida es Calibre `epub→pdf` con 20,6 s, así que el margen es de ×5.
#: ~~**Cambio que pido al núcleo** (§7.6 del informe): que `Motor.orden()` reciba
#: el timeout del que convierte, para no tener que adivinarlo aquí.~~
#: **APLICADO el 22/08:** `orden()` recibe el `timeout` de quien convierte y el
#: tope de dentro se DERIVA de él (`_tope_dentro`). Esta constante queda solo
#: como valor por defecto para cuando nadie pasa uno.
TIMEOUT_DENTRO = 110

#: Cuánto se le resta al tope de fuera para fijar el de dentro. El de dentro
#: tiene que disparar PRIMERO: si dispara el de fuera, se mata al cliente de
#: Docker y el contenedor sigue vivo — MEDIDO, 37 minutos.
MARGEN_TOPE = 10

#: **El contenedor que este HILO tiene lanzado ahora mismo** (a4).
#:
#: `Motor.parar()` no recibe argumentos y la instancia del motor es ÚNICA para
#: todo el proceso —`nucleo._un_salto` hace `self.motores[arista.motor]`—, así
#: que guardar el nombre en `self` haría que dos conversiones simultáneas se
#: pisaran el identificador y una parara el contenedor de la otra: la trampa 26
#: con un tercer recurso. Guardarlo por HILO no: un trabajo corre entero en su
#: propio hilo (`servicio.py` lanza `threading.Thread(target=corre, …)`), que es
#: la misma observación con la que N-a resolvió C34.
#:
#: Y lo escribe `_argv_docker`, que es el ÚNICO sitio donde se construye un
#: `docker run` de un motor: no hay una vía que se lo salte, y por eso no es
#: «un valor que hay que acordarse de fijar» —el defecto que este mismo fichero
#: ya documentó con `self._tope_dentro`—.
_HILO = threading.local()


# --------------------------------------------------------------- caché de sonda


def _fichero_cache() -> str:
    """La caché de la sonda vive FUERA del repositorio.

    Sondear los binarios dentro de la imagen cuesta **un arranque de
    contenedor**. Pagarlo en cada arranque de la CLI sería inaceptable, y no
    pagarlo nunca sería deducir en vez de sondear. El término medio honesto:
    **se sondea en ejecución y se cachea por ID de imagen**. Si la imagen
    cambia, el ID cambia y la sonda se repite sola.
    """
    return os.path.join(tempfile.gettempdir(), "filex-sonda-contenedor.json")


def _cache_leer(clave: str):
    try:
        with open(_fichero_cache(), encoding="utf-8") as f:
            return json.load(f).get(clave)
    except Exception:
        return None


def _cache_escribir(clave: str, valor) -> None:
    try:
        d = json.load(open(_fichero_cache(), encoding="utf-8"))
    except Exception:
        d = {}
    d[clave] = valor
    try:
        with open(_fichero_cache(), "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


#: El sondeo del entorno (demonio + imagen + binarios) es el MISMO para los tres
#: submotores. Se hace una vez por proceso: tres arranques de contenedor para
#: responder a la misma pregunta serían tres veces el coste y una vez la
#: información.
_ENTORNO: dict | None = None


def entorno(refrescar: bool = False) -> dict:
    """Sonda del entorno de contenedor. Devuelve siempre un dict, nunca lanza.

    Claves: `ok`, `motivo`, `imagen`, `imagen_id`, `servidor`, `binarios`.
    Los tres fallos posibles **no son el mismo fallo** y se distinguen: puede
    faltar `docker`, puede estar `docker` y no responder el demonio, y pueden
    estar los dos y no la imagen.
    """
    global _ENTORNO
    if _ENTORNO is not None and not refrescar:
        return _ENTORNO

    e = {"ok": False, "motivo": "", "imagen": "", "imagen_id": "",
         "servidor": "", "binarios": ()}

    ruta = invocacion.disponible("docker")
    if ruta is None:
        e["motivo"] = "no hay 'docker' en el PATH"
        _ENTORNO = e
        return e

    r = invocacion.ejecutar(["docker", "version", "--format", "{{.Server.Version}}"],
                            timeout=TIMEOUT_SONDA)
    servidor = (r.salida_txt or "").strip().splitlines()[0] if r.salida_txt.strip() else ""
    if not r.ok or not servidor:
        # Docker Desktop parado responde `npipe ... cannot find the file`; Docker
        # Desktop A MEDIO ARRANCAR responde **HTTP 500 con rc=0** — MEDIDO hoy,
        # y por eso no basta con mirar el código de salida.
        e["motivo"] = ("'docker' existe pero el demonio no responde "
                       "(¿Docker Desktop parado o arrancando?)")
        _ENTORNO = e
        return e
    e["servidor"] = servidor

    for img in IMAGENES:
        r = invocacion.ejecutar(["docker", "image", "inspect", img, "--format", "{{.Id}}"],
                                timeout=TIMEOUT_SONDA)
        if r.ok and (r.salida_txt or "").strip():
            e["imagen"] = img
            e["imagen_id"] = (r.salida_txt or "").strip()
            break
    if not e["imagen"]:
        e["motivo"] = ("el demonio responde pero no está ninguna de las imágenes: "
                       + ", ".join(IMAGENES))
        _ENTORNO = e
        return e

    e["binarios"] = _sondear_binarios(e["imagen"], e["imagen_id"])
    if not e["binarios"]:
        e["motivo"] = f"la imagen '{e['imagen']}' no trae ningún motor documental"
        _ENTORNO = e
        return e

    e["ok"] = True
    _ENTORNO = e
    return e


#: Lo que se busca dentro de la imagen. **Que `CLAUDE.md` §2 diga que la imagen
#: trae `soffice`, `pandoc` y `ebook-convert` es un dato de OTRA sesión**: aquí
#: se comprueba. El proyecto ya pagó por deducir en vez de sondear —`av1_nvenc`
#: aparece listado y no funciona; `paddlex` declara `limit_type='max'` donde la
#: sonda mide `'min'`.
BINARIOS = ("soffice", "pandoc", "ebook-convert")


def _sondear_binarios(imagen: str, imagen_id: str) -> tuple:
    clave = f"{imagen}@{imagen_id}"
    guardado = _cache_leer(clave)
    if isinstance(guardado, list):
        return tuple(guardado)
    guion = "; ".join(f"command -v {b} >/dev/null 2>&1 && echo {b}" for b in BINARIOS)
    # También la sonda lleva nombre. Pasa por `invocacion.ejecutar`, así que
    # está en el registro por hilo y es cancelable; sin `--name` su contenedor
    # sería el único de FileX que una cancelación no podría alcanzar.
    r = invocacion.ejecutar(
        ["docker", "run", "--rm", "--init", "--network", "none",
         "--name", invocacion.nombre_de_contenedor(),
         "--entrypoint", "sh", imagen, "-c", guion],
        timeout=TIMEOUT_SONDA_IMAGEN)
    if not r.ok:
        return ()
    hallados = tuple(x.strip() for x in (r.salida_txt or "").split() if x.strip())
    _cache_escribir(clave, list(hallados))
    return hallados


# ------------------------------------------------------------------ la base


class _EnContenedor:
    """Lo común a los tres submotores.

    **No hereda de `Motor` a propósito.** `motores._descubrir()` recoge toda
    subclase de `Motor` definida en el módulo, así que una base abstracta que
    heredara aparecería en `filex motores` como un motor roto.
    """

    #: Nombre del binario dentro de la imagen. Lo fija cada subclase.
    dentro = ""

    #: (origen, destino) -> (id_del_caso, coste_segundos, rasteriza)
    #: **Solo lo que K1 EJECUTÓ el 22/08/2026.** `bench/salidas-hito5/sonda.json`
    #: guarda rc, ms, bytes, sha256, el censo del punto 5 y si sobrevivió el
    #: centinela. Ninguna entrada de aquí se ha escrito a mano: las genera
    #: `bench/salidas-hito5/_tabla.py` desde el JSON.
    _MEDIDAS: dict = {}

    #: (origen, destino) -> (id_del_caso,). Aristas EJECUTADAS que NO funcionan.
    #: Una arista `nominal` sale del grafo entera. **Esto es la mitad del valor
    #: del fichero**: el 41,0 % de las aristas que los catálogos declaran no
    #: existen, y aquí se dice cuáles y con qué motor.
    _MUERTAS: dict = {}

    #: (origen, destino) que el motor declara y **nadie de este proyecto ha
    #: ejecutado**. Van `SIN_SONDEAR` y el grafo les suma +2,0 para que no
    #: adelanten jamás a una medida. La lista es DELIBERADAMENTE corta:
    #: LibreOffice declara 132 extensiones y Calibre 26 de entrada por 20 de
    #: salida, y volcarlas aquí sería exactamente el fallo que este proyecto
    #: mide en los demás — el 41,0 % de aristas nominales.
    _DECLARADAS: tuple = ()

    #: Coste de una arista sin medir: el peor medido de este submotor. Suponer
    #: que lo no medido es barato es la manera de que el grafo lo elija.
    COSTE_SIN_SONDEAR = 1.21

    # ---------------------------------------------------------------- sondeo

    def sondear(self) -> None:
        e = entorno()
        if not e["ok"] or self.dentro not in e["binarios"]:
            self.ruta = None
            self.motivo_ausencia = e["motivo"] or (
                f"la imagen '{e['imagen']}' no trae '{self.dentro}'")
            return
        self.ruta = invocacion.disponible("docker")
        self.imagen = e["imagen"]
        # El `build` de la arista incluye el ID de la imagen: es la quinta
        # dimensión, y sin ella la tabla miente en otra máquina — `svg→png` con
        # `magick` es real en Windows y NOMINAL en este mismo Debian.
        self.version = f"{e['servidor']} · {e['imagen']}@{e['imagen_id'][7:19]}"
        # Igual que los nativos: lo sondeado se superpone desde datos.
        self.aristas = sondeo.aplicar(self.nombre, self.build, self._aristas())

    # --------------------------------------------------------------- aristas

    def _aristas(self) -> list[Arista]:
        out = []
        for (o, d), (caso, coste, rast) in sorted(self._MEDIDAS.items()):
            out.append(Arista(
                origen=o, destino=d, motor=self.nombre, build=self.build,
                parametrizacion=self.dentro, estado=REAL, coste=coste,
                rasteriza=rast,
                evidencia=f"bench/salidas-hito5/sonda.json:{caso}"))
        for (o, d), (caso,) in sorted(self._MUERTAS.items()):
            out.append(Arista(
                origen=o, destino=d, motor=self.nombre, build=self.build,
                parametrizacion=self.dentro, estado=NOMINAL, coste=1.0,
                evidencia=f"bench/salidas-hito5/sonda.json:{caso}"))
        vistas = set(self._MEDIDAS) | set(self._MUERTAS)
        for o, d in self._DECLARADAS:
            if (o, d) in vistas:
                continue
            out.append(Arista(
                origen=o, destino=d, motor=self.nombre, build=self.build,
                parametrizacion=self.dentro, estado=SIN_SONDEAR,
                coste=self.COSTE_SIN_SONDEAR, evidencia=""))
        return out

    # --------------------------------------------------------------- invocar

    def _cmd(self, dentro_ent: str, dentro_sal: str, d: str, pedido: dict) -> list[str]:
        raise NotImplementedError

    def orden(self, entrada: str, salida: str, pedido: dict,
              *, timeout: float | None = None) -> list[str]:
        o = formatos.normaliza(os.path.splitext(entrada)[1])
        d = formatos.normaliza(os.path.splitext(salida)[1])
        if (o, d) in self._MUERTAS:
            # No debería llegar aquí: `nominal` cuesta infinito en el grafo.
            raise ValueError(f"'{o}→{d}' se sondeó con '{self.dentro}' y NO funciona")
        if (o, d) not in self._MEDIDAS and (o, d) not in self._DECLARADAS:
            raise ValueError(f"'{self.nombre}' no declara '{o}→{d}'")

        ent_abs = os.path.abspath(entrada)
        trabajo = os.path.dirname(os.path.abspath(salida))
        base = os.path.splitext(os.path.basename(salida))[0]
        nombre_dentro = f"{base}.{o}"
        cmd = self._cmd(f"/ent/{nombre_dentro}", f"/trabajo/{base}.{d}", d, pedido)
        # El tope de DENTRO se deriva del de quien llama y queda SIEMPRE por
        # debajo: el de dentro tiene que disparar primero, porque el de fuera
        # solo mata al cliente de Docker y deja el contenedor vivo. Suelo de 5 s
        # para que un tope absurdamente corto no produzca un `timeout 0`, que
        # mataría al arrancar.
        #
        # Va como PARÁMETRO y no como atributo de instancia a propósito: lo
        # tuve un rato guardado en `self._tope_dentro` desde `orden()` y
        # `_argv_docker` leía un valor rancio si alguien lo llamaba sin pasar
        # por `orden()` — que es justo lo que hace la prueba del tope. Un valor
        # que hay que acordarse de fijar antes no es una defensa; es la misma
        # forma de fallo que `nombre_seguro` sin llamar.
        tope = max(5, int(timeout - MARGEN_TOPE)) if timeout else None
        return self._argv_docker(ent_abs, trabajo, nombre_dentro, cmd, tope)

    def _argv_docker(self, entrada: str, trabajo: str, nombre_dentro: str,
                     cmd: list[str], tope: int | None = None) -> list[str]:
        """Ver el encabezado del módulo para el porqué de las cuatro decisiones.

        Lo que hay que mirar aquí es que **no hay shell y no hay concatenación**:
        `invocacion.ejecutar` recibe una lista, igual que para un binario nativo.
        Un contenedor no es una excusa para volver a `bash -c` — que es
        exactamente lo que le da a morphos una RCE (`analysis/00-licencias.md`).
        """
        ent = entrada.replace("\\", "/")
        trb = trabajo.replace("\\", "/")
        if "," in ent or "," in trb:
            # `--mount` separa sus opciones por comas y no las escapa. Mejor
            # negarse que montar otra cosa.
            raise ValueError("ruta con coma: el motor en contenedor no la admite")
        # a4: **la orden DECLARA qué contenedor es.** Hasta hoy había que
        # deducirlo del origen del bind mount de escritura leyendo `docker ps` +
        # `docker inspect` de toda la máquina (`bench/cancelacion-y-servicio.md`
        # §4.4 lo dejó escrito como residuo). El nombre lo acuña `invocacion`,
        # que es quien lo va a leer de vuelta, y se guarda por hilo para que
        # `parar()` —que no recibe argumentos— sepa a quién parar.
        nombre = invocacion.nombre_de_contenedor()
        _HILO.contenedor = nombre
        return [
            self.binario, "run", "--rm", "--init",
            "--name", nombre,
            "--network", "none",
            # El tope va DENTRO: matar el `docker run` no mata el contenedor.
            "--entrypoint", "timeout",
            "--mount", f"type=bind,source={ent},target=/ent/{nombre_dentro},readonly",
            "--mount", f"type=bind,source={trb},target=/trabajo",
            "-w", "/trabajo",
            # LibreOffice y Calibre quieren un HOME donde escribir su perfil. Si
            # no se les da uno, lo buscan — y lo encuentran donde no debe.
            "-e", "HOME=/tmp",
            self.imagen,
            # `-k 5`: si el motor ignora el TERM, cinco segundos después va un
            # KILL. LibreOffice colgado ignora el TERM — MEDIDO.
            # El tope de DENTRO se deriva del de quien llama, no se adivina:
            # con una constante, `convertir(..., timeout=30)` no dispararía
            # nunca el de dentro y volveríamos al contenedor huérfano.
            "-k", "5", str(TIMEOUT_DENTRO if tope is None else tope),
        ] + cmd

    # ----------------------------------------------------------------- parar

    def parar(self) -> None:
        """**El gancho que estaba muerto.** `Motor.parar()` era un `return None`
        que ninguna subclase sobrescribía (`bench/cancelacion-y-servicio.md`
        §4.4), justo en la única familia de motores que lo necesita.

        `nucleo._un_salto` lo llama cuando la invocación se agotó y **antes** de
        que el `finally` borre el desechable, y el orden es todo el asunto:
        borrar el origen de un bind mount vivo deja al contenedor en el estado
        del que `docker rm -f` responde *«did not receive an exit event»* —
        MEDIDO, `CLAUDE.md` §3.

        Para el contenedor de ESTE hilo, que es el que acaba de construir
        `_argv_docker`. Con la instancia compartida entre conversiones no se
        podía: el motor es único por proceso y el contenedor no. Y se limpia la
        marca al usarla, para que una segunda llamada no apunte a un nombre que
        ya no es de nadie.

        No es un camino caliente: solo corre cuando la invocación se agotó. En
        el camino normal el `timeout -k 5` de DENTRO ya mató al motor y `--rm`
        limpió el contenedor.
        """
        nombre = getattr(_HILO, "contenedor", "")
        _HILO.contenedor = ""
        if not nombre:
            return
        # `kill` para el que corre; `rm -f` para el que se creó y no llegó a
        # arrancar, que `docker ps` no lista. Los dos son seguros porque el
        # nombre lo acuñó FileX y el demonio garantiza que es único — MEDIDO
        # (`bench/salidas-contenedor/sonda_id.json`, S1).
        invocacion.matar_contenedor(nombre)
        invocacion.barrer_contenedor(nombre)


# ------------------------------------------------------------- LibreOffice


class LibreOfficeEnContenedor(_EnContenedor, Motor):
    """La vía ofimática. `docx/odt/rtf/txt/html → pdf`, y el salto que rasteriza."""

    dentro = "soffice"

    #: LibreOffice nombra la salida por el nombre de la ENTRADA, no por un
    #: argumento: no hay forma de decirle «escribe aquí con este nombre». Por eso
    #: **la entrada se monta con el nombre que queremos**: `/ent/salida.docx`
    #: produce `/trabajo/salida.pdf`. Sale gratis porque el montaje ya hacía
    #: falta, y evita el paso de renombrar — que sería otra escritura fuera de lo
    #: declarado y la vería el punto 5.
    _FILTRO = {"txt": "txt:Text"}

    _MEDIDAS = {
        ("docx", "html"): ('L08', 1.045, False),
        ("docx", "odt"): ('L06', 1.038, False),
        ("docx", "pdf"): ('L01', 1.065, False),
        # El salto que RASTERIZA: 38 798 B de PNG y CERO caracteres.
        ("docx", "png"): ('L09', 1.046, True),
        ("html", "pdf"): ('L04', 1.022, False),
        ("odt", "docx"): ('L07', 1.035, False),
        ("odt", "pdf"): ('L02', 1.042, False),
        ("odt", "txt"): ('L12', 1.104, False),
        ("rtf", "pdf"): ('L03', 1.025, False),
        ("txt", "pdf"): ('L05', 1.025, False),
    }
    _MUERTAS = {
        # Se CUELGA y escribe un `.tmp` que crece a ~1,5 MB/s: 471 859 200 B en
        # 240 s. Reproducido a 60 s dos veces (89,9 y 93,1 MB) y con el filtro
        # `txt` a secas, así que **no es el nombre del filtro**. `odt→txt` con
        # la MISMA orden tarda 6,2 s. El grafo llega igual: `docx→odt→txt`.
        ("docx", "txt"): ('L11',),
        # `Error: source file could not be loaded`. LibreOffice EXPORTA epub y
        # no lo IMPORTA. Es la arista que decide el hito.
        ("epub", "pdf"): ('L10',),
    }
    #: No medidas. Se declaran porque son el mismo filtro de importación que una
    #: medida, con otro filtro de exportación — no porque el catálogo las liste.
    _DECLARADAS = (("rtf", "odt"), ("rtf", "docx"), ("html", "odt"),
                   ("txt", "odt"), ("odt", "html"), ("docx", "rtf"))
    COSTE_SIN_SONDEAR = 1.21

    def __init__(self) -> None:
        super().__init__(nombre="doc_libreoffice", binario="docker")
        self.imagen = ""
        self.motivo_ausencia = ""

    def _cmd(self, ent: str, sal: str, d: str, pedido: dict) -> list[str]:
        return ["soffice", "--headless", "--norestore",
                "--convert-to", self._FILTRO.get(d, d), "--outdir", "/trabajo", ent]


# ------------------------------------------------------------------ Pandoc


class PandocEnContenedor(_EnContenedor, Motor):
    """Markup. El más barato de los tres: 12 de sus 15 aristas bajan de 2,5 s."""

    dentro = "pandoc"

    _MEDIDAS = {
        ("docx", "epub"): ('P14', 1.009, False),
        ("docx", "html"): ('P05', 1.01, False),
        ("docx", "md"): ('P04', 1.01, False),
        ("docx", "pdf"): ('P12', 1.072, False),
        ("docx", "rtf"): ('P06', 1.009, False),
        # Pandoc SÍ hace `epub→html`; Calibre NO (ver `CalibreEnContenedor`).
        ("epub", "html"): ('P10', 1.015, False),
        ("epub", "md"): ('P09', 1.096, False),
        ("html", "docx"): ('P07', 1.023, False),
        ("html", "md"): ('P08', 1.009, False),
        ("md", "docx"): ('P01', 1.033, False),
        ("md", "epub"): ('P03', 1.011, False),
        ("md", "html"): ('P02', 1.014, False),
        ("md", "odt"): ('P13', 1.025, False),
        ("md", "pdf"): ('P11', 1.124, False),
        ("md", "txt"): ('P15', 1.01, False),
    }
    _MUERTAS = {}
    _DECLARADAS = (("html", "epub"), ("html", "odt"), ("html", "rtf"),
                   ("docx", "odt"), ("epub", "docx"), ("epub", "txt"),
                   ("rtf", "md"), ("rtf", "html"), ("md", "rtf"))
    COSTE_SIN_SONDEAR = 1.21

    def __init__(self) -> None:
        super().__init__(nombre="doc_pandoc", binario="docker")
        self.imagen = ""
        self.motivo_ausencia = ""

    def _cmd(self, ent: str, sal: str, d: str, pedido: dict) -> list[str]:
        cmd = ["pandoc", ent]
        if d in ("html", "rtf", "tex"):
            # Sin `-s`, pandoc emite un FRAGMENTO sin `<html>`. Pasaría el punto
            # 1 del contrato por los pelos y no sería un documento.
            cmd.append("-s")
        if d == "pdf":
            cmd.append("--pdf-engine=xelatex")
        if d == "txt":
            cmd += ["-t", "plain"]
        return cmd + ["-o", sal]


# ----------------------------------------------------------------- Calibre


class CalibreEnContenedor(_EnContenedor, Motor):
    """Ebooks. Y `epub→pdf`, que es la arista que el hito 1 no podía demostrar."""

    dentro = "ebook-convert"

    _MEDIDAS = {
        ("docx", "epub"): ('C07', 1.075, False),
        ("docx", "pdf"): ('C09', 1.102, False),
        ("epub", "azw3"): ('C04', 1.05, False),
        ("epub", "docx"): ('C02', 1.074, False),
        ("epub", "mobi"): ('C03', 1.078, False),
        # LA arista. 26 817 B, los mismos que midió otro agente el 21/08 con
        # `docker exec` en vez de `docker run`.
        ("epub", "pdf"): ('C01', 1.206, False),
        ("epub", "txt"): ('C05', 1.049, False),
        ("html", "epub"): ('C08', 1.053, False),
    }
    _MUERTAS = {
        # `ValueError: No plugin to handle output format: html`. Calibre escribe
        # `.htmlz`, no `.html`. Y Pandoc SÍ hace `epub→html` en 1,5 s: el grafo
        # tiene que poder elegir, que es de lo que va el hito 1.
        ("epub", "html"): ('C06',),
    }
    _DECLARADAS = (("mobi", "epub"), ("azw3", "epub"), ("mobi", "pdf"),
                   ("azw3", "pdf"), ("txt", "epub"), ("md", "epub"),
                   ("epub", "epub"), ("mobi", "azw3"))
    COSTE_SIN_SONDEAR = 1.21

    def __init__(self) -> None:
        super().__init__(nombre="doc_calibre", binario="docker")
        self.imagen = ""
        self.motivo_ausencia = ""

    def _cmd(self, ent: str, sal: str, d: str, pedido: dict) -> list[str]:
        return ["ebook-convert", ent, sal]
