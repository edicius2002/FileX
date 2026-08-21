# SnapOtter — `snapotter-hq/SnapOtter`

2.2k ⭐ · **AGPL-3.0 + open-core comercial** · TypeScript monorepo + sidecar Python · ~198k líneas TS en 563 ficheros · 100+ commits/30d · creado 2026-03-29

**Veredicto: es el competidor real y la mejor referencia arquitectónica, pero NO es viable como base. Copiar el patrón, no el repositorio.**

## 1. Qué resuelve
"200+ herramientas en 5 modalidades" (imagen, vídeo, audio, PDF, documentos): convierte, comprime, OCR, transcribe, quita metadatos, y ejecuta IA local. UI web + REST API + pipelines, todo en Docker. Se posiciona explícitamente contra CloudConvert, Smallpdf, TinyPNG y Otter.ai.

Cubre **11 de tus 12 categorías**. Lo que no tiene: **CLI, watcher y MCP**. Los 5 resultados de "mcp" en el repo son falsos positivos (`docs.ts`, `.dockerignore`, configs de Stryker). **No existe servidor MCP.**

## 2. Arquitectura — la parte valiosa
Monorepo: `apps/{api,web,docs,landing,demo}` + `packages/{ai,doc-engine,image-engine,media-engine,enterprise,shared}`.

**Ya implementa el híbrido núcleo-TS + sidecar-Python que se planteaba para FileX**:
- `packages/ai/src/bridge.ts` (~900 líneas) define la clase **`PythonDispatcher`** (`bridge.ts:280`), que mantiene vivo un proceso `dispatcher.py`. El `spawn(pythonBin, [scriptPath, ...args])` con fallback a `python3` vive en `runPerRequest` (`bridge.ts:648`) y es la **ruta de respaldo**, no la principal: el código lo dice literalmente en `bridge.ts:896-919` — *"Try persistent dispatcher first"* y, si el dispatcher muere, *"Fall back to per-request spawning"*.
- `packages/ai/python/` contiene los scripts reales (`dispatcher.py`, `transcribe.py`, `colorize.py`, `doc_*.py`…).
- `packages/ai/src/ocr-runtime-dispatcher.ts` (~1000 líneas) mantiene otro proceso persistente (`OcrRuntimeManager`) para el runtime de OCR.

> **Corrección.** Una versión anterior de este análisis afirmaba que `bridge.ts` arrancaba un proceso por invocación frente a un dispatcher de OCR persistente. **Es falso**: ambas rutas son persistentes. La asimetría real es otra —venv mutable compartido frente a runtime inmutable y firmado— y es lo que justifica la existencia de `venv-lock.ts`.

Un comentario en `apps/api/src/lib/env.ts:70` explica por qué el sidecar está aislado: *"torch/CUDA reserve huge virtual space"*. Es exactamente el problema que obliga a separar el proceso de IA del núcleo.

**Esto es la validación independiente más fuerte de la arquitectura propuesta para FileX**: un equipo con 100 commits/mes llegó a la misma conclusión.

### Pero no gestionan la VRAM en absoluto
No hay una sola consulta proactiva de memoria de GPU en todo el repositorio. Las cinco coincidencias de "memory" relacionadas con CUDA son **regex de detección de errores** (`/out of memory|cudaerrormemoryallocation|bad_alloc/i` en `bridge.ts:99` y `background-removal.ts:33`) más un fichero de test: SnapOtter *reacciona* a un OOM, nunca *pregunta* cuánta memoria queda. `nvidia-smi` se usa solo para obtener el nombre de la tarjeta (`packages/ai/python/gpu.py:18`).

Peor aún para el caso de FileX: `dispatcher.py:290` ejecuta cada petición con `exec(code, module_globals)` sobre un espacio de nombres **nuevo**, así que solo sobrevive la caché de imports de Python — **los pesos de los modelos se recargan en cada llamada**. El runtime de OCR sí los cachea, pero sin política de desalojo.

Sus gates de memoria son de RAM del cgroup y **se desactivan en anfitriones con GPU** (`hq-memory-gate.ts:32`).

**Consecuencia directa para FileX:** ninguna de esas dos políticas sobrevive a una 3060 de 12 GB compartida con el escritorio, donde el presupuesto real ronda los 9 GB. FileX necesita lo que SnapOtter no tiene: un **registro LRU de modelos acotado por bytes de VRAM y con TTL de inactividad**.

## 3. GPU — dónde acelera y dónde renuncia
CUDA vía compose específico. Acelera: **eliminación de fondo, upscaling y transcripción**.

**El OCR está bloqueado en CPU por diseño**, no por omisión. En `ocr-runtime-dispatcher.ts:1028-1040`, `validateReadinessResult()` **lanza excepción** si el runtime reporta otra cosa:
```js
result.device !== "cpu" ||          // ← rechaza cualquier resultado en GPU
  ...
throw new Error("Accurate OCR runtime returned a malformed readiness result");
```
El README lo confirma: *"OCR deliberately uses the same portable CPU runtime on CPU-only and NVIDIA hosts"*. Priorizan reproducibilidad sobre velocidad.

Transcripción (`packages/ai/python/transcribe.py`): faster-whisper/CTranslate2, `cuda+float16` si hay GPU, `cpu+int8` si no — pero el modelo empaquetado es **`faster-whisper-small`**, no `large-v3`. Techo de calidad autoimpuesto por tamaño de imagen Docker.

**Hueco para FileX (doble):** OCR en GPU (Surya/PaddleOCR sobre la 3060) y transcripción con `large-v3` en fp16 — los 12 GB dan de sobra para ambos. Es la ventaja más defendible que se ha encontrado.

## 4. Licencia — el motivo real del descarte
Open-core con **doble licencia**:
- Todo AGPL-3.0 **excepto** `packages/enterprise/` (licencia comercial propietaria).
- **CLA obligatorio**: el contribuidor concede a SnapOtter derecho irrevocable a redistribuir su código *"under any license, including the commercial license we sell"*.

Consecuencias prácticas: partir de su código obliga a AGPL, incluso ofreciendo FileX solo por red. Contribuir aguas arriba significa alimentar gratis el activo comercial de una empresa. Y mantener un fork divergente frente a 100 commits/mes es insostenible en solitario.

## 5. Salud
El repo más activo del conjunto (100+ commits/30d), CI, OpenSSF Best Practices, Trivy, Stryker (mutation testing), release automatizada, Discord, sponsors. Es un producto de empresa, no un proyecto de fin de semana. **Va a seguir creciendo — competir de frente en su terreno (UI web self-hosted) es perder.**

## 6. Qué extraer para FileX
1. **El patrón de sidecar persistente** (`bridge.ts` + `ocr-runtime-dispatcher.ts`): un proceso Python vivo con los modelos cargados, no un arranque por invocación. Resuelve el arranque en frío, que es *la* métrica crítica para un MCP.
2. **La separación por modalidad** en paquetes (`doc-engine`/`image-engine`/`media-engine`).
3. **El aislamiento del proceso IA** por el consumo de memoria virtual de torch/CUDA.
4. **Sus dos renuncias como oportunidad**: OCR en CPU y whisper-small.
5. **Su hueco de producto**: es UI-first. FileX debe ser **agent-first** (MCP + CLI + watcher). No compiten por el mismo usuario.
