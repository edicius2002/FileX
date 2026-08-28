# El bitrate de vídeo, el lock alrededor del codificado y el `.pdb` · N4

**Fecha:** 2026-08-28 · **Agente:** N4 · **Worktree:** `agent-a252dc57c56703459`
**Encargo:** N24 (regla de bitrate de vídeo en el contrato), N25 (el lock de GPU
rodea al codificado), N22 (`.pdb`, el último `sin_vocabulario` con deuda real).

**Restricción cumplida:** la GPU la estaba usando otro agente (S6). **Ninguna
celda de este informe codifica en la tarjeta.** Lo único que la toca es la
consulta de solo lectura de `nvidia-smi` que hace `gpu.guardia()`, y sale
cronometrada en §3. El lock de máquina **no se ha tomado**: las medidas de §3 y
las pruebas de `pruebas/test_bitrate_y_lock.py` apuntan `GPU_LOCK` a un fichero
propio del `tempdir`. Las cifras de NVENC que aparecen son **de H2, citadas**.

---

## 0. Lo que sale de aquí, en siete líneas

1. **N24 — la regla no faltaba: faltaba el DATO.** *Ni la sonda en proceso ni
   `ffprobe -show_streams` publican el `bitrate_bps` de una pista de VÍDEO*
   — 4 contenedores de 4 con `None`. Quitar el filtro `tipo == "audio"` que
   denunció H2 **no habría arreglado nada** (trampa 58).
2. **Sobre lo único observable —el bitrate del CONTENEDOR— las dos clases SE
   SOLAPAN**: legítimo hasta **+106,13 %**, patológico desde **+82,13 %**.
   **No existe umbral bilateral**, y la pregunta correcta era la de la trampa 51.
3. **Sí existe una regla asimétrica, y la asimetría tiene demostración, no
   prudencia**: el audio solo SUMA, así que el contenedor es cota **superior**
   del vídeo. Por abajo vale siempre; por arriba, solo sin audio.
   **Meseta de 0 falsos positivos: 60–75 %. `BITRATE_VIDEO_TOL = 0.60`.**
4. **Punta a punta sobre 84 celdas:** de 12 patológicas que salían `ok_parcial`,
   **8 pasan a `fallo`** y 4 quedan declaradas no evaluables. **0 falsos
   positivos sobre las 72 legítimas y 0 de 53 salidas del patrón oro movidas.**
5. **N25 — la medida de H2 se reproduce y su CIFRA no.** `gpu.Lock` tomar+soltar
   da **1 341,1 µs** frente a sus 1 403,6 (−4,5 %), pero su parche usa
   `with gpu.Lock(...)`, y `__enter__` llama a `guardia()`: **47 482,6 µs**,
   **×35,4** lo que su informe le atribuye — y contradice a su propia §6.3.
   Aplicado con la guardia **fuera de la reentrada**.
6. **N22 — `.pdb` no son dos formatos: es un CONTENEDOR de Palm con al menos
   TRES tipos**, y el motivo por el que se dejó fuera era cierto midiendo otra
   cosa: los 32 primeros bytes de un PalmDB **son el nombre del fichero**. El
   marcador está en el byte 60. **Se gana detección** — al revés que `vips:mat`.
7. **Coste de huella, MEDIDO y NO resondeado:** el componente `contrato` pasa de
   `38626025e73df9e1` a `9beb191c5479d72e` y **caduca en los 5 motores**; el
   grafo baja de **210 `real` / 5 `nominal`** a **57 / 3 / 155 `sin_sondear`**.
   `filex/nucleo.py` **no está en ninguna huella**: N25 no caduca nada.

---

## 1. Método y confinamiento

- Directorio desechable en `%TEMP%`, **listado antes y después** (R21). Primera
  pasada: 6 ficheros antes, **60 aparecidos, 0 no pedidos**. Segunda: 66 antes,
  **28 aparecidos, 0 no pedidos**. Se borra al terminar; nada binario se versiona.
- Topes: `-t`/`-frames:v` no hacen falta porque ninguna orden usa filtros de
  flujo infinito, pero **todo `subprocess` lleva `timeout` explícito** (900 s los
  codificados, 300 s las sondas) y `stdin=DEVNULL`. Ningún huérfano.
- Contenedor para N22: `docker ps -a` antes y después (6 contenedores, los
  mismos), `--name` único por invocación (`n4-pdb-1`..`n4-pdb-8`), y
  **`--rm --init --entrypoint timeout -k 5 N`** — con `--init`, que sin él son
  `rc=125` y cero bytes (trampa 71).
- **Testigos de ruido**, los dos, con tope propio de 20 s. La tanda de §3 se
  repitió: la primera corrió **con mi propia campaña de codificación encima** y
  la segunda no. Se publican las dos, y la comparación con H2 usa la segunda.
- La suite y el patrón oro corren con el corpus de LFS restaurado
  (`git lfs checkout`; `tipico.png` = 42 855 B, trampa 34).

### 1.1 Una trampa del worktree que costó una tanda entera

