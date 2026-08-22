# Cuánto del 50,5 % es invocación y no capacidad

**Qué contesta este documento.** `bench/aristas-nominales.md` §11.5 deja abierta la pregunta que decide una promesa de producto, y la señala como *«probablemente el pendiente de más valor que abre este informe»*:

> «Todo se ha medido con la invocación de ConvertX. Cuánto de ese 50,5 % se recupera con una invocación mejor (`-size` para los crudos, `-map 0`, `-density`, `-f` explícito) **no se ha medido**, y es la pregunta que decide si FileX puede prometer más aristas que ConvertX con los mismos motores.»

Aquí se mide. No se repite el trabajo de E1: se **parte de sus fallos ya clasificados** —las 34 semiaristas de entrada muertas, las 37 de salida y las 118 aristas nominales de su muestra— y se reintenta cada una, una a una, con una política de invocación declarada antes de medir. Es un **censo de los fallos de E1**, no una submuestra nueva: la única incertidumbre muestral que entra es la que ya traía su 23,1 %.

Toda afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**.

- Datos crudos e instrumentos: `bench/salidas-invocacion/` (ver §12 y su `MANIFIESTO.md`)
- Verificación: copia congelada de `bench/scripts/verificador.py` → `verificador_p2.py`, sha256 `cb3e479b6a75dddf…`, 3 532 líneas, usada **en proceso**. P3 está editando el original en paralelo; congelarlo evita medir contra un blanco móvil, exactamente como hizo E1.
- **El juez no se ha tocado.** `_p2_lib.juzga()` es copia literal de `_muestra.py:99` de E1. Si el criterio de «nominal» cambiara, la comparación antes/después mediría el juez y no la invocación.
- Contención: no se ha usado la GPU (P1 la tiene en exclusiva), no se han tocado los documentos maestros, ni `referencia.json`, ni `bench/scripts/`, ni `bench/salidas-aristas/` (solo lectura).

---

## 0. La cifra

> ### **El 18,8 % del 50,5 % es invocación, no capacidad.**
> **IC 95 %: [16,8 % – 21,3 %]. [MEDIDO]**
>
> Con los **mismos motores, el mismo build y el mismo corpus**, la tasa de aristas nominales baja de **50,5 %** a **41,0 %**: **5 930 aristas de las 31 533** que E1 declaró inexistentes sí existen y lo que fallaba era la orden.

Y el reparto en las tres categorías del encargo **es el resultado**, porque cambia lo que se puede prometer:

| Categoría | Qué significa | Aristas | % del 50,5 % |
|---|---|---:|---:|
| **1 · Recuperable con bandera** | la arista existe y ConvertX la llama mal. **Ganancia automática para FileX** | **3 226** | **10,2 %** |
| **2 · Recuperable con un parámetro del usuario** | existe, pero el dato **no está en el fichero** (geometría y profundidad de los crudos). **Es una arista, no una arista automática** | **2 704** | **8,6 %** |
| **3 · Irrecuperable** | el motor no puede: no hay pista compatible, o el codificador no está compilado | **25 603** | **81,2 %** |

> **La respuesta a la pregunta del encargo es «una quinta parte, y la mitad de esa quinta parte no es gratis».** FileX **sí** puede prometer más aristas que ConvertX con exactamente los mismos motores instalados —**+3 226 aristas sin pedir nada al usuario, +2 704 más si hay un canal para los metadatos**—, pero **cuatro de cada cinco aristas que el sector declara de más siguen sin existir después de invocarlas bien**. La tesis de E1 sobrevive casi intacta; lo que cambia es que ahora tiene una cota, y la cota es del producto, no del sector.

**Sensibilidad.** Si las 4 627 aristas que resucitan por semiarista conservaran el residuo nominal de E1 (23,1 %) en vez del residuo mejorado (17,8 %), la cifra sería **18,0 %** en vez de 18,8 %. La conclusión no depende de ese supuesto.

---

## 1. La política de invocación, declarada antes de medir

Sin esto la medición no vale nada: reintentar caso por caso hasta que salga verde no mide una política, mide mi terquedad. **P2-INV** está escrita entera en la cabecera de `_p2_lib.py` y se fijó **antes** de la primera ejecución. Las tres reglas marcadas con ⚠ se añadieron después y **cada una nació de un error propio**, que se documenta en §7.

| Regla | Motor | Qué hace | Categoría que produce |
|---|---|---|---|
| **G** | magick | `-size WxH -depth N` para los formatos crudos sin cabecera | **2** — la geometría no está en el fichero |
| **X** | magick | prefijo `FMT:` explícito en entrada y salida, para no depender de la extensión | 1 |
| **L** | magick | `-resize 256x256>` + `-define icon:auto-resize=…` para destinos con techo duro (`ico`, `icon`, `icn`, `cur`) | 1 |
| **A** | magick | `-alpha set` cuando el destino exige canal alfa (`matte`, `mask`, `clip`) | 1 |
| **D** | magick | `-units PixelsPerInch -density N` para destinos paginados desde raster | 1 |
| **M** | ffmpeg | `-map 0:<tipo>` **explícito** para cada tipo de pista compatible (CLAUDE.md §5) | 1 |
| **C** | ffmpeg | `-c:v`/`-c:a` = el codec **por defecto del muxer**, sondeado con `ffmpeg -h muxer=X` | 1 |
| **F** | ffmpeg | `-f <muxer>` explícito; y `-f rawvideo -pixel_format -video_size` en la entrada cruda | 1 / 2 |
| **R** | ffmpeg | restricciones que el **propio codificador declara** (`ffmpeg -h encoder=X`): `gsm` solo admite 8 000 Hz mono | 1 |
| ⚠ **R2** | ffmpeg | barrer **todas** las tasas declaradas, no quedarse con la primera | 1 |
| ⚠ **P** | ffmpeg | **perfil de codec**: tabla pequeña y declarada de geometrías fijas (DV = 720×576@25, X-Face = 48×48) | 1 |
| ⚠ **U** | ffmpeg | `-frames:v 1 -update 1` cuando el destino es **una imagen única** y la entrada tiene varios fotogramas | 1 |
| ⚠ **C2** | ffmpeg | si el token de destino **nombra un codificador** (`vbn`, `xface`), se usa ese y no el defecto del muxer | 1 |
| ⚠ **NO-C** | ffmpeg | **excepción a C**: con el muxer `image2` **no se fuerza el códec**. Ver §7.2 | — |

