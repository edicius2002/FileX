# Matriz de formatos — extraída del código, no de los README

Fuente: parseo automático de las declaraciones `properties.from` / `properties.to` de los 20 adaptadores de ConvertX (`repos/orchestrators/ConvertX/src/converters/*.ts`). Son las tablas que el código consulta en tiempo de ejecución.

> ## ⚠️ Aviso de lectura, añadido el 21/08/2026: **todo lo de este documento es cobertura DECLARADA, y ahora existe su factor de descuento MEDIDO**
>
> `bench/aristas-nominales.md` ejecutó **1 104 sondas de semiarista** (censo completo) y **598 aristas** de una muestra aleatoria estratificada, verificando cada salida con el verificador del proyecto. Resultado:
>
> > **El 50,5 % de las aristas declaradas que se han podido verificar NO EXISTE.** IC 95 % **[48,2 % – 53,0 %]**, sobre **62 487 aristas (45,1 % de la población)**. **Declarado explícitamente como COTA INFERIOR.**
>
> **Este documento no se corrige: sus cifras son correctas para lo que miden.** Lo que cambia es cómo hay que citarlas — **una tabla declarada no es una capacidad** —, y ese era ya el argumento del propio documento («las cifras de cobertura del sector describen tablas declaradas, no capacidades reales»). **Ahora tiene número.** Ver §«El descuento medido», al final.
>
> **Ampliado el 21/08/2026 a las 14:00:** el descuento **tiene a su vez su propia recuperación. El 18,8 % de ese 50,5 % era INVOCACIÓN, no capacidad**: con los mismos motores y el mismo build la tasa baja a **41,0 %**, y **3 226 aristas (10,2 %) son ganancia automática**. **Hay que citar los tres números juntos —50,5 % declarado, 41,0 % con invocación cuidada, 3,0-3,1 % en el estrato documental— o cualquiera de ellos engaña.** Ver §6.

## Cobertura declarada por motor

| Motor | Formatos entrada | Formatos salida | Entradas exclusivas |
|---|---:|---:|---:|
| ffmpeg | 473 | 202 | **422** |
| imagemagick | 245 | 183 | 78 |
| graphicsmagick | 167 | 130 | 29 |
| assimp | 77 | 23 | 69 |
| vips | 45 | 23 | 17 |
| libreoffice | 41 | 22 | 29 |
| pandoc | 40 | 58 | 31 |
| calibre | 26 | 20 | 16 |
| libheif | 11 | 3 | 4 |
| libjxl | 11 | 10 | 0 |
| vtracer | 8 | 1 | 0 |
| inkscape | 7 | 17 | 0 |
| markitdown | 6 | 1 | 3 |
| dasel | 5 | 4 | 2 |
| dvisvgm | 4 | 2 | 2 |
| potrace | 4 | 11 | 0 |
| xelatex | 2 | 1 | 1 |
| msgconvert | 1 | 1 | 1 |
| resvg | 1 | 1 | 0 |
| vcf | 1 | 1 | 1 |

**Totales canónicos:** **896 formatos de entrada únicos, 503 de salida.**

> **Corrección metodológica.** Una primera extracción dio 893/496 porque la expresión regular limitaba los identificadores a 12 caracteres y descartaba 7 dialectos largos de pandoc (`markdown_strict`, `markdown_phpextra`, `asciidoc_legacy`, `jats_archiving`, `jats_articleauthoring`, `jats_publishing`, `pandoc native`). Las cifras de este documento son las de la extracción sin límite de longitud, confirmadas por una segunda extracción independiente vía AST.

## El agujero que nadie menciona: ConvertX no convierte hojas de cálculo

Búsqueda de `xlsx`, `xls` y `ods` en los 20 adaptadores: **cero apariciones**, ni como entrada ni como salida. Tampoco `ppt` ni `odp`; `pptx` solo entra por markitdown y sale por pandoc.

La causa está en `libreoffice.ts`: registra **únicamente la familia `text:`** (líneas 6 y 51), aunque el binario `soffice` que invoca convierte hojas de cálculo y presentaciones sin problema. **Es una limitación de la tabla declarada, no del motor.**

Un proyecto de 18 500 estrellas que anuncia "1000+ formatos" no puede convertir un Excel. Refuerza la tesis central de esta investigación: **las cifras de cobertura del sector describen tablas declaradas, no capacidades reales**, y por eso todo aquí se ha extraído del código.

