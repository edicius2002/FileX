# El hito 6: un criterio que se puede verificar, y el sidecar que lo verifica

**Agente S6 · 2026-08-28 · hito 6 (sidecar de IA) y N23**
Salidas y arneses: `bench/salidas-hito6/` · Código: `filex/sidecar.py`,
`pruebas/test_hito6.py` · Informe: este fichero.

---

## 0. Lo que hay que llevarse

*(las cifras y las tablas, en las secciones que se citan)*

1. **MEDIDO — «dos modelos residentes» no es realizable en un proceso, y no por
   memoria: por las DLL.** Cargar `faster-whisper` y después RapidOCR en el
   mismo proceso mata el proceso en **10 de 10** corridas, con
   `Could not load symbol cudnnGetLibConfig. Error code 127` y
   `rc=0xC0000409`. **Invirtiendo el orden de importación, 0 de 10.** El
   mecanismo, sondeado y no deducido: en `.venv-ai` hay **dos `cudnn64_9.dll`
   distintas** —la de `ctranslate2` (266 288 B) y la de `torch\lib` (438 840 B,
   la única que trae los ocho sub-módulos)—, **las dos acaban cargadas a la vez**
   y lo que decide es **cuál se cargó primero**, porque Windows resuelve la
   petición sin ruta por nombre base (§2.2, donde también se cuenta que mi
   primera hipótesis era falsa y que la sonda estuvo rota dos intentos).
2. **MEDIDO — y esto CIERRA el pendiente que `ocr-produccion-sidecar.md` §9
   declaró como «lo que de verdad falta para cerrar el hito 6»: la suma no es
   exacta, pero se equivoca del lado bueno.** Con el factorial completo en **una
   sola tanda** (6 fases alternadas, n=9 cada una), audio + OCR + NVENC medidos
   por separado suman **3 784 MiB** y medidos a la vez, en dos procesos, dan
   **3 739**: **−45 MiB, el 1,2 %**, con el signo replicado en una segunda tanda
   (−9). **Sumar cifras medidas por separado es CONSERVADOR**, que es lo que
   hace falta de un presupuesto (§3.1).
3. **MEDIDO — la arquitectura robusta cuesta +106 MiB (×1,029).** Los dos
   modelos en un proceso (con el orden bueno) gastan **3 633 MiB**; en dos
   procesos, **3 739**. Menos del 3 % a cambio de quitar de en medio un fallo
   determinista que no lanza excepción (§3.2).
4. **El criterio nuevo está en §4, y su diferencia con la reescritura propuesta
   por G5 no es el número: es que nombra la TOPOLOGÍA DE PROCESOS.** La
   propuesta de §6.3 de aquel informe presuponía que los dos modelos podían
   convivir, que es justo lo que aquí resulta falso en un proceso. Se conservan
   sus tres condiciones y se le añaden dos.
5. **MEDIDO — el perfil de referencia CUMPLE, y ahora se sabe de punta a punta y
   no sumando informes:** *(escritorio + `distil-large-v3` + RapidOCR
   PP-OCRv6 small + NVENC 4K, documentos de hasta 8,882 Mpx)*. Coste propio
   medido **3 739 MiB**; con la base de escritorio documentada en su peor caso
   (3 448) da **7 187 MiB = 7,02 GB ≤ 8,7** (§3.4). Y el tope de RapidOCR se
   **reproduce con 7 MiB de diferencia** sobre los 1 526 publicados, otro día y
   con otro arnés, sobre los mismos `sha256` de píxeles (§3.3).
6. **Entregado `filex/sidecar.py`** (stdlib, cero dependencias nuevas): registro
   con **TTL** y **LRU por VRAM**, admisión por la recta `min(ordenada +
   pendiente × Mpx, tope)` evaluada **antes de cada página**, reciclado por
   muerte y relanzamiento del trabajador, lote en **orden descendente** y un
   proceso trabajador por `(motor, dispositivo)`. **52 pruebas nuevas**, 51 de
   ellas sin tocar la tarjeta (§5).
7. **MEDIDO — un `stderr` en `PIPE` que nadie lee cuelga al trabajador, y con
   control positivo:** sin drenar, el arranque **no termina** (12,01 s hasta el
   tope); drenando, **0,06 s**. Es un modo de fallo que solo aparece con
   procesos de vida larga, y por eso ningún informe anterior lo había visto
   (§8.2).
8. **REFUTADO a medias un número heredado, y en el lado malo:** la recta de
   RapidOCR de §5.1 **subestima 339 MiB** en el tramo de en medio (pide 1 117 a
   4,352 Mpx donde su propio informe midió 1 456). El margen de 500 MiB lo tapa
   por 161. No invalida nada publicado; sí obliga a no bajar el margen (§8.3).
9. **N23 hecho:** `bench/scripts/ocr_motor.py` ya lleva **los dos testigos de
   ruido con tope propio** y la resolución del reloj declarada (§7).
10. **MEDIDO y contra lo que yo esperaba — el ORDEN del lote es una variable del
    MOTOR, igual que el `k`.** Sobre EasyOCR el descendente gana 5 350 MiB
    (medido por G5); sobre RapidOCR, que tiene tope propio, **pierde 77**, con el
    signo conservado en **5 de 5** repeticiones y por encima del ruido. No
    refuta la trampa 67: la matiza, y ahora el orden se fija por **mínimo
    arrepentimiento con el arrepentimiento publicado** (§6, V2).
11. **MEDIDO — la DURACIÓN del audio mueve la VRAM, y eso obliga a un sexto
    componente en el perfil.** `large-v3` pide **3 479 MiB** con 11 s de audio y
    **4 533** con 308: **+1 054, ×1,30**, con un recorrido de **2 MiB** entre
    repeticiones. Es la trampa 68 en el modelo de audio: **un presupuesto sin la
    duración dentro tiene el mismo defecto que uno de OCR sin los megapíxeles**,
    y ninguna versión del criterio —ni la vieja ni la reescritura propuesta— lo
    nombraba (§4.2 cláusula C, §6 V7).
12. **Un fallo del proceso de medición, declarado:** edité `filex/sidecar.py`
    con una tanda corriendo y **partí la tanda en dos poblaciones**. Una corrida
    murió con `AttributeError` —eso fue la suerte— y cuatro anteriores midieron
    otra versión del código. La tanda entera se tiró y se repitió (§8.1).

**PENDIENTE, y se dice al principio:** todo lo de VRAM sale de **un** documento
base reescalado, **una** tarjeta y **una** versión de cada motor; el modelo de
audio se ha medido con `distil-large-v3` y `large-v3` pero **no** con Docling,
que el hito nombra explícitamente; y la cláusula de precisión se verifica sobre
los tres documentos que ya la cumplían — `d3` y `escaneado_d4` **siguen sin
cerrarse y no se prometen**.

---

## 1. Cómo se midió

### 1.1 El lock de GPU, tomado **desde Python**

`CLAUDE.md` §1 deja escrito que **0 de 15 arneses `.py` toman el lock** y que eso
sigue PENDIENTE. Las tandas de este informe lo toman, con `filex/gpu.py` —que
implementa el protocolo de `bench/lib/harness.sh`, `O_CREAT|O_EXCL` sobre
`%TEMP%/filex-gpu.lock`— y por tanto **excluyen también a los 51 ficheros de
`bench/` que usan el arnés de shell**. No se usa `filex/cerrojo.py`: su exclusión
contra el shell es asimétrica y desde el lado del `.py` parece funcionar
(trampa 77).

