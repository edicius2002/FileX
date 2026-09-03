# `C28`-barato cerrado, y `C16` con un número medido gracias a FATE

**Encargo R11 · worker2, carril CPU/Docker, `edicius2002/filex-cpu`.** Orden pedido:
lo barato de `C28` (los 8 `sin_clasificar` + los 17 de 23 sin probar) antes de tocar
FATE; luego `C16` con FATE. Las dos primeras filas están enteras; la tercera (los 56
que ningún motor escribe) se deja fuera — el porqué, en §3.

**Máquina:** *worktree* `C:\Users\krato\orca\workspaces\FileX\filex-cpu`. Windows 10,
Python 3.11.9. **worker1 tiene la tarjeta** en el carril GPU de la ronda 11 (`N31`,
`N26`): no se tocó. CPU al **48 %** (`wmic cpu get loadpercentage`) durante la tanda —
carga moderada, compartida con worker1. Docker (`29.4.3`) arriba con
`filex-convertx`, `filex-snapotter(+pg,+redis)` y `filex-gotenberg8` sanos, 12 h de
uptime, comprobado antes de tocar nada. **El corpus FATE**
(`D:\Work\research\fate-suite`, 1,3 GB, 2 529 ficheros, 303 subdirectorios) se
referenció por ruta absoluta y no se copió, no se versionó, no entró en `corpus/`.

**Fecha:** 03/09/2026.

---

## 1. `C28`-barato: los 8 `sin_clasificar` y 17 de los 23 sin probar

### 1.1 Los 8 `sin_clasificar` — el `stderr` truncado, reproducido entero

`firmas-cierre.md` §4.4 diagnosticó la causa sin resolverla: el censo original
(`_censo_firmas.py::corre()`) guarda sólo `(p.stderr or "")[-400:]`. Los 8 formatos
—`8bimwtext`, `app1jpeg`, `clip`, `iptcwtext`, `jpt`, `mask`, `matte`, `thumbnail`—
se reprodujeron con la MISMA invocación (`magick <entrada> -auto-orient <salida>`,
la misma semilla `a1.png` de 64×48 con ruido aleatorio), esta vez sin truncar. Un
control aparte confirma que JPEG2000 escribe bien en esta build (`.jp2`, `rc=0`,
20 351 B) — para aislar «esta build no tiene JP2» de «esta variante de JP2 falla».

**Resultado, en tres clases — MEDIDO:**

| Formato | `rc` | Mensaje completo | Clase real |
|---|---:|---|---|
| `clip` | 1 | *«image does not have a clip mask»* | metadato/canal ausente EN LA ENTRADA |
| `mask` | 1 | *«image does not have an mask channel»* | metadato/canal ausente EN LA ENTRADA |
| `matte` | 1 | *«image does not have an alpha channel»* | metadato/canal ausente EN LA ENTRADA |
| `thumbnail` | 1 | *«image does not have a EXIF thumbnail»* | metadato/canal ausente EN LA ENTRADA |
| `jpt` | 1 | *«unable to encode image file»* (`error/jp2.c/WriteJP2Image/1271`) | el delegado JP2 no admite ESTA variante (control: `.jp2` sí funciona) |
| `8bimwtext` | **0** | *(vacío: ni stdout, ni stderr, ni fichero)* | silencio doble — ver 1.1.1 |
| `app1jpeg` | **0** | *(ídem)* | silencio doble |
| `iptcwtext` | **0** | *(ídem)* | silencio doble |

**4 de 8 (`clip`, `mask`, `matte`, `thumbnail`) son la MISMA clase que el bucket ya
existente «metadato, no formato»** (8 formatos: `8bim`, `app1`, `exif`, `icc`, `icm`,
`iptc`, `iptctext`) **— el regex que los clasificaba no los alcanzaba, no porque la
causa fuera distinta.** El patrón `No (8BIM|APP1|IPTC|color profile|EXIF)[^.]* data
is available` exige la frase «data is available»; ImageMagick fraseó estos cuatro
como «does not have a/an X», con el mismo significado (el canal/perfil/máscara no
está en la imagen de origen) y otra gramática. **El bucket «metadato, no formato»
pasa de 8 a 12; el remedio es el mismo: una entrada que lleve ese dato.**

