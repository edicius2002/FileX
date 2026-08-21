# FileX — Especificaciones de agentes para los motores pendientes

**Documento de traspaso.** Cuatro agentes, uno por motor no probado. Escrito para lanzarlos en otra sesión copiando los prompts tal cual. Fecha: 19 de agosto de 2026.

> **Uso rápido:** lee §1 y §2, decide el orden en §7, y copia el prompt del agente que quieras lanzar. Los prompts ya incluyen el contexto que cada agente necesita — no hace falta explicarles nada más.

---

## 1. Por qué existen estos agentes

De los 9 motores de IA clonados, **6 se ejecutaron y 3 no**. Estos agentes cierran ese hueco:

| Motor | Estado | Motivo |
|---|---|---|
| **OCRmyPDF** | ❌ nunca se intentó | Necesita el binario de Tesseract; no hay gestor de paquetes en Windows |
| **marker** | ❌ descartado sin instalar | Se creyó bloqueado por surya. **Diagnóstico erróneo, ver §3.2** |
| **surya** | ❌ instalado, no arranca | Solo se probó su backend por defecto (vLLM). **Tiene cuatro** |
| **MinerU** | ❌ nunca se intentó | Aplazado por peso; su licencia sí se resolvió (es utilizable) |

**El agujero que justifica todo esto:** en la variante de dificultad 3 del corpus **fallaron los tres motores de OCR probados** — RapidOCR 65,8 %, PaddleOCR 75,9 %, EasyOCR 57,0 % de error por carácter. Ninguno resolvió el documento muy degradado. Los motores pendientes son los candidatos que quedan.

---

## 2. Contexto compartido — pégalo en cualquier prompt

Todo agente necesita saber esto. Está verificado; no hay que recomprobarlo.

```
ENTORNO VERIFICADO (19 ago 2026)

Hardware
- RTX 3060, 12 288 MiB, compute capability 8.6, driver 572.61
- 12 núcleos · Windows 10 · Docker 29.4.3
- VRAM realmente disponible: ~8,7 GB (el escritorio ocupa ~2,5 GB de forma permanente)
- Hay una SESIÓN DE ESCRITORIO REMOTO activa: el motor 3D nunca baja del 10 %, con
  picos del 50 %. NO la cierres. NVENC y NVDEC sí están libres.
- Disco: C: 79 GB libres, D: 88 GB libres

Verificado y disponible
- NVIDIA Container Toolkit FUNCIONA: `docker run --gpus all nvidia/cuda:12.4.1-base`
  ve la 3060 con sus 12 288 MiB.
- WSL2 con Ubuntu 26.04 LTS y acceso a GPU (`nvidia-smi` funciona dentro).
- La VM de Docker tiene 2 vCPU y 1,9 GiB por decisión deliberada del usuario
  en su .wslconfig. NO LA CAMBIES ni sugieras cambiarla.

Entornos virtuales existentes — NO ROMPER
- .venv-ai/      torch 2.6.0+cu124 (CUDA: True), docling 2.120.3, faster-whisper 1.2.1,
                 rapidocr 3.9.2, easyocr 1.7.2, surya-ocr 0.22.1, onnxruntime-gpu 1.22.0
- .venv-paddle/  paddleocr 3.7.0 + paddlepaddle-gpu 3.2.0 (aislado a propósito)
- .venv-mcp-md/  markitdown 0.1.7 + markitdown-mcp (mcp~=1.8.0, incompatible con docling)

Corpus (D:\Work\research\FileX\corpus\)
- pdf/tipico_texto.pdf          CON capa de texto extraíble
- pdf/patologico_escaneado.pdf  SIN capa de texto, inclinado 1,7°, con ruido gaussiano
- pdf/escaneado_d1.pdf          degradado nivel 1
- pdf/escaneado_d2.pdf          degradado nivel 2 (150 ppp, más inclinación, JPEG q60)
- pdf/escaneado_d3.pdf          degradado nivel 3 (100 ppp, 3-5°, contraste bajo, JPEG q25)
- video/, audio/, imagen/, datos/ para el resto de categorías

TEXTO DE REFERENCIA de los PDF escaneados (idéntico en las 4 variantes):
  "DOCUMENTO ESCANEADO"
  "Texto que solo existe como pixeles."
  "Debe recuperarse con OCR."

Marcas a batir (CER = tasa de error por carácter, medianas de n=9)
  Motor        dificultad 2    dificultad 3
  RapidOCR        1,3 %          65,8 %
  PaddleOCR       0,0 %          75,9 %
  EasyOCR        43,0 %          57,0 %

Arnés de medición: bench/lib/harness.sh
  gpu_acquire "<etiqueta>" / gpu_release   -> lock EXCLUSIVO de GPU
  measure "etiqueta" N -- comando args...  -> mediana, rango, etiqueta limpia/SUCIA
  peak_vram comando args...                -> VRAM máxima durante la ejecución
```

