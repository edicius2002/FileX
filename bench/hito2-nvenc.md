# Hito 2 — NVENC con sondeo y degradación · B6 (el lote) · N7 (el lock en `filex/`)

Agente **H2**, 28/08/2026. Worktree aislado, `main` en `1144a83`.
Salidas y arneses en `bench/salidas-hito2/` (`MANIFIESTO.md` con las órdenes).

> **Estado del hito 2: CUMPLIDO en sus tres cláusulas, con la tercera
> reformulada y dicha en voz alta.** El camino hasta ahí destapó **dos falsos
> negativos** que habrían dejado el hito «hecho» y roto, y **la premisa de B6
> queda REFUTADA**: el lote no concentra la ventaja de la GPU, la **diluye**.

---

## 0. Resumen ejecutable

| # | Afirmación | Marca |
|---|---|---|
| 1 | `av1_nvenc` aparece listado **y con página de ayuda completa**; falla al **abrir el codificador**, con `rc = AVERROR_EXTERNAL (-542398533)` y **0 fotogramas** | MEDIDO |
| 2 | **Una sonda de 64×64 declara averiados `hevc_nvenc` y `h264_nvenc`**, que sí funcionan. Mínimos exactos por bisección: **129×33** y **145×49** | MEDIDO |
| 3 | El número de fotogramas de la sonda **no decide nada** (1→25 idéntico); el **tamaño** sí | MEDIDO |
| 4 | Degradar el **códec** sin degradar su **control de tasa** produce `rc=-22` y **0 bytes**: `libsvtav1` no admite `-maxrate` | MEDIDO |
| 5 | `hevc_nvenc` por defecto para HEVC; `av1_nvenc` → `libsvtav1` **sin intervención**, con su `rc` viajando dentro | MEDIDO |
| 6 | El desvío de bitrate de NVENC va de **+9,82 % a +24,59 %** y **crece al bajar el bitrate**; el de `libx265`, de +2,10 % a +10,35 % | MEDIDO |
| 7 | El contrato da **`ok` a las 8 celdas**, incluida la de +24,59 %: **no hay regla de bitrate de VÍDEO**, solo de audio | MEDIDO |
| 8 | **B6: el lote da ×4,10, la conversión suelta ×7,68.** El lote DILUYE | MEDIDO |
| 9 | El `bash` que Python encuentra por nombre es el de **WSL2**, no el Git Bash | MEDIDO |
| 10 | `cerrojo.Candado` **NO** excluye al `noclobber` del arnés; `gpu.Lock` **SÍ**, en las dos direcciones y con los dos controles | MEDIDO |
| 11 | NVENC cuesta **~211 MiB** de VRAM: el umbral de 6 000 MiB del `GPU_GUARD` está calibrado para otro régimen | MEDIDO |
| 12 | El lock **dentro de la conversión** no se puede poner desde `motores.py`: hace falta una línea en `nucleo.py`, que no es mío | PENDIENTE, acotado |

**Suite:** `333 passed, 6 skipped, 1 failed`. Base declarada: `298 passed, 6 skipped`.
Los **36** nuevos son `pruebas/test_hito2.py`; el rojo es
`test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`
con `{'ffmpeg': ['motor']}`, **que es el rojo esperado y aceptado** (§7).

---

## 1. Dónde falla `av1_nvenc`, que es lo que decide dónde va la degradación

La regla del proyecto dice *«`av1_nvenc` aparece listado y no funciona»*. La
pregunta operativa era **dónde**, y la respuesta cambia el diseño.

**No hay nada que mirar antes de ejecutar — MEDIDO** (`sonda_nvenc.sh`):

```
Encoder av1_nvenc [NVIDIA NVENC av1 encoder]:
    General capabilities: dr1 delay hardware
    Supported hardware devices: cuda cuda d3d11va d3d11va
    Supported pixel formats: yuv420p nv12 p010le yuv444p ... (14 formatos)
    av1_nvenc AVOptions: ...
```

`ffmpeg -encoders` lo lista y **`-h encoder=av1_nvenc` responde con la ficha
entera**: dispositivos, formatos de píxel y opciones privadas. Un sondeo
«estático» —que es lo que casi todo el mundo haría— **diría que sí**.

**Falla al abrir el codificador, antes del primer fotograma:**

```
[av1_nvenc] Codec not supported
[av1_nvenc] No capable devices found
[enc:av1_nvenc] Error while opening encoder - maybe incorrect parameters ...
[out#0/matroska] Nothing was written into output file ...
frame=    0 ... Conversion failed!
```

**Consecuencia de diseño:** como falla en `avcodec_open2` y no a mitad del
flujo, la degradación puede vivir **antes** de la invocación real —una sonda
barata y cacheada— en vez de tener que reintentar la conversión entera. Si
hubiera fallado a mitad, el hito 2 habría necesitado reintento con
`ffmpeg` ya arrancado, que es otro coste y otro contrato.

### 1.1 El `rc` es la respuesta (trampa 72), y aquí separa dos cosas

| Códec | `rc` (con signo) | Bytes en disco | Mensaje |
|---|---:|---:|---|
| `av1_nvenc` | **−542 398 533** (`AVERROR_EXTERNAL`) | **0** | `No capable devices found` |
| `hevc_nvenc` a 64×64 | **−22** (`EINVAL`) | **0** | `Error while opening encoder` |

