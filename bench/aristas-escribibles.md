# C50 + residuo de C28 — escribir lo que el censo declaró inescribible

**worker10, carril CPU, ronda 20.** Rama `cpu/aristas-escribibles`.
Salidas en `bench/salidas-aristas-escribibles/`, con su `MANIFIESTO.md`.

**Estado de la máquina:** worker11 trabajaba en paralelo (Dockerfile y documentación
del contenedor). No compartimos un solo fichero, pero **la máquina no estaba
despejada**: los milisegundos de este informe son orientativos y ninguna conclusión
depende de ellos. Lo que se publica son `rc`, bytes y recuentos, que son
deterministas.

**Intérprete:** `python.exe` de Windows 3.11.9. **Motores:** `ffmpeg N-121159` (local),
`magick 7.1.2 Q16-HDRI` (local), y `ffmpeg 8.1.1-4` + `ebook-convert` + `msgconvert`
dentro del contenedor `filex-convertx`.

---

## 0. Resumen

| | Antes | Ahora |
|---|---|---|
| Motivo de las 445 `no_materializable` | un solo string, falso para 73 | **53 de los 73 escritos, con su `rc`** |
| Semiaristas de entrada de esos 73 | `indeterminada` | **26 vivas, 27 muertas** (318 celdas de lectura) |
| Estrato indeterminado | 53,88 % (worker9) | **46,78 %** |
| `chk` (residuo de C28) | «otro paradigma, no una bandera» | **escrito**, y el paradigma medido |
| `oeb` (residuo de C28) | «escribe un directorio» (inferido) | **escribe un directorio** (medido) |
| `eml` (residuo de C28) | «escribe un directorio» | **refutado: nunca se ejecutó** |
| «otra build de ffmpeg», coste no medido | incógnita | **medido: cierra 3 de 13, coste 0 de red** |

**Todo lo de este informe son segundos de máquina.** El corpus FATE de ~1 GB que el
pendiente de `aristas-nominales.md` reclamaba **no hizo falta para una sola celda**.

---

## 1. Los 73: 53 escritos, y la partición predice cuáles — MEDIDO

La trampa 122 dice que las 445 entradas `no_materializable` comparten un motivo único
y que para 73 es falso, porque `materializa()` sólo intenta con ffmpeg si el token
está en `viva_ff_out`. worker9 partió esos 73 en tres grupos. **Reproducir su
partición fue el control previo** (t.58) y da 54 / 14 / 5 exactos.

Escalera, con parada al primer éxito y **4 semillas** por nivel (`video_cif` 352×288,
`audio48` estéreo, `subtitulo` SRT, `jpeg_exif`):

| Pasada | Qué invoca | Escritos | Acumulado |
|---|---|---:|---:|
| 1 | `-f <muxer>` y, si falla, por extensión | **36** | 36 |
| 2 | remedio dirigido por el `rc` | **+10** | 46 |
| 3 | el mismo remedio **con `-f <muxer>`** | **+7** | **53** |

**338 celdas en 30 s** la pasada 1; las otras dos, 5 s entre ambas. Cada celda con su
`argv`, su `rc`, sus bytes, su directorio desechable propio y el censo del directorio
antes y después (t.21).

### 1.1 El reparto por grupo es el hallazgo, no el total — MEDIDO

De la pasada 1, **los 36 escritos son los 36 del grupo «nunca probado»**:

| Grupo de worker9 | n | escritos en la pasada 1 |
|---|---:|---:|
| **nunca se probó como destino** | 54 | **36** |
| se probó como destino y salió muerto | 14 | **0** |
| se intentó y falló | 5 | **0** |

**El motivo falso estaba exactamente donde no hubo sonda, y sólo allí.** Es la
predicción de la trampa 122 confirmada por ejecución: *«no se pudo» y «no se intentó»
se escriben igual, y aquí se separan con 338 invocaciones*.

### 1.2 El `rc` dirigió los remedios, y son los mensajes del propio motor

Ninguna bandera de la pasada 2 sale de la documentación de ffmpeg: **todas salen del
`stderr` medido en la pasada 1**, que este arnés guarda **completo** (C28 lo truncó a
400 caracteres y tuvo que volver a correr 8 celdas).

