# FileX — Carril GPU, Fase 2: ¿es alcanzable el OCR en GPU?

**Máquina:** RTX 3060 12 GB (compute capability 8.6), driver 572.61, 12 hilos de CPU, Windows 10.
**Fecha:** 2026-08-19. **Arnés:** `bench/lib/harness.sh` (lock exclusivo `fase2`, medianas, `peak_vram`).
**Scripts:** `bench/scripts/ocr_*.py`, `bench/scripts/whisper_precision.py`, `bench/scripts/gen_corpus_ocr.sh`.
**Salidas:** `bench/salidas-fase2/`. **Registros crudos:** `bench/logs/fase2_*.log`.

---

> ## ⚠️ AVISO AÑADIDO EL 21/08/2026 — las cifras de CER de d2 y d3 NO miden a los motores
>
> **Las cifras de este informe son las que se midieron y se conservan tal cual.** Lo que cambia es su
> interpretación, y solo para las dificultades **2 y 3**.
>
> **El arnés de esta fase rasterizaba todos los PDF a 200 ppp.** Verificado sobre el corpus:
> `corpus/pdf/escaneado_d2.pdf` y `escaneado_d3.pdf` llevan una imagen incrustada de **647×850 px sobre
> una página de 465,84×612 pt = 100 ppp nativos**. Rasterizarlos a 200 ppp es **interpolar ×2**, que
> convierte el grano JPEG q25 en manchas del tamaño de un trazo. (Para `patologico_escaneado.pdf`,
> 1294×1792 sobre 465,84×645,12 pt = **200 ppp nativos**, el arnés era correcto; d0 y d1 no están
> afectados de la misma forma.)
>
> **Consecuencia:** las marcas de d2 y d3 de las tablas de §1, §3, §4 y §5 —RapidOCR 65,8 %,
> PaddleOCR 75,9 %, EasyOCR 57,0 % de CER en d3— **no son válidas como medida de la capacidad de los
> motores frente a un documento degradado**: miden en buena parte ese ×2 de interpolación. **A ppp
> nativos, PaddleOCR resuelve d3 con 2,5 % de CER**, confirmado tres veces de forma independiente.
> La conclusión «en d3 fallan los tres» es **falsa**.
>
> **Lo que sí sobrevive como asimetría real entre motores:** **RapidOCR no resuelve d3 a ninguna
> resolución** (mejor caso 53,2 %). Es límite de modelo, no de preprocesado.
>
> La cadena de medición es fiel: el control `ctrlppp200` reproduce estas marcas **exactamente, 4 de 4**.
> El sesgo está localizado en la elección de ppp del arnés, no en el instrumento.
>
> **Detalle, matriz ppp × deskew y consecuencias de diseño: `bench/ocrmypdf.md` §3.4 y §8.**
> **PENDIENTE:** repetir esta fase rasterizando a los ppp nativos.

---

## 0. Veredicto, primero

**Sí, el hueco competitivo nº 4 (OCR acelerado por GPU) es alcanzable, y sale más barato de
lo que la fase 1 hacía temer.** No hace falta surya, ni marker, ni vLLM, ni Docker.

| Pregunta | Respuesta medida |
|---|---|
| ¿Puede docling hacer OCR en GPU? | **Sí**, por dos vías distintas, ambas verificadas |
| ¿Cuál es la vía más barata? | `RapidOcrOptions(backend="torch")` — **0 bytes de instalación nueva**, usa el torch cu124 que ya está |
| ¿Cuál es la más rápida? | `onnxruntime-gpu==1.22.0` + un `rapidocr_params` de dos líneas |
| Aceleración real, tubería docling completa | **3,1× frente a todo-CPU**; **2,2× frente al estado de la fase 1** |
| Aceleración del OCR aislado | **4,2×** RapidOCR · **10,8×** PaddleOCR · **17,0×** EasyOCR |
| Coste en VRAM | **+1 555 MiB** (backend torch) a **+2 127 MiB** (onnxruntime-gpu) |
| ¿Cabe encima del perfil de fase 1? | **Sí**: pico de 7 702 MiB con whisper `large-v3` residente + OCR-GPU + NVENC, **4 586 MiB libres** |
| Motor más preciso | **PaddleOCR** (0 % de error hasta d2), seguido de RapidOCR (1,3 %) |
| Coste de integración más bajo | **RapidOCR vía docling** — ya está instalado, misma API, mismo proceso |

**Recomendación:** docling + RapidOCR con `backend="torch"`. Es GPU real, no cuesta ni un
paquete nuevo, no toca `onnxruntime`, y evita el riesgo de degradar la instalación CUDA que
destrozó la fase 1. `onnxruntime-gpu==1.22.0` es el escalón siguiente si se quiere el 10 %
extra de velocidad, a cambio de 346 MB en disco y de un parámetro no documentado.

**PaddleOCR se instaló sin un solo error y es el más preciso, pero vive en su propio venv de
3,7 GB con su propio runtime CUDA.** Es la opción de calidad, no la opción por defecto.

---

## 1. Tarea D — Un corpus de OCR que sí discrimina

La sospecha del encargo era correcta: `corpus/pdf/patologico_escaneado.pdf` es demasiado
limpio. **Los seis motores/configuraciones lo resuelven con distancia de edición 0.** Como
prueba comparativa no vale para nada.

Generé tres variantes progresivamente peores con ImageMagick 7.1.2
(`bench/scripts/gen_corpus_ocr.sh`), **con el texto de referencia idéntico** para poder medir
distancia de edición contra la misma cadena conocida:

`DOCUMENTO ESCANEADO` · `Texto que solo existe como pixeles.` · `Debe recuperarse con OCR.`

| Variante | ppp | Inclinación | Ruido gaussiano | Contraste | Desenfoque | JPEG | Tamaño |
|---|---|---|---|---|---|---|---|
| `patologico_escaneado.pdf` (d0, ya existía) | 200 | 1,7° | leve | pleno | — | — | 8,56 MB |
| **`escaneado_d1.pdf`** | 150 | **+3°** | 0,30 | `+level 8%,92%` | — | q60 | 85 kB |
| **`escaneado_d2.pdf`** | 100 | **−5°** | 0,55 | `+level 22%,80%` | 0,6 px | q40 | 42 kB |
| **`escaneado_d3.pdf`** | 100 | **+5°** | 0,90 | `+level 38%,72%` | 1,1 px | q25 | 41 kB |