Y **una regla negativa, que es la que hace honesta la medida**:

> **Si el muxer solo admite un tipo de pista que la entrada no tiene, la arista es IRRECUPERABLE (categoría 3) y no se fabrica la pista que falta.** Convertir un `hevc` sin audio en un `opus` exigiría inventar el audio. **69 de las 118 aristas nominales de E1 caen exactamente aquí.**

Las tres desviaciones de CLAUDE.md §5 se mantienen en las dos invocaciones y en las dos ramas de la comparación: **`stdin=DEVNULL` primero, `-y`/`-nostdin` después, timeout duro**. Son disciplina, no política, y por tanto **no forman parte de lo que se está midiendo**.

### 1.1 Qué cuenta como recuperación

Tres condiciones, y las tres a la vez. **`rc=0` no basta.**

1. La invocación de ConvertX sobre **esa misma entrada** tiene que fallar (línea base ejecutada en cada caso: **1 discrepancia sobre 118**, §2.2).
2. La salida de P2-INV tiene que pasar el **mismo juez** que usó E1 (N1/N2/N3) y salir **ÍNTEGRO**, **PÉRDIDA INEVITABLE** o **DEGRADADO** — nunca **DESTRUIDO** ni **FALLO**.
3. La salida tiene que **ser del formato pedido**, comprobado por un tercero. §7.3 explica por qué esta tercera condición no es redundante: **eliminó 4 de las 32 «recuperaciones» que las dos primeras daban por buenas.**

---

## 2. Método y sesgos, declarados antes de los resultados

1. **Es un censo de fallos, no una muestra nueva.** Se reintentan **las 34 + 37 semiaristas muertas** (censo exacto) y **las 118 aristas nominales** de la muestra de 498 + 100 de E1 (censo de sus fallos). La única incertidumbre muestral es la de E1: sus 118 nominales estiman el residuo del marco.
2. **Las cifras de E1 se reprodujeron primero, sin tocarlas.** `_p2_censo.py` da **exactamente 138 501** aristas y `_p2_agrega.py` **exactamente 40 252 / 22 235 / 75 874 / 140**. Sin esa reproducción no habría a qué restar. **[MEDIDO]**
3. **El sesgo de materialización de E1 se hereda entero, y se agrava en un punto.** Las semillas las escribe el propio motor que luego las lee. Para los crudos sin cabecera eso es *más* favorable de lo que parece, porque el motor conoce su propio empaquetado; con un `.rgb` de un tercero la profundidad podría no ser 16 bits. **La tasa de recuperación de los crudos es, por construcción, una cota superior.**
4. **El vocabulario de firmas sigue cubriendo poco.** El punto 1 del contrato solo es evaluable en el 12 % de los destinos (E1 §2, sesgo 3). Por eso se añadió el control de §7.3 con `magick identify` y `ffprobe` como terceros.
5. **Un solo build.** `ffmpeg N-121159`, `ImageMagick 7.1.2-21 Q16-HDRI`, `Ghostscript 10.07`, `Gotenberg 8`, `ConvertX` de `ghcr.io/c4illin/convertx:latest`. §5 muestra que **el build decide 19 de las 33 semiaristas de salida muertas de ffmpeg**: en otro build la respuesta cambia.
6. **Dos intentos por problema.** Cada bloque tiene exactamente dos vueltas. Lo que no revivió en la segunda queda documentado con su error exacto y no se vuelve a tocar.
7. **No hay ninguna conclusión que sea un tiempo.** Los ms de los datos crudos son orientativos.

### 2.1 Los dos testigos de ruido

Con dos agentes más corriendo (P1 en GPU, P3 en CPU), un solo testigo no vale: el monohilo es ciego a la contención multinúcleo (`verificador-ghostscript.md` §4).

| Momento | Deriva (SHA-256 ×400 000, mediana de 7) | Nivel (`ffprobe -version`, mediana de 9) |
|---|---:|---:|
| al cerrar la campaña | 367,93 ms | **25,64 ms** |
| al terminar | **331,15 ms** | **25,35 ms** |
| referencia de E1 (mínimo) | 330,39 ms | — |
| calibración en reposo | — | 26,5 – 26,8 ms |

**Los dos testigos dicen lo mismo: la máquina estaba tranquila.** La deriva final queda a **+0,2 %** del mínimo de E1 y el nivel de lanzamiento está **por debajo** de la calibración en reposo. **[MEDIDO]** Sigue siendo **SUCIA estructural** por la sesión de escritorio remoto, como todo en este repositorio.

### 2.2 Disciplina de ejecución

**917 invocaciones de motor** en los cuatro bloques de C15 y C17 (364 en semiaristas, 288 en el residuo, 116 en los crudos, 149 en C17), más las de C13. **[MEDIDO]**

- **1 solo *timeout*** (`mkv → wpg` de ImageMagick, 45 s).
- **0 procesos huérfanos** al terminar (`Get-Process magick,ffmpeg,ffprobe,gswin64c` → 0).
- **0 ficheros parásitos en la raíz del repositorio.** Todo se ejecutó con `cwd` en un directorio desechable, que es la regla R18 que E1 propuso; §7.4 cuenta lo que apareció dentro de él.
- **1 discrepancia con E1 sobre 118**: `png → ico` de ImageMagick, que aquí **no falla** con la invocación de ConvertX. La causa es la semilla: E1 usaba `pool/in/m.png` (1920×1080, escrito desde el JPEG del corpus) y aquí el corpus aportó un PNG más pequeño. **Se excluye del numerador y se deja en el denominador**, que es la lectura conservadora.

---

## 3. La mitad que más aristas mata: las semiaristas

E1 demostró que **una semiarista muerta mata de golpe todas las aristas que la usan**: 22 235 aristas (16,05 % de la población) refutadas por 71 sondas. Es también donde más se puede recuperar, y por la misma razón.

| | Muertas en E1 | **Revividas con P2-INV** | | IC 95 % |
|---|---:|---:|---:|---|
| Semiaristas de **entrada** | 34 | **22** | **64,7 %** | [47,9 – 78,5] |
| Semiaristas de **salida** | 37 | **8** | **21,6 %** | [11,4 – 37,2] |
| **Aristas que eso devuelve al marco** | | **4 627** | | censo, sin error muestral |

