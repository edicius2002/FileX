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

from . import formatos, gpu, invocacion, sondeo
from .grafo import REAL, SIN_SONDEAR, Arista

#: El patrón oro midió con 4 hilos. Se conserva para que las cifras comparen.
HILOS = "4"

#: Hito 2 — qué codificador se pide y con qué se degrada cuando el de la
#: tarjeta no existe. **El orden es la preferencia**, y la lista se recorre
#: SONDEANDO, no leyendo `ffmpeg -encoders`: `av1_nvenc` aparece listado, tiene
#: página de ayuda completa con sus formatos de píxel y sus AVOptions, y falla
#: al abrir el codificador con `No capable devices found`.
#:
#: `hevc` es la única fila donde la GPU se paga de verdad: `hevc_nvenc` cuesta
#: lo mismo que `h264_nvenc` mientras `libx265` es 3× más lento que `libx264`
#: (`HUECOS.md` §4). En `h264` la ventaja medida es de 2,74–2,98× y en `av1` no
#: hay ventaja ninguna, porque no hay codificador.
CODECS_VIDEO: dict[str, tuple[str, ...]] = {
    "hevc": ("hevc_nvenc", "libx265"),
    "av1": ("av1_nvenc", "libsvtav1"),
    "h264": ("h264_nvenc", "libx264"),
    "vp9": ("libvpx-vp9",),
}

#: Alias de lo que un usuario escribe.
ALIAS_CODEC = {"h265": "hevc", "x265": "hevc", "265": "hevc",
               "x264": "h264", "avc": "h264", "264": "h264",
               "av01": "av1", "vp09": "vp9"}

#: **El control de tasa es del CODIFICADOR, no de la petición — MEDIDO, y es el
#: fallo que casi se publica como «hito 2 cumplido».** Degradar `av1_nvenc` a
#: `libsvtav1` cambiando solo el nombre del códec produce
#: `Svt[error]: Max Bitrate only supported with CRF mode`, `rc=-22` y un fichero
#: de **0 bytes**: SVT-AV1 no acepta `-maxrate`/`-bufsize` fuera de modo CRF,
#: mientras `hevc_nvenc` y `libx265` sí. La degradación que solo cambia el
#: códec **sustituye un fallo por otro**.
#:
#: Cada fila es `(banderas de bitrate objetivo, banderas de calidad constante)`,
#: y las dos están SONDEADAS en ejecución (`bench/salidas-hito2/matriz_tasa.json`,
#: 10 de 10 celdas): esta tabla no se deduce del manual de nadie.
_TASA = {
    # NVENC: `-rc vbr` con techo. Acota lo que se puede acotar desde el argv;
    # el desvío que queda se DECLARA (§4).
    "nvenc": (lambda b: ["-b:v", str(b), "-maxrate", str(int(b * 1.5)),
                         "-bufsize", str(b * 2), "-rc", "vbr"],
              lambda q: ["-rc", "vbr", "-cq", str(q), "-b:v", "0"]),
    # x264/x265: ABR con techo, o CRF.
    "x26x": (lambda b: ["-b:v", str(b), "-maxrate", str(int(b * 1.5)),
                        "-bufsize", str(b * 2)],
             lambda q: ["-crf", str(q)]),
    # SVT-AV1: ABR **a secas**. Un `-maxrate` aquí es un fichero de 0 bytes.
    "svtav1": (lambda b: ["-b:v", str(b)],
               lambda q: ["-crf", str(q)]),
    # VP9: el CRF exige `-b:v 0` o se interpreta como techo y no como calidad.
    "vpx": (lambda b: ["-b:v", str(b)],
            lambda q: ["-crf", str(q), "-b:v", "0", "-row-mt", "1"]),
}

#: Qué familia de control de tasa le toca a cada codificador concreto.
FAMILIA_TASA = {
    "hevc_nvenc": "nvenc", "h264_nvenc": "nvenc", "av1_nvenc": "nvenc",
    "libx265": "x26x", "libx264": "x26x",
    "libsvtav1": "svtav1", "libvpx-vp9": "vpx",
}


def codec_normaliza(nombre: str) -> str:
    n = (nombre or "").strip().lower()
    return ALIAS_CODEC.get(n, n)