**Los dos devuelven cero bytes y los dos «fallan al abrir».** Solo el `rc` los
separa, y son cosas opuestas: uno es una tarjeta que no sabe, el otro es una
sonda mal construida. Por eso `gpu.capacidad()` devuelve `(funciona, rc, motivo)`
y no un booleano, y por eso la degradación se lleva el `rc` dentro.

### 1.2 El destino de la sonda da igual — MEDIDO (`sonda_rc.json`, 20 celdas)

`-f null -`, `-f null NUL`, `-f null <devnull>` y un fichero Matroska real dan
**el mismo `rc` en los cinco códecs**. Lo que no da igual es el tamaño.

---

## 2. ⚠ El falso negativo de la sonda: **el lienzo pequeño**

Este es el hallazgo que más cerca estuvo de dejar el hito «hecho» y roto.

El reflejo al escribir una sonda de capacidad es hacerla **lo más barata
posible**: un lienzo diminuto, un fotograma. Y la trampa 52 del proyecto
*obliga* a poner el tope dentro de la orden (`-frames:v N`), lo que refuerza
ese reflejo. Con `testsrc=size=64x64 -frames:v 1`:

```
hevc_nvenc  rc=-22   <- FALSO NEGATIVO: este codificador SÍ funciona
h264_nvenc  rc=-22   <- FALSO NEGATIVO
av1_nvenc   rc=-542398533
```

**Y no es el número de fotogramas.** Barrido de 1, 2, 3, 4, 5, 8, 16 y 25
(`sonda_frames.json`, 24 celdas): **`rc` idéntico en los tres códecs a las ocho
duraciones**. La primera hipótesis —«NVENC tiene retardo de tubería y con un
fotograma no llega a emitir»— era plausible y **falsa**.

**Es la GEOMETRÍA.** Barrido de 12 tamaños (`sonda_geometria.json`, 36 celdas,
deterministas):

| Códec | 16–128 px | 144×144 | 160×160 | 320×240 |
|---|---|---|---|---|
| `hevc_nvenc` | `-22` | **`0`** | `0` | `0` |
| `h264_nvenc` | `-22` | `-22` | **`0`** | `0` |
| `av1_nvenc` | `-542398533` | `-542398533` | `-542398533` | `-542398533` |

Frontera exacta por bisección independiente en cada eje (`sonda_frontera.json`),
con el píxel de menos comprobado en los dos ejes:

| Códec | ancho mínimo | alto mínimo | `w-1` | `h-1` |
|---|---:|---:|---|---|
| `hevc_nvenc` | **129** | **33** | `-22` | `-22` |
| `h264_nvenc` | **145** | **49** | `-22` | `-22` |

`SONDA_LIENZO = "256x256"` en `filex/gpu.py` sale de aquí, y
`pruebas/test_hito2.py` comprueba las **dos** direcciones: que el lienzo supera
los dos mínimos, **y que con 64×64 el falso negativo sigue reproduciéndose**.
Una constante cuya trampa no se puede reproducir es una constante cosmética.

> **La forma general, que es lo transferible:** una sonda de capacidad se
> construye con la **entrada más pequeña posible**, y los aceleradores por
> hardware tienen **mínimos de entrada**. La sonda barata y el codificador
> capaz **no se solapan**. Y el modo de fallo es el peor posible: `EINVAL`,
> «argumento inválido», que es exactamente lo que uno espera de un
> codificador que no existe.

---

## 3. ⚠ El segundo falso negativo: **degradar el códec no degrada sus banderas**

La primera versión de la degradación era correcta en el `argv` y **producía un
fichero de 0 bytes**. `av1_nvenc` → `libsvtav1`, cambiando el nombre del códec y
conservando el control de tasa:

```
Svt[error]: Instance 1: Max Bitrate only supported with CRF mode
[libsvtav1] Error setting encoder parameters: bad parameter (0x80001005)
[enc:libsvtav1] Error while opening encoder ...
rc = -22 ·  0 bytes
```

`-maxrate`/`-bufsize` son válidos en `hevc_nvenc` y en `libx265`, y **SVT-AV1
los rechaza fuera de modo CRF**. La degradación **sustituía un fallo por otro**,
y con un `rc` (`-22`) idéntico al del falso negativo de §2.

Se cerró con `motores._TASA` + `motores.FAMILIA_TASA`: el control de tasa es del
**codificador real** —el que queda tras degradar—, no del que se pidió. La tabla
está **sondeada en ejecución**, no deducida de cuatro manuales
(`matriz_tasa.json`, 7 códecs × 2 modos):

| | bitrate objetivo | calidad constante |
|---|---|---|
| `hevc_nvenc`, `h264_nvenc` | `-b:v N -maxrate 1.5N -bufsize 2N -rc vbr` ✔ | `-rc vbr -cq Q -b:v 0` ✔ |
| `libx265`, `libx264` | `-b:v N -maxrate -bufsize` ✔ | `-crf Q` ✔ |
| `libsvtav1` | `-b:v N` **a secas** ✔ | `-crf Q` ✔ |
| `libvpx-vp9` | `-b:v N` ✔ | `-crf Q -b:v 0 -row-mt 1` ✔ |
| `av1_nvenc` | ✘ `-542398533` | ✘ `-542398533` |

**12 de 14 celdas OK**, y las 2 que fallan son las dos de `av1_nvenc`, que es la
premisa del hito. La celda se cuenta OK con `rc == 0 **y** bytes > 0`: con solo
el `rc`, la versión rota habría pasado.

