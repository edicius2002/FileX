# Los píxeles que faltaban y el OCR que no necesita tarjeta

**Encargo V1.** Cerrar dos de los siete PENDIENTE de `bench/verificador-fidelidad.md` §7
—la cobertura de `min(alfa)` en TIFF comprimido, GIF y PNG entrelazado, más las reglas de
fidelidad **V2** y **V5**— y **ejercitar por primera vez el Tesseract que Ghostscript 10.07
lleva compilado dentro**.

**Fecha:** 21 de agosto de 2026, 07:20–09:40.
**Máquina:** Windows 10, 12 núcleos, Python 3.11.9, Ghostscript 10.07, ImageMagick
7.1.2-21 Q16-HDRI, ffmpeg/ffprobe N-121159. **Sin GPU y sin pedir su lock** (lo tenía G1).
**Sin dependencias nuevas:** `bench/scripts/verificador.py` sigue siendo biblioteca estándar
de Python y nada más.
**Salidas:** `bench/salidas-verificador-gs/` (11 scripts, 20 `.json`, 15 `.txt` de OCR y
`MANIFIESTO.md`; 316 KB, todo texto — las 48 binarias, 21,6 MB, están borradas con su
`sha256` y su orden de reproducción).

> Cada afirmación va marcada **MEDIDO** o **PENDIENTE**.
> **Otros tres agentes corrían en paralelo**; uno de ellos (E1) midiendo también en CPU. El
> §4 explica por qué eso obligó a **cambiar el testigo de ruido**, y qué pasó antes de
> hacerlo.

---

## 0. Las nueve líneas que importan

1. **Los tres formatos están cubiertos y coinciden con `magick` en 36 de 36 ficheros
   comparables.** **MEDIDO.** TIFF (sin comprimir / LZW / Deflate / PackBits, con predictor,
   *chunky* y *planar*, 8 y 16 bits), GIF (descomprimiendo el LZW) y PNG entrelazado Adam7.
   AVIF/HEIF sigue diciendo «no evaluable», que es la respuesta correcta. *(§1)*
2. **Sin el atajo de «fila opaca», ampliar la cobertura habría hecho el verificador *más
   lento que `magick`* en tres casos.** **MEDIDO.** El TIFF de 1920×1080 RGBA16 opaco costaba
   **479 ms** frente a 336 ms de `magick`, y el PNG Adam7 equivalente **1 208 ms** frente a
   413 ms. Trasladando el truco del PNG no entrelazado a los otros dos formatos: **80,7 ms**
   y **66,3 ms**, ×4,1 y ×6,8 a favor. **Ese atajo no es una optimización: es la condición
   para que la cobertura merezca la pena.** *(§1.3)*
3. **El GIF ya no dice «no evaluable»: dice 1,0, y tiene razón.** **MEDIDO.** «Declara un
   índice transparente» no es «lo usa». El GIF de paleta del patrón oro lo declara y su
   fotograma 1 no lo usa. Comprobado de forma independiente: `magick "…gif[0]"` también da 1.
   Sobre el fichero entero, en cambio, **`magick` devuelve `1e59`, un número inutilizable**;
   el lector en proceso da la respuesta buena en **12,3 ms** frente a **1 901 ms**. *(§1.4)*
4. **Se encontró un fallo preexistente, y no era cosmético.** **MEDIDO.** En PNG de paleta de
   1/2/4 bits, la coordenada del primer píxel transparente devolvía el índice del **byte**, no
   el del **píxel**: con 2 bits por píxel, `(12,8)` se publicaba como `(3,8)`. Esa coordenada
   es la que la regla I3 usa para leer un píxel de la salida con `magick`: **leía otro
   píxel**. No lo vio nadie porque `alpha.png`, la única entrada con alfa del corpus, es de
   8 bits. *(§1.5)*
5. **V2 es, con diferencia, la regla más cara de todo el grupo C: sube la suite de fidelidad
   un 60,6 %.** **MEDIDO.** `ffprobe -count_frames` **decodifica el vídeo entero**: 3 482 ms
   sobre un MP4 de 16 MB, **×10 240 el contrato**. Sobre las 53 salidas, la fidelidad pasa de
   **28 858 ms a 46 332 ms**, y **16 592 de esos ms son solo V2**. *(§2)*
6. **Las dos reglas nuevas discriminan: 5 de 5 en los fallos fabricados**, incluida la
   excepción de «se pidió cambiar el fps». **MEDIDO.** Sobre el patrón oro no fallan nunca, y
   eso **no** demostraba que sirvieran. *(§2.3)*
7. **Los falsos positivos siguen en 0, y los 5 fallos documentados siguen atrapados 12 de
   12.** **MEDIDO.** Seis configuraciones de contrato × 53 salidas: 0 FP, 0 FN, los mismos 3
   avisos en proceso y 4 con subprocesos. *(§3)*
8. **El OCR de Ghostscript funciona, es gratis de instalar y resuelve la arista de
   reparación en 3 de los 4 escaneados con 0,0 % de CER.** **MEDIDO.** `pdf escaneado → docx`
   pasa de **2 caracteres de basura** (un salto, `docxwrite` directo) a **texto íntegro** (dos
   saltos, `pdfocr8` y luego `docxwrite`), en **438–1 255 ms**. En `escaneado_d3` **fracasa**,
   y fracasa **alucinando**: 119 % de CER. *(§5.6)*
9. **La laguna del castellano queda medida, y el evaluador ciego oculta 6,3 puntos.**
   **MEDIDO.** Sobre un PDF acentuado fabricado para esto, `-sOCRLanguage=spa` da **1,9 %** de
   CER con tildes; `eng` da **9,2 % leído con `ocr_eval.py` y 15,5 % de verdad**. El evaluador
   compartido **subestima el error en un 41 % relativo** justo donde más importa. *(§5.5)*

**Y un hallazgo que no estaba en el encargo:** el verificador **declara `OK`** la reparación
por OCR de `escaneado_d3`, que es ruido puro, porque la regla P5 dice «si la entrada no tenía
texto, no se exige texto en la salida» y el umbral de P6 (≥10 caracteres) lo superan **75
caracteres de ruido**. Hay una señal barata que los separa y está medida. *(§5.8)*

---

## 1. `min(alfa)`: los tres formatos que faltaban

### 1.1 Qué cubre ahora — **MEDIDO**

| Formato | Antes | Ahora | Vía |
|---|---|---|---|
| TIFF sin `ExtraSamples` | cabecera | cabecera | `SamplesPerPixel` |
| **TIFF sin comprimir, con alfa** | **no evaluable** | **exacto** | banda cruda, carril alfa |
| **TIFF LZW** | **no evaluable** | **exacto** | LZW de TIFF (MSB, *early change*) |
| **TIFF Deflate (8 y 32946)** | **no evaluable** | **exacto** | `zlib` |
| **TIFF PackBits (32773)** | **no evaluable** | **exacto** | RLE |
| **TIFF con `Predictor=2`** | **no evaluable** | **exacto** | el carril se des-predice solo |
| **TIFF `PlanarConfig=2`** | **no evaluable** | **exacto** | el plano alfa va en sus propias bandas |
| **TIFF 16 bits** | **no evaluable** | **exacto** | pareja alto/bajo según el orden de bytes |
| TIFF en teselas | — | **no evaluable** | `TileWidth`/`TileLength`: no implementado |
| TIFF con compresión JPEG (6/7) | — | **no evaluable** | exigiría un decodificador JPEG |
| TIFF `SampleFormat=3` (flotante) | — | **no evaluable** | no implementado |
| **GIF, transparencia declarada** | **no evaluable (con cota)** | **exacto** | LZW de GIF (LSB, sin *early change*) del **fotograma 1** |
| GIF sin GCE de transparencia | cabecera | cabecera | barrido **real** de bloques |
| **PNG entrelazado (Adam7)** | **no evaluable** | **exacto** | 7 pasadas, carril alfa, atajo por pasada |
| PNG con `tRNS` de color clave (ct 0/2) | no evaluable | no evaluable | no hay canal alfa que leer |
| AVIF / HEIF | no evaluable | **no evaluable** | **a propósito**: el plano alfa es un flujo AV1/HEVC |
| WebP animado | no evaluable | no evaluable | no implementado |

**AVIF/HEIF sigue igual por instrucción explícita del encargo y por la razón del informe
anterior: exigiría un decodificador AV1 en proceso.** Que siga diciendo «no evaluable» es el
resultado correcto, no una tarea sin hacer.

### 1.2 Verdad de referencia: 36 de 36 — **MEDIDO**

`prueba_alfa.py` compara `min(alfa)` en proceso contra `magick -format "%[fx:minima.a]"`
sobre **38 ficheros, 36 de ellos comparables** (los otros dos son los AVIF, que se declaran no
evaluables a propósito): **26 fixtures nuevos** —13 TIFF, 3 GIF y 10 PNG entrelazados— más los
casos que el informe anterior ya cubría.

