# Sondeo de las 70 aristas `sin_sondear` de ffmpeg

**Agente S2 · 22/08/2026 · build `ffmpeg N-121159-g0bd5a7d371-20250921`**
Datos: `filex/sondeo/ffmpeg.json` · crudo y órdenes: `bench/salidas-sondeo-ff/`

---

## 0. Resumen

Las **70 aristas** se han **ejecutado**, una a una, por `FileX.convertir()` —con el
directorio desechable, el censo del punto 5 y el contrato de cinco puntos
dentro—, con **n = 3** por arista. **MEDIDO:**

| | aristas |
|---|---:|
| **`real`** (rc = 0 y el contrato no dicta `fallo`) | **49** |
| **`nominal`** (rc ≠ 0 o el contrato dicta `fallo`) | **21** |

Y el reparto de las 21, que es lo que se pedía distinguir:

| causa | aristas | ¿es de ffmpeg? |
|---|---:|---|
| **La sonda EN PROCESO del verificador no sabe leer el formato** | **16** | **no** |
| **Parametrización de FileX: `-map 0` contra el muxer `gif`** | **4** | **no** |
| **Umbral del contrato: la trama de *priming* del AAC** | **1** | **no** |
| Codificador no compilado (`build`) | **0** | — |
| El motor produjo algo mal | **0** | — |

> **Ni una sola de las 21 lo es por ffmpeg.** No hay ningún codificador sin
> compilar entre estas 70 —el reparto «19 de 33 son build» de
> `bench/aristas-nominales.md` era de las **semiaristas de salida** del catálogo
> nominal completo, no de las que FileX declara—; **el catálogo que FileX
> declara para ffmpeg está bien elegido, y lo que falla es FileX mirándose a sí
> mismo.**

**MEDIDO, y es la cifra del informe: con 5 líneas de cambio en
`filex/verificador.py`, 16 de las 21 pasan a `real`** (§4.4). Con 1 línea más
en `filex/motores.py`, las 5 de `gif` también (§5.3).

Cada `nominal` del JSON lleva un campo `causa` —`verificador`,
`verificador_tolerancia` o `parametrizacion`— además del `motivo`.
`sondeo.aplicar` ignora las claves que no conoce, así que el campo no cambia el
comportamiento del grafo: está para que la próxima persona no tenga que volver
a diagnosticar lo mismo.

**El punto 5 del contrato NO se disparó ni una vez**: 0 sobrantes en las 70
conversiones, censo tomado en las 70. Ninguna de estas aristas escribe fuera de
lo declarado; el caso `.mpd` necesita un destino `.mpd`, que no está en el
catálogo. **Se reporta como no-hallazgo, no se calla.**

**`-map 0` sigue funcionando: 45 de 45.** Todas las fuentes de vídeo derivan de
`corpus/video/patologico_2pistas.mkv` y llevan **dos pistas de audio**; las 45
aristas sondeadas con esa fuente entregaron exactamente las pistas esperadas
(las dos cuando el destino es vídeo, una cuando es audio). **Cero regresiones.**

**Y una arista que el catálogo declaraba `real` está REFUTADA:** `mp4→gif`
(`referencia.json:vid.2gif.paleta`). Solo pasaba porque `trivial.mp4` **no
tiene pista de audio**. Con cualquier MP4 que sí la tenga, falla igual que las
otras cuatro: **5 de 5 aristas vídeo→gif rotas** (§5).

> Por eso `filex/sondeo/ffmpeg.json` tiene **71 entradas y no 70**: la
> septuagésima primera es `mp4>gif`, y **degrada a `nominal` una arista que el
> motor declara `real`**. Está puesto a propósito y con la evidencia delante:
> una tabla que sabe que una arista no funciona y la sigue anunciando es el
> fallo que este repositorio existe para no cometer.

---

## 1. Cómo se midió

**Un grafo de UNA arista por sondeo.** `convertir()` planifica, y el
planificador **no elige siempre la arista directa**: una `sin_sondear` cuesta
`1,0 + 2,0 = 3,0` (`grafo.py:_coste_paso`) y dos `real` encadenadas cuestan
`1,0 + 1,0 = 2,0`. Pedirle `mp3→opus` al grafo entero le hace tomar
`mp3→wav→opus` y **la arista que se quería sondear no se ejecuta**. Para cada
arista se sustituye `fx.grafo` por un `Grafo([arista])`; todo lo demás —la
orden de `motores.FFmpeg.orden()`, `stdin=DEVNULL`, el desechable, el censo, el
contrato— es el núcleo sin tocar.