Se toma **una vez por tanda**, no una por corrida: tomarlo y soltarlo 60 veces
deja 59 ventanas por las que se cuela otro. Y la **guardia** (`GPU_GUARD`,
aborto por debajo de 6 000 MiB libres) se evalúa **antes de cada corrida**,
porque el lock solo excluye a quien lo toma. Lanzador:
`bench/salidas-hito6/run_h6.py`.

### 1.2 Los dos testigos, con tope propio

Cada corrida mide **deriva** (bucle monohilo, antes y después) y **nivel**
(lanzamiento de `ffprobe -version`), con **tope de 20 s en el propio testigo**
—devolviendo el tope y marcando `SUCIA`—. El veredicto va dentro del `.json` de
cada corrida con los cuatro números, no solo la etiqueta: con la sesión de
escritorio remoto activa **todo sale SUCIA** de forma estructural y la etiqueta
sola no informa. `bench/salidas-hito6/testigos.py`, y la misma lógica en
`bench/scripts/ocr_motor.py` (§7).

### 1.3 El instrumento, antes de medir con él

- **El reloj:** `time.perf_counter`, resolución **1e-07 s** leída con
  `get_clock_info` y guardada en cada `.json` (trampa 62).
- **La VRAM:** `nvidia-smi --query-gpu=memory.used`, **total, nunca por PID**
  (trampa 31), muestreada por un hilo a **250 ms** durante toda la corrida — el
  pico ocurre **durante** la inferencia y una lectura al terminar no lo ve. El
  ruido de este instrumento está medido por G5 en **±43 MiB**, y ninguna
  diferencia por debajo de eso se interpreta aquí.
- **La base:** todas las cifras de VRAM son `delta` sobre la base del **propio
  proceso**. La base de escritorio de estas tandas fue de **1 626–1 656 MiB**,
  no los 3 292–3 448 documentados; por eso el coste propio es comparable entre
  fases y **el margen absoluto se calcula aparte**, con la base documentada en
  su peor caso.

### 1.4 Las dos variables que el corpus esconde, fijadas y declaradas

- **Dispositivo** (trampa 11): `cuda` en todas las celdas de este informe, y va
  en el nombre de cada corrida y en cada resultado del sidecar.
- **Vía de entrada** (trampa 30): **`ruta`** en todas, y también en cada
  resultado. Un sidecar que decodificara una vez y repartiera el array tendría
  que entregar BGR de tres canales y **no puede dar por hecho que equivale a
  pasar la ruta**; esa vía no se ha medido aquí y queda en §9.

### 1.5 Los píxeles, comprobados contra los de quien midió antes

`bench/salidas-hito6/preparar_h6.py` rasteriza con **Ghostscript** (ImageMagick
delega en él, trampa 8) la misma rejilla que usó G5 y **compara los `sha256` con
los que aquel informe publicó**: **5 de 5 coinciden**. La parte de VRAM de este
informe corre sobre exactamente los mismos píxeles que la suya, y eso no se
supone: se comprueba. No se declara `pHYs` porque los motores de este informe
son inmunes a él (trampa 29) y la omisión es deliberada.

### 1.6 La métrica de CER, declarada

`bench/scripts/ocr_eval.py`, **importado y no reimplementado**, con la métrica
canónica **`acentos`**. Cada celda lleva la clave `metrica` (trampa 55). La
referencia de los tres documentos de la cláusula de precisión tiene **79
caracteres**, así que cuantiza a **1,27 puntos por carácter** (trampa 9) — da
igual para un criterio de *distancia de edición 0*, que es un entero, pero
importaría para cualquier gradiente.

---

## 2. «Dos modelos residentes» muere en 10 de 10, y el orden de importación decide

### 2.1 El fallo — MEDIDO, determinista

La primera tanda (A) medía cinco fases, y una de ellas era la del criterio:
**los dos modelos en el mismo proceso**, `faster-whisper` primero y RapidOCR
después, que es el orden natural (el sidecar carga el audio y luego le piden un
OCR).

| fase | corridas | `rc` | qué pasó |
|---|---:|---|---|
| `base` | 10 | 0 | control: proceso vacío |
| `solo_audio` | 10 | 0 | `distil-large-v3`, carga + transcripción |
| `solo_ocr` | 10 | 0 | RapidOCR PP-OCRv6 small + R6, folio de 8,88 Mpx |
| `solo_nvenc` | 10 | 0 | `hevc_nvenc`, 20 s de 4K |
| **`coresidente`** | **10** | **`0xC0000409`** | **muere antes de cargar el OCR** |

**10 de 10**, con el mismo código de salida y el mismo mensaje:

```
Could not load symbol cudnnGetLibConfig. Error code 127
```

`0xC0000409` es `STATUS_STACK_BUFFER_OVERRUN`, que en la práctica es el
`__fastfail` con el que el CRT aborta sin excepción; y `127` es
`ERROR_PROC_NOT_FOUND`. **No hay excepción de Python que capturar**: el proceso
desaparece. Es la trampa 25 en su forma más peligrosa —un proceso que **no
llegó a arrancar** frente a uno que midió cero—, y lo único que las separa es
haber registrado el `rc` de cada celda, que es lo que el arnés hace.

### 2.2 El mecanismo, sondeado en ejecución

La explicación cómoda —*«se estorban por VRAM»*— es falsa: el proceso muere
**antes** de reservar nada, y la fase `solo_ocr` sola consume 1 529 MiB sobre
una tarjeta con más de 8 000 libres. Sondeando el venv en vez de deducirlo:

| fichero | bytes | `sha256` (12) |
|---|---:|---|
| `ctranslate2\cudnn64_9.dll` | 266 288 | `9edbcdff73b0` |
| `torch\lib\cudnn64_9.dll` | 438 840 | `c07cc47f2fa4` |

**Hay dos `cudnn64_9.dll` distintas en el mismo entorno virtual**, y ninguna de
las dos es un fichero cualquiera: cuDNN 9 está **partida**, `cudnn64_9.dll` es
un despachador que carga `cudnn_graph64_9.dll`, `cudnn_ops64_9.dll`,
`cudnn_engines_*.dll`… **`torch\lib` trae los ocho módulos; `ctranslate2` trae
solo el despachador.** *(Y ninguna de las dos exporta `cudnnGetLibConfig` por sí
misma: el símbolo vive en los sub-módulos, que es justo lo que a `ctranslate2`
le falta.)*

**Y aquí mi primera hipótesis resultó falsa, medida contra mi propia sonda.**
Yo escribí que *«la segunda no llega a cargarse»*. Sondeando los módulos vivos
del proceso (`EnumProcessModules`) en los dos órdenes:

| momento | módulos totales | `cudnn*.dll` cargadas |
|---|---:|---|
| proceso vacío | 32 | ninguna |
| **orden bueno**, tras construir RapidOCR | 139 | las **8 de `torch\lib`** |
| **orden bueno**, tras construir además Whisper | 230 | las 8 **+ la de `ctranslate2`** |
| **orden malo**, tras construir Whisper | 203 | la de `ctranslate2` **+ las 8 de `torch\lib`** |

**Las dos conviven en memoria en los dos órdenes.** Lo que cambia no es qué se
carga, sino **cuál se cargó primero**: Windows resuelve una petición de
`cudnn64_9.dll` **sin ruta** devolviendo la que ya está cargada con ese nombre
base. En el orden malo, la primera es la de `ctranslate2`, y el cliente que
llega después —`onnxruntime`— recibe un despachador sin sub-módulos y su
`GetProcAddress` de `cudnnGetLibConfig` devuelve `ERROR_PROC_NOT_FOUND`.

