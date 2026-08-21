# FileX — Carril GPU, Fase 1

**Máquina:** RTX 3060 12 GB (compute capability 8.6), driver 572.61, 12 hilos de CPU, Windows 10.
**Fecha:** 2026-08-19. **Arnés:** `bench/lib/harness.sh` (lock exclusivo, medianas, `peak_vram`).
**Scripts:** `bench/scripts/`. **Salidas:** `bench/salidas-fase1/`. **Registros crudos:** `bench/logs/`.

---

## 0. Cómo leer las etiquetas `limpia` / `SUCIA`

De 47 mediciones cronometradas, **una sola** salió `limpia`. Esto no significa que los
números no valgan: significa que el umbral del arnés (`<10 %` de utilización sostenida)
es **inalcanzable en esta máquina mientras haya sesión de escritorio remoto**, porque
Chrome Remote Desktop + AnyDesk mantienen el motor 3D con una media del 21,9 %. La
etiqueta `SUCIA` hay que leerla como *"el motor 3D estaba ocupado"*, no como *"el dato
está mal"*.

Lo importante es que **el motor 3D y el motor de vídeo son unidades independientes del
chip**. Medido durante una transcodificación 4K con tubería GPU completa:

| Motor | Máximo durante el encode 4K |
|---|---|
| 3D / cómputo (`utilization.gpu`) | **27 %** (ruido del escritorio remoto) |
| **NVENC** (`utilization.encoder`) | **100 %** |
| **NVDEC** (`utilization.decoder`) | **76 %** |

Es decir: cuando NVENC trabaja, se satura él, no la parte de la GPU que el escritorio
remoto ocupa. **Las mediciones NVENC son defendibles a pesar del `SUCIA`.** Donde sí hay
que desconfiar es en el ancho del rango: cuando el mínimo y la mediana casi coinciden
(p. ej. `3299–3612 ms`, mediana `3346`) el dato es sólido; cuando el rango se dispara
(`1756–8150`), un pico externo contaminó alguna repetición y **la mediana sigue siendo
válida pero el máximo no dice nada**.

### Aviso metodológico: la primera tanda fue contaminada y se repitió

La primera tanda de NVENC coincidió con la descarga e instalación de PyTorch (2,5 GB).
El resultado fue absurdo y lo dejo escrito porque es la mejor ilustración de por qué el
arnés existe:

| Medición | Tanda contaminada | Tanda tranquila (n=9) | Error |
|---|---|---|---|
| 1080p `h264_nvenc -preset p4` | **14 513 ms** (rango 2100–22061) | **1 973 ms** (rango 1748–2419) | 7,4× |
| 4K `libx264 -preset medium` | **24 953 ms** (rango 16524–62215) | **11 427 ms** (rango 9601–24674) | 2,2× |

Todas las cifras de velocidad de este informe salen de la **tanda tranquila** (n=9,
`bench/logs/nvenc_rep.log`). La tanda contaminada queda en `bench/logs/nvenc.log`.

---

## A. NVENC extendido

Fuentes: `corpus/video/tipico.mp4` (1080p30, 20 s, 600 fotogramas),
`corpus/video/fuente_4k.mp4` (3840×2160, 30 fps, 10 s, 300 fotogramas, generado con
`testsrc2`), `corpus/video/patologico_2pistas.mkv` (720p + 2 pistas de audio).

### A.1 · A.2 — libx264/libx265 frente a NVENC

n=9, mediana. Tiempos de proceso completo (incluye arranque de ffmpeg, demux y mux).

| Caso | CPU (mediana / rango) | GPU (mediana / rango) | Aceleración | Etiqueta |
|---|---|---|---|---|
| 1080p H.264 `medium` vs `p4` | 5 407 ms / 4808–9586 | **1 973 ms** / 1748–2419 | **2,74×** | SUCIA (pico 17 %) |
| 4K H.264 `medium` vs `p4` | 11 427 ms / 9601–24674 | **4 286 ms** / 3343–7795 | **2,67×** | SUCIA (pico 18–58 %) |
| 1080p HEVC `medium` vs `p4` | 16 598 ms / 14937–41015 | **1 978 ms** / 1902–3453 | **8,39×** | SUCIA (pico 16–18 %) |
| 1080p completo v+a (transcode real) | 5 248 ms / 4809–6049 | **1 762 ms** / 1731–1878 | **2,98×** | **limpia** (la GPU) |
| Patológico 720p, 2 pistas de audio | 1 358 ms / 1300–1404 | **628 ms** / 620–667 | **2,16×** | SUCIA (pico 18 %) |

**Lecturas:**

- El **3,3× que se citaba como cifra de referencia queda matizado**: en H.264 la ventaja
  real es **2,7–3,0×**, no 3,3×. Solo el caso completo con audio llega a 2,98×.
- Donde NVENC arrasa es en **HEVC: 8,4×**. `libx265 -preset medium` es unas 3 veces más
  lento que `libx264 -preset medium`, mientras que `hevc_nvenc` cuesta lo mismo que
  `h264_nvenc` (1 978 ms vs 1 973 ms). Para el codificador de hardware, HEVC es gratis.