## Dos conclusiones que cambian las prioridades

### 1. El "1000+ formatos" del marketing son en realidad dos binarios
**ffmpeg e ImageMagick juntos cubren 675 de los 896 formatos de entrada: el 75%.** Todo el resto del ecosistema aporta el 24% restante. Integrar bien esos dos motores es el 76% del trabajo de cobertura.

### 2. Los motores irremplazables se identifican por sus formatos exclusivos
- **ffmpeg** (422 exclusivos): insustituible. `264`, `265`, `3dostr`, `4xm`, `669`...
- **imagemagick** (78): `ai`, `bayer`, `bgra`, `bmp2`...
- **assimp** (69): todo el 3D (`3ds`, `3mf`, `ac3d`, `ase`). *Categoría excluida por decisión tuya, pero el adaptador existe si algún día interesa.*
- **pandoc** (31): el markup académico (`bibtex`, `biblatex`, `commonmark`, `djot`, `creole`).
- **libreoffice** (29): la ofimática heredada (`doc`, `docm`, `dot`, `abw`, `cwk`, `602`).
- **calibre** (16): ebooks y cómic (`azw4`, `cbr`, `cbz`, `cb7`, `chm`, `djvu`).
- **vips** (17): imagen científica y microscopía (`mrxs`, `ndpi`, `nia`, `svs`).

Ninguno de estos siete se puede suprimir sin perder una categoría entera.

## El cálculo que justifica el grafo de conversión

Con las mismas 20 tablas, se comparó la cobertura del despacho de un salto (lo que hace todo el ecosistema) contra un grafo dirigido recorrido hasta 3 saltos:

| Estrategia | Pares (origen, destino) alcanzables |
|---|---:|
| **1 salto** (ConvertX, transmute, SnapOtter, todos) | 152 584 |
| **Grafo, hasta 3 saltos** | **447 398** |
| **Conversiones nuevas que hoy no puede hacer nadie** | **294 814** |

**Multiplicador: 2,93× la cobertura, con exactamente los mismos motores instalados.**

Ejemplos verificados sobre el grafo real:

| Conversión | Estado hoy | Con grafo |
|---|---|---|
| `epub` a `png` | ❌ imposible | ✅ 2 saltos |
| `docx` a `webp` | ❌ imposible | ✅ 2 saltos |
| `tex` a `docx` | ❌ imposible | ✅ 2 saltos |
| `cbz` a `pdf` | ✅ ya directo | igual |
| `heic` a `avif` | ✅ ya directo | igual |

### Salvedad honesta
La cifra de 447 398 es un **límite superior de alcanzabilidad, no una promesa de fidelidad**. Encadenar degrada: pasar por un formato rasterizado pierde el texto seleccionable, y algunos pares declarados son nominales (un motor "acepta" un formato con soporte parcial). Por eso el grafo necesita **coste por arista** —velocidad, pérdida de calidad, si preserva texto— y no solo conectividad. Un camino de 3 saltos que destruye el contenido debe puntuar peor que "no se puede".

~~Aun descontando agresivamente, el margen sobre 152 584 es enorme, y **es puramente algorítmico: no requiere ni un motor más.**~~ **Corregido el 21/08/2026: la frase «aun descontando agresivamente» era una intuición sin número, y los dos descuentos ya están medidos.**

---

## El descuento medido — **MEDIDO el 21/08/2026**

### 1 · La fidelidad del multi-salto (`bench/fidelidad-caminos.md`, 69 caminos ejecutados)

- **Con los motores realmente instalados el multiplicador es 1,93×, no 2,93×** (138 501 → 266 927 pares). Los saltos intermedios interesantes los daban pandoc, calibre, LibreOffice nativo, vips e inkscape, que no están.
- **De los 128 426 pares nuevos, solo 610 (0,48 %) son plausibles**: la ganancia honesta es **+32,7 %, no +193 %**.
- **820 de los 1 599 pares «pedidos» (51 %) tienen PDF como único intermedio.** El multi-salto de esta máquina es, casi entero, *«pásalo por PDF»*.
- **Solo el 31,9 % de los caminos multi-salto ejecutados da una salida aceptable**, frente al 54,5 % de un salto.

### 2 · Cuántas de las aristas declaradas existen (`bench/aristas-nominales.md`)