**[MEDIDO]** El desequilibrio entre las dos filas es el hallazgo estructural de esta sección y tiene una explicación de una línea: **leer mal es un problema de invocación; escribir lo que el binario no sabe codificar es un problema de build.**

### 3.1 Las 22 semiaristas de entrada que reviven

| Motor | Formatos | Regla | Categoría |
|---|---|---|---|
| imagemagick | `bgr, bgra, cmyk, cmyka, gray, graya, mono, pal, rgb, rgba, rgbo, uyvy, ycbcr, ycbcra, yuv` (15) | **G + X** | **2** |
| imagemagick | `bayer, bayera` (2) | **G + X** | **2**, y **[PENDIENTE]** de referencia de fidelidad (§4.3) |
| imagemagick | `avs` (1) | semilla pequeña: el fallo era `unable to extend cache … No space left on device`, un **límite de recurso**, no de formato | 1 |
| imagemagick | `pix` (1) | **X** (prefijo explícito) | 1 |
| ffmpeg | `rgb, yuv` (2) | **F** en la entrada (`-f rawvideo -pixel_format -video_size`) | **2** |
| ffmpeg | `txt` (1) | **M + C + F** | 1 |

Y las **12 que no reviven**, con su causa exacta **[MEDIDO]**:

| Formato | Motor | Por qué no |
|---|---|---|
| `bgro` | magick | **`0xC0000005`**. El escritor emite **6 bytes por píxel** para un formato de **4 canales** (12 bits/canal, que no es un ancho válido) y el lector se sale de memoria. Es autoinconsistencia del mismo binario, y **cae sin código de error útil** — el mismo patrón que la trampa 18 de CLAUDE.md con `-sOCRLanguage=osd` |
| `map` | magick | el lector exige un **fichero de paleta aparte** (`No such file or directory @ error/map.c/ReadMAPImage/255`). El dato no está ni dentro del fichero ni en un parámetro |
| `ftxt` | magick | revive con `rc=0` **y entrega basura**: RMSE **0,652** contra la referencia. §4.2 |
| `g4, msvg, pcl, rgf` | magick | causas propias de cada formato, sin relación con la invocación |
| `avs, avs2` | ffmpeg | el decodificador `davs2` arranca y no produce fotogramas |
| `mpc, mtv` | ffmpeg | `Invalid data found when processing input` sobre un fichero que el propio ffmpeg escribió |
| `svg` | ffmpeg | `no decoder found for: svg`. **No es invocación: ffmpeg no lleva rasterizador SVG** |

### 3.2 Las 8 semiaristas de salida que reviven, y las 19 que son del build

**El resultado más limpio de esta sección es una separación, no una recuperación.** Sondeando `ffmpeg -encoders` contra el códec por defecto de cada muxer, las 33 semiaristas de salida muertas de ffmpeg se parten en tres grupos que no admiten discusión:

| Grupo | Cuántas | Formatos |
|---|---:|---|
| **El codificador NO está compilado en este build** | **19** | `ac4, avs3, bit(g729), c2(codec2), cavs, cvg(adpcm_psx), dts, evc, gsm, js, jss(jacosub), lbc(ilbc), oma(atrac3), rcv(wmv3), scc(eia_608), spx(speex), sub(microdvd), sup(hdmv_pgs), vc1` |
| **El muxer no declara ningún códec por defecto** | 2 | `chk` (`webm_chunk`), `xml` (`webm_dash_manifest`) — son muxers de *sidecar* DASH, no destinos de conversión |
| **El codificador existe y la invocación fallaba** | **12** | de los cuales **8 reviven** |

Las 8 que reviven, todas validadas con `ffprobe` sobre la salida **[MEDIDO]**:

| Formato | Regla decisiva | Salida comprobada |
|---|---|---|
| `302` | R2: `-ar 96000 -ac 6` (el muxer `daud` no admite otra cosa) | `format_name=daud`, `pcm_s24daud`, 1 728 192 B |
| `dnxhd`, `dnxhr` | **P**: `-s 1920x1080 -r 25 -pix_fmt yuv422p -b:v 120M` | `format_name=dnxhd`, 1920×1080 |
| `dv` | **P**: `-s 720x576 -r 25 -pix_fmt yuv420p` | `format_name=dv`, `dvvideo` + `pcm_s16le`, 720×576 |
| `flm` | **P**: `-pix_fmt rgba` | `format_name=filmstrip`, `rawvideo` |
| `tun` | R2: `-ar 11025 -ac 1` | `format_name=alp`, `adpcm_ima_alp` |
| `vbn` | **C2**: `-c:v vbn`, no el `mjpeg` por defecto de `image2` | `format_name=vbn_pipe`, `codec_name=vbn` |
| `xface` | **C2 + P**: `-c:v xface -s 48x48` | `codec_name=xface`, 48×48 |

Las 4 que siguen muertas tras barrer el espacio de parámetros declarado (`amv`, `gxf`, `mlp`, `thd`) dan todas `received no packets`. Dos intentos gastados; **[PENDIENTE]**.

Las 4 de ImageMagick (`clip`, `jpt`, `mask`, `thumbnail`) tampoco reviven, y por una razón que conviene decir: **tres de ellas no son destinos de conversión, son extractores de propiedad**. `clip` exige una ruta de recorte, `mask` un canal de máscara y `thumbnail` una miniatura EXIF; `-alpha set` no fabrica ninguna de las tres. `jpt` da `unable to encode image file` en el delegado JPEG-2000. **Que ConvertX los declare como formatos de salida es un error de catálogo, no una arista rota.**

---

## 4. Los crudos sin cabecera: la medición que hubo que rehacer tres veces

E1 §4.2 los señala como el mejor punto de partida: **20 de los 26 formatos que ImageMagick declara leer y no lee** son formatos de píxeles crudos que fallan con `must specify image size`, y **ConvertX no tiene dónde guardar ese dato**. Son también el bloque que más aristas mueve: 3 290 de las 4 627 recuperadas.

**La respuesta corta: sí reviven, 17 de 20, pero hacen falta DOS datos externos, no uno.**

### 4.1 La profundidad es tan externa como la geometría — y ese fue mi error

`-size WxH` no basta. Este ImageMagick es **Q16-HDRI** y escribe los crudos a **16 bits por canal**: un `.rgb` de 64×48 ocupa **6 bytes por píxel**, no 3. Leerlo con `-depth 8` **no falla**: consume la mitad del fichero, entrega una imagen **de la geometría exacta pedida** y con los píxeles equivocados.

