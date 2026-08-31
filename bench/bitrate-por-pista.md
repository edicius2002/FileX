# N28 — bitrate obtenido por pista y residuo C25

**MEDIDO:** CPU/Git Bash, ruta resuelta `D:\utils\ffmpeg\bin\ffmpeg.EXE`, build N-121159-g0bd5a7d371-20250921. Sin GPU. La tanda es **SUCIA**: no hubo los dos testigos ni n≥9; los ms guardados son trazabilidad, no medida de rendimiento.

## N28

**REFUTADO:** restar `n_audio × bitrate_audio_bps` pedido. La medición anterior demostró que `-b:a` puede quedar por debajo de la tasa obtenida, así que esa resta sobreestima vídeo y puede falso-positivar. Se retiró de `V10` y también de `decidido`.

Regla escrita: el lado bajo sigue siendo `fallo`, porque el contenedor es cota superior del vídeo; el lado alto es `fallo` sólo sin audio. Con una o más pistas de audio queda `informativo`, incluso si alguien entrega `bitrate_audio_bps`: pedido no equivale a obtenido.

**MEDIDO:** de las 12 patológicas originales, **8** siguen atrapadas (lado bajo) y **4** con exceso y audio quedan declaradas, no atrapadas. No se añadió un falso positivo por esta retirada: las 72 legítimas conservan el lado bajo demostrado; las 53 del patrón oro no traen `bitrate_video_bps`, por lo que V10 no aplica en ninguna.

### ¿Se puede publicar lo obtenido por pista?

| Vía | MP4 | MKV | WEBM | MOV | Resultado |
|---|---|---|---|---|---|
| `-show_entries stream=bit_rate` | AAC 96 890 b/s | `None` | `None` | AAC 96 890 b/s | no uniforme |
| `-count_packets` + stream | 95 paquetes, tasa presente | 95, tasa ausente | 101, tasa ausente | 95, tasa presente | sólo cuenta; no crea tasa |
| `-show_packets` + suma `pkt_size` por `stream_index` / duración | 97 924 | 96 906 | 123 817 Opus | 97 924 | **uniforme y caro** |

Todos los contenedores se generaron con `rc=0` y bytes positivos. La última vía recorre el fichero completo y devuelve además cada paquete: es la única base correcta para una tasa obtenida por pista, pero no entra en la sonda caliente sin medir su coste n≥9 y sin decidir presupuesto. **PENDIENTE:** instrumentarla como operación explícita/posterior, no disfrazarla de atributo barato de `sondear()`.

Recomendación: mantener la media regla demostrable (`informativo` con audio) hasta disponer de esa operación cara. `-c copy` y codec fuera de tabla también permanecen informativos por el mismo motivo.

## C25

**MEDIDO:** `amv` queda cerrado como fallo documentado: dos intentos ya gastados, `rc=-22 (EINVAL)`, 0 B; el segundo perfil llega a `block_size 1470` y vuelve a EINVAL. No se reintentó.

**AUTOCORRECCIÓN:** el supuesto bloqueo anterior era falso. Leí la ausencia física de `pool/` sin leer `bench/salidas-invocacion/MANIFIESTO.md` ni su índice: la poda es deliberada y `_p2_semillas.py` reconstruye las entradas. Confundir un activo regenerable con una pérdida fue el espejo de la trampa 89 y no una medida de bloqueo.

## C25 (segunda pasada)

**MEDIDO:** ejecuté `python bench/salidas-invocacion/_p2_semillas.py` desde Git Bash. Materializó 111 entradas (264 MiB en disco); el script tiene `D:\Work\research\FileX` como raíz, por lo que el pool quedó en esa raíz común, que es exactamente la ruta que usan los `argv` P2. El directorio temporal `C:\Users\krato\AppData\Local\Temp\filex-c25-segunda-77fge3o_` se listó vacío antes, con `c01`…`c15` durante la tanda, y fue borrado después. El `pool/` regenerado también se borró al terminar. `MANIFIESTO.md` ya declaraba tanto la poda como la orden de regeneración; no precisó edición.

Reejecuté las 15 filas cuyo `err` contiene `received no packets`, con `-t 8` dentro de cada orden y timeout exterior de 20 s. La salida conserva por celda el `argv` exacto, `rc`, bytes y stderr. Criterio aplicado: buena sólo si `rc == 0` **y** `bytes > 0`.

| Clase por rc | Celdas | Resultado |
|---|---:|---|
| `-22` (`EINVAL`) | 14 | 0 B; la invocación no satisface las restricciones del formato/flujo. Incluye las que ya llevaban `-strict -2`: no son casos `EXPERIMENTAL`. |
| `-40` (`Function not implemented`) | 1 (`w64 → amr`) | 0 B; `libopencore_amrnb` no puede abrir el encoder antes de EOF. Es un fallo de implementación/codificador, distinto de EINVAL. |

