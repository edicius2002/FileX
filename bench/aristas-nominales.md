# Aristas nominales — cuántas de las conversiones declaradas no existen

**Qué contesta este documento.** `HUECOS.md` §2 y `bench/fidelidad-caminos.md` §7 dejan abierta la única pregunta que el proyecto se reprocha sobre el diferenciador nº 2:

> «**La tasa de aristas nominales del grafo.** Se han refutado 4 por ejecución. Cuántas de las 138 501 son nominales es desconocido; sondearlas todas es un trabajo de días y sería la medición que de verdad cierra el hueco.»

Aquí se mide. No se sondean las 138 501 una a una: se demuestra que **no hace falta**, porque las aristas son cuadráticas (`entradas × salidas`) y las *semiaristas* son lineales (`entradas + salidas`). El censo de las 1 104 semiaristas cabe en **nueve minutos y medio de ejecución** y decide por sí solo el 45 % de la población. El resto se estima con una **muestra aleatoria estratificada de 498 aristas ejecutadas y verificadas**.

Toda afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**.

- Datos crudos e instrumentos: `bench/salidas-aristas/` (ver §10)
- Verificación: copia congelada de `bench/scripts/verificador.py` (`verificador_congelado.py`, sha256 `c753ca43…`), usada **en proceso**. V1 está editando el original en paralelo; congelarlo evita medir contra un blanco móvil.
- Contención: no se ha usado la GPU, no se han tocado los documentos maestros, ni `referencia.json`, ni `bench/scripts/verificador.py`.

---

## 0. La cifra

> ### **El 50,5 % de las aristas declaradas que se han podido verificar NO EXISTE.**
> **IC 95 %: [48,2 % – 53,0 %]**, sobre las **62 487 aristas (45,1 % de la población)** para las que hay veredicto de ejecución. **[MEDIDO]**

Descompuesta, y sin extrapolar nada:

| | Aristas | % de las 138 501 | Cómo se sabe |
|---|---:|---:|---|
| **Refutadas por ejecución de una semiarista** | **22 235** | **16,05 %** | **Censo**, no muestra: 1 104 sondas ejecutadas |
| Con las dos semiaristas vivas → muestreadas | 40 252 | 29,06 % | Marco muestral; n=498; **23,1 %** nominales [19,6–27,0] |
| Indeterminadas (no se pudo fabricar el origen) | 75 874 | 54,78 % | Sin veredicto; se declara, no se rellena |
| Ghostscript / Gotenberg (tratadas aparte, §8) | 140 | 0,10 % | |

Y sobre la población **entera**, con el supuesto escrito en cada escenario:

| Escenario | Supuesto | Nominales | % de 138 501 |
|---|---|---:|---:|
| **A — cota inferior** | las 75 874 indeterminadas son **todas reales** | 31 530 | **22,8 %** |
| **B — central** | las indeterminadas se comportan como las verificadas **de su propio motor** | 67 345 | **48,6 %** |
| C — cota superior | las indeterminadas son todas nominales | 107 404 | 77,5 % |

**La tesis del encargo —*una arista declarada por el catálogo de un motor no es una arista*— queda confirmada, y por un margen que no depende de qué escenario se elija: incluso en el más favorable al catálogo, más de una de cada cinco aristas declaradas no existe.** **[MEDIDO]**

**Y hay una refutación parcial, que es el hallazgo más útil:** la tasa **no es uniforme**. Va del **76,9 %** (ffmpeg cruzando familias) al **3,0 %** (aristas que tocan PDF). Las aristas que el grafo usa como **intermedias** —las que sostienen el multi-salto— son justo las que **sí existen**. Ver §6.

---

## 1. La población y de dónde sale

Se parte del **grafo instalado** de `bench/fidelidad-caminos.md` §1.2: ffmpeg + ImageMagick (sondeado) + Ghostscript + Gotenberg. `bench/salidas-aristas/_censo.py` lo reconstruye desde cero y da **exactamente 138 501 aristas dirigidas**, la misma cifra publicada. **[MEDIDO]** Esa reproducción exacta es la que autoriza a comparar todo lo que sigue con aquel informe.

El reparto de la población por motor declarante importa, porque decide dónde hay que mirar:

| Motor declarante | Aristas | % |
|---|---:|---:|
| ffmpeg | 93 508 | 67,5 % |
| imagemagick | 42 884 | 31,0 % |
| ffmpeg + imagemagick | 1 906 | 1,4 % |
| gotenberg-lo | 102 | 0,07 % |
| resto (gs, gotenberg-chromium, mixtos) | 101 | 0,07 % |

**El 98,5 % de la población son dos productos cartesianos**: `473 × 202` de ffmpeg y `245 × 183` de ImageMagick. Ahí es donde está la pregunta.

---

## 2. Criterio de muestreo, declarado como sesgo

Siguiendo el modelo de `bench/fidelidad-caminos.md` §2, los sesgos, uno por uno, **antes** de los resultados:

1. **El marco muestral no es la población.** Solo el **29,06 %** de las aristas entra en la muestra: las que tienen las dos semiaristas vivas. El **16,05 %** ya está decidido por censo y el **54,78 %** no tiene veredicto. Los porcentajes de §5 describen el marco, y **solo** el marco.
2. **Sesgo favorable al catálogo en la materialización.** Para sondear si un motor sabe *leer* el formato `a`, hay que tener un fichero de formato `a`. Cuando no está en el corpus, **lo escribe el propio motor que luego lo lee**. Es el mejor caso posible: el motor lee su propia salida. Un fichero de `a` de otra procedencia fallaría más. **La tasa de semiaristas de entrada muertas es, por construcción, una cota inferior.** El caso de libro es `txt`: `txt → png` está refutado en `fidelidad-caminos.md` §1.4 con un fichero de texto plano, y aquí sale **viva**, porque el «TXT» que fabrica ImageMagick es su volcado de píxeles, no texto. Las dos medidas son correctas y miden cosas distintas.
3. **Sesgo favorable al catálogo en el criterio N2.** «La firma real no es la del formato pedido» solo se puede juzgar dentro del vocabulario cerrado de firmas que el verificador sabe leer (24 nombres). **Fue evaluable en 62 de las 498 aristas de la muestra (12 %).** Fuera de ese vocabulario, una salida que sea basura del formato equivocado pasa como buena. **Otra cota inferior.**
4. **Una sola ejecución por arista, con un solo fichero.** No hay medianas: aquí no se mide tiempo, se mide **si la arista existe**, que es determinista. Los ms de los datos crudos son orientativos y **no deben citarse como rendimiento**.
5. **Semillas mínimas.** 64×48 px, 0,5 s de audio y vídeo. Eso produce **falsos muertos** (§4.1) que hubo que corregir con una segunda vuelta de semillas más ricas.
6. **La estratificación por «familia» es empírica y burda.** La familia de un formato se deduce de qué semilla consiguió escribirlo. Como la semilla de vídeo lleva audio, algunos formatos de audio quedan etiquetados «vídeo». Eso empeora la *eficiencia* de la asignación, no la insesgadez: la estimación global se pondera por tamaño de estrato y coincide con la no ponderada (23,2 % frente a 23,1 %).
7. **Un solo Windows, un solo día, estas builds.** `ffmpeg N-121159`, `ImageMagick 7.1.2-21`, `Ghostscript 10.07`. §7 muestra que la respuesta **cambia con el build**: la misma arista `svg → png` es real en el ImageMagick de Windows y nominal en el de Debian.

### 2.1 Qué cuenta como NOMINAL

Tres criterios, y solo tres. **Una degradación no es una arista nominal.**

| | Criterio | Categoría |
|---|---|---|
| **N1** | el proceso falla, agota el *timeout*, o no deja fichero / deja 0 bytes | **FALLO** |
| **N2** | el fichero existe pero su **firma real** no es la del formato pedido (punto 1 del contrato) | **DESTRUIDO** |
| **N3** | el fichero es del formato pedido pero está **vacío de contenido** (0 pistas, 0 píxeles) o es un volcado absurdo (destino textual, salida >100× la entrada) | **DESTRUIDO** |

Lo demás es una arista **real**, y se clasifica con el vocabulario del patrón oro: **ÍNTEGRO** (sin hallazgos) o **DEGRADADO** (hallazgos del contrato). *PÉRDIDA INEVITABLE* no aparece como categoría separada en la muestra porque se necesita el contrato de la petición para distinguirla de DEGRADADO, y aquí la petición es siempre «conviérteme a `b`», sin más.

### 2.2 Invocación y disciplina

Se replica la invocación **real** de los adaptadores de ConvertX, leída del código:

```
ffmpeg.ts:733-740     ffmpeg -i ENTRADA [-c:v libx264|libx265|libaom-av1] SALIDA
imagemagick.ts:~150   magick ENTRADA -auto-orient SALIDA
```

Con **tres desviaciones deliberadas**, que ConvertX no tiene y que CLAUDE.md §5 exige: **`stdin=DEVNULL`**, **`-y`** y **timeout duro** (20–60 s según fase). Sin ellas la campaña se cuelga: `mp4 → pdf` de `fidelidad-caminos.md` §1.4 ya demostró que el delegado sobrevive al *kill*. Con ellas, **cero procesos huérfanos** en las **1 703 invocaciones de motor registradas** (1 105 de censo + 598 de muestra), y solo **6 *timeouts*** — todos sobre las tres mismas semillas gigantes (`m.txt` de 103 MB, `m.ftxt` de 54 MB, el MKV del corpus). **[MEDIDO]**

### 2.3 Mitigación de ruido

V1 mide en CPU en paralelo. No se ha intentado evitar el ruido: se **etiqueta**, con un testigo determinista (400 000 SHA-256 encadenados, mediana de 7) antes y después de cada tanda.

| Momento | Mediana | Desvío sobre el mínimo |
|---|---:|---:|
| antes del censo de semiaristas | 338,11 ms | +2,3 % |
| antes de la muestra | **330,39 ms** | — (mínimo) |
| después de la muestra | **389,85 ms** | **+18,0 %** |
| al terminar | 355,04 ms | +7,5 % |

**+18,0 % < 20 % → la tanda de la muestra queda etiquetada LIMPIA respecto al testigo. [MEDIDO]** Sigue siendo **SUCIA estructural** por la sesión de escritorio remoto, como todo en este repositorio. Y no importa mucho: **ninguna conclusión de este informe es un tiempo.**

---

## 3. Nivel 0 — el cribado por nombre, y por qué no basta

Primero, lo barato: preguntar al binario si conoce el nombre. `ffmpeg -demuxers` / `-muxers` da los nombres; `ffmpeg -h muxer=N` da la línea `Common extensions:`; `ffmpeg -devices` da los dispositivos.

| | ConvertX declara | El binario conoce | Desconocidos |
|---|---:|---:|---:|
| ffmpeg, entrada | 473 | 541 tokens (405 demuxers + 267 ext + 5 dispositivos) | **17** |
| ffmpeg, salida | 202 | 300 tokens (184 muxers + 203 ext) | **0** |

**17 nombres de entrada que el binario no reconoce → 3 385 aristas (2,44 %) muertas por nombre. [MEDIDO]**