**El `pedido` declara lo que se pide.** Ver §3: sin declarar `solo_audio`, 13 de
las 24 aristas vídeo→audio que hoy salen `real` saldrían `fallo` por un hueco
del núcleo. Se declara, y se mide también qué pasa sin declararlo.

**Diagnóstico aparte para las que fallan.** Cuando el contrato dicta `fallo` el
núcleo borra el desechable y la salida se pierde. Para cada `nominal` se repite
la orden EXACTA en un directorio de diagnóstico y se sondea con `ffprobe`. Eso
es lo que separa «el motor no produjo nada» de «el motor produjo un fichero
bueno que el verificador no sabe leer», y sin ello las 21 habrían quedado en un
montón indistinguible.

**Fuentes.** El corpus no trae `.webm`, `.mov`, `.avi`, `.m4a`, `.opus` ni
`.ogg`. Se derivan con `ffmpeg` directo (no con FileX: si `wav→ogg` fallara, no
habría fuente `.ogg` y otras 5 aristas caerían por un motivo que no es el suyo).
Las órdenes literales, con `sha256`, en `bench/salidas-sondeo-ff/MANIFIESTO.md`.

**Una fuente que costó un intento:** `-c:v copy` de H.264 desde MKV a AVI
**falla** — «Error writing trailer: Invalid data found». El H.264 sale en AVCC y
el índice clásico de AVI exige Annex B. El AVI se escribe con MPEG-4 parte 2 +
MP3, que además es lo que un `.avi` real lleva dentro. **Es del contenedor, no
de la invocación.**

### 1.1 Ruido — la tanda es `SUCIA`

Sesión remota activa y **tres agentes trabajando** (S1 ImageMagick, S3
contenedores). Dos testigos, n = 140 cada uno, con tope de 20 s en el de proceso:

| testigo | mín | mediana | p90 | máx | máx/mín |
|---|---:|---:|---:|---:|---:|
| proceso (`ffprobe -version`) | 30,7 | 37,7 | 53,7 | **299,8** | **9,8×** |
| deriva (bucle monohilo) | 23,7 | 31,2 | 39,6 | 57,0 | 2,4× |

Otra vez el patrón de CLAUDE.md §3: **el monohilo es ciego a la contención
multinúcleo** (2,4× frente a 9,8×). Ningún testigo se topó. **Los `ms` de este
informe desempatan dentro de la tanda; no se comparan con otro informe.**

---

## 2. Las 70, una a una

`veredicto` es el del contrato; `—` significa que no hubo salida que juzgar.

### 2.1 Vídeo → vídeo (17): 13 `real`, 4 `nominal`

| arista | estado | veredicto | ms (n=3) | nota |
|---|---|---|---:|---|
| `avi>mkv` | real | ok | 3143,8 | |
| `avi>mov` | nominal | fallo | 2239,9 | la sonda no lee `.mov`; recuperada con el parche |
| `avi>mp4` | real | ok | 3318,7 | |
| `avi>webm` | real | ok | 11270,5 | |
| `mkv>avi` | real | ok_parcial | 2153,7 | no hay lector de AVI: puntos 3 y 4 sin cobertura |
| `mkv>mov` | nominal | fallo | 2140,4 | la sonda no lee `.mov`; recuperada con el parche |
| `mkv>webm` | real | ok | 8917,6 | |
| `mov>avi` | real | ok_parcial | 2233,4 | no hay lector de AVI: puntos 3 y 4 sin cobertura |
| `mov>mkv` | real | **aviso** V3/V7 | 2342,8 | el mismo defecto de `.mov`, del lado de la ENTRADA |
| `mov>mp4` | real | **aviso** V3/V7 | 2134,1 | ídem |
| `mov>webm` | real | **aviso** V3/V7 | 9556,9 | ídem |
| `mp4>avi` | real | ok_parcial | 2231,6 | no hay lector de AVI |
| `mp4>mov` | nominal | fallo | 5435,1 | la sonda no lee `.mov`; recuperada con el parche |
| `webm>avi` | real | ok_parcial | 2075,1 | no hay lector de AVI |
| `webm>mkv` | real | ok | 2288,2 | |
| `webm>mov` | nominal | fallo | 1978,3 | la sonda no lee `.mov`; recuperada con el parche |
| `webm>mp4` | real | ok | 2490,0 | |