**Discrepancias: 0 de 36.** Datos: `alfa_cobertura.json`.

Los fixtures no salen del corpus: se generan con `gen_fixtures.py` (ImageMagick),
`gen_predictor.py` y `gen_adam7_4b.py`. Dos de ellos hubo que escribirlos a mano y la razón
es en sí un dato:

- **`magick` ignora `-define tiff:predictor=2`**: el fichero sale byte a byte del mismo
  tamaño que sin él. **MEDIDO.** Resultó ser irrelevante porque **ImageMagick ya escribe
  `Predictor=2` por defecto** en TIFF RGBA con LZW y con Deflate —lo dice la IFD de los seis
  fixtures—, así que el camino del predictor **sí** está ejercitado con salidas reales de un
  motor real. El fixture a mano añade el control con `Predictor=1`.
- **`magick` no sabe escribir un PNG de paleta de menos de 8 bits que conserve el `tRNS`**:
  `-colors 12` aplana el alfa. Como ese camino lleva la aritmética delicada (los bits de
  relleno de la última celda), se fabricó con `zlib` + `struct`: 13×9 píxeles, 2 bits, con el
  único píxel transparente en **la esquina inferior derecha**, que es justo el que cae en el
  relleno si la aritmética está mal. **Es el fixture que destapó el fallo del §1.5.**

### 1.3 El coste, y por qué el atajo de fila opaca no es opcional — **MEDIDO**

Mediana de n=9. `sin atajo` es la primera implementación, completa y correcta; `con atajo` es
la definitiva. Datos: `cobertura_alfa_sin_atajo.json` y `cobertura_alfa.json`.

| Caso | sin atajo | **con atajo** | `magick` | **factor** |
|---|---:|---:|---:|---:|
| TIFF 1920×1080 RGBA16 **LZW** opaco (peor caso) | 479,2 ms | **80,7 ms** | 329,4 ms | **×4,1** |
| TIFF 1920×1080 RGBA16 **Deflate** opaco | 426,1 ms | **53,5 ms** | 388,0 ms | **×7,2** |
| **PNG Adam7** 1920×1080 RGBA16 opaco (peor caso) | 1 207,6 ms | **66,3 ms** | 452,3 ms | **×6,8** |
| PNG Adam7 1920×1080 RGBA8 opaco | 581,1 ms | **37,1 ms** | 365,8 ms | **×9,9** |
| TIFF 200×200 RGBA8 LZW+pred2 con alfa real | 2,85 ms | 2,75 ms | 45,3 ms | ×16,5 |
| TIFF 200×200 RGBA8 Deflate+pred2 con alfa real | 0,64 ms | 0,64 ms | 48,4 ms | ×75,5 |
| TIFF 200×200 RGBA8 PackBits con alfa real | 0,93 ms | 1,34 ms | 49,7 ms | ×37,1 |
| TIFF 200×200 RGBA8 LZW **planar** con alfa real | 1,76 ms | 1,68 ms | 45,2 ms | ×26,9 |
| TIFF 200×200 RGBA16 LZW con alfa real | 5,58 ms | 4,98 ms | 44,9 ms | ×9,0 |
| **GIF 200×200 con transparencia USADA** | 0,20 ms | **0,19 ms** | 51,5 ms | **×265,5** |
| **GIF animado que DECLARA y no usa** (patrón oro) | 8,59 ms | **12,28 ms** | 1 900,9 ms | **×154,8** |
| GIF animado sin declararla (patrón oro) | 0,61 ms | 0,85 ms | 1 866,5 ms | ×2 188 |
| GIF 1920×1080 opaco (cabecera) | 0,19 ms | 0,32 ms | 267,1 ms | ×842,5 |
| PNG Adam7 200×200 paleta+tRNS con alfa real | 0,30 ms | 0,24 ms | 58,0 ms | ×241,9 |
| PNG Adam7 200×200 RGBA8 con alfa real | 0,44 ms | 0,52 ms | 50,5 ms | ×96,5 |
| PNG Adam7 200×200 RGBA16 con alfa real | 0,78 ms | 0,93 ms | 52,8 ms | ×57,0 |
| PNG Adam7 13×9 paleta 2 bits, transp. en la esquina | 0,37 ms | 0,57 ms | 49,2 ms | ×85,7 |
| *control:* PNG 1920×1080 RGBA16 opaco (informe anterior) | 59,0 ms | 67,6 ms | 469,7 ms | ×6,9 |
| *control:* PNG 200×200 paleta+tRNS (mejor caso) | 0,20 ms | 0,29 ms | 55,4 ms | ×189,8 |
| *control:* TIFF 4000×3000 RGB16 sin alfa | 0,11 ms | 0,11 ms | 1 163,3 ms | ×10 771 |
| *control:* AVIF con alfa (**no evaluable a propósito**) | 0,05 ms | 0,06 ms | 63,5 ms | — |

**La lectura, y es el resultado de diseño de esta parte:**

El informe anterior explicaba (§1.1b) que «esta fila es 100 % opaca» se decide en PNG **sin
reconstruir nada**, comparando el carril alfa **filtrado** contra un patrón fijo. Ese truco
parecía específico del filtrado de PNG. **No lo es.** El mismo argumento vale para el
predictor de TIFF, que es literalmente el filtro `Sub` de PNG con otro nombre:

| Formato | Forma exacta del carril alfa de una fila 100 % opaca |
|---|---|
| TIFF, `Predictor=1` | `FF FF FF …` (todas las muestras al máximo) |
| TIFF, `Predictor=2` | `FF 00 00 …` (la primera al máximo, el resto deltas 0) |
| PNG Adam7 | el mismo `_PATRON_OPACO` del PNG plano, **aplicado por pasada** |

Son **dos comparaciones de bytes en C** en vez de un bucle de Python por píxel, y son
**exactas, no heurísticas**. El efecto está arriba: **×5,9 en el TIFF LZW, ×8,0 en el TIFF
Deflate y ×18,2 en el PNG Adam7**. Con el atajo, el PNG entrelazado de 1920×1080 cuesta
**66,3 ms**, prácticamente lo mismo que el no entrelazado (67,6 ms en esta sesión): **el
entrelazado sale gratis**.

**Sin el atajo, la conclusión del informe anterior —«en proceso siempre gana»— habría dejado
de ser cierta en tres casos.** Merece la pena decirlo así de claro: ampliar la cobertura de un
verificador puede *empeorarlo*, y la única forma de saberlo es medir el peor caso, no el caso
que uno tenía a mano.

### 1.4 El GIF: «declara» no es «tiene», y `magick` no sabe responder — **MEDIDO**

El informe anterior devolvía `evaluable: false` con la cota `0.0` y el motivo *«transparencia
DECLARADA en el bloque de control gráfico; confirmar que el índice se usa exigiría
descomprimir el LZW»*. Se ha descomprimido. Tres cosas salieron:

**(a) El barrido de bloques anterior era una heurística.** Buscaba `b"\x21\xf9\x04"` con
`find()` en los primeros 64 KB. Esa secuencia **aparece por casualidad dentro de los datos
LZW**. Ahora se recorre la estructura de verdad (cabecera, tabla global, extensiones con sus
sub-bloques, descriptores de imagen con su tabla local). **Es la corrección que hace que el
resto sea fiable.**

**(b) La respuesta correcta para `trivial_mp4-to-palette.gif` es 1,0.** Su GCE declara el
índice 255 como transparente y **el fotograma 1 no lo usa**. Confirmado de forma independiente
con `magick "…palette.gif[0]" -format "%[fx:minima.a]"` → **1**. En un GIF animado los
fotogramas 2..n usan el índice transparente como **codificación diferencial** («no repintes
este píxel»), no como transparencia visible; por eso se evalúa el fotograma 1, que es la
imagen que se ve, y se devuelve además una `nota` diciéndolo.

**(c) `magick` sobre el fichero entero devuelve un número que no se puede usar.** Da
`1e59` para el GIF de paleta y la concatenación `2.7431e+303` + `1e59` para el ingenuo:
agrega los fotogramas. El lector en proceso da **1,0** en **12,3 ms** frente a **1 901 ms**.
Es un caso más de la lista del informe anterior (`2.7431e+303` para «sin alfa», `SSIM` = 0
para imágenes idénticas): **la sonda externa no es la verdad, es otra medida con sus propios
defectos.**

**Límite declarado:** si el fotograma 1 es opaco pero un fotograma posterior *sí* deja píxeles
sin pintar al componer, el lector diría 1,0. Decidirlo exigiría componer la animación entera.
**PENDIENTE**, y sin caso que lo exija en el corpus.