> **Y esto no es «una incompatibilidad conocida» que se pueda leer en la
> documentación de nadie: es una propiedad de ESTE venv.** Otro entorno con una
> sola cuDNN no la tendría. Por eso el criterio del hito no puede decir *«dos
> modelos residentes»* sin decir **en cuántos procesos**.

**Y la sonda estuvo rota dos intentos, con el fallo perfecto:** sin declarar los
`argtypes`, `EnumProcessModules` recibía punteros truncados a 32 bits, fallaba,
y la sonda devolvía **una lista vacía en los dos órdenes** — que se lee como
*«no hay ninguna cuDNN cargada»* y es una conclusión. **Lo destapó el control
positivo**: contar también los módulos **totales**, que salían 0. Es la trampa 66
otra vez —*«si una sonda devuelve el mismo valor para dos configuraciones que
sabes que son distintas, la sonda está rota»*—, y la comprobación costó una
línea.

### 2.3 Las dos salidas, y por qué el criterio elige la segunda

| vía | ¿arranca? | coste propio | fragilidad |
|---|---|---:|---|
| `coresidente` — audio y luego OCR, 1 proceso | **no**, 0 de 10 | — | — |
| `coresidente_inv` — OCR y luego audio, 1 proceso | **sí**, 10 de 10 | menor | **depende del orden de un `import`** |
| `dos_procesos` — el OCR en un trabajador | **sí**, 10 de 10 | +98 MiB | ninguna de este tipo |

La vía del medio funciona y es **más barata** (§3.2), y aun así el criterio
elige la tercera: *una disciplina que hay que recordar en cada punto de
invocación no es una defensa*, y «acuérdate de importar RapidOCR antes que
faster-whisper» es exactamente eso. Un `import` movido de sitio por cualquier
refactor —o una biblioteca nueva que traiga una tercera cuDNN— tumba el sidecar
entero **sin una sola excepción que capturar**.

---

## 3. ¿Es aditiva la suma del presupuesto? — el pendiente que cerraba el hito

`ocr-produccion-sidecar.md` §9 lo dejó escrito con todas las letras:

> *«Ni una sola medida con dos modelos residentes a la vez. El presupuesto de
> §6.1 SUMA cifras de informes distintos, y la suma es una hipótesis: los
> asignadores podrían compartir o estorbarse. **PENDIENTE, y es lo que de verdad
> falta para cerrar el hito 6**.»*

### 3.1 El factorial, entero y en UNA sola tanda — MEDIDO

Las seis fases alternadas, 10 corridas cada una, **un proceso por corrida**, la
primera de cada fase descartada (trampa 7). Medir las partes en una tanda y el
todo en otra sería exactamente lo que la trampa 59 prohíbe.

| fase | n | base med. | **propio med.** | min | max | recorrido |
|---|---:|---:|---:|---:|---:|---:|
| `base` (control) | 9 | 1 582 | **0** | 0 | 41 | 41 |
| `solo_nvenc` | 9 | 1 583 | **500** | 418 | 502 | 84 |
| `solo_ocr` @8,882 Mpx | 9 | 1 582 | **1 533** | 1 528 | 1 570 | 42 |
| `solo_audio` `distil-large-v3` | 9 | 1 583 | **1 751** | 1 718 | 1 761 | 43 |
| **suma de las tres partes** | | | **3 784** | | | |
| `coresidente_inv` (1 proceso) | 9 | 1 582 | **3 633** | 3 610 | 3 679 | 69 |
| `dos_procesos` (el del sidecar) | 9 | 1 596 | **3 739** | 3 706 | 3 862 | 156 |

**La respuesta:**

| topología | medido | suma | diferencia | ratio | ¿supera el ruido (±43)? |
|---|---:|---:|---:|---:|---|
| dos procesos | 3 739 | 3 784 | **−45** | ×0,988 | **por 2 MiB** |
| un proceso | 3 633 | 3 784 | **−151** | ×0,960 | sí |

Y la réplica que exige la trampa 36 —*«si solo puedes medir por diferencia,
repite la tanda y mira si el signo se conserva»*—, en otra tanda independiente:
**−9** y **−107**, mismo signo las dos.

> **MEDIDO — la suma NO es exacta, pero se equivoca del lado bueno.** En la
> arquitectura de dos procesos, sumar las partes **sobreestima entre el 0,2 % y
> el 1,2 %**; en un proceso, entre el 2,9 % y el 4,0 %. **Un presupuesto que
> suma cifras medidas por separado es, por tanto, CONSERVADOR**, que es lo que
> hace falta de un presupuesto. Lo que era una hipótesis ya es un número, y el
> número es pequeño.

### 3.2 El precio de la arquitectura robusta

| | tanda F | tanda E |
|---|---:|---:|
| un proceso (`coresidente_inv`) | 3 633 | 3 642 |
| dos procesos | 3 739 | 3 740 |
| **precio** | **+106 (×1,029)** | **+98 (×1,027)** |

**Menos del 3 %**, y a cambio se quita de en medio un fallo determinista que no
lanza excepción (§2). El coste en tiempo también se mide: la fase de dos
procesos tarda **13,95 s** de mediana contra **11,54** — y de esa diferencia, la
mayor parte es el arranque del trabajador, que en un sidecar de vida larga se
paga **una vez**, no por página.

### 3.3 Contra las cifras publicadas, componente a componente

| componente | publicado (§6.1 de G5) | **medido aquí** | diferencia |
|---|---:|---:|---:|
| `distil-large-v3` | 1 847 | **1 751** | −96 |
| RapidOCR PP-OCRv6 small @8,882 Mpx | 1 526 | **1 533** | **+7** |
| NVENC 4K | 743 | **500** | −243 |
| **suma** | **4 116** | **3 784** | −332 |
| los tres a la vez, dos procesos | — | **3 739** | |

**El tope de RapidOCR se reproduce con 7 MiB de diferencia sobre 1 526**, en otra
tanda, otro día y con otro arnés: es la confirmación más fuerte de este informe,
y vale porque los píxeles son **los mismos `sha256`** (§1.5).

**Salvedad obligatoria en la fila de NVENC (trampa 79):** mi medida sale de
`ffmpeg -t 20 -i fuente_4k.mp4 -map 0 -c:v hevc_nvenc -b:v 8M -c:a copy -f null NUL`,
y el 743 publicado sale de otro arnés con otra orden. **No son la misma medida
y no se restan como si lo fueran**; se ponen al lado con las dos órdenes a la
vista, y el presupuesto usa la mía porque es la que corresponde al perfil que se
declara.

### 3.4 El presupuesto absoluto

Las cifras de arriba son `delta` sobre la base del propio proceso, y la base de
escritorio de estas tandas fue baja (1 582-1 596 MiB). El presupuesto se calcula
con la base **documentada en su peor caso**, que es lo que exige un presupuesto:

```
  3 448  escritorio (peor caso documentado, CLAUDE.md §2)
+ 3 739  distil-large-v3 + RapidOCR/PP-OCRv6 small + NVENC 4K, MEDIDOS A LA VEZ
         con documentos de hasta 8,882 Mpx
-------
  7 187  MiB = 7,02 GB   ≤  8 909 MiB (los «~8,7 GB» del criterio)   CUMPLE
```

Y con la suma conservadora de las cifras publicadas habría dado **7 564**, que
también cumple: **el veredicto no cambia, pero ahora está medido y no supuesto.**

---

## 4. El criterio nuevo del hito 6

### 4.1 Qué le pasa a la reescritura que se me dio