**1 de 8 (`jpt`) es una clase nueva: el delegado SÍ existe pero no esta variante.**
No es «falta una entrada»: es que el propio código de escritura de JP2
(`error/jp2.c/WriteJP2Image`) rechaza el perfil `jpt` con una build que sí escribe
`.jp2` sin problema. Más cerca de «otro motor u otra build» que de «metadato».

#### 1.1.1 El hallazgo que no estaba en el pendiente: silencio doble

**3 de 8 (`8bimwtext`, `app1jpeg`, `iptcwtext`) no tienen mensaje que capturar
porque no hay ERROR: hay un `rc=0` que no escribe absolutamente nada** — ni el
fichero pedido, ni `sal-0.ext`, ni una línea de stdout o stderr. Rastreando de dónde
salió el `sin_clasificar` original: **estos tres NO están en el censo LOCAL de
ImageMagick** (`firmas_censo_local.json` no los tiene), **vienen del censo del
CONTENEDOR, y del motor `graphicsmagick`**, que sí falla — con `rc=1` y **error
completamente vacío** (`"errores": ["rc=1 "]`, literal). Es decir: **GraphicsMagick
falla en silencio (`rc=1`, cero explicación) e ImageMagick local «tiene éxito» en
silencio (`rc=0`, cero bytes escritos).** Ninguno de los dos motores da una pista
utilizable; el `rc=0` de ImageMagick es el más peligroso de los dos porque **un
`rc=0` sin verificar el fichero de salida se leería como conversión correcta** — es
la misma familia de fallo que motiva el punto 5 del contrato (verificar lo que el
motor ESCRIBIÓ, no lo que declaró). Queda **PENDIENTE** sondear si hay una bandera
de ImageMagick que lo haga fallar en vez de callar; no se ha buscado esta ronda.

### 1.2 Los 17 de 23 «con invocación mejor» — sondeados, no deducidos

`firmas-cierre.md` §4.4 ya había escrito 6 de las 23 (`h261`, `h263`, `dnxhd`, `dts`,
`mlp`, `thd`). Quedaban 17: 15 `EINVAL` (`302`, `amv`, `avs2`, `chk`, `dnxhr`, `gxf`,
`js`, `mmf`, `rco`, `roq`, `sup`, `tco`, `tun`, `vbn`, `xface`) + 2 `AVERROR_INVALIDDATA`
(`dv`, `flm`). El censo sólo guardaba la ETIQUETA del `rc`, no la restricción real
—**sondeado en ejecución** con `ffmpeg -h muxer=X` / `-h encoder=X` antes de escribir
una sola línea de invocación, no deducido de la documentación.

**14/17 escritos de verdad, con DOS semillas cada uno y prefijo común estable —
MEDIDO, mismo método que `_c28_prueba21.py`:**

| Formato | Restricción real (sondeada, no adivinada) | Prefijo estable |
|---|---|---:|
| `302` (daud) | **exactamente 6 canales** a **96 000 Hz** — dos restricciones encadenadas, cada una descubierta al arreglar la anterior | 10 B |
| `amv` | **2 streams obligatorios** (vídeo+audio) + audio a **22 050 Hz** + `-block_size 882` (el propio ffmpeg lo sugiere: *«Try -block_size 882»*) | 64 B |
| `avs2` | vídeo puro, **sin** pista de audio (el muxer no la admite) | 64 B |
| `dnxhr` | perfil DNxHR explícito (`dnxhr_hq`) + `yuv422p` | 64 B |
| `gxf` | geometría PAL (720×576) + `mpeg2video`/`pcm_s16le` explícitos | 64 B |
| `mmf` | 44 100 Hz exacto (una semilla nacía a 48 000 y el muxer la rechazaba) | 64 B |
| `rco`, `tco` | `g723_1` a 8 000 Hz — **mismo fix que `C25`, ronda 9** | 0 B (raw, sin cabecera — esperado) |
| `roq` (vídeo) | `yuvj444p` explícito (el `roq_dpcm`/22 050 Hz de audio ya estaba fijado en `C25`) | 26 B |
| `tun` (alp) | **22 050 Hz exacto** — *«Sample rate must be 22050 for TUN files»* | 16 B |
| `vbn` | códec y `pix_fmt` explícitos (`image2` adivinaba mal el códec por defecto) | 64 B |
| `xface` | **48×48 fijo** + `pix_fmt monow` (el encoder sólo admite ese formato de píxel) | 0 B (raw, esperado) |
| `dv` | NTSC 720×480@29,97 + `yuv411p` | 64 B |
| `flm` (filmstrip) | `pix_fmt rgba` explícito | 0 B (raw, esperado) |