---

## 4. El criterio del hito 2, cláusula por cláusula

> «`hevc_nvenc` se usa por defecto cuando el destino es HEVC; `av1_nvenc` se
> sondea, falla, y degrada a `libsvtav1` **sin intervención**. El desvío de
> bitrate queda registrado en los metadatos de salida.»

### 4.1 «Cuando el destino es HEVC» — el criterio nombra algo que no es un destino

**HEVC no es un destino en este grafo.** Las aristas son `(extensión origen,
extensión destino)` y HEVC es un **códec dentro** de `mkv`/`mp4`/`mov`.
`formatos.formato("hevc")` devuelve `None` y debe seguir devolviéndolo.

Resuelto **sin tocar el grafo**: `codec_video` es una **parametrización** de las
aristas de vídeo que ya existen. El grafo sigue en **215 aristas** (§7).
`pruebas/test_hito2.py::ElFormatoHevcNoEsUnaExtension` lo deja escrito para que
nadie «cierre el hito» añadiendo un `Formato("hevc", …)`.

**Cumplido — MEDIDO.** Con la capacidad sondeada en `True`:

```
elegir_codec("hevc") -> codec_video_real='hevc_nvenc', nvenc=True, degradado_de=''
```

### 4.2 «Se sondea, falla, y degrada sin intervención» — CUMPLIDO

Punta a punta por `FileX.convertir`, n=9, sobre `corpus/video/tipico.mp4`
(1920×1080, 20 s), sin que nadie configure nada:

| Petición | Códec real | Mediana | Bytes | Pistas | `comment` en el fichero |
|---|---|---:|---:|---:|---|
| `codec_video: hevc` | `hevc_nvenc` | **1 899,7 ms** | 5 766 274 | 2 | `filex.codec=hevc_nvenc; filex.bitrate_pedido_bps=2000000` |
| `codec_video: hevc` (GPU vetada) | `libx265` | 14 588,6 ms | 5 302 898 | 2 | `…; filex.degradado_de=hevc_nvenc rc=0` |
| **`codec_video: av1`** | **`libsvtav1`** | 8 697,8 ms | 5 452 547 | 2 | `filex.codec=libsvtav1; …; **filex.degradado_de=av1_nvenc rc=-542398533**` |

La tercera fila **es el criterio**: se pidió AV1, nadie intervino, salió un
fichero AV1 válido de 5,4 MB con sus dos pistas, y **el fichero lleva escrito
por qué**.

La sonda cuesta **~250 ms** y se **cachea por proceso**, como pedía
`PLAN-ORQUESTADOR.md` §4.3. No se cachea el caso «la tarjeta estaba ocupada»:
eso no es una medida de la tarjeta, es una medida del reloj, y cachearlo dejaría
a un proceso de vida larga degradando para siempre por una coincidencia de 30 s.

### 4.3 «El desvío de bitrate queda registrado en los metadatos de salida» — REFORMULADO

**La cláusula, tal como está escrita, no es implementable en una pasada**: el
desvío no existe cuando se construye el `argv`. Registrarlo *dentro del fichero*
exigiría **remuxar** después de medir, es decir una segunda pasada sobre todo el
contenido para escribir una cadena de 60 bytes.

**Lo que se hace, y es equivalente y gratis:** el fichero lleva escrito **lo
pedido** (`-metadata comment=filex.bitrate_pedido_bps=…`, más el códec real y la
degradación), y **lo obtenido se deriva del propio fichero** (`bytes·8/duración`
menos el audio declarado). Con las dos mitades dentro, **el desvío es computable
sin preguntarle nada a FileX** — que es lo que la cláusula persigue.

Y una trampa de lectura que casi da un falso «no se escribió»: **el mismo
`-metadata comment=…` sale como `comment` en MP4 y como `COMMENT` en Matroska.**
Una sonda que busque la clave literal devuelve `None` en la mitad de los
contenedores.

**El desvío, MEDIDO** (`corpus/video/tipico.mp4`, HEVC, contrato ejecutado):

| Pedido | `hevc_nvenc` | desvío | `libx265` | desvío | Veredicto del contrato |
|---:|---:|---:|---:|---:|---|
| 1 000 000 | 1 245 937 | **+24,59 %** | 1 103 453 | +10,35 % | `ok` / `ok` |
| 2 000 000 | 2 302 135 | **+15,11 %** | 2 118 408 | +5,92 % | `ok` / `ok` |
| 4 000 000 | 4 422 089 | +10,55 % | 4 144 073 | +3,60 % | `ok` / `ok` |
| 8 000 000 | 8 785 354 | +9,82 % | 8 167 678 | +2,10 % | `ok` / `ok` |

Dos cosas que `HUECOS.md` §4 no decía:

1. **El desvío no es una constante del codificador: crece al bajar el bitrate.**
   El «8–11 %» publicado es el extremo **cómodo** del rango. A 1 Mbps son
   **+24,59 %**, y NVENC ya lleva `-maxrate 1,5·N` y `-bufsize 2·N` puestos.
   Es la trampa 68 otra vez: **un desvío sin el bitrate al que se midió no es un
   número.**
2. **El contrato aprueba las ocho celdas, incluida la de +24,59 %.** No es un
   fallo del contrato: `verificador.py:3719` compara `bitrate_bps` **solo contra
   pistas de AUDIO** (`x["tipo"] == "audio"`). **No existe regla de bitrate de
   vídeo.** Queda como hueco declarado (§8) — no lo toco, porque
   `filex/verificador.py` es de N3.