`ocr-produccion-sidecar.md` §6.3 propone tres condiciones, y **las tres son
buenas**: el techo por motor con su recta, el perfil declarado entero con el
mayor documento admitido, y el reciclado obligatorio con su coste. Lo que le
falta es lo que §2 destapa:

- **su condición 2 presupone que los dos modelos pueden convivir**, y en un
  proceso **no pueden** con el orden natural de carga;
- **y su suma seguía siendo una hipótesis**, declarada como tal en su propio §9.

O sea: la reescritura no se refuta, **se completa**. Se le añaden dos
condiciones —una de topología y una de verificación— y se le pone dentro el
número que la hacía verificable.

### 4.2 El criterio, redactado

> ## Aceptación del hito 6 — sidecar de IA
>
> El sidecar es un proceso Python persistente con un registro de modelos
> residentes con **TTL** y **LRU por VRAM**.
>
> **A · Topología de procesos.** Cada motor de OCR vive en su **propio proceso
> trabajador**; ningún proceso carga a la vez un modelo de audio y un motor de
> OCR. *(MEDIDO: en el mismo proceso y con el orden natural de carga, muere en
> 10 de 10 con `rc=0xC0000409` y sin excepción capturable — §2. El precio de la
> separación es **+106 MiB, ×1,029** — §3.2.)*
>
> **B · Admisión, con el tamaño de la entrada dentro.** Antes de **cada página**
> se evalúa `coste = min(ordenada + pendiente × Mpx, tope)` del motor, más
> **500 MiB de margen**, contra la **VRAM libre total**. Si no cabe: **reciclar**
> (matar y relanzar el trabajador); si tras reciclar sigue sin caber:
> **rechazar**, con el motivo y las cifras dentro. Tamaños máximos admitidos con
> los 6 000 MiB libres que exige el `GPU_GUARD`:
>
> | motor | Mpx admisibles | ¿entra un A4 a 300 ppp (8,70 Mpx)? |
> |---|---|---|
> | RapidOCR ONNX PP-OCRv6 small | **sin límite** (tope propio 1 526 MiB) | **sí** |
> | PaddleOCR | 7,37 | **no** |
> | EasyOCR | 4,50 | **no** |
>
> **Un motor sin recta de VRAM medida no entra en el sidecar**, y uno sin tope
> propio entra **con** su política de reciclado o no entra.
>
> **C · Presupuesto del perfil, declarado entero y medido a la vez.** El perfil
> se declara con sus **seis** componentes —escritorio, modelo de audio, motor de
> OCR, NVENC, **el mayor documento admitido** y **la mayor duración de audio
> admitida**— y su total se **mide con todos los componentes vivos**, no sumando
> informes.
>
> *(El sexto componente sale de una medida de este informe y no estaba en
> ninguna versión anterior del criterio: **la duración del audio mueve la VRAM**.
> `large-v3` pide **3 479 MiB** con 11 s de audio y **4 533** con 308 —
> **+1 054, ×1,30**, con un recorrido de 2 MiB entre repeticiones—. Un
> presupuesto de audio sin la duración dentro tiene el mismo defecto que uno de
> OCR sin los megapíxeles: es la trampa 68 en el otro modelo.)*
>
> | perfil | total | veredicto |
> |---|---:|---|
> | escritorio + `distil-large-v3` + RapidOCR/v6 small + NVENC 4K, ≤ 8,882 Mpx, audio de 11 s | **7 187 MiB (7,02 GB)** | **cumple** |
> | lo mismo con `large-v3` y audio de 11 s | 8 917 MiB (8,71 GB) | **no cumple, por 8 MiB** |
> | lo mismo con `large-v3` y audio de 308 s | 9 531 MiB (9,31 GB) | **no cumple** |
>
> **D · Descarga por inactividad, demostrada en la tarjeta.** El TTL no vacía un
> diccionario: **devuelve la VRAM**, y se comprueba leyendo la tarjeta antes y
> después. *(MEDIDO: retenidos 1 493 MiB, devueltos 1 552 — §6, V1.)*
>
> **E · Reciclado con su coste publicado.** Matar y relanzar, porque esperar no
> devuelve un solo MiB. *(MEDIDO de punta a punta, con el protocolo del
> trabajador dentro: **5,84 s** para RapidOCR — §6, V4.)*
>
> **F · Precisión, con su métrica declarada.** Distancia de edición **0** en
> `patologico_escaneado`, `escaneado_d1` y `escaneado_d2`, **a sus ppp nativos**
> (200 / 150 / 100), con la configuración de producción, dispositivo fijado y
> vía de entrada `ruta`. Métrica **`acentos`** (`bench/scripts/ocr_eval.py`).
> **`escaneado_d3` y `escaneado_d4` quedan FUERA del criterio**: ningún motor
> baja del 18,60 % en `d4`, y ese margen sigue abierto — el hito no lo cierra y
> no lo promete.

### 4.3 Las cuatro cosas que este criterio hace y el anterior no

1. **Nombra el tamaño máximo de entrada** (trampa 68). *«El pico no supera
   ~8,7 GB»* lo cumple o no la misma implementación según qué PDF le entre; con
   `mpx_max` dentro, es una afirmación que se puede comprobar.
2. **Nombra la topología de procesos.** *«Dos modelos residentes»* no dice en
   cuántos procesos, y aquí esa es la diferencia entre funcionar y morir.
3. **Separa medir de sumar.** La cláusula C exige que el total se mida con todo
   vivo. Sumar sigue valiendo como cota —y es conservadora, §3.1— pero ya no
   como verificación.
4. **Dice qué NO cubre.** `d3` y `d4` fuera, por escrito, en el propio criterio.
   Un criterio que promete lo que nadie ha conseguido no se puede cerrar nunca.

---

## 5. El sidecar — `filex/sidecar.py`

**Stdlib pura, cero dependencias nuevas.** `filex` no tiene dependencias por
decisión escrita en `pyproject.toml`, así que aquí no se importa ni `torch` ni
`rapidocr`: **los motores viven en procesos trabajadores**, uno por
`(motor, dispositivo)`, cada uno bajo el intérprete de su propio venv. Es la
misma arquitectura que la vía `dos_procesos` de §2.3, y la mide §3.

### 5.1 Las piezas

| pieza | qué hace | de dónde sale el número |
|---|---|---|
| `Motor` | `coste_previsto(mpx) = min(ordenada + pendiente × Mpx, tope)` | `ocr-produccion-sidecar.md` §5.1 |
| `Motor.mpx_admisibles` | **el tamaño máximo de entrada** con N MiB libres | ídem |
| `Perfil` | el presupuesto de una configuración **entera**, con `mpx_max` dentro | §4, cláusula C |
| `decidir` | `admitir` / `reciclar` / `rechazar`, con los números en el veredicto | §5.1 de aquel informe |
| `orden_descendente` | el lote, el mayor primero | refutación de §3.4 de aquel informe |
| `megapixeles` | geometría de PNG/JPEG **leyendo la cabecera, en proceso** | regla de diseño |
| `Trabajador` | el proceso con el modelo dentro; recicla **matando y relanzando** | §4.1 de aquel informe |
| `Registro` | residentes con **TTL** y **LRU por VRAM** | criterio del hito |

### 5.2 Seis decisiones que no son obvias, y por qué

1. **La admisión se evalúa antes de cada página, no cada N páginas.** Un
   contador de páginas no predice nada: 20 páginas de 1,25 Mpx mueven 39-42 MiB
   y **una** de 4,35 mueve 3 209. Una página rechazada **ni siquiera provoca la
   carga del modelo** (prueba
   `test_rechaza_la_pagina_que_no_cabe_y_no_arranca_nada`).
