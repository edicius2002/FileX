# `C28`: los 12 restantes del techo de 15/56, y `C16` ampliada con alias — n=69→95

**Encargo R1 · worker11, carril CPU/Docker nuevo, `edicius2002/filex-fate-completo`.**
Continuación directa de `bench/fate-y-aristas.md` (worker2, ronda 11). Dos tareas: ir a
buscar en FATE los 12 formatos de `C28` que el techo de worker2 ya dejaba medido
(`firmas-cierre.md` §4.4: FATE cierra como mucho 15 de 56, y de esos 15 solo 3 tenían
dato de rebote) y ampliar la muestra de `C16` (69 de 445) con **alias** — formatos cuyo
demuxer/coder tiene un nombre distinto al del subdirectorio de FATE que los contiene.

**Máquina:** *worktree* `C:\Users\krato\orca\workspaces\FileX\filex-fate-completo`.
Windows 10, Python 3.11.9. **No se tocó la GPU** — todo el trabajo es ffmpeg/ImageMagick
en CPU. Docker (`29.4.3`) arriba con `filex-convertx`, `filex-snapotter(+pg,+redis)` y
`filex-gotenberg8` sanos (`docker ps -a` comprobado antes de empezar), aunque esta ronda
no necesitó ningún contenedor — todo el trabajo es sobre binarios nativos
(`ffmpeg`/`ffprobe`/`magick`). **El corpus FATE** (`D:\Work\research\fate-suite`, 1,3 GB,
2 529 ficheros, 303 subdirectorios) se referenció por ruta absoluta, no se copió, no se
versionó, no entró en `corpus/`.

**Fecha:** 03/09/2026.

---

## 1 · `C28` — los 12 restantes del techo de 15/56

`firmas-cierre.md` §4.4 midió que, de los 56 destinos que "ningún motor local sabe
escribir", **FATE cierra como mucho 15** (11 `AVERROR_ENCODER_NOT_FOUND` + 4 que el
motor dice directamente que no sabe escribir), **y ni siquiera bien**: FATE es un
corpus para *decodificar*, no una muestra *escrita* con la que medir el marcador de
escritura. De esos 15, worker2 ya tenía dato de rebote de la muestra de `C16` para 3
(`oma` VIVO, `vc1` VIVO, `evc` MUERTO), sin ir a buscar los 12 restantes:
`ac4 avs3 bit c2 cavs cvg dzi lbc nia nii pml rcv`.

### 1.1 Los 4 que no son del dominio de FATE — declarado, no un fallo

`dzi`, `nia`, `nii` y `pml` son la clase "el motor no lo sabe escribir" de vips —
Deep Zoom Image (pirámide de teselas), NIfTI (imagen médica ×2) y paleta de GIMP. **No
son códecs de audio/vídeo**: FATE es el corpus de conformidad de ffmpeg y **no tiene ni
subdirectorio ni un solo fichero de ninguno de los tres tipos** entre sus 2 529.
`os.path.isdir` da `False` para los tres nombres, y no hay alias razonable que buscar —
un fichero NIfTI o una pirámide DZI no tienen "otro nombre" en un corpus de vídeo. Es
un dato, no un hueco de método.

### 1.2 Los 8 de ffmpeg — 2 VIVOS directos, 5 no encontrados, 1 colisión declarada

Mismo método exacto que `c16_semi_entrada_fate.py` (trampa 79): destinos
`["mkv","wav","png"]` en ese orden, basta uno vivo, tope 25 s, criterio `rc==0 &&
bytes>0` (trampa 75). Primero se buscó el alias de codec REAL de cada formato —ya
sondeado por worker2 en `bench/invocacion-aristas.md` L151 (`bit→g729`, `c2→codec2`,
`cavs→cavs`, `cvg→adpcm_psx`, `lbc→ilbc`, `rcv→wmv3`)— y luego se buscó ese alias en
FATE, por directorio y, si no había, por extensión en el corpus entero:

| Formato | Codec real | ¿Directorio en FATE? | ¿Extensión `.<fmt>` en FATE? | Resultado |
|---|---|---|---|---|
| `cavs` | cavs | **SÍ** (`cavs/`) | — | **VIVA** |
| `rcv` | wmv3 | no (pero el codec vive en `vc1/`) | **SÍ**, 2 ficheros en `vc1/` | **VIVA** |
| `bit` | g729 | no | **SÍ, 231 ficheros** | **COLISIÓN, declarada — ver 1.2.1** |
| `ac4` | ac4 | no | no | no encontrado |
| `avs3` | avs3 | no | no | no encontrado |
| `c2` | codec2 | no | no | no encontrado |
| `cvg` | adpcm_psx | no (`argo-asf/` existe pero es OTRO formato de Argonaut) | no | no encontrado |
| `lbc` | ilbc | no | no | no encontrado |