> **Y hay una razón para NO reutilizar la clave existente, que costó un `fallo`
> evitado:** si el bitrate de vídeo se declarase como `bitrate_bps`, la regla del
> contrato compararía los **2 000 kbps de vídeo** contra los **128 kbps de la
> pista de audio** y devolvería `fallo` sobre una salida perfecta. Por eso
> `decidido` usa `bitrate_video_bps`, y hay una prueba que lo vigila.

### 4.4 `-map 0` explícito — comprobado punta a punta

`corpus/video/patologico_2pistas.mkv` existe para esto. En el lote de B6, por
`Servicio.batch`, **los dos clips que vienen de él conservan sus dos pistas**:

```
clip05.mkv  ['hevc,video', 'aac,audio', 'aac,audio']
clip06.mkv  ['hevc,video', 'aac,audio', 'aac,audio']
```

---

## 5. B6 — el lote sobre una carpeta real, y la premisa **REFUTADA**

`HUECOS.md` §4 declara el lote *«el único escenario donde el 8,39× de HEVC decide
algo: para una conversión suelta, 16 s frente a 2 s no cambia el comportamiento
de nadie»*.

**Carpeta real:** 8 clips de 5 s, 39 920 528 B, recodificados desde las cuatro
fuentes del corpus (incluido el 4K y el de dos pistas de audio).
**Vía real:** `Servicio.batch`, la que usan las cuatro superficies, con
`job_id` y espera con tope.

| Vía | Mediana (n=3) | Tandas | Estado | Salidas |
|---|---:|---|---|---|
| GPU (`hevc_nvenc`) | **7 645,6 ms** | 6 553 / 7 951 / 7 646 | `completed` | 8/8 |
| CPU (`libx265`) | **31 330,0 ms** | 31 330 / 31 759 / 29 997 | `completed` | 8/8 |

**Ganancia en lote: ×4,10.** (Un segundo arnés independiente, con
`FileX.convertir` en bucle sobre la misma carpeta, dio **×4,43**: el orden de
magnitud se reproduce entre arneses.)

**Ganancia en conversión SUELTA, misma tanda: ×7,68** (14 588,6 / 1 899,7).

> ### El lote DILUYE la ventaja; no la concentra. La premisa de B6 está al revés.

**Y el mecanismo está medido, no supuesto.** La ganancia depende de la
**duración de la entrada**, porque el arranque de `ffmpeg`, el staging, el
desechable, el censo del punto 5 y el contrato son costes **fijos**:

| Duración | `hevc_nvenc` | `libx265` | Ganancia (tanda A) | Ganancia (tanda B) |
|---:|---:|---:|---:|---:|
| 1 s | 660,4 ms | 3 871,5 ms | ×5,86 | ×2,44 |
| 2 s | 753,1 ms | 2 158,6 ms | ×2,87 | ×3,39 |
| 5 s | 775,1 ms | 3 934,1 ms | ×5,08 | ×4,68 |
| 10 s | 1 184,9 ms | 8 347,4 ms | **×7,04** | **×6,38** |
| 20 s | 1 932,5 ms | 15 202,3 ms | **×7,87** | **×6,83** |

**Las celdas de 10 s y 20 s se reproducen entre tandas; las de 1 s y 2 s no**
(×5,86 frente a ×2,44 sobre el mismo fichero). Por debajo de ~5 s la diferencia
no es una medida: es el suelo del instrumento (trampa 36), y el ruido entra por
el lado de la CPU, no por el de la GPU — ver §5.2.

El coste fijo de FileX sobre el motor, aislado (n=9, clip de 5 s):

| Vía | `ffmpeg` crudo | `FileX.convertir` entero | Fijo |
|---|---:|---:|---:|
| `hevc_nvenc` | 753,5 ms | 780,7 ms | **+27,2 ms (+3,6 %)** |
| `libx265` | 4 047,4 ms | 4 488,8 ms | +441,4 ms (+10,9 %) |

**FileX no se come la ventaja: cuesta 27 ms sobre una conversión de GPU.** Lo
que se la come es que un clip corto no da tiempo a la tarjeta a amortizar el
arranque del proceso. **El lote no es el escenario donde la GPU decide: el
escenario es el fichero LARGO, esté suelto o en lote.**

### 5.1 Salvedad obligatoria: el vecino de CPU

**N3 estaba trabajando en CPU en paralelo durante toda la campaña.** Se ve en
los datos y hay que decirlo:

- Las celdas de **GPU** reproducen entre tandas dentro de **±2 %**
  (1 899,7 / 1 889,7 / 1 932,5 ms para el mismo fichero de 20 s).
- Las de **CPU**, dentro de **±9 %** (14 588,6 / 12 907,3 / 15 202,3 ms).

Los dos testigos de ruido dieron `limpia` en la campaña principal, y **eso es
justo el caso ya conocido**: el testigo monohilo cabe en un núcleo libre de los
12 y no ve la contención. **Todos los ratios de este informe llevan la CPU en el
denominador, así que son conservadores por el lado bueno de la GPU y ruidosos
por el otro.** El orden de magnitud (×4 en lote, ×7–8 suelto y largo) se
reproduce en tres arneses independientes; los decimales, no.

### 5.2 Un hueco que el lote destapa y que no es mío