- El caso patológico (2 pistas de audio, MKV) **no rompe nada**: `-map 0` conserva las dos
  pistas y la aceleración se mantiene en 2,16×. El suelo lo pone el arranque del proceso,
  no el códec: 628 ms para 10 s de 720p es prácticamente coste fijo.
- El multiplicador **cae al subir la resolución** (2,74× en 1080p, 2,67× en 4K): la CPU con
  12 hilos escala mejor de lo que se supone, y NVENC empieza a saturarse.
- `av1_nvenc` no existe en Ampere (verificado previamente: `No capable devices found`).
  Para AV1 en esta máquina solo hay ruta CPU (`libsvtav1`, `librav1e`, `libaom`).

### A.3 — Tubería GPU completa vs decodificar en CPU

Pregunta: ¿cuánto aporta evitar la copia VRAM↔RAM con
`-hwaccel cuda -hwaccel_output_format cuda`?

| Caso | Decodifica CPU + codifica GPU | Todo GPU | Diferencia |
|---|---|---|---|
| 1080p H.264 | **1 771 ms** / 1756–8150 | 2 001 ms / 1731–4360 | **GPU un 13 % peor** |
| 4K H.264 | 3 346 ms / 3299–3612 | **3 240 ms** / 3195–7313 | GPU un 3 % mejor |
| 4K → 1080p con escalado | **1 542 ms** / 1526–5515 | 2 071 ms / 2042–4484 | **GPU un 34 % peor** |

**Respuesta honesta: en esta máquina, evitar la copia de memoria no aporta nada medible.**

- A 1080p los mínimos son idénticos (1 756 vs 1 731 ms): la copia no es el cuello de
  botella, lo es NVENC.
- A 4K la ventaja es del 3 %, dentro del ruido.
- Con escalado, la ruta GPU es **claramente peor**. `scale_cuda` a 300 fotogramas 4K→1080p
  tarda más que decodificar en 12 hilos de CPU, escalar con `swscale` y subir los
  fotogramas. Matiz: `scale_cuda` usa interpolación bilineal por defecto y `swscale` usa
  bicúbica, así que no hacen exactamente el mismo trabajo — pero para un conversor el
  resultado práctico es el que cuenta.
- La primera tanda (contaminada) sugería lo contrario (GPU un 9–14 % mejor). Que el signo
  del resultado cambie según el ruido de fondo es precisamente la prueba de que **la
  diferencia entre ambas rutas está por debajo del umbral de ruido de esta máquina**.

**Conclusión de diseño:** no merece la pena complicar el grafo de filtros de FileX con
`-hwaccel cuda -hwaccel_output_format cuda` y filtros `_cuda`. Decodificar en CPU y
codificar en GPU es igual de rápido, mucho más compatible (cualquier códec de entrada,
cualquier filtro de ffmpeg) y no obliga a duplicar cadenas de filtros. La tubería GPU
completa solo se justificaría con varios flujos 4K simultáneos, donde la CPU sí sería el
límite.

### A.4 — Calidad: la contrapartida honesta de la velocidad

Mismo bitrate objetivo, VMAF (modelo `vmaf_v0.6.1`, ffmpeg con `--enable-libvmaf`), PSNR y
SSIM contra la fuente. Se incluye el **bitrate realmente producido**, porque NVENC no
respeta el objetivo tan bien como x264/x265 y eso falsea cualquier comparación que solo
mire la calidad.

#### H.264, 1080p

| Codificador | Objetivo | Bitrate real | Desvío | VMAF | PSNR (dB) | SSIM |
|---|---|---|---|---|---|---|
| `libx264 -preset medium` | 2M | 2 026 kbps | +1,3 % | **89,70** | 38,88 | 0,9851 |
| `h264_nvenc -preset p4` | 2M | 2 214 kbps | **+10,7 %** | 88,71 | 38,30 | 0,9824 |
| `h264_nvenc -preset p7` | 2M | 2 161 kbps | +8,0 % | 89,22 | 38,54 | 0,9807 |
| `libx264 -preset medium` | 5M | 5 048 kbps | +1,0 % | **95,71** | 43,74 | 0,9947 |
| `h264_nvenc -preset p4` | 5M | 5 421 kbps | **+8,4 %** | 95,20 | 42,77 | 0,9931 |
| `h264_nvenc -preset p7` | 5M | 5 297 kbps | +5,9 % | 95,60 | 43,32 | 0,9931 |
| `libx264 -preset medium` | 10M | 10 023 kbps | +0,2 % | **98,87** | 52,72 | 0,9991 |
| `h264_nvenc -preset p4` | 10M | 10 785 kbps | **+7,9 %** | 98,55 | 50,29 | 0,9986 |
| `h264_nvenc -preset p7` | 10M | 10 826 kbps | +8,3 % | 98,77 | 51,28 | 0,9987 |

#### HEVC, 1080p

