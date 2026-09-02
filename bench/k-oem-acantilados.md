# B16 + B23 + B24 — el racimo del `k`: un peine, no un acantilado; un `--oem` que no existe; y Ghostscript ya vale

## Estado y condiciones de medida

**MEDIDO: 234 celdas** repartidas en tres pendientes que comparten rejilla
(B16: 26 celdas · B23: 140 · B24: 78 sin contar el control de 10 del raster,
que se cuenta aparte). Todas deterministas, todas con `rc` por celda, ninguna
configuración con el 100 % de sus celdas a CER 100 % (trampa 99). Referencia
`d4_texto.BLOQUES` (610 → 596 acentuados) para B23/B24 sobre la familia `d5`;
la referencia **legada** de 79 caracteres (`LEGADO["cuerpo"]`,
`bench/salidas-k-motor/ocr_eval_d4.py`) para B16 sobre `escaneado_d3`, con
**cuantización real de 1,27 puntos por carácter** — no se publican décimas ahí.

**Evaluador de B16: `ocr_eval_km.py` + `ocr_eval_d4.py`, copiados byte a byte**
de `bench/salidas-k-motor/` (`sha256` idéntico, verificado antes de tocar
nada) — el mismo que produjo los tres anclajes ya citados en `CLAUDE.md`, para
que la rejilla nueva sea comparable con ellos celda a celda. Evaluador de
B23/B24: `bench/scripts/ocr_eval.py`, el mismo que uso en `psm-suelo-ppp.md` y
`cajas-rapidocr.md`.

**Raster:** B16 usa la MISMA receta que `preparar_km.py` (gris, ruta, **sin**
declarar pHYs) — a propósito, para reproducir los anclajes byte a byte;
RapidOCR y PaddleOCR son inmunes al pHYs (trampa 29) así que esto no cambia su
resultado. B23 usa esa misma receta para los tres motores no-Tesseract y la
receta **declarada** (`-units PixelsPerInch -density N`) para Tesseract. B24
usa siempre la declarada.

**GPU:** `filex.gpu.Lock` tomado por configuración; Tesseract no lo toma (CPU).
VRAM libre 8,8–9,1 GiB durante toda la sesión, por encima del guardián de
6 000 MiB. Dos testigos de ruido con tope 20 s en cada tanda; **todas
`limpia`**.

**Riesgo que SÍ se materializó, y lo dice el propio log.** El primer intento
del conductor desprendido de B23 (RapidOCR+R6, PaddleOCR, EasyOCR) murió en el
mismo segundo con `rc=2` en las tres — dos defectos: una ruta de Linux pasada
al `python.exe` de Windows (`D:\mnt\d\...`, la misma trampa que `wslpath -w`
ya documentó) y `USERPROFILE`/`HOME` sin fijar. El master lo diagnosticó,
corrigió (`cd` al worktree + ruta relativa; `WSLENV=` limpio + `USERPROFILE`
fijado) y relanzó; el conductor corregido cerró las tres, 28/28 celdas cada
una, `rc=0`. Se deja escrito como lo que fue: un fallo real de la disciplina
de conductor-desprendido, no un acierto.