Un lote mixto **no se puede transcodificar entero**: `nucleo.convertir` rechaza
`origen y destino son el mismo formato` cuando la extensión coincide, y
«convierte esta carpeta a HEVC» es exactamente el caso de un `.mkv` que ya está
en el contenedor de destino. En la primera tanda, **3 de 8 ficheros** fallaron
por esto (2) y por un artefacto de mi corpus (1). Recodificar dentro del mismo
contenedor es una operación legítima y hoy no existe. Vive en `filex/nucleo.py`,
que es de N3: **queda declarado, no arreglado**.

*(El tercer fallo era mío: cortar los clips con `-c copy` cae en el fotograma
clave más cercano y deja una duración declarada que no es la real, con lo que la
regla A1/V1 del contrato marca `fallo` en la conversión siguiente. Los clips
definitivos se recodifican. El contrato tenía razón.)*

---

## 6. N7 — el lock de GPU dentro de `filex/`

### 6.1 La pregunta que había que responder con número

`bench/cerrojo-unico.md` §6.6 y su pendiente 3 dicen que el `noclobber` del
arnés *«es incompatible con un candado de rango de bytes»*. **Reproducido con
los dos controles** (`medicion_n7.json`):

| Primitivo | control − (`sh` con nadie) | control + (`sh` vs `sh`) | py dentro → `sh` | **`sh` VIVO dentro → py** | **¿Excluye?** |
|---|---|---|---|---|---|
| `cerrojo.Candado` (rango de bytes) | ✔ toma | ✔ bloqueado | ✔ bloqueado | **✘ NO bloqueado** | **NO** |
| `gpu.Lock` (`O_CREAT\|O_EXCL`) | ✔ toma | ✔ bloqueado | ✔ bloqueado | **✔ bloqueado** | **SÍ** |

**Y la asimetría es peor que la incompatibilidad limpia.** `cerrojo.Candado`
*sí* bloquea al shell —de rebote, porque crea el fichero y `noclobber` se
estrella con su mera existencia— **pero el shell no lo bloquea a él**, porque el
candado mira rangos de bytes y no la existencia. Es media exclusión, y media
exclusión es peor que ninguna: **desde el lado del `.py` todo parece funcionar.**

**Respuesta a la pregunta del encargo: se usa el protocolo de `harness.sh`.**
`filex/gpu.py` implementa `O_CREAT|O_EXCL` sobre **el mismo fichero**
(`$GPU_LOCK` o `%TEMP%/filex-gpu.lock`) con **el mismo TSV de seis campos**
(`etiqueta·pid_msys·winpid·imagen·epoch·raiz`) y **la misma recogida de
huérfanos** (PID + nombre de imagen, robo bajo `mkdir` atómico). No se toca
`bench/lib/harness.sh` ni `filex/cerrojo.py`.

**Contrapartida, declarada:** `O_CREAT|O_EXCL` **no lo suelta el sistema
operativo** —que es justo por lo que `cerrojo.py` eligió el candado de bytes—.
Por eso la recogida de huérfanos es obligatoria y está medida: un lock de un PID
muerto se recupera en **122,3 ms**, y uno de dueño vivo **no** se roba.

### 6.2 ⚠ El hallazgo que casi invalida esta sección: `bash` **es WSL2**

La primera tanda decía «el shell no puede tomar el lock **ni con nadie
dentro**». Eso es un control negativo suspendido, y con él la tabla entera no
valía nada — aunque el «control positivo» salía verde (falso: `sh_toma`
devolvía siempre `BLOQUEADO`, así que «el segundo queda bloqueado» era cierto y
vacío). Es la trampa 38 en el arnés de N7.

La explicación cómoda —«los argumentos posicionales de `bash -c` no funcionan
aquí»— era **falsa**. Sondeado (`dbg_quebash.py`):

| Invocación desde Python | `uname -a` | `$BASH_VERSION` | `/mnt` |
|---|---|---|---|
| `subprocess.run(["bash", …])` | `Linux … 6.18.33.2-microsoft-standard-WSL2` | *(vacío)* | `c d wsl` |
| `subprocess.run([shutil.which("bash"), …])` | `MINGW64_NT-10.0-19045 … Msys` | `5.3.9(1)-release` | *(vacío)* |

**`bash` a secas resuelve a `C:\Windows\System32\bash.exe`, el lanzador de
WSL2.** El arnés corría dentro de la VM, donde ni las rutas de `%TEMP%` ni el
entorno cruzan — que es exactamente el límite que el proyecto ya tenía escrito
(«`%TEMP%` es por usuario y no cruza a WSL2»), aparecido por accidente en vez de
por diseño. Ahora está medido a propósito y como fila propia (`n7_wsl2`).

**Consecuencia que va más allá de mi arnés:** cualquier código de `filex/` o de
`bench/` que invoque `bash` **por nombre** desde Python en esta máquina está
hablando con otra máquina.

### 6.3 Coste, y la reentrancia que la propia defensa necesitaba

| Pieza | Mediana | n |
|---|---:|---:|
| `gpu.Lock` tomar+soltar | **1 403,6 µs** | 21 |
| `cerrojo.Candado` tomar+soltar (comparación) | 625,3 µs | 21 |
| Guardia (`nvidia-smi --query-gpu=memory.free`) | **46,3 ms** | 9 |
| Recogida de un huérfano | 122,3 ms | 1 |
| Sondeo de capacidad (una vez, cacheado) | ~250 ms | — |