Detalle metodológico que costó una iteración: `-level` **aumenta** el contraste; el que lo
**reduce** es `+level`. La primera tanda salió engañosamente limpia por ese signo. Además el
ruido tiene que aplicarse **después** de comprimir el rango, o el recorte a negro/blanco se
lo come.

El resultado es una escala que discrimina de verdad:

- **d0 y d1**: todos los motores aciertan al 100 %. Sirven de control.
- **d2**: separa a EasyOCR (43 % de error) de RapidOCR (1,3 %) y PaddleOCR (0 %).
- **d3**: rompe a todos. Nadie recupera más que el titular. Es el suelo de la escala.

> ⚠️ **Corregido el 21/08/2026 (ver aviso de cabecera).** «d3 rompe a todos» es un artefacto del arnés:
> d2 y d3 son de **100 ppp nativos** y se rasterizaron a 200. A ppp nativos **PaddleOCR resuelve d3 con
> 2,5 % de CER**; RapidOCR no lo resuelve a ninguna resolución. `bench/ocrmypdf.md` §3.4.

`escaneado_d3.pdf` sigue siendo legible para un humano —lo verifiqué visualmente— así que
mide el margen real que queda por ganar, no un imposible.

---

## 2. Tarea A — ¿Puede docling hacer OCR en GPU? Sí, y de dos formas

### A.0 — Qué motores de OCR ofrece docling 2.120.3

```
OcrEngine: ['auto', 'easyocr', 'tesseract_cli', 'tesseract', 'ocrmac', 'rapidocr']
```

Y `RapidOcrOptions` acepta cuatro backends de inferencia:
`onnxruntime`, `openvino`, `paddle`, `torch`.

| Motor | ¿Acepta GPU? | Estado en esta máquina |
|---|---|---|
| `rapidocr` + `onnxruntime` | Sí, con `onnxruntime-gpu` **y un override** | **Medido** — ver A.2/A.3 |
| `rapidocr` + `torch` | **Sí, sin instalar nada** | **Medido** — ver A.4 |
| `rapidocr` + `paddle` | Sí en teoría | **No probado**: exigiría `paddlepaddle-gpu` dentro de `.venv-ai`, justo el conflicto torch/paddle que el encargo mandaba evitar |
| `rapidocr` + `openvino` | No (es CPU/iGPU Intel) | Irrelevante en NVIDIA |
| `easyocr` | Sí (`use_gpu=True`, va por torch) | **Medido** — ver §3 |
| `tesseract` / `tesseract_cli` | **No**, Tesseract es CPU por diseño | **No instalado** en la máquina (`which tesseract` → nada). No lo instalé: aunque funcionara no aportaría GPU, que es lo que se estaba midiendo |
| `ocrmac` | — | Solo macOS |

### A.1 — Primer intento: `onnxruntime-gpu` 1.29.0 → **fallo silencioso, otra vez**

Instalación limpia (desinstalar `onnxruntime`, instalar `onnxruntime-gpu==1.29.0`, 148 MB).
Comprobación de rutina:

```python
ort.get_device()               # -> 'GPU'
ort.get_available_providers()  # -> ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

**Las dos señales dicen que hay GPU. Las dos mienten.** Al crear la sesión de verdad:

```
[E:onnxruntime:Default, provider_bridge_ort.cc:2395] Error loading
  "...\onnxruntime\capi\onnxruntime_providers_cuda.dll"
  which depends on "cublasLt64_13.dll" which is missing. (Error 126)
[W] Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 13.*
session.get_providers()  # -> ['CPUExecutionProvider']
```

**`onnxruntime-gpu` 1.29.0 exige CUDA 13.** Esta máquina tiene toolkits 12.6 y 12.8, y torch
está compilado contra 12.4. La sesión se crea sin excepción y corre en CPU.

Esto es **exactamente el mismo patrón que el desastre de `surya-ocr` en la fase 1**: la pila
degrada a CPU sin un solo error, y solo se detecta si se comprueba explícitamente. Pero con
un agravante: aquí ni siquiera `get_available_providers()` sirve como comprobación, porque
**lista proveedores que no se pueden instanciar**. La única verificación válida es
`session.get_providers()` sobre una sesión ya creada.

> **Requisito de diseño para FileX:** verificar el proveedor **sobre una sesión real**, no
> sobre la lista de disponibles. `get_available_providers()` refleja cómo se compiló el
> paquete, no lo que la máquina puede ejecutar.

### A.2 — Segundo intento: `onnxruntime-gpu` 1.22.0 → **funciona**

`docling-slim` declara `onnxruntime-gpu<1.24`, así que la versión 1.29 que había instalada
estaba fuera del rango que los propios autores de docling soportan. Instalé **1.22.0**
(214,9 MB de descarga, 346 MB en disco), que está compilada contra CUDA 12.x + cuDNN 9.

```
ort 1.22.0  session.get_providers() -> ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

Modelo de detección PP-OCRv6 aislado, entrada 1×3×960×960, n=11, mediana:

| Proveedor | Mediana | Rango | VRAM |
|---|---|---|---|
| `CPUExecutionProvider` | **174,5 ms** | 169,6–180,2 | — |
| `CUDAExecutionProvider` | **15,0 ms** | 14,3–16,5 | +379 MiB |

**11,6× en el modelo de detección.** Ahí está el hueco nº 4.

Detalle operativo: en Windows, `onnxruntime-gpu` necesita las DLL de CUDA/cuDNN en la ruta de
búsqueda. **No hace falta instalar cuDNN**: las que trae `torch 2.6.0+cu124` en
`torch/lib/` (`cudnn64_9.dll` y compañía) sirven, basta con
`os.add_dll_directory(os.path.dirname(torch.__file__) + "/lib")` antes de importar
`onnxruntime`. En esta máquina funcionó incluso sin ese paso, porque los toolkits CUDA 12.6
y 12.8 ya están en el `PATH` del sistema — pero **FileX no puede contar con eso** y debe
añadir el directorio explícitamente.