---

## 3. Reglas comunes a los cuatro agentes

Inclúyelas en todos los prompts.

1. **Un fichero de informe por agente.** Nunca dos agentes escribiendo el mismo fichero. No tocar `analysis/`, ni informes de `bench/` que no sean el propio.
2. **Venv nuevo por motor.** Jamás instalar en `.venv-ai`, `.venv-paddle` ni `.venv-mcp-md`.
3. **Verificar `torch.cuda.is_available()` en `.venv-ai` después de cada instalación.** `pip install surya-ocr` ya degradó torch de `2.6.0+cu124` a `2.13.0+cpu` **sin emitir un solo error**. Si pasa a `False`, abortar esa vía y documentarlo.
4. **Lock de GPU obligatorio** para todo lo que use la tarjeta. Solo un agente a la vez.
5. **Medianas de n≥9.** Con la sesión remota activa todo saldrá etiquetado `SUCIA`; es estructural, no un fallo.
6. **Dos intentos por problema**, luego documentar el error exacto y seguir. **Nada de bucles de reintento.**
7. **Reportar los fallos como fallos.** Un "no se pudo instalar" documentado mide el coste real de integración, que es justo lo que FileX necesita saber.
8. **No cerrar aplicaciones del usuario, no tocar la sesión remota, no tocar el `.wslconfig`, no modificar `repos/`.**

---

## 4. Ficha por motor

### 4.1 Agente A — OCRmyPDF en WSL · **el más barato y el de mayor valor**

| | |
|---|---|
| **Entorno** | WSL2 Ubuntu 26.04 LTS |
| **Instalación** | `sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-spa unpaper pngquant` |
| **GPU** | ❌ No la usa. **No necesita el lock** |
| **Riesgo para lo existente** | **Cero** — otro espacio de nombres del SO, ningún venv de Windows implicado |
| **Entregable** | `bench/ocrmypdf.md` + salidas en `bench/salidas-ocrmypdf/` |
| **Coste de disco** | ~500 MB |

**Lo que se busca no es su OCR sino su preprocesado.** OCRmyPDF delega en Tesseract (CPU), así que como motor de OCR no va a ganar. Su valor está en `--deskew`, `--clean`, `--remove-background`, `--rotate-pages`: corrección de inclinación, eliminación de ruido y rotación automática.

**La prueba realmente interesante es la compuesta:** usar OCRmyPDF **solo como preprocesador** y pasar su salida a RapidOCR y PaddleOCR. Si eso rescata la dificultad 3, la conclusión para FileX no es "añadir OCRmyPDF como motor" sino **"añadir una etapa de preprocesado antes de cualquier OCR"** — que es un hallazgo de arquitectura, no de catálogo.

**Trampa conocida:** el acceso a `/mnt/d/` desde WSL es lento. Copiar el corpus al sistema de ficheros de WSL antes de medir tiempos.

---

### 4.2 Agente B — marker desde el clon · **el diagnóstico anterior era erróneo**

| | |
|---|---|
| **Entorno** | Venv nuevo `.venv-marker` (Windows) |
| **Instalación** | `pip install -e D:\Work\research\FileX\repos\ai-engines\marker` |
| **GPU** | ✅ Sí. **Lock obligatorio** |
| **Entregable** | `bench/marker.md` + salidas en `bench/salidas-marker/` |
| **Coste de disco** | ~4 GB (torch 2.7 + modelos) |

**Contexto que el agente debe recibir.** Un análisis previo concluyó que marker estaba bloqueado por surya. **Es falso.** Leyendo el clon (commit `e1a6226`, 2026-08-07):

