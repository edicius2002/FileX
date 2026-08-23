"""La conversión. Y la verificación **dentro** de ella, no después.

Es la decisión de diseño más importante del hito 1, y está MEDIDA
(`bench/contrato-quinto-punto.md`):

    **El punto 5 es el único punto del contrato que NO se puede verificar a
    posteriori.** Sin censo, **49 de las 53 salidas del patrón oro bajan de `ok`
    a `ok_parcial`**. Hay que estar mirando cuando el motor escribe.

Por eso aquí no hay una función `convertir()` y otra `verificar()` que alguien
pueda llamar en el orden equivocado o saltarse: **el censo se toma dentro del
mismo `with` que lanza el motor**, y la salida no sale del directorio desechable
hasta que el contrato la ha juzgado.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

from . import contrato, formatos, invocacion, motores as _motores
from .confinamiento import Confinamiento, Denegado, nombre_seguro
from .grafo import Arista, Camino, Decision, Grafo
from .trabajo import DirectorioDeTrabajo


#: Las claves del pedido que deciden PÍXELES, y por tanto tienen que actuar en
#: el salto que los crea, no en el último — MEDIDO (`bench/sondeo-imagemagick.md`
#: §6.1): `--params '{"dpi":400}'` sobre `svg→pdf` daba una página de 3,0×1,5 cm
#: con los mismos 480×240 píxeles **y contrato 6/6 en los dos saltos**, porque el
#: `dpi` llegaba al `png→pdf` cuando el rasterizado ya había ocurrido.
#:
#: Lo que NO se propaga son las decisiones de CODIFICACIÓN —calidad, códec,
#: bitrate, sin_perdida—: esas pertenecen al fichero final, y aplicarlas a un
#: intermedio es recodificar dos veces.
CLAVES_DE_PIXEL = ("dpi", "ancho", "alto", "profundidad_bits", "fondo")


def _pedido_intermedio(pedido: dict) -> dict:
    return {k: v for k, v in (pedido or {}).items() if k in CLAVES_DE_PIXEL}


# --------------------------------------------------------------------------
# El destino en curso — un agujero que solo se ve con CONCURRENCIA
# --------------------------------------------------------------------------
#
# HITO 7, y es el hallazgo del hito — MEDIDO (`bench/hito7-superficies.md` §5.3).
# Tres peticiones simultáneas de la API HTTP con **tres entradas distintas**
# (PNG de 42 855 B, JPEG de 87 954 B y TIFF de 72 MB) y **la misma ruta de
# salida** devolvieron las tres `ok`, con contrato aprobado, declarando
# **13 516 / 14 402 / 647 580 bytes** — y en el disco quedó **un solo fichero de
# 647 580 B**. Dos de las tres respuestas describían un fichero que ya no
# existía.
#
# **El contrato no puede atraparlo y no es culpa suya:** juzga la salida dentro
# del directorio desechable, que es privado de cada conversión, y el
# atropello ocurre después, en el `shutil.move` al destino. El punto 5 mira el
# desechable; nadie miraba el destino.
#
# El arreglo va AQUÍ y no en la API, y eso es R10 funcionando: el fallo lo
# encontró la cuarta superficie y el remedio no vive en ella — la CLI, MCP y el
# watcher tenían exactamente el mismo agujero y se cierra en el mismo sitio para
# los cuatro.
#
# **Alcance declarado, sin adornos: es un cerrojo DE PROCESO.** Dos procesos
# `filex` distintos —una API y un watcher, por ejemplo— siguen pudiendo pisarse.
# Cerrarlo entre procesos necesita un cerrojo de fichero o un mutex con nombre,
# igual que el `gpu_acquire` de `bench/`, y queda **PENDIENTE**.
_DESTINOS_EN_CURSO: set[str] = set()
_CERROJO_DESTINOS = threading.Lock()


def _reservar_destino(ruta: str) -> bool:
    clave = os.path.normcase(os.path.abspath(ruta))
    with _CERROJO_DESTINOS:
        if clave in _DESTINOS_EN_CURSO:
            return False
        _DESTINOS_EN_CURSO.add(clave)
        return True


def _soltar_destino(ruta: str) -> None:
    clave = os.path.normcase(os.path.abspath(ruta))
    with _CERROJO_DESTINOS:
        _DESTINOS_EN_CURSO.discard(clave)


@dataclass
class Salto:
    arista: Arista
    rc: int | None = None
    ms: float = 0.0
    veredicto: str = ""
    hallazgos: list = field(default_factory=list)
    cobertura: dict = field(default_factory=dict)
    sobrantes: dict = field(default_factory=dict)
    motivo: str = ""
    #: Dónde quedó la salida de ESTE salto: dentro del desechable si es
    #: intermedia, en el destino real si es la última.
    ruta: str = ""
    #: `stderr` crudo. Para el log y para el humano. **Nunca para un modelo.**
    err: str = ""


@dataclass
class Conversion:
    entrada: str
    salida: str
    camino: Camino | None = None
    saltos: list[Salto] = field(default_factory=list)
    ok: bool = False
    motivo: str = ""
    aviso: str = ""
    rechazados: list = field(default_factory=list)

    @property
    def veredicto(self) -> str:
        if not self.ok:
            return "fallo"
        peor = "ok"
        for s in self.saltos:
            if s.veredicto == "fallo":
                return "fallo"
            if s.veredicto in ("aviso", "ok_parcial") and peor == "ok":
                peor = s.veredicto
        return peor


class FileX:
    """El núcleo. Las cuatro superficies (CLA, MCP, watcher, API) lo usan a él.

    R10: **la validación vive en el núcleo, no en la superficie.** La CLI de
    kordoc ignora su propia variable de confinamiento porque la validación
    estaba en la capa MCP. Aquí no puede pasar: no hay otro camino.
    """

    def __init__(self, raices_lectura=None, raices_escritura=None) -> None:
        self.motores = {m.nombre: m for m in _motores.sondear_todos()}
        self.grafo = Grafo()
        for m in self.motores.values():
            if m.disponible:
                for a in m.aristas:
                    self.grafo.añadir(a)
        self.confinamiento = None
        if raices_lectura:
            self.confinamiento = Confinamiento(raices_lectura, raices_escritura)

    # ------------------------------------------------------------ inventario

    @property
    def disponibles(self) -> list:
        return [m for m in self.motores.values() if m.disponible]

    @property
    def ausentes(self) -> list:
        return [m for m in self.motores.values() if not m.disponible]

    def destinos(self, ext: str) -> list[str]:
        """`list_targets`: la única respuesta honesta a «¿puedo hacer X?».

        MEDIDO y contraintuitivo (`bench/saturacion-herramientas.md` §3.5):
        cuando el catálogo no cubre lo que se pide, un modelo **no se abstiene**
        — llama a la más parecida y declara éxito con un dato falso, el 15-17 %
        de las veces. Por eso esto es un mecanismo de seguridad, no una comodidad.
        """
        o = formatos.normaliza(ext)
        vistos = {o}
        frente = [o]
        while frente:
            act = frente.pop()
            for a in self.grafo.desde(act):
                if a.destino not in vistos:
                    vistos.add(a.destino)
                    frente.append(a.destino)
        return sorted(vistos - {o})

    def planificar(self, entrada: str, salida: str) -> Decision:
        return self.grafo.camino(
            formatos.normaliza(os.path.splitext(entrada)[1]),
            formatos.normaliza(os.path.splitext(salida)[1]),
        )

    # ------------------------------------------------------------ conversión

    def _resolver(self, entrada: str, salida: str) -> tuple[str, str]:
        # R12 sobre el NOMBRE DE SALIDA, y va ANTES de mirar si hay lista
        # blanca: sin esto se escriben 94 B en el flujo alternativo de un
        # fichero ajeno con `veredicto: ok`, y el contenido visible de la
        # víctima queda intacto, así que nadie lo nota. Validar el DIRECTORIO
        # del destino no basta — el nombre del fichero no lo miraba nadie.
        if not nombre_seguro(os.path.basename(os.path.abspath(salida))):
            raise Denegado()
        if self.confinamiento is None:
            return os.path.abspath(entrada), os.path.abspath(salida)
        ent = self.confinamiento.resolver(entrada)
        # La salida aún no existe: se valida su DIRECTORIO, que sí.
        dsal = os.path.dirname(os.path.abspath(salida)) or "."
        self.confinamiento.resolver(dsal, escritura=True)
        return ent, os.path.abspath(salida)

    def convertir(self, entrada: str, salida: str, pedido: dict | None = None,
                  *, timeout: float = invocacion.TIMEOUT_POR_DEFECTO) -> Conversion:
        pedido = dict(pedido or {})
        conv = Conversion(entrada=entrada, salida=salida)

        try:
            ent_abs, sal_abs = self._resolver(entrada, salida)
        except Denegado as e:
            conv.motivo = str(e)
            return conv
        if not os.path.isfile(ent_abs):
            # R4: el MISMO mensaje que para «prohibido». Distinguirlos convierte
            # el conversor en un oráculo de existencia del disco ajeno.
            conv.motivo = "ruta no accesible"
            return conv

        dec = self.planificar(entrada, salida)
        conv.camino = dec.camino
        conv.rechazados = dec.rechazados
        conv.aviso = dec.aviso
        if not dec.hay:
            conv.motivo = dec.motivo
            return conv
        if dec.camino is not None and dec.camino.saltos == 0:
            conv.motivo = "origen y destino son el mismo formato"
            return conv

        # Nadie más puede estar escribiendo este destino. Se reserva DESPUÉS de
        # saber que hay camino —reservar para luego decir «no hay camino» sería
        # bloquear un destino por nada— y se suelta en el `finally`.
        if not _reservar_destino(sal_abs):
            # No es un mensaje opaco y no debe serlo: el cliente **pidió** esta
            # ruta, así que nombrarla no le dice nada que no supiera. Lo que sí
            # sería un fallo es devolver `ok` como se hacía hasta el hito 7.
            conv.motivo = "otra conversión está escribiendo ya esa ruta de salida"
            return conv

        actual = ent_abs
        temporales: list[DirectorioDeTrabajo] = []
        try:
            for i, paso in enumerate(dec.camino.pasos):
                ultimo = i == len(dec.camino.pasos) - 1
                s = self._un_salto(paso.arista, actual, sal_abs, pedido,
                                   ultimo=ultimo, timeout=timeout,
                                   temporales=temporales)
                conv.saltos.append(s)
                if s.veredicto == "fallo" or s.rc not in (0,):
                    conv.motivo = s.motivo or "el motor rechazó la conversión"
                    return conv
                actual = s.ruta
            conv.ok = True
            return conv
        finally:
            _soltar_destino(sal_abs)
            for t in temporales:
                t.cerrar()

    def _un_salto(self, arista: Arista, entrada: str, destino_final: str,
                  pedido: dict, *, ultimo: bool, timeout: float,
                  temporales: list) -> Salto:
        """Un salto = un directorio desechable + un motor + un censo + el contrato."""
        motor = self.motores[arista.motor]
        s = Salto(arista=arista)

        t = DirectorioDeTrabajo()
        temporales.append(t)
        nombre = f"salida.{arista.destino}"
        dentro = t.destino(nombre)

        try:
            # El motor recibe el tope de QUIEN LLAMA: el de aquí solo alcanza
            # al cliente, y hay motores cuyo trabajo real vive en otro proceso.
            argv = motor.orden(entrada, dentro,
                               pedido if ultimo else _pedido_intermedio(pedido),
                               timeout=timeout)
            # `orden()` puede devolver `(argv, decidido)`: lo que el motor eligio
            # por su cuenta y el contrato tiene que saber. Es aditivo — quien
            # devuelva solo `argv` sigue funcionando — y evita la unica
            # alternativa, que era duplicar la logica de decision en un segundo
            # metodo y verla divergir.
            declarado = {}
            if isinstance(argv, tuple):
                argv, declarado = argv
                declarado = dict(declarado or {})
        except Exception as e:
            s.motivo = f"no se pudo construir la orden: {e}"
            return s

        # El `cwd` del hijo va DENTRO del desechable. Validar la ruta de salida
        # NO basta: hay motores que escriben en el `cwd`.
        r = invocacion.ejecutar(argv, timeout=timeout, cwd=t.ruta)
        s.rc, s.ms, s.err = r.rc, r.ms, r.err
        if r.agotado:
            # ANTES de que el `finally` borre el desechable. Borrar el origen de
            # un bind mount vivo deja al contenedor atascado — MEDIDO.
            try:
                motor.parar()
            except Exception:
                pass
        if not r.ok:
            s.motivo = r.motivo
            s.ruta = dentro
            return s

        # --- el punto 5, tomado AQUÍ: después ya no existe -------------------
        censo = t.censo()
        s.sobrantes = t.sobrantes([nombre])

        # Lo que el MOTOR decide y nadie pidio tiene que llegar al contrato, o
        # el punto 4 —escrito para atrapar a `image-worker-mcp`— atrapa a FileX.
        # Tres agentes dieron con la misma forma el mismo dia: el motor y el
        # contrato no compartian el `pedido`.
        ped = dict(pedido, destino=arista.destino)
        _f = formatos.formato(arista.destino)
        if _f is not None and _f.categoria == "audio" and not ped.get("solo_audio"):
            # `orden()` pone `-vn` por la categoria del destino, y el contrato
            # exigia que un .wav extraido de un .mp4 conservara el video. MEDIDO
            # (`bench/sondeo-ffmpeg.md` 3): 13 aristas video->audio pasaban a
            # `V7 fallo` por no declararlo. Los DOS sitios hacen falta: el punto
            # 2 mira `solo_audio` o `params.solo_audio`, y el punto 4 solo mira
            # `params`.
            ped["solo_audio"] = True
            ped["params"] = dict(ped.get("params") or {}, solo_audio=True)
        ped["params"] = dict(ped.get("params") or {}, **declarado)
        ped.update(declarado)
        res = contrato.verificar(dentro, entrada, ped, censo)
        s.veredicto = res.get("veredicto", "?")
        s.hallazgos = res.get("hallazgos", [])
        s.cobertura = res.get("cobertura", {})
        if s.veredicto == "fallo":
            s.motivo = contrato.resumen(res)
            s.ruta = dentro
            return s

        if ultimo:
            t.recoger(nombre, destino_final)
            s.ruta = destino_final
        else:
            s.ruta = dentro  # el desechable vive hasta el final
        return s