| Codificador | Objetivo | Bitrate real | Desvío | VMAF | PSNR (dB) | SSIM |
|---|---|---|---|---|---|---|
| `libx265 -preset medium` | 3M | 3 048 kbps | +1,6 % | 91,56 | 40,21 | 0,9895 |
| `hevc_nvenc -preset p4` | 3M | 3 308 kbps | **+10,3 %** | 90,96 | 39,79 | 0,9870 |
| `hevc_nvenc -preset p7` | 3M | 3 286 kbps | +9,5 % | **91,65** | 40,07 | 0,9877 |
| `libx265 -preset medium` | 6M | 6 081 kbps | +1,3 % | 95,65 | 44,37 | 0,9954 |
| `hevc_nvenc -preset p4` | 6M | 6 485 kbps | +8,1 % | 95,65 | 44,04 | 0,9949 |
| `hevc_nvenc -preset p7` | 6M | 6 547 kbps | +9,1 % | **96,14** | 44,58 | 0,9956 |

#### H.264, 4K @ 20M

| Codificador | Bitrate real | Desvío | VMAF | PSNR (dB) | SSIM |
|---|---|---|---|---|---|
| `libx264 -preset medium` | 20 718 kbps | +3,6 % | **93,43** | 43,25 | 0,9942 |
| `h264_nvenc -preset p4` | 22 364 kbps | **+11,8 %** | 93,27 | 42,95 | 0,9937 |

**Lecturas:**

- **El déficit de VMAF de NVENC es pequeño: 0,16 a 0,99 puntos con `p4`.** A escala VMAF
  eso es casi imperceptible; nadie distingue 95,20 de 95,71 mirando el vídeo.
- **Pero NVENC gasta sistemáticamente entre un 6 % y un 12 % más de bits de los pedidos**,
  mientras que x264/x265 se quedan en +0,2 % a +3,6 %. Ese es el coste real y es el que
  se suele omitir: **NVENC no es "un poco peor a igual bitrate", es "casi igual gastando
  un 8 % más de fichero"**. Corregido por bits, la penalización efectiva se acerca al
  10–15 % de tamaño para la misma calidad.
- **`preset p7` prácticamente anula el déficit de calidad** (y en HEVC lo invierte: 96,14
  frente a 95,65 de x265 a 6M), pero sigue sin arreglar el desvío de bitrate. Como p7 en
  esta tarjeta cuesta poco más que p4, **p7 es la elección por defecto sensata para un
  conversor**, no p4.
- PSNR castiga a NVENC más que VMAF (hasta 2,4 dB a 10M). Es coherente: NVENC optimiza
  percepción y no error cuadrático.
- Aviso de validez: el corpus es sintético (`testsrc2` y similares), con bordes duros y
  patrones que no representan bien el vídeo natural. Los valores absolutos de VMAF hay que
  tomarlos con reservas; **la comparación relativa CPU/GPU, que es lo que se pedía, sí es
  válida** porque ambos codificaron exactamente la misma fuente.

### A.5 — VRAM durante la transcodificación

`peak_vram` mide la memoria **total** de la tarjeta; la columna de coste propio resta la
línea base del escritorio (2 585 MiB en ese momento).

| Operación | Pico total | Coste propio |
|---|---|---|
| 1080p `h264_nvenc` | 2 794 MiB | **209 MiB** |
| 1080p `hevc_nvenc` | 2 789 MiB | **204 MiB** |
| 4K `h264_nvenc` (decodifica CPU) | 3 049 MiB | **464 MiB** |
| 4K tubería GPU completa | 3 328 MiB | **743 MiB** |
| 4K, dos sesiones NVENC en paralelo | 3 847 MiB | **1 262 MiB** |

**NVENC es baratísimo en VRAM.** Una transcodificación 1080p cabe en 0,2 GB; una 4K con
tubería completa en 0,75 GB. Frente a los 3–4,5 GB de un modelo de IA, el vídeo es ruido
en el presupuesto. Dos sesiones NVENC simultáneas funcionaron sin problema (las GeForce
modernas ya no imponen el límite de 2 sesiones de antaño).

---

## B. Pila de IA