**Hallazgo de método, nuevo y con explicación mecánica:** fijar
`USERPROFILE`/`HOME` a un valor de Windows **desde bash de WSL** no basta con
escribir el valor correcto — `HOME` y `USERPROFILE` llevan el flag `/p`
(traducir-como-ruta) en `$WSLENV`, y ese traductor **corrompe un valor que YA
es de Windows** (no es una ruta WSL) convirtiendo `:` → `;` y `\` → `\uf05c`
(un carácter de área de uso privado). `C:\Users\krato` llega al proceso como
`C;\uf05cUsers\uf05ckrato`, y un proceso que resuelve `~` con eso (PaddleX)
crea un directorio real con ese nombre corrupto — es exactamente el origen de
los directorios sueltos `C;\Users\krato` que ya se habían visto en
`bench/salidas-suelo-ppp/` y `bench/salidas-k-motor/` sin diagnosticar. El
arreglo es **`WSLENV=` vacío en la invocación**: sin la traducción, el valor
pasa literal (o, si no se fija nada, el proceso hijo hereda el `USERPROFILE`
nativo de Windows, que ya es el correcto). Se limpió el directorio corrupto
que este mismo agente creó por el mismo motivo antes de diagnosticarlo.

## B16 — no es un acantilado: es un PEINE, y el mecanismo es colapso de detección, no degradación

**MEDIDO, 26 celdas (13 ppp × 2 motores), deterministas.** El pendiente decía
*«acantilado entre ×1,25 y ×1,40»* porque solo había dos puntos. Con trece,
**no hay transición limpia: hay oscilación densa**, con celdas casi perfectas
junto a celdas casi vacías separadas por 2-3 ppp:

### RapidOCR v6 + R6, `escaneado_d3` (79 car. de referencia, paso 1,27 pt)

| factor | ppp | CER | dist/79 |
|---:|---:|---:|---:|
| 1,25 | 125 | 2,53 % | 2 |
| 1,28 | 128 | 73,42 % | 58 |
| 1,30 | 130 | 25,32 % | 20 |
| 1,32 | 132 | 6,33 % | 5 |
| **1,35** | **135** | **0,00 %** | **0** |
| 1,38 | 138 | 75,95 % | 60 |
| 1,40 | 140 | 46,84 % | 37 |

### PaddleOCR v6 medium, `escaneado_d3`

| factor | ppp | CER | dist/79 |
|---:|---:|---:|---:|
| 1,40 | 140 | 3,80 % | 3 |
| 1,44 | 144 | 8,86 % | 7 |
| 1,48 | 148 | 5,06 % | 4 |
| 1,50 | 150 | 31,65 % | 25 |
| 1,52 | 152 | 75,95 % | 60 |
| 1,56 | 156 | 12,66 % | 10 |
| 1,60 | 160 | 75,95 % | 60 |

Los tres anclajes ya publicados se reproducen exactos (×1,25→2,53; ×1,40→
46,84 en RapidOCR; ×1,40→3,80, ×1,60→75,95 en PaddleOCR): la rejilla nueva es
la misma medida, más fina.

**El 75,95 % que se repite EXACTO en `k` no contiguos —1,38/1,52/1,60 en
RapidOCR+R6; 1,52/1,60 en PaddleOCR— es colapso de modo, verificado leyendo el
texto, no adivinado por la cifra:**

```
k1280  DOCUMENTO ESCANEADO R
k1380  DOCUMENTO ESCANEADO
k1520  DOCUMENTO ESCANEADO   (PaddleOCR y RapidOCR+R6, igual)
k1600  DOCUMENTO ESCANEADO   (idem)
```

Las cinco celdas devuelven, **letra por letra**, sólo la primera línea de la
referencia (`"DOCUMENTO ESCANEADO"`, 19 caracteres) y **ninguna de las otras
dos** (`"Texto que solo existe como pixeles."` / `"Debe recuperarse con
OCR."`, 60 caracteres = 75,95 % de 79 exactos). No es una lectura mala: es que
el detector **deja de proponer caja para las dos líneas de cuerpo** en esos
`k`, en dos motores distintos, de forma reproducible. Y al lado, `k1350` lee
las 60 letras del cuerpo **sin un solo error** (0,00 %) — la misma zona que
produce el colapso total tres pasos de rejilla más allá produce la lectura
perfecta. La forma completa, con las siete celdas de RapidOCR+R6 leídas letra
a letra:

```
k1250  DOCUMENTO ESCANEADO Texto que solo existe coma pireles Debe recuperarse con OCR
k1280  DOCUMENTO ESCANEADO R
k1300  DOCUMENTO ESCANEADO Texto que sulo existe como poxales. con OCR
k1320  DOCUMENTO ESCANEADO Texto que sulo existe coma pirales Dabe recuperarse con OCR
k1350  DOCUMENTO ESCANEADO Texto que solo existe como pixeles Debe recuperarse con OCR
k1380  DOCUMENTO ESCANEADO
k1400  DOCUMENTO ESCANEADO Texto que orarse chn OGR
```

**Conclusión: no es un escalón ni una rampa. Es un peine de celdas
alternadamente casi perfectas y con colapso total del cuerpo de la página, con
un período de 2-3 ppp**, del mismo tipo de mecanismo que `bench/cajas-rapidocr.md`
midió para el bloque de 7 pt de `d5c` (recorte inestable en el borde del
reescalado del detector) pero aquí afecta al CUERPO ENTERO de una página con
solo tres líneas, no a una sola línea de un documento con maqueta más rica.
**No se sondearon aquí las cajas de estas 26 celdas** (lo que sí se hizo para
`d5c`/`d5a` en la ronda anterior); queda como el pendiente natural para quien
retome el mecanismo exacto.

## B23 — el `k` por mínimo arrepentimiento, sobre un corpus REDUCIDO y declarado como tal

**MEDIDO, 140 celdas: 5 configuraciones × 4 documentos `d5` (60/72/80/90 ppp
nativos, cuatro geometrías de página distintas, generador compartido con
`d4` para el TEXTO pero no la degradación) × 7 factores (0,75 / 0,875 / 1,00 /
1,125 / 1,25 / 1,40 / 1,60).**