### 2.2 Vídeo → audio (28): 24 `real`, 4 `nominal`

| arista | estado | veredicto | ms (n=3) | nota |
|---|---|---|---:|---|
| `avi>flac` | real | ok | 57,0 | |
| `avi>m4a` | real | ok | 852,2 | |
| `avi>mp3` | real | ok | 126,2 | |
| `avi>ogg` | real | ok | 177,7 | pasa **porque la sonda no lee el AVI de origen** (§4.3) |
| `avi>opus` | real | ok | 138,7 | |
| `avi>wav` | real | ok | 59,2 | |
| `mkv>flac` | real | ok | 79,9 | |
| `mkv>m4a` | nominal | fallo | 818,8 | *priming* del AAC contra el umbral (§4.5) |
| `mkv>mp3` | real | ok | 143,3 | |
| `mkv>ogg` | nominal | fallo | 174,8 | gránulo de Vorbis; recuperada con el parche |
| `mkv>opus` | real | ok | 173,6 | |
| `mkv>wav` | real | ok | 85,9 | |
| `mov>flac` | real | ok | 113,1 | |
| `mov>m4a` | real | ok | 1923,6 | |
| `mov>mp3` | real | ok | 150,5 | |
| `mov>ogg` | nominal | fallo | 669,8 | gránulo de Vorbis; recuperada con el parche |
| `mov>opus` | real | ok | 169,4 | |
| `mov>wav` | real | ok | 92,3 | |
| `mp4>flac` | real | **aviso** A6 | 75,4 | profundidad inflada AAC→FLAC |
| `mp4>ogg` | nominal | fallo | 159,6 | gránulo de Vorbis; recuperada con el parche |
| `mp4>opus` | real | ok | 140,4 | |
| `mp4>wav` | real | ok | 71,0 | |
| `webm>flac` | real | ok | 86,3 | |
| `webm>m4a` | real | ok | 1097,4 | |
| `webm>mp3` | real | ok | 177,8 | |
| `webm>ogg` | real | ok | 295,8 | pasa **porque el origen es Opus a 48 kHz** (§4.3) |
| `webm>opus` | real | ok | 153,0 | |
| `webm>wav` | real | ok | 90,5 | |

### 2.3 Audio → audio (21): 12 `real`, 9 `nominal`

| arista | estado | veredicto | ms (n=3) | nota |
|---|---|---|---:|---|
| `flac>m4a` | real | ok | 642,1 | |
| `flac>ogg` | nominal | fallo | 118,9 | gránulo de Vorbis; recuperada con el parche |
| `m4a>flac` | real | **aviso** A6 | 59,6 | profundidad inflada AAC→FLAC |
| `m4a>mp3` | real | ok | 111,9 | |
| `m4a>ogg` | nominal | fallo | 125,9 | gránulo de Vorbis; recuperada con el parche |
| `m4a>opus` | real | ok | 108,6 | |
| `m4a>wav` | real | ok | 63,6 | |
| `mp3>m4a` | real | ok | 588,2 | |
| `mp3>ogg` | nominal | fallo | 120,1 | gránulo de Vorbis; recuperada con el parche |
| `mp3>opus` | real | ok | 109,4 | |
| `ogg>flac` | nominal | fallo | 57,2 | gránulo de Vorbis; recuperada con el parche |
| `ogg>m4a` | nominal | fallo | 565,1 | ídem |
| `ogg>mp3` | nominal | fallo | 100,3 | ídem |
| `ogg>opus` | nominal | fallo | 110,5 | ídem |
| `ogg>wav` | nominal | fallo | 66,8 | ídem |
| `opus>flac` | real | ok | 91,4 | |
| `opus>m4a` | real | ok | 688,1 | |
| `opus>mp3` | real | ok | 113,7 | |
| `opus>ogg` | real | ok | 146,9 | **el único `→ogg` que pasa**: el origen ya va a 48 kHz |
| `opus>wav` | real | ok | 70,1 | |
| `wav>ogg` | nominal | fallo | 152,5 | gránulo de Vorbis; recuperada con el parche |