**Las 53 salidas del patrón oro NO se versionan** (`CLAUDE.md` §6: no se
versionan salidas binarias regenerables), así que en un *worktree* nuevo
`bench/salidas-referencia/` solo tiene `MANIFIESTO.md` y `referencia.json`.
`bench/salidas-verificacion/trabajos.py` construye las rutas contra su propia
`RAIZ`, que en un worktree es el worktree, y la primera pasada del arnés devolvió

```
[antes] 53 salidas en 88 ms | FALSOS POSITIVOS 52 | contrato {'fallo': 53}
```

**53 `fallo` con reglas `G1`/`G2` y 52 «falsos positivos» sin que nadie hubiera
tocado una línea de código.** Es la trampa 34 sobre otro activo. `referencia.json`
ya trae la ruta ABSOLUTA de cada salida y ahí sí existen: `regresion_53_n4.py`
remapea por nombre base y reproduce el veredicto publicado **al detalle**
(`ok 39 · aviso 3 · ok_parcial 10 · fallo 1`, fidelidad `37/8/8/0`).

---

## 2. N24 — el bitrate de vídeo

### 2.1 El hueco es real y su CAUSA no era la que se publicó — MEDIDO

`hito2-nvenc.md` §4.3 dice, y es cierto, que `verificador.py` *«compara
`bitrate_bps` **solo contra pistas de AUDIO** (`x["tipo"] == "audio"`). No existe
regla de bitrate de vídeo»*. Reproducido: las 8 celdas de NVENC salen `ok`.

**Pero quitar ese filtro no habría producido una sola comparación**, porque la
clave no existe en las pistas de vídeo. `bench/salidas-bitrate/dbg_sonda.py`,
misma entrada, cuatro contenedores:

| destino | códec | `pista.bitrate_bps` (vídeo) | `sonda.bitrate_bps` (contenedor) |
|---|---|---|---:|
| `.mp4` | libx264 | **`None`** | 970 041 |
| `.mkv` | libx264 | **`None`** | 969 064 |
| `.webm` | libvpx-vp9 | **`None`** | 697 393 |
| `.mov` | libx264 | **`None`** | 969 956 |

Y no es de la sonda en proceso: **`sondear_subproceso` tampoco lo publica**, y se
ve en su propio código — la rama `t == "video"` asigna `ancho`, `alto`, `fps` y
`profundidad_bits` y **no** `bitrate_bps`; solo la rama de audio lo hace. Lo
mismo vale para las pistas de audio dentro de un contenedor: `tipico.mp4` y
`patologico_2pistas.mkv` devuelven `bitrate_bps = None` en **todas** sus pistas,
así que **la regla de bitrate de audio que sí existe tampoco puede dispararse
sobre un vídeo**; solo actúa sobre ficheros de audio sueltos.

Es la trampa 58 exacta: *el hecho era cierto y la causa estaba un nivel más
abajo*. Quien hubiera «arreglado el filtro» habría escrito código para un
problema que no existía y habría dejado el que sí.

### 2.2 La campaña — 84 celdas, y las tres variables que la trampa manda variar

| eje | valores | por qué |
|---|---|---|
| codificador | `libx264`, `libx265`, `libsvtav1`, `libvpx-vp9` | **trampa 78**: un umbral calibrado con un motor describe a ese motor |
| fuente | `trivial.mp4` (640×480, 5 s, **sin audio**), `patologico_2pistas.mkv` (1280×720, 10 s, **2 audios**), `tipico.mp4` (1920×1080, 20 s, 1 audio) | **trampa 50**: varía la entrada |
| contenedor | `.mkv` y `.mp4` | dos muxers, dos sobrecargas |
| tasa pedida | 200 k, 500 k, 1 M, 2 M, 4 M, 8 M | **trampa 76**: un desvío sin su tasa no es un número |

**72 celdas legítimas** por `FileX.convertir` con la GPU vetada (`gpu._CACHE`
precargado a `False`, el idioma de `pruebas/test_hito2.py`: no toca la tarjeta ni
su lock) y **12 patológicas**, fabricadas para que el motor **ignore** la
petición: `-crf 51` declarando 4 Mbps, `-crf 10` declarando 300 kbps, y codificar
a ×0,1 y ×10 de lo declarado.

**El instrumento** (trampa 62): la verdad de campo del bitrate de vídeo se saca
sumando los PAQUETES (`ffprobe -show_entries packet=codec_type,size`). Eso
recorre el fichero entero y **el contrato no lo puede hacer**: sirve como vara,
no como sonda.

**Una celda mal montada, registrada como tal** (trampa 38): la primera pasada
mandó `2pistas` a `.mkv`, y `.mkv → .mkv` no tiene camino. **24 celdas en blanco
con `veredicto=None` y sin un solo error por pantalla.** Se repitieron contra
`.mp4`, que de paso varía el contenedor.

### 2.3 El desvío legítimo es enorme, y depende de la FUENTE más que del motor

Sobre la verdad de campo (`desvio_real`), 72 celdas legítimas:

| códec | n | peor por abajo | peor por arriba |
|---|---:|---:|---:|
| `libsvtav1` | 18 | −45,24 % (`trivial` @8 M) | **+56,30 %** (`trivial` @1 M) |
| `libx264` | 18 | **−47,65 %** (`trivial` @8 M) | +2,32 % |
| `libx265` | 18 | −38,07 % (`trivial` @8 M) | +2,19 % |
| `libvpx-vp9` | 18 | **−54,83 %** (`trivial` @8 M) | +7,83 % |

| fuente | n | recorrido |
|---|---:|---|
| `trivial` (640×480, 5 s) | 24 | **−54,83 % .. +56,30 %** |
| `2pistas` (1280×720, 10 s) | 24 | −38,58 % .. +20,11 % |
| `tipico` (1920×1080, 20 s) | 24 | −33,62 % .. +7,83 % |

**El desvío grande no es del codificador: es de la ENTRADA.** Los cuatro peores
«por abajo» son la misma celda —pedirle 8 Mbps a un 640×480 de 5 segundos que no
los llena— y el peor «por arriba» es el mismo fichero pequeño con SVT-AV1. Sobre
1080p los cuatro codificadores clavan la tasa dentro del ±7 %.

Y el corolario para H2: **los +24,59 % de `hevc_nvenc` a 1 Mbps están cómodamente
dentro del rango legítimo de los codificadores de CPU.** Una tolerancia del 15 %
como la de la regla de audio daría **19 falsos positivos de 72**.

### 2.4 ¿Existe umbral? Sobre la observable buena SÍ; sobre la que hay, NO

`desvio_real` — la que el contrato **no tiene**:

| |desvío| máximo legítimo | mínimo patológico | |
|---:|---:|---|
| **+56,30 %** | **+89,40 %** | hueco de **33,09 puntos** |

`desvio_contenedor` — la única en proceso:

| |desvío| máximo legítimo | mínimo patológico | |
|---:|---:|---|
| **+106,13 %** | **+82,13 %** | **SE SOLAPAN** |

**El solape lo fabrica el audio, y se mide:** con el mismo pedido de 2 Mbps,

| fuente | `n_audio` | vídeo real | contenedor | delta | lo que la sonda sabe del audio |
|---|---:|---:|---:|---:|---|
| `trivial` | 0 | 1 783 387 | 1 786 182 | **+2 795** | — |
| `tipico` | 1 | 2 008 438 | 2 101 675 | **+93 237** | `[None]` |
| `2pistas` | 2 | 1 993 825 | 2 187 118 | **+193 293** | `[None, None]` |

Sobre 200 kbps pedidos, esos 193 293 bps de audio son **+96 %** de sesgo en una
conversión perfectamente buena: `2pistas → .mp4` a 200 kbps da **+95,17 %
(x264)**, **+98,10 % (x265)**, **+101,11 % (vp9)** y **+106,13 % (svtav1)** de
`desvio_contenedor`. **Y la sonda no puede restarlo: publica `None`.**

### 2.5 La regla que SÍ se puede escribir, y su tabla de meseta

La asimetría no es prudencia, es una desigualdad: **el audio solo suma**, luego

```
bitrate_video  ≤  bitrate_contenedor
```

- **Por abajo vale siempre.** Si el contenedor ya se queda corto, el vídeo se
  queda corto seguro. Ninguna pista de audio puede fabricar un falso positivo.
- **Por arriba solo es decidible sin audio.** Con audio se declara
  `informativo`, que es lo que este verificador hace donde no se puede saber.

**La tabla, sobre `desvio_contenedor`** (trampa 51: qué atrapa y qué rompe en
cada candidato):

| umbral | ABAJO (72 legítimas) fp / atrapadas de 6 | ARRIBA sin audio (24 legítimas) fp / atrapadas de 2 |
|---:|---|---|
| 25 % | 10 de 72 / **6 de 6** | 4 de 24 / 2 de 2 |
| 40 % | 3 de 72 / **6 de 6** | 3 de 24 / 2 de 2 |
| 50 % | 1 de 72 / **6 de 6** | 1 de 24 / 2 de 2 |
| **60 %** | **0 de 72 / 6 de 6** | **0 de 24 / 2 de 2** | ← **borde de abajo de la meseta** |
| 75 % | 0 de 72 / 6 de 6 | 0 de 24 / 2 de 2 | ← meseta |
| 100 % | 0 de 72 / **0 de 6** | 0 de 24 / 2 de 2 |
| 150 % | 0 de 72 / 0 de 6 | 0 de 24 / **1 de 2** |

Subir de 60 a 75 **no atrapa ni una celda más**; bajar a 50 compra **dos falsos
positivos por cero detección**. `BITRATE_VIDEO_TOL = 0.60`.

Márgenes: **5,21 puntos** sobre el peor legítimo por abajo (−54,79 %) y **3,43**
por arriba sin audio (+56,57 %); **22,13 puntos** por debajo del patológico menos
malo por abajo (−82,13 %) y **59,33** por arriba (+119,33 %).

**No hay meseta para un segundo nivel de `aviso` más estricto**: por debajo del
60 % todos los candidatos ya cuestan falsos positivos. La regla tiene **un
nivel**, al revés que la de audio (15 % aviso / 50 % fallo).