2. **`reciclar` y `rechazar` se distinguen por lo que el proceso RETIENE.**
   `Registro.admitir` calcula lo retenido como `coste_previsto(mpx_max_visto)`
   del trabajador vivo, que es lo único que reciclar puede recuperar. Si ni con
   eso cabe, se rechaza con motivo: *«reciclar dos veces seguidas no ayuda»*.
3. **`vram_libre()` puede devolver `None`, y `None` no es cero.** Sin lectura de
   la tarjeta se **admite**: confundir «no hay GPU» con «la GPU está llena»
   convierte una máquina sin tarjeta en una máquina bloqueada. En `cpu` tampoco
   se presupuesta, y el dispositivo va **en la clave del registro**, porque CPU
   y GPU no dan la misma salida (trampa 11).
4. **Un motor sin recta medida no entra.** `admitir` lanza `KeyError` con el
   motivo escrito. *«Una constante global hace que cada motor nuevo herede en
   silencio los ppp que le convenían a otro»* — aquí sería la VRAM.
5. **`stdin` como canal es una excepción DECLARADA a `stdin=DEVNULL`.** La regla
   protege contra un motor de terceros que espera entrada; el trabajador **es
   este mismo fichero**. Todo lo demás se cumple: sin shell, argv en array,
   `stderr` capturado y **nunca devuelto crudo**, y tope en cada petición.
6. **Cada trabajador vive en un directorio desechable propio** (R18), censado al
   arrancar y al cerrar, y borrado entero. Medido: **0 sobrantes** en las 10
   corridas de `dos_procesos` y en las de la verificación.

### 5.3 Lo que las pruebas comprueban sin tocar la tarjeta

`pruebas/test_hito6.py`, **52 pruebas**, de las que **51 no usan GPU** y **5
tampoco cargan ningún modelo pero sí lanzan procesos de verdad** (con un motor
de mentira). Que una regla de recurso solo se pueda ejercitar con la tarjeta
delante es no tener prueba: **nadie va a llenar 12 GiB de VRAM de verdad para
comprobar que el rechazo funciona**, así que la VRAM y el reloj son inyectables.

Tres que merecen mención:

- `test_arranca_pese_a_4000_lineas_de_stderr` — el modo de fallo de §8.2, con su
  control positivo medido aparte.
- `test_una_linea_ajena_al_protocolo_no_mata_al_trabajador` — PaddleOCR imprime
  por su cuenta en `stdout`; una línea suya cerraría el trabajador con «murió
  sin responder», que es un **diagnóstico falso**.
- `test_la_recta_de_rapidocr_subestima_en_el_tramo_de_en_medio` — §8.3. Una
  prueba que documenta un residuo heredado, para que no lo descubra producción.

Y las de forma van **sobre el AST** (trampa 42), con la comprobación de que la
fuente compila antes de comparar nada (trampa 60): sin shell, sin dependencias
nuevas al nivel de módulo, ninguna espera de subproceso sin tope, y el `stderr`
del motor devuelto como **tipo** de excepción y no como texto.

---

## 6. La verificación, cláusula por cláusula

`bench/salidas-hito6/verificar_criterio.py`, con el lock tomado y el sidecar de
verdad. Salida cruda en `json/verificacion.json`; ruido de la tanda: `limpia`.

### V1 · Cláusula D — el TTL devuelve la VRAM — **MEDIDO**

| momento | VRAM usada (MiB) |
|---|---:|
| antes de cargar nada | 1 709 |
| con el trabajador vivo, tras un folio de 8,882 Mpx | 3 202 |
| 4 s después (TTL de 3 s) y con el proceso ya muerto | **1 650** |

**Retenido 1 493 MiB; devuelto 1 552.** *(Devuelve 59 más de lo que retuvo
porque la base de la tarjeta se movió entre las dos lecturas: está dentro del
±43 del instrumento más la deriva del escritorio. Lo que importa es que **no
queda nada**.)* Y el contraste que da sentido a la cláusula: **esperar sin matar
el proceso no devuelve un solo MiB** — eso lo midió G5 con cinco lecturas
idénticas separadas por 80 s.

### V2 · La cláusula que NO salió como se esperaba — el orden del lote

Con n=1, el orden **ascendente** salió más barato que el descendente, que es lo
contrario de lo que G5 refutó con EasyOCR. Con n=1 eso no es una medida, así que
se repitió con **5 repeticiones y las dos órdenes alternadas dentro de cada
una**, proceso nuevo por celda (`orden_lote.py`):

| orden | n | mediana | min | max | recorrido |
|---|---:|---:|---:|---:|---:|
| descendente | 5 | **1 532** | 1 528 | 1 578 | 50 |
| ascendente | 5 | **1 455** | 1 448 | 1 498 | 50 |

**Diferencia −77 MiB, signo conservado en 5 de 5 repeticiones, y supera el ruido
de ±43.** Es decir:

> **MEDIDO — el ORDEN del lote es una variable del MOTOR, igual que el `k`.**
> Sobre EasyOCR, que no tiene tope, el descendente gana **5 350 MiB**; sobre
> RapidOCR, que recorta a 2 000 px y sí lo tiene, el descendente **pierde 77**.
> Los dos números están medidos y **no se contradicen**: describen motores
> distintos. Se fija **un** orden por **mínimo arrepentimiento** —descendente— y
> **se publica el arrepentimiento**, que es de 77 MiB (el 5 % del coste de
> RapidOCR) contra una ganancia de 5 350 en el motor donde importa.

Esto matiza la trampa 67 sin refutarla: su enunciado —*«el orden bueno es
descendente»*— sigue siendo la elección correcta, pero **no es gratis en todos
los motores**, y quien lea la trampa tiene que saberlo antes de aplicarla a un
motor con tope.

### V3 · Cláusula B — el rechazo ocurre ANTES de cargar el modelo — **MEDIDO**

Con la VRAM inyectada a 900 MiB —no hace falta llenar 12 GiB de verdad, y **no
se puede** sin robarle la tarjeta a otro— y pidiendo EasyOCR sobre 8,882 Mpx:

```
veredicto  : rechazar
motivo     : 10234 + 500 > 900 MiB aun reciclando: esta pagina no cabe en esta maquina
residentes : 0
VRAM movida: 0 MiB
```

**Cero residentes y cero MiB movidos**: la decisión se toma con la aritmética,
no descubriendo el atasco. Y el motivo lleva **los cuatro números dentro**, que
es lo que separa un veredicto auditable de un `False`.

### V4 · Cláusula E — el reciclado, con PID y VRAM a los dos lados — **MEDIDO**

| | |
|---|---|
| VRAM con el modelo dentro | 3 164 MiB |
| VRAM tras reciclar | **1 820 MiB** |
| coste | **5,842 s** |
| PID antes → después | 29 156 → **33 240** (distinto) |
| `mpx_max_visto` tras reciclar | **0,0** (el historial se olvida, que es el punto) |

**Se comprueba el mecanismo, no solo el efecto** (trampa 40): el PID cambia. Un
«reciclado» que reutilizara el proceso devolvería VRAM por casualidad o por
nada, y la prueba de comportamiento pasaría igual.

**Salvedad de comparabilidad:** los **4,08 s** que publica G5 para RapidOCR son
`import` + construcción del motor medidos dentro del proceso; mis **5,84 s** son
*cerrar el proceso + lanzarlo + protocolo de arranque + esperar el «listo»*, es
decir el reciclado **completo tal y como lo hace el sidecar**. Son dos órdenes
distintas y **no se restan** (trampa 79). La conclusión operativa no cambia:
reciclar es caro y por eso la política no puede ser «cada N páginas».