| Token | Mensaje medido | Remedio | Resultado |
|---|---|---|---|
| `daud` | `Invalid number of channels 1, must be exactly 6` | `-ac 6 -ar 96000` | 1 728 192 B |
| `mmf` | `Unsupported sample rate 48000, supported are 4000, 8000, 11025, 22050 and 44100` | `-ar 44100 -ac 1` | 22 619 B |
| `filmstrip` | `only AV_PIX_FMT_RGBA is supported` | `-pix_fmt rgba` | 10 137 636 B |
| `gxf` | `gxf muxer only accepts PAL or NTSC resolutions` | `-s 720x480 -r 30000/1001 -c:v mpeg2video` | 262 052 B |
| `3gp`, `3g2` | `libopencore_amrnb ... Error while opening encoder` | `-c:v libx264 -c:a aac` | 18 698 B |
| `amr` | ídem | `-ar 8000 -ac 1 -b:a 12.2k` | 1 638 B |
| `g723_1`, `g726`, `g726le`, `alp`, `roq`, `dv`, `truehd` | restricción de tasa, geometría o `-strict` | ver `remedios_ff.py` | escritos |

### 1.3 Reproduce C28 al pie de la letra — control positivo

`firmas-cierre.md` §4.4 publicó tres banderas concretas. Ejecutadas aquí, en otra
tanda y con otro arnés:

| Formato | Banderas de C28 | ¿escribe? | bytes |
|---|---|:--:|---:|
| `dnxhd` | `-s 1920x1080 -b:v 36M -pix_fmt yuv422p` | **sí** | 4 710 400 |
| `dts` | `-strict -2` | **sí** | 177 096 |
| `mlp` | `-strict -2 -ar 48000` | **sí** | 35 060 |

Y **`truehd` cae con las mismas banderas que `thd`**, que es su extensión: el par que
C28 escribió 2/2 se completa.

### 1.4 Un defecto MÍO, y la diferencia entre dos pasadas es el dato

La pasada 2 compone `ffmpeg -i SEM <remedio> <dest>` y **pierde el `-f <muxer>`** que
la pasada 1 sí llevaba. Diez tokens la pasaron igual porque su extensión coincide con
el nombre del muxer; los demás devolvieron
`Error initializing the muxer ...: Invalid argument`.

**Con el `-f` puesto y sin tocar una sola bandera del remedio, siete pasan de EINVAL a
escritos:** `alp`, `daud`, `filmstrip`, `g723_1`, `g726`, `g726le`, `truehd`.

> **No es un segundo intento del problema: es un arnés incompleto.** Las dos pasadas
> se publican enteras porque **la diferencia entre ellas mide cuánto vale la regla
> «fuerza el muxer»** de `CLAUDE.md` §5: **7 de 12 celdas**, sobre remedios que ya
> eran correctos. Un remedio que se mide sobre una invocación distinta de la que ya
> funcionaba no está midiendo el remedio.

### 1.5 Los 20 que no se escriben, por clase — MEDIDO

| Clase | n | Tokens | Qué haría falta |
|---|---:|---|---|
| `AVERROR_ENCODER_NOT_FOUND` | **13** | `ac4 aea avs3 bit cavsvideo codec2 codec2raw evc gsm ilbc oma vc1 vc1test` | otra build (§3) |
| sin codificador de **subtítulo** | **4** | `jacosub mcc microdvd scc` | un codificador que esta build no trae |
| exige entrada de **mapa de bits** | **1** | `sup` | una entrada, no una bandera |
| **destino de red, no fichero** | **2** | `rtsp sap` | nada: no es una conversión de fichero |

**Los 4 de subtítulos son un `ENCODER_NOT_FOUND` disfrazado de `EINVAL`.** El `rc` de
la pasada 1 decía `Output file does not contain any stream`, que se lee como una
invocación mal construida; forzando `-c:s` el motor responde
`Error selecting an encoder`. Sondeado en ejecución, `ffmpeg -encoders` sólo trae
**11 codificadores de subtítulo** y ninguno es `microdvd`, `jacosub`, `eia_608` ni
`hdmv_pgs_subtitle`. **Amplía la trampa 72: `EINVAL` no siempre es «la invocación no
cumplía», a veces es «el codificador no está» con otro traje.**