### 2.6 Punta a punta por `verificar()`, antes y después — MEDIDO

`bench/salidas-bitrate/verificar_v10.py`, las 84 celdas por el contrato entero,
con el verificador de `HEAD` y con el del árbol:

| | antes (`HEAD`) | **después** |
|---|---|---|
| legítimas (72) | `ok_parcial` 72, **0 hallazgos V10** | `ok_parcial` 72 · **0 falsos positivos** · 4 con `informativo` |
| patológicas (12) | `ok_parcial` 12, **0 hallazgos V10** | **`fallo` 8** · `ok_parcial` 4 con `informativo` |

Las **4 que no atrapa son exactamente la familia declarada**: sobrepasar la tasa
**con pistas de audio** (`2pistas` y `tipico`, `crf10_supra` y `diez_veces_mas`).
No se esconden: salen con un hallazgo que dice por qué no es evaluable.

### 2.7 Cero falsos positivos sobre las 53, antes y después — MEDIDO

```
[antes]   53 salidas | FALSOS POSITIVOS 0 | contrato {ok 39, aviso 3, ok_parcial 10, fallo 1}
                                          | fidelidad {ok 37, aviso 8, ok_parcial 8, fallo 0}
[despues] 53 salidas | FALSOS POSITIVOS 0 | contrato IDÉNTICO | fidelidad IDÉNTICA
--diff -> 0 de 53 salidas cambian de veredicto o de reglas.
```

Ni una se mueve, y el motivo es estructural: **ninguna de las 53 lleva
`bitrate_video_bps` en su pedido**, porque esa clave la introdujo `motores.py` en
el hito 2 y el patrón oro es de agosto. V10 no puede dispararse ahí.

### 2.8 Lo que esta regla NO cubre, dicho con nombre

- **Sobrepasar la tasa con audio** (4 de 12 celdas patológicas). Se cierra en
  cuanto la sonda —o el `decidido` del motor— publique el bitrate del audio.
  `motores.FFmpeg` **ya lo sabe**: escribe `-b:a 128k` en el `argv`. Bastaría con
  meterlo en `decidido` como `bitrate_audio_bps` y restarlo aquí. **`motores.py`
  no es mío; queda PENDIENTE y acotado.**
- **NVENC no se ha medido en esta ronda.** Las cuatro filas de `hevc_nvenc` son
  de H2. La regla se ha comprobado contra ellas *como datos* —ninguna sale
  `fallo`, prueba propia—, no contra la tarjeta.
- **La clase patológica es fabricada por mí**, cuatro familias. No hay ni un
  motor real que ignore la tasa en este corpus; el precedente que lo motiva
  (ConvertX entregando 64 kbps por 192) es de audio.
- **El umbral se calibró con `duracion_s` fiable.** Sobre un fichero cuya
  duración declarada no es la real, `bytes·8/duración` miente y V10 con él. Esa
  familia la cubre la regla de truncados (trampa 46), no ésta.

---

## 3. N25 — el lock rodea al codificado, y el parche de H2 cuesta ×35

### 3.1 La medida ajena, reproducida ANTES de tocar nada (trampa 58)

Dos tandas. La primera corrió **con mi propia campaña de codificación encima** y
está publicada solo para que se vea la diferencia; la comparación con H2 usa la
segunda, con los dos testigos limpios (deriva ×1,018, nivel 29,85→29,13 ms).

| pieza | H2 §6.3 | **tanda 1 (con ruido propio)** | **tanda 2 (limpia)** | n |
|---|---:|---:|---:|---:|
| `gpu.Lock` tomar+soltar | 1 403,6 µs | 2 180,3 µs | **1 341,1 µs** *(−4,5 % de H2)* | 21 |
| `guardia()` (`nvidia-smi`) | 46,3 ms | 47,26 ms | **46,86 ms** *(+1,2 %)* | 9 |
| **`with gpu.Lock(...)`** | *(no publicado)* | 48,67 ms | **47,48 ms** | 9 |
| `gpu.usa_gpu(argv)` | — | 1,3 µs | **0,9–1,0 µs** | 201 |

**Las dos cifras de H2 se reproducen.** Etiqueta `SUCIA`, estructural.

### 3.2 Y su parche no cuesta lo que dice — REFUTADO

§6.5 propone, literalmente:

```python
ctx = gpu.Lock(f"filex-{arista.motor}") if gpu.usa_gpu(argv) else contextlib.nullcontext()
with ctx:
    r = invocacion.ejecutar(argv, timeout=timeout, cwd=t.ruta)
```

y lo tasa en *«1 403,6 µs por conversión que use la tarjeta —el 0,19 % de una
conversión NVENC de 5 s»*. **`Lock.__enter__` no es `tomar()`**: llama a
`tomar()` **y después a `guardia()`**, que lanza `nvidia-smi`. El coste real del
parche tal como está escrito es **47 482,6 µs**:

| | µs | sobre los 753,5 ms de una conversión NVENC de 5 s (H2 §6.3) |
|---|---:|---:|
| lo que H2 publicó | 1 403,6 | 0,19 % |
| **lo que el parche cuesta** | **47 482,6** | **6,30 %** |
| ratio | | **×35,4** |

Y el error no es de aritmética: **contradice a la propia §6.3 de H2**, que dice
*«preguntar por la VRAM en cada conversión sería caro; por eso la guardia se
aplica al tomar el lock, una vez por tanda, y no por fichero»*. Su parche la
aplica por fichero — y también **dentro de un lote que ya tiene el lock**,
porque `__enter__` llama a `guardia()` aunque `tomar()` haya salido por la
reentrada.

### 3.3 Lo aplicado, y por qué no es `with gpu.Lock(...)`

`filex/nucleo.py` gana `_lock_gpu(etiqueta, argv)`, un gestor de contexto que:

1. si `gpu.usa_gpu(argv)` es falso, **no toca nada** — 0,9 µs, el coste de un
   `any()` sobre el `argv`;
2. si es cierto, toma el lock con el tope de `FILEX_GPU_ESPERA`;
3. **llama a `guardia()` solo si el proceso NO tenía ya el lock** (`gpu.poseido()`),
   que es lo que la §6.3 de H2 prescribe y su parche incumple;
4. lo suelta en un `finally`.

`GpuOcupada` se convierte en un `Salto` con motivo, **no en una excepción que
suba**: quien pidió una conversión merece un veredicto, y «la tarjeta está
ocupada» es una respuesta.

**No se ha tocado `filex/gpu.py`** (lo lee S6) ni `filex/cerrojo.py`: el
primitivo es el de `harness.sh` (`O_CREAT|O_EXCL`), y meter el candado de rango
de bytes aquí sería media exclusión (trampa 77).

### 3.4 N25 no caduca ni una arista, y eso está comprobado, no supuesto

`huella.de_motor` tiene exactamente tres componentes: `motor` (la clase y su
MRO), `invocacion` (el fichero `invocacion.py` entero) y `contrato` (el cierre de
llamadas de `verificar`). **`nucleo.py` no es ninguno de los tres**, y hay una
prueba que lo deja escrito.

### 3.5 La prueba que falla sin el arreglo

`test_la_ejecucion_esta_DENTRO_del_with_en_el_arbol` recorre el **AST** de
`_un_salto` (trampa 42: una prueba de texto no distingue una llamada de una
mención) y **comprueba antes que la fuente compila** (trampa 60). Contra las dos
versiones:

```
ANTES (HEAD)     compila=True  ejecutar dentro de with _lock_gpu = False
DESPUES (arbol)  compila=True  ejecutar dentro de with _lock_gpu = True
```

Y `test_la_guardia_no_se_repite_en_la_reentrada` es la que separa mi parche del
de H2: con el lock ya tomado por fuera, `guardia()` **no** se vuelve a llamar.

---

## 4. N22 — `.pdb` es un contenedor, no una colisión de dos

### 4.1 El motivo de F1 era CIERTO y medía otra cosa

`firmas-cierre.md` §8.8 deja `gm:pdb` y `calibre:pdb` fuera del vocabulario con
el motivo *«el prefijo común medido es la ruta del fichero, no un marcador»*.
**Literalmente cierto**: los 32 primeros bytes de un PalmDB **son el nombre**, y
cada motor lo rellena con el nombre del fichero — el de **salida** en
ImageMagick y GraphicsMagick, el de **entrada** en Calibre:

```
0000000  67 6d 5f 75 6e 6f 2e 70 64 62 00 ...   >gm_uno.pdb......<
0000048  00 ... 00 76 49 4d 47                  >............vIMG<
0000064  56 69 65 77 ...                        >View............<
```

**El censo de prefijos comunes estaba mirando los bytes 0..31.** El marcador de
verdad son los **8 bytes 60..67**, que en PalmDB son `type` + `creator`.

### 4.2 Los escritores y sus marcadores — MEDIDO en `filex-c13`

| orden | bytes | `cab[60:68]` | testigo externo (**no el escritor**, trampa 71) |
|---|---:|---|---|
| `magick s.png im.pdb` | 156 | `vIMGView` | `magick identify` → `PDB 64x48` |
| `gm convert s.png gm.pdb` | 1 679 | `vIMGView` | `gm identify` → `PDB 64x48` |
| `ebook-convert s.txt c.pdb` | 147 | `TEXtREAd` | `ebook-meta` → `Title: s` |
| `ebook-convert s.txt c.pdb -f ereader` | 333 | `PNRdPPrs` | `ebook-meta` → `Title: s` |
| `ebook-convert s.txt c.pdb -f ztxt` | **0** | — | **`rc=1`**: este motor no lo escribe aquí |

Y la prueba de que son formatos distintos la da un tercero: **`magick identify`
sobre el `.pdb` de Calibre** responde `improper image header ...
error/pdb.c/ReadPDBImage/348`.

**No son dos formatos, son al menos tres**, y **no son dos escritores, son
cuatro**: ImageMagick escribe el mismo `vIMGView` que GraphicsMagick, así que el
enunciado *«el de GraphicsMagick»* describía a un motor de dos.