### A.3 — El fallo de docling: `use_cuda` no llega al motor

Con la CUDA EP ya funcional, docling **seguía haciendo OCR en CPU**. Instrumenté
`onnxruntime.InferenceSession` para registrar el proveedor de cada sesión
(`SONDA_ORT=1` en `bench/scripts/ocr_docling.py`):

```
{"evento":"sesion_ort","modelo":"PP-OCRv6_det_small.onnx","providers":["CPUExecutionProvider"]}
{"evento":"sesion_ort","modelo":"ch_ppocr_mobile_v2.0_cls_mobile.onnx","providers":["CPUExecutionProvider"]}
{"evento":"sesion_ort","modelo":"PP-OCRv6_rec_small.onnx","providers":["CPUExecutionProvider"]}
```

La causa está en `docling/models/stages/ocr/rapid_ocr_model.py`. Docling calcula `use_cuda`
correctamente y lo escribe donde no se lee:

```python
params = {
    "Det.use_cuda": use_cuda,                      # <- docling escribe aquí
    "Cls.use_cuda": use_cuda,
    "Rec.use_cuda": use_cuda,
    "EngineConfig.paddle.use_cuda": use_cuda,      # <- y aquí para paddle
    "EngineConfig.torch.use_cuda":  use_cuda,      # <- y aquí para torch
    # NO existe "EngineConfig.onnxruntime.use_cuda"
}
```

Pero `rapidocr/inference_engine/onnxruntime/provider_config.py` lo lee de otro sitio:

```python
self.cfg_use_cuda = engine_cfg.get("use_cuda", False)   # engine_cfg = EngineConfig.onnxruntime
```

**Docling rellena `EngineConfig.paddle.use_cuda` y `EngineConfig.torch.use_cuda` pero olvida
`EngineConfig.onnxruntime.use_cuda`.** Resultado: el backend por defecto —onnxruntime— es el
único de los cuatro que nunca ve la GPU.

Se arregla desde fuera, sin parchear docling, usando el escape `rapidocr_params`:

```python
RapidOcrOptions(
    backend="onnxruntime",
    rapidocr_params={
        "EngineConfig.onnxruntime.use_cuda": True,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
    },
)
```

Con eso, las tres sesiones salen en `['CUDAExecutionProvider', 'CPUExecutionProvider']` y el
tiempo por documento cae de 1,16 s a 0,53 s.

> Esto es deuda de integración real: **un parámetro no documentado que hay que mantener** y
> que puede romperse en cualquier versión de docling. Es el argumento más fuerte a favor de
> la vía del backend `torch`, que no lo necesita.

### A.4 — `backend="torch"`: OCR en GPU sin instalar absolutamente nada

RapidOCR 3.9.2 incluye un motor PyTorch (`rapidocr/inference_engine/pytorch/`) que carga los
mismos modelos PP-OCR en formato `.pth` y los ejecuta con `torch`. Como `.venv-ai` ya tiene
`torch 2.6.0+cu124`, **no hace falta instalar ni una dependencia**, y docling sí rellena
`EngineConfig.torch.use_cuda` correctamente, así que **funciona sin ningún override**:

```python
RapidOcrOptions(backend="torch")   # y AcceleratorDevice.CUDA. Eso es todo.
```

Verificado en las dos configuraciones de `onnxruntime`:

| Entorno | d0 | d1 | d2 | d3 | VRAM pico |
|---|---|---|---|---|---|
| con `onnxruntime-gpu` 1.22 instalado | 0,74 s | 0,59 s | 0,54 s | 0,53 s | 3 692 MiB |
| con `onnxruntime` **CPU** 1.23.2 instalado | 0,83 s | 0,66 s | 0,63 s | 0,59 s | 3 817 MiB |

La diferencia entre ambas filas es ruido de la sesión remota (la segunda tanda salió con un
pico del 24 %). **Lo importante es que la segunda fila existe: el backend `torch` da OCR en
GPU con `onnxruntime` de CPU instalado.** Coste de descarga: 62 MB de pesos `.pth`, que
RapidOCR se trae solo la primera vez.

### A.5 — Tabla A: docling, tubería completa

Mediana de **n=9 conversiones en caliente dentro del mismo proceso** (así no se mide el
arranque del intérprete ni la carga de modelos). Formato `tiempo / CER`.

| Configuración | d0 (200 ppp) | d1 (150 ppp, 3°) | d2 (100 ppp, −5°) | d3 (100 ppp, 5°) | VRAM pico | Coste propio |
|---|---|---|---|---|---|---|
| `docling_cpu` — todo CPU, rapidocr/onnx | 1,80 s / 0,0 % | 1,62 s / 0,0 % | 1,61 s / 0,0 % | 1,59 s / 58,2 % | 2 141 MiB | **0** |
| `docling_cpu_torch` — todo CPU, backend torch | 2,35 s / 0,0 % | 2,22 s / 0,0 % | 2,13 s / 0,0 % | 2,12 s / 58,2 % | 2 257 MiB | 0 |
| `docling_cuda_ocrcpu` — **estado de la fase 1** | 1,29 s / 0,0 % | 1,16 s / 0,0 % | 1,07 s / 0,0 % | 1,09 s / 58,2 % | 2 968 MiB | +827 |
| **`docling_cuda_ocrgpu`** — onnxruntime-gpu | **0,71 s / 0,0 %** | **0,53 s / 0,0 %** | **0,48 s / 0,0 %** | **0,51 s / 58,2 %** | 4 268 MiB | **+2 127** |
| **`docling_cuda_torch`** — backend torch | 0,83 s / 0,0 % | 0,66 s / 0,0 % | 0,63 s / 0,0 % | 0,59 s / 58,2 % | 3 817 MiB | **+1 555** |
| `docling_easyocr_cpu` | 8,12 s / 0,0 % | 8,62 s / 0,0 % | 8,62 s / 40,5 % | 8,09 s / 75,9 % | 2 290 MiB | 0 |
| `docling_easyocr_gpu` | 0,98 s / 0,0 % | 0,76 s / 0,0 % | 0,77 s / 40,5 % | 0,90 s / 75,9 % | 5 122 MiB | +2 977 |