### V5 · Cláusula C — el presupuesto declarado

El `Perfil` del módulo reproduce la aritmética de §6.1 de G5 al MiB (7 564 con
sus cifras publicadas), y §3.4 lo mide de punta a punta: **7 187 MiB**. Las dos
cumplen; la segunda es una medida.

### V7 · Cláusula C — los tres perfiles, medidos de punta a punta — **MEDIDO**

`large-v3` con audio de 11 s (tanda G, n=9) y con el de **308 s** (tanda H,
n=3 — menos repeticiones porque cada corrida transcribe cinco minutos de audio y
cuesta 134 s; el recorrido entre ellas fue de **100 MiB**, y de **2 MiB** en la
fase de audio solo).

| perfil (todo `cuda`, vía `ruta`, ≤ 8,882 Mpx) | coste propio medido | + escritorio 3 448 | veredicto (techo 8 909 MiB) |
|---|---:|---:|---|
| **A** · `distil-large-v3`, audio 11 s | **3 739** | **7 187** (7,02 GB) | **cumple** |
| **B** · `large-v3`, audio 11 s | **5 469** | **8 917** (8,71 GB) | **NO cumple — por 8 MiB** |
| **C** · `large-v3`, audio 308 s | **6 083** | **9 531** (9,31 GB) | **NO cumple** |

> **La fila B es la mejor demostración de por qué el criterio necesitaba el
> tamaño de la entrada dentro.** El mismo perfil, el mismo código, los mismos
> modelos: **incumple por 8 MiB con un audio de 11 segundos y por 622 con uno de
> cinco minutos.** Sin declarar la duración, «`large-v3` + OCR + NVENC no cumple»
> es una afirmación que unos días saldría y otros no.

Y la aditividad, para este perfil (tanda H, las cuatro fases en la misma tanda):

| | MiB |
|---|---:|
| `solo_nvenc` | 459 |
| `solo_ocr` @8,882 Mpx | 1 520 |
| `solo_audio` `large-v3` 308 s | 4 575 |
| **suma** | **6 554** |
| **`dos_procesos`, los tres a la vez** | **6 083** |
| diferencia | **−471 (−7,2 %)** |

**MEDIDO — y matiza §3.1: la sobreestimación de la suma NO es una constante, es
del perfil.** Con `distil` es del **1,2 %** y con `large-v3` del **7,2 %**. El
signo se conserva en los tres perfiles medidos —la suma **siempre** sobreestima—
así que sigue valiendo como cota superior; lo que no vale es publicar «el 1 %»
como si fuera una propiedad del sistema.

### V6 · Cláusula F — la precisión, contra ESTA implementación — **MEDIDO**

`precision_h6.py`, con el sidecar real, dispositivo **`cuda`**, vía **`ruta`**,
motor **RapidOCR ONNX PP-OCRv6 small + R6**, métrica **`acentos`**
(`bench/scripts/ocr_eval.py`, importado):

| documento | ppp nativos | Mpx | chars | **distancia de edición** | CER (`acentos`) | frases exactas | ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| `patologico_escaneado` | 200 | 2,319 | 81 | **0** | 0,0 % | 3 / 3 | 883,1 |
| `escaneado_d1` | 150 | 1,261 | 81 | **0** | 0,0 % | 3 / 3 | 310,8 |
| `escaneado_d2` | 100 | 0,550 | 81 | **0** | 0,0 % | 3 / 3 | 595,0 |

**3 de 3 con distancia 0.** No es una cifra heredada: sale de pedirle las tres
páginas al sidecar que se entrega. La referencia tiene 79 caracteres y **no
lleva ni un diacrítico**, así que la métrica acentuada y la ciega dan lo mismo
aquí (0,0 y 0,0) — se declara para que nadie lea este 0 como evidencia sobre
castellano acentuado, que es lo que mide `escaneado_d4` y **sigue sin cerrarse**.

---

## 7. N23 — los dos testigos en `bench/scripts/ocr_motor.py`

**El pendiente lo declaró su propio autor** (`ocr-produccion-sidecar.md` §10):
*«`ocr_motor.py` no los lleva y se declara»*. Sin ellos sus milisegundos valen
como cifra relativa dentro de una tanda y nada más — y ni siquiera eso, porque
una tanda que coincidió con una descarga dio un error de **7,4×** y nadie lo
vio.

Puesto:

- **`testigo_deriva()`** — bucle monohilo, antes y después. Ve la deriva
  **dentro** de la tanda.
- **`testigo_nivel()`** — `ffprobe -version`. Ve el **nivel** de carga de la
  máquina, que es a lo que el monohilo es ciego: con 12 núcleos cabe en un
  núcleo libre y etiquetó `limpia` una tanda que salió ×6,8.
- **Tope de 20 s en el propio testigo**, devolviendo el tope y marcando `SUCIA`:
  en el caso P3, `ffprobe -version` agotó un timeout de 60 s y **tumbó la
  medición que venía a vigilar**.
- **`veredicto_ruido()`** devuelve `limpia`/`SUCIA` **con los cuatro números
  dentro**, y va en `fin["ruido"]` y en la raíz del resumen `.json`. La etiqueta
  sola no vale: con la sesión remota activa todo sale `SUCIA` por construcción.
- Y de paso, **la resolución del reloj** (`get_clock_info("perf_counter")`,
  1e-07 s) queda escrita en `meta` (trampa 62).

Las funciones van **auto-contenidas** en el fichero, no importadas: `bench/`
`scripts/` es código compartido y no puede depender del directorio de salidas de
un agente. La misma lógica vive en `bench/salidas-hito6/testigos.py` y **la
duplicación se declara en los dos sitios**.

**Lo que N23 NO arregla, y hay que decirlo:** los testigos miden el ruido de las
tandas **futuras**. Las cifras ya publicadas por informes que usaron este arnés
**no ganan un veredicto retroactivo**; siguen siendo relativas dentro de su
tanda.

---

## 8. Lo que falló, y lo que refuté

### 8.1 Rompí una tanda editando el código que estaba midiendo

Con la tanda del factorial corriendo, edité `filex/sidecar.py` para añadir el
drenado del `stderr` (§8.2). Consecuencia:

- la corrida 04 de `dos_procesos` murió con
  `AttributeError: 'Trabajador' object has no attribute '_drenar_stderr'`
  —el módulo se releyó a medias— y quedó con `rc=1`;
- **y las cuatro corridas anteriores de esa fase habían medido OTRA versión del
  código**, sin que nada lo dijera.

Lo visible fue la suerte. Lo que había que tirar era la tanda entera, y se tiró:
las cifras que se publican en §3 son de una tanda repetida **después** de dejar
el código quieto. La versión rota se conserva en
`bench/salidas-hito6/json/E_*.json` con esta nota, porque borrarla sería peor.

### 8.2 El `stderr` en `PIPE` que nadie lee cuelga al trabajador — con control positivo

Un `subprocess.run(..., capture_output=True)` no sufre esto: lee al final. Un
**proceso de vida larga** con `stderr=PIPE` y nadie leyendo se para en cuanto la
tubería se llena, y la tubería de Windows son **64 KiB**. RapidOCR emite una
línea de `INFO` por fichero de pesos; PaddleOCR imprime más.

Medido con un trabajador de mentira que escribe 4 000 líneas en `stderr` antes
de decir «listo», con el tope de arranque bajado a 12 s a propósito:

| variante | tiempo hasta el resultado | resultado |
|---|---:|---|
| **con** el hilo que drena | **0,06 s** | arranca |
| **sin** el hilo que drena | **12,01 s** | agota el tope y muere |