**Verificado antes de escribir, no después (trampa 99):** las 140 celdas
dieron `determinista=true` (3/3 repeticiones idénticas), `err.log` vacío en
las tres tandas GPU, y **ningún fichero de texto por debajo de 3 bytes** en
las 140 — ninguna configuración se acerca a «100 % de sus celdas a CER 100 %».
El *script* de este pendiente no registra un `rc` explícito para los tres
motores GPU (son llamadas en proceso, no subprocesos; una excepción habría
tirado el script entero y se habría visto en el `err.log`) ni para Tesseract
dentro de `b23_k_d5.py` (a diferencia de `b16_acantilados.py` y `b24_tess.py`,
que sí lo hacen) — es una brecha de la disciplina de la trampa 99 en este
fichero concreto, cerrada aquí por inspección directa del tamaño de cada
salida en vez de por un campo `rc`, y queda anotada para quien reutilice este
script.

**Esto NO es el racimo completo que pedía el encargo — se declara así, no se
disimula.** El original (`k-por-motor.md`) midió **9 configuraciones × 4
documentos × 11 factores = 396 celdas**; aquí van **5 configuraciones** (se
quedan fuera Docling defecto, Docling+R6, RapidOCR v6 defecto y RapidOCR v5
defecto — los cuatro motores que el propio informe original ya marcaba como
"no recomendados para producción" o redundantes con RapidOCR+R6) **y 7
factores** (se quedan fuera 0,50, 0,625, 1,80 — los tres extremos que en el
barrido original casi nunca ganaban). Es una rejilla dirigida a las
configuraciones que FileX enviaría, no una repetición completa.

| Configuración | `k` por mínimo arrepentimiento | Arrepentimiento máx. | `k` óptimo por documento (d5a·d5c·d5·d5b) |
|---|---:|---:|---|
| RapidOCR v6 + R6 | **1,00** | 4,8 pt | 1,00 · 1,00 · 1,00 · 1,125 |
| PaddleOCR v6 medium | **1,00** | 0,3 pt | 1,25 · 1,40 · 1,00 · 1,60 |
| EasyOCR | **1,60**¹ | 0,2 pt | 1,25 · 1,60 · 1,60 · 1,60 |
| Tesseract `psm 3`² | **1,40** | 0,7 pt | 1,40 · 1,60 · 1,60 · 1,40 |
| Tesseract `psm 11`² | **1,60**¹ | 0,2 pt | 1,40 · 1,40 · 1,40 · 1,60 |

¹ En el borde de la rejilla: EasyOCR mejora monótonamente hasta 1,60 en 3 de 4
documentos, así que el verdadero óptimo puede estar por encima de lo medido
— **PENDIENTE**, habría que extender la rejilla a 1,80 y más.
² **No comparable en magnitud con el `k` publicado hoy en `CLAUDE.md`
(×0,875 psm 3 / ×0,75 psm 11): ese valor se midió con pHYs SIN declarar**
(el propio `k-por-motor.md` lo advierte en su cabecera), y este con pHYs
DECLARADO. Cambiar la declaración del pHYs cambia el análisis de maquetación
de Tesseract (trampa 8/29), así que **la diferencia de ×1,6 a ×2,1 entre el
valor viejo y el nuevo mezcla dos variables — el corpus Y el pHYs — y no se
puede repartir entre ellas sin medir la celda que falta** (el `k` óptimo con
pHYs SIN declarar sobre la familia `d5`, que no se ha medido aquí).

**Lo que SÍ es comparable, porque los tres motores son inmunes al pHYs:**
RapidOCR v6+R6 pasa de ×1,00 (anclado en el `d4` original, y el propio
informe decía que sobrevivía en 3 de 9) a ×1,00 sobre la familia `d5` —
**coincide**. PaddleOCR pasa de ×1,25 (anclado en `d4`, sobrevivía también) a
×1,00 sobre `d5` — **cerca, no idéntico**. Para estos dos motores, el `k`
publicado hoy **no se refuta**, se **confirma con un segundo corpus
independiente** — la primera vez que el `k` de un motor pHYs-inmune se
verifica fuera del corpus que lo fijó.

**Y el arrepentimiento de RapidOCR+R6 (4,8 puntos) es varias veces el de los
otros cuatro (0,2–0,7): reproduce el mismo peine de B16, ahora sobre la
familia `d5`.** `escaneado_d5a` y `escaneado_d5c` dan **9,1 %** y **18,5 %** a
×1,25 —un pico aislado, rodeado de celdas buenas a ×1,00 y ×1,40 (0,3 % y
0,7-9,4 %)— exactamente la forma de pico que `cajas-rapidocr.md` ya
caracterizó como colapso del reconocedor, no del detector, sobre estos mismos
documentos.