**Los 46,3 ms de la guardia son la cifra que decide una arquitectura**: es el
**6,1 %** de una conversión NVENC de un clip de 5 s (753,5 ms). Preguntar por la
VRAM en cada conversión sería caro; por eso la guardia se aplica **al tomar el
lock**, una vez por tanda, y no por fichero.

**Y una trampa que la defensa se creaba a sí misma:** un lote que toma el lock
para toda la tanda y luego llama a `capacidad()` **se bloquearía contra sí
mismo**, agotaría el tope y **cachearía «esta tarjeta no sabe hacer esto»** —
un falso negativo permanente producido por el propio lock. `gpu.poseido()` y la
reentrancia por proceso lo cierran, con prueba propia.

*(Segunda trampa del mismo sitio: la recogida de huérfanos **no reintentaba**.
Con `espera=0` —el caso de quien no quiere bloquearse— recogía el huérfano y
salía por el tope en la misma vuelta, devolviendo `False` con el lock ya libre.
La medida decía «el mecanismo no funciona» y funcionaba.)*

### 6.4 La otra mitad: `GPU_GUARD`, y su umbral está calibrado para otro régimen

`filex/gpu.py` aplica los **mismos umbrales** que el arnés (aviso 7 500 MiB,
aborto 6 000) por VRAM libre **TOTAL**, nunca por PID (trampa 31). No hay censo
de procesos: un censo que solo da sospechosos no puede decidir automáticamente.

**Pero NVENC no es el régimen para el que se calibró ese umbral — MEDIDO:**

| | MiB |
|---|---:|
| Reposo (n=5, idénticas) | 1 473 |
| Pico durante una conversión `hevc_nvenc` de 1080p/20 s (n=9 muestras a 0,2 s) | 1 684 |
| **Coste propio de NVENC** | **~211** |

El umbral de aborto está **por encima del coste propio del motor más caro
medido, EasyOCR +4 430 MiB**. NVENC cuesta **×21 menos**. Conservarlo es
correcto —es un umbral de máquina compartido y no debe haber dos políticas—,
pero **abortar una conversión NVENC porque quedan 5 999 MiB libres es abortar
una tarea que necesita 211**. Queda declarado, no cambiado (§8).

*(Nota de entorno: el escritorio ocupaba **1 473 MiB** durante esta campaña, no
los 3 292–3 448 MiB documentados el 23/08. El recorrido del escritorio depende
de qué haya abierto; el número documentado no es una constante de la máquina.)*

### 6.5 Lo que NO está cerrado, acotado con precisión

**El lock se toma alrededor del SONDEO, y no alrededor del CODIFICADO.**

`Motor` tiene tres asas —`sondear()`, `orden()` y `parar()`— y **ninguna
envuelve la ejecución**: quien lanza el proceso es `nucleo._un_salto`, que llama
a `motor.orden(...)` y después a `invocacion.ejecutar(...)`. Desde `motores.py`
no hay forma honesta de sostener un lock entre las dos llamadas: `orden()`
retorna antes de que el motor arranque y `parar()` solo se invoca cuando la
invocación se agotó.

**No lo he forzado**, porque un lock que se toma en `orden()` y se suelta «en
algún sitio» es exactamente *«un lock que parezca funcionar y no excluya»*.

**El parche es de una línea y está listo**, en `filex/nucleo.py:_un_salto`,
justo antes de `invocacion.ejecutar`:

```python
import contextlib                    # nucleo.py NO lo importa hoy: comprobado
from . import gpu
ctx = gpu.Lock(f"filex-{arista.motor}") if gpu.usa_gpu(argv) else contextlib.nullcontext()
with ctx:
    r = invocacion.ejecutar(argv, timeout=timeout, cwd=t.ruta)
```

`gpu.usa_gpu(argv)` ya existe y decide **léxicamente sobre el argv construido**,
que es lo único que no depende de que cada punto de invocación se acuerde de
declararlo. Coste medido si se aplica: **1 403,6 µs** por conversión que use la
tarjeta —el **0,19 %** de una conversión NVENC de 5 s— y **0** para las que no.
`filex/nucleo.py` es de **N3**: no lo toco.

Mientras tanto, quien quiera la exclusión la tiene tomándola alrededor de la
tanda, que es lo que hacen los tres arneses de este informe y lo que hará un
lote. **La sonda —que es lo que hoy toca la tarjeta desde el paquete— sí toma el
lock siempre.**

---

## 7. Impacto sobre el sondeo — medido, **no resondeado**

Tocar `FFmpeg` caduca el componente `motor` de su huella. **Lo he medido y no he
resondeado nada**, ni he tocado `filex/huella.py`, `filex/sondeo.py` ni el campo
`huella` de ningún `filex/sondeo/*.json`.

| Motor | Componentes caducados | Aristas en su fichero | Caducan |
|---|---|---:|---:|
| `imagemagick` | — | 62 | **0** |
| **`ffmpeg`** | **`['motor']`** | 70 | **70** |
| `doc_libreoffice` | — | 16 | 0 |
| `doc_pandoc` | — | 16 | 0 |
| `doc_calibre` | — | 8 | 0 |

**70 aristas caducan; las 102 de los otros cuatro motores, ninguna.** La
granularidad por motor que `huella.py` promete se cumple: hashea la clase y su
MRO, y `ImageMagick` y `Ghostscript` no comparten nada con `FFmpeg` por debajo
de `Motor`, que no he tocado.