> **El 50,5 % de las aristas declaradas verificables NO EXISTE**, IC 95 % [48,2 – 53,0], sobre **62 487 aristas (45,1 % de la población)**. Sobre la población entera: **cota inferior 22,8 %, central 48,6 %, superior 77,5 %**. **Es una cota inferior declarada.**

**Método, porque es lo que hace la cifra creíble:** las aristas son cuadráticas (`entradas × salidas`) y las **semiaristas** lineales (`entradas + salidas`). El censo de las **1 104 semiaristas** cuesta **9 min 35 s** y **una semiarista muerta mata de golpe todas las aristas que la usan**: **22 235 aristas (16,05 %) quedan refutadas sin ejecutar ni una de ellas.** El resto se estima con **muestra aleatoria estratificada, n=498**, semilla anotada, con cada salida verificada por `verificador.py`.

**Qué le pasa exactamente a las tablas de este documento:**

| Motor | Declaradas | Vivas al ejecutarlas | **Muertas** |
|---|---:|---:|---:|
| ffmpeg · **salidas** | 202 | 169 | **33 (16,3 %)** — `Encoder not found` o `received no packets` |
| imagemagick · **salidas** | 183 | 179 | **4 (2,2 %)** — `clip`, `jpt`, `mask`, `thumbnail` |
| ffmpeg · **entradas** materializables | 114 | 106 | **8 (7,0 %)** |
| imagemagick · **entradas** materializables | 160 | 134 | **26 (16,2 %)** |

**Y el nivel 0, el cribado por nombre: de los 473 formatos de entrada que este documento atribuye a ffmpeg, el binario no reconoce 17** → **3 385 aristas (2,44 %) muertas solo por nombre**. **Diez de los diecisiete son dispositivos de captura de Linux** (`alsa`, `oss`, `pulse`, `jack`, `sndio`, `video4linux2`, `x11grab`, `kmsgrab`, `fbdev`, `iec61883`): **no son formatos de fichero en absoluto**, y ConvertX los declara como entradas porque copió la salida de `ffmpeg -formats` sin filtrar.

**El 16,2 % de ImageMagick merece leerse entero, porque es la mejor ilustración de la tesis de este documento:** de los 26, **veinte son formatos de píxeles crudos sin cabecera** (`bayer`, `bgr`, `bgra`, `cmyk`, `gray`, `map`, `mono`, `pal`, `rgb`, `rgba`, `uyvy`, `ycbcr`, `yuv`…), todos con el mismo error —`must specify image size`— **sobre ficheros que ImageMagick acaba de escribir él mismo**. La geometría **no está en el fichero**, y ConvertX invoca `magick ENTRADA -auto-orient SALIDA` **sin `-size` porque no tiene dónde guardar ese dato**. **La arista es irrecuperable con esa invocación, y no por un fallo del motor: la información no está.**

### 3 · Pero la tasa NO es uniforme — factor 18, y esto salva el argumento del grafo

| Estrato | Nominal | IC 95 % |
|---|---:|---|
| `ffmpeg` **cruzando** familias | **76,9 %** | [67,3 – 84,4] |
| `ffmpeg` misma familia | 28,8 % | [21,2 – 37,9] |
| `imagemagick` distinta familia | 5,1 % | [1,7 – 13,9] |
| `imagemagick` **misma** familia | **4,2 %** | [2,3 – 7,6] |
| **aristas que tocan PDF** (n=100) | **3,0 %** | **[1,0 – 8,5]** |

**No es que ffmpeg sea peor que ImageMagick: es que el producto cartesiano de ffmpeg cruza modalidades y el de ImageMagick no.** Los `245 × 183` de ImageMagick son casi todos imagen contra imagen, **y ahí la tabla es casi verdad**.

> **Y el estrato prioritario —PDF como intermedio, el que sostiene el multi-salto de este documento— sale al 3,0 %.** **Las aristas que el grafo usa de verdad SÍ existen.** Los dos hechos —el 50,5 % global y el 3,0 % del estrato útil— **hay que citarlos juntos o la cifra engaña.**

### 4 · Los tres ejemplos de la tabla de arriba, reejecutados