> **Ese es el fallo que el punto 4 del contrato no atrapa, encontrado esta vez desde dentro.** Firma correcta, flujos correctos, propiedades correctas, **pedido = obtenido** — y la imagen es basura. Es el mismo hueco que `aristas-nominales.md` §8.2 documentó con `resvg`, ahora en otro motor y por otro camino. **Lo único que lo detecta es una comparación de fidelidad.** **[MEDIDO]**

Por eso la tercera vuelta mide **bytes por píxel** de lo que el motor escribió, deriva la profundidad, barre un espacio de parámetros cerrado (`-depth {auto,8,16} × -interlace {defecto,plane}`) y **elige por RMSE**, no por `rc=0`. Trampa 5 de CLAUDE.md: `SSIM` devuelve 0 en esta build; se usa RMSE.

### 4.2 La tabla

| Formato | B/píxel | bits/canal | Variante que gana | RMSE vs color | RMSE vs ideal | Veredicto |
|---|---:|---:|---|---:|---:|---|
| `rgb` | 6,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `rgba` | 8,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `rgbo` | 8,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `bgr` | 6,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `bgra` | 8,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `cmyk` | 8,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `cmyka` | 10,0 | 16 | `-depth 16` | **0,000000** | — | **ÍNTEGRO** |
| `ycbcr` | 6,0 | 16 | `-depth 16` | 0,000167 | — | **ÍNTEGRO** |
| `ycbcra` | 8,0 | 16 | `-depth 16` | 0,000167 | — | **ÍNTEGRO** |
| `pal` | 2,0 | 16 | `-depth 16` | 0,014153 | — | **ÍNTEGRO** |
| `uyvy` | 2,0 | 8 | `-depth 8` | 0,014153 | — | **ÍNTEGRO** |
| `gray` | 2,0 | 16 | `-depth 16` | 0,353895 | **0,000000** | **ÍNTEGRO** |
| `graya` | 4,0 | 16 | `-depth 16` | 0,353895 | **0,000000** | **ÍNTEGRO** |
| `mono` | 0,125 | 1 | `-depth 1` | 0,422631 | **0,000000** | **ÍNTEGRO** |
| `yuv` | 3,0 | 8 | `-depth 16` | 0,023312 | — | **DEGRADADO** |
| `bayer` | 2,0 | 16 | `-depth 16` | 0,071944 | — | **[PENDIENTE]** |
| `bayera` | 2,0 | 8 | `-depth 16` | 0,071944 | — | **[PENDIENTE]** |
| `ftxt` | 20,17 | — | `-depth 16` | 0,652292 | 0,652292 | **DESTRUIDO** |
| `map` | 1,05 | 8,4 | — | — | — | **FALLO** |
| `bgro` | 6,0 | **12** | — | — | — | **FALLO** (`0xC0000005`) |
| `rgb` (ffmpeg) | 7,5 | — | `-f rawvideo -pixel_format yuv420p` | — | — | ÍNTEGRO |
| `yuv` (ffmpeg) | 7,5 | — | ídem | — | — | ÍNTEGRO |

**La columna «RMSE vs ideal» es la que separa PÉRDIDA INEVITABLE de DESTRUIDO**, y hubo que añadirla: comparar `gray` contra una referencia **en color** mide la pérdida del formato, no la de la invocación. Contra su referencia ideal degradada (`-colorspace Gray`, `-monochrome`), `gray`, `graya` y `mono` dan **RMSE exactamente 0**. `ftxt` da **0,652 contra el original**, que debería ser sin pérdida: **no revive**. **[MEDIDO]**

### 4.3 Lo que queda abierto

- **`bayer`/`bayera` [PENDIENTE]**: no hay referencia ideal trivial para un mosaico CFA. Su RMSE de 0,072 contra la referencia en color es *compatible* con una demosaización correcta, pero no lo demuestra. Se cuentan como recuperadas; si no lo fueran, la cifra global bajaría en unas 366 aristas (0,2 puntos).
- **La otra mitad del sesgo**: todas las semillas las escribió el propio ImageMagick, así que la profundidad de 16 bits es *su* convenio. Un `.rgb` de una cámara o de otro programa vendría a 8 bits y **la misma bandera daría basura**. **Eso convierte la categoría 2 en algo más caro de lo que parece**: FileX no necesita «un dato», necesita **geometría, profundidad, número de canales y orden de entrelazado**, y necesita que sean los del fichero real. **[PENDIENTE]**

---

## 5. El residuo: las 118 aristas nominales de la muestra de E1

De las 118 (115 del estrato general + 3 del estrato PDF), **27 se recuperan: 22,9 %** [IC 95 % Wilson: **16,2 – 31,2**]. **[MEDIDO]** Veredicto de las 27: **ÍNTEGRO 24 · DEGRADADO 3**.

| Estrato | Nominales en E1 | Recuperadas | % |
|---|---:|---:|---:|
| `imagemagick` · misma familia | 10 | **8** | **80,0 %** |
| `pdf` | 3 | 2 | 66,7 % |
| `imagemagick` · distinta familia | 3 | 1 | 33,3 % |
| `ffmpeg` · distinta familia | 70 | **12** | **17,1 %** |
| `ffmpeg` · misma familia | 32 | 4 | 12,5 % |
| **Total** | **118** | **27** | **22,9 %** |

**El gradiente se invierte respecto al de E1, y eso es informativo.** E1 midió que el peor estrato era `ffmpeg` cruzando familias (76,9 % nominal) y el mejor `imagemagick` misma familia (4,2 %). Aquí el orden de *recuperabilidad* es el contrario: **donde ConvertX fallaba poco, fallaba por invocación (80 % recuperable); donde fallaba mucho, fallaba por capacidad (17 % recuperable).**

### 5.1 Por qué no se recuperan las 91 restantes

| Causa | Cuántas |
|---|---:|
| **El muxer no admite ninguna pista que la entrada tenga** | **69** |
| `received no packets` tras barrer el espacio de parámetros declarado | 11 |
| El codificador no está compilado en este build (`amr_nb`, `libx266`) | 2 |
| Otras (ImageMagick: `epsi→group4`, `ptif→mov`, `pdf→txt`) | 3 |
| *Timeout* (`mkv → wpg`) | 1 |