**El grafo sigue teniendo 215 aristas**; lo que cambia es su estado:

| | Antes (declarado) | Ahora |
|---|---:|---:|
| `real` | 210 | **142** |
| `nominal` | 5 | **3** |
| `sin_sondear` | 0 | **70** |

142 + 68 = 210 y 3 + 2 = 5: los 70 que pasan a `sin_sondear` son **exactamente**
los de ffmpeg. `sondeo.aplicar` se niega a aplicar un fichero caducado, que es
lo correcto. **Un resondeo de ffmpeg lo devuelve a 210 + 5.**

Por motor, tras el cambio:

```
imagemagick     {'real': 67}
ghostscript     {'real':  4}
ffmpeg          {'sin_sondear': 70, 'real': 15}   <- los 15 que declara _MEDIDAS
doc_libreoffice {'real': 16, 'nominal': 2}
doc_pandoc      {'real': 24}
doc_calibre     {'real': 16, 'nominal': 1}
```

Los 15 `real` que le quedan a ffmpeg son los que su propio código declara con
evidencia de `referencia.json`, que no dependen del fichero de sondeo.

Rojo esperado y aceptado:
`pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`
→ `AssertionError: {'ffmpeg': ['motor']} != {}`.

---

## 8. Lo que abre este informe

| # | Pendiente | Dónde vive | Por qué no lo cierro yo |
|---|---|---|---|
| 1 | **Resondear `ffmpeg`** (70 aristas) | `filex/sondeo/ffmpeg.json` | El encargo lo reserva explícitamente |
| 2 | **El lock alrededor del codificado** (§6.5), parche de una línea listo | `filex/nucleo.py` | Es de N3 |
| 3 | **No hay regla de bitrate de VÍDEO en el contrato** (§4.3): +24,59 % pasa como `ok` | `filex/verificador.py:3719` | Es de N3 |
| 4 | **Un lote mixto no se transcodifica**: `origen y destino son el mismo formato` (§5.2) | `filex/nucleo.py` | Es de N3 |
| 5 | **`GPU_GUARD` a 6 000 MiB para un motor que consume 211** (§6.4). ¿Umbral por tipo de tarea, o uno solo? | `harness.sh` + `gpu.py` | Cambiar uno solo crearía dos políticas |
| 6 | **`h264_nvenc` funciona y no se usa por defecto**: `codec_video` hay que pedirlo. ¿Debería `mp4→mkv` elegir GPU sola? | `motores.py` | Es una decisión de producto, no una medida |
| 7 | **El desvío de NVENC crece al bajar el bitrate** (§4.3). ¿Hay `-rc`/`-multipass` que lo acote por debajo de 2 Mbps? | — | No sondeado |
| 8 | **Todo lo de aquí es de UNA tarjeta.** Los mínimos 129×33 y 145×49 son de NVENC de Ampere; otra generación puede tener otros | — | No hay segunda tarjeta |

---

## 9. Ficheros

| Fichero | Qué es |
|---|---|
| `filex/gpu.py` | **Nuevo.** Lock compatible con `harness.sh`, guardia de VRAM y sondeo de capacidades NVENC cacheado |
| `filex/motores.py` | `CODECS_VIDEO`, `_TASA`, `FAMILIA_TASA`, `FFmpeg.elegir_codec`, `_video_codec`, `_metadatos`, `_a_bps` |
| `pruebas/test_hito2.py` | **Nuevo.** 36 pruebas; las de tarjeta y las de `ffmpeg` se saltan solas |
| `bench/salidas-hito2/` | Arneses, JSON y logs. `MANIFIESTO.md` con las órdenes y los `sha256` de lo borrado |

**Estado de la GPU al terminar:** lock **libre** (`/tmp/filex-gpu.lock` no
existe), cero procesos propios vivos, VRAM en 1 578 MiB usados / 10 538 libres.

---

## NO APLICADAS — trampas propuestas para `CLAUDE.md`, 74 a 77

*No las aplico yo. El rango está cerrado en 4; van agrupadas donde hacía falta.*

**74. Una sonda de capacidad se escribe con la entrada más pequeña posible, y el
acelerador que quieres sondear tiene un TAMAÑO MÍNIMO DE ENTRADA — MEDIDO**
(`bench/hito2-nvenc.md` §2). Con `testsrc=size=64x64`, `hevc_nvenc` y
`h264_nvenc` —que **sí** funcionan en esta tarjeta— devuelven `rc=-22`, y la
sonda barata declara averiado justo lo que venía a validar. **No es el número de
fotogramas**: el barrido de 1 a 25 da el mismo `rc` en los tres codificadores;
es la geometría, y los mínimos exactos por bisección son **129×33 para
`hevc_nvenc` y 145×49 para `h264_nvenc`** (el píxel de menos en cualquiera de
los dos ejes basta). El destino de la sonda —`-f null -`, `NUL`, `os.devnull` o
un fichero real— **da igual en 20 de 20 celdas**. Y el modo de fallo es el peor
posible: `EINVAL`, «argumento inválido», que es exactamente lo que uno esperaría
de un codificador inexistente. **La trampa 52 empuja hacia el error** —el tope
va dentro de la orden, y de ahí a hacerla mínima hay un paso—: el tope se pone
en la duración, **nunca en el tamaño**. Corolario: `av1_nvenc` falla con
`AVERROR_EXTERNAL (-542398533)` y la sonda mal dimensionada con `-22`; **los dos
dejan 0 bytes y los dos «fallan al abrir el codificador», y solo el `rc` los
separa** (trampa 25 y 72 sobre un recurso nuevo). Y el otro lado: `av1_nvenc`
aparece en `ffmpeg -encoders` **y `-h encoder=av1_nvenc` devuelve la ficha
entera** —dispositivos, 14 formatos de píxel, AVOptions—, así que **no hay nada
que sondear estáticamente**: falla en `avcodec_open2`, con `frame=0`.