- **`epub → png`: NO es una arista muerta, es un fallo de selección de motor.** `epub→pdf` falla con **LibreOffice** (`rc=1` invocando `soffice` directamente en Linux, y HTTP 500 vía Gotenberg) **y funciona con Calibre** (`rc=0`, PDF de 26 817 B, 565 caracteres, centinela y tabla intactos). **Y ConvertX tiene adaptador de Calibre** (`calibre.ts`, 26 entradas / 20 salidas): lo que falla es el bug de despacho de `main.ts:213-229`.
- **`docx → webp`** funciona.
- **`tex → docx`** es inalcanzable en Windows (sin Pandoc ni XeLaTeX) y **alcanzable dentro del contenedor** de ConvertX, que sí los trae.

### 5 · La consecuencia de diseño

> **El nodo del grafo no puede ser el formato y la arista no puede ser el par.** Cuatro medidas independientes lo dicen: `epub→pdf` es real con Calibre y nominal con LibreOffice; `png→ico` es real por ffmpeg y nominal por ImageMagick; `svg→png` es real en el ImageMagick de Windows y nominal en el de Debian; y los crudos sin cabecera son irrecuperables con la invocación de ConvertX y triviales con `-size`.
>
> **La arista mínima viable es `(origen, destino, motor, parametrización, build)`.**

**Y una consecuencia operativa:** **sondear el mapa de capacidades al arrancar, no leer estas tablas.** Cuesta **1 104 sondas y ~11 minutos en frío** para ffmpeg + ImageMagick y **decide el 45 % de la población de aristas**. Con ese censo, el término *«+50 por arista nominal»* que `bench/fidelidad-caminos.md` §5.2 proponía para la función de coste **desaparece**: para las semiaristas ya no hay que adivinar.

**PENDIENTE:** el **54,78 %** de aristas indeterminadas —las que no se pudieron sondear porque no hay forma de fabricar un fichero del formato de origen— exige un corpus de **445 formatos que ningún motor local escribe**. Es lo único que convierte el escenario central (48,6 %) en un número medido.

Aun con todo esto, **el margen sobre 152 584 sigue siendo grande y sigue siendo puramente algorítmico: no requiere ni un motor más.** Lo que ya no se puede decir es *«aun descontando agresivamente»* sin dar el descuento.

---

## 6 · Y el descuento tiene su propia recuperación — **MEDIDO el 21/08/2026, 14:00** (`bench/invocacion-aristas.md`)

El 50,5 % de arriba **se midió entero con la invocación de ConvertX**. La pregunta que quedaba abierta —*cuánto de eso es capacidad y cuánto es la orden*— se cerró reintentando **las 34 + 37 semiaristas muertas y las 118 aristas nominales**, es decir **un censo de los fallos, no una muestra nueva**, con una política de invocación declarada **antes** de medir y **con el mismo juez**, para no medir el juez en vez de la invocación.

> ### **El 18,8 % del 50,5 % es invocación, no capacidad.** IC 95 % [16,8 – 21,3].
> Con los **mismos motores, el mismo build y el mismo corpus**, la tasa nominal baja de **50,5 % a 41,0 %**.

| Categoría | Aristas | % del 50,5 % |
|---|---:|---:|
| **Recuperable con bandera — ganancia automática** | **3 226** | **10,2 %** |
| Recuperable con un parámetro del usuario | 2 704 | 8,6 % |
| **Irrecuperable** | **25 603** | **81,2 %** |

**Qué le pasa exactamente a las cuatro filas de la tabla de §2 de este documento:**

| | Muertas | **Revividas** | |
|---|---:|---:|---:|
| Semiaristas de **entrada** | 34 | **22** | **64,7 %** |
| Semiaristas de **salida** | 37 | **8** | 21,6 % |

**Leer mal es un problema de invocación; escribir lo que el binario no sabe codificar es un problema de build:** de las 33 semiaristas de salida muertas de ffmpeg, **19 son codificadores no compilados** (`ac4`, `dts`, `gsm`, `speex`, `vc1`…) y **2 son muxers de sidecar DASH que no declaran códec por defecto** — es decir, **21 de 33 no son invocación en absoluto**. Y de las 4 de ImageMagick, **tres (`clip`, `mask`, `thumbnail`) no son destinos de conversión sino extractores de propiedad: que ConvertX las declare es un error de catálogo, no una arista rota**.