Entorno: `D:\Work\research\FileX\.venv-ai\` (Python 3.11.9). Nada instalado fuera del venv.

### B.0 — Un fallo de instalación que hay que documentar

`pip install surya-ocr` **destruyó silenciosamente la instalación CUDA de PyTorch**:

```
torch 2.6.0+cu124   →   torch 2.13.0        (rueda de PyPI: CPU pura en Windows)
torchvision 0.21.0+cu124 → torchvision 0.28.0
ERROR: torchaudio 2.6.0+cu124 requires torch==2.6.0+cu124, but you have torch 2.13.0
```

Después de eso, `torch.cuda.is_available()` devolvía `False` y **toda la pila habría
corrido en CPU sin dar un solo error**. Solo se detectó porque lo comprobé explícitamente.
Reparado con:

```
pip install --force-reinstall --no-deps torch==2.6.0+cu124 torchvision==0.21.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124
```

Estado final verificado: `torch 2.6.0+cu124`, `cuda True (12.4)`, `RTX 3060`,
compute capability `(8, 6)`, `bf16 True`.

**Esto no es una anécdota, es un requisito de diseño**: en Windows, las ruedas `torch` de
PyPI son solo CPU, y cualquier dependencia que declare `torch` a secas puede degradar la
GPU a CPU en una actualización rutinaria. FileX necesita fijar la versión de torch, usar
el índice de PyTorch y **verificar `torch.cuda.is_available()` en el arranque del sidecar**,
fallando ruidosamente si es `False`.

### B.1 — faster-whisper

`large-v3` y `distil-large-v3`, ambos en `float16`, `device="cuda"`, `beam_size=5`.
Corpus: `corpus/audio/` + audio extraído de `corpus/video/tipico.mp4`. Como el corpus de
audio original son tonos sintéticos de 8 s (inútiles para medir transcripción), añadí
`corpus/audio/habla_jfk.flac` (11 s de voz real, transcripción conocida) y
`corpus/audio/habla_largo.flac` (308 s, 28 repeticiones del anterior).

#### Tiempos de carga

| Modelo | Carga en frío (incluye descarga) | Carga en caliente (en proceso) | Carga en caliente (proceso completo, n=7) |
|---|---|---|---|
| `large-v3` | 159,6 s (2,88 GB descargados) | 4,0–8,5 s | mediana **9 389 ms** / 7914–27875 · SUCIA |
| `distil-large-v3` | 53,3 s (1,41 GB descargados) | 2,3–2,7 s | — |

La carga en caliente medida con `measure` (9,4 s) incluye arranque del intérprete de
Python e inicialización de CTranslate2; la carga del modelo en sí son 4–8 s. **Para el
sidecar la conclusión es la misma: no se puede pagar esto por petición.**

#### VRAM

| Modelo | Solo cargado | Pico durante inferencia |
|---|---|---|
| `large-v3` fp16 | **+3 082 MiB** | **+4 525 MiB** |
| `distil-large-v3` fp16 | **+1 605 MiB** | **+1 847 MiB** |

Obsérvese que la inferencia de `large-v3` añade **1,4 GB por encima del modelo cargado**
(buffers de beam search y del codificador). El presupuesto no puede calcularse con el
tamaño del modelo: hay que usar el pico de inferencia.

#### Velocidad y corrección

| Modelo | Audio | Duración | Tiempo | Factor tiempo real | Salida |
|---|---|---|---|---|---|
| `large-v3` | habla_jfk | 11,0 s | 1,56 s | **7,0×** | correcta al 100 % |
| `large-v3` | habla_largo | 308,0 s | 111,37 s | **2,8×** | 3 049 chars (esperado ~3 024) |
| `distil-large-v3` | habla_jfk | 11,0 s | 0,90 s | **12,3×** | correcta al 100 % |
| `distil-large-v3` | habla_largo | 308,0 s | 26,17 s | **11,8×** | 3 500 chars (**+16 % de más**) |

- `distil-large-v3` es **4,3× más rápido** en el archivo largo y usa **2,5× menos VRAM**.
- Pero produce un 16 % más de texto del esperado sobre un audio de contenido repetido:
  hay duplicación de segmentos. `large-v3` clavó la longitud (3 049 vs 3 024 esperados).
  La comparación fina de precisión es materia de fase 2, pero la señal ya está ahí.
- Ambos transcribieron el fragmento de JFK **palabra por palabra sin un solo error**.

#### Alucinaciones sobre audio no hablado — hallazgo importante

Los tonos sinusoidales del corpus original produjeron texto inventado:

| Entrada | `large-v3` | `distil-large-v3` |
|---|---|---|
| `tipico.mp3` (tono, 8 s) | `Thanks for watching!` | (7 chars) |
| `trivial.wav` (tono, 8 s) | `Thanks for watching!` | (13 chars) |
| audio de `tipico.mp4` (20 s) | `Thank you for watching.` | (9 chars) |

Probabilidad de idioma detectada: **0,35–0,37** frente a 0,91–0,97 en el audio con voz
real. **FileX debe usar ese umbral como filtro**: por debajo de ~0,5 de confianza de
idioma, la transcripción es probablemente alucinada y debe descartarse o marcarse, no
entregarse como resultado.

### B.2 — docling

`AcceleratorDevice.CUDA`, `do_ocr=True`, `do_table_structure=True`.

#### ¿Usa realmente la GPU? Sí — con prueba

| Prueba | CUDA | CPU |
|---|---|---|
| Delta de VRAM (`nvidia-smi`) | **+827 MiB** | **0 MiB** |
| `torch.cuda.max_memory_allocated()` | **575,2 MiB** | — |
| `torch.cuda.max_memory_reserved()` | **698,0 MiB** | — |
| Tiempo total de los 3 PDF | 13,5 s | 14,35 s |

La memoria se reserva y se asigna vía torch: **no es un `device="cuda"` decorativo**. Pero
**el tiempo es prácticamente idéntico (6 % de diferencia)**: en documentos de una página, el
coste está en el arranque y en la parte de CPU, no en la inferencia de layout.

#### Matiz importante: la OCR de docling corre en CPU

`onnxruntime 1.29.0` instalado ofrece únicamente
`['AzureExecutionProvider', 'CPUExecutionProvider']`. El motor de OCR de docling
(RapidOCR / PP-OCRv6 sobre ONNX) **no toca la GPU**. Lo que sí va a GPU es el modelo de
layout y el de estructura de tablas (`docling-layout-heron`, `docling-models`, en torch).
Para tener OCR en GPU con docling habría que instalar `onnxruntime-gpu`.

#### Tiempos por documento (en caliente, CUDA)

| Documento | Tiempo | Caracteres extraídos |
|---|---|---|
| `tipico_texto.pdf` | 6,07 s | 158 |
| `patologico_escaneado.pdf` | 0,92 s | 81 |
| `trivial.pdf` | 0,50 s | 10 |

Modelos descargados: 0,49 GB.

### B.3 — surya: **NO FUNCIONA en GPU en esta máquina**

Lo reporto como fallo, sin maquillar.

`surya-ocr 0.22.1` **ya no es un modelo PyTorch en proceso**. Su arquitectura ha cambiado:
`SuryaInferenceManager` envuelve un backend que habla el protocolo OpenAI de chat
completions, y elige backend automáticamente (`surya/inference/__init__.py`):

```python
def _autodetect_backend() -> str:
    # NVIDIA GPU → vllm, mps/cpu → llamacpp
    if _has_nvidia_gpu():
        return "vllm"
    return "llamacpp"