Cuatro (`rco`, `tco`, `xface`, `flm`) dan **prefijo común de 0 bytes: son formatos
crudos sin cabecera, y eso es lo esperado, no un fallo** — la misma conclusión que
`C25` ya midió para `g723_1`. Los otros 10 dan cabecera estable de 10 a 64 bytes.

**2/17 no tienen invocación que arreglar: esta build de ffmpeg NO TRAE el códec.**
`ffmpeg -h encoder=jacosub` y `-h encoder=hdmv_pgs_subtitle` responden los dos *«no
encoders for it are available»*. **`js` y `sup` estaban mal encasillados como
`EINVAL`** (el fallo real ocurre al intentar abrir un encoder inexistente para un
stream OBLIGATORIO, y eso se manifiesta como `Invalid argument` en vez del
`AVERROR_ENCODER_NOT_FOUND` textual que dan los codecs opcionales) **y en realidad
pertenecen a la MISMA clase que los 11 `AVERROR_ENCODER_NOT_FOUND` ya conocidos: otro
motor u otra build, no una bandera.** Es un refinamiento real del reparto de
`firmas-cierre.md` §4.4, no una revisión cosmética.

**1/17 (`chk`, `webm_chunk`) no es una bandera: es OTRO PARADIGMA de invocación.**
Exige fragmentar la salida en varios ficheros (`chunk_start_index`, un fichero de
cabecera aparte) — no hay forma de resolverlo con un `-c:v`/`-s` porque el propio
CONTRATO de "un fichero de salida" no aplica a este muxer. Se declara aparte y no se
fuerza dentro del molde de las demás 16.

### 1.3 Balance de `C28`-barato

**22/25 celdas de esta mitad quedan cerradas con evidencia directa** (14 invocaciones
escritas + 4 reclasificadas al bucket de metadato + 1 reclasificada a delegado
insuficiente + 3 diagnosticadas con el mecanismo exacto del silencio doble). Quedan
**2 en el bucket "otro motor/build" ampliado** (`js`, `sup`) y **1 en un paradigma de
invocación no cubierto** (`chk`). Ninguna necesitó FATE.

---

## 2. `C16` — el 54,78 % indeterminado: un número medido, no una muestra de las 2 529

### 2.1 Qué se mide y por qué no las 2 529 celdas

Las 75 874 aristas «indeterminadas» lo son porque su formato de ORIGEN es uno de los
**445** que **ningún motor local sabe ESCRIBIR** (`bench/salidas-aristas/
semi_entrada.json`+`semi_entrada2.json`, `estado == "no_materializable"`: 359 de
ffmpeg + 86 de ImageMagick). Sin poder fabricar un fichero de ese formato, la
semiarista de ENTRADA nunca se pudo probar. FATE resuelve exactamente esa carencia:
son ficheros REALES, no fabricados por el propio motor que luego los leería (lo que
sería el sesgo favorable ya declarado en `aristas-nominales.md` §2.2).

**No se han sondeado los 445**, y no hace falta: se toma una **muestra estratificada
por disponibilidad** — los formatos cuyo NOMBRE de directorio en FATE coincide con el
nombre del formato — y se declara exactamente ese sesgo, no se esconde.

### 2.2 El emparejamiento, y su sesgo declarado