**Lecturas:**

- Sobre d1, la aceleración total es **1,62 → 0,53 s = 3,06×**. Frente al estado en que la
  fase 1 dejó el sistema (OCR en CPU con layout en GPU), la ganancia es **2,19×**.
- **La salida es idéntica en CPU y en GPU, carácter a carácter, en las tres configuraciones
  de RapidOCR y en las dos de EasyOCR.** Mover el OCR a la GPU no cuesta precisión.
- El backend `torch` cuesta **572 MiB menos de VRAM** que `onnxruntime-gpu` y es solo un
  10–20 % más lento. Con el presupuesto de 8,7 GB de la fase 1, esos 572 MiB importan.
- **Ojo con el backend `torch` en CPU**: 2,1–2,3 s frente a 1,6 s de onnxruntime. Si FileX
  decide el backend por dispositivo, en CPU debe usar `onnxruntime` y en CUDA `torch`.
- EasyOCR en CPU es **inutilizable** dentro de docling: 8,1–8,6 s por página, cinco veces
  más lento que RapidOCR. Y encima es el menos preciso.

---

## 3. Tarea B — EasyOCR

**Instalación: limpia y sin sustos.** `pip install easyocr` en `.venv-ai` resolvió `torch`
como *ya satisfecho* y no intentó tocarlo. Verificación posterior obligatoria:

```
torch 2.6.0+cu124  cuda True  NVIDIA GeForce RTX 3060
```

Instaló `easyocr-1.7.2`, `scikit-image-0.26.0`, `imageio`, `tifffile`, `python-bidi`,
`ninja`, `lazy-loader` y **degradó `sympy` de 1.14.0 a 1.13.1**, que es justo lo que
`torch 2.6.0` pide. Peso: 16 MB el paquete, ~130 MB con dependencias, **94 MB de modelos**
(`craft_mlt_25k.pth` + `latin_g2.pth`) descargados a `~/.EasyOCR`.

Es el caso contrario al de `surya-ocr` en la fase 1: **EasyOCR es el vecino educado de la
pila torch.** Declara `torch` sin fijar versión y pip lo respeta.

### Velocidad: es donde más se nota la GPU

Motor aislado, sin docling, sobre las páginas rasterizadas a 200 ppp, mediana de n=9:

| | d0 | d1 | d2 | d3 |
|---|---|---|---|---|
| CPU | 6 660 ms | 6 972 ms | 6 998 ms | 6 345 ms |
| **CUDA** | **538 ms** | **410 ms** | **442 ms** | **513 ms** |
| **Aceleración** | **12,4×** | **17,0×** | **15,8×** | **12,4×** |

**EasyOCR es el motor que más gana con la GPU: hasta 17×.** También es el que más VRAM
consume: **+2 079 MiB** aislado, **+2 977 MiB** dentro de docling.

### Precisión: es el peor de los tres

| Documento | CER CPU | CER CUDA |
|---|---|---|
| d0 | 0,0 % | 0,0 % |
| d1 | 0,0 % | 0,0 % |
| **d2** | **43,0 %** | **43,0 %** |
| d3 | 57,0 % | **59,5 %** |

> ⚠️ **d2 y d3 medidos con ×2 de sobremuestreo** (100 ppp nativos rasterizados a 200). No valen como
> medida de capacidad del motor. Ver aviso de cabecera y `bench/ocrmypdf.md` §3.4.

Sobre d2, EasyOCR desordena las líneas y confunde caracteres:
`documento escaneado solo existe texlo con ocr debe recuperarse pixeles` — mezcla el orden de
lectura de las dos frases. RapidOCR sobre el mismo documento se equivoca en **un solo
carácter** (`coma` en vez de `como`).

**Un detalle que merece constancia:** sobre d3, EasyOCR **no es determinista entre CPU y
GPU** (distancia 45 vs 47). Es la única discrepancia CPU/GPU de toda la fase 2, y aparece
solo cuando la entrada está tan degradada que el modelo trabaja al borde de su umbral de
confianza. No invalida nada, pero **FileX no puede prometer salida idéntica entre
dispositivos con EasyOCR**.

---

## 4. Tarea C — PaddleOCR

**Instalación: correcta al primer intento, en venv separado, sin tocar `.venv-ai`.**

```
python -m venv .venv-paddle                                   # Python 3.11.9
pip install paddlepaddle-gpu==3.2.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
pip install paddleocr                                          # -> paddleocr 3.7.0 + paddlex 3.7.2
```

`paddlepaddle-gpu` 3.2.0 se trae su propio runtime CUDA vía ruedas `nvidia-*`
(`cublas 12.6.4.1`, `cudnn 9.5.1.17`, `cufft`, `curand`, `cusolver`, `cusparse`,
`nvjitlink`), así que **no depende de los toolkits del sistema ni de las DLL de torch**. Eso
es precisamente por lo que necesita su propio venv: metería un segundo juego completo de
librerías CUDA junto a las de torch.

Verificación oficial:

```
GPU Compute Capability: 8.6, Driver API Version: 12.8, Runtime API Version: 12.6
PaddlePaddle works well on 1 GPU.
```

Y `torch` en `.venv-ai` seguía en `2.6.0+cu124 / True` después. **El aislamiento funcionó.**

**Coste: 3,73 GB de venv + 139 MB de modelos** (`~/.paddlex`). Es, con diferencia, la
instalación más cara de la fase.

### Velocidad y precisión

| | d0 | d1 | d2 | d3 |
|---|---|---|---|---|
| CPU | 2 446 ms | 2 424 ms | 2 546 ms | 2 221 ms |
| **GPU** | **274 ms** | **224 ms** | **217 ms** | **198 ms** |
| **Aceleración** | **8,9×** | **10,8×** | **11,7×** | **11,2×** |
| **CER** (idéntico CPU/GPU) | 0,0 % | 0,0 % | **0,0 %** | 75,9 % |