El control positivo es lo que hace que la prueba signifique algo: sin él,
`test_arranca_pese_a_4000_lineas_de_stderr` sería una prueba que pasa siempre
(trampa 38). El anillo de 50 líneas que se conserva es **para el humano que
depura** y sale por un método aparte (`Trabajador.diagnostico()`): *nunca
devolver `stderr` crudo* sigue valiendo por el camino normal.

### 8.3 La recta de RapidOCR subestima 339 MiB en el tramo de en medio

`ocr-produccion-sidecar.md` §5.1 publica para RapidOCR
`ordenada 643, 109 MiB/Mpx, tope 1 526`, con **r²=0,7581**, y explica el r² malo
diciendo que *«no es ruido: es la saturación»*. Eso es cierto en el extremo y
**engañoso en el medio**:

| Mpx | modelo `min(643 + 109·Mpx, 1526)` | medida de §3.3 de aquel informe | residuo |
|---:|---:|---:|---:|
| 0,550 | 703 | 556 | +147 (sobreestima) |
| 1,248 | 779 | 688 | +91 |
| 2,221 | 885 | 944 | **−59** |
| 4,352 | **1 117** | **1 456** | **−339** |
| 8,882 | 1 526 | 1 456 | +70 |

**Un modelo que subestima no es una cota superior**, y un presupuesto construido
sobre él se queda corto justo donde no hay aviso. Aquí no rompe nada porque el
**margen de 500 MiB lo tapa por 161**, pero eso convierte el margen en una pieza
que sostiene el modelo y no en un lujo: **bajarlo a 300 MiB dejaría la celda de
4,352 Mpx en descubierto**. Queda escrito, y con una prueba que lo fija.

*(No invalida ninguna cifra publicada: G5 declaró la recta como cota floja y no
la usó para presupuestar nada. Lo que se corrige es la lectura de su r².)*

### 8.4 Lo que NO conseguí refutar

- **El orden descendente de un lote.** Se comprueba en §6 y sale como se
  esperaba: sobre el motor de producción, que tiene tope propio, **no hay
  diferencia** entre ascendente y descendente. Es un resultado nulo **con su
  mecanismo dicho** —el recorte a 2 000 px hace que los folios grandes sean el
  mismo array— y por tanto no dice nada contra la medida de EasyOCR, que sí la
  tenía. Un resultado nulo sin mecanismo se cae en cuanto cambie el motor
  (trampa 56).
- **La cláusula de precisión.** Distancia de edición 0 en los tres documentos
  que ya la cumplían (§6). No he movido `d3` ni `escaneado_d4`, y no lo prometo.

---

## 9. Lo que este informe NO cubre

- **Docling no se ha medido, y el hito lo nombra.** El enunciado pide *«Docling
  con RapidOCR en `backend="torch"`»* y aquí solo hay **RapidOCR ONNX suelto**.
  El backend `torch` tiene otro asignador y **no se puede suponer que hereda el
  tope de 1 526 MiB**. Es el mismo pendiente que dejó G5, y sigue abierto.
- **La mitad de audio del hito está a medias.** El criterio nombra
  *«faster-whisper (`distil` ≤30 s, `large-v3` por encima)»*; aquí se han medido
  los dos modelos y **el umbral de 30 s no se ha implementado en el sidecar**:
  `filex/sidecar.py` gestiona motores de OCR, y el registro de modelos de audio
  usaría las mismas piezas pero **no está escrito ni medido**.
- **Un solo documento base para la VRAM.** Toda la parte de tamaños sale de
  `escaneado_d4` reescalado. Si el coste dependiera del **contenido** (número de
  cajas detectadas) y no solo del tamaño del array, aquí no se vería.
- **La vía de entrada `ndarray` no se ha medido.** El sidecar entrega **ruta**
  siempre, que es la vía con la que están medidas todas las rectas. Repartir un
  array a varios motores vale hasta **12,58 puntos de CER** (trampa 30) y es un
  cambio de adaptador, no de sidecar.
- **Un solo actor.** Todo con un usuario y una tarjeta. Dos sidecars de dos
  usuarios sobre la misma GPU no se han probado; el `GPU_GUARD` los vería por
  VRAM libre total, pero eso es una expectativa, no una medida.
- **Nada de esto se ha medido en CPU.** El dispositivo está fijado a `cuda`
  (trampa 11) y el camino de CPU del sidecar solo tiene pruebas de lógica.
- **El sidecar no está enchufado a `filex/nucleo.py`.** Es una pieza con su API
  y sus pruebas; **quién lo llama y cuándo** es trabajo del hito que lo integre,
  y este informe no lo toca (ese fichero es de otro agente esta ronda).

---

## 10. Reglas del encargo

| regla | estado |
|---|---|
| Escribir solo en `filex/sidecar.py`, `bench/scripts/ocr_motor.py`, `pruebas/test_hito6.py`, `bench/hito6-sidecar.md`, `bench/salidas-hito6/` | **Cumplida.** `git status` al terminar no muestra ningún otro fichero tocado |
| No tocar `filex/verificador.py`, `nucleo.py`, `contrato.py`, `gpu.py`, `cerrojo.py`, `huella.py`, `sondeo*`, `ocr_eval.py`, `harness.sh`, `referencia.json`, informes ajenos | **Cumplida.** `gpu.py` y `ocr_eval.py` **importados y usados**, no editados; `referencia.json` ni abierto |
| Corpus LFS | `corpus/imagen/tipico.png` venía en **130 B**; `git lfs checkout` (266 MB, del almacén local, sin red) antes de nada |
| Lock de GPU con `filex/gpu.py` | **Cumplida en las cinco tandas.** Es además el primer arnés `.py` del proyecto que lo toma (§1.1) |
| Medianas de n≥9 con los dos testigos y tope de 20 s | **Cumplida.** n=10 corridas por fase, la primera descartada (trampa 7); los dos testigos en las 100+ corridas |
| Marcar MEDIDO/PENDIENTE | **Cumplida** |
| Trampa 68: el criterio nombra el tamaño de la entrada | **Cumplida.** `mpx_max` es un campo obligatorio de `Perfil`, y la cláusula B publica los tres tamaños admisibles |
| Trampa 62: preguntar al instrumento su resolución | **Cumplida.** Reloj (1e-07 s) y ruido de la sonda de VRAM (±43 MiB) declarados antes de usarlos |
| Dispositivo fijado (trampa 11) | **Cumplida.** `cuda` en todo, y en cada resultado del sidecar |
| Vía de entrada declarada (trampa 30) | **Cumplida.** `ruta`, en cada resultado |
| Timeouts explícitos | **Cumplida.** Arranque, petición, NVENC (`-t` DENTRO de la orden), sonda y testigos |
| Dos intentos por problema | **Cumplida.** La coresidencia: intento 1 (mismo proceso) muere, intento 2 (orden invertido y dos procesos) funciona y se mide. Nada de bucles de reintento |
| Directorio desechable y censo (R21) | **Cumplida.** Un desechable por trabajador, censado al arrancar y al cerrar: **0 sobrantes**; `git status` limpio salvo lo mío |
| No versionar binarios regenerables, pero **guardar el texto** | **Cumplida.** Los PNG del rasterizado se borran con `sha256` y orden exacta en el `MANIFIESTO.md`; **las salidas de OCR en texto se quedan** (fila N17) |
| Nada instalado en los venv | **Cumplida.** `.venv-ai` solo se usó para ejecutar |
| Suite verde | **Cumplida.** De **348 passed, 6 skipped** a **398 passed, 8 skipped**. Las 348 anteriores, intactas |
| GPU libre al terminar | **Cumplida.** Lock libre, **10 380 MiB libres**, y un censo de procesos: **cero** procesos de Python míos vivos |