**75. Degradar a un motor de repuesto no es cambiarle el nombre: sus BANDERAS no
se transfieren, y la degradación se convierte en el fallo nuevo — MEDIDO**
(ídem §3). Degradar `av1_nvenc` a `libsvtav1` conservando el control de tasa da
`Svt[error]: Max Bitrate only supported with CRF mode`, `rc=-22` y un fichero de
**0 bytes**: SVT-AV1 rechaza `-maxrate`/`-bufsize` fuera de modo CRF, mientras
`hevc_nvenc` y `libx265` los aceptan. El `argv` era impecable y la degradación
funcionaba «en el papel». **La parametrización pertenece al motor que EJECUTA,
no al que se pidió**, y la tabla que lo arregla no se puede deducir de la
documentación de cuatro proyectos distintos: se ejecutan las celdas y se
registra el `rc` de cada una (12 de 14 OK; las 2 que fallan son la premisa).
**Y una celda se cuenta buena con `rc == 0` Y `bytes > 0`**: con solo el `rc`, la
versión rota pasa. Es la trampa 23 en el eje del motor de repuesto.

**76. La ventaja de un acelerador depende del TAMAÑO de la entrada, así que un
lote de ficheros pequeños la DILUYE en vez de concentrarla — MEDIDO, y refuta
`HUECOS.md` §4** (ídem §5). El hueco B6 declaraba el lote *«el único escenario
donde el 8,39× de HEVC decide algo»*. Sobre una carpeta real de 8 clips por
`Servicio.batch`, la GPU gana **×4,10**; sobre **una sola** conversión larga de
la misma tanda, **×7,68**. El mecanismo está medido y es un coste fijo: el
mismo fichero a 1, 2, 5, 10 y 20 s da ×2,4–5,9 / ×2,9 / ×4,7–5,1 / ×6,4–7,0 /
**×6,8–7,9**, y FileX solo añade **27,2 ms (+3,6 %)** sobre el `ffmpeg` crudo,
así que **no es el orquestador**: es que un clip corto no amortiza el arranque
del proceso. **El escenario donde la GPU decide es el fichero LARGO, suelto o en
lote.** Dos avisos que van con esto: por debajo de ~5 s la diferencia está en el
suelo del instrumento y **no se reproduce entre tandas** (×5,86 y ×2,44 sobre el
mismo fichero de 1 s); y con un agente vecino en CPU, **las celdas de GPU
reproducen dentro de ±2 % y las de CPU dentro de ±9 %** — todo ratio GPU/CPU
lleva el ruido en el denominador. Corolario, que es la trampa 68 otra vez:
**un «×N» sin la duración de la entrada no es un número**, y el ×8,39 heredado
no la declaraba. Lo mismo vale para el desvío de bitrate de NVENC, que **no es
una constante**: el «8–11 %» publicado es el extremo cómodo, y a 1 Mbps son
**+24,59 %**.

**77. `bash` a secas desde Python NO es el Git Bash: es el lanzador de WSL2, y un
control cruza de máquina sin decirlo — MEDIDO** (ídem §6.2).
`subprocess.run(["bash", …])` resuelve a `C:\Windows\System32\bash.exe`
(`uname -a` → `Linux … microsoft-standard-WSL2`, `$BASH_VERSION` **vacío**,
`/mnt` → `c d wsl`), mientras `shutil.which("bash")` da el de Git
(`MINGW64_NT-10.0-19045`, bash 5.3.9), que es el que ejecuta
`bench/lib/harness.sh`. Con el equivocado, el control **negativo** del arnés de
locks daba «el shell no puede tomar el lock **ni con nadie dentro**» —cierto, y
sobre otra máquina— y el control **positivo** salía verde por el motivo
equivocado, porque una sonda que siempre responde «bloqueado» hace que «el
segundo queda bloqueado» sea trivialmente cierto. **Invoca el intérprete por
ruta resuelta, nunca por nombre**, y cuando un control negativo suspenda,
sospecha del instrumento antes que del objeto. *(Y el segundo hallazgo del mismo
sitio, que es de contenido: `filex/cerrojo.py` **no** excluye al `noclobber` del
arnés, pero **sí lo bloquea a él** —de rebote, porque crea el fichero—, así que
la exclusión es **asimétrica**: desde el lado del `.py` parece funcionar. Media
exclusión es peor que ninguna. La respuesta es usar el primitivo del arnés,
`O_CREAT|O_EXCL`, con su mismo fichero, su mismo TSV de seis campos y su misma
recogida de huérfanos — y declarar que ese primitivo, a diferencia del candado
de rango de bytes, **no lo suelta el sistema operativo**, por lo que la recogida
de huérfanos deja de ser un lujo. Un lock reentrante DENTRO del proceso tampoco
es un lujo: sin él, un lote que toma el lock para toda la tanda se bloquea
contra sí mismo al sondear y **cachea un «no» falso**.)*