**69 de los 445 (15,5 %) tienen un subdirectorio en FATE con el mismo nombre**: 68 de
ffmpeg, 1 de ImageMagick (`heif`). **Es un sesgo de COBERTURA, no una muestra
aleatoria**: FATE organiza sus subdirectorios por decodificador, y los formatos que
tienen nombre propio en FATE tienden a ser los que alguna vez motivaron un caso de
prueba dedicado — es decir, **formatos con implementación más madura y más probada**
en ffmpeg, lo que sesga la muestra hacia el lado optimista. Dos parejas dudosas se
declaran aparte: **`imf`** emparejó con `ASSETMAP.xml` (un índice, no un fichero de
medios — IMF es un paquete multi-fichero) y **`gsm`** con `ciao.wav` (GSM embebido en
WAV, no el `.gsm` crudo sin cabecera que la extensión nombra). Los dos cuentan en el
resultado con su fichero real declarado; no se disimula la coincidencia imperfecta.

### 2.3 Nivel 1 — la semiarista de entrada, con ficheros reales: 67/69 VIVA (97,1 %)

Misma invocación que `_semi_in.py` (trampa 79): ffmpeg contra `["mkv","wav","png"]`
en ese orden, ImageMagick contra `["png"]`, tope de 25 s, criterio de nivel 1 (basta
UN destino vivo). **MEDIDO**, n=69:

| | n | VIVA | MUERTA | % viva |
|---|---:|---:|---:|---:|
| ffmpeg | 68 | 66 | 2 | 97,1 % |
| imagemagick | 1 | 1 | 0 | 100 % |
| **total** | **69** | **67** | **2** | **97,1 %** |

Las dos muertas: **`evc`** (MPEG-5 EVC, un códec joven — ffmpeg no lo decodifica en
esta build) y **`imf`** (la pareja dudosa de §2.2: `ASSETMAP.xml` no es un fichero de
medios, así que su «muerte» no dice nada sobre el soporte real de IMF).

**97,1 % es MUY superior al 48,6 % del Escenario B** (que asumía que las
indeterminadas se comportan como la tasa YA MEDIDA de su propio motor sobre el
estrato materializable). Con el matiz de sesgo de §2.2 declarado —esta muestra
favorece formatos maduros—, **es evidencia directa de que Escenario B era
conservador para el estrato que FATE puede alcanzar**: al menos una parte
sustancial de las 75 874 indeterminadas no son un signo de interrogación real, son
aristas vivas que nunca se pudieron probar por falta de fichero.

### 2.4 Nivel 2 — muestra de aristas reales, 6 destinos por origen: 269/402 (66,9 %)

Sobre los 67 orígenes vivos, 6 destinos fijos que cruzan familia (vídeo `mkv`,
imagen `gif`/`png`, audio `mp3`/`wav`/`flac` para ffmpeg; `png`/`jpg`/`webp`/`bmp`/
`tiff`/`gif` para ImageMagick). **Criterio: `rc==0` y `bytes>0` (trampa 75) — NO el
contrato de 5 puntos completo que usa `aristas-nominales.md` para su 23,1 %.** Se
declara la diferencia de bar explícitamente: este número es un **piso más barato**
sobre un estrato que la muestra original nunca cubrió, no un reemplazo de aquélla.

| Destino | buenas/probadas |
|---|---:|
| `mkv` | 66/66 |
| `mp3` / `wav` / `flac` | 50/66 cada uno |
| `gif` | 42/67 |
| `png` | 7/67 |
| `jpg`/`webp`/`bmp`/`tiff` (ImageMagick) | 1/1 cada uno |

**269/402 = 66,9 %.** `mkv` es casi universal (ffmpeg envuelve casi cualquier cosa en
Matroska); `png`/`gif` caen porque muchos orígenes son audio puro, sin vídeo que
rasterizar — el mismo patrón de «distinta familia cuesta más» que
`aristas-nominales.md` §6 ya había medido. **67/67 orígenes tienen AL MENOS un
destino bueno** de los 6 probados, coherente con el 97,1 % del nivel 1 (redundancia
de control: `mkv`/`png` aparecen en las dos tandas y no se contradicen).

