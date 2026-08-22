"""Los adaptadores de motor. Un motor = un binario + sus aristas + cómo se le llama.

**Todo lo que hay aquí se sondea en ejecución, no se deduce** — `av1_nvenc`
aparece listado por ffmpeg y no funciona; `paddlex` declara sus ocho detectores
con `limit_type='max'` mientras la sonda mide `'min'` en la ruta que se usa de
verdad. Deducir del código dio **lo contrario** de lo que hace el código.

Las órdenes no son inventadas: salen de las **39 órdenes reproducibles** de
`bench/salidas-referencia/referencia.json`, y se les añade lo que el patrón oro
no necesitaba porque corría en un directorio limpio y aquí sí hace falta:

* `-y` y `-nostdin` — banderas no interactivas (higiene; la defensa real es
  `stdin=DEVNULL`, que vive en `invocacion.py`).
* **`-map 0` explícito** — MEDIDO: por defecto ffmpeg **descarta la segunda
  pista de audio, en silencio**, y los dos competidores caen en ello.
* **`-frames:v 1 -update 1`** cuando el destino es una imagen única — recupera
  **13 de las 27** aristas del residuo: la bandera con mejor relación
  coste/beneficio medida.
* **La densidad de `imagen→pdf` se AJUSTA a la página, no se fija** — con
  `-density 150` sale un A3 y medio; calculándola, **A4 exacto y 7 de 7 íntegro**.

Y una regla que parece contraria a las otras y está MEDIDA
(`bench/invocacion-aristas.md` §7.2): **fuerza lo que el motor no puede deducir;
no fuerces lo que ya deduce bien.** Forzar el códec «por defecto» del muxer
`image2` **escribe un JPEG dentro de un `.ppm`** y es PEOR que no forzar nada.
Un valor que el motor declara «por defecto» no es una capacidad sondeada.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from . import formatos, invocacion, sondeo
from .grafo import REAL, SIN_SONDEAR, Arista

#: El patrón oro midió con 4 hilos. Se conserva para que las cifras comparen.
HILOS = "4"


@dataclass
class Motor:
    nombre: str
    binario: str
    version: str = ""
    ruta: str | None = None
    aristas: list[Arista] = field(default_factory=list)
    #: Por qué NO está disponible, cuando no lo está. «Falta el ejecutable X»
    #: no siempre es verdad: puede faltar el demonio de Docker, la imagen, o un
    #: binario DENTRO de ella — cuatro cosas distintas. R14: se nombra la
    #: CAPACIDAD que falta, nunca el comando que la instala.
    motivo_ausencia: str = ""

    @property
    def disponible(self) -> bool:
        return self.ruta is not None

    def sondear(self) -> None:
        """Rellena `ruta` y `version` preguntándole AL BINARIO.

        Y superpone lo que haya en `filex/sondeo/<motor>.json`: el resultado de
        ejecutar una arista es DATO, no código. Una tabla tecleada en este
        fichero no llevaría su `build`, y sin `build` una arista miente en la
        siguiente máquina — `svg→png` con `magick` es real en Windows y nominal
        en el Debian del contenedor.
        """
        self.ruta = invocacion.disponible(self.binario)
        if self.ruta:
            self.version = self._version()
            self.aristas = sondeo.aplicar(self.nombre, self.build, self._aristas())

    def _version(self) -> str:
        return ""

    def _aristas(self) -> list[Arista]:
        return []

    def orden(self, entrada: str, salida: str, pedido: dict,
              *, timeout: float | None = None) -> list[str]:
        """`timeout` es el tope de QUIEN LLAMA, y algunos motores lo necesitan.

        MEDIDO (`bench/hito5-documental.md` §1): **matar el `docker run` no mata
        el contenedor** —tres `soffice` sobrevivieron 37 minutos al
        `taskkill /F /T`, y `--rm` tampoco—, así que un motor que delega en un
        proceso remoto tiene que poner **su propio tope por dentro**. Adivinarlo
        con una constante deja de funcionar en cuanto alguien pide otro.
        """
        raise NotImplementedError

    def parar(self) -> None:
        """Garantizar que el motor ha parado. Se llama ANTES de borrar el
        desechable cuando la invocación se agotó.

        Con motores nativos no hace falta: `_matar_arbol` sí los mata. Con un
        contenedor sí, y el precio de no hacerlo está medido: borrar el origen
        de un *bind mount* vivo dejó a `docker rm -f` respondiendo «did not
        receive an exit event»."""
        return None

    @property
    def build(self) -> str:
        """La quinta dimensión de la arista. Sin esto, la tabla miente en otra
        máquina: `svg→png` con `magick` es real en Windows y nominal en Debian."""
        return f"{self.nombre} {self.version}" if self.version else self.nombre


# ---------------------------------------------------------------- ImageMagick


class ImageMagick(Motor):
    def __init__(self) -> None:
        super().__init__(nombre="imagemagick", binario="magick")

    def _version(self) -> str:
        r = invocacion.ejecutar([self.binario, "-version"], timeout=20)
        if not r.ok:
            return ""
        primera = (r.salida_txt or "").splitlines()[0] if r.salida_txt else ""
        # "Version: ImageMagick 7.1.2-21 Q16-HDRI ..."
        for t in primera.split():
            if t and t[0].isdigit():
                return t
        return primera[:40]

    #: Los que el patrón oro ejecutó de verdad, con su `id` de `referencia.json`.
    _MEDIDAS = {
        ("png", "webp"): "img.png2webp",
        ("png", "avif"): "img.png2avif",
        ("png", "jpg"): "img.png2jpg",
        ("tif", "png"): "img.tif16_2png",
        ("png", "pdf"): "img.png2pdf.150",
    }

    _RASTER = {"png", "jpg", "webp", "avif", "gif", "bmp", "tif", "ico"}

    def _aristas(self) -> list[Arista]:
        out = []
        for o in self._RASTER:
            for d in self._RASTER:
                if o == d:
                    continue
                ev = self._MEDIDAS.get((o, d), "")
                out.append(Arista(
                    origen=o, destino=d, motor=self.nombre, build=self.build,
                    estado=REAL if ev else SIN_SONDEAR, coste=1.0,
                    evidencia=f"referencia.json:{ev}" if ev else "",
                ))
            # imagen → pdf: NO rasteriza (los píxeles ya eran píxeles).
            out.append(Arista(origen=o, destino="pdf", motor=self.nombre,
                              parametrizacion="densidad_ajustada_a_pagina",
                              build=self.build,
                              estado=REAL if (o, "pdf") in self._MEDIDAS else SIN_SONDEAR,
                              coste=1.2,
                              evidencia="bench/invocacion-aristas.md §6"))
        # svg → raster: SÍ rasteriza, y aquí es donde se pierde el texto.
        for d in ("png", "webp", "jpg"):
            out.append(Arista(origen="svg", destino=d, motor=self.nombre,
                              build=self.build, estado=SIN_SONDEAR, coste=1.0,
                              rasteriza=True,
                              evidencia="bench/aristas-nominales.md §8.2"))
        return out

    def orden(self, entrada: str, salida: str, pedido: dict,
              *, timeout: float | None = None) -> list[str]:
        d = formatos.normaliza(os.path.splitext(salida)[1])
        argv = [self.binario, "-limit", "thread", HILOS, entrada]

        if pedido.get("ancho") or pedido.get("alto"):
            geo = f"{pedido.get('ancho', '')}x{pedido.get('alto', '')}"
            argv += ["-resize", geo]
        if pedido.get("profundidad_bits"):
            argv += ["-depth", str(pedido["profundidad_bits"])]

        if d in ("jpg", "jpeg"):
            # MEDIDO: ImageMagick aplana el alfa sobre NEGRO. Lo esperable es
            # blanco, y el patrón oro guarda las dos variantes por eso mismo.
            argv += ["-background", pedido.get("fondo", "white"), "-flatten",
                     "-quality", str(pedido.get("calidad", 85))]
        elif d == "webp":
            if pedido.get("sin_perdida"):
                # MEDIDO: con paleta / 1 bit, sin pérdida es exacto Y MÁS PEQUEÑO
                # (42 B contra 94 B). Usar pérdida ahí es peor por los dos lados.
                argv += ["-define", "webp:lossless=true"]
            else:
                argv += ["-quality", str(pedido.get("calidad", 80))]
        elif d == "avif":
            argv += ["-quality", str(pedido.get("calidad", 50))]
        elif d == "pdf":
            argv += ["-density", str(pedido.get("dpi", 150))]

        argv.append(salida)
        return argv


# ---------------------------------------------------------------- Ghostscript


class Ghostscript(Motor):
    def __init__(self) -> None:
        super().__init__(nombre="ghostscript",
                         binario="gswin64c" if os.name == "nt" else "gs")

    def _version(self) -> str:
        r = invocacion.ejecutar([self.binario, "--version"], timeout=20)
        return (r.salida_txt or "").strip().splitlines()[0] if r.ok else ""

    _DEVICE = {"png": "png16m", "jpg": "jpeg", "tif": "tiff24nc", "pdf": "pdfwrite"}

    def _aristas(self) -> list[Arista]:
        out = []
        for d, ev in (("png", "pdf.2png"), ("jpg", "pdf.2jpg"), ("tif", "pdf.2tif")):
            out.append(Arista(origen="pdf", destino=d, motor=self.nombre,
                              parametrizacion=f"-sDEVICE={self._DEVICE[d]} -r150",
                              build=self.build, estado=REAL, coste=1.0,
                              rasteriza=True,
                              evidencia=f"referencia.json:{ev}"))
        out.append(Arista(origen="pdf", destino="pdf", motor=self.nombre,
                          parametrizacion="-sDEVICE=pdfwrite", build=self.build,
                          estado=REAL, coste=1.0,
                          evidencia="referencia.json:pdf.2pdf"))
        return out

    def orden(self, entrada: str, salida: str, pedido: dict,
              *, timeout: float | None = None) -> list[str]:
        d = formatos.normaliza(os.path.splitext(salida)[1])
        dev = self._DEVICE.get(d)
        if dev is None:
            raise ValueError(f"ghostscript no escribe '{d}'")
        argv = [self.binario, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                f"-sDEVICE={dev}"]
        if d == "jpg":
            argv.append(f"-dJPEGQ={pedido.get('calidad', 85)}")
        if dev != "pdfwrite":
            # MEDIDO, y es la trampa nº 6 del proyecto: **no sobremuestrear**.
            # El arnés de la fase 2 rasterizaba a 200 ppp documentos con imagen
            # incrustada a 100 nativos, y ese ×2 de interpolación INVENTÓ las
            # marcas de «fallan los tres motores». Quien conozca los ppp
            # nativos debe pasarlos en `pedido['dpi']`.
            argv.append(f"-r{pedido.get('dpi', 150)}")
            argv.append("-dNumRenderingThreads=" + HILOS)
        argv += [f"-sOutputFile={salida}", entrada]
        return argv


# ---------------------------------------------------------------------- ffmpeg


class FFmpeg(Motor):
    def __init__(self) -> None:
        super().__init__(nombre="ffmpeg", binario="ffmpeg")

    def _version(self) -> str:
        r = invocacion.ejecutar([self.binario, "-hide_banner", "-version"], timeout=20)
        if not r.ok:
            return ""
        p = (r.salida_txt or "").split()
        return p[2] if len(p) > 2 else ""

    _VIDEO = ("mp4", "mkv", "webm", "mov", "avi")
    _AUDIO = ("wav", "flac", "mp3", "m4a", "opus", "ogg")

    _MEDIDAS = {
        ("mkv", "mp4"): "vid.mkv2mp4.map0", ("mp4", "webm"): "vid.mp42webm",
        ("mp4", "mkv"): "vid.mp42mkv", ("mp4", "gif"): "vid.2gif.paleta",
        ("mp4", "mp3"): "vid.extraer.mp3", ("mp4", "m4a"): "vid.extraer.copy",
        ("wav", "mp3"): "aud.wav2mp3", ("wav", "flac"): "aud.wav2flac",
        ("wav", "opus"): "aud.wav2opus", ("wav", "m4a"): "aud.wav2aac",
        ("flac", "wav"): "aud.flac2wav", ("flac", "mp3"): "aud.flac2mp3",
        ("flac", "opus"): "aud.flac2opus", ("mp3", "wav"): "aud.mp32wav",
        ("mp3", "flac"): "aud.mp32flac",
    }

    def _aristas(self) -> list[Arista]:
        out = []
        pares = ([(o, d) for o in self._VIDEO for d in self._VIDEO if o != d]
                 + [(o, d) for o in self._VIDEO for d in self._AUDIO]
                 + [(o, d) for o in self._AUDIO for d in self._AUDIO if o != d]
                 + [(o, "gif") for o in self._VIDEO])
        for o, d in pares:
            ev = self._MEDIDAS.get((o, d), "")
            out.append(Arista(origen=o, destino=d, motor=self.nombre,
                              build=self.build,
                              estado=REAL if ev else SIN_SONDEAR,
                              coste=1.0,
                              evidencia=f"referencia.json:{ev}" if ev else ""))
        return out

    def orden(self, entrada: str, salida: str, pedido: dict,
              *, timeout: float | None = None):
        d = formatos.normaliza(os.path.splitext(salida)[1])
        fo = formatos.formato(d)
        #: Lo que este motor decide por su cuenta y el contrato tiene que saber.
        decidido: dict = {}
        # `-y` y `-nostdin` son HIGIENE. La defensa es `stdin=DEVNULL`, en
        # `invocacion.py`: MEDIDO que `-y` es necesario y NO suficiente.
        argv = [self.binario, "-hide_banner", "-nostdin", "-y",
                "-threads", HILOS, "-i", entrada]

        solo_audio = fo is not None and fo.categoria == "audio"
        if solo_audio:
            argv.append("-vn")
        elif d == "gif":
            # `-map 0` y el muxer `gif` se destruyen mutuamente: `gif` no tiene
            # códec de audio y arrastrar las pistas de la entrada aborta con
            # AVERROR_ENCODER_NOT_FOUND. MEDIDO: 5 de 5 aristas vídeo→gif rotas,
            # **`mp4→gif` incluida** — que el patrón oro daba por buena **solo
            # porque `trivial.mp4` no tiene audio** (`bench/sondeo-ffmpeg.md` §5).
            argv += ["-map", "0:v:0"]
        else:
            # -map 0 EXPLÍCITO. Sin esto ffmpeg descarta la segunda pista de
            # audio en silencio, y el contrato lo detecta después: mejor no
            # producirlo.
            argv += ["-map", "0"]

        if pedido.get("copia"):
            argv += ["-c", "copy"] if not solo_audio else ["-c:a", "copy"]
        elif d == "gif":
            # La paleta NO es un lujo: el GIF con paleta genérica pesa un 35 %
            # MENOS que el bueno, así que «más pequeño» no sirve de criterio.
            fps = pedido.get("fps", 12)
            ancho = pedido.get("ancho", 320)
            # El motor ESCALA por su cuenta y tiene que decirlo, o el punto 4 lo
            # llama «redimensionado no solicitado» — y con razón, porque nadie
            # lo pidió. MEDIDO (`bench/sondeo-ffmpeg.md` §5): con `-map 0:v:0`
            # se recuperan 2 de 5 aristas; **declarar la escala recupera las 5**.
            decidido["ancho"] = ancho
            argv += ["-vf",
                     f"fps={fps},scale={ancho}:-1:flags=lanczos,split[a][b];"
                     f"[a]palettegen=max_colors=256[p];[b][p]paletteuse=dither=bayer",
                     "-loop", "0"]
        elif solo_audio:
            codec = {"mp3": "libmp3lame", "flac": "flac", "opus": "libopus",
                     "m4a": "aac", "aac": "aac", "wav": "pcm_s16le",
                     "ogg": "libvorbis"}.get(d)
            if codec:
                argv += ["-c:a", codec]
            if fo is not None and fo.perdida:
                argv += ["-b:a", str(pedido.get("bitrate_audio", "192k"))]
        else:
            if d == "webm":
                argv += ["-c:v", "libvpx-vp9", "-crf", str(pedido.get("crf", 33)),
                         "-b:v", "0", "-row-mt", "1", "-deadline", "good",
                         "-cpu-used", "4", "-c:a", "libopus", "-b:a", "96k"]
            else:
                argv += ["-c:v", "libx264", "-crf", str(pedido.get("crf", 23)),
                         "-preset", "medium", "-c:a", "aac", "-b:a", "128k"]

        # Forzar el MUXER sí: es lo que el motor no puede deducir con seguridad
        # cuando la extensión es ambigua. Forzar el CÓDEC por defecto, no.
        muxer = {"mkv": "matroska", "m4a": "ipod", "jpg": "image2"}.get(d)
        if muxer:
            argv += ["-f", muxer]

        argv.append(salida)
        return (argv, decidido) if decidido else argv


# ----------------------------------------------------------------- registro


#: Los motores NATIVOS. Los de fuera no se listan aquí: se DESCUBREN.
MOTORES = (ImageMagick, Ghostscript, FFmpeg)


def _descubrir() -> list:
    """Motores que viven en su propio fichero `filex/motor_*.py`.

    **Un motor nuevo no toca este fichero.** Es una decisión de coordinación
    antes que de arquitectura: una tupla central que hay que editar para añadir
    un motor es un punto de colisión garantizado en cuanto dos personas —o dos
    agentes— añaden uno a la vez. Aquí cada motor trae su fichero y su nombre.

    Un módulo que no importa **no tumba el registro**: se ignora, igual que un
    binario que falta. La misma regla, un nivel más arriba.
    """
    import importlib
    import pkgutil

    fuera = []
    paquete = __name__.rsplit(".", 1)[0]
    for info in pkgutil.iter_modules([os.path.dirname(os.path.abspath(__file__))]):
        if not info.name.startswith("motor_"):
            continue
        try:
            mod = importlib.import_module(f"{paquete}.{info.name}")
        except Exception:
            continue
        for obj in vars(mod).values():
            if (isinstance(obj, type) and issubclass(obj, Motor) and obj is not Motor
                    and obj.__module__ == mod.__name__):
                fuera.append(obj)
    return fuera


def sondear_todos() -> list[Motor]:
    """Sondea los motores UNA vez y devuelve todos, disponibles o no.

    «Un motor cuyo binario falta se auto-excluye y la CLI lo informa, en lugar
    de fallar» — criterio de aceptación del hito 1.
    """
    out = []
    for cls in list(MOTORES) + _descubrir():
        try:
            m = cls()
            m.sondear()
        except Exception:
            try:
                m = cls()
            except Exception:
                continue
            m.ruta = None
        out.append(m)
    return out