```

En esta máquina autodetecta `vllm`. Y el backend vllm **lanza un contenedor Docker**
(`surya/inference/backends/vllm.py`):

```
docker run --rm -d --name surya-vllm-<puerto> --runtime nvidia --gpus device=<n>
    -v ~/.cache/huggingface:/root/.cache/huggingface -p <puerto>:8000 --ipc=host
    vllm/vllm-openai:v0.20.1 --model datalab-to/surya-ocr-2 --dtype bfloat16
    --gpu-memory-utilization 0.85 --max-model-len 18000 ...
```

Configuración por defecto leída del propio paquete:

| Ajuste | Valor |
|---|---|
| `VLLM_DOCKER_IMAGE` | `vllm/vllm-openai:v0.20.1` |
| `SURYA_MODEL_CHECKPOINT` | `datalab-to/surya-ocr-2` |
| `VLLM_DTYPE` | `bfloat16` |
| `VLLM_GPU_MEMORY_UTILIZATION` | **0.85** |
| `VLLM_GPU_TYPE` | `4090` (¡valor por defecto, no la tarjeta real!) |
| `SURYA_INFERENCE_STARTUP_TIMEOUT` | 600 s |

**Qué pasó exactamente:**

1. **Intento 1** — API antigua (`surya.foundation.FoundationPredictor`):
   `ModuleNotFoundError: No module named 'surya.foundation'`. Esa API ya no existe en 0.22.1.
2. **Intento 2** — API nueva (`SuryaInferenceManager` + `RecognitionPredictor(full_page=True)`):
   el constructor devuelve en 0,98 s (es perezoso), y la **primera llamada de OCR se cuelga
   indefinidamente**. Sin excepción, sin traza, sin contenedor creado
   (`docker ps -a` no muestra ningún `surya-vllm-*`), sin descarga de imagen
   (`docker events` sin eventos de imagen), sin aumento de VRAM. Se quedó bloqueado en el
   sondeo de salud del servidor. Lo maté tras superar dos veces el margen de tiempo.

**Por qué no lo he forzado:**

- `vllm` no está instalado ni es instalable oficialmente en Windows (`vllm_instalado: false`,
  `llama_cpp_instalado: false`).
- La ruta GPU requiere Docker con `--runtime nvidia`, que en Windows significa Docker
  Desktop con paso de GPU por WSL2. Docker 29.4.3 está presente pero ocupado por otro
  agente del proyecto (contenedores `filex-*` en marcha), y `bench/docker.md` es territorio
  de ese agente.
- La imagen `vllm/vllm-openai:v0.20.1` ronda los 10–20 GB. Traerla habría consumido casi
  todo el presupuesto de 25 GB para un componente que además **no cabe**: con
  `--gpu-memory-utilization 0.85` vLLM reservaría 0,85 × 12 288 = **10 445 MiB**, más que
  los ~9 760 MiB libres. Habría fallado por falta de VRAM incluso funcionando.
- Decisión tomada antes de descargar nada, como pedía el encargo.

**Sobre el camino `bfloat16`** (lo que se pedía comprobar): la tarjeta **sí cualifica**.
`torch.cuda.is_bf16_supported() == True`, compute capability `(8, 6)` ≥ 8.0, y surya
define `MODEL_DTYPE_BFLOAT = torch.bfloat16` y `VLLM_DTYPE = "bfloat16"`. Pero **ese camino
vive dentro del contenedor vLLM**, así que es inalcanzable aquí. El `MODEL_DTYPE` del
proceso Python es `torch.float16`, no bf16.

**VRAM de surya: no medida.** No hay dato porque el motor nunca llegó a cargar.

### B.4 — marker: **descartado con criterio, no intentado**

`marker-pdf 2.0.0` declara:

```
Requires-Dist: surya-ocr<0.23.0,>=0.22.1
Requires-Dist: torch<3,>=2.7.0
Requires-Dist: transformers<6,>=5.12.1
```

Dos motivos para no instalarlo:

1. **Hereda el bloqueo de surya**: exige exactamente la versión 0.22.1–0.22.x, la que
   necesita el servidor vLLM en Docker. No habría funcionado en GPU.
2. **`torch>=2.7.0` volvería a romper la instalación CUDA**: en Windows, pip resolvería a
   una rueda de PyPI sin CUDA, repitiendo el desastre de B.0 y dejando whisper y docling
   también en CPU.

Metadatos comprobados sin instalar nada (`pip download --no-deps`, 195 kB). Coste evitado:
la reinstalación completa de la pila.

### B.5 — La pregunta central: ¿cuántos modelos caben a la vez?

#### Coste de VRAM por motor (medido por separado)

| Motor | Solo cargado | Pico en uso |
|---|---|---|
| Escritorio + sesión remota (línea base) | — | **2 086 – 2 590 MiB** |
| faster-whisper `large-v3` fp16 | 3 082 MiB | **4 525 MiB** |
| faster-whisper `distil-large-v3` fp16 | 1 605 MiB | **1 847 MiB** |
| docling CUDA (layout + tablas) | 827 MiB | **910 MiB** |
| NVENC 1080p | — | **209 MiB** |
| NVENC 4K (tubería completa) | — | **743 MiB** |
| NVENC 4K × 2 en paralelo | — | **1 262 MiB** |
| surya | *sin dato — no arranca* | *sin dato* |
| marker | *no instalado — ver B.4* | *no instalado* |

#### Prueba 1 — tres modelos residentes + NVENC 4K encima

`bench/logs/coexistencia.log`, `bench/scripts/ia_coexistencia.sh`:

| Paso | VRAM total | Incremento |
|---|---|---|
| 0 · línea base | 2 145 MiB | — |
| 1 · + whisper `large-v3` | 5 220 MiB | +3 075 |
| 2 · + docling CUDA | 6 130 MiB | +910 |
| 3 · + whisper `distil-large-v3` | 7 652 MiB | +1 522 |
| 4 · + transcodificación NVENC 4K | **8 557 MiB (pico)** | +905 |
| **Total sobre la línea base** | | **+6 412 MiB** |
| **VRAM libre restante** | | **3 731 MiB** |

La transcodificación NVENC terminó correctamente (`rc=0`) con los tres modelos residentes.

#### Prueba 2 — inferencia activa simultánea (el caso realista)

`bench/logs/coexistencia_activa.log`: whisper `large-v3` transcribiendo 308 s de audio,
docling convirtiendo tres PDF y NVENC transcodificando 4K, **todo a la vez**.

| Métrica | Valor |
|---|---|
| Pico de VRAM total | **7 446 MiB** |
| Incremento sobre la línea base | **5 283 MiB** |
| Pico de utilización de GPU | 100 % |
| **VRAM libre restante** | **4 842 MiB** |
| Coste en rendimiento — whisper | 2,8× → **2,3× tiempo real (−18 %)** |
| Coste en rendimiento — docling (`tipico_texto.pdf`) | 6,07 s → **8,54 s (+41 %)** |

Nada falló. **Los tres motores conviven sin quedarse sin memoria y sin errores CUDA.**

#### Presupuesto de VRAM resultante

Sobre 12 288 MiB totales:

| Partida | MiB | Comentario |
|---|---|---|
| Escritorio + sesión remota | **2 600** | usar el máximo observado, no la media |
| Margen de seguridad | **800** | fragmentación, picos del escritorio, driver |
| **Disponible para FileX** | **8 888** | ~8,7 GB |
| whisper `large-v3` (pico de inferencia) | 4 525 | el que manda |
| docling CUDA | 910 | |
| NVENC 4K | 743 | |
| **Suma del perfil completo** | **6 178** | |
| **Holgura sobrante** | **2 710** | |

**Perfiles que caben:**

| Perfil | Coste | ¿Cabe en 8 888 MiB? |
|---|---|---|
| whisper `large-v3` + docling + NVENC | 6 178 MiB | **Sí**, con 2,7 GB de holgura |
| whisper `distil` + docling + NVENC × 2 | 4 019 MiB | **Sí**, con 4,9 GB de holgura |
| 2 × whisper `large-v3` | 9 050 MiB | **No** |
| whisper `large-v3` + `distil` + docling + NVENC | 8 025 MiB | Justo — 0,9 GB de margen, arriesgado |

---

## C. Verificación funcional

Salidas en `bench/salidas-fase1/`. Verificador: `bench/scripts/verificar_ocr.py`.

### PDF escaneado sin capa de texto — precisión real del OCR

Texto original del documento: `DOCUMENTO ESCANEADO`,
`Texto que solo existe como pixeles.`, `Debe recuperarse con OCR.`

| Motor | Frases exactas | Distancia de edición | Salida literal |
|---|---|---|---|
| **docling CUDA** | **3/3** | **0** en las tres | `DOCUMENTO ESCANEADO Texto que solo existe como pixeles. Debe recuperarse con OCR.` |
| **docling CPU** | **3/3** | **0** en las tres | idéntica |
| surya | *sin salida* | — | el motor no arrancó |

**docling recuperó el texto escaneado sin un solo carácter de error**, y la salida de la
ruta CUDA es byte a byte idéntica a la de CPU (lo esperable: la OCR corre en CPU en ambos
casos, como se documentó en B.2).

### PDF con capa de texto

`docling_cuda_tipico_texto.pdf.md`:

```
FileX - documento de prueba con texto seleccionable Segunda linea: acentos aeiou n ˆ
y simbolos % &amp; @ Tabla:  Col A    Col B    Col C 1        2        3
```

Correcto en estructura y tabla, con dos defectos: **los acentos se pierden**
(`aeiou n ˆ` en lugar de `áéíóú ñ`) y el `&` sale como entidad HTML `&amp;`. Ambos son
problemas de normalización de texto que FileX tendrá que corregir en la capa de
posproceso — no fallos de GPU.

### Transcripción

| Comprobación | Resultado |
|---|---|
| `large-v3` sobre voz real | **Correcta al 100 %** |
| `distil-large-v3` sobre voz real | **Correcta al 100 %** |
| Ambos sobre tonos sintéticos | **Alucinan** (`Thanks for watching!`) — ver B.1 |

### Vídeo

Los 20 ficheros generados en `bench/salidas-fase1/video/` abren correctamente y `ffprobe`
confirma resolución, códec y duración esperados. El caso patológico de 2 pistas de audio
conserva ambas con `-map 0`.

---

## Presupuesto consumido

| Concepto | Tamaño |
|---|---|
| Entorno virtual `.venv-ai` (torch cu124, faster-whisper, docling, surya) | 5,41 GB |
| Modelos descargados a la caché de Hugging Face | 4,78 GB |
| · `Systran/faster-whisper-large-v3` | 2,88 GB |
| · `Systran/faster-distil-whisper-large-v3` | 1,41 GB |
| · `docling-project/docling-models` + `docling-layout-heron` | 0,49 GB |
| Fuente 4K generada + salidas de prueba | 0,93 GB |
| **Total** | **≈ 11,1 GB** de los 25 GB autorizados |
| Imagen `vllm/vllm-openai` **no descargada** (decisión, ver B.3) | ~10–20 GB evitados |
| Espacio libre en D: al terminar | 91,7 GB |

---

## Implicaciones para el diseño del sidecar de FileX

### 1. El sidecar debe ser un proceso residente, no un ejecutable por petición

`large-v3` tarda **4–8 s en cargar el modelo** y **9,4 s de proceso completo** (medido con
n=7). Docling reserva sus modelos en el primer `convert()`. Pagar eso por cada archivo
convertido es inviable. El sidecar arranca una vez, carga lo que le corresponde y atiende
peticiones.

### 2. Presupuesto de VRAM: **8,7 GB para FileX, ni uno más**

Reservar 2,6 GB para el escritorio y la sesión remota (máximo observado, no media) y
0,8 GB de margen. El perfil recomendado —whisper `large-v3` + docling + NVENC— consume
**6,2 GB y deja 2,7 GB de holgura**, verificado con las tres cargas activas a la vez.

Dos reglas duras que salen de las mediciones:

- **Presupuestar por pico de inferencia, no por tamaño de modelo.** `large-v3` ocupa
  3,1 GB cargado pero llega a **4,5 GB** transcribiendo. Presupuestar con 3,1 GB provoca
  OOM en producción.
- **Una sola instancia de `large-v3`.** Dos no caben (9,1 GB). Si hacen falta dos flujos de
  transcripción simultáneos, la segunda debe ser `distil-large-v3` (1,8 GB de pico).

### 3. NVENC es prácticamente gratis en memoria: dárselo siempre al vídeo

209 MiB a 1080p, 743 MiB a 4K con tubería completa. **El vídeo nunca es lo que llena la
VRAM.** El sidecar puede transcodificar mientras los modelos de IA están cargados sin
plantearse siquiera si cabe. Con `distil` en lugar de `large-v3` caben hasta dos sesiones
NVENC 4K simultáneas con 4,9 GB de sobra.

### 4. `hevc_nvenc` es la joya: 8,4× — no `h264_nvenc`

La aceleración de H.264 es 2,7–3,0×, no el 3,3× que se venía citando. Pero **HEVC en GPU
es 8,4× más rápido que `libx265 -preset medium` y cuesta lo mismo que H.264 en NVENC**.
Cuando el destino admita HEVC, FileX debe preferirlo: obtiene mejor compresión y ahorra el
mayor factor de tiempo de todo el carril de vídeo.

### 5. Usar `preset p7`, no `p4`

`p7` elimina casi todo el déficit de calidad (y en HEVC supera a x265) y en esta tarjeta
cuesta poco más. Y **corregir siempre el bitrate objetivo**: NVENC entrega un 6–12 % más de
bits de los pedidos, mientras que x264/x265 se quedan en +0,2–3,6 %. Si FileX promete un
tamaño de salida, tiene que pedir a NVENC entre un 7 % y un 10 % menos del objetivo real, o
usar `-maxrate`/`-bufsize` para acotarlo.

### 6. No construir tuberías GPU completas

`-hwaccel cuda -hwaccel_output_format cuda` **no aporta nada medible** (−13 % a +3 %, dentro
del ruido) y con escalado es un 34 % **peor**. Decodificar en CPU y codificar en GPU es
igual de rápido, acepta cualquier códec de entrada y cualquier filtro de ffmpeg, y evita
mantener dos cadenas de filtros paralelas. Reconsiderarlo solo si aparecen varios flujos 4K
concurrentes.

### 7. Comprobación obligatoria de CUDA al arrancar

El incidente de B.0 es el riesgo operativo más serio detectado: `pip install surya-ocr`
degradó torch a una rueda CPU **sin error visible**, y toda la pila habría corrido en CPU
en silencio. El sidecar debe:

- fijar `torch==2.6.0+cu124` con el índice explícito de PyTorch;
- comprobar `torch.cuda.is_available()` al arrancar y **fallar ruidosamente** si es falso;
- exponer la versión de torch y el nombre del dispositivo en su endpoint de salud;
- congelar el entorno (`pip freeze`) y no permitir resoluciones transitivas de `torch`.

### 8. La OCR de docling está en CPU: es un cuello de botella oculto

`onnxruntime` instalado solo tiene proveedor CPU. Los modelos de layout y tablas van a GPU,
pero el reconocimiento de caracteres no. Para lotes grandes de documentos escaneados hay
que instalar `onnxruntime-gpu` y volver a medir. **Con documentos de una página la GPU no
aporta nada** (13,5 s CUDA vs 14,35 s CPU): FileX debería enrutar los PDF pequeños a CPU y
reservar la GPU para lotes, liberando VRAM para transcripción.

### 9. Filtro anti-alucinación en transcripción, obligatorio

Whisper devuelve `Thanks for watching!` sobre un tono puro, con total aplomo. La señal que
lo delata es `language_probability`: **0,35–0,37 en audio no hablado frente a 0,91–0,97 en
voz real**. FileX debe descartar o marcar toda transcripción por debajo de ~0,5. Sin ese
filtro, un conversor universal generará subtítulos inventados para cualquier vídeo sin voz.

### 10. surya y marker quedan fuera del sidecar hasta nuevo aviso

No es una preferencia, es una restricción de arquitectura: **`surya-ocr` 0.22.1 no es una
biblioteca en proceso, es un cliente de un servidor vLLM en Docker**. Meterlo en FileX
significaría:

- añadir Docker con `--runtime nvidia` como dependencia dura del sidecar;
- una imagen de 10–20 GB;
- **y aun así no cabría**: `--gpu-memory-utilization 0.85` reserva 10,4 GB, más que los
  9,7 GB libres. Habría que bajar ese ajuste y `VLLM_MAX_MODEL_LEN`, y `VLLM_GPU_TYPE`
  viene por defecto en `4090`, no en una 3060.

`marker-pdf 2.0.0` hereda el bloqueo (fija `surya-ocr>=0.22.1,<0.23.0`) y además exige
`torch>=2.7.0`, lo que repetiría el desastre de B.0.

**Recomendación:** docling cubre el caso de OCR probado —3/3 frases exactas, distancia de
edición 0 sobre el PDF escaneado— sin ninguna de estas dependencias. Si en el futuro hace
falta surya, la vía realista es **pinchar una versión anterior que corra torch en proceso**,
y verificarlo antes de comprometerse.

---

## Apéndice — dónde está cada cosa

| Ruta | Contenido |
|---|---|
| `bench/scripts/bench_nvenc.sh` | Tanda NVENC original (contaminada) |
| `bench/scripts/bench_nvenc_repeticion.sh` | Tanda NVENC tranquila, n=9 — **la buena** |
| `bench/scripts/bench_calidad.sh` | VMAF / PSNR / SSIM, CPU vs GPU |
| `bench/scripts/gpuwatch.py` | Monitor de VRAM y utilización con línea base |
| `bench/scripts/ia_whisper.py` | faster-whisper (modos: `todo`, `solo_carga`, `residente`) |
| `bench/scripts/ia_docling.py` | docling CUDA/CPU |
| `bench/scripts/ia_surya.py` | surya — **no funcional**, conservado como evidencia |
| `bench/scripts/ia_coexistencia.sh` | Modelos residentes + NVENC |
| `bench/scripts/ia_coexistencia_activa.sh` | Inferencia activa simultánea |
| `bench/scripts/verificar_ocr.py` | Verificación de precisión del OCR |
| `bench/scripts/instalar_ia.sh` | Instalación del venv |
| `bench/logs/` | Todas las salidas crudas |
| `bench/salidas-fase1/video/` | Ficheros de vídeo generados |
| `bench/salidas-fase1/video/calidad/` | Muestras usadas para VMAF |
| `bench/salidas-fase1/ia/` | Transcripciones, Markdown de docling, verificación |
| `corpus/audio/habla_jfk.flac` | Voz real añadida (11 s, transcripción conocida) |
| `corpus/audio/habla_largo.flac` | Voz real añadida (308 s) |
| `corpus/video/fuente_4k.mp4` | Fuente 4K generada con `testsrc2` |