### 1.5 El fallo preexistente que destapó el fixture — **MEDIDO**

En el camino de PNG de paleta de 1/2/4 bits, el mínimo de alfa era correcto pero la
**coordenada del primer píxel transparente estaba mal**: se devolvía `car.index(v)`, que es el
índice del **byte**, y en un PNG de 2 bits un byte lleva **cuatro** píxeles.

| Fixture | Píxel transparente real | Antes | Ahora |
|---|---|---|---|
| `plano_4b_esquina.png` (13×9, 2 bits, **no** entrelazado) | (12, 8) | **(3, 8)** | (12, 8) |
| `adam7_4b_esquina.png` (13×9, 2 bits, Adam7) | (12, 8) | **(4, 8)** | (12, 8) |
| *control:* `corpus/imagen/alpha.png` (8 bits) | (0, 0) | (0, 0) | (0, 0) |

**Por qué importa:** esa coordenada es exactamente lo que la regla **I3** pasa a
`magick … -format "%[pixel:p{x,y}]"` para comprobar sobre qué color se aplanó la salida.
Con la coordenada mal, **I3 leía otro píxel** y su veredicto era una casualidad. No lo detectó
nadie porque la única entrada con alfa del corpus (`alpha.png`) es de 8 bits, donde
byte e índice coinciden. Corregido en los dos caminos, con la explicación en el código
(`_pixel_en_byte`).

> Esto es la misma lección del §2.3 del informe anterior por otra puerta: **las excepciones y
> los fallos salen de ejecutar contra datos, no de leer la especificación.** Aquí bastó
> fabricar un fichero con el píxel malo en el sitio malo.

---

## 2. Las reglas V2 y V5

### 2.1 Qué comprueban

| Regla | `referencia.json` dice | Implementación | Severidad |
|---|---|---|---|
| **V2** | «el número de fotogramas de vídeo se conserva exactamente si no se cambia el fps»; *«usar `-count_frames`: en MKV/WebM `nb_frames` viene vacío y ffprobe no lo estima»* | `ffprobe -count_frames -select_streams v:0` sobre entrada y salida | **fallo** |
| **V5** | «las etiquetas de idioma y título de cada pista se conservan cuando el contenedor las admite» | `ffprobe -show_entries stream_tags=language,title` en las dos, comparadas **pista a pista** | **aviso** |

Tres decisiones, con su motivo:

1. **V2 no corre si se pidió cambiar el fps.** Si se pidió, el número **debe** cambiar y
   exigir igualdad sería un falso positivo. Es el mismo principio del punto 4 del contrato:
   *pedido frente a obtenido*. Comprobado con un caso fabricado (§2.3).
2. **V5 corre aunque se haya pedido reescalar o recortar.** Reescalar no es excusa para
   perder el idioma de una pista. Va, por tanto, **antes** de los cortes por `escala`/`fps`.
3. **`und` no cuenta como pérdida.** Es el valor por defecto de MP4 y Matroska: que la salida
   ponga `und` donde la entrada no decía nada no es una pérdida. Al revés sí.

### 2.2 Coste — **MEDIDO** (mediana n≥9, tanda con nivel de ruido verificado, §4)

| Regla | Caso | Mediana | Frente al contrato (0,34 ms) | Etiqueta |
|---|---|---:|---:|---|
| **V2** | `-count_frames` de `trivial.mp4` (540 KB) | **143,3 ms** | ×421 | SUCIA (deriva +21 %) |
| **V2** | `-count_frames` de `trivial_mp4-to.webm` (VP9) | **172,1 ms** | ×506 | limpia |
| **V2** | `-count_frames` de `patologico_2pistas.mkv` (4 MB) | **719,5 ms** | ×2 116 | limpia |
| **V2** | `-count_frames` de `tipico.mp4` (16 MB) | **3 481,8 ms** | **×10 240** | SUCIA (nivel ×1,2) |
| **V5** | etiquetas de `patologico_2pistas.mkv` | **36,6 ms** | ×108 | limpia |
| **V5** | etiquetas de `tipico.mp4` | **44,9 ms** | ×132 | limpia |
| **V5** | etiquetas de `tipico.flac` | **32,8 ms** | ×96 | SUCIA (deriva +28 %) |
| *control* | **V6** `framemd5` de `trivial.mp4` | 147,4 ms | ×434 | limpia |
| *control* | **CONTRATO** completo en proceso | **0,34 ms** | ×1 | limpia |

Los dos controles reproducen el informe anterior (V6: 147,4 frente a 129,2 ms; contrato: 0,34
frente a 0,37 ms), así que la tanda es comparable.

**V2 es la regla más cara del proyecto, y por una razón estructural: `-count_frames`
decodifica el vídeo entero.** No hay atajo: es exactamente lo que la nota de la propia regla
exige, porque `nb_frames` no se puede creer. Sobre las 53 salidas del patrón oro:

| Suite de fidelidad | Total | V2 | V5 | Resto |
|---|---:|---:|---:|---:|
| Informe anterior (10 reglas) | 28 858 ms | — | — | 28 858 ms |
| **Con V2 y V5 (12 reglas)** | **46 332 ms** | **16 592 ms** | **1 289 ms** | 28 451 ms |
| Incremento | **+60,6 %** | **36 % del total** | 2,8 % | — |

**Consecuencia para el diseño, y es la que hay que llevarse:** el grupo C ya estaba fuera del
camino caliente por costar el 38,5 % de convertir; con V2 pasa a costar **el 61,9 %**. **V2
merece su propio interruptor dentro del grupo C**: en una suite de regresión nocturna sí; en
un «verifica la fidelidad de esta conversión» pedido por un usuario sobre un vídeo de dos
horas, no. La alternativa barata —comparar `nb_frames` declarado— es precisamente la que la
regla prohíbe.

### 2.3 ¿Discriminan? Cinco de cinco — **MEDIDO**

Sobre las 53 salidas del patrón oro, V2 y V5 **nunca fallan**. Eso no demuestra que sirvan:
puede que no sepan fallar. `discrimina_v2_v5.py` fabrica los cuatro fallos y sus controles.
Datos: `discriminacion_v2_v5.json`.

| Caso fabricado | Esperado | Obtenido |
|---|---|---|
| V5 control: remux con `-map 0 -c copy` que conserva las etiquetas | sin aviso | **informativo: «las 2 etiquetas de pista se conservan»** ✔ |
| V5 fallo: el mismo remux con `-map_metadata -1` | aviso | **AVISO: «pista 1 language: 'spa' → None; pista 1 title: 'Castellano' → None…»** ✔ |
| V2 control: remux con todos los fotogramas | sin fallo | **informativo: «300 fotogramas conservados (contados)»** ✔ |
| V2 fallo: la salida entrega **150 de 300** fotogramas | fallo | **FALLO: «el número de fotogramas de vídeo NO se conserva» (300 → 150)** ✔ |
| V2 excepción: se **pidió** `fps=15` | sin fallo | **V2 no se evalúa; veredicto `ok`** ✔ |

Nota necesaria: para probar V5 hubo que **añadir** etiquetas a `patologico_2pistas.mkv`, porque
no las trae. Eso lo dice la nota de la propia regla en `referencia.json` (*«patologico_2pistas.mkv
NO trae etiquetas de idioma; no discrimina»*) y queda **confirmado**: en las 53 salidas, V5
dice «la entrada no trae etiquetas… la regla no discrimina» en **12 de las 22 veces** que se
evalúa. **El corpus no tiene con qué ejercitar V5.**

### 2.4 Efecto sobre la cobertura — **MEDIDO**

Los `ok_parcial` de la fidelidad bajan de **14 a 8**. Los seis que cambian son salidas de
audio a las que antes **no aplicaba ninguna regla** y a las que ahora aplica V5.

**Y aquí hay una decisión de diseño que conviene poner encima de la mesa, no esconder:** en
esos seis casos V5 pasa porque la entrada no tenía etiquetas que perder. Es una **verdad
vacua**. Se ha marcado `cobertura: true` —la regla *se evaluó*, se leyeron las dos partes y no
había nada que exigir, que no es lo mismo que «no pude comprobarlo»— pero **una lectura más
estricta las dejaría en `ok_parcial`**. Los ocho que siguen parciales son los correctos: tres
`.csv`/`.json` y cinco PDF→imagen, a los que sigue sin aplicar ninguna regla de fidelidad.

---

## 3. Regresión: nada se ha roto — **MEDIDO**

### 3.1 Falsos positivos sobre las 53: siguen en **0**

Datos: `contrato53.json`. Mismo protocolo que el informe anterior: dos motores × tres modos de
`min(alfa)`.

