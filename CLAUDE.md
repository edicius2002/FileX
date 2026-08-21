# CLAUDE.md — reglas de trabajo en FileX

Proyecto de investigación en español. **Escribe todo en español**, incluidos informes y comentarios.

---

## 1. Nunca toques esto

| Qué | Por qué |
|---|---|
| **`.wslconfig`** | Los 2 vCPU y 1,9 GiB de la VM de Docker son decisión deliberada del usuario, con sus motivos escritos en comentarios |
| **`.venv-ai/`, `.venv-paddle/`, `.venv-mcp-md/`, `.venv-marker/`** | Entornos CUDA funcionales y frágiles. **Usarlos para ejecutar sí; instalar en ellos, jamás** |
| **El código fuente de `repos/`** | Son clones de referencia. Instalar dependencias o construir dentro está bien (`repos/` está en `.gitignore`); editar su código no |
| **La sesión de escritorio remoto** | Está activa a propósito. No la cierres |
| **`~/.claude.json`** | Configuración MCP **solo de proyecto**, en `D:\Work\research\FileX\.mcp.json` |
| **`bench/salidas-referencia/referencia.json`** | Es el patrón oro: se lee, no se toca |
| **`bench/scripts/mcp_probe_bin.py`, `bench/salidas-mcp/mcp_probe.py`** | Arneses compartidos. Si necesitas una variante, cópiala a tu directorio de salidas |

**Un fichero de salida por agente.** Dos agentes no escriben nunca el mismo fichero.

## 2. Entorno verificado — no lo recompruebes

RTX 3060 12 288 MiB (compute 8.6, driver 572.61) · 12 núcleos · Windows 10 · Docker 29.4.3 + WSL2 (Ubuntu) · Python 3.11.9 · Node 22.23.2 · Go 1.22.5.

**Nativos:** `ffmpeg` N-121159 (gpl, x264, x265, cuda-llvm), `magick` 7.1.2 Q16-HDRI, `gswin64c` 10.07.

**NO instalados:** vips, LibreOffice, Pandoc, qpdf, Calibre, Inkscape, DuckDB. **No hay gestor de paquetes** (ni winget, ni choco, ni scoop) — lo que falte va en contenedor, no instalado a mano.

**Matices que cuestan tiempo si no se saben:**
- `tesseract.exe` **existe** en `C:\Program Files\Tesseract-OCR\` pero **no está en el PATH**, y solo trae `eng`+`osd`.
- **Ghostscript 10.07 lleva Tesseract y Leptonica compilados dentro**, lo que habilita `-sDEVICE=ocr` y `pdfocr*` — pero **sin datos de idioma**: falla con `Tesseract couldn't load any languages!` si no fijas `TESSDATA_PREFIX`.
- **VRAM realmente disponible: ~8,7 GB de los 12.** El escritorio ocupa ~2,5 GB de forma permanente. NVENC y NVDEC sí están libres.

**Contenedores:** SnapOtter `:1349` (`admin` / `<CONTRASENA-REDACTADA>`), ConvertX `:3100`, Gotenberg `:3200`.

## 3. Cómo se mide aquí

- **Medianas de n≥9**, con `bench/lib/harness.sh`: `measure`, `gpu_acquire`/`gpu_release`, `peak_vram`.
- **Lock de GPU obligatorio** para todo lo que use la tarjeta. Solo un agente a la vez.
- Con la sesión remota activa **todo sale etiquetado `SUCIA`**. Es estructural, no un fallo.
- **Medir con ruido no es medir**: una tanda que coincidió con una descarga dio un error de **7,4×**.
- **Timeouts explícitos en todo.** No dejes procesos colgados: estos motores dejan huérfanos vivos 13 minutos.
- **Dos intentos por problema**, luego documenta el error exacto y sigue. **Nada de bucles de reintento.**

**Marca cada afirmación MEDIDO o PENDIENTE.** No es opcional: es lo que hace útil este repositorio.

**Reporta los fallos como fallos.** Un «no se pudo instalar» documentado mide el coste real de integración, que es justo lo que hay que saber. Y **refutar una conclusión propia es el resultado más valioso que puedes traer** — varios de los mejores hallazgos aquí son autocorrecciones.

## 4. Trampas ya pagadas — no vuelvas a caer

