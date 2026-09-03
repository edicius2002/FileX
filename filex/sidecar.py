"""El sidecar de IA: registro de modelos residentes con **LRU por VRAM y TTL**.

Hito 6. Este modulo es el gestor; los modelos viven en **procesos trabajadores**,
uno por `(motor, dispositivo)`, cada uno bajo el interprete de su propio entorno
virtual. `filex` no tiene dependencias —es una decision escrita en
`pyproject.toml`— asi que aqui no se importa ni `torch` ni `rapidocr`: se lanzan.

──────────────────────────────────────────────────────────────────────────────
1. POR QUE EL CRITERIO DE RECICLADO ES DE VRAM Y NO DE PAGINAS
──────────────────────────────────────────────────────────────────────────────
El asignador de estos motores **no devuelve la memoria** (trampa 8 de
`CLAUDE.md`), y lo que la hace crecer **no es el numero de paginas ni los
megapixeles acumulados**: es el **documento MAYOR** que ese proceso haya visto y
el **CAMINO** hasta el (trampa 67, `bench/ocr-produccion-sidecar.md` §3).

* 20 paginas de 1,25 Mpx —24,97 Mpx acumulados— mueven **39-42 MiB**;
* **una** de 4,35 Mpx mueve **3 209** en EasyOCR y no la devuelve;
* llegar al mismo folio de 8,88 Mpx **en escalera** cuesta **×2,25** mas VRAM
  que ir directo (9 646 frente a 4 296 MiB).

De ahi las tres consecuencias que este modulo implementa:

* la admision se calcula **antes** de cada pagina, con `ordenada + pendiente ×
  Mpx` acotado por el `tope` propio del motor (`Motor.coste_previsto`);
* un lote se ordena **DESCENDENTE**, el folio grande primero
  (`orden_descendente`), porque el ascendente es el peor de los ordenes;
* reciclar es **matar y relanzar el proceso**: esperar no devuelve un solo MiB.

──────────────────────────────────────────────────────────────────────────────
2. LA DECISION SE TOMA POR VRAM LIBRE **TOTAL**
──────────────────────────────────────────────────────────────────────────────
Por PID no es observable en esta maquina: en WDDM
``nvidia-smi --query-compute-apps=used_memory`` devuelve ``[N/A]`` en los 30
procesos (trampa 31). El total si sirve, porque los dos regimenes estan a un
orden de magnitud. Se lee con `filex.gpu.vram_libre_mib()`, que devuelve `None`
—no cero— cuando no hay tarjeta: **confundir «no hay GPU» con «la GPU esta
llena» convierte una maquina sin tarjeta en una maquina bloqueada.**

──────────────────────────────────────────────────────────────────────────────
3. LA EXCEPCION DECLARADA A `stdin=DEVNULL`
──────────────────────────────────────────────────────────────────────────────
La regla de invocacion del proyecto es *«proceso separado, sin shell, argumentos
en array y `stdin=DEVNULL`»*, y su motivo es que **un motor que espera entrada
cuelga la conversion**. El trabajador de este modulo **no es un motor de
terceros: es este mismo fichero**, y su `stdin` es el canal del protocolo. La
excepcion es la misma figura que la de `inspect` frente a R8/R18: se declara, se
razona y no se extiende. Todo lo demas se cumple —sin shell, argv en array,
`stderr` capturado y **nunca devuelto crudo**, y **timeout en cada peticion**.

──────────────────────────────────────────────────────────────────────────────
4. DOS VARIABLES QUE NO SE PUEDEN DEJAR IMPLICITAS
──────────────────────────────────────────────────────────────────────────────
* **El dispositivo** (trampa 11): CPU y GPU **no** dan la misma salida — 5 de 21
  celdas difieren. Va en la clave del registro y en cada resultado.
* **La via de entrada** (trampa 30): `ruta` y `ndarray` valen hasta 12,58 puntos
  de CER, EasyOCR **nunca coincide consigo mismo** entre las dos y un PNG de
  paleta llega a RapidOCR como matriz 2-D de indices. Este sidecar entrega
  **siempre la ruta**, y lo declara en cada resultado: la via es una variable del
  adaptador, no un detalle de implementacion.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

# `filex.gpu` solo se importa cuando hace falta: este modulo tiene que poder
# usarse (y probarse) en una maquina sin tarjeta, y como **trabajador** bajo el
# interprete de un venv donde el paquete `filex` no esta instalado.
_MODO_TRABAJADOR = "--trabajador" in sys.argv


# ==========================================================================
# El modelo de coste, con su procedencia dentro
# ==========================================================================
class Motor:
    """Un motor de OCR y **su recta de VRAM**, con la fuente de cada numero.

    `coste_previsto(mpx) = min(ordenada + pendiente × mpx, tope)`

    Los valores salen de `bench/ocr-produccion-sidecar.md` §5.1 (cinco puntos por
    motor, 0,55 a 8,88 Mpx, un solo documento base reescalado).

    **La recta de RapidOCR NO se ajusta sobre los cinco puntos** (N27,
    `bench/vram-rapidocr.md`): el motor recorta a 2 000 px (`Global.max_side_len`)
    y a partir de ahi el quinto punto y una parte del cuarto ya estan en la
    meseta, no en el tramo lineal — meterlos en el mismo ajuste que los tres
    puntos sin recortar sesga la recta hacia abajo justo en el tramo de en medio
    (subestimaba 339 MiB a 4,352 Mpx con el ajuste viejo de 5 puntos). La recta
    de aqui sale de los **tres** puntos confirmados sin recorte (0,55/1,25/2,22
    Mpx, r²=0,992) mas un redondeo al alza minimo para que ninguno de los tres
    quede por debajo — no para que cuadre un cuarto o quinto punto, que seria la
    misma trampa con otro nombre. El `tope` es el maximo de tres medidas
    independientes del mismo `sha256` de pixeles (1 456 / 1 526 / 1 533 MiB):
    usar la mas baja de las tres NO seria una cota superior.
    """

    __slots__ = ("nombre", "ordenada_mib", "pendiente_mib_mpx", "tope_mib",
                 "fuente", "r2", "recicla")

    def __init__(self, nombre: str, ordenada_mib: int, pendiente_mib_mpx: int,
                 tope_mib: int | None, fuente: str, r2: float | None = None):
        self.nombre = nombre
        self.ordenada_mib = ordenada_mib
        self.pendiente_mib_mpx = pendiente_mib_mpx
        self.tope_mib = tope_mib
        self.fuente = fuente
        self.r2 = r2
        #: ¿Necesita politica de reciclado? Un motor **con tope propio** no la
        #: necesita nunca por memoria; uno sin tope, si, y entra en el sidecar
        #: **con** ella o no entra.
        self.recicla = tope_mib is None

    def coste_previsto(self, mpx: float) -> int:
        """MiB que este motor va a retener con una pagina de `mpx` megapixeles."""
        if mpx < 0:
            raise ValueError("los megapixeles no pueden ser negativos")
        c = self.ordenada_mib + self.pendiente_mib_mpx * mpx
        if self.tope_mib is not None:
            c = min(c, float(self.tope_mib))
        return int(round(c))

    def mpx_admisibles(self, libre_mib: int, margen_mib: int) -> float:
        """El **tamaño maximo de entrada** que cabe con `libre_mib` libres.

        Es la mitad del criterio que la trampa 68 echaba en falta: *«un
        presupuesto de recurso lleva dentro el tamaño maximo de entrada
        admitido, o no es un presupuesto»*. `inf` cuando el tope propio del motor
        ya cabe: entonces no hay tamaño que lo rompa.
        """
        disponible = libre_mib - margen_mib
        if self.tope_mib is not None and self.tope_mib <= disponible:
            return float("inf")
        if self.pendiente_mib_mpx <= 0:
            return float("inf") if self.ordenada_mib <= disponible else 0.0
        return max(0.0, (disponible - self.ordenada_mib) / self.pendiente_mib_mpx)

    def __repr__(self) -> str:                                  # pragma: no cover
        return f"<Motor {self.nombre} {self.ordenada_mib}+{self.pendiente_mib_mpx}/Mpx>"


_F = "bench/ocr-produccion-sidecar.md §5.1 (MEDIDO, 5 puntos, escaneado_d4 reescalado)"
#: N27: la recta de RapidOCR ya NO sale de los 5 puntos de `_F` (ver el
#: docstring de `Motor`) — sale de los 3 sin recortar de ese mismo informe, más
#: el tope corregido de `bench/vram-rapidocr.md`. Se mantiene la subcadena
#: "ocr-produccion-sidecar" porque los TRES puntos siguen siendo de ahí.
_F_RAPIDOCR = ("bench/ocr-produccion-sidecar.md §3.3 (3 puntos sin recortar, "
              "0,55-2,22 Mpx) + bench/vram-rapidocr.md (N27: la recta corregida "
              "y el tope, MEDIDO)")

#: Las tres rectas medidas. **Un motor nuevo no hereda ninguna**: entra con la
#: suya medida o no entra — es la misma regla que la del `k` por motor, *«una
#: constante global hace que cada motor nuevo herede en silencio los ppp que le
#: convenian a otro»*.
MOTORES: dict[str, Motor] = {
    "rapidocr": Motor("rapidocr", 428, 235, 1533, _F_RAPIDOCR, r2=0.9853),
    "paddleocr": Motor("paddleocr", 202, 719, None, _F, r2=0.9995),
    "easyocr": Motor("easyocr", 641, 1080, None, _F, r2=0.9571),
}

#: Margen de seguridad sobre el coste previsto, en MiB. El mismo que §5.1.
MARGEN_MIB = int(os.environ.get("FILEX_SIDECAR_MARGEN_MIB", "500"))

#: Segundos de inactividad tras los que un trabajador se descarga. «Los modelos
#: se descargan por inactividad» es la mitad del criterio del hito que **no**
#: cambia en la reescritura.
TTL_S = float(os.environ.get("FILEX_SIDECAR_TTL_S", "300"))

#: Tope de una peticion al trabajador. Timeouts explicitos en todo: estos
#: motores dejan huerfanos vivos 13 minutos.
TIMEOUT_PETICION_S = float(os.environ.get("FILEX_SIDECAR_TIMEOUT_S", "600"))

#: Tope del arranque de un trabajador. Medido: 4,0-7,0 s de carga en frio, con
#: el `import` dominando (3,6-4,4 s). 120 s es holgado a proposito.
TIMEOUT_ARRANQUE_S = float(os.environ.get("FILEX_SIDECAR_ARRANQUE_S", "120"))

#: Cuantas lineas ajenas al protocolo se toleran en `stdout` antes de rendirse.
#: El tope de tiempo manda igualmente; esto solo acota el bucle.
_LINEAS_INTRUSAS_MAX = 200


# ==========================================================================
# El presupuesto: un perfil COMPLETO, con el tamaño de entrada dentro
# ==========================================================================
class Perfil:
    """El presupuesto de VRAM de una configuracion **entera**, declarada.

    La trampa 68 dice por que esto no puede ser un numero suelto: *«un criterio
    de aceptacion que no nombra el tamaño de la entrada no se puede verificar»*.
    Un `Perfil` obliga a nombrar las cinco cosas: **escritorio**, **modelo de
    audio**, **motor de OCR**, **NVENC** y **el documento mayor admitido**.
    """

    __slots__ = ("nombre", "escritorio_mib", "audio_mib", "motor", "mpx_max",
                 "nvenc_mib", "techo_mib", "medido_mib")

    def __init__(self, nombre: str, escritorio_mib: int, audio_mib: int,
                 motor: Motor, mpx_max: float, nvenc_mib: int = 0,
                 techo_mib: int = 8909, medido_mib: int | None = None):
        self.nombre = nombre
        self.escritorio_mib = escritorio_mib
        self.audio_mib = audio_mib
        self.motor = motor
        self.mpx_max = mpx_max
        self.nvenc_mib = nvenc_mib
        #: 8 909 MiB = los «~8,7 GB» del criterio original en MiB (8,7 × 1024).
        self.techo_mib = techo_mib
        #: N26 (bench/presupuesto-vram.md): la suma SIEMPRE sobreestima (medido
        #: en los 3 perfiles de la Clausula C), pero por cuanto es DEL PERFIL,
        #: no del sistema -- 1,2 % con `distil`, 7,2 % con `large-v3`. Cuando un
        #: perfil YA tiene una medida conjunta (los tres componentes vivos a la
        #: vez), esa medida es mas ajustada que la suma y no introduce riesgo:
        #: la suma nunca ha infravalorado en ningun perfil medido. `medido_mib`
        #: es el "coste propio medido" de SV7 -- audio+ocr+nvenc vivos a la vez,
        #: SIN el escritorio, la misma convencion que ya usa `suma_mib` (el
        #: escritorio se suma una vez, en `total_mib`, con los dos caminos). Si
        #: no se da, `total_mib` sigue sumando componente a componente
        #: (comportamiento igual al de antes de esta ronda).
        self.medido_mib = medido_mib

    @property
    def ocr_mib(self) -> int:
        return self.motor.coste_previsto(self.mpx_max)

    @property
    def suma_mib(self) -> int:
        """La suma de los componentes medidos por separado. Cota superior
        conservadora SIEMPRE (sesgo del signo verificado en 3 perfiles), pero
        de magnitud propia del perfil, no del sistema -- no se usa para
        derivar un margen unico."""
        return (self.escritorio_mib + self.audio_mib + self.ocr_mib
                + self.nvenc_mib)

    @property
    def total_mib(self) -> int:
        if self.medido_mib is not None:
            return self.escritorio_mib + self.medido_mib
        return self.suma_mib

    def evaluar(self, tarjeta_mib: int = 12288) -> dict:
        """El veredicto, con los sumandos a la vista y **sin ocultar la suma**.

        `aditividad_supuesta` no es decoracion: mientras el total sea una suma de
        medidas tomadas por separado, es una **hipotesis**, y quien lea el
        veredicto tiene que verlo. `bench/hito6-sidecar.md` §3 la mide.
        Con `medido_mib` puesto, el total es una MEDIDA (Clausula C, los
        componentes vivos a la vez), no una suma, y el campo lo declara.
        """
        t = self.total_mib
        return {"perfil": self.nombre, "escritorio_MiB": self.escritorio_mib,
                "audio_MiB": self.audio_mib, "ocr_MiB": self.ocr_mib,
                "nvenc_MiB": self.nvenc_mib, "mpx_max": self.mpx_max,
                "motor": self.motor.nombre, "total_MiB": t,
                "suma_MiB": self.suma_mib,
                "techo_MiB": self.techo_mib, "tarjeta_MiB": tarjeta_mib,
                "cumple_techo": t <= self.techo_mib,
                "cabe_en_tarjeta": t <= tarjeta_mib,
                "aditividad_supuesta": self.medido_mib is None}


# ==========================================================================
# El orden del lote
# ==========================================================================
def orden_descendente(paginas):
    """Ordena `[(clave, mpx), ...]` de MAYOR a menor.

    **No es una preferencia: es una refutacion medida.** `k-por-motor.md` §6.3
    proponia *«procesa en orden ascendente de tamaño»* y resulto ser el **peor**
    de los ordenes: llegar al folio de 8,88 Mpx en escalera cuesta **+5 350 MiB**
    en EasyOCR frente a ir directo (×2,25), con el signo replicado en una segunda
    tanda independiente. Con el mayor primero, el resto cabe en lo ya reservado.

    **Y el arrepentimiento, medido, porque no gana siempre**
    (`bench/hito6-sidecar.md` §6, n=5, signo conservado 5 de 5): sobre RapidOCR
    —que tiene tope propio porque recorta a 2 000 px— el descendente **pierde
    77 MiB** frente al ascendente (1 532 contra 1 455). Es decir: **el orden es
    una variable del MOTOR, como el `k`**. Se fija uno solo, por **minimo
    arrepentimiento**, y se publica el arrepentimiento: se pierden **77 MiB** en
    el motor con tope y se ganan **5 350** en el que no lo tiene.
    """
    return sorted(paginas, key=lambda p: -float(p[1]))


# ==========================================================================
# La geometria, leida de la cabecera EN PROCESO
# ==========================================================================
def megapixeles(ruta: str) -> float:
    """Mpx de un PNG o un JPEG, leyendo **la cabecera**, no el fichero.

    *«Verificar leyendo cabeceras en proceso, no con `ffprobe`»*: aqui la
    alternativa costaria un lanzamiento de proceso por pagina para saber si la
    pagina cabe. Se leen los dos formatos que produce el rasterizado de este
    proyecto (Ghostscript escribe PNG; `magick` puede escribir JPEG).
    """
    with open(ruta, "rb") as f:
        cab = f.read(32)
        if cab[:8] == b"\x89PNG\r\n\x1a\n" and cab[12:16] == b"IHDR":
            an = int.from_bytes(cab[16:20], "big")
            al = int.from_bytes(cab[20:24], "big")
            return an * al / 1e6
        if cab[:2] == b"\xff\xd8":
            f.seek(2)
            while True:
                b = f.read(2)
                if len(b) < 2 or b[0] != 0xFF:
                    break
                marca = b[1]
                if marca in (0xD8, 0xD9) or 0xD0 <= marca <= 0xD7:
                    continue
                largo = int.from_bytes(f.read(2), "big")
                if 0xC0 <= marca <= 0xCF and marca not in (0xC4, 0xC8, 0xCC):
                    c = f.read(largo - 2)
                    al = int.from_bytes(c[1:3], "big")
                    an = int.from_bytes(c[3:5], "big")
                    return an * al / 1e6
                f.seek(largo - 2, os.SEEK_CUR)
    raise ValueError(f"no se pudo leer la geometria de {os.path.basename(ruta)}")


# ==========================================================================
# La decision de admision
# ==========================================================================
class Decision:
    """`admitir` / `reciclar` / `rechazar`, **con los numeros que la sostienen**."""

    __slots__ = ("veredicto", "motivo", "coste_previsto_mib", "libre_mib",
                 "margen_mib", "mpx", "motor", "mpx_admisibles")

    def __init__(self, veredicto, motivo, coste_previsto_mib, libre_mib,
                 margen_mib, mpx, motor, mpx_admisibles):
        self.veredicto = veredicto
        self.motivo = motivo
        self.coste_previsto_mib = coste_previsto_mib
        self.libre_mib = libre_mib
        self.margen_mib = margen_mib
        self.mpx = mpx
        self.motor = motor
        self.mpx_admisibles = mpx_admisibles

    @property
    def ok(self) -> bool:
        return self.veredicto == "admitir"

    def como_dict(self) -> dict:
        return {"veredicto": self.veredicto, "motivo": self.motivo,
                "coste_previsto_MiB": self.coste_previsto_mib,
                "libre_MiB": self.libre_mib, "margen_MiB": self.margen_mib,
                "mpx": round(self.mpx, 3), "motor": self.motor,
                "mpx_admisibles": (None if self.mpx_admisibles == float("inf")
                                   else round(self.mpx_admisibles, 3))}

    def __repr__(self) -> str:                                  # pragma: no cover
        return f"<Decision {self.veredicto}: {self.motivo}>"


def decidir(motor: Motor, mpx: float, libre_mib: int | None, *,
            residente_mib: int = 0, margen_mib: int = MARGEN_MIB) -> Decision:
    """La regla de §5.1, evaluada **antes** de procesar la pagina.

    `residente_mib` es lo que este proceso ya tiene reservado y **no va a
    devolver**: reciclar solo sirve si recupera algo, y esa es justo la
    diferencia entre `reciclar` y `rechazar`. *«Si aun asi no cabe, el documento
    no cabe en esta maquina. Reciclar dos veces seguidas no ayuda.»*

    Con `libre_mib is None` —sin tarjeta o `nvidia-smi` mudo— se **admite**: en
    CPU no hay VRAM que presupuestar, y bloquear ahi seria convertir la falta de
    instrumento en una averia.
    """
    coste = motor.coste_previsto(mpx)
    if libre_mib is None:
        return Decision("admitir", "no hay lectura de VRAM: no se presupuesta",
                        coste, None, margen_mib, mpx, motor.nombre, float("inf"))
    admisibles = motor.mpx_admisibles(libre_mib + residente_mib, margen_mib)
    if coste + margen_mib <= libre_mib:
        return Decision("admitir",
                        f"{coste} + {margen_mib} de margen <= {libre_mib} libres",
                        coste, libre_mib, margen_mib, mpx, motor.nombre, admisibles)
    if coste + margen_mib <= libre_mib + residente_mib:
        return Decision("reciclar",
                        f"{coste} + {margen_mib} > {libre_mib} libres, pero cabe "
                        f"recuperando los {residente_mib} MiB retenidos",
                        coste, libre_mib, margen_mib, mpx, motor.nombre, admisibles)
    return Decision("rechazar",
                    f"{coste} + {margen_mib} > {libre_mib + residente_mib} MiB "
                    f"aun reciclando: esta pagina no cabe en esta maquina",
                    coste, libre_mib, margen_mib, mpx, motor.nombre, admisibles)


# ==========================================================================
# El trabajador: un proceso, un motor, un dispositivo
# ==========================================================================
class ErrorTrabajador(RuntimeError):
    """Fallo del proceso trabajador. **Nunca lleva el `stderr` crudo dentro.**"""


class Trabajador:
    """El proceso que tiene el modelo cargado.

    Se habla con el por lineas de JSON. Se recicla **matandolo y relanzandolo**,
    porque el asignador no devuelve la memoria de ninguna otra forma: *«reiniciar
    el proceso lo arregla; esperar, no»*.
    """

    def __init__(self, motor: str, dispositivo: str, python: str | None = None,
                 guion: str | None = None, cwd: str | None = None):
        self.motor = motor
        self.dispositivo = dispositivo
        self.python = python or sys.executable
        self.guion = guion or os.path.abspath(__file__)
        #: Directorio de trabajo DESECHABLE (R18/R21). Hay motores que escriben
        #: fuera del destino, en el `cwd` del proceso —`ffmpeg -i x out.mpd` deja
        #: los segmentos DASH ahi—, y un trabajador de vida larga los acumularia
        #: donde le tocara arrancar. `censo()` lo lista para saber si ocurre.
        self.cwd = cwd
        self._cwd_propio = False
        self.proc: subprocess.Popen | None = None
        self.ultimo_uso = time.monotonic()
        self.paginas = 0
        self.mpx_max_visto = 0.0
        self.reciclados = 0
        self.arrancado_en: float | None = None
        #: Lineas de `stdout` que no eran del protocolo. Se cuentan porque un
        #: motor que empieza a imprimir es una regresion silenciosa.
        self.intrusas = 0
        self.meta: dict = {}
        self._lock = threading.Lock()

    # -- ciclo de vida ----------------------------------------------------
    def vivo(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def censo(self) -> list[str]:
        """Lo que hay en el desechable **ahora**. Se llama antes y despues: el
        punto 5 del contrato no se puede verificar a posteriori."""
        if not self.cwd or not os.path.isdir(self.cwd):
            return []
        return sorted(os.listdir(self.cwd))

    def arrancar(self) -> None:
        if self.vivo():
            return
        if self.cwd is None:
            import tempfile
            self.cwd = tempfile.mkdtemp(prefix=f"filex-sidecar-{self.motor}-")
            self._cwd_propio = True
        self.censo_inicial = self.censo()
        argv = [self.python, self.guion, "--trabajador", self.motor,
                self.dispositivo]
        # Sin shell y con el argv en array. `stdin` es el canal del protocolo:
        # es la excepcion declarada en la cabecera de este modulo.
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.cwd)
        self._drenar_stderr()
        t0 = time.monotonic()
        listo = self._leer_linea(TIMEOUT_ARRANQUE_S)
        if not listo or listo.get("evento") != "listo":
            self.cerrar()
            raise ErrorTrabajador(
                f"el trabajador de {self.motor} no llego a estar listo")
        self.arrancado_en = time.monotonic() - t0
        self.ultimo_uso = time.monotonic()
        self.meta = listo

    def _drenar_stderr(self) -> None:
        """Un hilo que VACIA el `stderr` del trabajador y guarda las ultimas
        lineas en un anillo.

        **No es higiene: es una tuberia de 64 KiB que, llena, BLOQUEA al
        escritor.** RapidOCR emite una linea de `INFO` por fichero de pesos y
        PaddleOCR imprime por su cuenta; un trabajador de vida larga con el
        `stderr` en `PIPE` y sin nadie leyendo se cuelga a las pocas decenas de
        paginas, y se cuelga **escribiendo un log**, que es el ultimo sitio
        donde nadie mira. El anillo es para diagnostico local y **no sale de
        aqui**: nunca se devuelve `stderr` crudo a quien llama.
        """
        import collections
        self.stderr_cola = collections.deque(maxlen=50)
        p = self.proc

        def bucle():
            try:
                for linea in iter(p.stderr.readline, b""):
                    self.stderr_cola.append(
                        linea.decode("utf-8", "replace").rstrip())
            except (OSError, ValueError):
                pass

        h = threading.Thread(target=bucle, daemon=True)
        h.start()
        self._hilo_stderr = h

    def diagnostico(self) -> list[str]:
        """Las ultimas lineas del `stderr`, **para el humano que depura**.

        Existe como metodo aparte y no como campo del resultado a proposito: el
        error de un motor puede dirigir la siguiente accion de un agente, asi
        que sale por peticion explicita de una persona, no por el camino normal.
        """
        return list(getattr(self, "stderr_cola", []))

    def sobrantes(self) -> list[str]:
        """Lo que el trabajador dejo en el desechable y no estaba al arrancar."""
        antes = set(getattr(self, "censo_inicial", []))
        return [n for n in self.censo() if n not in antes]

    def cerrar(self) -> None:
        p, self.proc = self.proc, None
        if p is None:
            self._borrar_desechable()
            return
        try:
            if p.poll() is None:
                p.stdin.close()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=10)
        except OSError:
            pass
        finally:
            for canal in (p.stdout, p.stderr):
                try:
                    if canal:
                        canal.close()
                except OSError:
                    pass
            self._borrar_desechable()

    def _borrar_desechable(self) -> None:
        """Borra el desechable **entero**, y solo si lo creamos nosotros."""
        if not (self._cwd_propio and self.cwd):
            return
        import shutil
        shutil.rmtree(self.cwd, ignore_errors=True)
        self.cwd = None
        self._cwd_propio = False

    def reciclar(self) -> None:
        """Matar y relanzar. Cuesta **4,08 s (RapidOCR), 6,74 (EasyOCR), 7,05
        (PaddleOCR)** medidos, y el `import` es de 3,6-4,4 s de esos."""
        self.cerrar()
        self.reciclados += 1
        self.paginas = 0
        self.mpx_max_visto = 0.0
        self.arrancar()

    # -- protocolo --------------------------------------------------------
    def _leer_linea(self, timeout: float) -> dict | None:
        """Lee una linea de JSON del trabajador **con tope**.

        El tope se implementa con un hilo porque en Windows no hay `select` sobre
        una tuberia. Un `readline` sin tope es exactamente el modo de fallo que
        el proyecto ya pago: un proceso colgado que nadie mata.
        """
        salida: list = []

        def leer():
            try:
                salida.append(self.proc.stdout.readline())
            except (OSError, ValueError):
                salida.append(b"")

        limite = time.monotonic() + timeout
        # Se saltan las lineas que NO son del protocolo. No es indulgencia: hay
        # motores que imprimen por su cuenta en `stdout` —PaddleOCR lo hace— y
        # una sola linea suya cerraria el trabajador con «murio sin responder»,
        # que es un diagnostico falso. El tope sigue siendo global, asi que un
        # motor que solo escribiera basura no puede hacer que esto no termine.
        for _ in range(_LINEAS_INTRUSAS_MAX):
            salida.clear()
            h = threading.Thread(target=leer, daemon=True)
            h.start()
            h.join(max(0.0, limite - time.monotonic()))
            if h.is_alive():
                self.matar()
                raise ErrorTrabajador(
                    f"el trabajador de {self.motor} agoto su tope de {timeout} s")
            linea = salida[0] if salida else b""
            if not linea:
                return None
            try:
                return json.loads(linea.decode("utf-8", "replace"))
            except ValueError:
                self.intrusas += 1
                if time.monotonic() >= limite:
                    return None
        return None

    def matar(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=10)
            except OSError:                                     # pragma: no cover
                pass
        self.proc = None

    def pedir(self, orden: dict, timeout: float = TIMEOUT_PETICION_S) -> dict:
        with self._lock:
            if not self.vivo():
                raise ErrorTrabajador(f"el trabajador de {self.motor} no esta vivo")
            try:
                self.proc.stdin.write((json.dumps(orden) + "\n").encode("utf-8"))
                self.proc.stdin.flush()
            except OSError as e:
                raise ErrorTrabajador(
                    f"no se pudo hablar con el trabajador de {self.motor} "
                    f"({type(e).__name__})") from None
            r = self._leer_linea(timeout)
            if r is None:
                self.matar()
                raise ErrorTrabajador(
                    f"el trabajador de {self.motor} murio sin responder")
            self.ultimo_uso = time.monotonic()
            return r


# ==========================================================================
# El registro: LRU por VRAM + TTL
# ==========================================================================
class Registro:
    """Los modelos residentes, con **descarga por inactividad y por presion**.

    Dos politicas, y no son la misma:

    * **TTL** — un trabajador que lleva `ttl_s` sin usarse se cierra. Es «los
      modelos se descargan por inactividad», la mitad del criterio del hito 6 que
      no cambia.
    * **LRU por VRAM** — cuando la pagina siguiente no cabe, se cierran
      trabajadores **por orden de uso mas antiguo** hasta que quepa. Se desaloja
      al que lleva mas tiempo sin usarse, no al que mas ocupa: el que mas ocupa
      suele ser el que se esta usando.

    `vram_libre` y `reloj` son inyectables **para poder probar las dos politicas
    sin tarjeta**. Que una regla de recurso solo se pueda ejercitar con el
    hardware delante es como no tener prueba.
    """

    def __init__(self, *, ttl_s: float = TTL_S, margen_mib: int = MARGEN_MIB,
                 vram_libre=None, reloj=time.monotonic, python: str | None = None,
                 fabrica=None):
        self.ttl_s = ttl_s
        self.margen_mib = margen_mib
        self.reloj = reloj
        self.python = python
        self._fabrica = fabrica or (lambda m, d: Trabajador(m, d, python=self.python))
        self._vram_libre = vram_libre
        self.residentes: dict[tuple[str, str], Trabajador] = {}
        self.sucesos: list[dict] = []
        self._lock = threading.RLock()

    # -- la tarjeta -------------------------------------------------------
    def vram_libre(self) -> int | None:
        if self._vram_libre is not None:
            return self._vram_libre()
        from filex import gpu                     # import perezoso: puede no haber GPU
        return gpu.vram_libre_mib()

    def _anotar(self, **kw) -> dict:
        kw["t"] = round(self.reloj(), 3)
        self.sucesos.append(kw)
        return kw

    # -- TTL --------------------------------------------------------------
    def caducar(self) -> list[tuple[str, str]]:
        """Cierra los trabajadores inactivos. Devuelve los que se llevo."""
        fuera = []
        with self._lock:
            ahora = self.reloj()
            for clave, t in list(self.residentes.items()):
                if ahora - t.ultimo_uso >= self.ttl_s:
                    t.cerrar()
                    del self.residentes[clave]
                    fuera.append(clave)
                    self._anotar(suceso="ttl", motor=clave[0], dispositivo=clave[1],
                                 inactivo_s=round(ahora - t.ultimo_uso, 1))
        return fuera

    # -- LRU --------------------------------------------------------------
    def desalojar_lru(self, salvar: tuple[str, str] | None = None) -> tuple | None:
        """Cierra el residente **menos recientemente usado**. `None` si no queda."""
        with self._lock:
            candidatos = [(t.ultimo_uso, c) for c, t in self.residentes.items()
                          if c != salvar]
            if not candidatos:
                return None
            _, clave = min(candidatos)
            self.residentes[clave].cerrar()
            del self.residentes[clave]
            self._anotar(suceso="lru", motor=clave[0], dispositivo=clave[1])
            return clave

    # -- admision ---------------------------------------------------------
    def admitir(self, motor: str, mpx: float, dispositivo: str = "cuda") -> Decision:
        """La decision, **antes** de procesar. No toca ningun modelo."""
        m = MOTORES.get(motor)
        if m is None:
            raise KeyError(
                f"motor sin recta de VRAM medida: {motor}. Un motor entra en el "
                f"sidecar con su recta medida o no entra")
        if dispositivo != "cuda":
            # En CPU no hay VRAM que presupuestar, y el dispositivo **cambia la
            # salida** (trampa 11): por eso viaja en la clave y en la decision.
            return Decision("admitir", "dispositivo cpu: no hay VRAM que presupuestar",
                            m.coste_previsto(mpx), None, self.margen_mib, mpx,
                            motor, float("inf"))
        t = self.residentes.get((motor, dispositivo))
        residente = 0
        if t is not None and t.mpx_max_visto > 0:
            # Lo que ese proceso ya retiene por el mayor documento que ha visto:
            # es lo unico que reciclar puede recuperar.
            residente = m.coste_previsto(t.mpx_max_visto)
        return decidir(m, mpx, self.vram_libre(), residente_mib=residente,
                       margen_mib=self.margen_mib)

    # -- el camino completo -----------------------------------------------
    def obtener(self, motor: str, dispositivo: str = "cuda") -> Trabajador:
        with self._lock:
            self.caducar()
            clave = (motor, dispositivo)
            t = self.residentes.get(clave)
            if t is not None and t.vivo():
                return t
            t = self._fabrica(motor, dispositivo)
            t.arrancar()
            self.residentes[clave] = t
            self._anotar(suceso="arranque", motor=motor, dispositivo=dispositivo,
                         s=round(t.arrancado_en or 0.0, 3))
            return t

    def procesar(self, motor: str, ruta: str, *, dispositivo: str = "cuda",
                 mpx: float | None = None,
                 timeout: float = TIMEOUT_PETICION_S) -> dict:
        """Una pagina, con la admision **por delante** y el reciclado dentro."""
        if mpx is None:
            mpx = megapixeles(ruta)
        d = self.admitir(motor, mpx, dispositivo)
        if d.veredicto == "rechazar":
            return {"ok": False, "rechazada": True, "decision": d.como_dict(),
                    "motor": motor, "dispositivo": dispositivo,
                    "via_entrada": "ruta"}
        t = self.obtener(motor, dispositivo)
        if d.veredicto == "reciclar":
            self._anotar(suceso="reciclado", dispositivo=dispositivo,
                         **d.como_dict())
            t.reciclar()
            # Segunda evaluacion: si sigue sin caber, se desaloja por LRU a otro.
            d2 = self.admitir(motor, mpx, dispositivo)
            while d2.veredicto != "admitir" and self.desalojar_lru(salvar=(motor, dispositivo)):
                d2 = self.admitir(motor, mpx, dispositivo)
            if d2.veredicto == "rechazar":
                return {"ok": False, "rechazada": True, "decision": d2.como_dict(),
                        "motor": motor, "dispositivo": dispositivo,
                        "via_entrada": "ruta"}
            d = d2
        r = t.pedir({"orden": "ocr", "ruta": os.path.abspath(ruta)}, timeout=timeout)
        t.paginas += 1
        t.mpx_max_visto = max(t.mpx_max_visto, mpx)
        r["decision"] = d.como_dict()
        r["motor"] = motor
        r["dispositivo"] = dispositivo          # trampa 11: en cada resultado
        r["via_entrada"] = "ruta"               # trampa 30: en cada resultado
        r["mpx"] = round(mpx, 3)
        return r

    def procesar_lote(self, motor: str, rutas, *, dispositivo: str = "cuda",
                      timeout: float = TIMEOUT_PETICION_S) -> list[dict]:
        """El lote, **en orden descendente de tamaño**. Ver `orden_descendente`."""
        pares = [(r, megapixeles(r)) for r in rutas]
        salida = []
        for ruta, mpx in orden_descendente(pares):
            salida.append(self.procesar(motor, ruta, dispositivo=dispositivo,
                                        mpx=mpx, timeout=timeout))
        return salida

    def cerrar(self) -> None:
        with self._lock:
            for t in self.residentes.values():
                t.cerrar()
            self.residentes.clear()

    def __enter__(self) -> "Registro":
        return self

    def __exit__(self, *_e) -> None:
        self.cerrar()

    def estado(self) -> dict:
        return {"residentes": [
                    {"motor": c[0], "dispositivo": c[1], "paginas": t.paginas,
                     "mpx_max_visto": round(t.mpx_max_visto, 3),
                     "reciclados": t.reciclados,
                     "inactivo_s": round(self.reloj() - t.ultimo_uso, 1),
                     "vivo": t.vivo()}
                    for c, t in self.residentes.items()],
                "vram_libre_MiB": self.vram_libre(), "ttl_s": self.ttl_s,
                "margen_MiB": self.margen_mib}


# ==========================================================================
# MODO TRABAJADOR — este mismo fichero, bajo el interprete del venv
# ==========================================================================
def _trabajador(motor: str, dispositivo: str) -> None:          # pragma: no cover
    """Carga el motor, dice `listo` y atiende ordenes por lineas de JSON.

    Corre bajo `.venv-ai` (o el que sea), donde `filex` **no** esta instalado:
    por eso no importa nada del paquete. La configuracion de RapidOCR es la
    vigente de produccion —`PP-OCRv6 small` + R6, `bench/scripts/ocr_motor.py`—,
    la unica pareja con **0 regresiones sobre 15 documentos**; aplicar R6 a otro
    checkpoint es la trampa 17.
    """
    meta = {"evento": "listo", "motor": motor, "dispositivo": dispositivo,
            "via_entrada": "ruta", "pid": os.getpid()}
    t0 = time.perf_counter()
    gpu = dispositivo == "cuda"

    if motor == "rapidocr":
        import torch
        os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
        from rapidocr import (EngineType, LangDet, LangRec, ModelType, OCRVersion,
                              RapidOCR)
        meta["import_s"] = round(time.perf_counter() - t0, 3)
        t1 = time.perf_counter()
        params = {
            "EngineConfig.onnxruntime.use_cuda": gpu,
            "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
            "Det.ocr_version": OCRVersion("PP-OCRv6"),
            "Rec.ocr_version": OCRVersion("PP-OCRv6"),
            "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
            "Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
            "Det.thresh": 0.2, "Det.box_thresh": 0.45,
            "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000,
        }
        lector = RapidOCR(params=params)
        try:    # trampa 13: get_providers(), NUNCA get_device()
            meta["providers"] = list(lector.text_det.session.session.get_providers())
        except Exception as ex:
            meta["providers"] = f"{type(ex).__name__}: {ex}"

        def leer(ruta):
            r = lector(ruta)
            return " ".join(r.txts) if r and r.txts else ""

    elif motor == "easyocr":
        import torch
        import easyocr
        meta["import_s"] = round(time.perf_counter() - t0, 3)
        t1 = time.perf_counter()
        meta["torch_cuda"] = torch.cuda.is_available()          # trampa 12
        lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)

        def leer(ruta):
            return " ".join(lector.readtext(ruta, detail=0, paragraph=False))

    elif motor == "paddleocr":
        import paddle
        from paddleocr import PaddleOCR
        meta["import_s"] = round(time.perf_counter() - t0, 3)
        t1 = time.perf_counter()
        meta["paddle_cuda"] = paddle.device.is_compiled_with_cuda()
        lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                           use_doc_orientation_classify=False,
                           use_doc_unwarping=False, use_textline_orientation=True)

        def leer(ruta):
            out = []
            for p in lector.predict(ruta):
                d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
                out.extend(d.get("rec_texts", []))
            return " ".join(out)

    else:
        sys.stdout.write(json.dumps({"evento": "error",
                                     "motivo": f"motor desconocido: {motor}"}) + "\n")
        sys.stdout.flush()
        return

    meta["construccion_s"] = round(time.perf_counter() - t1, 3)
    meta["carga_s"] = round(time.perf_counter() - t0, 3)
    sys.stdout.write(json.dumps(meta, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            orden = json.loads(linea)
        except ValueError:
            continue
        if orden.get("orden") == "fin":
            break
        if orden.get("orden") == "ocr":
            t = time.perf_counter()
            try:
                texto = leer(orden["ruta"])
                r = {"ok": True, "chars": len(texto), "texto": texto,
                     "ms": round((time.perf_counter() - t) * 1000, 1)}
            except Exception as ex:
                # El `stderr` de un motor NO vuelve crudo: solo el tipo.
                r = {"ok": False, "error": type(ex).__name__,
                     "ms": round((time.perf_counter() - t) * 1000, 1)}
            sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        elif orden.get("orden") == "ping":
            sys.stdout.write(json.dumps({"ok": True, "pid": os.getpid()}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__" and _MODO_TRABAJADOR:                 # pragma: no cover
    i = sys.argv.index("--trabajador")
    _trabajador(sys.argv[i + 1], sys.argv[i + 2] if len(sys.argv) > i + 2 else "cuda")