Las 69 son el corazón del asunto y merecen leerse una a una: `hevc → opus` (vídeo sin audio a contenedor de solo audio), `gif → caf`, `tta → gif`, `mjpeg → m2a`, `ec3 → 265`, `flac → fits`, `caf → a64`… **Son exactamente lo que E1 diagnosticó en §5.1: el producto cartesiano `473 × 202` de ffmpeg cruza modalidades y declara que se puede convertir un `.aptx` en un `.gif`.** Ninguna invocación arregla eso, porque no hay nada que convertir.

> **Este es el número que más peso tiene en la conclusión: 69 de 118 aristas nominales (58,5 %) son declaraciones sin sentido, no órdenes mal escritas.** **[MEDIDO]**

### 5.2 Las 27 que sí se recuperan, y con qué

| Regla | Aristas | Ejemplos |
|---|---:|---|
| **U** (`-frames:v 1 -update 1`) | **13** | `mjpeg→ppm`, `isma→exr`, `265→jp2`, `h263→pfm`, `f4v→tif`, `hevc→pbm`, `y4m→jpeg`, `266→bmp`, `asf→rs`, `h263→ras`, `mxf→sgi`, `wtv→tif`, `isma→ppm` |
| **L** (techo de 256 px) | **7** | `data→icn`, `miff→icn`, `pfm→icn`, `gif87→icon`, `cals→icon`, `pdf→cur`, `pdf→ico` |
| **A** (`-alpha set`) | 3 | `pdb→matte`, `ipl→matte`, `hdr→matte` |
| **X** (prefijo de formato) | 1 | `avif→inline` |
| **M+R+C+F** | 3 | `apm→swf`, `aptx→isma`, `msbc→ismv` |

**La regla U merece un renglón aparte porque es la más barata del informe.** El «`Error opening output files: Invalid argument`» que E1 encontró 69 veces tiene dos causas distintas que su instrumentación no separaba: en la mayoría es la incompatibilidad de modalidad (irrecuperable), pero en **13 casos** es que **el destino es una imagen única y la entrada tiene más de un fotograma**. ffmpeg escribe el primer fotograma, no encuentra el patrón `%d` y aborta con el fichero ya en disco. **Dos banderas lo arreglan.**

Y la regla **L** cierra el caso que E1 destacó: `png → ico` y sus parientes fallan por el techo de 256 px del formato ICO, y **ConvertX ya tiene el caso especial en `ffmpeg.ts:702` y no lo tiene en `imagemagick.ts`**. Aquí se confirma que el arreglo es una línea: `-resize 256x256> -define icon:auto-resize=256,128,64,48,32,16` produce un ICO multirresolución que `magick identify` reconoce como `ICO 256x256 … 16x16`. **[MEDIDO]**

---

## 6. `imagen → pdf` sin densidad: no está en el 50,5 %, y aun así es lo más rentable

E1 §6 encontró que **once de las doce degradaciones del estrato PDF son la misma regla** —`P7 · 1 px → 1 pt: página absurda`— y concluyó que *«no es un caso, es el comportamiento por defecto de todas las aristas `imagen → pdf`»*.

**Aviso de contabilidad, y es importante: esto NO entra en el 18,8 %.** Una degradación no es una arista nominal (E1 §2.1), así que estas aristas ya contaban como reales. Lo que se mide aquí es otra cosa: **cuánta calidad, no cuántas aristas.**

De las 12 degradaciones del estrato PDF, **7 son `→ pdf`** y **6 llevan la marca P7**. Comparando tres invocaciones sobre las mismas aristas **[MEDIDO]**:

| Invocación | Página resultante (desde 1920×1080) | Con P7 | Veredicto |
|---|---|---:|---|
| ConvertX (`magick ENT -auto-orient SAL.pdf`) | **677,3 × 381,0 mm** | **6 de 7** | DEGRADADO 6 · ÍNTEGRO 1 |
| **D** (`-units PixelsPerInch -density 150`) | 325,1 × 182,9 mm | **0 de 7** | **ÍNTEGRO 7** |
| **D ajustada a A4** (densidad calculada) | **210,0 × 118,1 mm** | **0 de 7** | **ÍNTEGRO 7** |

> **Seis de seis degradaciones P7 desaparecen con una sola bandera.** Es categoría 1, cuesta un `-density`, y es la corrección más rentable que sale de este trabajo: **afecta al comportamiento por defecto de toda la familia `imagen → pdf`, que es de las que un producto real sirve todos los días.** La variante que ajusta a A4 es la que hay que implementar: `-density 150` sigue dando un A3 y medio.

---

## 7. Cuatro veces que me equivoqué, y qué enseña cada una

Refutar una conclusión propia es el resultado más valioso que se puede traer (CLAUDE.md §3). Aquí hay cuatro, y **tres cambian una recomendación**.

### 7.1 La semilla la escribió el motor que no la iba a leer

E1 materializaba cada formato con el **primer** motor capaz de escribirlo. Para los crudos eso es fatal: **`ffmpeg -i s_cif.mp4 m.rgb` usa el muxer `rawvideo`, que ignora la extensión y vuelca el `pix_fmt` de la entrada (`yuv420p`)**. El fichero llamado `m.rgb` no contiene RGB. Mi primera vuelta se negó a construir la invocación porque no tenía geometría, y declaró muertos `rgb` y `yuv` de ImageMagick que en realidad **reviven perfectamente** cuando la semilla la escribe ImageMagick.

**Consecuencia de diseño:** la autoconsistencia de un sondeo de capacidades **exige que el escritor y el lector sean el mismo motor**. Si FileX sondea el mapa de capacidades al arrancar (E1 §9.1), tiene que emparejarlos.

### 7.2 Forzar el códec por defecto del muxer es PEOR que no forzar nada

La regla C decía «usa el códec por defecto del muxer, sondeado». Para el muxer `image2` **eso es una trampa**: su «códec de vídeo por defecto» declarado es `mjpeg`, así que `-f image2 -c:v mjpeg out.ppm` **escribe un JPEG dentro de un fichero llamado `.ppm`** — una salida **peor** que la que da ConvertX, que al no forzar nada deja que ffmpeg elija el códec por la extensión, y acierta.