### 2.4 Vídeo → GIF (4): 0 `real`, 4 `nominal`

| arista | estado | rc | ms (n=3) | nota |
|---|---|---|---:|---|
| `avi>gif` | nominal | 3165764104 | 43,5 | `-map 0` contra el muxer `gif` (§5) |
| `mkv>gif` | nominal | 3165764104 | 56,4 | ídem |
| `mov>gif` | nominal | 3165764104 | 66,7 | ídem |
| `webm>gif` | nominal | 3165764104 | 56,8 | ídem |

---

## 3. El hueco del núcleo: el motor decide `-vn` y no se lo dice al contrato

`motores.FFmpeg.orden()` añade `-vn` cuando el destino es de categoría audio.
`nucleo.py:_un_salto` llama al contrato con `dict(pedido, destino=…)` y **nada
más**, así que el contrato no sabe que se pidió audio, compara la salida con la
entrada pista a pista y exige que un `.wav` extraído de un `.mp4` conserve la
pista de vídeo: **`V7 fallo`, «numero de pistas de video distinto del
esperado»**.

**MEDIDO**, ejecutando cada arista con destino audio dos veces —una declarando
`solo_audio` y otra sin declararlo—:

| | aristas |
|---|---:|
| pasan de un veredicto **sin fallo** a **`fallo`** por no declararlo | **13** |
| bajan de `ok` a `aviso` | 5 |
| no cambian | 31 |

Las 13: `mp4>wav`, `mp4>flac`, `mp4>opus`, `mkv>wav`, `mkv>flac`, `mkv>mp3`,
`mkv>opus`, `webm>wav`, `webm>flac`, `webm>mp3`, `webm>m4a`, `webm>opus`,
`webm>ogg`.

**No son 28 porque el defecto se tapa con otro:** las de origen `.avi` no fallan
porque la sonda **no sabe leer AVI** y el punto 2 se queda sin referencia; las
de origen `.mov` no fallan porque la sonda lee **0 pistas** y entonces «0 vídeo
esperadas, 0 obtenidas» cuadra. **Dos defectos que se cancelan no son medio
defecto: son dos.**

El sondeo declara `solo_audio` —que es la verdad de lo que se pide— y por eso
las 24 salen `real`. **Pero el núcleo tal como está hoy no lo declara**, así que
en producción esas 13 conversiones entregarían `fallo`. Diff en §6.1.

---

## 4. El hallazgo principal: 16 de las 21 `nominal` son de la SONDA, no del motor

Las 16 tienen `rc = 0`, entregan un fichero que `ffprobe` lee sin una queja, y
el contrato las tumba porque **`verificador.sondear_en_proceso` lee mal el
fichero**. Son cuatro defectos distintos, y los cuatro están en el lector de
cabeceras en proceso — la pieza que CLAUDE.md §5 defiende («verificar leyendo
cabeceras en proceso, no con `ffprobe`»). **La regla no se cae; el lector tiene
agujeros, y este sondeo mide cuáles y cuánto cuestan.**

### 4.1 `.mov` → «0 pistas». QuickTime pone un segundo `hdlr`

`_isobmff` recorre el `trak` y se queda con **el último `hdlr` que ve**. En un
MP4 de ffmpeg solo hay uno por pista, en `mdia`, y sale bien. **QuickTime
escribe un SEGUNDO `hdlr` dentro de `minf`** con el manejador de DATOS. Volcado
literal de los `hdlr` de los dos ficheros, byte a byte el mismo contenido:

```
=== f.mp4                      === f.mov
  hdlr -> b'vide'                hdlr -> b'vide'
                                   hdlr -> b'url '      <-- dentro de minf
  hdlr -> b'soun'                hdlr -> b'soun'
                                   hdlr -> b'url '
  hdlr -> b'soun'                hdlr -> b'soun'
                                   hdlr -> b'url '
```

Resultado: las tres pistas se clasifican como «otro», `n_pistas = 0`. La
duración sale bien (el `mvhd` sí se lee), así que la categoría sigue siendo `av`
y el fichero **parece** legible.

Y el daño es **asimétrico**, que es lo que hace que no salte a la vista:

* con `.mov` de **DESTINO**: `obtenido < esperado` → **`V7 fallo`** → 4 aristas
  `nominal` (`mp4>mov`, `mkv>mov`, `webm>mov`, `avi>mov`);
* con `.mov` de **ORIGEN**: `obtenido > esperado` → **`aviso`** → 3 aristas
  (`mov>mp4`, `mov>mkv`, `mov>webm`) salen `real` con un aviso falso;
* `avi>mov` ni siquiera da `V7`: da **`G4 fallo`, «el contenedor no declara
  ninguna pista»**, porque el origen AVI tampoco es legible y el punto 2 no
  llega a ejecutarse. **El mismo defecto con dos síntomas distintos según la
  entrada.**

### 4.2 `.avi` → no hay lector. Cobertura, no fallo

`sondear_en_proceso` no tiene rama para RIFF/AVI: devuelve
`categoria: "desconocida"`. Con la corrección F1 del propio verificador eso
**no** es un `fallo` — es cobertura falsa a `False` en los puntos 3 y 4, y el
veredicto baja a `ok_parcial`. **4 aristas** (`mp4>avi`, `mkv>avi`, `webm>avi`,
`mov>avi`) salen `real` pero **sin haber comprobado nada de la salida**, y las 6
de origen AVI salen `real` con el punto 2 declarado informativo.

**Es el agujero más honesto de los cinco y el más peligroso**: no rompe nada, y
por eso nadie lo mira. FileX hoy **escribe AVI y no puede verificarlo**.

### 4.3 `.ogg` de Vorbis → duración ×0,91875. El gránulo no va a 48 kHz

`_ogg` hace `duracion_s = (granulo - preskip) / 48000.0`, **siempre**. Es
correcto para Opus, que por definición entrega a 48 kHz, y **falso para Vorbis**,
cuyo gránulo va a la frecuencia del propio flujo. Un Vorbis de 8,000 s a
44,1 kHz se lee como **7,350 s** = 8 × 44100/48000. Diferencia: **650 ms** contra
una tolerancia de 23,2 ms.

**El control que lo cierra**, medido a propósito: el mismo audio reescrito a
48 kHz (`-ar 48000 -c:a libvorbis`) se lee **8,0 s exactos** en proceso y 8,0 en
`ffprobe`. Y el patrón aparece solo en las 15 aristas donde se cumple:

| arista | origen | resultado | por qué |
|---|---|---|---|
| `wav>ogg`, `flac>ogg`, `mp3>ogg`, `m4a>ogg`, `mp4>ogg`, `mkv>ogg`, `mov>ogg` | 44,1 kHz | **fallo** | el Vorbis de salida hereda 44,1 kHz |
| `webm>ogg` | Opus 48 kHz | **ok** | el Vorbis de salida va a 48 kHz |
| `opus>ogg` | Opus 48 kHz | **ok** | ídem |
| `avi>ogg` | 44,1 kHz | **ok** | el origen AVI no es legible: no hay con qué comparar (§4.2) |
| `ogg>wav/flac/mp3/m4a/opus` | Vorbis 44,1 kHz | **fallo** | ahora el mal leído es el ORIGEN |

**12 aristas caen por el gránulo** (7 con `.ogg` de destino y 5 con `.ogg` de
origen) **y una decimotercera, `avi>ogg`, pasa por ceguera.** De las 15 aristas
que tocan `.ogg`, solo dos —`webm>ogg` y `opus>ogg`— pasan por el motivo bueno.

### 4.4 Lo que recuperan los parches — MEDIDO

Se vuelven a pasar las 21 `nominal` por el mismo `FileX.convertir()`, con la
sonda parcheada **en memoria** (no se toca `filex/verificador.py`, que es de
otro agente) y con `_isobmff` **copiado literal salvo tres líneas**:

| | antes | después |
|---|---|---|
| `mp4>mov`, `mkv>mov`, `webm>mov`, `avi>mov` | fallo | **ok** ×4 |
| `wav>ogg`, `flac>ogg`, `mp3>ogg`, `m4a>ogg`, `mp4>ogg`, `mkv>ogg`, `mov>ogg` | fallo | **ok** ×7 |
| `ogg>wav`, `ogg>flac`, `ogg>mp3`, `ogg>m4a`, `ogg>opus` | fallo | **ok** ×5 |
| `mkv>m4a` | fallo | fallo (§4.5) |
| las 4 de `gif` | rc≠0 | rc≠0 (§5) |