**De medición:**
1. **El «alfa trivial»**: `corpus/imagen/tipico.png` declara canal alfa pero es **enteramente opaco**. Solo exige conservación si `min(alfa) < 1,0`. Usa `alpha.png` para el caso real.
2. **Menor tamaño ≠ mejor conversión.** El GIF con paleta genérica pesa un 35 % *menos* que el bueno.
3. **Opus fuerza 48 kHz** y convierte 8,000 s en 8,0065 s: toda tolerancia por debajo de ±10 ms da falsos fallos.
4. **`txtwrite` emite 1-3 caracteres de basura** en PDF sin texto: el umbral de «conserva texto» es **≥10**, no >0.
5. **`magick compare -metric SSIM` devuelve 0 para imágenes idénticas** en esta build. Usa **PSNR y RMSE**.
6. **No sobremuestrees al rasterizar.** `escaneado_d2/d3.pdf` tienen imagen incrustada a **100 ppp nativos**; el arnés de la fase 2 los rasterizaba a 200 y ese ×2 de interpolación **inventó** las marcas de «fallan los tres motores» en dificultad 3. A ppp nativos, PaddleOCR resuelve d3 con **2,5 % de CER**.
7. **Windows Defender infla el primer arranque** de un binario recién compilado (41 → 110 ms). Calienta antes de medir.

**De entorno:**
8. **`pip install surya-ocr` degradó torch de `2.6.0+cu124` a `+cpu` sin un solo error.** Verifica `torch.cuda.is_available()` en `.venv-ai` **después de cada instalación**.
9. **`onnxruntime-gpu` 1.29.0 exige CUDA 13** y cae a CPU en silencio. Usa **1.22.0**. Y comprueba `session.get_providers()`, **nunca `get_device()`**, que devuelve `'GPU'` mientras corre en CPU.
10. **`mcp~=1.8.0` y `mcp>=2.0.0` no coexisten** en un venv. Un venv por servidor.
11. **Surya 0.22.1 lanza un contenedor vLLM** que reserva el 85 % de la VRAM y se cuelga **sin excepción**. Pon timeout: no llegará un error.
12. **Clonar en Windows** necesita `git -c core.longpaths=true` para algunos repos.

**De herramienta:**
13. **Los heredocs de shell se comen los backslashes** en este entorno. Para generar JSON con rutas de Windows, **escribe un script de Python** y usa barras normales (`D:/Work/...`), que Python acepta.
14. **`git gc` sobre este repo tarda más de 2 minutos.** Lánzalo en segundo plano y **no borres los `tmp_pack_*` mientras haya un `git.exe` vivo**: estarías corrompiendo el repack en curso.

## 5. Reglas de diseño no negociables

Salen de la evidencia y están desarrolladas en `PLAN-ORQUESTADOR.md` §5 y `RESULTADOS-MCP.md`:

- **Invocar motores como proceso separado, sin shell**, con argumentos en array, y **`stdin=DEVNULL`**. El orden importa: `stdin=DEVNULL` primero, las banderas (`-y`, `-nostdin`) después — una disciplina que hay que recordar en cada punto de invocación no es una defensa.
- **Verificar la salida siempre.** Firma real, flujos, propiedades declaradas **y propiedades pedidas frente a obtenidas** (sin este cuarto punto, un redimensionado no solicitado pasa los otros tres).
- **Verificar leyendo cabeceras en proceso, no con `ffprobe`.** Con subprocesos, en el 38 % de los casos verificar cuesta más que convertir; en proceso cuesta el 0,032 %.
- **Sondear capacidades en ejecución, no deducirlas.** `av1_nvenc` aparece listado y no funciona.
- **`-map 0` explícito en ffmpeg.** Por defecto descarta la segunda pista de audio, en silencio.
- **MCP devuelve ruta y metadatos, nunca contenido** — y «contenido» incluye **base64 dentro de un `TextContent`**, que es como aparece de verdad. El criterio es **tokens de respuesta**, no tipos del protocolo.
- **Nunca devolver `stderr` crudo al modelo.** El error de un motor puede dirigir la siguiente acción del agente.
- **Lista blanca de raíces, denegar por defecto**, con el predicado **léxico antes de tocar el disco**, y **un mensaje opaco** para «prohibido» y «no existe».
- **La validación vive en el núcleo, no en la superficie.** FileX tendrá cuatro: CLA, MCP, watcher y API HTTP.

## 6. Peso del repositorio

**No versiones salidas binarias regenerables.** El repositorio ya pagó una vez este error: 986 MB de pack, 99,9 % binario.

Si generas salidas, **borra las grandes al terminar** y deja un `MANIFIESTO.md` con nombre, `sha256`, tamaño y **la orden exacta que las reproduce**. `bench/salidas-referencia/referencia.json` tiene 39 de esas órdenes.

Lo que **sí** se versiona: los `.md`, los scripts, los `.json` de resultados, y **los logs** — son texto barato y son la trazabilidad de cada informe.

El `corpus/` está en **Git LFS**. Tras clonar: `git lfs pull`.