> ⚠️ **El 75,9 % de d3 mide el ×2 de sobremuestreo del arnés, no al motor.** A los 100 ppp nativos del
> documento, **PaddleOCR resuelve d3 con 2,5 % de CER** (y con la imagen incrustada sin rasterizar,
> igual). Ver aviso de cabecera y `bench/ocrmypdf.md` §3.4.

**PaddleOCR es el más preciso del banco: el único que resuelve d2 sin un solo error.** Y en
GPU es igual de rápido que RapidOCR (198–274 ms frente a 210–275 ms), lo cual tiene sentido
—RapidOCR ejecuta los mismos modelos PP-OCR, solo que exportados a ONNX.

Contrapartidas medidas:

- **Carga: 24,8 s en GPU** frente a 3,5–8,6 s de los demás. Es el arranque más lento de todo
  el banco. Para un sidecar residente es coste único; para un proceso por petición es
  prohibitivo.
- Sobre d3 es el que menos recupera (solo el titular): es preciso o calla, no inventa.
- Necesita proceso separado. Integrarlo en FileX significa **un segundo sidecar** con su
  propio venv de 3,7 GB y su propio runtime CUDA compitiendo por VRAM con el primero.

---

## 5. Tabla comparativa maestra de motores

Motor aislado sobre las páginas rasterizadas a 200 ppp (sin la etapa de maquetación de
docling), mediana de n=9. `Coste propio` = VRAM pico menos la línea base del escritorio.

> ⚠️ **Las cuatro columnas de CER de d2 y d3 no son válidas como medida de capacidad de los motores**:
> esos dos documentos son de **100 ppp nativos** y aquí se rasterizaron a 200 (×2 de interpolación).
> Las columnas de tiempo y VRAM **sí** valen. A ppp nativos: **PaddleOCR d3 = 2,5 %**; RapidOCR no
> resuelve d3 a ninguna resolución (mejor caso 53,2 %). Ver aviso de cabecera y `bench/ocrmypdf.md` §3.4.

| Motor | Disp. | Carga | Coste VRAM | d0 | d1 | d2 | d3 | CER d0 | CER d1 | CER d2 | CER d3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **RapidOCR** (PP-OCRv5 mobile, ONNX) | CPU | 3,5 s | +14 MiB | 967 ms | 924 ms | 763 ms | 827 ms | 0,0 % | 0,0 % | 1,3 % | 70,9 % |
| **RapidOCR** | **CUDA** | 8,6 s | **+1 344 MiB** | **275 ms** | **220 ms** | **211 ms** | **210 ms** | 0,0 % | 0,0 % | 1,3 % | 65,8 % |
| **EasyOCR** (CRAFT + latin_g2) | CPU | 5,3 s | +144 MiB | 6 660 ms | 6 972 ms | 6 998 ms | 6 345 ms | 0,0 % | 0,0 % | 43,0 % | 57,0 % |
| **EasyOCR** | **CUDA** | 5,5 s | **+2 079 MiB** | 538 ms | 410 ms | 442 ms | 513 ms | 0,0 % | 0,0 % | 43,0 % | 59,5 % |
| **PaddleOCR** (PP-OCRv5, es) | CPU | 3,9 s | +165 MiB | 2 446 ms | 2 424 ms | 2 546 ms | 2 221 ms | 0,0 % | 0,0 % | **0,0 %** | 75,9 % |
| **PaddleOCR** | **CUDA** | **24,8 s** | **+1 486 MiB** | **274 ms** | **224 ms** | **217 ms** | **198 ms** | 0,0 % | 0,0 % | **0,0 %** | 75,9 % |

Aceleración GPU por motor (mediana sobre los cuatro documentos):

| Motor | Aceleración | Comentario |
|---|---|---|
| EasyOCR | **12,4–17,0×** | El que más gana, el que más VRAM cuesta, el menos preciso |
| PaddleOCR | **8,9–11,7×** | El más preciso, el que más tarda en cargar |
| RapidOCR | **3,5–4,2×** | El que menos gana… porque su versión CPU ya es la más rápida |

**Lectura importante y contraintuitiva:** RapidOCR gana "poco" con la GPU no porque su ruta
GPU sea mala, sino porque **su ruta CPU es excelente** (763–967 ms frente a los 2,4 s de
Paddle y los 6,7 s de EasyOCR). En GPU los tres convergen a ~200–500 ms. Si se compara **lo
mejor de CPU contra lo mejor de GPU**, la ganancia real del hueco nº 4 es
**763 → 198 ms = 3,9×**, no 17×. Los factores grandes de EasyOCR miden sobre todo lo mala
que es su implementación en CPU.

**Nota de comparabilidad:** el banco aislado usa PP-OCRv5 *mobile* para RapidOCR, mientras
que docling resuelve a PP-OCRv6 *small*. Por eso los CER de d3 de las tablas A y de esta no
coinciden exactamente (65,8 % frente a 58,2 %). Dentro de cada tabla la comparación es
homogénea; entre tablas, no.

---

## 6. Tarea E.1 — `large-v3` frente a `distil-large-v3` sobre voz real

La fase 1 dejó la señal (`distil` producía un 16 % más de caracteres de lo esperado) pero no
la medición. Aquí está, con WER y CER contra la referencia conocida.

**Corpus:** `corpus/audio/habla_jfk.flac` (11 s, texto conocido) y `habla_largo.flac` (308 s,
28 repeticiones). Añadí dos degradaciones realistas en `bench/salidas-fase2/audio/`:

- `jfk_ruido` / `largo_ruido`: ruido blanco sumado (`anoisesrc a=0.05`, `amix`)
- `jfk_telefono`: banda 300–3 400 Hz remuestreada a 8 kHz (calidad telefónica)

Referencia (22 palabras): *"And so my fellow Americans ask not what your country can do for
you ask what you can do for your country"*.