### 4.3 Aquí SÍ se gana detección — al revés que `vips:mat`

El precedente de `vips:mat` fue una cesión porque no había marcador que ganar.
Aquí lo hay: 8 bytes ASCII en un desplazamiento fijo, con significado
documentado. `firma_real` ya usaba ese sitio para `BOOKMOBI`/`TEXtREAd`; lo único
que faltaba era **la tabla en vez de la tupla**:

```python
MARCAS_PALMDB = {b"BOOKMOBI": "mobi",  b"TEXtREAd": "mobi",
                 b"vIMGView": "palm_imagen", b"PNRdPPrs": "ereader"}
```

más `("pdb", {"mobi", "palm_imagen", "ereader"})` en `EXT_A_FIRMAS`. Resultado:

| fichero | firma antes | **firma después** | `punto1_estado` antes | **después** |
|---|---|---|---|---|
| `im.pdb` | `desconocido` | **`palm_imagen`** | `sin_vocabulario` | **`evaluado`** |
| `cal_doc.pdb` | `mobi` | `mobi` | `sin_vocabulario` | **`evaluado`** |
| `cal_ereader.pdb` | `desconocido` | **`ereader`** | `sin_vocabulario` | **`evaluado`** |

**Cierra 2 de los 11 `sin_vocabulario` del contenedor** (`gm:pdb`, `calibre:pdb`)
que `firmas-cierre.md` §8.8 dejó abiertos. Los otros nueve siguen como estaban:
ocho son de la clase «el motor escribió otro formato» —que es G6, no
vocabulario— y `gm:shtml` no se ha tocado.

**Y se sigue el valor hasta donde se USA** (trampa 70): `CAT_POR_FIRMA` elige la
sonda, así que `palm_imagen → imagen` (y `magick identify` lo lee de verdad: 64
px de ancho) y `ereader → documento`, con los demás libros.

**Dos cosas que se dejan quietas y se declaran:** `TEXtREAd` sigue devolviendo
`mobi` aunque PalmDoc no sea MOBI —cambiarlo movería clasificaciones que nadie ha
pedido mover—, y `.palm` sigue en `EXT_SIN_FIRMA` como *«cabecera sin
constante»*: es otra extensión de ImageMagick y **no se ha medido**.

### 4.4 El fixture se genera, no se teclea

La primera copia a mano del base64 de `cal_ereader.pdb` perdió **6 bytes**
(327 en vez de 333) **sin que nada fallara**: el fichero seguía abriéndose y el
marcador del byte 60 seguía siendo el bueno. Es la trampa 48 en miniatura. Por
eso `muestras_pdb.py` lo genera con `gen_muestras_pdb.py` y **se autocomprueba**
al ejecutarse.

---

## 5. Impacto sobre el sondeo — MEDIDO, **no resondeado**

Tocar `verificador.py` dentro del cierre de `verificar()` **sí caduca** el
componente `contrato`, esta vez de verdad:

| | antes | después |
|---|---|---|
| `huella.de_contrato()` | `38626025e73df9e1` | **`9beb191c5479d72e`** |
| `sondeo.diagnostico()["caducados"]` | `{}` | **los 5 motores, `['contrato']`** |
| grafo | **210 `real` · 5 `nominal`** | **57 `real` · 3 `nominal` · 155 `sin_sondear`** |

**155 aristas de 215 se degradan a `sin_sondear`** (153 desde `real`, 2 desde
`nominal`). Las 60 que quedan no vienen de `filex/sondeo/*.json`, sino de
evidencia declarada en el código (`referencia.json`, `bench/salidas-hito5/`,
`bench/invocacion-aristas.md`), y por eso la huella no las toca.

**No he resondeado nada** ni he tocado `filex/sondeo/*.json`, `filex/huella.py`
ni `filex/sondeo.py`. El resondeo es de quien coordina.

Y la mitad que importa: **N25 no caduca nada** (`nucleo.py` no está en ninguno de
los tres componentes) y **N22 caduca lo mismo que N24**, porque las dos tocan el
mismo cierre. **El coste de huella de este encargo es UNO, no dos.**

---

## 6. La API pública de `bench/scripts/verificador.py`

El envoltorio aliasea en `sys.modules`, así que hay un solo objeto-módulo.
**Solo se AÑADEN nombres** (`MARCAS_PALMDB`, `BITRATE_VIDEO_TOL`) y **se cambian
dos tablas por dentro** (`EXT_A_FIRMAS["pdb"]`, dos claves nuevas en
`CAT_POR_FIRMA`). Nada se quita ni cambia de firma: los 19 arneses de `bench/`
siguen importando lo mismo.

**Aviso a quien reejecute arneses viejos:** un `.pdb` pasa de `sin_vocabulario` a
`evaluado`, y una salida de vídeo con `bitrate_video_bps` en el pedido puede
ganar un hallazgo `V10`. Es la regla nueva, no una regresión.

---

## 7. Suite