**16 de 21, con 5 líneas.** Crudo en `bench/salidas-sondeo-ff/reparacion.json`.

Y un aviso metodológico que costó una iteración: **el primer parche del `.mov`
contaba las pistas y no leía sus propiedades**, y entonces el punto 3 disparaba
`V7 fallo, «pista de video sin dimensiones»` — recuperaba 0 de 4. El parche
bueno es el de tres líneas sobre la función original, que ya lee `tkhd` y
`stsd`. **Reparar la sonda a mano en vez de arreglar la sonda de verdad da el
número equivocado.**

### 4.5 La que no se recupera: el *priming* del AAC contra el umbral

`mkv>m4a`, y solo esa. `rc = 0`, `ffprobe` lee **10,030998 s**, la entrada dura
10,023 s. Pero la sonda en proceso lee del `mdhd` **10,054 s**:

```
433 tramas AAC × 1024 = 443 392 muestras / 44 100 = 10,0542 s   <- mdhd
menos 1 024 de priming  = 442 368 muestras / 44 100 = 10,0310 s <- lo que ve ffprobe
```

**Un `elst` (edit list) recorta exactamente una trama de *priming*, y `_isobmff`
no lee `edts/elst`.** Δ = 31,0 ms contra una tolerancia de 23,2 ms (una trama de
AAC). Es el quinto defecto de la sonda, y el más sutil, porque **normalmente se
cancela solo**: si el origen también es ISO-BMFF con AAC, la sonda le suma el
mismo *priming* a los dos lados y la resta sale bien. **Solo se ve cuando el
origen es de otra familia** —Matroska aquí—, que es justo el caso en que un
`elst` importa.

Nota de calibración, con los números en proceso de las cuatro `→m4a`
(tolerancia = una trama AAC = 1024/44100 = **23,22 ms**):

| arista | entrada (s) | salida, pista (s) | Δ | resultado |
|---|---:|---:|---:|---|
| `mkv>m4a` | 10,0230 (pista) | 10,0540 | **31,0 ms** | **fallo** |
| `mov>m4a` | 10,0310 (contenedor: no hay pistas legibles) | 10,0540 | **23,0 ms** | ok **por 0,22 ms** |
| `webm>m4a` | 10,0380 | 10,0524 | 14,4 ms | ok |
| `avi>m4a` | — (origen ilegible) | 10,0804 | — | ok, **sin comparar** |

**Dos de las tres que pasan lo hacen por el filo o por ceguera.** El umbral no
está mal calibrado: lo que está mal es que la sonda mida el `mdhd` crudo.

---

## 5. `-map 0` y el muxer `gif` se destruyen mutuamente

Las 4 aristas vídeo→gif dan `rc = 3165764104`. En complemento a dos eso es
**`-1129203192 = AVERROR_ENCODER_NOT_FOUND`**, y el motivo literal:

```
Automatic encoder selection failed
Default encoder for format gif (codec none) is probably disabled.
Error selecting an encoder
```

`orden()` añade **`-map 0`** a todo destino que no sea de categoría audio, GIF
incluido. El muxer `gif` **no tiene códec de audio por defecto**, así que
arrastrar las pistas de audio de la entrada aborta la conversión antes de
codificar un solo fotograma.

**Es la colisión de dos reglas MEDIDAS del proyecto.** `-map 0` existe porque
sin él ffmpeg descarta la segunda pista de audio en silencio; aquí es
precisamente `-map 0` lo que rompe la arista.

### 5.1 Y refuta una arista que el catálogo declara `real`

`mp4→gif` está marcada `real` con evidencia `referencia.json:vid.2gif.paleta`.
**Falla exactamente igual.** La referencia usó `corpus/video/trivial.mp4`, que
**no tiene pista de audio**: sin audio no hay nada que mapear y `-map 0` es
inocuo. Con un MP4 que sí lo tenga —el caso normal— la conversión aborta.

> **La arista no era `real`: era `real para una entrada sin audio`.** Es el mismo
> error que este proyecto denuncia en los catálogos ajenos, cometido en casa y
> con la evidencia bien puesta.