| Motor | Modo de `min(alfa)` | Salidas | **Falsos positivos** | Falsos negativos | `ok_parcial` | Avisos | Coste de `min(alfa)` |
|---|---|---:|---:|---:|---:|---:|---:|
| proceso | inyectado desde `referencia.json` | 53 | **0** | 0 | 0 | 3 | 0,0 ms |
| proceso | **calculado en proceso** | 53 | **0** | 0 | 0 | 3 | 322,5 ms |
| proceso | no disponible | 53 | **0** | 0 | 11 | 3 | 0,0 ms |
| subproceso | inyectado | 53 | **0** | 0 | 0 | 4 | 0,0 ms |
| subproceso | **calculado en proceso** | 53 | **0** | 0 | 0 | 4 | 308,4 ms |
| subproceso | no disponible | 53 | **0** | 0 | 11 | 4 | 0,0 ms |

**Idéntico al informe anterior en las seis configuraciones**, incluidos los 3 y 4 avisos y las
11 salidas que caen a `ok_parcial` sin `min(alfa)`. La ampliación de cobertura **no ha tocado
ningún veredicto del contrato**, que es exactamente lo que debía pasar: los formatos nuevos no
aparecen como entrada con alfa en el patrón oro.

### 3.2 Fidelidad sobre las 53: **0 fallos, los mismos 8 avisos**

Datos: `fidelidad53.json`. Los ocho avisos son los mismos ocho del informe anterior
(`tipico_mp3-to.flac`, `tipico_mp4-audio.flac`, `alpha_png-to.avif`, `alpha_png-to.jpg`,
`alpha_png-to.webp`, `trivial_png-to.webp`, `trivial_mp4-to-naive.gif`,
`trivial_mp4-to.webm`). **V2 y V5 no añaden ni un aviso ni un fallo.**

### 3.3 Los cinco fallos documentados: **12 de 12** — **MEDIDO**

Datos: `fallos5.json`. Cada caso contra los dos motores, con `alfa=True`.

| # | Fallo | Esperado | En proceso | Coste | Subproceso | Coste |
|---|---|---|---|---:|---|---:|
| 1 | PNG entregado con extensión `.avif` | fallo | **FALLO** ✔ | 72,3 ms | **FALLO** ✔ | 324,4 ms |
| 2 | pierde una pista de audio | fallo | **FALLO** ✔ | 1,1 ms | **FALLO** ✔ | 100,7 ms |
| 3 | degradación de 16 a 8 bits sin pedirla | fallo | **FALLO** ✔ | 0,7 ms | **FALLO** ✔ | 469,5 ms |
| 4a | redimensionado no solicitado | fallo | **FALLO** ✔ | 65,4 ms | **FALLO** ✔ | 230,8 ms |
| 4b | *control*: JPEG → PNG sin tocar geometría | ok | **OK** ✔ | 0,7 ms | **OK** ✔ | 102,9 ms |
| 5 | fichero de 0 bytes presentado como éxito | fallo | **FALLO** ✔ | 0,9 ms | **FALLO** ✔ | 52,8 ms |

---

## 4. El testigo que no vio nada — corrección de método

**Esto es una autocorrección y va aquí porque afecta a cómo se lee todo lo demás.**

El testigo de ruido que estableció `verificador-fidelidad.md` §8 —un bucle de Python
determinista medido antes y después de cada tanda, `SUCIA` si se desvía más del 20 %— **es
ciego a la contención multinúcleo**. Con 12 núcleos y otro agente (E1) midiendo en CPU, un
bucle monohilo de Python **cabe en un núcleo libre y no se entera**, mientras las sondas
externas van varias veces más lentas.

**La evidencia, con la misma medida repetida tres veces — MEDIDO:**

| Medida | Tanda 1 | Tanda 2 | Tanda 3 (con testigo nuevo) | Informe anterior |
|---|---:|---:|---:|---:|
| V6 `framemd5` de `trivial.mp4` | **879,3 ms** `limpia` | 163,4 ms `limpia` | **147,4 ms** `limpia` | 129,2 ms |
| V5 etiquetas de `patologico_2pistas.mkv` | **131,3 ms** `limpia` | 40,5 ms `SUCIA` | **36,6 ms** `limpia` | — |
| CONTRATO completo en proceso | 0,71 ms `limpia` | 0,40 ms `limpia` | **0,34 ms** `limpia` | 0,37 ms |
| Suite de fidelidad completa (53 salidas) | **109 978 ms** | — | **46 332 ms** | 28 858 ms |

**Una tanda etiquetada `limpia` dio ×6,8 sobre el mismo control del informe anterior.** Con el
precedente del proyecto —una tanda que coincidió con una descarga y dio un error de ×7,4— el
paralelismo es demasiado exacto para ignorarlo.

**La corrección: un segundo testigo, de lanzamiento de proceso.** Mide lo mismo que sufre una
sonda externa (planificador, E/S, Defender), no lo que sufre un bucle de Python. Se calibra
con la máquina en reposo al empezar y se marca `SUCIA` si el nivel sube más del 20 %:

```python
def _testigo_sub():
    t = time.perf_counter()
    subprocess.run(["ffprobe", "-v", "quiet", "-version"], capture_output=True,
                   stdin=subprocess.DEVNULL, timeout=60)
    return (time.perf_counter() - t) * 1000
```

**Los dos testigos miden cosas distintas y hay que llevar los dos:** el monohilo detecta
**deriva dentro** de la tanda; el de subproceso detecta el **nivel** de carga de la máquina.
El primero solo, no. Y hay un valor de calibración que sale gratis y es útil por sí mismo:

| Testigo en reposo | Mediana |
|---|---:|
| `ffprobe -version` | **26,5–26,8 ms** |
| `gswin64c --version` | **121,7 ms** |

**Ghostscript tarda 122 ms en arrancar** —cargar `gsdll64.dll`, 27,7 MB— antes de mirar el
fichero. Ese número reaparece en el §5.4 y cambia cómo se lee la comparación con la GPU.

**Todas las medidas de este informe que se reportan como coste unitario están tomadas con los
dos testigos**, salvo las tres tandas que se indican explícitamente. Las de `cobertura` del
§1.3 llevan solo el monohilo (se tomaron antes de la corrección) y por eso el §1.3 se apoya en
**comparaciones dentro de la misma tanda** (sin atajo / con atajo / `magick`), que son robustas
al nivel de carga.

---

## 5. C2 — el OCR que FileX obtiene sin tarjeta

### 5.1 Hacerlo funcionar — **MEDIDO**

Datos: `ocr_sonda.json`.

| Comprobación | Resultado |
|---|---|
| `gswin64c --version` | **10.07.0** |
| Dispositivos declarados en `-h` | **`ocr`, `hocr`, `pdfocr8`, `pdfocr24`, `pdfocr32`**, `txtwrite`, `docxwrite`, `xpswrite`, `pclm` |
| **Sin** `TESSDATA_PREFIX` | `rc=1` · `Error opening data file ./eng.traineddata` → `Tesseract couldn't load any languages!` |
| Sin él, con `-sOCRLanguage=spa` | `rc=1` · `Error opening data file ./spa.traineddata` |
| Con `TESSDATA_PREFIX` = `C:\Program Files\Tesseract-OCR\tessdata` | **`eng` funciona**; **`spa` falla**: ese tessdata solo trae `eng` y `osd` |
| Con `TESSDATA_PREFIX` al directorio propio (`eng`+`osd`+`spa`) | **`eng`, `spa`, `spa+eng` y `eng+spa` funcionan los cuatro** |
| `-dOCRLanguage=spa` | `rc=1` · `Invalid value for option -dOCRLanguage=spa, use -sNAME= to define string constants` |
| `-sOCRLanguage=deu` (no está en el tessdata) | `rc=1` · `Error opening data file …\deu.traineddata` |
| **`-sOCRLanguage=osd`** | **`rc=3221225477` (0xC0000005, violación de acceso)** · `Error: LSTM requested, but not present!!` |

Todo lo que `bench/fidelidad-caminos.md` §0.1 dejó apuntado se reproduce. Y aparece **una
cosa nueva y seria**:

> **`-sOCRLanguage=osd` no devuelve un error: revienta Ghostscript con una violación de
> acceso.** **MEDIDO.** `osd.traineddata` existe, se carga, y no es un modelo de
> reconocimiento; el resultado es un `0xC0000005`, no un código de salida. **Regla de diseño
> directa para FileX: el idioma de OCR nunca puede venir de la entrada del usuario sin pasar
> por una lista blanca.** Es la misma familia de fallo que `av1_nvenc`, que aparece listado y
> no funciona: **hay que sondear en ejecución, no deducir del catálogo.**

**Sobre `spa.traineddata`: no hubo que descargarlo, y eso NO significa que sea gratis.**
**MEDIDO.** Está en `C:\Program Files\PDFgear\tessdata\spa.traineddata` (2 294 433 bytes), con
otros 15 idiomas. **Lo puso PDFgear, no este proyecto.** El coste de distribución es real y
hay que decirlo con su número:

| Idioma | Bytes | De dónde sale en esta máquina |
|---|---:|---|
| `eng` | 4 113 088 | Tesseract-OCR (ajeno al proyecto) |
| `osd` | 10 562 727 | Tesseract-OCR (ajeno al proyecto) — **y hace reventar `gs` si se pide como idioma** |
| `spa` | 2 294 433 | **PDFgear** (ajeno al proyecto) |

**Conclusión de distribución: Ghostscript trae el motor pero no los datos.** Si FileX se apoya
en esta vía, tiene que **distribuir el `.traineddata` de cada idioma que declare soportar** —
del orden de **2–4 MB por idioma**, licencia Apache-2.0 en `tessdata`/`tessdata_fast`— y fijar
`TESSDATA_PREFIX` **en el entorno del proceso hijo**, no en la máquina. Los scripts de este
informe lo hacen así a propósito: **no se ha tocado ninguna variable de entorno del sistema.**

### 5.2 CER a ppp nativos, comparable con la tabla canónica — **MEDIDO**

Datos: `ocr_cer.json`. Rasterizado **a los ppp nativos** de `ocr-ppp-nativos.md` §1
(patológico 200, d1 150, d2 100, d3 100): **no se sobremuestrea**. Métrica:
`bench/scripts/ocr_eval.py` **sin modificar**, para que las cifras entren en la tabla canónica.

| Motor | patológico (200) | d1 (150) | d2 (100) | d3 (100) |
|---|---:|---:|---:|---:|
| PaddleOCR (PP-OCRv6 medium, es) · **GPU** | 0,0 % | 0,0 % | 0,0 % | **2,5 %** |
| Docling+RapidOCR torch (v6 small) · **GPU** | 0,0 % | 0,0 % | 0,0 % | 75,9 % |
| RapidOCR (PP-OCRv5 mobile, ONNX) · **GPU** | 1,3 % | 0,0 % | 0,0 % | 77,2 % |
| EasyOCR (CRAFT + latin_g2) · **GPU** | 0,0 % | 0,0 % | 43,0 % | 54,4 % |
| **gs `-sDEVICE=ocr`, `spa` · CPU** | **0,0 %** | **0,0 %** | **0,0 %** | **165,8 %** |
| **gs `-sDEVICE=ocr`, `eng` · CPU** | **0,0 %** | **0,0 %** | **1,3 %** | **245,6 %** |
| **gs `-sDEVICE=ocr`, `spa+eng` · CPU** | **0,0 %** | **0,0 %** | **0,0 %** | **216,5 %** |

*(Las cuatro primeras filas son de `bench/ocr-ppp-nativos.md` §3 y se citan, no se remiden.)*

**Tres lecturas:**

1. **En los tres documentos que la ruta actual resuelve, el OCR de CPU los resuelve
   igual: 0,0 %.** Sin tarjeta, sin venv, sin descargar un modelo, sin carga en frío.
2. **`spa` bate a `eng` donde el documento es marginal.** En d2 `eng` confunde «solo» con
   «golo» (1,3 %) y `spa` acierta. `spa+eng` empata con `spa`: combinar no aporta.
3. **En d3 no falla: alucina.** El CER pasa de 100 % porque **la salida es más larga que la
   referencia y es ruido**: `'a O | o — | o a a . a | oO a ENS CANEADO EE ES'`. Es un modo de
   fallo **cualitativamente distinto** al de los tres motores de GPU que también fallan en d3,
   que devuelven **poco** texto (menos de 30 caracteres, el titular y nada más). **Un
   orquestador que solo mire «¿hay texto?» clasificaría este fallo como éxito.** Ver §5.8.

*(Aviso de método: `ocr_eval.py` define CER = distancia de edición / longitud de la
referencia. **Puede pasar de 100 %** y aquí pasa. No es un error de la métrica; es lo que
significa cuando el motor inventa.)*

### 5.3 La regla R1 se confirma, y en d3 es brutal — **MEDIDO**

Datos: `ocr_ppp.json`. 60 celdas: 3 documentos × 10 resoluciones × 2 idiomas. CER con
`ocr_eval.py`.

| ppp | ×nativo (d3) | **d3 `spa`** | **d3 `eng`** | d2 `spa` | d2 `eng` | d1 `spa` |
|---:|---:|---:|---:|---:|---:|---:|
| 75 | ×0,75 | **105,1 %** | 153,2 % | 3,8 % | 2,5 % | 0,0 % |
| **100 (nativo d2/d3)** | **×1,00** | **165,8 %** | 245,6 % | **0,0 %** | 1,3 % | 0,0 % |
| 125 | ×1,25 | 307,6 % | 462,0 % | 0,0 % | 1,3 % | 0,0 % |
| 140 | ×1,40 | 303,8 % | 573,4 % | 0,0 % | 0,0 % | 0,0 % |
| 150 | ×1,50 | 402,5 % | 853,2 % | 0,0 % | 1,3 % | **0,0 %** (nativo d1) |
| 160 | ×1,60 | 250,6 % | 700,0 % | 0,0 % | 0,0 % | 0,0 % |
| 175 | ×1,75 | 481,0 % | 1 654,4 % | 0,0 % | 1,3 % | 0,0 % |
| 200 | ×2,00 | 715,2 % | 1 449,4 % | 0,0 % | 2,5 % | 0,0 % |
| 250 | ×2,50 | 635,4 % | 1 402,5 % | 0,0 % | 0,0 % | 0,0 % |
| 300 | ×3,00 | **834,2 %** | **1 570,9 %** | 0,0 % | 0,0 % | 0,0 % |

- **En d3, sobremuestrear es monótonamente catastrófico**: de 105 % a 834 % con `spa`, de 153 %
  a 1 571 % con `eng`. **No hay acantilado: hay una rampa.** Cuantos más píxeles, más ruido
  inventa. Es la confirmación más fuerte de R1 que ha producido el proyecto, y llega de un
  motor completamente distinto a los cuatro con los que se calibró.
- **En d2 y d1 no hay techo ×1,4 visible con `spa`: la curva es plana en 0,0 % de 100 a 300
  ppp.** El acantilado entre ×1,4 y ×1,6 que `ocr-ppp-nativos.md` §5 midió **es de PaddleOCR,
  no de la resolución**. Aquí sale la otra mitad del mismo argumento: la degradación por
  sobremuestreo **existe pero depende del motor**.
- **El suelo por abajo SÍ se reproduce**: a 75 ppp d2 pasa de 0,0 % a 3,8 % (`spa`) y d3 empeora.
  Coincide con lo medido para RapidOCR (0,0 → 44,3 % en d2 a 75 ppp). **Submuestrear hace daño
  antes de que sobremuestrear lo haga**, también aquí.

**Consecuencia para la regla:** `ppp_ocr = clamp(ppp_nativos, 100, ppp_nativos × 1,4)` **sigue
siendo la elección correcta** — es la única que va bien con los cinco motores medidos. Con el
matiz de que el techo protege a unos motores y el suelo a todos.

### 5.4 Tiempo, y la comparación honesta con la GPU — **MEDIDO**

Datos: `ocr_tiempo.json`. Mediana n=9, con los dos testigos (§4).

| Documento | ppp | `-sDEVICE=ocr` **eng** | **spa** | `pdfocr8` **spa** |
|---|---:|---:|---:|---:|
| `patologico_escaneado` | 200 | 726,9 ms | 664,5 ms | 1 087,0 ms |
| `escaneado_d1` | 150 | 243,2 ms | 242,4 ms | 355,1 ms |
| `escaneado_d2` | 100 | 236,5 ms | **225,8 ms** | 253,7 ms |
| `escaneado_d3` | 100 | 1 025,3 ms | 1 030,6 ms | 1 071,7 ms |
| *suelo:* `txtwrite` sobre d2, **sin OCR** | — | — | **189,0 ms** | — |
| *suelo:* `gswin64c --version` (solo arrancar) | — | — | **121,7 ms** | — |

**La comparación con los motores de GPU hay que hacerla con dos avisos, y sin ellos es
tramposa:**

- La tabla de `ocr-ppp-nativos.md` §7.1 mide **el OCR sobre una imagen ya rasterizada, en un
  proceso ya caliente**. La de arriba mide **arrancar el proceso, cargar 27,7 MB de DLL,
  parsear el PDF, rasterizar y reconocer**, todo dentro de la misma invocación.
- Por eso el número comparable no es el bruto sino el **incremento sobre el suelo**.