---

## 11. Trampas propuestas para `CLAUDE.md` — **NO APLICADAS**

Rango **82-85, cerrado**. **No se han escrito en `CLAUDE.md`.**

> **82. Dos bibliotecas de GPU en el mismo entorno pueden traer la MISMA DLL con
> distinto contenido, y entonces quien la carga PRIMERO decide si la otra
> funciona — MEDIDO** (`bench/hito6-sidecar.md` §2). En `.venv-ai` hay **dos
> `cudnn64_9.dll`**: la de `ctranslate2` (266 288 B) y la de `torch\lib`
> (438 840 B, que además trae los siete módulos en que cuDNN 9 está partida).
> Importando `faster-whisper` **antes** que RapidOCR, el proceso muere en **10 de
> 10** con `Could not load symbol cudnnGetLibConfig. Error code 127` y
> `rc=0xC0000409` —`__fastfail`, **sin excepción que capturar**—; invirtiendo el
> orden, **0 de 10**. **Consecuencia de diseño: un criterio de aceptación que
> dice «dos modelos residentes» tiene que decir EN CUÁNTOS PROCESOS**, y la
> respuesta segura es uno por motor, que aquí cuesta **+98 MiB (×1,027)**. Y el
> corolario general: **cuando dos venvs de IA se junten, inventaría las DLL
> repetidas antes de suponer que conviven** — `ctranslate2`, `torch`,
> `onnxruntime` y `paddle` traen las suyas.

> **83. Un `stderr` en `PIPE` que nadie lee es un tope de 64 KiB, y el proceso se
> cuelga escribiendo un LOG — MEDIDO, con control positivo** (ídem §8.2). Con un
> trabajador que emite 4 000 líneas en `stderr` antes de decir «listo»: **sin**
> el hilo que drena, el arranque **no termina** (12,01 s hasta el tope); **con**
> él, **0,06 s**. `subprocess.run(capture_output=True)` no lo sufre porque lee al
> final, así que **el modo de fallo aparece justo al pasar de invocar un motor a
> mantener un proceso vivo**, que es lo que hace un sidecar. Y la mitad
> defensiva: el `stderr` drenado se guarda en un anillo **para el humano que
> depura** y sale por un método aparte — *nunca devolver `stderr` crudo* sigue
> valiendo por el camino normal.

> **84. No edites el código que está bajo medición: la tanda se parte en dos
> poblaciones y no lo dice nadie — MEDIDO por accidente** (ídem §8.1). Con una
> tanda de 60 corridas en marcha, un cambio en `filex/sidecar.py` hizo que una
> corrida muriera con `AttributeError` **y que las cuatro anteriores de esa fase
> hubieran medido otra versión del código**. La que murió fue la suerte: la que
> hace daño es la que sigue devolviendo un número. **Lo que hay que tirar no es
> la corrida rota, es la tanda**, y el arreglo es una regla de proceso, no de
> código: mientras haya una tanda corriendo, el código que mide y el código que
> se mide **no se tocan**.

> **85. Un modelo publicado como «cota superior» puede SUBESTIMAR en el tramo de
> en medio, y su r² malo lo estaba anunciando — MEDIDO** (ídem §8.3). La recta de
> RapidOCR `min(643 + 109·Mpx, 1526)` (r²=0,7581) pide **1 117 MiB a 4,352 Mpx**
> donde su propio informe midió **1 456**: **−339**, y en dos de los cinco puntos
> el residuo es negativo. El r² se había leído como *«no es ruido, es la
> saturación»*, que es cierto **en el extremo** y falso en el medio. No rompe
> nada porque el margen de 500 MiB lo tapa por 161 — **y eso convierte el margen
> en la pieza que sostiene el modelo**, así que bajarlo deja una celda en
> descubierto. **Cuando heredes un modelo con r² malo, tabula el residuo punto
> por punto antes de presupuestar con él: la explicación del r² no es el
> residuo.**

---

## 12. Ficheros

### Código entregado

| ruta | qué es |
|---|---|
| `filex/sidecar.py` | **nuevo.** El sidecar: `Motor`, `Perfil`, `decidir`, `orden_descendente`, `megapixeles`, `Trabajador`, `Registro`, y el modo `--trabajador` que corre bajo el intérprete de cada venv |
| `pruebas/test_hito6.py` | **nuevo.** 52 pruebas: rectas, decisión, orden, geometría, presupuesto, registro (TTL/LRU/reciclado), protocolo del trabajador y forma sobre el AST |
| `bench/scripts/ocr_motor.py` | **modificado (N23).** Los dos testigos de ruido con tope propio, el veredicto en el resumen y la resolución del reloj declarada |

### Arneses y salidas

| ruta | qué es |
|---|---|
| `bench/salidas-hito6/preparar_h6.py` | rasteriza con Ghostscript y **compara los `sha256` con los de G5** |
| `bench/salidas-hito6/coresidencia.py` | el arnés del factorial: fases `base`, `solo_audio`, `solo_ocr`, `solo_nvenc`, `coresidente`, `coresidente_inv`, `dos_procesos` |
| `bench/salidas-hito6/run_h6.py` | el lanzador, **con el lock de GPU tomado desde Python** |
| `bench/salidas-hito6/testigos.py` | los dos testigos de ruido con tope |
| `bench/salidas-hito6/sonda_cudnn.py` | el inventario de cuDNN y los módulos vivos del proceso (§2.2) |
| `bench/salidas-hito6/verificar_criterio.py` | V1-V5: TTL, orden, rechazo, reciclado, presupuesto |
| `bench/salidas-hito6/orden_lote.py` | V2 repetido n=5 con las dos órdenes alternadas |
| `bench/salidas-hito6/precision_h6.py` | V6: la cláusula de precisión con `ocr_eval.py` importado |
| `bench/salidas-hito6/plan_gen.py`, `plan_*.json` | los planes de tanda |
| `bench/salidas-hito6/analisis_h6.py`, `ver.py` | las tablas de §3 |
| `bench/salidas-hito6/{json,logs,texto}/` | resultados crudos, trazas y **las salidas de OCR y de transcripción en texto** |
| `bench/salidas-hito6/MANIFIESTO.md` | cómo se reproduce todo, con `sha256` de los PNG borrados |

### Estado al terminar

- **Suite:** **398 passed, 8 skipped**, desde **348 passed, 6 skipped**. Los dos
  `skip` nuevos son los dos que tienen que serlo: `ConLaTarjeta` (detrás de
  `FILEX_PRUEBAS_SIDECAR=1`, porque el lock de GPU es de máquina y meterla en la
  suite sería robarle la tarjeta a quien esté midiendo — con la variable puesta,
  **50 passed**) y `test_png_del_rasterizado` (el ráster se borra al terminar,
  §6 del `CLAUDE.md`; la geometría queda cubierta por dos pruebas con PNG y JPEG
  **sintéticos**, que no dependen de ningún binario).
- **Huella:** `sondeo.diagnostico()` → `caducados: {}`, `sin_huella: []`,
  `build_distinto: []`. **Comprobado, no supuesto**: `filex/sidecar.py` es un
  módulo nuevo que ningún motor alcanza desde `verificar()` ni desde su MRO, y
  `bench/scripts/ocr_motor.py` no es código del paquete.
- **GPU:** lock libre, cero procesos de OCR o de audio propios vivos, y la VRAM
  de vuelta en su base.

---