---

## 2. La segunda mitad, que es la que mueve aristas: LEER

Materializar no basta. En `_agrega.py` una semiarista de entrada sale del estrato
indeterminado **sólo si además se lee**. Las 53 muestras se convirtieron a
`mkv`/`wav`/`png` con la invocación del censo (que replica el adaptador de ConvertX),
y con una segunda vuelta forzando el demuxer. **318 celdas, 25 s.**

| Columna | Vivas | Qué significa |
|---|---:|---|
| **nominal** (`ffmpeg -i m.tok x.mkv`) | **26 de 53** | lo que ConvertX ejecutaría — **es la que decide el grafo A** |
| demuxer forzado (`ffmpeg -f tok -i ...`) | 48 de 53 | si el formato es legible siquiera |

**Los 22 de diferencia son, los 22, formatos CRUDOS**: `alaw`, `mulaw`, `s8`…`s32be`,
`u8`…`u32le`, `f32le`, `f32be`, `g726`, `g726le`, `filmstrip`, `vidc`. No llevan
cabecera, así que ffmpeg no puede adivinar frecuencia, canales ni profundidad. **Es un
resultado limpio y no una laguna**: un `.s16le` suelto no es autodescriptivo, y una
conversión que dependa de adivinarlo no debería declararse viva.

**Cinco no se leen ni forzando**, y dos de ellos por un límite declarado de mi arnés:

| Token | Por qué |
|---|---|
| `ffmetadata` | es un volcado de metadatos: `Output file does not contain any stream`. Muerta legítima |
| `rawvideo` | necesita además `-pix_fmt` y `-s`; el demuxer solo no basta |
| `rtp` | necesita el SDP, que va aparte |
| `hls`, `dash` | **límite del arnés, no del formato**: la muestra guardada es el `.m3u8`/`.mpd`, y sus segmentos (`m0.ts`, `chunk-stream*.m4s`) se quedaron en el desechable. **No afirmo que sean ilegibles** |

---

## 3. La deuda de «otra build de ffmpeg» deja de ser una incógnita — MEDIDO

`firmas-cierre.md` §8.2 la dejó escrita como recurso externo *«~1 GB de FATE, o
compilar ffmpeg con más codificadores»*, y el encargo pedía decir con esas palabras si
seguía sin poder medirse. **Sí se puede medir, y el coste es cero de red:** hay una
segunda build de ffmpeg ya instalada en esta máquina, dentro de `filex-convertx`
—**8.1.1-4 de Debian** frente a **N-121159** en Windows—.

Los 13 `AVERROR_ENCODER_NOT_FOUND`, ejecutados **dentro** del contenedor con el tope
dentro de la orden:

| Resultado | n | Tokens |
|---|---:|---|
| **se escriben en Debian y no en Windows** | **2** | `codec2` (182 B), `codec2raw` (175 B) |
| se escribe con un remedio de parámetros | **1** | `gsm` — allí hay `libgsm`, y el fallo era `Error while opening encoder`, no «not found»; con `-ar 8000 -ac 1` da **1 650 B** |
| siguen sin codificador en las dos builds | **10** | `ac4 aea avs3 bit cavsvideo evc ilbc oma vc1 vc1test` |

> **La deuda valía 13 y vale 10.** Y `gsm` enseña otra vez lo de la trampa 72 por el
> otro lado: **«Encoder not found» y «Error while opening encoder» son dos cosas
> distintas**, y agruparlas compra el remedio caro. Los 5 de subtítulos también se
> probaron dentro: fallan igual, así que **no son un defecto de la build de Windows**.

**Lo que sigue PENDIENTE, y lo digo con esas palabras:** para los 10 restantes **no
está medido** qué build los traería. No he descargado FATE ni compilado ffmpeg. Lo que
sí queda medido es que **la segunda build más obvia y ya disponible no los trae**, así
que la deuda ya no se puede pagar con «prueba en otro sitio»: exige una build
construida a propósito, y ese coste sigue sin medir.