| Documento | gs bruto (`spa`) | gs − suelo `txtwrite` | PaddleOCR GPU | RapidOCR GPU | EasyOCR GPU |
|---|---:|---:|---:|---:|---:|
| `patologico_escaneado` (200) | 664,5 ms | ~475 ms | 270,6 ms | 465,3 ms | 537,4 ms |
| `escaneado_d1` (150) | 242,4 ms | ~53 ms | 151,3 ms | 149,3 ms | 276,6 ms |
| `escaneado_d2` (100) | 225,8 ms | **~37 ms** | 90,7 ms | 82,1 ms | 183,8 ms |
| `escaneado_d3` (100) | 1 030,6 ms | ~842 ms | 82,6 ms | 69,1 ms | 309,2 ms |

**El resultado que decide:**

1. **En bruto, el OCR de CPU está en el mismo orden de magnitud que los motores de GPU** —de
   ×1,6 a ×2,5 más lento que el mejor de ellos en los tres documentos que resuelve—, no en
   otro planeta.
2. **Descontando el suelo, en d1 y d2 es más rápido que cualquiera de ellos.** El trabajo de
   OCR propiamente dicho cuesta ~37 ms en d2.
3. **Y la carga en frío no se compara: no existe.** Los motores de GPU cuestan **3,4–17,3 s**
   de carga en frío (`ocr-ppp-nativos.md` §7.1); Ghostscript, **122 ms**. Para una CLI que
   convierte un fichero y termina, **la carga en frío ES el coste**, y ahí la diferencia es de
   **28× a 142×** a favor de la CPU.
4. **d3 cuesta 4,5× más que d2 a la misma resolución** (1 031 ms frente a 226 ms). Alucinar es
   caro: el reconocedor emite muchas más cajas. **El tiempo es, por sí mismo, una señal de
   degradación** — apuntado como candidato para la heurística B7 de `ESTADO-Y-REPARTO.md`,
   **PENDIENTE** de calibrar.
5. **VRAM: 0 MiB.** No es una cifra pequeña: es una columna entera del presupuesto del sidecar
   (hito 6) que desaparece. EasyOCR llegó a 11 877 de 12 288 MiB con **un documento de una
   página**.

### 5.5 Castellano con tildes: las dos lecturas — **MEDIDO**

Ninguna medición de OCR del proyecto llevaba tildes, y `bench/scripts/ocr_eval.py` **normaliza
quitándolas** (`NFKD` + descarte de combinantes + `[^a-z0-9 ]`). Para cerrar esa laguna se
fabricó un PDF castellano a 150 ppp con tildes, eñes y diéresis —**en `fixtures/`, sin tocar
`corpus/`, que es la base de 296 celdas ya medidas**— y se midió con **los dos evaluadores**.
El sensible a tildes es `ocr_eval_tildes.py`, **copia** de `ocr_eval.py` (que es arnés
compartido y no se modifica). Datos: `ocr_acentos.json`.

Texto real: `INFORME TÉCNICO` / `La conversión se añadió en el último año.` /
`Ñandú, camión, acción, pequeñez y ambigüedad.`

| Idioma | CER con `ocr_eval.py` (**ciego a tildes**) | **CER real (con tildes)** | Puntos que oculta el evaluador | Frases exactas |
|---|---:|---:|---:|---:|
| **`spa`** | 2,0 % | **1,9 %** | −0,1 | **2 de 3** |
| **`eng`** | **9,2 %** | **15,5 %** | **+6,3** | **0 de 3** |
| `spa+eng` | 2,0 % | 1,9 % | −0,1 | 2 de 3 |

Lo que devuelve cada uno:

```
spa : INFORME TÉCNICO / La conversión se añadió en el último año.
      / Ñandú, camión, acción, pequeñez y ambigiledad.
eng : INFORME TECNICO / La conversion se afiadio en el ultimo afio.
      / Nandu, camion, accién, pequefiez y ambigiiedad.
```

**Tres conclusiones, y la segunda es la importante para todo el proyecto:**

1. **`spa` lee el castellano acentuado bien: 1,9 % de CER.** Su único fallo es la diéresis:
   `ambigüedad` → `ambigiledad`. Cierra el PENDIENTE que dejó `fidelidad-caminos.md` §0.1.
2. **El evaluador compartido subestima el error de `eng` en 6,3 puntos, un 41 % relativo.**
   `eng` transcribe **`añadió` → `afiadio`, `año` → `afio`, `Ñandú` → `Nandu`**: destruye
   sistemáticamente la eñe y todas las tildes. `ocr_eval.py` da 9,2 % porque **normaliza
   exactamente el error que se quiere medir**. La ceguera no es teórica: **es de 6,3 puntos
   sobre un texto de tres frases.** Confirma el diagnóstico de `ocr-ppp-nativos.md` §8 con un
   número.
3. **Elegir mal el idioma cuesta 13,6 puntos de CER real (1,9 → 15,5 %) y no cuesta un
   milisegundo** (§5.4: `eng` y `spa` tardan lo mismo, 236,5 y 225,8 ms en d2). **El idioma
   del reconocedor es un parámetro obligatorio, no una preferencia**, y no hay ningún motivo
   de coste para no fijarlo.

*(Límite: son 3 frases y 105 caracteres, un caso, no un corpus. La comparación fuerte entre
motores con tildes la dará el `escaneado_d4` de G1. Lo que aquí queda **MEDIDO** es que la
ceguera del evaluador tiene un tamaño y no es despreciable.)*

### 5.6 La arista de reparación, y la pregunta del hito 1 — **MEDIDO**

Datos: `ocr_reparacion.json`. Dos caminos por documento, con el mismo destino.

| Documento | 1 salto: `docxwrite` directo | | 2 saltos: `pdfocr8` → `docxwrite` | | |
|---|---:|---|---:|---:|---|
| | **chars** | veredicto | **chars** | **CER** | tiempo total |
| `patologico_escaneado` | **2** | DESTRUIDO | **99** | **0,0 %** | 1 255 ms |
| `escaneado_d1` | **2** | DESTRUIDO | **102** | **0,0 %** | 549 ms |
| `escaneado_d2` | **2** | DESTRUIDO | **102** | **0,0 %** | 438 ms |
| `escaneado_d3` | **2** | DESTRUIDO | 173 | **119,0 %** | 1 225 ms |

Y la capa de texto que queda dentro del PDF intermedio, leída con `txtwrite`:

| Documento | caracteres | CER | ¿supera el umbral P6 (≥10)? |
|---|---:|---:|---|
| `patologico_escaneado` | 97 | **0,0 %** | sí |
| `escaneado_d1` | 114 | **0,0 %** | sí |
| `escaneado_d2` | 100 | **1,3 %** | sí |
| `escaneado_d3` | 170 | **93,7 %** | **sí — y es ruido** |

**Esto reproduce y cuantifica J10/J11 de `fidelidad-caminos.md`:** el camino de un salto
entrega un `.docx` **sin una sola línea del documento** (2 caracteres, por debajo del umbral
P6, que es exactamente el caso para el que se calibró el umbral) y el camino de **dos** saltos
gana. La novedad es el número: **0,0 % de CER en tres de los cuatro**, y **el coste completo
por debajo de 1,3 s**.

> ### La respuesta a la pregunta del encargo
>
> **«¿Basta el OCR de Ghostscript en CPU para la arista de reparación `pdf escaneado → docx`
> conservando texto, que es el "objetivo mejor" del hito 1?»**
>
> **SÍ, en 3 de los 4 documentos del corpus, con 0,0 % de CER y en 438–1 255 ms — y NO en el
> cuarto.** **MEDIDO.**
>
> Con tres precisiones que cambian cómo se usa la respuesta:
>
> 1. **La arista `pdf escaneado → docx` de un salto no existe**: `docxwrite` directo entrega
>    2 caracteres. Lo que existe es la de **dos** saltos, `pdfocr8` y luego `docxwrite`. El
>    criterio de aceptación del hito 1 se cumple **si y solo si el grafo sabe insertar el paso
>    de OCR**, que es justo lo que `fidelidad-caminos.md` §6 proponía demostrar.
> 2. **`escaneado_d3` no se resuelve, y de los cinco motores medidos en este proyecto solo
>    PaddleOCR lo resuelve (2,5 %).** La arista de reparación en CPU cubre el caso normal, no
>    el caso degradado. Para el degradado sigue haciendo falta el sidecar de GPU (hito 6).
> 3. **Y hoy el verificador no sabe distinguir un caso del otro** (§5.8). Mientras no lo sepa,
>    la arista es utilizable pero **no es verificable**, y en este proyecto eso es media
>    respuesta.

### 5.7 El 99,0 % de `fidelidad-caminos.md` **no** se reproduce — **MEDIDO**

El camino I1 (`pdf con texto → png → pdf → txt` con OCR) se le atribuye una similitud del
**99,0 %**, y es la cifra que sostiene el peso `1000 · (1 − similitud)` de su función de coste
(§5.2 de aquel informe). Reejecutado:

| Normalización | `eng` | `spa` |
|---|---:|---:|
| Espacios normalizados (`" ".join(t.split())`) | **94,7 %** (7 de 105) | **94,7 %** (7 de 105) |
| Espacios **ignorados** | **97,1 %** (3) | 96,2 % (4) |
| Con `ocr_eval.py` (ciego a tildes) | 97,5 % | 94,2 % |

**No llega al 99,0 % con ninguna de las tres lecturas.** La distancia es pequeña —de 3 a 7
caracteres sobre 105— y las diferencias son identificables: `FileX` → `Filex`, el carácter
*mojibake* que el PDF original ya traía (`ˆ\x91`), y los tres espacios de `Col A` / `Col B` /
`Col C` que el OCR une en `ColA`.

**No se declara refutado, se declara NO REPRODUCIDO**, y por un motivo concreto: aquel informe
**no publica ni los ppp de su rasterizado ni el idioma de OCR ni su fórmula de similitud**, y
aquí se ha usado 150 ppp y dos normalizaciones distintas. Lo que sí queda **MEDIDO** es que
**el orden de magnitud correcto es 94–97 %, no 99 %**, y que **la mayor parte de la pérdida
son espacios, no letras** — lo cual, si se confirma, hace la cifra *mejor* de lo que parece
para el uso al que se destina (recuperar contenido) y *peor* para el otro (reproducir
maquetación). **PENDIENTE** de que se publiquen los parámetros de I1 para cerrarlo.

### 5.8 El verificador declara `OK` una alucinación — **MEDIDO**

Pasando el PDF reparado de `escaneado_d3` por el propio verificador:

```
CONTRATO (grupo A)     OK          escaneado_d3_ocr_spa.pdf
  (sin hallazgos)                  cobertura: completa   ms: 0,89
FIDELIDAD (grupo C)    OK          escaneado_d3_ocr_spa.pdf
  [pF P6 informativo] texto extraido: 75 caracteres imprimibles (umbral 10)
  [pF P5 informativo] la entrada no tiene capa de texto (0 caracteres):
                      no se exige texto en la salida
```

**El texto son 75 caracteres de ruido puro y el verificador no protesta.** La cadena es
correcta regla a regla y equivocada como conjunto:

- **P5** dice: *«un PDF escaneado sin capa de texto sigue sin tenerla tras convertir: no es un
  fallo salvo que se pidiera OCR»*. Se pidió OCR, pero **el `pedido` no lleva ese dato**.
- **P6** exige **≥10 caracteres imprimibles**, umbral calibrado contra la basura de 1-3
  caracteres de `txtwrite`. **75 caracteres de ruido lo superan siete veces.**

**El umbral de P6 protege contra la basura de `txtwrite`, no contra la alucinación de un
OCR. Son dos fallos distintos y el proyecto solo tenía medido el primero.**

**Hay señal barata que los separa, y está en proceso.** Sobre las cuatro capas OCR realmente
producidas, más el control de un PDF con capa de texto real (`senal_alucinacion.json`):

| Capa de texto | tokens | **longitud media** | **% de tokens de 1 letra** | % con ≥3 letras | ¿pasa P6? |
|---|---:|---:|---:|---:|---|
| `patologico_escaneado` (0,0 % CER) | 12 | **5,67** | **0,0 %** | 100 % | sí |
| `escaneado_d1` (0,0 %) | 12 | **5,67** | **0,0 %** | 100 % | sí |
| `escaneado_d2` (1,3 %) | 11 | **6,18** | **0,0 %** | 100 % | sí |
| **`escaneado_d3` (93,7 %)** | 34 | **2,03** | **61,8 %** | 26,5 % | **sí** |
| *control:* `tipico_texto.pdf`, capa **real** | 24 | 4,04 | 33,3 % | 62,5 % | sí |

**Propuesta, marcada como lo que es:** una regla `P9` para la arista de reparación —
*«si se pidió OCR, la capa resultante debe tener longitud media de token ≥ 3,0 y menos del
50 % de tokens de una sola letra»*— separa los cinco casos, **cuesta microsegundos y no lanza
ningún proceso** (el texto ya está extraído por P6). **Está calibrada sobre 5 puntos: es una
propuesta, no una regla validada.** El control es deliberadamente el caso más difícil: un PDF
con tabla (`Col A` / `1 2 3`) llega al 33,3 % de tokens de una letra, así que el margen entre
33,3 % y 61,8 % es lo que hay, y no es enorme. **PENDIENTE** de validar contra un corpus de
capas OCR reales.

**Y la corrección que no hace falta calibrar: el `pedido` tiene que llevar `ocr: true`.** Sin
ese dato P5 no puede hacer su trabajo, porque la propia regla dice *«salvo que se pidiera
OCR»* y hoy el verificador no tiene forma de saberlo. Es, otra vez, el punto 4 del contrato:
**pedido frente a obtenido**.

### 5.9 Una observación no reproducida, que se anota igual

En la **primera** ejecución del verificador sobre `escaneado_d3_ocr_spa.pdf`, P6 devolvió **0
caracteres** en vez de 75. Reejecutado inmediatamente: 75. Repetido **20 veces seguidas sobre
los dos ficheros: 20 de 20 con el mismo valor** (75 en d3, 70 en d2). **Dos intentos, no
reproducido, se documenta y se sigue.** No afecta a ninguna conclusión —de hecho el valor malo
llevaba al veredicto conservador— pero un `txtwrite` que devuelve vacío una vez de cada muchas
sería grave para una regla de severidad `fallo` como P2, y queda apuntado.

---

## 6. Coste de implementación — **MEDIDO**

`bench/scripts/verificador.py`: de **3 035** a **3 859** líneas, **+824 netas**. Sigue sin una
sola dependencia externa.

| Bloque | Líneas | De código |
|---|---:|---:|
| **TIFF comprimido** (IFD completa, descompresión, carriles, predictor, planar, 16 bits) | 209 | 173 |
| **PNG entrelazado Adam7** (7 pasadas + atajo por pasada) | 144 | 126 |
| **LZW de TIFF + LZW de GIF + PackBits** | 118 | 93 |
| **GIF** (barrido real de bloques + fotograma 1) | 111 | 99 |
| **V2/V5**: sondas `ffprobe` | 33 | 30 |
| **V2/V5**: las reglas dentro de `fidelidad_video` | ~65 | ~57 |
| `_pixel_en_byte` (la corrección de la coordenada) | 17 | 15 |
| Atajos de fila opaca, despachador, CLI y ayuda | ~127 | ~110 |

**Las tres lecturas:**

- **El 70 % de lo añadido (582 de 824 líneas) vuelve a ser «fabricar el acceso al dato».**
  Es el tercer informe seguido que mide lo mismo: 53 % en el prototipo original, 61 % en la
  extensión de fidelidad, **70 % aquí**. **La lógica de la regla nunca es el coste.**
- **Los dos dialectos de LZW son 93 líneas de código y son la mitad del riesgo.** TIFF empaqueta
  MSB primero con *early change*; GIF, LSB primero sin él. **Confundirlos no da error: da bytes
  plausibles y equivocados**, que para un verificador es el peor fallo posible. Por eso los
  36 contrastes contra `magick` del §1.2 no son un adorno: son la única prueba de que el
  decodificador es correcto.
- **Las estimaciones del informe anterior se quedaron cortas, y por poco.** Estimaba 120-180
  líneas para «TIFF y GIF» y 40 para Adam7; el coste real es **438** para TIFF+GIF+LZW y
  **144** para Adam7 —×2,9 y ×3,6—. La diferencia entera está en lo que no se ve desde fuera:
  el predictor, el planar, los 16 bits, el barrido correcto de bloques del GIF y los atajos
  sin los que la cobertura no compensaba.

---

## 7. Lo que sigue **PENDIENTE**

De los siete pendientes de `verificador-fidelidad.md` §7, **quedan cerrados el 1 (salvo
AVIF/HEIF, cerrado por decisión) y el 5 (V2 y V5; D3/D6/D7 siguen sin implementar)**. Lo que
este informe deja abierto:

1. **`min(alfa)` de AVIF/HEIF.** Sigue «no evaluable» **a propósito**: exigiría un decodificador
   AV1 en proceso. No es una tarea, es una decisión tomada.
2. **TIFF en teselas, TIFF con compresión JPEG, TIFF de coma flotante y WebP animado.** Cuatro
   «no evaluable» nuevos, cada uno con su motivo escrito. Ninguno aparece en el corpus.
3. **GIF animado cuyo fotograma 1 no cubre el lienzo y cuyos fotogramas posteriores sí revelan
   transparencia.** Exigiría componer la animación. Sin caso que lo pida.
4. **Validar `P9`** (la señal contra la alucinación) contra un corpus de capas OCR reales. Está
   calibrada sobre 5 puntos.