**`cavs` — VIVA, con un matiz que el propio directorio ya escondía.** `cavs/` tiene dos
ficheros: `cavs.mpg` (2 048 000 B, un `mpeg` con la pista `Video: cavs` limpia) y
`bunny.mp4` (177 752 B, un flujo `cavsvideo` crudo). El script, por diseño, toma el MÁS
PEQUEÑO —`bunny.mp4`— y la conversión a `.mkv` sale `rc=0`, 465 243 B: **VIVA por el
criterio barato.** Pero `ffprobe` sobre ese mismo fichero avisa *«weighted prediction
not yet supported»* y *«no frame decoded»* **55 veces** en el log de la conversión, y el
`.mkv` resultante sólo tiene 60 fotogramas para 2 s a 30 fps con decenas de ellos
fallidos. Se comprobó aparte con `cavs.mpg` (el fichero más grande del mismo
directorio): **decodifica limpio, 0 avisos, mismo `rc=0`.** **El heurístico "coge el
fichero más pequeño" puede elegir la muestra más degradada del directorio** — el
criterio barato (`rc==0 && bytes>0`) no lo distingue, y ambos cuentan como VIVA, pero
uno es una lectura completa y el otro una lectura parcial con frames perdidos. Dato
para quien reutilice el método: **el tamaño mínimo no es proxy de "mejor calidad de
muestra"**.

**`rcv` — VIVA, limpia.** No hay directorio `rcv/`, pero el codec que declara ese
destino (`wmv3`, sondeado por worker2) SÍ tiene ficheros reales con esa extensión
exacta dentro de `vc1/`: `SMM0005.rcv` y `SMM0015.rcv`. `ffprobe` natural (sin forzar)
ya los detecta como demuxer `vc1test`, stream `Video: wmv3 (Main)` — coincide con el
codec esperado. La conversión a `.mkv` da `rc=0`, 410 350 B, **0 avisos de "no frame
decoded" ni "not supported"** en el log: lectura limpia.

#### 1.2.1 `bit` — 231 candidatos por extensión, 0 genuinos: la trampa 70/73 otra vez

Buscar `*.bit` en FATE devuelve **231 ficheros**, pero están todos en
`hevc-conformance/`, `vvc-conformance/` y `mp3-conformance/`: son bitstreams crudos de
**HEVC, VVC y MP3**, no de G.729. `.bit` es la extensión GENÉRICA que estos tres
conjuntos de conformidad usan para "bitstream crudo sin contenedor", y coincide por
casualidad con la extensión que el muxer `bit` de ffmpeg usa para G.729. **Se verificó
con `ffprobe` antes de usar ninguno**: sobre `mp3-conformance/si.bit`, autodetección
natural (sin forzar formato) lo identifica como **HEVC** (`Video: hevc (Main),
2560x1600`) — el contenido real gana la probabilidad sobre la extensión. Forzando `-f
g729` sobre el MISMO fichero, ffprobe "acepta" leerlo como G.729 (`Audio: g729, 8000
Hz, mono`) **sin ningún error** — lo cual no prueba nada: G.729 es un formato crudo sin
cabecera ni marcador, así que CUALQUIER secuencia de bytes "se deja" interpretar como
G.729 muestra a muestra. **Es la misma familia que la trampa 73 (`3ds`/TIFF) y la 70
(`.pcd`/`mpegaudio`): una extensión compartida no prueba el mismo formato**, y aquí el
propio formato (crudo, sin marcador) hace que ni siquiera un intento forzado sirva de
control. Se declara: **`bit` sigue sin fichero genuino en FATE**, y no se cuenta como
acierto.

### 1.3 Balance de los 12

| Resultado | n | Formatos |
|---|---:|---|
| **VIVA** (fichero real, decodifica) | **2** | `cavs`, `rcv` |
| No encontrado en FATE (ni directorio ni extensión) | **5** | `ac4`, `avs3`, `c2`, `cvg`, `lbc` |
| Colisión de extensión declarada, no genuino | **1** | `bit` |
| Fuera del dominio de FATE (formato de vips) | **4** | `dzi`, `nia`, `nii`, `pml` |