- `marker/models.py:13,43` — el backend es un **parámetro público**: `create_model_dict(..., inference_backend: str | None = None)` → `SuryaInferenceManager(method=inference_backend)`. El contenedor vLLM es el valor por defecto, no el único camino.
- `marker/models.py:27,31` — el servidor es **perezoso**: *"only spawns a server when OCR is actually [needed]"*, *"Holds no model; spawns/attaches the server on first call, not here."*
- `marker/builders/ocr.py:82` — *"clean pages already skip OCR entirely via pdftext"*. **Un PDF con capa de texto nunca toca el servidor de inferencia.**
- `marker/builders/ocr.py:80` — su propio código mide rendimiento en llama.cpp (*"~7x on llama.cpp"*): ese backend es una vía soportada de primera clase.

**Único bloqueo real:** `torch>=2.7.0,<3` frente al `2.6.0+cu124` instalado → exige venv propio. No impide nada.

**Plan en dos fases, y la primera es casi gratis:**

1. **Fase 1 — sin servidor de inferencia.** Convertir `corpus/pdf/tipico_texto.pdf` (tiene capa de texto). Debe funcionar **sin arrancar servidor alguno**. Verificar con `nvidia-smi` y con los logs que efectivamente no se lanza. Si esto pasa, marker es utilizable y ya tenemos la respuesta principal.
2. **Fase 2 — solo si la 1 funciona y hay tiempo.** OCR real sobre los escaneados con `inference_backend="llamacpp"`, que necesita el binario `llama-server` (su docstring da instrucciones para Linux/macOS → **encaja mejor en WSL**). **No intentar el backend vLLM**: ya se sabe que reserva 10,4 GB de los 9,7 libres y se cuelga sin excepción.

---

### 4.3 Agente C — surya, reintento con backend y VRAM configurables

| | |
|---|---|
| **Entorno** | Venv nuevo `.venv-surya` (copia limpia; **no usar `.venv-ai`**) |
| **GPU** | ✅ Sí. **Lock obligatorio** |
| **Entregable** | `bench/surya-reintento.md` |
| **Coste de disco** | Vía A: ~2 GB · Vía B: **10–20 GB** (imagen vLLM) |

**Contexto.** La fase 2 concluyó "surya no funciona" tras probar **solo el backend por defecto**. Surya 0.22.1 tiene cuatro: `vllm.py`, `llamacpp.py`, `openai_client.py`, `spawn.py`. Y `settings.py` es un `BaseSettings` de pydantic, así que **todo es configurable por variable de entorno**:

```
SURYA_INFERENCE_BACKEND       # "vllm" | "llamacpp" | None (auto)
VLLM_GPU_MEMORY_UTILIZATION   # 0.85 por defecto -> 10 445 MiB, no cabe
VLLM_DOCKER_IMAGE             # vllm/vllm-openai:v0.20.1
```

**Dos vías, por orden de coste:**

- **Vía A — `SURYA_INFERENCE_BACKEND=llamacpp`.** Sin contenedor, sin reserva del 85 %. Necesita el binario `llama-server` (llama.cpp). **Preferible.**
- **Vía B — `VLLM_GPU_MEMORY_UTILIZATION=0.5`** → 6,1 GB en vez de 10,4. Con los ~2,5 GB del escritorio suman 8,6 de 12: **cabe, pero sin margen**. El toolkit ya está verificado, así que el contenedor sí arrancará. Descarga de 10–20 GB.

**Trampas críticas:**

- **Surya se cuelga sin excepción ni traza** cuando no puede reservar VRAM. **Poner timeout a todo** (por ejemplo 300 s) y matar el proceso; no esperar un error que no va a llegar.
- **Su instalación tumbó CUDA una vez en silencio.** Instalar en venv propio y verificar `.venv-ai` después.
- Si ambas vías fallan, **probar surya ≤0.17.1** en venv aparte: las versiones anteriores a la 0.20 son PyTorch en proceso, sin backends de servidor. Hay 80 versiones publicadas.

---

### 4.4 Agente D — MinerU con el extra `vlm`

| | |
|---|---|
| **Entorno** | Venv nuevo `.venv-mineru` |
| **Instalación** | `pip install "mineru[vlm]"` — **NO `[vllm]`** |
| **GPU** | ✅ Sí. **Lock obligatorio** |
| **Entregable** | `bench/mineru.md` |
| **Coste de disco** | ~6–8 GB estimado (verificar antes de descargar) |

**Contexto.** Se aplazó por peso (71,6k líneas), no por un fallo. Dos cosas lo hacen más barato de lo estimado:

- Su extra `vlm` pide **`torch>=2.6.0,<3`**: **compatible con el torch ya instalado**. No obliga a una versión nueva.
- El extra `vllm` es el pesado (`vllm>=0.10.1.1`). **Evitarlo.**
- Alternativa si pip da problemas: `repos/ai-engines/MinerU/docker/global/` con su `compose.yaml`. Viable ahora que el toolkit está verificado.