def _a_bps(v) -> int:
    """`'2000k'`, `'2M'`, `2000000` -> bits por segundo.

    Se normaliza **aquí y una vez**: el bitrate viaja al argv, a `decidido`, a
    los metadatos del fichero y al contrato, y cuatro sitios con cuatro
    unidades distintas es exactamente cómo se publica un desvío que no existe.
    """
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower().replace("bps", "").replace("bit/s", "").strip()
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1000000, s[:-1]
    return int(float(s) * mult)


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

    # ---------------------------------------------------------- hito 2 -----
    def elegir_codec(self, familia: str) -> dict:
        """Sondea la familia pedida y devuelve QUÉ se va a usar y POR QUÉ.

        **Sin intervención**: nadie configura nada, nadie lee un listado. Se
        prueba el codificador de la tarjeta, y si no abre se pasa al siguiente
        de `CODECS_VIDEO`. `av1_nvenc` es el caso del criterio del hito 2 y sale
        degradado a `libsvtav1` **con el `rc` que lo degradó**, porque un 0 de
        bytes sin `rc` no distingue una tarjeta incapaz de un proceso que no
        arrancó (trampa 25).

        Un motor NO decide sobre la tarjeta sin la guardia de VRAM: `capacidad`
        toma el lock de máquina y aplica `GPU_GUARD` antes de medir nada.
        """
        fam = codec_normaliza(familia)
        cands = CODECS_VIDEO.get(fam)
        if not cands:
            raise ValueError(f"códec de vídeo no soportado: '{familia}'")
        info = {"codec_video": fam, "codec_video_real": "", "nvenc": False,
                "degradado_de": "", "degradado_rc": 0, "degradado_motivo": ""}
        for cand in cands:
            if "nvenc" not in cand:
                info["codec_video_real"] = cand
                return info
            try:
                ok, rc, motivo = gpu.capacidad(cand)
            except gpu.GpuOcupada as e:
                ok, rc, motivo = False, 0, str(e)
            if ok:
                info["codec_video_real"] = cand
                info["nvenc"] = True
                return info
            # Se anota el PRIMER rechazo, que es el del codificador preferido.
            if not info["degradado_de"]:
                info["degradado_de"] = cand
                info["degradado_rc"] = rc
                info["degradado_motivo"] = motivo
        # Ningún candidato: la familia solo tenía NVENC y no funciona.
        raise ValueError(f"no hay codificador disponible para '{fam}'")

    def _video_codec(self, pedido: dict, decidido: dict) -> list[str]:
        """Las banderas de vídeo, y lo que el motor decidió por su cuenta.

        Todo lo elegido aquí va a `decidido`, que el núcleo mete en
        `pedido['params']`: si el motor elige y no lo dice, el punto 4 del
        contrato lo llama «propiedad no solicitada» — y tiene razón.
        """
        info = self.elegir_codec(pedido["codec_video"])
        decidido.update(info)
        cv = info["codec_video_real"]
        argv = ["-c:v", cv]

        # Las banderas de tasa son del CODIFICADOR REAL, el que se va a usar
        # tras la degradación — no del que se pidió. Cogerlas del pedido es lo
        # que dejaba `libsvtav1` con un `-maxrate` que no admite.
        por_bitrate, por_calidad = _TASA[FAMILIA_TASA[cv]]
        decidido["familia_tasa"] = FAMILIA_TASA[cv]

        br = pedido.get("bitrate_video")
        if br:
            bps = _a_bps(br)
            # `bitrate_video_bps`, NO `bitrate_bps`: esa clave la lee la regla
            # de bitrate del contrato, que solo mira PISTAS DE AUDIO. Meter
            # aquí el bitrate de vídeo haría que la pista de audio de 128 kbps
            # se comparase con 2 000 kbps y saliera `fallo`.
            decidido["bitrate_video_bps"] = bps
            argv += por_bitrate(bps)
        else:
            # Sin bitrate pedido, calidad constante. Cada codificador tiene su
            # escala y NO son la misma: `-cq` en NVENC, `-crf` en x265, SVT-AV1
            # y VP9. El número que llega es el que pidió quien llama.
            q = int(pedido.get("crf", 28 if info["codec_video"] == "hevc" else 30))
            argv += por_calidad(q)
            decidido["calidad_constante"] = q
        return argv

    def _metadatos(self, decidido: dict) -> list[str]:
        """Lo que el fichero de salida lleva escrito sobre su propia conversión.

        MEDIDO: Matroska conserva las etiquetas arbitrarias; **MP4 no** —solo
        acepta un puñado de claves del átomo `ilst`—, así que la clave que
        sobrevive en los dos es `comment`. Se escribe una sola línea legible,
        no seis etiquetas que tres formatos tirarían en silencio.
        """
        trozos = [f"filex.codec={decidido.get('codec_video_real', '')}"]
        if decidido.get("bitrate_video_bps"):
            trozos.append(f"filex.bitrate_pedido_bps={decidido['bitrate_video_bps']}")
        if decidido.get("degradado_de"):
            trozos.append(f"filex.degradado_de={decidido['degradado_de']}"
                          f" rc={decidido.get('degradado_rc', 0)}")
        return ["-metadata", "comment=" + "; ".join(trozos)]

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
        elif pedido.get("codec_video"):
            # ---- hito 2: NVENC con sondeo y degradación ---------------------
            argv += self._video_codec(pedido, decidido)
            audio = pedido.get("bitrate_audio", "96k" if d == "webm" else "128k")
            argv += ["-c:a", "libopus" if d == "webm" else "aac",
                     "-b:a", str(audio)]
            # El desvío de bitrate se registra en los METADATOS DE SALIDA. Lo
            # que se puede escribir en UNA pasada es lo pedido y con qué se
            # codificó; el bitrate obtenido no existe todavía cuando se
            # construye este argv, y se lee del propio fichero después
            # (`bitrate = bytes*8/duración`). Con las dos mitades EN EL FICHERO,
            # el desvío es computable sin consultar a FileX.
            argv += self._metadatos(decidido)
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