---

## 4. Los dispositivos de Linux: son NUEVE, no diez — REFUTADO

El encargo hablaba de «los 10 dispositivos de Linux». worker9 los dejó quietos a
propósito, y con razón: clasificar por el **nombre** es el error que su propio informe
corrige. Preguntado al ffmpeg que sí los conoce, con `docker exec` y no deduciendo:

| Token | `-devices` | `-demuxers` | `-muxers` | Veredicto |
|---|:--:|:--:|:--:|---|
| `alsa`, `fbdev`, `oss`, `pulse`, `video4linux2` | `DE` | — | `Ed` | **dispositivo** |
| `iec61883`, `jack`, `kmsgrab`, `x11grab` | `D` | — | — | **dispositivo** |
| `awb`, `pp`, `sndio` | — | — | — | **tampoco los conoce esta build** |

**Son 9 dispositivos confirmados por ejecución, no 10.** `sndio` no está compilado en
el ffmpeg de Debian, así que **no puedo confirmarlo y no lo cuento**; `awb` es una
extensión (AMR-WB) y `pp` es `libpostproc`, y ninguno de los dos es un dispositivo.
**Se retiran los 9 y sólo los 9**, con la misma regla que worker9 aplicó a `lavfi` y
`openal`: el origen no es un fichero, luego la arista no existe.

### 4.1 Y refuto media frase de worker9 — MEDIDO

worker9 refutó al maestro con esto, y acertó en lo esencial: *«`hls`, `dash`, `rtp`,
`rtsp` y `mpjpeg` parecen protocolos por el nombre y son formatos de fichero que
ffmpeg **escribe**»*. Ejecutados:

| Token | ¿escribe un fichero? | bytes |
|---|:--:|---|
| `hls` | **sí** | 112 B de `.m3u8` **+ `m0.ts`**, 21 920 B en total |
| `dash` | **sí** | 1 881 B de `.mpd` **+ 4 segmentos**, 21 047 B |
| `rtp` | **sí** | 96 172 B |
| `mpjpeg` | **sí** | 163 537 B |
| `rtsp` | **NO** | `rc=-5`, 0 bytes |
| `sap` | **NO** | `rc=-5`, 0 bytes |

**Acierta en 4 de 6**, no en los 5 que enumeró. `rtsp` y `sap` están en `-muxers`
—luego «son muxers» es cierto— pero **no escriben un fichero**: su destino es una URL
de red, y ninguno de los dos aparece en la lista de protocolos de **salida**. La
distinción que faltaba no es «protocolo contra formato», es **«tiene destino de
fichero» contra «no lo tiene»**.

> Y de propina, para el quinto punto del contrato: **`hls` y `dash` escriben ficheros
> que nadie pidió** —un `.ts` y cuatro `.m4s` junto al destino declarado—. El censo
> por celda los vio porque lista el desechable antes y después (t.21). **Son dos
> destinos más de la familia del `ffmpeg -i x out.mpd` que ya motivó el punto 5.**

---

## 5. `clip` y `mask`: ImageMagick los declara `rw+` y no son formatos — MEDIDO

worker9 los dejó en `im_pseudo_operador` con el motivo *«consume un fichero o una
imagen: NO se reclasifica»*. **El hecho es cierto y ahora hay mecanismo:**

| Caso | `rc` | Mensaje | Veredicto |
|---|:--:|---|---|
| `magick tipico.png m.clip` | 1 | `image does not have a clip mask @ error/clip.c/WriteCLIPImage/234` | no escribe |
| `magick tipico.png -clip m.clip` | 1 | `no clip path defined ... ClipImagePath/730` | no escribe |
| `magick alpha.png -clip m.clip` | 1 | ídem, también con alfa real | **no escribe** |
| `magick tipico.png m.mask` | 1 | `image does not have an mask channel @ WriteMASKImage/353` | no escribe |
| `magick alpha.png -alpha extract m.mask` | 1 | ídem | no escribe |
| **`magick alpha.png -write-mask alpha.png m.mask`** | **0** | — | **escribe** |