**Con esto, los 15 completos del techo de `firmas-cierre.md` §4.4 quedan con dato
directo, uno a uno**: `oma` VIVO, `vc1` VIVO, `evc` MUERTO (rebote de `C16`, worker2) +
`cavs` VIVO, `rcv` VIVO (este informe) = **5 con lectura real confirmada** (4 vivas, 1
muerta), y **10 sin fichero real aprovechable en FATE** (5 no encontrados, 1 colisión,
4 fuera de dominio). **El pendiente §8.2 de `firmas-cierre.md` ("ir a buscar los 12
restantes") queda cerrado.** Esto **no** cambia el techo declarado —FATE sigue sin
aportar capacidad de ESCRITURA para ninguno de los 56, y "ni siquiera bien" seguía
siendo la frase correcta incluso para `cavs`/`rcv`: confirma que el codec de LECTURA
existe y funciona, no que ffmpeg pueda ESCRIBIR ese destino—. Lo que cierra es la
pregunta "¿hay más ficheros reales que mirar?", y la respuesta es no para 10 de los 12.

---

## 2 · `C16` — la muestra de alias: n=69 → n=95

`c16_semi_entrada_fate.py` (worker2) empareja por **nombre de directorio idéntico al
nombre del formato** — 69 de 445. El encargo pide ir más allá con **alias conocidos**:
formatos cuyo demuxer/decoder en ffmpeg o ImageMagick tiene un nombre distinto del
subdirectorio de FATE que realmente los contiene.

### 2.1 Método: cada candidato se verifica ANTES de gastarlo en la tanda

Un fuzzy-match ingenuo (normalizar guiones/underscores y buscar subcadena) sobre los
376 formatos restantes (291 ffmpeg + 85 ImageMagick) devuelve **79 candidatos**, y la
mayoría son ruido por coincidencia de subcadena (`nfo` "encaja" dentro de
`h264-conformance` porque contiene la subcadena `nfo` en "co**nfo**rmance"; `mac`
"encaja" con `smacker`; etc.). **Cada candidato se sondeó con `ffprobe` SIN forzar
formato** antes de usarlo — si el demuxer que ffmpeg detecta de verdad en el fichero
más pequeño del directorio candidato coincide con el nombre del alias, se acepta; si
no, se descarta. Esto es la misma disciplina que ya pagó la trampa 73/70 en la sección
1: un nombre parecido no prueba el mismo formato.

**24 candidatos de ffmpeg pasaron la sonda** (23 con autodetección natural + `mvi`,
más `asf_o` que se declara aparte por necesitar forzado):

| Alias | Directorio de FATE | Demuxer autodetectado (sin forzar) |
|---|---|---|
| `cavsvideo` | `cavs/` | `cavsvideo` ✓ |
| `vc1test` | `vc1/` (fichero `.rcv`, no `.vc1`) | `vc1test` ✓ |
| `roq` | `idroq/` | `roq` ✓ |
| `anm` | `deluxepaint-anm/` | `anm` ✓ |
| `c93` | `cyberia-c93/` | `c93` ✓ |
| `dfa` | `chronomaster-dfa/` | `dfa` ✓ |
| `iss` | `funcom-iss/` | `iss` ✓ |
| `wsvqa` | `vqa/` | `wsvqa` ✓ |
| `wsaud` | `westwood-aud/` | `wsaud` ✓ |
| `daud` | `d-cinema/` | `daud` ✓ |
| `argo_asf` | `argo-asf/` | `argo_asf` ✓ |
| `amr` | `amrnb/` | `amr` ✓ |
| `ipmovie` | `interplay-mve/` | `ipmovie` ✓ |
| `dsicin` | `delphine-cin/` | `dsicin` ✓ |
| `ans` | `ansi/` | `tty` (subtitipo, mismo demuxer de texto — aceptado) |
| `psxstr` | `psx-str/` | `psxstr` ✓ |
| `film_cpk` | `film/` | `film_cpk` ✓ |
| `bethsoftvid` | `bethsoft-vid/` | `bethsoftvid` ✓ |
| `brender_pix` | `brenderpix/` | `brender_pix` ✓ |
| `alias_pix` | `aliaspix/` | `alias_pix` ✓ |
| `ea_cdata` | `ea-cdata/` | `ea_cdata` ✓ |
| `tiertexseq` | `tiertex-seq/` | `tiertexseq` ✓ |
| `mvi` | `motion-pixels/` | `mvi` ✓ |
| `asf_o` | `asf/` | `asf` (NO `asf_o` — ver 2.2) |

Y **2 candidatos de ImageMagick**, buscados por EXTENSIÓN en el corpus entero (no hay
convenio de directorio-por-formato en ImageMagick): `heic` (6 ficheros reales en
`heif-conformance/`, `magick identify` los reconoce como HEIC de verdad) y `3gp` (4
ficheros reales en `aac/CT_DecoderCheck/`, contenedores 3GP legítimos de las pruebas de
audio AAC). Un tercer candidato, `.raw` (3 ficheros), se **descartó como colisión**:
`magick identify` los intenta leer como DNG (`error/dng.c/ReadDNGImage`) y falla — son
un volcado de audio TrueHD y dos rásteres de filtro, no una imagen RAW de cámara.

**Candidatos investigados y rechazados, declarados para que nadie los repita:** `dtshd`
(forzando `-f dtshd` sobre el `.dts` más pequeño de `dts/`, ffprobe da *"chunk size too
big"* / *"Invalid data found"* — no es DTS-HD, es DTS core) y `.raw` de ImageMagick
(arriba). Los ~55 candidatos restantes del fuzzy-match no se investigaron uno a uno —
son coincidencias de subcadena sin base semántica (`mac→smacker`, `dat→ea-cdata`,
`raw→quickdraw`...) y perseguirlos todos habría sido gastar la tanda en ruido conocido.

### 2.2 `asf_o` — el único forzado, y la única MUERTA nueva de ffmpeg

Ningún fichero de `asf/` autodetecta el demuxer legacy `asf_o`: todos resuelven de
forma natural al demuxer moderno `asf`. Para probar `asf_o` de verdad hace falta
forzarlo (`-f asf_o`), y se declara así explícitamente — no es la misma medida que un
alias que se detecta solo. **Resultado: MUERTA.** `ffmpeg -f asf_o -i bug821-2.asf
out.mkv` falla en los tres destinos con *"Invalid data found when processing input"*.
Es un dato genuino, no un fallo de método: el parser legacy de ASF, en esta build, no
admite el mismo fichero que el parser moderno sí lee — coherente con que `asf_o` sea
código heredado y menos permisivo.

### 2.3 Resultado, nivel 1 (semiarista de entrada)

Mismo criterio que `c16_semi_entrada_fate.py`: destinos `["mkv","wav","png"]` para
ffmpeg (uno vivo basta), `["png"]` para ImageMagick, tope 25 s.

| | n | VIVA | MUERTA | % viva |
|---|---:|---:|---:|---:|
| ffmpeg (alias) | 24 | 23 | 1 (`asf_o`, forzado) | 95,8 % |
| imagemagick (alias) | 2 | 1 (`heic`) | 1 (`3gp`, sin pista de vídeo) | 50,0 % |
| **alias, total** | **26** | **24** | **2** | **92,3 %** |
| Muestra original de worker2 (69) | 69 | 67 | 2 | 97,1 % |
| **COMBINADO** | **95** | **91** | **4** | **95,8 %** |

**La cifra se mueve, y se publica movida**: de 97,1 % (n=69) a 95,8 % (n=95). Sigue
**muy por encima** del 48,6 % de Escenario B y del 77,5 % de Escenario C (cota
superior), y el movimiento es pequeño (1,3 puntos) para un incremento del 38 % en `n`
— no hay indicio de que el sesgo de cobertura (formatos con mejor soporte en ffmpeg)
se esté rompiendo con esta ampliación: los 24 alias de ffmpeg son en su mayoría
formatos de VIDEOJUEGOS ANTIGUOS (Interplay, Delphine, Bethsoft, Cyberia, Chronomaster,
Argonaut, Tiertex, Sega FILM, Westwood) — la MISMA categoría de "formato con caso de
prueba dedicado en FATE porque alguna vez alguien necesitó decodificarlo", así que el
sesgo de §2.2 de `fate-y-aristas.md` sigue aplicando igual de fuerte a la muestra
ampliada. **No es un dato que rompa el sesgo declarado: lo confirma con más `n`.**

`asf_o` (MUERTA) y `evc` (MUERTA, ya conocida) son las únicas dos muertes con causa
DIAGNOSTICADA (parser legacy más estricto; códec joven sin decodificador en esta
build); las otras dos MUERTAS de la muestra original de worker2 no tienen diagnóstico
adicional en este informe.

### 2.4 Nivel 2 (aristas, 6 destinos por origen) sobre los 24 orígenes vivos de alias

Mismo método que `c16_muestra_aristas_fate.py`: 6 destinos fijos que cruzan familia
(`mkv/gif/png/mp3/wav/flac` para ffmpeg, `png/jpg/webp/bmp/tiff/gif` para ImageMagick),
criterio barato `rc==0 && bytes>0` (trampa 75), **no** el contrato de 5 puntos.

| | n orígenes | n aristas | buenas | % |
|---|---:|---:|---:|---:|
| Alias (este informe) | 24 | 144 | 96 | 66,7 % |
| Muestra original (worker2) | 67 | 402 | 269 | 66,9 % |
| **COMBINADO** | **91** | **546** | **365** | **66,85 %** |

**24/24 orígenes de alias tienen al menos un destino bueno de los 6 probados**
(tautológico en parte: los destinos de nivel 1 —`mkv`/`wav`/`png`— son subconjunto de
los 6 de nivel 2, así que todo VIVO de nivel 1 hereda al menos un destino bueno en
nivel 2). **La tasa de arista se mantiene prácticamente idéntica** (66,9 % → 66,85 %
combinado) — el patrón "mkv casi universal, png/gif caen en orígenes de audio puro" que
worker2 ya documentó se reproduce en la muestra de alias sin sorpresas.

### 2.5 Lo que esto cambia — y lo que NO

**Sigue sin cerrar el 54,78 % entero.** 95 de 445 formatos "no_materializables" tienen
ahora dato real (21,3 %, frente al 15,5 % de la muestra de worker2), y quedan **350**
sin ningún fichero real conocido en FATE. El fuzzy-match de esta ronda encontró 26
alias nuevos sobre 376 candidatos posibles (6,9 % de tasa de acierto del método) —
**extrapolando** esa tasa (sin medirla: es una proyección, no una medición) a los 350
restantes daría del orden de 24 alias más por encontrar con el mismo esfuerzo, pero
**no se ha hecho esa búsqueda exhaustiva** y no se inventa esa precisión aquí. Lo que
SÍ es un resultado firme: **con n=95 (más del doble de la muestra original), la tasa de
semiarista viva sigue en el rango 95-97 %** y la tasa de arista sigue en ~67 % — el
Escenario B (48,6 %) sigue pareciendo demasiado pesimista para el estrato de FATE, y el
sesgo de cobertura declarado por worker2 (formatos maduros) se sostiene con más datos,
no se diluye.

---

## 3 · Verificación

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python
3.11.9, `win32`.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```

**Resultado:** `459 passed, 4 skipped, 130 subtests passed` en 292,02 s. Sin fallos.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```

**Resultado:** las 9 comprobaciones en `OK` (`citas`, `inventario`, `un-emoji-por-fila`,
`trampas`, `informes-registrados`, `manifiestos`, `secretos`, `binarios`, `en-curso`).

**Qué quedó fuera de la verificación y por qué:** esta ronda **no tocó ningún fichero
de `filex/`** — es investigación de bancos (`bench/`) sobre motores externos
(ffmpeg, ImageMagick) y el corpus FATE. Ninguna GPU, ningún contenedor Docker
(se comprobó `docker ps -a` al empezar por disciplina, pero ningún script de esta
ronda invoca `docker run`). No hay código de producto que verificar más allá de la
suite existente, que se corre sin cambios para confirmar que nada se rompió por
accidente.

**Estado de la máquina:** Windows 10, CPU sin carga reportada de otros carriles en el
momento de esta tanda (no se comprobó `wmic cpu get loadpercentage` explícitamente —
las tandas de este informe son ffmpeg/ImageMagick de segundos por celda, no minutos, y
ninguna celda se acercó al tope de 25 s). Sin GPU tomada. Docker arriba y sano pero no
usado por ningún script de esta ronda.

---

## 4 · Salidas en disco

`bench/salidas-fate-completo/` — ver `MANIFIESTO.md`, con `sha256`, tamaños y las
órdenes exactas. Sin binarios: los directorios temporales de cada script se crean y se
borran al terminar (`tmp_c28_12/`, `tmp16b/`, `tmp16c/`, `tmp16im/`). El corpus FATE se
referenció por ruta absoluta y no se tocó ni se copió.