| | |
|---|---|
| antes de tocar nada | **`348 passed, 6 skipped`** (236,46 s) |
| después | **`363 passed, 6 skipped, 1 failed`** (185,18 s) |

348 + 16 nuevas = 364 = 363 + 1. `pruebas/test_bitrate_y_lock.py` añade **16
pruebas**: 8 de N24 (incluida la del mecanismo —la sonda no publica el bitrate de
vídeo— y la de que el desvío normal de NVENC no puede salir `fallo`, con las
cuatro cifras de H2), 5 de N25 y 3 de N22.

### 7.1 El único rojo, y es el esperado

```
FAILED pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado
AssertionError: {'imagemagick': ['contrato'], 'ffmpeg': ['contrato'],
                 'doc_libreoffice': ['contrato'], 'doc_pandoc': ['contrato'],
                 'doc_calibre': ['contrato']} != {}
```

Es **el centinela de la huella haciendo su trabajo** (§5): dice, con razón, que
hay que resondear. `pruebas/test_sondeo.py` es de T y **no se toca**; el resondeo
tampoco es mío. Mismo rojo que `contrato-familia-resvg.md` §8 declaró en su día
como el único esperado.

### 7.2 Dos rojos que aparecieron y NO son míos — registrado por honestidad

En una pasada intermedia salieron además
`test_hito2.py::SondeoEnEjecucion::{test_av1_nvenc_esta_listado_y_no_funciona,
test_hevc_nvenc_si_funciona}`. **Corridas solas, las cuatro de esa clase pasan**
(`4 passed in 1.18 s`), y en la pasada final también. Es el otro agente teniendo
la tarjeta: `gpu.capacidad` toma el lock de máquina con
`FILEX_GPU_ESPERA_SONDA=30`, y al agotarlo devuelve *«la tarjeta está ocupada»*
sin cachear. **Un rojo de esas dos pruebas con un vecino en la GPU no es una
regresión**, y conviene saberlo antes de perseguirlo.

### 7.3 Un fichero de otro agente tocado, y es UNA línea — declarado

`pruebas/test_firmas_cierre.py` (de F2) tenía `"mobi"` en una lista **literal** de
firmas alcanzables, precisamente porque el despacho del byte 60 era una tupla
dentro del cuerpo de `firma_real` y no una tabla que se pudiera recorrer. Con
`MARCAS_PALMDB` la lista se deriva:

```python
posibles |= set(V.MARCAS_PALMDB.values())    # y se quita "mobi" del literal
```

Sin eso, la prueba
`test_ninguna_extension_espera_una_firma_INALCANZABLE` da
`['ereader', 'palm_imagen'] != []`. **Es exactamente lo que esa prueba defiende**
—una entrada literal es una entrada que se queda atrás sola—, pero el fichero no
es mío: si F2 prefiere otra forma, el cambio está en un solo sitio y comentado.

---

## 8. Pendientes que dejo abiertos

1. **El lado de arriba de V10 con audio** (§2.8). Se cierra metiendo
   `bitrate_audio_bps` en el `decidido` de `motores.FFmpeg`, que ya conoce el
   valor. **4 de 12 celdas patológicas** dependen de eso.
2. **La sonda no publica el bitrate de ninguna pista de un contenedor**, ni de
   vídeo ni de audio (§2.1). Consecuencia que nadie había escrito: **la regla de
   bitrate de audio del punto 4 solo actúa sobre ficheros de audio sueltos**.
   Nadie la ha medido sobre un `.mkv` con audio.
3. **NVENC contra V10, en la tarjeta.** Las cuatro celdas de H2 se han usado como
   datos; no se han vuelto a producir.
4. **El umbral de aborto de `GPU_GUARD` sigue calibrado para otro régimen**
   (H2 §6.4: NVENC cuesta ~211 MiB y el umbral aborta a 6 000 libres). Ahora que
   el lock rodea al codificado, ese umbral **decide conversiones**, no solo
   sondeos. Sin medir.
5. **`.palm` de ImageMagick** sigue en `EXT_SIN_FIRMA` sin muestra (§4.3).
6. **`ebook-convert -f ztxt` da `rc=1` y 0 bytes** en `filex-c13`. No se ha
   averiguado por qué; el `rc` queda registrado (trampa 72).
7. **La clase patológica de §2.2 es fabricada.** Un motor real que ignore la tasa
   de vídeo cerraría la calibración de verdad.

---

## 9. Ficheros

**Código tocado:** `filex/verificador.py` · `filex/nucleo.py` ·
`pruebas/test_bitrate_y_lock.py` (míos) · **`pruebas/test_firmas_cierre.py`, una
línea, declarada en §7.3** (de F2).

**Arneses y resultados** (`bench/salidas-bitrate/`, todo texto):