Los 17: `alsa, awb, fbdev, iec61883, jack, kmsgrab, mpg, opus, oss, pp, pulse, sndio, ssa, tif, video4linux2, wma, x11grab`. **Diez de los diecisiete son dispositivos de captura de Linux** (`alsa`, `oss`, `pulse`, `jack`, `sndio`, `v4l2`, `x11grab`, `kmsgrab`, `fbdev`, `iec61883`): no son formatos de fichero en absoluto, y ConvertX los declara como «formatos de entrada» porque copió la salida de `ffmpeg -formats` sin filtrar.

**Pero este cribado se equivocó dos veces y hay que decirlo:**

- **Falsos positivos, primera pasada: 20.** `png`, `bmp`, `jpeg`, `tif`, `webp`, `psd`, `pcx`, `sgi`, `dds`… salieron «desconocidos» porque el demuxer se llama `png_pipe`, no `png`. Corregido añadiendo la raíz de todo demuxer `*_pipe`.
- **Falsos positivos, segunda pasada: 7.** `av1.mkv`, `h264.mp4`, `h265.mkv`, `h266.mkv`… no son nombres de muxer: son **pseudoformatos «códec.contenedor» que ConvertX descompone en código** (`ffmpeg.ts:711-714`). Corregido tratándolos como vivos si su contenedor lo está.

**Conclusión del nivel 0: el cribado por nombre sirve para orientar y no para concluir.** Solo cuenta la ejecución. Es exactamente la regla de CLAUDE.md §5 —*«sondear capacidades en ejecución, no deducirlas»*— aplicada a mí mismo.

---

## 4. Nivel 1 — censo de semiaristas por ejecución

**La idea que hace tratable el problema.** Una arista es `(a → b, motor)`. Se descompone en dos semiaristas:

- **semiarista de salida** `(* → b)`: escribir `b` desde una semilla canónica;
- **semiarista de entrada** `(a → *)`: leer un fichero auténtico de `a`.

Hay `473 + 202 + 246 + 183 = 1 104` semiaristas frente a 138 501 aristas. **Y una semiarista muerta mata de golpe todas las aristas que la usan.** El censo completo costó **9 min 35 s** de reloj: 25 s las salidas, 7 s la segunda vuelta de salidas, 297 s las entradas y 246 s su recomprobación. **[MEDIDO]**

### 4.1 Semiaristas de SALIDA — dos vueltas, y la segunda fue necesaria

| Motor | Declaradas | Vivas | **Muertas** | |
|---|---:|---:|---:|---:|
| ffmpeg | 202 | 169 | **33** | **16,3 %** |
| imagemagick | 183 | 179 | **4** | **2,2 %** |

La primera vuelta (semillas de 64×48, sin pista de subtítulos) dio 41 y 5. **Nueve eran falsos muertos míos, no del motor:**

| Revivida por | Formatos | Por qué fallaba |
|---|---|---|
| semilla de **subtítulo** (`.srt` real) | `ass, srt, ssa, ttml, vtt, lrc` | los muxers de subtítulo necesitan una pista de subtítulos que escribir |
| semilla de **vídeo CIF 352×288** | `h261, h263` | esos códecs solo admiten resoluciones fijas; 64×48 no es una |
| semilla con **canal alfa** | `matte` (IM) | «the image does not have an alpha channel» |

**Refutar el propio arnés antes de publicar es parte del método, no una anécdota:** sin la segunda vuelta este informe habría inflado la tasa nominal en 9 semiaristas y varios miles de aristas.

Las 33 muertas de ffmpeg, ya confirmadas: `302, ac4, amv, avs3, bit, c2, cavs, chk, cvg, dnxhd, dnxhr, dts, dv, evc, flm, gsm, gxf, js, jss, lbc, mlp, oma, rcv, scc, spx, sub, sup, thd, tun, vbn, vc1, xface, xml`. Dos causas dominantes, ambas verificadas en el stderr: **`Encoder not found`** (el muxer existe, el codificador no está compilado en este build) y **`received no packets`** (el muxer solo admite un códec que no se puede producir desde ninguna de las cuatro semillas). Las 4 de ImageMagick —`clip, jpt, mask, thumbnail`— exigen una propiedad que la entrada no trae (una máscara de recorte, una miniatura EXIF).

### 4.2 Semiaristas de ENTRADA — y aquí aparece el hallazgo incómodo

| Motor | Declaradas | No materializables | En el marco | Vivas | **Muertas** | |
|---|---:|---:|---:|---:|---:|---:|
| ffmpeg | 473 | 359 | 114 | 106 | **8** | **7,0 %** |
| imagemagick | 246 | 86 | 160 | 134 | **26** | **16,2 %** |

**El 16,2 % de los formatos que ImageMagick declara leer, ImageMagick no los lee — y son ficheros que acaba de escribir él mismo. [MEDIDO]** Es autoinconsistencia del mismo binario, en la misma sesión, en el mismo directorio.

Veinte de los veintiséis son la misma historia y merecen leerse enteros: `bayer, bayera, bgr, bgra, bgro, cmyk, cmyka, ftxt, gray, graya, map, mono, pal, rgb, rgba, rgbo, uyvy, ycbcr, ycbcra, yuv`. Todos dan el mismo error:

```
magick: must specify image size `…/m.rgb' @ error/rgb.c/ReadRGBImage/147.
```

Son **formatos de píxeles crudos sin cabecera**. La geometría no está en el fichero: hay que pasarla con `-size`. Y ConvertX invoca `magick ENTRADA -auto-orient SALIDA`, sin `-size`, porque **no tiene dónde guardar ese dato**. La arista es irrecuperable con esa invocación, y no por un fallo del motor: **la información no está en el fichero.** Los otros seis (`avs, g4, msvg, pcl, pix, rgf`) fallan por causas propias de cada formato.

Del lado de ffmpeg, 8 muertas (`avs, avs2, mpc, mtv, rgb, svg, txt, yuv`), la mitad por la misma razón: crudo sin cabecera.

**Aquí también hubo que corregirme.** La primera pasada declaró 48 muertas de ImageMagick; **22 eran falsos negativos de mi arnés**: la sonda buscaba exactamente `x.png` y `magick` escribe `x-0.png`, `x-1.png`… cuando la entrada tiene varios fotogramas o capas. Trece salieron muertas **con stderr vacío**, que es la firma clásica de un fallo del arnés y no del motor: `avi, avif, flv, gif, m2v, m4v, mkv, mov, mp4, mpeg, mpg, psd, ptif, webm, wmv, ept, ept2, ept3, fits, fts, psb, txt`.

### 4.3 De semiaristas a aristas

| | Aristas | % |
|---|---:|---:|
| **Refutadas: alguna mitad muerta en todos sus motores** | **22 235** | **16,05 %** |
| Las dos mitades vivas en algún motor (marco muestral) | 40 252 | 29,06 % |
| Indeterminadas: origen no materializable | 75 874 | 54,78 % |
| Ghostscript / Gotenberg | 140 | 0,10 % |

Causa de las 22 235, según el motor principal: **16 202 por la mitad de salida**, **5 665 por la de entrada**, **368 por las dos**. **[MEDIDO]**

> **El 16,05 % de las aristas declaradas está refutado por ejecución sin haber ejecutado una sola de ellas.** Once minutos de sondas lineales deciden 22 235 aristas cuadráticas. Esa asimetría es el resultado metodológico del informe.

---

## 5. Nivel 2 — muestra aleatoria estratificada sobre el marco

**498 aristas ejecutadas y verificadas**, de las 40 252 del marco. Asignación proporcional al tamaño del estrato, mínimo 12, semilla aleatoria `20260821` anotada en `muestra.json`. Cada salida se sondea y se juzga **en proceso** con el verificador congelado.

| Estrato | N (marco) | n | Nominal | IC 95 % (Wilson) |
|---|---:|---:|---:|---|
| `ffmpeg` · distinta familia | 7 414 | 91 | **76,9 %** | [67,3 % – 84,4 %] |
| `ffmpeg` · misma familia | 8 985 | 111 | **28,8 %** | [21,2 % – 37,9 %] |
| `imagemagick` · distinta familia | 4 760 | 59 | **5,1 %** | [1,7 % – 13,9 %] |
| `imagemagick` · misma familia | 19 093 | 237 | **4,2 %** | [2,3 % – 7,6 %] |
| **Total** | **40 252** | **498** | **23,1 %** | **[19,6 % – 27,0 %]** |

Ponderado por tamaño de estrato: **23,2 %**. La coincidencia con el 23,1 % sin ponderar confirma que la asignación fue prácticamente autoponderada.

Categorías del patrón oro sobre la muestra: **ÍNTEGRO 320 · DEGRADADO 63 · FALLO 112 · DESTRUIDO 3.**

### 5.1 Lo que discrimina no es el motor: es el cruce de familia

**76,9 % frente a 4,2 %: un factor 18 entre el peor estrato y el mejor. [MEDIDO]** Y la explicación no es que ffmpeg sea peor que ImageMagick. Es que **el producto cartesiano de ffmpeg cruza modalidades y el de ImageMagick no**: los 473 formatos de entrada de ffmpeg son vídeo, audio, subtítulos y unos pocos de imagen, y sus 202 salidas también. Declarar `473 × 202` es declarar que se puede convertir un `.aptx` en un `.gif`. Los 245 × 183 de ImageMagick son casi todos imagen contra imagen, y ahí la tabla es casi verdad.

Ejemplos reales de la muestra, con su stderr:

| Arista | Motor | Qué pasa |
|---|---|---|
| `hevc → opus` | ffmpeg | `Error opening output files: Invalid argument` |
| `avif → aptx` | ffmpeg | ídem |
| `gif → caf` | ffmpeg | ídem |
| `mjpeg → m2a` | ffmpeg | ídem |
| `aptx → isma` | ffmpeg | `received no packets` |
| `png → ico`, `cals → icon` | imagemagick | `width or height exceeds limit … WriteICONImage/1086` — el ICO tiene un techo de 256 px y ConvertX **sí** tiene un caso especial para `ico` en `ffmpeg.ts:702` **y no lo tiene en `imagemagick.ts`** |
| `pdb → matte`, `hdr → matte` | imagemagick | `does not have an alpha channel` |
| `epsi → group4` | imagemagick | **N2**: entrega un fichero de texto llamado `.group4` |
| `avif → inline`, `ptif → mov` | imagemagick | **N3**: contenedor sin ninguna pista |

`png → ico` merece un renglón aparte: es una arista **popular**, de las que un producto real sirve todos los días, y falla con la invocación que ConvertX hace de ImageMagick mientras funciona con la que hace de ffmpeg. **La arista no es del par de formatos: es del par (motor, parametrización)**, que es exactamente lo que sostenía `fidelidad-caminos.md` §5.5 ejemplo 4.

### 5.2 Hallazgo lateral: hay aristas que escriben FUERA del destino, y una escribe en el directorio de trabajo

Al terminar la campaña, `git status` sobre la raíz del repositorio mostró **33 ficheros que yo no había pedido**: `chunk-stream0-00001.m4s`, `init-stream0.m4s`, `o0478_map.shtml`, `z0486-17_map.shtml`… Ninguno estaba en el directorio temporal donde se escribían las salidas. **Reproducido después de forma controlada, con la invocación exacta de ConvertX. [MEDIDO]**

| Orden | Escribe en el destino | Escribe **también** |
|---|---|---|
| `ffmpeg -i trivial.mp4 DEST/t.mpd` | `t.mpd` (1 234 B) | **`init-stream0.m4s` (814 B) y `chunk-stream0-00001.m4s` (528 447 B) en el DIRECTORIO DE TRABAJO** |
| `magick trivial.png -auto-orient DEST/u.html` | `u.html` (506 B) **y `u.png` (329 B)** | **`u_map.shtml` (98 B) en el DIRECTORIO DE TRABAJO** |
| `magick trivial.png -auto-orient DEST/u.map` | `u.map` (4 102 B) | — |

Tres consecuencias, en orden de gravedad:

1. **La arista `vídeo → mpd` produce un `.mpd` de 1,2 KB que no sirve para nada**: los 528 KB de vídeo están en dos segmentos que se quedaron en otro directorio. Es una arista que **pasa los cuatro puntos del contrato** —firma correcta, es un manifiesto DASH válido— y no lleva el contenido. Categoría correcta: **DESTRUIDO**. Mi propio arnés la contó como **ÍNTEGRO**, porque solo miraba la ruta de destino.
2. **Es un escape de confinamiento, no una rareza estética.** `RESULTADOS-MCP.md` y `PLAN-ORQUESTADOR.md` §4.6 R8 diseñan el *staging* asumiendo que el motor escribe **donde se le dice**. Estos dos no. Un motor que escribe en el `cwd` del proceso escribe donde esté el orquestador, no donde esté el trabajo. **La contención tiene que ser un directorio de trabajo propio y desechable por conversión, no solo una ruta de salida.**
3. **Una salida puede ser varios ficheros.** `magick … out.html` produce dos: el HTML y el PNG al que apunta. Devolver solo el declarado entrega un documento roto. Y la sonda `--sondear` del verificador, que juzga **un** fichero, no puede verlo.

**Y es una autocrítica de esta medición:** el criterio N3 no detecta este caso, así que en la muestra hay un número desconocido —pequeño, pero no cero— de aristas contadas como reales que entregan un fichero incompleto. **Otra razón por la que el 50,5 % es una cota inferior.**

---

## 6. El estrato prioritario — las aristas que el grafo usa como intermedias

`fidelidad-caminos.md` §1.3 midió que **820 de los 1 599 pares nuevos «pedidos» (51 %) tienen PDF como único intermedio posible**. Si una arista hacia PDF fuera nominal, se caería media tesis del multi-salto. Se muestrean **100 de las 311 aristas del marco que tocan PDF** (537 en el grafo declarado: 352 hacia PDF, 185 desde PDF).

| | Resultado |
|---|---|
| **Nominales** | **3 de 100 → 3,0 %**, IC 95 % **[1,0 % – 8,5 %]** |
| Categorías | ÍNTEGRO 85 · DEGRADADO 12 · DESTRUIDO 1 · FALLO 2 |

> **Las aristas hacia y desde PDF son, con diferencia, las más reales del grafo: 3,0 % nominales frente al 23,1 % general.** El «pásalo por PDF» que `fidelidad-caminos.md` llamaba *«un caso especial resuelto a mano hace años»* **es también el único trozo del grafo cuyas aristas se sostienen al ejecutarlas.** **[MEDIDO]**

Las tres nominales son ilustrativas y las tres estaban previstas:

| Arista | Categoría | Qué pasa |
|---|---|---|
| `pdf → txt` (IM) | DESTRUIDO | **156 520 548 B desde 91 324 B**. Reproduce, con otro fichero y otro arnés, el hallazgo H4 de `fidelidad-caminos.md` §3: el «TXT» de ImageMagick es la enumeración de los píxeles |
| `pdf → cur` (IM) | FALLO | rc=1, 0 bytes |
| `pdf → ico` (IM) | FALLO | rc=1, 0 bytes — el mismo techo de 256 px |

Y los 12 DEGRADADO son **once veces la misma regla**: `P7 · 1 px → 1 pt: página absurda (1920 × 1080 pt = 677 × 381 mm)`, en `png → pdf`, `jpeg → pdf`, `gif87 → pdf`, `group4 → pdf`, `png48 → pdf`, `pjpeg → pdf`, `sf3 → pdf`… **La arista `imagen → pdf` de ImageMagick existe y funciona; lo que está mal es que nadie declara la densidad.** Es la regla P7 del patrón oro y el par I5/I6 de `fidelidad-caminos.md`, encontrado ahora de forma masiva y sistemática: **no es un caso, es el comportamiento por defecto de todas las aristas `imagen → pdf`.**

---

## 7. Los tres escenarios, y por qué el central es el defendible

El 54,78 % indeterminado no se rellena con una suposición escondida. Se reparte así:

| Motor del estrato indeterminado | Aristas | Residual medido en su marco | Semiarista de entrada muerta medida |
|---|---:|---:|---:|
| ffmpeg | 60 664 | 50,6 % | 7,0 % |
| imagemagick | 15 210 | 4,4 % | 16,2 % |

El **escenario B** aplica a cada trozo la tasa medida de **su propio motor** —no la global— y da **48,6 %**. Es el defendible por dos razones: (a) las 359 entradas no materializables de ffmpeg son formatos exóticos de un solo propósito (audio de telefonía, contenedores de videojuegos antiguos) que se combinan con las mismas 202 salidas, o sea **más cruce de familia, no menos**; y (b) las 86 de ImageMagick son en su mayoría los mismos crudos sin cabecera que ya fallaron.

**PENDIENTE:** cerrar el estrato indeterminado exige un corpus de ficheros de esos 445 formatos. No existe en esta máquina y fabricarlos no es posible con los motores locales — por definición, son los que ningún motor local escribe. La vía realista es el *corpus* FATE de ffmpeg (~1 GB de descarga) o los bancos de muestras de cada formato.

---

## 8. C8 — los siete casos `no_evaluable` de `referencia.json`

`bench/salidas-referencia/referencia.json` deja 7 conversiones sin veredicto por falta de motor. **Lo que falta va en contenedor, no instalado a mano.** Y el contenedor ya estaba ahí: **la imagen de ConvertX trae 6 de los 7 motores que faltan en Windows.**

> **Cambio de estado que provoqué yo, igual que `fidelidad-caminos.md` §0:** Docker Desktop estaba **parado** al empezar (`npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`, y `:3100`/`:3200` rechazando conexión). Lo relancé; los cinco contenedores volvieron solos. **Quedan levantados.** No cerré nada.

Inventario de `filex-convertx` (Debian forky/sid), comprobado con `command -v`: **[MEDIDO]**

| Presente | Ausente |
|---|---|
| `soffice`, `libreoffice`, `pandoc`, `ebook-convert` (Calibre), `vips`, `inkscape`, `resvg`, `magick`, `ffmpeg`, `gs`, `assimp`, `dasel`, `potrace`, `vtracer`, `dvisvgm`, `xelatex`, `msgconvert`, `cjxl`, `djxl`, `heif-enc`, `python3` | **`qpdf`**, **`tesseract`** |

Resultado de las 30 conversiones lanzadas dentro del contenedor (`c8_dentro.sh`), verificadas **fuera** con el verificador congelado:

| # | Caso `no_evaluable` | Motor | Veredicto | Evidencia |
|---|---|---|---|---|
| 1 | DOCX/XLSX/ODT ↔ PDF | LibreOffice | **CERRADO** | `docx→pdf`, `xlsx→pdf`, `odt→pdf`, `docx→odt`, `pdf→docx` (con `--infilter=writer_pdf_import`): **5/5 rc=0**, centinela y tabla presentes en las cinco salidas |
| 2 | Markdown/HTML/DOCX ↔ otros | Pandoc | **CERRADO** | `md→docx`, `docx→md`, `html→docx`, `md→html`, `docx→pdf` (xelatex), `epub→md`, `md→epub`, `docx→rtf`: **8/8 rc=0**, centinela y tabla en las ocho |
| 3 | EPUB/MOBI/AZW3 ↔ otros | Calibre | **CERRADO** | `epub→pdf`, `epub→mobi`, `epub→azw3`, `azw3→epub`, `mobi→epub`, `epub→docx`: **6/6 rc=0** |
| 4 | SVG → PNG/PDF con fidelidad tipográfica | Inkscape / resvg / magick | **CERRADO, y con hallazgo** | ver §8.2 |
| 5 | PDF escaneado → PDF con capa de texto (OCR) | Tesseract / ocrmypdf | **NO CERRADO** | **la imagen de ConvertX no lleva `tesseract`**. Es el encargo C2 de V1, con el Tesseract embebido en Ghostscript: no se duplica aquí |
| 6 | PDF → PDF linealizado / cifrado | qpdf | **NO CERRADO** | `qpdf --linearize` y `qpdf --encrypt`: **rc=127, no existe el binario**. Ningún contenedor levantado lo trae |
| 7 | imagen → imagen con libvips | vips | **CERRADO** | `png→jpg`, `png→webp`, `png→tif`: **3/3 rc=0**, firmas `jpeg`/`webp`/`tiff` correctas |

**Cinco de siete cerrados sin instalar nada en Windows.** El coste de integración real es: **dos motores** (`qpdf`, `tesseract`) que habría que añadir a una imagen, no siete.

### 8.1 `epub → pdf`: la arista nominal más citada del proyecto, refutada como universal

`fidelidad-caminos.md` §1.4 y el enunciado de este encargo la señalan como *el mejor ejemplo de arista nominal del proyecto*: Gotenberg declara `.epub` y LibreOffice devuelve HTTP 500 con tres EPUB distintos. **No se ha repetido esa medida.** Se han hecho otras dos, que la sitúan:

| Vía | Resultado |
|---|---|
| **LibreOffice dentro de `filex-convertx`** (`soffice --headless --convert-to pdf entrada.epub`) | **rc=1, sin salida.** **[MEDIDO]** |
| **Calibre dentro de `filex-convertx`** (`ebook-convert entrada.epub c_epub.pdf`) | **rc=0, PDF de 26 817 B, 565 caracteres recuperados, centinela `FILEXSENTINELA7743` y la tabla `AX-1` presentes.** 7 045 ms **[MEDIDO]** |

**Dos consecuencias, y la segunda cambia una regla de diseño.**

1. **El fallo es de LibreOffice, no de Gotenberg.** Se reproduce con otro build, en otro sistema operativo, invocando `soffice` directamente. LibreOffice **exporta** EPUB y no lo **importa**; que Gotenberg liste `.epub` en `Api.Extensions()` es una tabla declarada que su motor no cumple.
2. **`epub → pdf` NO es una arista nominal del grafo: es una arista nominal *de un motor*.** Con Calibre existe y funciona. Y ConvertX **tiene** adaptador de Calibre (`calibre.ts`, 26 entradas / 20 salidas). O sea que el ejemplo estrella del hueco 2 —`epub → png` en dos saltos— **es alcanzable**; lo que falla es **la elección de motor**, que es el bug conocido de `ConvertX/src/converters/main.ts:213-229`.

> **Esto refuerza, no debilita, la conclusión de `fidelidad-caminos.md` §6:** *«lo que se sostiene del grafo es la selección correcta con coste explícito»*. La arista existe; el orquestador elige el motor que no la implementa. **La unidad del grafo no puede ser el par de formatos: tiene que ser `(formato_origen, formato_destino, motor, parametrización)`.**

### 8.2 SVG: el rasterizador que devuelve un PNG perfecto y sin una sola letra

El caso 4 pide «SVG → PNG/PDF **con fidelidad tipográfica**». Se rasteriza el mismo `e1.svg` (dos textos, uno *sans* y uno *serif*, más figuras) con tres rasterizadores y se mide la **tinta en la banda del texto** (`y = 155…205`), que es lo que la palabra «tipográfica» significa:

| Rasterizador | Bytes | Geometría | **Tinta en la banda de texto** | Tinta total | rc |
|---|---:|---|---:|---:|---:|
| Inkscape (contenedor) | 13 456 | 400×200 | **14,02 %** | 13,38 % | 0 |
| **resvg 0.46.0 (contenedor)** | 8 973 | 400×200 | **0,00 %** | 8,78 % | **0** |
| magick 7.1.2 (Windows) | 8 628 | 400×200 | **15,07 %** | 13,39 % | 0 |
| magick (contenedor Debian) | — | — | — | — | **1** |

RMSE entre pares: Inkscape↔resvg **0,1294**; Inkscape↔magick-Windows **0,1381**; resvg↔magick-Windows **0,1369**.

**resvg devuelve código de salida 0, un PNG con firma PNG válida, de la geometría exacta pedida — y sin una sola letra. [MEDIDO]** Los cuatro puntos del contrato de verificación lo dan por bueno: firma correcta, flujos correctos, propiedades correctas, pedido = obtenido. Lo único que delata el fallo está en `stderr`:

```
Warning (in usvg::text:129): No match for '"DejaVu Sans", sans-serif' font-family.
Warning (in usvg::text:129): No match for 'serif' font-family.
```

…y el contenedor **tiene 153 fuentes instaladas** (`fc-list | wc -l`). No es un problema de fuentes: es que ese build de resvg no resuelve familias.

**Esto es material nuevo para `HUECOS.md` §1, la lista de fallos de verificación documentados.** Es un caso que **ninguno de los cuatro puntos del contrato atrapa** y que **sí** atraparía una regla de fidelidad: *si el origen SVG contiene elementos `<text>`, la salida rasterizada debe tener tinta donde estaban*. Coste: una comparación de tinta por banda, del orden de los 26 ms que `verificador-fidelidad.md` mide para el grupo C.

**Y una nota de portabilidad medida:** `magick svg → png` **funciona en el ImageMagick de Windows y falla (rc=1) en el de Debian del contenedor**. La misma arista, el mismo motor, la misma versión mayor: real en una máquina y nominal en otra. **[MEDIDO]** Cualquier tabla de aristas que no lleve el *build* como dimensión está mintiendo en alguna máquina.

---

## 9. Consecuencias para el diseño de FileX

1. **Sondear el mapa de capacidades al arrancar, no leer tablas.** Cuesta **1 104 sondas** y **11 minutos** en frío para ffmpeg + ImageMagick, y decide el 45 % de la población de aristas. `fidelidad-caminos.md` §5.2 proponía un término `T` con **+50 para «arista nominal (nunca ejecutada con éxito aquí)»** y **∞ para «arista refutada»**. Con este censo, **el +50 desaparece**: para las semiaristas ya no hay que adivinar. Queda el ∞ para lo refutado y una penalización solo para el residuo de composición.
2. **El nodo del grafo no puede ser el formato, y la arista no puede ser el par.** Cuatro medidas independientes lo dicen: `epub→pdf` es real con Calibre y nominal con LibreOffice (§8.1); `png→ico` es real por ffmpeg y nominal por ImageMagick (§5.1); `svg→png` es real en Windows y nominal en Debian (§8.2); los crudos sin cabecera son irrecuperables **con la invocación de ConvertX** y triviales con `-size` (§4.2). La arista mínima viable es **`(origen, destino, motor, parametrización, build)`**.
3. **Los formatos crudos sin cabecera necesitan un canal para la geometría.** Son **20 de los 26** formatos que ImageMagick declara leer y no lee. O FileX guarda la geometría fuera del fichero y la pasa con `-size`, o esos 20 formatos no son formatos de entrada y hay que **borrarlos del catálogo declarado**. Declararlos y no poder cumplirlos es lo que `saturacion-herramientas.md` §8 identificó como **fallo silencioso**, y por eso la cobertura declarada de `convert` es un requisito de seguridad.
4. **`imagen → pdf` necesita densidad explícita, siempre.** Once de doce degradaciones del estrato PDF son la regla P7. No es un caso raro: es el **defecto** de esa familia de aristas.
5. **La verificación por firma solo cubre el 12 % de los destinos.** El vocabulario de firmas del verificador (24 nombres) es suficiente para los formatos que la gente pide y **claramente insuficiente** para el catálogo declarado. ~~Si FileX declara 500 formatos de salida, tiene que poder verificar 500 firmas — o **declarar menos**.~~

   > **Matizado el 22/08 (`bench/firmas-contrato.md` §3): NO SE PUEDEN VERIFICAR 500 FIRMAS PORQUE NO EXISTEN 500 FIRMAS.** De **381 formatos con veredicto, 90 (23,6 %) no tienen marcador**. La frase correcta es *«o verifica las que existen y declara `no_aplica` en las que no, o declara menos»*. Ampliar el vocabulario llevó el punto 1 del **12,4 % al 54,2 %** — **pero por firma dispara `fallo` en 0 de las 598**, y quien de verdad sube la cifra es **G6** (19 aristas, 17 de ellas que este informe contó como REALES).
6. **El multi-salto sale reforzado justo donde `fidelidad-caminos.md` lo dejaba:** las aristas hacia y desde PDF son las más sólidas del grafo (3,0 % nominal). La propina es pequeña, pero **la propina existe y sus aristas son reales**.
7. **Un directorio de trabajo propio y desechable por conversión, no solo una ruta de salida.** §5.2: ffmpeg escribe los segmentos DASH y ImageMagick el mapa de imagen **en el `cwd` del proceso**. Y **una conversión puede producir varios ficheros**: `magick … out.html` entrega un HTML y el PNG al que apunta. El contrato de verificación necesita un quinto punto —*«¿el motor escribió algo fuera de lo declarado?»*— que es trivial de implementar (listar el directorio de trabajo antes y después) y que hoy no tiene nadie.

---

## 10. Qué queda en disco

`bench/salidas-aristas/` — **1,2 MB** tras podar. Se borraron: `pool/` (**711 MB** de semillas materializadas), `tmp*/`, `aristas.json` (5,8 MB) y `marco.json` (0,9 MB), todos regenerables. `MANIFIESTO.md` lleva nombre, `sha256`, tamaño y **la orden exacta** de cada uno.

| Fichero | Qué es |
|---|---|
| `censo.json`, `log-semi-*.txt` | Nivel 0 y nivel 1: capacidades por nombre y por ejecución |
| `semi_salida.json` / `semi_salida2.json` | Censo de semiaristas de salida, con las dos vueltas y el stderr de cada intento |
| `semi_entrada.json` / `semi_entrada2.json` | Ídem de entrada, con la procedencia de cada semilla |
| `agregado.json`, `resultado.json`, `escenarios.json` | La contabilidad a nivel de arista y la cifra con su IC |
| `muestra.json` | Las 598 aristas ejecutadas (498 generales + 100 del estrato PDF), una por una, con orden, rc, bytes, firma, categoría y motivo |
| `testigo.jsonl` | Las seis medidas del testigo de CPU |
| `c8/resultado.tsv`, `c8/verificado.json`, `c8/svg_comparacion.json` | Las 30 conversiones de C8 y su verificación |
| `c8/out/` | Las salidas de C8 (170 KB; se borró `v.tif`, 16 MB) |
| `fuga/` | La reproducción controlada de §5.2: los ficheros que ffmpeg y `magick` escriben fuera del destino |
| `_censo.py … _svg_comp.py`, `c8_*.sh/py` | Los instrumentos, reproducibles |
| `verificador_congelado.py` | Copia congelada del verificador de V1 (sha256 `c753ca43…`), para que la medida no dependa de sus ediciones en curso |

---

## 11. Lo que este informe NO ha medido — **[PENDIENTE]**

1. ~~**El 54,78 % indeterminado.** Exige un corpus de los 445 formatos que ningún
   motor local escribe. Es la única vía para pasar del escenario B a un número
   medido (§7).~~ **AVANZADO el 03/09/2026 por worker2** (`bench/fate-y-aristas.md`
   §2, ronda 11, corpus FATE ya en disco): con ficheros reales sobre **69 de los
   445** formatos (sesgo de cobertura declarado, no muestra aleatoria de los 445),
   la semiarista de entrada sale VIVA en el **97,1 %** y una muestra de aristas da
   **66,9 %** (criterio más barato que el contrato de 5 puntos) — las dos MUY por
   encima del 48,6 % de Escenario B, cerca del 77,5 % de Escenario C. **No cierra
   el 54,78 % entero**: sigue PENDIENTE para los 376 formatos que FATE no nombra
   igual.
2. **La otra mitad del sesgo de materialización.** Todas las semiaristas de entrada se probaron con ficheros escritos por el propio motor. Con ficheros de terceros la tasa **subiría**, y no se sabe cuánto. El caso `txt` (§2, sesgo 2) muestra que la diferencia puede ser total.
3. **El 88 % de destinos donde N2 no es evaluable.** Son **436 de las 498** aristas de la muestra: en ellas, una salida con la firma equivocada pasa como buena. Ampliar el vocabulario de firmas del verificador (hoy 24 nombres) es trabajo de V1, y **solo puede subir el 50,5 %, nunca bajarlo**.
4. **Los 140 aristas de Ghostscript y Gotenberg** no se han muestreado: son el 0,10 % de la población, pero son **toda** la superficie documental del grafo. `fidelidad-caminos.md` ya ejecutó 69 caminos sobre ellas; falta el censo.
5. **La invocación alternativa.** Todo se ha medido con la invocación de ConvertX. Cuánto de ese 50,5 % se recupera con una invocación mejor (`-size` para los crudos, `-map 0`, `-density`, `-f` explícito) **no se ha medido**, y es la pregunta que decide si FileX puede prometer más aristas que ConvertX con los mismos motores. Es probablemente el pendiente de más valor que abre este informe.
6. **Si esas conversiones se piden.** Sigue abierto lo que ya señalaban `HUECOS.md` §2 y `fidelidad-caminos.md` §7.1. Una arista nominal en un formato que nadie pide no cuesta nada; una en `png → ico`, sí.
7. **qpdf y Tesseract** siguen sin motor en ninguna imagen levantada (§8, casos 5 y 6).