5. **Añadir `ocr: true` al `pedido`** para que P5 pueda distinguir «no se pidió OCR» de «se
   pidió y salió ruido». Es una línea del contrato, no del verificador.
6. **V2 necesita su propio interruptor dentro del grupo C.** Cuesta el 36 % de la suite.
7. **`D3/D6/D7`** (contenido exacto de los campos de datos) siguen sin implementar, como ya
   decía el informe anterior.
8. **Los 7 casos `no_evaluable` de `referencia.json`** siguen sin motor en esta máquina (es el
   encargo C8, de E1).
9. **El `txtwrite` que devolvió vacío una vez** (§5.9). No reproducido en 20 intentos.
10. **Los parámetros de I1** en `fidelidad-caminos.md`, para poder cerrar el 99,0 % (§5.7).
11. **El tiempo como señal de degradación de OCR** (§5.4, punto 4): d3 cuesta 4,5× lo que d2 a
    la misma resolución. Encaja con el pendiente B7 y está sin calibrar.

---

## 8. Para D1 — lo que este informe cambia en los documentos maestros

**No he tocado ningún maestro** (los lleva D1 en paralelo). Esto es lo que hay que llevarse, con
su fuente:

| Documento | Qué dice hoy | Qué hay que añadir | Fuente aquí |
|---|---|---|---|
| `HUECOS.md` §5 | El OCR embebido de Ghostscript aparece como vía sin ejercitar | **Ejercitado.** 0,0 % de CER en patológico, d1 y d2 a ppp nativos con `spa`; fracasa en d3 alucinando (165,8 %). VRAM 0. Carga en frío 122 ms frente a 3,4–17,3 s | §5.2, §5.4 |
| `HUECOS.md` §5 | — | **La arista de reparación `pdf escaneado → docx` funciona en 3 de 4, con 0,0 % de CER y < 1,3 s**, y solo con **dos** saltos: el `docxwrite` directo entrega 2 caracteres | §5.6 |
| `PLAN-ORQUESTADOR.md` §4.2 / §4.6 | Regla de ppp con techo ×1,4 y suelo 100 | **Se confirma con un quinto motor y desde otro ángulo:** en d3 el OCR de gs empeora **monótonamente** al sobremuestrear (105 % → 834 %); en d2/d1 la curva es **plana** entre 100 y 300 ppp. **El acantilado ×1,4/×1,6 es de PaddleOCR; el suelo de 75 ppp es de todos** | §5.3 |
| `PLAN-ORQUESTADOR.md` §5 (reglas de diseño) | «Sondear capacidades en ejecución, no deducirlas» | **Caso nuevo y más grave que `av1_nvenc`: `-sOCRLanguage=osd` revienta Ghostscript con `0xC0000005`.** El idioma de OCR **exige lista blanca**, nunca entrada del usuario | §5.1 |
| `PLAN-ORQUESTADOR.md` §7, hito 1 | Criterio propuesto: «resuelve `pdf escaneado → docx` conservando el texto» | **Alcanzable hoy y sin GPU, en 3 de los 4 documentos**, con la condición de que el grafo sepa **insertar** el paso de OCR (dos saltos, no uno) | §5.6 |
| `PLAN-ORQUESTADOR.md` (distribución) | — | **Ghostscript trae el motor de OCR pero no los datos de idioma.** FileX tendría que distribuir 2–4 MB por idioma y fijar `TESSDATA_PREFIX` en el entorno del hijo | §5.1 |
| `HUECOS.md` §1 / `ANALISIS-COMPLETO.md` | Prototipo: 3.035 líneas, 5/5 fallos, 0 FP sobre 53 | **3.859 líneas. Siguen 0 FP en las seis configuraciones y 12/12 fallos atrapados.** La fidelidad pasa de 28 858 a **46 332 ms** (+60,6 %) por V2 | §2.2, §3 |
| `ocr-ppp-nativos.md` §8 / cualquier cita de `ocr_eval.py` | «la métrica actual es estructuralmente ciega a las tildes» | **Ahora con número: oculta 6,3 puntos de CER (9,2 % frente a 15,5 % reales) para `eng` sobre castellano acentuado.** Y `spa` lee las tildes bien: 1,9 % | §5.5 |
| Metodología (todos) | Testigo de CPU antes/después, umbral 20 % | **Ese testigo es ciego a la contención multinúcleo.** Etiquetó `limpia` una tanda que salió ×6,8 sobre el mismo control. Hace falta **un segundo testigo, de lanzamiento de proceso** | §4 |
| `fidelidad-caminos.md` §3 (I1) | Similitud 99,0 % | **NO REPRODUCIDO.** 94,7 % con espacios normalizados, 97,1 % ignorándolos. No se declara refutado: aquel informe no publica sus parámetros | §5.7 |

---

## 9. Índice de datos crudos

Todo en `bench/salidas-verificador-gs/`, con su `MANIFIESTO.md` (48 binarias, 21,6 MB,
borradas, con `sha256`, tamaño y la orden exacta que reproduce cada una).

| Fichero | Contenido |
|---|---|
| `gen_fixtures.py`, `gen_predictor.py`, `gen_adam7_4b.py` | Los 27 ficheros de prueba. El segundo escribe TIFF con `Predictor=2` a mano porque `magick` ignora la opción; el tercero, PNG de paleta de 2 bits entrelazado, que `magick` no sabe escribir con `tRNS` |
| `inspecciona_fixtures.py`, `fixtures_inspeccion.json` | Las IFD y las cabeceras de cada fixture, y la verdad de `magick`. **Fuente del §1.2** |
| `prueba_alfa.py`, `alfa_cobertura.json` | `min(alfa)` en proceso frente a `magick`, **36 ficheros, 0 discrepancias**. **Fuente del §1.2 y del §1.5** |
| `medir_gs.py` | Banco de medida. Copia adaptada de `medir_fid.py`, que es del informe anterior y **no se toca**. Cinco subcomandos y **los dos testigos de ruido** |
| `cobertura_alfa_sin_atajo.json` / `cobertura_alfa.json` | Coste de `min(alfa)` en los formatos nuevos, **antes y después** del atajo de fila opaca. **Fuente del §1.3** |
| `reglas_v2_v5.json` | Coste unitario de V2 y V5, mediana n≥9, con nivel verificado. **Fuente del §2.2 y del §4** |
| `contrato53.json` | Las 53 salidas por el contrato, 2 motores × 3 modos de alfa. **Fuente del §3.1** |
| `fidelidad53.json` | Las 53 salidas por las 12 reglas de fidelidad. **Fuente del §2.2 y del §3.2** |
| `fallos5.json` | Los 5 fallos documentados, con los dos motores. **Fuente del §3.3** |
| `discrimina_v2_v5.py`, `discriminacion_v2_v5.json` | Los cuatro fallos fabricados y sus controles. **Fuente del §2.3** |
| `ocr_gs.py` | Banco del OCR embebido. Seis subcomandos. `TESSDATA_PREFIX` **solo en el entorno del hijo** |
| `ocr_eval_tildes.py` | Evaluador de OCR **sensible a las tildes**. Copia de `ocr_eval.py`, que es arnés compartido |
| `ocr_sonda.json` | Dispositivos, idiomas, los errores exactos y el `0xC0000005`. **Fuente del §5.1** |
| `ocr_cer.json`, `ocr/*.txt` | CER a ppp nativos, 4 documentos × 3 idiomas, con el texto devuelto. **Fuente del §5.2** |
| `ocr_ppp.json` | 60 celdas del barrido de ppp. **Fuente del §5.3** |
| `ocr_tiempo.json` | Mediana n=9 de `ocr` y `pdfocr8`, con los dos suelos. **Fuente del §5.4** |
| `ocr_acentos.json` | El PDF castellano acentuado, con las dos lecturas. **Fuente del §5.5** |
| `ocr_reparacion.json` | Las cuatro cadenas de reparación y el camino I1. **Fuente del §5.6 y del §5.7** |
| `senal_alucinacion.py`, `senal_alucinacion.json` | La señal que separa texto recuperado de ruido. **Fuente del §5.8** |

**Metodología.** Medianas, nunca medias; n=9 en todo coste unitario (n=15 en el contrato de
referencia). Calentamiento antes de cada tanda. **Dos testigos de ruido** —uno de CPU monohilo
para la deriva, otro de lanzamiento de proceso para el nivel—, umbral del 20 % en los dos; ver
§4 para por qué el segundo tuvo que añadirse a mitad del trabajo. **No se usó la GPU ni se tomó
su lock** (lo tenía G1). **No se ha modificado ninguna variable de entorno del sistema, ningún
fichero del corpus, ningún arnés compartido y ningún documento maestro.** Sin dependencias
nuevas: `verificador.py` sigue siendo biblioteca estándar de Python y nada más.