**Consecuencia de diseño, y va contra la intuición del proyecto:** *«sondear capacidades en ejecución, no deducirlas»* es correcto, **pero un valor sondeado que el motor declara como «por defecto» no es una capacidad, es un valor por defecto** — y el motor puede tener una lógica mejor que ese valor. La regla queda: **fuerza lo que el motor no puede deducir (el muxer, el mapeo de pistas, las restricciones del codificador) y no fuerces lo que ya deduce bien (el códec de una imagen a partir de su extensión).**

### 7.3 El control antifalso positivo eliminó 4 de 32 «recuperaciones»

El vocabulario de firmas del verificador cubre 24 nombres y casi ningún destino de imagen exótico está dentro (E1 §2, sesgo 3). Sin un tercero, `rc=0` más un fichero no vacío **da por viva una arista que entrega otro formato**. Se reejecutaron **las 32 aristas revividas** y se preguntó a `magick identify` y a `ffprobe` qué eran de verdad:

| Resultado | Cuántas |
|---|---:|
| Coincide con el formato pedido | 21 |
| Comprobado por `ffprobe` / cabecera (`swf`, `isma`, `ismv`, `matte`, `inline`) | 7 |
| **DISCREPA — falso positivo** | **3** |
| No comprobable | 1 |

Los tres falsos positivos, más uno descartado por prudencia **[MEDIDO]**:

- **`ogg → im24`** y **`wtv → im1`**: ffmpeg escribió un **Sun Raster** dentro de ficheros `.im24` y `.im1`.
- **`tta → h265.mp4`**: el pseudoformato pide **vídeo H.265**; la entrada es solo audio y la salida es un MP4 **con solo AAC y sin una sola pista de vídeo**. Pasa la firma y falla el punto 4 del contrato (*pedido frente a obtenido*).
- **`266 → y`**: 50 688 B para 352×288 es exactamente la mitad de un plano de gris. No comprobable; **se descarta por prudencia**.

Y antes de eso, la **primera** vuelta produjo dos falsos positivos aún más claros: `vbn` y `xface` «revivieron» escribiendo **JPEG** a través de `image2`. La regla **C2** nació de ahí.

> **Sin este control la cifra habría salido 19,8 % en vez de 18,8 %** (31 de 118 en el residuo en vez de 27). El control cuesta una reejecución y una llamada a un tercero. **Cuando el vocabulario de firmas no cubre el destino, «arista viva» no es una medición: es una suposición.**

### 7.4 El quinto punto del contrato, comprobado y sin hallazgos aquí

Toda la campaña del residuo corrió con `cwd` en un directorio desechable y **listando el directorio antes y después de cada invocación**, que es la regla R18 que E1 propuso. Resultado: **0 de 118 aristas escribieron fuera del destino declarado**. **[MEDIDO]**

**No refuta a E1: confirma que su hallazgo era específico.** Los dos casos que él encontró (`ffmpeg … out.mpd` y `magick … out.html`) tienen destinos —`mpd`, `html`— que **no aparecen entre las 118 aristas nominales de su muestra**, porque esas dos aristas no fallaban: entregaban un fichero incompleto. **La fuga y el fallo son poblaciones disjuntas**, y eso es justo por lo que el quinto punto hace falta: los cuatro puntos no la ven y el juez de aristas nominales tampoco.

*(Nota de método: sí hubo un fichero parásito, y era mío. Una sustitución de plantilla mal hecha —`x == "__SAL__"` en vez de `x.replace(…)`— dejó que `magick` escribiera 39 ficheros llamados `__SAL__*` en mi directorio de salidas. Cayeron dentro del directorio de trabajo y no en la raíz del repositorio, que es exactamente para lo que sirve la regla.)*

---

## 8. C17 — el censo de Ghostscript y Gotenberg

Son el **0,10 %** de la población (136 aristas exclusivas de estos motores) y **toda la superficie documental del grafo**. E1 las dejó fuera de la muestra.

| Motor | Aristas | Evaluadas | **Nominales** | Tasa | IC 95 % |
|---|---:|---:|---:|---:|---|
| **ghostscript** | 9 | **9 (censo completo)** | **0** | **0,0 %** | [0 – 29,9] |
| **gotenberg-chromium** | 25 | **25 (censo completo)** | **0** | **0,0 %** | [0 – 13,3] |
| **gotenberg-lo** | 102 | 30 | **2** | 6,7 % | [1,8 – 21,3] |
| **Total** | **136** | **64** | **2** | **3,1 %** | **[0,9 – 10,7]** |

**[MEDIDO]**

> **La superficie documental del grafo es la más sólida que se ha medido en este proyecto: 3,1 % de aristas nominales, frente al 23,1 % del marco general y al 50,5 % global.** Coincide con el 3,0 % que E1 midió para el estrato PDF (§6 de su informe) por un camino completamente distinto, con otros motores y otro protocolo. **Dos medidas independientes que dan lo mismo.**

**Ghostscript, censo completo: 9 de 9 reales.** `{pdf, ps, eps} × {docx, pclm, xps}`, todas `rc=0` con salida no vacía y verdicto ÍNTEGRO. Las semillas `.ps` y `.eps` las genera el propio Ghostscript desde el PDF del corpus (`ps2write`, `eps2write`).

**Gotenberg/Chromium, censo completo: 25 de 25 reales.** `{html, htm, xhtml, md, url} × {pdf, png, jpeg, jpg, webp}` por su API HTTP real (`/forms/chromium/convert/*` y `/forms/chromium/screenshot/*`). Las cinco firmas de salida se verificaron en proceso: `pdf`, `png`, `jpeg`, `webp`, todas correctas. **La ruta de captura de pantalla, que es lo que hace que Gotenberg declare `png/jpeg/webp`, funciona.**

**Gotenberg/LibreOffice: 2 nominales de 30 evaluadas.** Las dos, con su error literal:

| Arista | HTTP | Error |
|---|---:|---|
| `epub → pdf` | **500** | `LibreOffice failed to convert the document 'entrada.epub'` |
| `dbf → pdf` | **500** | `LibreOffice failed to convert the document 's.dbf'` |

`epub → pdf` **reproduce por tercera vez, y por un tercer camino**, lo que E1 §8.1 ya había medido dos veces: falla con LibreOffice dentro del contenedor de ConvertX (`rc=1`), falla a través de Gotenberg (HTTP 500) y **funciona con Calibre** (26 817 B, centinela intacto). No es una arista nominal del grafo: **es una arista nominal de un motor.**