| Modelo | Tarea | Duración | Tiempo | Factor TR | Prob. idioma | Palabras ref/hip | **WER** | **CER** |
|---|---|---|---|---|---|---|---|---|
| `large-v3` | jfk limpio | 11 s | 1,82 s | 6,0× | 0,912 | 22 / 22 | **0,00 %** | **0,00 %** |
| `large-v3` | jfk **con ruido** | 11 s | 1,14 s | 9,6× | 0,954 | 22 / 22 | **0,00 %** | **0,00 %** |
| `large-v3` | jfk **telefónico 8 kHz** | 11 s | 1,16 s | 9,5× | 0,936 | 22 / 22 | **0,00 %** | **0,00 %** |
| `large-v3` | largo limpio | 308 s | 110,63 s | 2,8× | 0,966 | 616 / **616** | **0,00 %** | **0,00 %** |
| `large-v3` | largo **con ruido** | 308 s | 116,07 s | 2,7× | 0,942 | 616 / **616** | **0,00 %** | **0,00 %** |
| `distil-large-v3` | jfk limpio | 11 s | 0,92 s | 11,9× | 0,978 | 22 / 22 | **0,00 %** | 0,00 % |
| `distil-large-v3` | jfk **con ruido** | 11 s | 0,78 s | 14,2× | 0,986 | 22 / 22 | **0,00 %** | 0,00 % |
| `distil-large-v3` | jfk **telefónico 8 kHz** | 11 s | 0,72 s | 15,2× | 0,980 | 22 / 22 | **0,00 %** | 0,00 % |
| `distil-large-v3` | largo limpio | 308 s | 28,51 s | 10,8× | 0,989 | 616 / **641** | **4,55 %** | 4,59 % |
| `distil-large-v3` | largo **con ruido** | 308 s | 32,26 s | 9,5× | 0,985 | 616 / **637** | **4,38 %** | 3,95 % |

### El resultado es limpio y no ambiguo

**`large-v3` transcribió los cinco casos con WER = 0,00 %.** No falló ni con ruido blanco
sumado ni con la banda telefónica de 8 kHz. La degradación de audio que preparé **no logró
hacerle cometer un solo error**.

**`distil-large-v3` empata en los clips cortos y falla solo en los largos.** El diagnóstico
exacto, contando cuántas veces aparece el arranque de la frase (la referencia tiene 28):

| Salida | "and so my fellow americans" | "ask not" | Palabras |
|---|---|---|---|
| `large-v3` largo limpio | **28** | **28** | **616** |
| `large-v3` largo con ruido | **28** | **28** | **616** |
| `distil` largo limpio | **29** | **30** | 641 |
| `distil` largo con ruido | **27** | **29** | 637 |

**No es que `distil` entienda peor las palabras: es que pierde el hilo en las costuras entre
ventanas de 30 s.** Duplica un fragmento aquí, se salta otro allá. `large-v3` clava las 28
repeticiones exactas en las dos condiciones.

### Veredicto de E.1

| Criterio | `large-v3` | `distil-large-v3` |
|---|---|---|
| WER en clips cortos (≤30 s) | 0,00 % | **0,00 % — empate** |
| WER en audio largo (308 s) | **0,00 %** | 4,4–4,6 % |
| Factor tiempo real, largo | 2,8× | **10,8× (3,9× más rápido)** |
| VRAM tras cargar | 3 077 MiB | **1 597 MiB** |
| VRAM pico en inferencia | 3 229 MiB | **1 711 MiB** |

**La pérdida de calidad de `distil` SÍ compensa los 1 518 MiB de ahorro, pero solo por
debajo de la ventana de 30 s.** La regla para FileX:

- **Audio ≤ 30 s** (clips, notas de voz, fragmentos): `distil-large-v3`. Misma precisión,
  4× más rápido, la mitad de VRAM. No hay contrapartida.
- **Audio largo** (vídeos, podcasts, reuniones): `large-v3`. Un 4,5 % de WER sobre una
  transcripción de una hora son cientos de palabras inventadas o perdidas, y en subtítulos
  el error se acumula como desincronización. No es aceptable en un conversor.
- Si hacen falta dos flujos simultáneos, la segunda instancia debe ser `distil` **y debe
  atender solo trabajos cortos**.

*(Nota de ruido: la tanda de `distil` salió con un pico del 78 % de utilización de GPU —el
peor de toda la fase—, así que sus tiempos absolutos son los menos fiables del informe. El
WER no depende de la carga de la GPU y no queda afectado.)*

---

## 7. Tarea E.2 — Docling en CPU frente a CUDA: la fase 1 se quedó corta

La fase 1 concluyó que *"el tiempo es prácticamente idéntico (6 % de diferencia)"* entre CPU
y CUDA (13,5 s frente a 14,35 s para tres PDF). **Esa conclusión estaba distorsionada por
medir en frío**: los 13,5 s incluían la carga de los modelos, que domina cuando solo hay tres
documentos de una página.

Midiendo **en caliente**, con n=9 conversiones dentro del mismo proceso, el resultado cambia
por completo.

### Solo maquetación (`do_ocr=False`) — modelos de layout y estructura de tablas

| Documento | CPU (n=9) | CUDA (n=9) | Aceleración |
|---|---|---|---|
| `tipico_texto.pdf` | 0,73 s / 0,68–5,46 | **0,13 s** / 0,12–4,99 | **5,6×** |
| `trivial.pdf` | 0,70 s / 0,67–0,79 | **0,11 s** / 0,10–0,12 | **6,4×** |

*(El máximo del rango en CUDA corresponde a la primera repetición, que carga los modelos.)*

### Pipeline completo con OCR forzado sobre los mismos PDF con capa de texto

| Documento | CPU | CUDA + OCR-GPU | Aceleración |
|---|---|---|---|
| `tipico_texto.pdf` | 2,01 s | **0,58 s** | **3,5×** |
| `trivial.pdf` | 1,14 s | **0,29 s** | **3,9×** |

### Corrección a la fase 1

**La GPU aporta 5,6–6,4× en la parte de maquetación**, no el 6 % que se dedujo en frío. Lo
que la fase 1 midió realmente fue el coste de arranque, no el de inferencia. La
recomendación nº 8 de la fase 1 —*"FileX debería enrutar los PDF pequeños a CPU"*— **debe
revisarse**:

- Es correcta si el sidecar carga los modelos por petición (entonces el arranque domina y la
  GPU no compensa).
- **Es incorrecta si el sidecar es residente**, que es justo lo que la propia fase 1
  recomendaba en su punto nº 1. Con los modelos ya en VRAM, **cada documento sale entre 3,5×
  y 6,4× más rápido en GPU, sea grande o pequeño**.

Las dos recomendaciones de la fase 1 se contradecían entre sí. Con el sidecar residente,
**todo va a GPU**.

---

## 8. Coexistencia y presupuesto de VRAM actualizado

`bench/scripts/coexistencia_ocr.sh` — whisper `large-v3` residente **+** docling con OCR en
CUDA **+** transcodificación NVENC 1080p `p7`, simultáneos:

| Paso | VRAM total | Incremento |
|---|---|---|
| 0 · línea base (escritorio + sesión remota) | 2 271 MiB | — |
| 1 · + whisper `large-v3` residente | 5 346 MiB | +3 075 |
| 2 · + docling con OCR-GPU en marcha | 6 118 MiB | +772 |
| 3 · + NVENC 1080p terminado (rc=0) | 7 406 MiB | +1 288 |
| **Pico total muestreado** | **7 702 MiB** | **+5 431** |
| **VRAM libre restante** | **4 586 MiB** | |

Las tres sesiones ONNX se confirmaron en `['CUDAExecutionProvider', 'CPUExecutionProvider']`
durante toda la prueba, y **docling mantuvo 0,52–0,57 s por documento** con la GPU
compartida: sin degradación medible frente a los 0,48–0,53 s en solitario.

### Presupuesto revisado (sobre los 8 888 MiB que la fase 1 asignó a FileX)

| Partida | MiB | Cambio respecto a fase 1 |
|---|---|---|
| whisper `large-v3` (pico de inferencia) | 3 229 | −1 296 (medición más ajustada) |
| docling CUDA, layout + tablas | 910 | = |
| **OCR en GPU, backend `torch`** | **+728** | **nuevo** (1 555 − 827 ya contabilizados) |
| NVENC 4K | 743 | = |
| **Suma del perfil completo con OCR-GPU** | **5 610** | |
| **Holgura sobrante** | **3 278** | |

**El OCR en GPU cabe con holgura.** Con `onnxruntime-gpu` en vez del backend `torch` el
coste sube a +1 300 MiB y la holgura baja a 2 706 MiB: sigue cabiendo, pero es otro
argumento a favor del backend `torch`.

---

## 9. Qué se instaló y cuánto ocupó

| Concepto | Descarga | En disco | Estado final |
|---|---|---|---|
| `onnxruntime-gpu` 1.29.0 | 148,2 MB | — | **desinstalado** (exige CUDA 13) |
| `onnxruntime-gpu` **1.22.0** | 214,9 MB | 346 MB | **instalado** en `.venv-ai` |
| `easyocr` 1.7.2 + dependencias | ~120 MB | ~130 MB | instalado en `.venv-ai` |
| Modelos de EasyOCR (`~/.EasyOCR`) | 94 MB | 94 MB | descargados |
| Pesos `.pth` de RapidOCR (backend torch) | 32 MB | 84 MB total en `rapidocr/models` | descargados |
| **`.venv-paddle` completo** (`paddlepaddle-gpu` 3.2.0 cu126 + `paddleocr` 3.7.0 + `paddlex`) | ~1,6 GB | **3,73 GB** | instalado |
| Modelos de PaddleOCR (`~/.paddlex`) | 139 MB | 139 MB | descargados |
| Corpus OCR nuevo (`escaneado_d1/d2/d3.pdf`) | — | 136 kB | en `corpus/pdf/` |
| Audio degradado (`bench/salidas-fase2/audio/`) | — | 46 MB | generado |
| Salidas y páginas rasterizadas | — | 65 MB | en `bench/salidas-fase2/` |
| **Consumo neto de disco** | | **≈ 6 GB** | de los 14 GB autorizados |

Crecimiento de los entornos: `.venv-ai` 5,41 → **5,94 GB** (+0,53 GB);
`.venv-paddle` **3,73 GB** (nuevo).
Espacio libre al terminar: **D: 89 GB · C: 79 GB** (parte del consumo de C: es caché de pip,
purgable con `pip cache purge`).

**No se descargó ninguna imagen Docker.** No se tocó `analysis/`, `bench/docker.md` ni
`bench/gpu-fase1.md`.

### Estado final verificado de los entornos

```
.venv-ai      torch 2.6.0+cu124   cuda True
              onnxruntime-gpu 1.22.0  ['TensorrtExecutionProvider','CUDAExecutionProvider','CPUExecutionProvider']
              docling 2.120.3 · rapidocr 3.9.2 · easyocr 1.7.2 · faster-whisper 1.2.1

.venv-paddle  paddle 3.2.0  compiled_with_cuda True  device_count 1
              paddleocr 3.7.0 · paddlex 3.7.2
```

`torch.cuda.is_available()` se comprobó **después de cada una de las cinco instalaciones** y
salió `True` en todas. **La instalación CUDA de PyTorch sobrevivió intacta a toda la fase 2.**

---

## 10. Implicaciones para el diseño de FileX

### 1. El hueco nº 4 está cerrado, y el motor es el que ya estaba instalado

Docling + RapidOCR con `backend="torch"` da OCR en GPU con **cero instalaciones nuevas**,
3,1× más rápido que la ruta de CPU y con salida idéntica carácter a carácter. Ni SnapOtter
(CPU por diseño), ni OCRmyPDF (Tesseract), ni la docling de serie lo ofrecen. **El coste de
integración es una línea de configuración.**

```python
po.ocr_options = RapidOcrOptions(backend="torch", force_full_page_ocr=True)
po.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CUDA)
```

### 2. Seleccionar el backend por dispositivo, no globalmente