| fichero | qué es |
|---|---|
| `dbg_sonda.py` | la sonda que destapa que el bitrate de vídeo no existe |
| `calibrar_bitrate.py` · `calibracion.json` · `calibracion_2pistas.json` | las 84 celdas |
| `analizar_bitrate.py` | las tablas de meseta y de solape |
| `verificar_v10.py` · `v10_antes.json` · `v10_despues.json` | el contrato entero sobre las 84 |
| `regresion_53_n4.py` · `regresion_antes.json` · `regresion_despues.json` | las 53 del patrón oro |
| `medir_lock.py` · `medicion_lock.json` · `medicion_lock_tanda1.json` | N25 |
| `muestras_pdb.py` · `gen_muestras_pdb.py` | N22 |
| `MANIFIESTO.md` | cómo se reproduce todo |

---

## 10. NO APLICADAS — trampas propuestas para `CLAUDE.md`, 86 a 89

> **86. Una regla que no se puede escribir puede no ser una regla que falta, sino
> un DATO que no existe — y hay que sondear la sonda antes de calibrar nada —
> MEDIDO** (`bench/bitrate-y-lock.md` §2.1). `hito2-nvenc.md` §4.3 denunció que
> el contrato compara el bitrate *«solo contra pistas de AUDIO»*
> (`x["tipo"] == "audio"`), y el hecho era cierto. Quitar ese filtro **no habría
> producido ni una comparación**: ni la sonda en proceso ni
> `ffprobe -show_streams` publican el `bitrate_bps` de una pista de VÍDEO —4
> contenedores de 4 con `None`, y en `sondear_subproceso` se ve en el código: la
> rama de vídeo no asigna esa clave—. Y arrastra un segundo hallazgo que nadie
> había escrito: **tampoco la publican para las pistas de AUDIO dentro de un
> contenedor**, así que la regla de bitrate de audio que sí existe **solo actúa
> sobre ficheros de audio sueltos**. Es la trampa 58 en su forma más cara: el
> arreglo obvio habría sido código para un problema inexistente. **Antes de
> calibrar un umbral sobre una magnitud, comprueba que la sonda la publica —en
> los contenedores que te importan, no en el que probaste.**

> **87. Cuando la magnitud que quieres juzgar viene MEZCLADA con otra, la
> desigualdad decide qué mitad de la regla es escribible — MEDIDO** (ídem §2.4,
> §2.5). Sobre el bitrate del CONTENEDOR, las clases legítima y patológica **se
> solapan** (legítimo hasta +106,13 %, patológico desde +82,13 %): no hay umbral
> bilateral, y el solape entero lo fabrica el audio —**+193 293 bps** en un
> fichero de dos pistas, con la sonda devolviendo `[None, None]`—. Pero el audio
> solo **SUMA**, así que el contenedor es cota **superior** del vídeo y **el lado
> de abajo es sano para siempre**: 0 falsos positivos sobre 72 celdas. **Antes de
> retirar un umbral por solape, mira si la contaminación tiene SIGNO: media regla
> demostrable vale más que una regla entera calibrada a ojo** — y la otra media
> se declara `informativo`, no se adivina. Con la meseta tabulada (trampa 51) en
> 60–75 % por los dos lados.

> **88. Un parche ajeno «de una línea» puede llamar a algo que su propio informe
> declaró caro, y el ratio no se ve hasta que se cronometra la línea entera —
> MEDIDO** (ídem §3.2). `hito2-nvenc.md` §6.5 deja escrito
> `with gpu.Lock(...)` y lo tasa en **1 403,6 µs, el 0,19 %** de una conversión.
> Reproducido: `tomar()+soltar()` da **1 341,1 µs** (−4,5 %, la medida es buena),
> pero `Lock.__enter__` llama además a `guardia()` —`nvidia-smi`, **46,9 ms**— y
> el `with` entero cuesta **47 482,6 µs: ×35,4**. Y el aviso estaba en el mismo
> informe, dos secciones antes: *«preguntar por la VRAM en cada conversión sería
> caro; por eso la guardia se aplica una vez por tanda y no por fichero»*. **La
> trampa 58 dice «reproduce la medida antes de arreglar»; ésta añade: reproduce
> la medida DEL PARCHE, no la de la pieza que el parche nombra** — y cuando un
> informe se contradiga entre dos secciones, gana la que trae número.

> **89. Las 53 salidas del patrón oro NO EXISTEN en un worktree nuevo, y el arnés
> que las juzga devuelve 52 falsos positivos sin que nadie haya tocado el código
> — MEDIDO** (ídem §1.1). Es la trampa 34 sobre otro activo y con peor disfraz:
> el corpus da `improper image header` y se ve, pero
> `bench/salidas-referencia/` **solo tiene `MANIFIESTO.md` y `referencia.json`**
> porque las salidas binarias no se versionan (§6), y `trabajos.py` las
> reconstruye contra su propia `RAIZ` — que en un worktree es el worktree. El
> resultado es `contrato {'fallo': 53}` con reglas `G1`/`G2`, que es exactamente
> la pinta de haber roto el verificador. **`referencia.json` ya trae la ruta
> ABSOLUTA de cada salida**: se remapea por nombre base y el veredicto publicado
> se reproduce al detalle. **Antes de creerte un rojo en un worktree, mira si el
> activo que juzgas está versionado** — y si un arnés compara contra ficheros que
> el repositorio no guarda, que lo diga al empezar y no al fallar.