**Y el sesgo de este censo hay que decirlo entero: 72 de las 102 extensiones de LibreOffice no se pudieron materializar.** Son los formatos propietarios heredados que LibreOffice **lee** y **no escribe** (`123`, `wk1`, `wpd`, `pages`, `key`, `numbers`, `hwp`, `cdr`, `lwp`, `mcw`, `vsd`…). Las semillas se generaron con `soffice --convert-to` dentro de `filex-convertx` desde dos bases (texto `.odt` y hoja `.xlsx`) más el corpus, lo que dio 30. **Ese 3,1 % es, como todo lo demás de esta línea de trabajo, una cota inferior.** **[PENDIENTE]**

---

## 9. C13 — qpdf y Tesseract: el coste de integración, medido

`aristas-nominales.md` §8 cierra 5 de los 7 casos `no_evaluable` de `referencia.json` y deja dos abiertos porque **`qpdf` y `tesseract` son los dos únicos motores que no trae ninguna imagen levantada**. El encargo pide medir qué cuesta añadirlos **en contenedor**.

**Cuesta ocho líneas de Dockerfile, 28 segundos y 50 MB. [MEDIDO]**

```dockerfile
FROM ghcr.io/c4illin/convertx:latest
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      qpdf tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*
```

| Métrica | Valor |
|---|---|
| Tiempo de construcción | **28,1 s** (17,3 s de `apt-get`) |
| Tamaño de la imagen | 5,73 GB → **5,78 GB** (**+50 MB, +0,9 %**) |
| Versiones | **qpdf 12.4.0**, **Tesseract 5.5.0** + Leptonica 1.86.0 |
| Idiomas de OCR | `eng`, `osd`, **`spa`** — **y esto resuelve de paso la nota de CLAUDE.md §2**: no hace falta distribuir 2–4 MB por idioma a mano ni depender del `tessdata` que dejó PDFgear |

**Caso 6 — qpdf: 7 de 7 operaciones, todas `rc=0`. [MEDIDO]**

| Operación | Bytes | ms |
|---|---:|---:|
| `--linearize` | 3 814 | 563 |
| `--encrypt "" ownerpw 256` | 3 014 | 835 |
| `--password=… --decrypt` | 3 203 | 316 |
| `--check` | 195 | 404 |
| `--json` | 4 333 | 1 068 |
| `--split-pages` | 1 408 | 117 |
| `--empty --pages … --` (fusión) | 1 586 | 171 |

**Caso 5 — Tesseract sobre PDF escaneado.** Rasterizado con Ghostscript **a ppp nativos** (regla R1) y CER con la métrica **acentuada** (`ocr_eval_p2.py`, copia de `ocr_eval_tildes.py`; `ocr_eval.py` es arnés compartido y no se toca):

| Documento | ppp nativos | CER a 150 ppp | **CER a ppp nativos** |
|---|---:|---:|---:|
| `patologico_escaneado` | 200 | 0,00 % | **0,00 %** |
| `escaneado_d1` | 150 | 0,00 % | **0,00 %** |
| `escaneado_d2` | 100 | **0,00 %** | **32,10 %** |
| `escaneado_d3` | 100 | 100,00 % | **100,00 %** |
| `escaneado_d4` | 200 | 82,89 % | **51,15 %** |

**Tres cosas que sacar de esa tabla:**

1. **Tesseract 5.5.0 externo falla en `d3` devolviendo un fichero de 0 bytes.** El Tesseract **embebido en Ghostscript** falla en el mismo documento **alucinando** (165,8 % de CER, `verificador-ghostscript.md`). **Mismo motor nominal, dos modos de fallo opuestos** — la diferencia tiene que estar en el preprocesado que aplica cada envoltorio. Es material para la heurística de degradación severa (B7): **un motor que devuelve 0 bytes y otro que devuelve más texto que la referencia son la misma señal de fallo vista desde dos lados.** **[PENDIENTE]** de aislar la causa.
2. **`escaneado_d2` es un contraejemplo a la regla R1, con n=1.** A 150 ppp da **0,00 %** y a sus 100 ppp nativos da **32,10 %**. `clamp(nativos, 100, 200)` le asigna 100 y **empeora**. La regla se midió sobre motores neuronales; **Tesseract no es uno de ellos** y su detector de líneas parece necesitar más píxeles. **[PENDIENTE]**: barrer la curva para Tesseract antes de aplicarle R1.
3. **En `d4`, en cambio, R1 acierta de largo**: 82,89 % a 150 ppp frente a **51,15 %** a 200. Y **51,15 % deja a Tesseract el peor de los cinco motores** del corpus d4 (PaddleOCR 19,30 · RapidOCR+normalización 18,62 · Docling+RapidOCR 36,91 · RapidOCR ONNX 41,78 · EasyOCR 61,41). **Sigue teniendo una ventaja decisiva: VRAM 0 y va en el mismo contenedor que el resto.**

> **El coste de integración real de los 7 casos `no_evaluable` queda medido: dos motores, 50 MB, 28 segundos.** No es un argumento contra añadirlos: es un argumento a favor. **[MEDIDO]**

---

## 10. Consecuencias para el diseño de FileX