**Resultado: 0/15 buenas.** No hay una semilla ausente ni timeout que lo explique. `rc` es la clasificación: 14 EINVAL y 1 fallo `-40`; no se resume como «no funciona».

## C25 (tercera pasada)

**CORRECCIÓN DEL 111/112:** no falta una semilla ni existe un `rc` que nombrar. `_p2_semillas.py` informó literalmente `materializados 111, sin semilla 0: []`. `pool_indice.json` tiene 112 claves porque las 111 entradas de formato llevan además la clave de metadatos `__semillas__` (las rutas base); por tanto **112 no es el número de formatos**. El informe anterior debió decir «111 formatos, 0 sin semilla», no inducir que faltaba uno.

**Condición de entrada registrada:** las 15 entradas fueron parseadas como `Input #0` con flujos reales durante la segunda pasada; ninguna tuvo `No such file`. Resultado: **entradas ausentes 0/15**. La próxima reejecución deja esto como campos explícitos `entrada_existe` y `entrada_parseada` en el arnés, en vez de inferirlo de `rc` o de la duración.

El segundo nivel de la clasificación separa cinco aristas que no tienen flujo semánticamente compatible y se declaran **`no_aplica`**, de nueve candidatas a otra invocación del grafo de filtros. La restante no es `no_aplica`, pero exige soporte de codificador, no otra bandera.

| Celda | Clase | Prueba en stderr |
|---|---|---|
| `aptx → isma` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `msbc → ismv` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `webp → rm` | grafo de filtros | `[vf#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `tta → h265.mp4` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `fits → flac` | `no_aplica`: imagen a muxer de audio | `No audio stream present.` |
| `w64 → amr` | implementación de codificador | `Function not implemented` al abrir `libopencore_amrnb` |
| `loas → roq` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `bmp → 3gp` | grafo de filtros | `[vf#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `png → aifc` | `no_aplica`: imagen a muxer de audio | `Stream #0:0 -> #0:0 (png … -> png …)`; `No audio stream present.` |
| `avi → rco` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `bmp → afc` | `no_aplica`: imagen a muxer de audio | `No audio stream present.` |
| `uw → roq` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `pgm → aif` | `no_aplica`: imagen a muxer de audio | `No audio stream present.` |
| `mov → tco` | grafo de filtros | `[af#0:0 …] Task finished with error code: -22 (Invalid argument)` |
| `ass → m3u8` | `no_aplica`: sólo subtítulos hacia HLS | `Subtitle: ass (ssa)`; `No streams to mux were specified` |

**Cifra útil:** 5/15 son irreparables por construcción (`no_aplica`); 9/15 siguen candidatas a una invocación distinta; 1/15 requiere soporte de codificador. No se reintentó ninguna: los intentos de esta deuda ya están gastados.

## Verificación

- Prueba roja y verde: V10 con audio y `bitrate_audio_bps` vuelve a `informativo`; el motor no publica la tasa pedida como obtenida.
- 19 pruebas dirigidas de bitrate/degradación: pasan.
- `py_compile` y `git diff --check`: pasan.

## Salidas

| Fichero | Tamaño | SHA-256 | Orden |
|---|---:|---|---|
| `bench/salidas-bitrate-pista/sondar.py` | 2 826 B | `c8158c35b1004385971b872f3c1e2de7ef70a30f9e266af24c527ceb12a4651a` | `python bench/salidas-bitrate-pista/sondar.py` desde Git Bash |
| `bench/salidas-bitrate-pista/resultado.json` | 69 905 B | `682a76a6b3d27e7f4bd1005c095eae042f873fce64083f05aea4aabbe911d1ca` | salida de la orden anterior |
| `bench/salidas-bitrate-pista/reintento_c25.py` | 5 038 B | `0f5dbebc4584c6d59eee0557a29e265a10c00898a738c250b14ff3a84ee82e1a` | `python bench/salidas-bitrate-pista/reintento_c25.py` desde Git Bash; `--clasificar` no reejecuta |
| `bench/salidas-bitrate-pista/c25-segunda-pasada.json` | 19 703 B | `f1ab471bf98688a2fbd9cc055ea79dc52778a4e12b003f1fdc3fb11e0bdcaa8e` | salida de la orden anterior; 15 argv/rc/bytes/stderr |
| `bench/salidas-bitrate-pista/c25-clases.json` | 6 509 B | `d5625aca72dfdabe746b78f09f04f832d4f9de59c55a1fc8a63dad85d7378fd4` | clasificación posterior de las 15 salidas; no ejecuta ffmpeg |

No se versionaron binarios regenerables; cada celda conserva orden, rc, bytes y stderr.