**Los dos son volcados de un metadato, no formatos de fichero:** escriben la
trayectoria de recorte y el canal de máscara *de la imagen de entrada*, y sólo existen
si la entrada los trae. Es **exactamente la clase «metadato, no formato»** que C28
identificó para 8 destinos (`No 8BIM / APP1 / IPTC / color profile data is
available`), y nadie había cruzado las dos listas.

`mask` **sí es escribible** activando la máscara (`-write-mask`), así que su
semiarista de entrada es materializable; `clip` **no**, porque ninguna imagen del
corpus tiene trayectoria de recorte. Usé `alpha.png` y no `tipico.png` para el caso de
alfa por la trampa 1: el alfa de `tipico.png` es enteramente opaco.

---

## 6. El residuo de `C28`: las tres celdas

### 6.1 `chk` — se escribe, y el paradigma queda medido

`fate-y-aristas.md` §1.2 lo dejó fuera con un motivo correcto —*«no es una bandera, es
otro paradigma de invocación»*— pero **en la ronda 11 no se ejecutó**: vivía en el
diccionario `OTRO_PARADIGMA`, fuera del bucle que invoca. Aquí se ejecuta.

| Caso | `rc` | Ficheros | bytes |
|---|:--:|---|---:|
| un solo fichero de salida (lo que el censo hizo) | −22 | 0 | 0 |
| cabecera + trozos, con las dos pistas | −22 | 0 | 0 |
| **`-map 0:v:0 -an -c:v libvpx -f webm_chunk -header h.chk -chunk_start_index 1 m_%d.chk`** | **0** | `h.chk`, `m_1.chk` | **22 777** |
| **la variante de audio** (`-map 0:a:0 -vn -c:a libvorbis`) | **0** | `ha.chk`, `a_1.chk` | **6 383** |

**`webm_chunk` es escribible.** Lo que faltaba, y el `stderr` lo decía
(`Output file does not contain any stream`), era **darle una sola pista**. Y el
veredicto de C28 se confirma en lo que importa: **la salida son N ficheros, no uno**,
así que el contrato de «un fichero de destino» sigue sin aplicarle. **La celda se
cierra: no como «inescribible», sino como «escribible fuera del molde de un destino
único», y ahora con `rc`, ficheros y bytes en vez de con una nota.**

### 6.2 `oeb` — la inferencia era correcta, y ahora está medida

C28 lo clasificó «el motor escribe un directorio», y esa palabra era **una inferencia
de su clasificador**: lo único registrado era `rc=0` y ausencia de fichero regular,
porque su arnés sólo miraba `os.path.isfile`. Ejecutado con Calibre dentro del
contenedor y **listando el directorio**:

```
RC=0
--- que es salida.oeb --- DIRECTORIO
content.opf 1614 · cover_image.jpg 46695 · index.html 400 · page_styles.css 51
page_styles1.css 166 · stylesheet.css 334 · titlepage.xhtml 787 · toc.ncx 479
--- cola del log --- OEB output written to /tmp/c50/salida.oeb
```

**Ocho ficheros, `rc=0`, y el propio Calibre escribe «OEB output written to».**
Confirmada por observación. El remedio que C28 proponía —tratar el destino como
directorio— es el correcto.

### 6.3 `eml` — REFUTADO: no escribe un directorio, es que nunca se ejecutó

**Su clase salió del valor por defecto de un clasificador ante una lista de errores
vacía.** `_c28_los56.py` asigna «rc=0 y sin fichero → el motor escribe un directorio»
cuando el texto de errores está vacío, y el de `eml` **estaba vacío porque nadie lo
midió**: `eml` no aparece ni en `firmas_censo_local.json` ni en
`firmas_censo_contenedor.json`. No hay `rc`, ni `stderr`, ni bytes.

Y al ir a medirlo aparecen **dos** correcciones más:

1. **`msgconvert` SÍ está en el contenedor**: `/usr/bin/msgconvert`. `bench/docker.md`
   §198 dice que el arranque de ConvertX *«declara ausentes `dasel` y `msgconvert`»* —
   lo declarará, pero el binario está.