1. **La promesa de producto se puede escribir, y es más modesta de lo que parecía.** *«FileX entrega 3 226 aristas que ConvertX declara y no cumple, con los mismos motores y sin pedir nada al usuario»* — un **10,2 %** de las aristas nominales. Añadiendo un canal de metadatos, **5 930** (18,8 %). Lo que **no** se puede prometer es el otro 81,2 %.
2. **La arista mínima viable gana su sexta dimensión, y la sexta es la que más manda.** E1 la dejó en `(origen, destino, motor, parametrización, build)`. Este trabajo confirma que **`build` decide 19 de las 33 semiaristas de salida muertas de ffmpeg** —el codificador simplemente no está compilado— y que **`parametrización` decide otras 8**. Un catálogo que no lleve las dos miente en cuanto cambias de máquina.
3. **La categoría 2 obliga a decidir algo que hoy no está decidido: qué hace FileX con los 17 formatos crudos.** Son aristas reales que **exigen cuatro datos que no están en el fichero** (geometría, profundidad, canales, entrelazado). Las tres salidas posibles son: (a) pedirlos al usuario, (b) guardarlos en un *sidecar* cuando el propio FileX escribió el fichero, o (c) **borrarlos del catálogo declarado**. Declararlos y no poder cumplirlos es el **fallo silencioso** que `saturacion-herramientas.md` §8 midió al 15–17 %.
4. **`imagen → pdf` necesita densidad ajustada a página, no una densidad fija.** `-density 150` quita la marca P7 pero sigue produciendo un A3 y medio. La regla correcta es **calcular la densidad para que la imagen quepa en la página objetivo**: 6 de 6 degradaciones desaparecen y la página sale exactamente A4.
5. **`-frames:v 1 -update 1` es la bandera con mejor relación coste/beneficio del informe.** Recupera **13 de las 27** aristas del residuo, y su ausencia es la causa de una parte del `Invalid argument` que E1 encontró 69 veces.
6. **La regla «fuerza lo que sondees» necesita una excepción.** Con `image2`, forzar el códec por defecto es peor que no forzarlo (§7.2). La formulación que sobrevive es: **fuerza el muxer, el mapeo de pistas y las restricciones del codificador; no fuerces el códec cuando el muxer lo deduce de la extensión.**
7. **Todo sondeo de capacidades tiene que emparejar escritor y lector del mismo motor** (§7.1), o el mapa que salga estará medido contra ficheros que no son lo que dicen ser.
8. **Cuando el vocabulario de firmas no cubre el destino, hace falta un tercero.** El control de §7.3 eliminó 4 de 32 recuperaciones. En producción ese tercero es la ampliación del vocabulario que pide C14; mientras no exista, **una arista fuera del vocabulario no se puede declarar viva, solo «sin refutar»**.
9. **La superficie documental es donde el grafo se sostiene.** 3,1 % nominal en gs+Gotenberg (§8) y 3,0 % en el estrato PDF de E1, medidos por caminos independientes. **Si FileX tiene que elegir dónde prometer, es aquí.**
10. **qpdf y Tesseract entran por 50 MB y 28 s.** No hay argumento de coste para dejarlos fuera.

---

## 11. Lo que este informe NO ha medido — **[PENDIENTE]**

1. **El 54,78 % indeterminado sigue indeterminado.** Peor: al revivir semiaristas de entrada, **2 868 aristas pasan de «muerta» a «sin veredicto»** (su otra mitad nunca se pudo materializar). Están contadas como nominales en la cifra conservadora, y **podrían ser recuperaciones adicionales**. Cerrarlo sigue exigiendo el corpus de C16.
2. **La profundidad de los crudos de terceros.** Todo lo medido son ficheros que escribió el propio ImageMagick a 16 bits. Un `.rgb` de 8 bits de otra procedencia **daría basura con la misma bandera**, y no se sabe cuánta gente lo tiene a 8 bits.
3. **`bayer` y `bayera`** no tienen referencia ideal: su recuperación está **supuesta**, no demostrada (≈366 aristas, 0,2 puntos).
4. **Las 4 semiaristas de salida que resistieron el barrido** (`amv`, `gxf`, `mlp`, `thd`) y las 11 aristas del residuo con `received no packets`. Dos intentos gastados en cada una.
5. **72 de las 102 extensiones de Gotenberg/LibreOffice** siguen sin semilla. El 3,1 % de C17 es cota inferior.
6. **La curva de ppp de Tesseract.** `escaneado_d2` refuta R1 para este motor con n=1. No se ha barrido.
7. **La causa de la asimetría entre el Tesseract externo (silencio) y el embebido en Ghostscript (alucinación)** sobre `escaneado_d3`.
8. **Si estas aristas se piden.** Sigue abierto lo de siempre: recuperar `mxf → sgi` no vale lo mismo que recuperar `png → ico`. De las 27 aristas del residuo recuperadas, **las de la familia `ico` son las únicas que un producto real sirve todos los días**.
9. **El coste en tiempo de P2-INV frente a la invocación de ConvertX.** No se ha medido: sondear el muxer y el codificador añade dos lanzamientos de proceso por arista, cacheables, pero no cuantificados aquí.

---

## 12. Qué queda en disco

`bench/salidas-invocacion/` — **1,09 MB** en 112 ficheros tras podar. Se borraron **380 MB** regenerables: `pool/` (225 MB de semillas), `pool2/`, `pool3/`, `sem_c17/`, los once `tmp_*/`, `aristas.json` (5,8 MB), `marco.json` (0,9 MB) y los binarios de `c13/`. `MANIFIESTO.md` lleva nombre, `sha256`, tamaño y **la orden exacta** de cada fichero, más el orden de ejecución completo.

| Fichero | Qué es |
|---|---|
| `inventario_e1.json` | Los fallos de E1 extraídos y clasificados: 34 + 37 semiaristas, 118 aristas nominales |
| `semi_in_p2.json`, `semi_in_p2b.json` | Las dos vueltas sobre las semiaristas de entrada |
| `crudos_p2.json`, `crudos_ideal.json` | Los 20 crudos con su barrido de profundidad y su RMSE contra la referencia ideal |
| `semi_out_p2.json`, `semi_out_p2b.json` | Las dos vueltas sobre las semiaristas de salida, con el sondeo de codificadores |
| `resid_p2.json`, `resid_p2b.json` | Las 118 aristas nominales, cada una con su línea base ConvertX y su P2-INV |
| `validacion_p2.json`, `validacion_p2_extra.json` | El control antifalso positivo con `magick identify` y `ffprobe` |
| `densidad_p2.json` | Las tres invocaciones de `imagen → pdf` con su tamaño de página en mm |
| `c17.json`, `c17b.json` | El censo de Ghostscript y Gotenberg |
| `c13/res.tsv`, `c13/res_ocr.tsv`, `c13_cer.json` | qpdf y Tesseract dentro de `filex-c13`, con su CER |
| `final_p2.json`, `resumen_p2.json` | La contabilidad y la cifra con su intervalo |
| `testigo.jsonl` | Los dos testigos de ruido |
| `verificador_p2.py` | Copia congelada del verificador (P3 edita el original en paralelo) |
| `Dockerfile.c13` | Los dos motores que faltaban, en ocho líneas |
| `_p2_*.py`, `c13_*.sh` | Los instrumentos, reproducibles |

**La imagen `filex-c13` queda construida** (5,78 GB, comparte capas con la base). Se reconstruye en 28 s con el Dockerfile.