**Licencia ya resuelta**, no hay que investigarla: Apache-2.0 con términos adicionales cuyos umbrales (100 M usuarios activos mensuales o 20 M USD mensuales) son irrelevantes. Solo obliga a atribución si se ofrece servicio online.

**Qué medir:** calidad sobre los 4 PDF escaneados frente a Docling (que ya logró distancia de edición 0 en el patológico), VRAM de pico, y **tiempo de carga en frío** — su pila de modelos es el motivo del aplazamiento, así que el dato decisivo es cuánto cuesta tenerlo caliente.

---

## 5. Qué debe contener todo informe

Para que los cuatro sean comparables entre sí y con lo ya medido:

1. **Qué se instaló y cuánto ocupó** (`du -sh` del venv, tamaño de los modelos descargados).
2. **Si arrancó o no**, con el error exacto si no.
3. **Precisión**: distancia de edición y CER contra el texto de referencia, para las 4 variantes de dificultad.
4. **Velocidad**: mediana de n≥9 con su etiqueta `limpia`/`SUCIA`.
5. **VRAM de pico** (`peak_vram`).
6. **Tiempo de carga en frío frente a caliente.**
7. **Verificación de que `.venv-ai` sigue con `torch.cuda.is_available() == True`.**
8. **Veredicto**: ¿entra en FileX, en qué papel, y a qué coste de integración?

---

## 6. Plantilla de prompt

Sustituye lo que va entre `⟨⟩`:

```
Investigación previa del proyecto FileX, un conversor universal de archivos.
Escribe en español. Proyecto: D:\Work\research\FileX\

TAREA: ⟨objetivo del agente, de la ficha §4⟩

[PEGA AQUÍ EL BLOQUE DE CONTEXTO COMPARTIDO DE §2]

CONTEXTO ESPECÍFICO DE ESTE MOTOR:
⟨el apartado correspondiente de §4, incluidas sus trampas⟩

TAREAS CONCRETAS:
⟨el plan por fases de la ficha⟩

ENTREGABLE: UN ÚNICO informe en ⟨bench/xxx.md⟩, más salidas en ⟨bench/salidas-xxx/⟩.
No toques analysis/, ni otros ficheros de bench/, ni corpus/, ni repos/.
El informe debe contener los 8 puntos de §5 de AGENTES-PRUEBAS-PENDIENTES.md.

REGLAS:
[PEGA AQUÍ LAS 8 REGLAS COMUNES DE §3]
```

---

## 7. Orden y paralelización

**El recurso escaso es la GPU: solo un agente a la vez sobre ella.**

| Fase | Agentes | Contención |
|---|---|---|
| **1ª (en paralelo)** | **A · OCRmyPDF (WSL, CPU)** + **B · marker (Windows, GPU)** | Solo compiten por núcleos de CPU. A no necesita el lock |
| **2ª** | **C · surya** | Necesita GPU en exclusiva |
| **3ª** | **D · MinerU** | Necesita GPU en exclusiva |

**Recomendación:** empezar por **A y B juntos**. Son los dos de mayor valor y menor riesgo, y entre ambos responden las dos preguntas abiertas — si el preprocesado rescata la dificultad 3, y si marker es utilizable. C y D son completar el mapa; puedes decidir si merecen la pena **después** de leer los informes de A y B.

Si solo vas a lanzar uno: **el A**. Riesgo cero, esfuerzo trivial, y es el único candidato para el agujero que nadie resolvió.

---

## 8. Documentos de referencia

| Ruta | Para qué |
|---|---|
| `ANALISIS-COMPLETO.md` | El análisis entero del ecosistema, 21 tablas |
| `PLAN-ORQUESTADOR.md` | El plan de construcción de FileX |
| `bench/gpu-fase1.md` | NVENC, VRAM, whisper, docling — y el fallo de surya |
| `bench/gpu-fase2.md` | Los tres motores de OCR y las marcas a batir |
| `bench/referencia-nativa.md` | Patrón oro y 46 reglas de regresión |
| `analysis/surya-marker.md` | Análisis de código de ambos |
| `analysis/OCRmyPDF.md` | Por qué su preprocesado importa |
| `analysis/MinerU.md` | Licencia y peso |
| `bench/lib/harness.sh` | El arnés de medición |