2. **Y está roto.** `msgconvert --help` devuelve **`rc=2`**:
   `Can't locate Email/Address.pm in @INC (you may need to install the Email::Address
   module) ... BEGIN failed--compilation aborted at /usr/bin/msgconvert line 8.`

> **El estado real de `eml` no es ninguno de los dos que se le habían puesto.** No es
> «el motor escribe un directorio» y tampoco es «el motor no está»: es **motor
> presente e inoperante por una dependencia de Perl que falta**, con su `rc` y su
> mensaje. Es la trampa 122 **en el eje de SALIDA**, y peor: allí el valor por defecto
> era un string de motivo, y aquí es una **clase de remedio**, que es lo que alguien
> habría ido a implementar.

---

## 7. El número corregido del estrato, con su derivación

**Dos controles antes de mover nada** (t.58), y los dos con `assert` en el código:

| Control | Esperado | Medido |
|---|---|---|
| la agregación original de `_agrega.py` | 138 501 / 40 252 / 22 235 / 75 874 / 140 | **coincide** |
| el recuento de worker9 (`C49`) | 135 535 / 73 030 indeterminadas | **coincide** |

`aristas_A.json` **estaba podado con su orden** (t.95): se reconstruyó con
`rehace_aristas.py`, copiado a mi directorio como manda `CLAUDE.md` §1, y devuelve las
138 501 exactas sin ejecutar un motor.

Se aplican **dos** cambios, y sólo dos:

**(a) Retirar** de la población los 9 dispositivos de Linux. Misma regla de worker9:
una arista sale sólo si **todos** sus motores la declaran desde un origen que no es un
fichero. **−1 818 aristas.**

**(b) Mover** de `indeterminada` a `viva`/`muerta` los 53 tokens materializados **y
leídos**, con el estado que dicta la columna nominal.

| | Original | worker9 (`C49`) | **C50** |
|---|---:|---:|---:|
| Población | 138 501 | 135 535 | **133 717** |
| Vivas | 40 252 (29,06 %) | 40 252 (29,70 %) | **44 641 (33,38 %)** |
| Refutadas por ejecución | 22 235 | 22 113 | **26 379** |
| **Indeterminadas** | **75 874 (54,78 %)** | **73 030 (53,88 %)** | **62 557 (46,78 %)** |
| Otro motor | 140 | 140 | 140 |

> ### El 53,88 % pasa al **46,78 %**: **7,10 puntos y 10 473 aristas**, frente a los 0,90 puntos de `C49`.

**Y la aritmética dice por qué es tan distinto de la corrección de worker9.** La suya
retiraba 16 tokens de la **población**, y cada token retirado sólo multiplica por las
salidas vivas de su motor. La mía **reclasifica 53 tokens de ENTRADA**, y cada uno
multiplica por las 202 salidas declaradas: por eso una corrección del mismo tamaño en
tokens vale ocho veces más en aristas. **`ff_declarado_muxer` era el 16,13 % del
estrato y se ha cerrado entero.**

### 7.1 Control de sensibilidad: la columna elegida no toca el estrato

Si el grafo decidiera con el **demuxer forzado** en vez de con la invocación nominal:

| | C50 (nominal) | C50 (forzado) |
|---|---:|---:|
| Vivas | 44 641 | 48 359 (**+3 718**) |
| Indeterminadas | **62 557** | **62 557** (igual) |

**La elección de columna reparte viva/muerta y no mueve el estrato ni una arista**,
porque las dos columnas materializan los mismos 53 tokens. Publico las dos: el 46,78 %
es robusto a esa decisión, y los 3 718 son el precio de que ffmpeg no pueda adivinar
los parámetros de un fichero crudo.

---

## 8. Lo que refuto

1. **El encargo: «los 10 dispositivos de Linux».** Son **9** confirmados por
   ejecución. `sndio` no está compilado en la build que podía confirmarlo, y `awb` y
   `pp` no son dispositivos (§4).
2. **worker9: «`hls`, `dash`, `rtp`, `rtsp` y `mpjpeg` son formatos que ffmpeg
   escribe».** Acierta en **4 de 6** medidos: `rtsp` y `sap` están en `-muxers` y **no
   escriben un fichero** (§4.1).