| Dispositivo | Backend | Motivo |
|---|---|---|
| CUDA | `torch` | 0,59–0,66 s/pág · +1 555 MiB · sin overrides |
| CPU | `onnxruntime` | 1,6 s/pág; el backend `torch` en CPU es un 37 % más lento |

### 3. Verificar el proveedor sobre una sesión real, no sobre la lista de disponibles

Es el hallazgo operativo más importante de la fase. `onnxruntime-gpu` 1.29.0 anuncia
`CUDAExecutionProvider` en `get_available_providers()` y `get_device() == 'GPU'`, y aun así
crea todas las sesiones en CPU porque le falta `cublasLt64_13.dll`. El *health check* del
sidecar debe crear una sesión de prueba y comprobar `session.get_providers()[0]`, y **fallar
ruidosamente** si no es la EP esperada. Es la versión ONNX del punto nº 7 de la fase 1.

### 4. Si se usa `onnxruntime-gpu`, fijar `<1.24` y añadir el directorio de DLL de torch

`docling-slim` ya lo declara así. La versión que había instalada (1.29.0) estaba fuera de ese
rango. Y en Windows hay que llamar a
`os.add_dll_directory(os.path.dirname(torch.__file__) + "/lib")` antes de importar
`onnxruntime`: las cuDNN 9 de torch bastan y evitan instalar cuDNN aparte.

### 5. El parche `EngineConfig.onnxruntime.use_cuda` es deuda, no solución

Docling 2.120.3 rellena `use_cuda` para los backends `paddle` y `torch` pero **no para
`onnxruntime`**, que es el que usa por defecto. Si FileX toma la ruta onnxruntime tiene que
mantener ese `rapidocr_params` y **probarlo en cada actualización de docling**, porque el día
que lo arreglen aguas arriba el override podría chocar. Motivo suficiente para preferir
`torch`.

### 6. PaddleOCR: la opción de calidad, en un segundo sidecar o en ninguno

Es el único motor con 0 % de error en d2 y es tan rápido como RapidOCR en GPU. Pero cuesta un
venv de 3,7 GB con su propio runtime CUDA, 24,8 s de carga y un proceso separado. **Solo
merece la pena si aparece un caso de negocio de "OCR de alta calidad" que justifique un
segundo sidecar.** Para el conversor general, RapidOCR está a un carácter de distancia por
una fracción del coste.

### 7. EasyOCR: descartado

Es el que más gana con la GPU (17×) y el que peor lo hace: 43 % de error en d2, +2 977 MiB
dentro de docling, y **no determinista entre CPU y GPU** en entradas degradadas. Un conversor
que prometa el mismo resultado en cualquier máquina no puede usarlo.

### 8. Transcripción: `distil` solo para clips cortos

`distil-large-v3` empata con `large-v3` (WER 0,00 %) en clips de 11 s, incluso con ruido
blanco y en banda telefónica, y es 4× más rápido con la mitad de VRAM. Pero en audio de
308 s produce **4,4–4,6 % de WER por duplicar y saltarse fragmentos en las costuras de las
ventanas de 30 s**. Umbral operativo: **`distil` por debajo de 30 s, `large-v3` por
encima.**

### 9. Corregir la recomendación nº 8 de la fase 1

*"FileX debería enrutar los PDF pequeños a CPU"* nace de una medición en frío. Con el sidecar
residente que la propia fase 1 recomienda, la maquetación va **5,6–6,4× más rápida en GPU** y
el pipeline completo **3,5×**, también en documentos de una página. **Con modelos
residentes, todo va a GPU.**

### 10. El corpus de prueba tiene que doler

`patologico_escaneado.pdf` daba 3/3 y distancia 0 a los seis motores: no medía nada. Solo al
bajar a 100 ppp con inclinación de 5°, contraste comprimido y JPEG q40 aparecieron las
diferencias reales (0 % Paddle · 1,3 % RapidOCR · 43 % EasyOCR). **FileX necesita este corpus
en su suite de regresión**, o cualquier cambio de motor pasará las pruebas sin que nadie note
la degradación.

---

## Apéndice — dónde está cada cosa

| Ruta | Contenido |
|---|---|
| `bench/scripts/gen_corpus_ocr.sh` | Genera `escaneado_d1/d2/d3.pdf` con ImageMagick |
| `bench/scripts/ocr_eval.py` | Métrica común: distancia de edición por frase + CER global |
| `bench/scripts/ocr_docling.py` | Docling con motor/backend/dispositivo parametrizables (`SONDA_ORT`, `FORZAR_ORT_CUDA`, `SIN_OCR`, `REPS`) |
| `bench/scripts/bench_ocr_docling.sh` | Matriz de configuraciones de docling con `peak_vram` |
| `bench/scripts/ocr_motor.py` | Banco de motores aislados (rapidocr / easyocr / paddleocr) |
| `bench/scripts/whisper_precision.py` | WER y CER de `large-v3` frente a `distil-large-v3` |
| `bench/scripts/coexistencia_ocr.sh` | whisper residente + OCR-GPU + NVENC simultáneos |
| `bench/logs/fase2_*.log` | Salidas crudas de todas las tandas |
| `bench/salidas-fase2/*__resumen.json` | Tiempos, VRAM y metadatos de cada corrida |
| `bench/salidas-fase2/*.txt` | Texto reconocido por cada motor y documento |
| `bench/salidas-fase2/img/` | Páginas rasterizadas a 200 ppp para el banco aislado |
| `bench/salidas-fase2/audio/` | `jfk_ruido`, `jfk_telefono`, `largo_ruido` |
| `bench/salidas-fase2/tmp_corpus/` | Intermedios de ImageMagick y recortes de inspección visual |
| `corpus/pdf/escaneado_d1.pdf` | 150 ppp, 3°, ruido moderado, JPEG 60 |
| `corpus/pdf/escaneado_d2.pdf` | 100 ppp, −5°, ruido fuerte, contraste bajo, JPEG 40 |
| `corpus/pdf/escaneado_d3.pdf` | 100 ppp, 5°, ruido muy fuerte, contraste muy bajo, JPEG 25 |
| `.venv-paddle/` | Entorno aislado de PaddleOCR (3,73 GB) |