### 2.5 Lo que esto cambia — y lo que NO

**No se sustituye la tabla de Escenarios de `aristas-nominales.md`.** Lo que se
aporta es una medición REAL sobre una submuestra de las 75 874 (69 de 445 formatos,
402 de las aristas que penden de ellos), con dos niveles y sus criterios declarados:

| Nivel | n | tasa | criterio |
|---|---:|---:|---|
| Semiarista de entrada (¿hay algún destino vivo?) | 69 orígenes | **97,1 %** | rc==0, bytes>0, 1 de 3 destinos basta |
| Arista (origen×destino) | 402 pares | **66,9 %** | rc==0, bytes>0, sin contrato de fidelidad |

Las dos cifras están **por encima** del 48,6 % de Escenario B, y la de semiarista
está cerca del 77,5 % de Escenario C (cota superior). **Con el sesgo de §2.2
declarado** (formatos con más soporte en FATE tienden a tener mejor soporte en
ffmpeg), lo defendible es: **el 54,78 % indeterminado NO se comporta uniformemente
como Escenario B lo asume; para el subconjunto que FATE puede materializar, se
comporta bastante más cerca de Escenario C.** Cerrar el 54,78 % entero —los 445
formatos completos, no 69— sigue **PENDIENTE**, y exigiría o bien encontrar más
ficheros reales de los 376 formatos que FATE no nombra igual (bancos de muestras de
cada formato, uno a uno) o aceptar el sesgo de cobertura como definitivo.

---

## 3. Lo que se dejó fuera, explícitamente

**Los 56 destinos de `C28` que «ningún motor escribe» no se han tocado esta ronda**,
más allá de un cruce gratuito: 3 de los 15 que `firmas-cierre.md` §4.4 marcó como
«necesitan FATE o un motor nuevo» (`oma`, `vc1`, `evc`) **ya tienen dato** porque
resultaron estar también en la muestra de C16 —`oma` y `vc1` VIVOS, `evc` MUERTO—,
pero no se ha ido a buscar los 12 restantes ni se ha reconstruido la tabla de
`firmas-cierre.md` §4.4 con ellos. El orden del encargo puso `C28`-barato antes de
FATE precisamente porque el trozo que FATE resuelve **ya tiene techo medido: cierra
como mucho 15 de 56** (`firmas-cierre.md` §4.4) — con el presupuesto de esta ronda ya
gastado en cerrar `C28`-barato entero y sacarle a `C16` un número con dos niveles de
medición, completar esos 15 restantes habría sido pulir un techo ya conocido en vez
de abrir terreno nuevo. Queda para una ronda futura, con la ventaja de que la
metodología de emparejamiento por nombre de `c16_semi_entrada_fate.py` es directamente
reutilizable.

---

## 4. Verificación

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, Python
3.11.9, `win32`.

**Entorno:** Docker arriba (§0, verificado antes de la suite — trampa 94), sin GPU
tomada, CPU compartida con worker1 al 48 % durante la tanda.

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
```

**Qué quedó fuera de la verificación y por qué:** esta ronda **no tocó ningún fichero
de `filex/`** — todo el trabajo es investigación de bancos (`bench/`) sobre motores
externos (ffmpeg, ImageMagick, FATE). No hay código de producto que verificar más
allá de la suite existente, que se corre sin cambios para confirmar que nada se
rompió por accidente (ningún fichero de `filex/` tocado, ningún riesgo de regresión
real, pero se corre de todos modos por disciplina).

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
```

**Estado de la máquina:** declarado en la cabecera y en §0. **`N30`** (las dos
pruebas intermitentes) no salió roja en esta tanda.

---

## 5. Salidas en disco

`bench/salidas-fate-y-aristas/` (8 ficheros: 4 scripts + 4 `.json` de resultado) —
ver `MANIFIESTO.md`, con `sha256`, tamaños y las órdenes exactas. Sin binarios: los
directorios temporales de cada script se crean y se borran al terminar. El corpus
FATE se referenció por ruta absoluta y no se tocó ni se copió.