3. **C28: «`eml` y `oeb`: el motor escribe un directorio».** Cierto y ahora **medido**
   para `oeb`; **falso para `eml`**, que nunca se ejecutó (§6.3).
4. **C28: `chk` no se puede cerrar con una invocación.** Su diagnóstico era correcto y
   su celda **sí se puede ejecutar**: se escribe (§6.1).
5. **«El coste de otra build de ffmpeg no está medido».** Ya lo está para 3 de los 13,
   con coste 0 de red (§3). Para los 10 restantes **sigue sin medirse**, y lo digo con
   esas palabras.
6. **Dos defectos míos**, corregidos antes de publicar: la pasada 2 perdió el `-f`
   (§1.4), y `timeout <builtin>` devolvió `127` haciendo que Calibre pareciera ausente
   (§9).

---

## 9. Lo que casi publico mal — tres defectos de instrumento

1. **Windows devuelve el `rc` de ffmpeg SIN SIGNO.** `4294967274` es `−22`. Sin
   convertirlo, mi clasificador del `rc` no reconocía **ni un solo `AVERROR`** y los
   338 fallos habrían salido con la etiqueta `otro_rc_4294967274`, que es la pinta
   exacta de «no sé qué pasó». Se detectó en la calibración, antes de la tanda.
2. **`timeout <builtin>` devuelve 127.** Componer el tope como
   `sh -c "timeout N cd /tmp/... && ..."` hace que `timeout` intente ejecutar `cd`
   como binario. La celda de `oeb` publicó `RC=127 ... NO_EXISTE`, **indistinguible de
   «Calibre no está en el contenedor»** — y Calibre estaba: la orden anterior, que
   empezaba por `rm`, había escrito un epub de 20 721 B. Se corrige con
   `timeout N sh -c '<orden>'`. **Es la trampa 25 en el arnés del contenedor.**
3. **Una sonda de `-encoders` que devolvía `None` en 13 de 13.** Era la firma de la
   trampa 66. Con control positivo (`aac`, `libx264`, `pcm_s16le`, `flac`: los cuatro
   presentes de 226) resultó **cierta**, pero se sustituyó igual por **ejecutar** los
   13 en vez de mirarlos en una lista, que es la regla del proyecto.

**Huérfanos al terminar: 0.** `docker ps -a` da los mismos 5 contenedores del inicio y
ninguno nuevo; `tasklist` no encuentra ni un `ffmpeg.exe` ni un `magick.exe` vivo
(t.37, t.112). **Ficheros fuera del desechable: 0** — el censo por celda sólo vio
aparecer el log del propio arnés.

---

## 10. Lo que queda PENDIENTE

1. **Los 10 sin codificador en ninguna de las dos builds** (`ac4 aea avs3 bit
   cavsvideo evc ilbc oma vc1 vc1test`). **El coste de una build construida a
   propósito no está medido.** No lo estimo.
2. **`hls` y `dash` como ORIGEN**: la muestra que guardé es la playlist sin sus
   segmentos, así que su «muerta» es del arnés. Se cierra guardando el directorio
   entero, que es un cambio de arnés de tres líneas.
3. **`sup`** exige una entrada de subtítulo de mapa de bits, que el corpus no tiene.
   Es un remedio de **entrada**, igual que los 8 «metadato, no formato» de C28.
4. **`clip`** exige una imagen con trayectoria de recorte (perfil 8BIM). Ninguna del
   corpus la trae.
5. **`eml`**: falta medir si instalar `Email::Address` en el contenedor lo arregla, y
   cuánto cuesta. Es la misma forma que el «+50 MB y 28,1 s» de `qpdf`/`tesseract`.
6. **`sndio`** queda sin confirmar: ninguna de las dos builds disponibles lo trae, así
   que **no afirmo que sea un dispositivo** aunque lo parezca por el nombre — que es
   justo el error que este informe evita en §4.
7. **Las 53 muestras no se han pasado por el contrato.** Son 53 ficheros nuevos de
   formatos que el patrón oro no cubre, y saber cuántos superan los cinco puntos es
   otra ronda.

---