### 5.2 La escalera: 0 → 2 → 5 de 5

Medido sobre las **cinco** aristas vídeo→gif, n = 3, sin tocar `motores.py` (se
parchea el método en memoria):

| paso | `real` |
|---|---:|
| **A** — el código de hoy (`-map 0`), fuentes con audio | **0/5** |
| **B** — `-map 0:v:0` solo cuando el destino es `gif` | **2/5** |
| **C** — B + el pedido declara la escala que el motor aplica | **5/5** |
| **D** — C + la sonda de `.mov` parcheada | **5/5** |

**Lo que enseña el paso B es más valioso que el arreglo.** Las 3 que siguen
fallando dan **`I1/V7 fallo: REDIMENSIONADO NO SOLICITADO`** — porque `orden()`
mete `scale=320:-1` a fuego y **no se lo dice al contrato**. Es decir: el cuarto
punto del contrato, escrito para atrapar el redimensionado silencioso de
`image-worker-mcp`, **atrapa a FileX haciendo lo mismo.** Y las 2 que «pasan» en
B son `mov>gif` y `avi>gif`: pasan **porque la sonda no sabe leer sus orígenes y
no puede comparar el tamaño**. Un aprobado por ceguera no es un aprobado — de
ahí el paso D, que confirma que con C el 5/5 es de verdad.

### 5.3 La forma del defecto es la misma que la del §3

`-vn` y `scale=320:-1` son **dos decisiones que toma el motor y que el contrato
no llega a conocer**. En un caso cuesta 13 aristas, en el otro 3. **No son dos
erratas: es que `motores.orden()` y `contrato.verificar()` no comparten el mismo
`pedido`, y el que sabe lo que se hizo es el motor.** El arreglo puntual está en
§6; el estructural —que el motor devuelva, junto a la orden, lo que esa orden
declara— es lo que este sondeo recomienda y **queda PENDIENTE**.

---

## 6. Cambios que pido

No he tocado `filex/*.py`. Estos son los diffs exactos, con el número que cada
uno recupera.

### 6.1 `filex/nucleo.py` — el núcleo declara `solo_audio` (recupera 13)

```diff
--- a/filex/nucleo.py
+++ b/filex/nucleo.py
@@ _un_salto
         censo = t.censo()
         s.sobrantes = t.sobrantes([nombre])
 
-        res = contrato.verificar(dentro, entrada, dict(pedido, destino=arista.destino),
-                                 censo)
+        # El motor decide `-vn` por la categoría del destino
+        # (`motores.FFmpeg.orden`) y el contrato no se enteraba: exigía que un
+        # `.wav` extraído de un `.mp4` conservara la pista de vídeo. MEDIDO
+        # (`bench/sondeo-ffmpeg.md` §3): 13 aristas vídeo→audio pasan de un
+        # veredicto sin fallo a `V7 fallo` por no declararlo.
+        ped = dict(pedido, destino=arista.destino)
+        _f = formatos.formato(arista.destino)
+        if _f is not None and _f.categoria == "audio" and not ped.get("solo_audio"):
+            ped["solo_audio"] = True
+            ped["params"] = dict(ped.get("params") or {}, solo_audio=True)
+        res = contrato.verificar(dentro, entrada, ped, censo)
```

(`formatos` ya está importado en `nucleo.py`. **Los dos sitios hacen falta**: el
punto 2 mira `pedido['solo_audio']` **o** `pedido['params']['solo_audio']`, y el
punto 4 mira **solo** `pedido['params']`.)

### 6.2 `filex/verificador.py` — el primer `hdlr` del `trak` (recupera 4, y quita 3 avisos falsos)

```diff
--- a/filex/verificador.py
+++ b/filex/verificador.py
@@ _isobmff
             elif tipo == b"hdlr":
-                fh.seek(di + 8)
-                estado["handler"] = fh.read(4)
+                # QuickTime pone un SEGUNDO `hdlr` dentro de `minf` con el
+                # manejador de DATOS ('url ', 'alis'). Quedarse con el ÚLTIMO
+                # clasifica las tres pistas de un `.mov` como «otro» y el
+                # fichero entero como «0 pistas». MP4 no trae el segundo; MOV
+                # sí. MEDIDO: `bench/sondeo-ffmpeg.md` §4.1.
+                if estado.get("handler") is None:
+                    fh.seek(di + 8)
+                    estado["handler"] = fh.read(4)
```