**Esto le añade algo a `k-por-motor.md` que su propia rejilla de 11 factores
no podía ver: el terreno donde se busca el argmin no es liso.** Con puntos
espaciados ×0,125–×0,20 (la rejilla original) un pico aislado de 2-3 puntos de
factor de ancho se puede caer entero entre dos medidas y el argmin publicado
parecer estable cuando en realidad está pegado al borde de un pico — como le
pasa aquí a `escaneado_d5a` en RapidOCR+R6: su óptimo de ×1,00 tiene un pico de
casi 9 puntos justo al lado, a sólo ×0,25 de distancia. Un argmin hallado en
rejilla gruesa no viene con la garantía de que su vecindad sea plana.

**PENDIENTE, declarado y no cubierto aquí:** las 4 configuraciones que
faltan del racimo de 9 (Docling defecto, Docling+R6, RapidOCR v6 defecto,
RapidOCR v5 defecto); la rejilla de factores por encima de 1,60 para EasyOCR y
Tesseract `psm 11`; y separar el efecto del pHYs del efecto del corpus en el
`k` de Tesseract.

## B24 — el `--oem` no existe en la práctica; el `--psm` restante colapsa a 3 clases; Ghostscript ya coincide

### `--oem`: sólo hay DOS valores usables, y son el mismo

**MEDIDO, 32 celdas (4 oem × 2 psm × 4 docs `d5`, ppp nativo).** `oem 0`
(legacy) y `oem 2` (legacy+LSTM) **fallan con `rc=1` en las 16 de 16 celdas**,
siempre con el mismo error:

```
Error: Tesseract (legacy) engine requested, but components are not present
in C:\Program Files\PDFgear\tessdata/spa.traineddata!!
```

El `spa.traineddata` que distribuye PDFgear **no trae datos del motor
legacy** — es LSTM-only, como la mayoría de los `.traineddata` modernos.
`oem 1` (LSTM) y `oem 3` (defecto) dan **CER idéntico, letra por letra, en
las 16 de 16 celdas** (1,2/2,5/10,1/28,7 % con `psm 3`; 1,2/2,0/10,2/25,3 %
con `psm 11` — los mismos números que `psm-suelo-ppp.md` midió al ppp
nativo). **`--oem` no es un parámetro libre para este proyecto: con los datos
de idioma que hay, sólo hay un motor posible**, y `--oem 3` (el que no se
declaraba) ya lo elegía por defecto. **CERRADO, sin trabajo pendiente**: no
hace falta rehacer ninguna tabla de `k` por `--oem`.

### Los ocho `--psm` restantes: tres clases de comportamiento, no ocho

**MEDIDO, 36 celdas (9 psm × 4 docs, ppp nativo, `--oem` por defecto).**

| Clase | `--psm` | Comportamiento |
|---|---|---|
| **Auto-layout** | 1, 4 (y ya medidos: 3) | Idéntico a `psm 3` en las 4×3 celdas — mismo CER exacto |
| **Texto disperso** | 12 (y ya medido: 11) | Idéntico a `psm 11` en las 4×2 celdas |
| **Bloque único** | 6 | Un tercer valor, siempre peor que las dos clases anteriores (5,7/9,7/21,1/36,7 %) |
| **Sin ajuste a la página** | 7, 8, 9, 10, 13 | `rc=0` pero **silencio (0 B) o cuenta atómica (2-3 B)** en las 4×5 = 20 celdas — confirma la trampa 25 sobre un corpus nuevo: modos pensados para una línea o palabra sueltas, alimentados con una página entera |

**Los 11 `--psm` usables de Tesseract se reducen, para un documento de página
completa, a 3 comportamientos reales.** No hace falta una tabla de `k` con 11
filas por documento: con 3 basta, y las otras 8 filas no son ruido, son la
misma trampa 25 confirmada con números nuevos.

### Ghostscript vs ImageMagick, con pHYs declarado en los dos lados: coinciden, 10 de 10

**MEDIDO, 10 celdas (control `escaneado_d4`@200 ppp + 4 documentos `d5` al
nativo, `psm 3` y `psm 11`).** `gswin64c -r<N>` (su forma nativa de declarar
resolución) frente a `magick -units PixelsPerInch -density N`: **píxeles
`md5` idénticos y texto de Tesseract idéntico en las 10 de 10 celdas**,
incluido el control que reproduce el 51,3 %/40,6 % ya publicado para `d4`.

**Esto cierra el pendiente sin rehacer nada: la tabla de `k` de Tesseract NO
necesita reconstruirse con Ghostscript.** Ya es válida para el contenedor,
**con la única condición que ya se venía cumpliendo**: declarar el pHYs
verdadero. Es la primera vez que esta equivalencia se comprueba sobre la
familia `d5` — antes sólo estaba medida sobre `d4`/`d3`/`d4c`.

## Manifiesto

Los 85 rásteres PNG (16 MB) se borraron; `bench/salidas-k-oem-acantilados/MANIFIESTO.md`
trae nombre, tamaño, `sha256` y la orden exacta que los reproduce.