## 11. Cambios que propongo y NO he hecho

No he tocado `filex/`, `pruebas/`, `ESTADO-Y-REPARTO.md`, `CLAUDE.md` ni
`PLAN-ORQUESTADOR.md`, ni he sobrescrito las salidas de worker9.

### 11.1 En `bench/salidas-aristas/semi_entrada.json` — el arreglo de fondo

**No propongo editar el JSON medido**, sino cambiar quien lo escribe. En
`bench/salidas-aristas/_semi_in.py`, la función `materializa()` devuelve
`(None, "no materializable (ningun motor local lo escribe)")` sin haber intentado
nada cuando el token no está en `viva_ff_out`. **El estado negativo tiene que decir
qué se intentó** (t.122). Sitio exacto: el `return` final de `materializa()`, que pasa
a devolver un diccionario en vez de un string:

```python
return None, {"motivo": "no materializable",
              "ffmpeg_declara_muxer": a in MUXERS,     # de `ffmpeg -muxers`
              "ffmpeg_intentado": a in viva_ff_out,
              "magick_intentado": a in viva_im_out}
```

Con eso, **el fallo se ve el día del censo y sin ejecutar un motor**: 73 filas dirían
`declara_muxer=True, intentado=False`.

### 11.2 En `ci/integridad.py` — aviso de entrega

La comprobación `informes-registrados` exige que todo `.md` de `bench/` figure en
`ESTADO-Y-REPARTO.md`, y **el encargo me prohíbe editarlo**. Así que esta entrega deja
esa comprobación en rojo hasta que se pegue **una línea**. Texto propuesto para la
tabla de §1:

```
| C50 | `bench/aristas-escribibles.md` | worker10 | 🟢 | 53 de 73 tokens escritos con su `rc`; el estrato indeterminado baja del 53,88 % al 46,78 % |
```

### 11.3 Trampa 125 propuesta

> 125. **Un remedio hay que medirlo sobre la invocación que YA funcionaba, o lo que
> mides es la invocación nueva — MEDIDO el 04/09** (`bench/aristas-escribibles.md`
> §1.4). La pasada 1 de `C50` escribía con `ffmpeg -i SEM -f <muxer> dest`; la pasada
> 2 añadió los remedios que el `stderr` dictaba y, al recomponer el `argv`, **perdió
> el `-f <muxer>`**. Diez tokens la pasaron igual —su extensión coincide con el nombre
> del muxer— y **los otros doce devolvieron `EINVAL` con `Error initializing the
> muxer`, que se lee como «el remedio no sirve»**. Con el `-f` puesto y **sin tocar
> una sola bandera del remedio, siete pasan de `EINVAL` a escritos**: `alp`, `daud`,
> `filmstrip`, `g723_1`, `g726`, `g726le` y `truehd`. El modo de fallo es el peor
> posible, porque el veredicto equivocado es *«esta clase no tiene remedio»*, que es
> una conclusión que nadie vuelve a mirar. Es la trampa 79 —*comprueba que lo que
> mediste es lo que el código ejecuta*— movida de una cifra de control a un `argv`, y
> la 75 por el otro lado: allí las banderas no se transferían entre motores, aquí **se
> perdió la bandera que no era del remedio sino del molde**. **Cuando pruebes un
> remedio, hazlo por DIFERENCIA sobre la invocación anterior —añade, no recompongas—,
> y publica las dos pasadas: la diferencia entre ellas es el dato.**

---

## 12. Cómo se reproduce

```sh
cd bench/salidas-aristas-escribibles
python rehace_aristas_copia.py   # reconstruye aristas_A.json sin ejecutar motores
python escribe_ff.py             # pasada 1: 338 celdas, ~30 s
python remedios_ff.py            # pasada 2
python remedios2_ff.py           # pasada 3
python contenedor2.py            # dispositivos, otra build, oeb, msgconvert
python cierres.py && python cierres2.py   # chk, clip, mask, gsm, eml
python lectura.py                # 318 celdas de lectura, ~25 s
python recuento50.py             # el número, con sus dos controles
```

Todo junto: **menos de dos minutos de máquina**, sin red y sin GPU.