`estado["handler"]` ya se reinicia a `None` al entrar en cada `trak`, así que la
guarda es por pista y no arrastra nada entre ellas.

### 6.3 `filex/verificador.py` — el gránulo de Vorbis (recupera 12)

```diff
--- a/filex/verificador.py
+++ b/filex/verificador.py
@@ _ogg
     if pos >= 0:
         gran = struct.unpack_from("<q", cola, pos + 6)[0]
-        d["duracion_s"] = round(max(0, gran - preskip) / 48000.0, 4)
+        # El gránulo de Opus SIEMPRE va a 48 kHz; el de Vorbis va a la
+        # frecuencia del propio flujo. Dividir siempre por 48000 deja un
+        # Vorbis de 8,000 s a 44,1 kHz en 7,350 (×0,91875) y dispara
+        # `A1/V1 fallo` en 11 aristas. MEDIDO: §4.3.
+        base = p.get("sample_rate") if p.get("codec") == "vorbis" else 48000
+        d["duracion_s"] = round(max(0, gran - preskip) / float(base or 48000), 4)
```

### 6.4 `filex/motores.py` — `-map 0:v:0` para GIF (recupera 4, y devuelve `mp4→gif`)

```diff
--- a/filex/motores.py
+++ b/filex/motores.py
@@ FFmpeg.orden
         solo_audio = fo is not None and fo.categoria == "audio"
         if solo_audio:
             argv.append("-vn")
+        elif d == "gif":
+            # `-map 0` y el muxer `gif` se destruyen mutuamente: `gif` no tiene
+            # códec de audio por defecto y arrastrar las pistas de audio de la
+            # entrada aborta con AVERROR_ENCODER_NOT_FOUND. MEDIDO: 5 de 5
+            # aristas vídeo→gif rotas, `mp4→gif` incluida —que pasaba solo
+            # porque `trivial.mp4` no tiene audio— (`bench/sondeo-ffmpeg.md` §5).
+            argv += ["-map", "0:v:0"]
         else:
             # -map 0 EXPLÍCITO. Sin esto ffmpeg descarta la segunda pista de
```

…**y la otra mitad, que sin ella solo recupera 2 de 5**: `orden()` aplica
`scale=320:-1` sin declararlo, y el punto 4 lo llama redimensionado no
solicitado. O el motor deja de escalar por defecto, o el núcleo tiene que
recibir del motor lo que la orden declara. Lo mínimo que funciona hoy es que
`orden()` escriba en el pedido el `ancho` que va a usar — pero **eso exige que
`orden()` pueda devolver algo además del `argv`, y eso ya es cambio de API.**
Lo dejo formulado, no parcheado.

### 6.5 PENDIENTE, sin diff

* **Lector de RIFF/AVI en `sondear_en_proceso`** (§4.2). Hoy FileX escribe AVI y
  **no verifica nada** de lo que escribe: 4 aristas en `ok_parcial` y 6 con el
  punto 2 informativo.
* **`edts/elst` en `_isobmff`** (§4.5). 1 arista, y una tolerancia que hoy pasa
  por el filo en otras dos.
* **Que el motor declare lo que su orden hace** (§5.3). Es la raíz de §3 y de la
  mitad de §5.

---

## 7. Lo que NO se encontró, dicho como tal

* **Punto 5: 0 sobrantes en 70 conversiones**, con censo tomado en las 70.
  Ninguna de estas aristas escribe fuera de lo declarado. El caso `.mpd` —528 KB
  de segmentos DASH— necesita un destino `.mpd`, que **no está en el catálogo
  que FileX declara**, así que no podía salir aquí.
* **0 codificadores no compilados.** Este build trae `libx264`, `libx265`,
  `libvpx-vp9`, `libopus`, `libvorbis`, `libmp3lame` y `aac`, que es todo lo que
  las 70 aristas necesitan. La distinción build/parametrización que pedía el
  encargo **existe y aquí sale 0/21 para `build`**; la dimensión que sí manda en
  este catálogo es una tercera: **el verificador**.
* **`-map 0`: ninguna regresión.** 45 de 45 con fuente de dos pistas.