**Los 20 crudos sin cabecera —el ejemplo estrella del §2 de este documento— reviven 17 de 20, y eso obliga a matizar la frase que este documento escribió:** *«la arista es irrecuperable con esa invocación, y no por un fallo del motor: la información no está»* **es correcta, y ahora se sabe que la información que falta son CUATRO datos, no uno**: geometría, **profundidad**, número de canales y orden de entrelazado. **Este ImageMagick es Q16-HDRI y escribe los crudos a 16 bits por canal**, así que un `.rgb` de 64×48 ocupa **6 bytes por píxel**; **releerlo con `-depth 8` no falla: entrega la geometría exacta pedida y píxeles basura**. *(`ftxt` no revive —RMSE 0,652 contra el original—, `map` exige un fichero de paleta aparte, y `bgro` revienta con `0xC0000005` porque el escritor emite 12 bits por canal, que no es un ancho válido.)*

**Y el sesgo de esa recuperación hay que decirlo: todas las semillas las escribió el propio ImageMagick, así que los 16 bits son SU convenio.** Un `.rgb` de una cámara o de otro programa vendría a 8 bits y **la misma bandera daría basura**. **La tasa de recuperación de los crudos es, por construcción, una cota superior**, y eso hace la categoría «recuperable con un parámetro» **más cara de lo que parece**.

**El otro descuento de este documento —el `imagen → pdf` con página absurda— se recupera entero:** las **6 de 6 degradaciones P7 desaparecen** con densidad explícita. *(Aviso de contabilidad: **no** entra en el 18,8 %, porque una degradación no es una arista nominal — esas aristas ya contaban como reales. Aquí se mide **calidad, no cantidad**.)* **Y `-density 150` no basta: sigue produciendo un A3 y medio (325,1 × 182,9 mm). La variante correcta calcula la densidad para que la imagen quepa en la página objetivo: 210,0 × 118,1 mm, A4 exacto, 7 de 7 ÍNTEGRO.**

### 6.1 · El estrato documental, con censo completo — y coincide con el 3,0 % de §3

| Motor | Aristas | Evaluadas | **Nominales** | Tasa |
|---|---:|---:|---:|---:|
| **ghostscript** | 9 | **9 (censo completo)** | **0** | **0,0 %** |
| **gotenberg-chromium** | 25 | **25 (censo completo)** | **0** | **0,0 %** |
| gotenberg-lo | 102 | 30 | 2 | 6,7 % |
| **Total** | **136** | 64 | **2** | **3,1 %** [0,9 – 10,7] |

> **La superficie documental es la más sólida que se ha medido: 3,1 % nominal frente al 50,5 % global — y COINCIDE con el 3,0 % del estrato PDF de §3, medido con otros motores, otro protocolo y otra muestra. Dos medidas independientes que dan lo mismo.** Es el argumento más fuerte que tiene el grafo de este documento.

Las dos nominales son `epub → pdf` y `dbf → pdf`, ambas con HTTP 500 de LibreOffice. **`epub → pdf` se reproduce por TERCERA vez y por un tercer camino** —falla invocando `soffice` directamente (`rc=1`), falla vía Gotenberg (HTTP 500) y **funciona con Calibre**—, lo que confirma el §4 de este documento. **Y el sesgo entero: 72 de las 102 extensiones de LibreOffice no se pudieron materializar** —son los formatos propietarios heredados que **lee y no escribe** (`123`, `wpd`, `pages`, `key`, `vsd`…)—, así que **ese 3,1 % es también una cota inferior. PENDIENTE.**

### 6.2 · Lo que esto cambia en cómo se cita este documento

1. **La frase «una tabla declarada no es una capacidad» sigue siendo correcta, y ahora tiene sus DOS números: 50,5 % de aristas nominales con la invocación del sector, 41,0 % con una invocación cuidada.** La diferencia entre los dos **es el producto, no el sector**.
2. **Se puede escribir una promesa concreta: 3 226 aristas más que ConvertX con exactamente los mismos motores instalados y sin pedirle nada al usuario.** Y **no se puede prometer** el 81,2 % restante.
3. **La sexta dimensión de la arista queda confirmada desde otro lado:** el `build` decide **19** de las 33 semiaristas de salida muertas de ffmpeg y la `parametrización` otras **8**. **Un catálogo que no lleve las dos miente en cuanto cambias de máquina.**
4. **Y el sondeo al arrancar gana una condición de método: escritor y lector tienen que ser el mismo motor.** `ffmpeg -i x m.rgb` usa el muxer `rawvideo`, que **ignora la extensión y vuelca el `pix_fmt` de la entrada**: el fichero llamado `m.rgb` **no contiene RGB**, y un mapa de capacidades construido así estaría medido contra ficheros que no son lo que dicen ser.
