# Fase 2 — Mediciones en la máquina real

Hardware: RTX 3060 12 GB (compute capability **8.6**, driver 572.61) · Windows 10 · Docker 29.4.3 · Python 3.11.9 · Node 22.23.2 · Go 1.22.5
FFmpeg: build N-121159 con `--enable-gpl --enable-libx264 --enable-libx265 --enable-cuda-llvm`

## 1. NVENC — qué acelera de verdad la 3060

| Codificador | Resultado |
|---|---|
| `h264_nvenc` | ✅ funciona |
| `hevc_nvenc` | ✅ funciona |
| `av1_nvenc` | ❌ **`No capable devices found`** |

`av1_nvenc` aparece listado en `ffmpeg -encoders` porque el binario se compiló con soporte, pero **Ampere (GA106) no tiene codificador AV1 por hardware** — solo decodificador (`av1_cuvid` sí está). Confirmado ejecutándolo, no asumido.

**Regla para FileX:** las capacidades deben **sondearse en tiempo de ejecución**, no deducirse de `ffmpeg -encoders`. Un intento fallido de `av1_nvenc` debe degradar automáticamente a `libsvtav1` en CPU.

### Transcodificación 1080p30, 30 s, 4 Mbps
| Codificador | Tiempo |
|---|---|
| `libx264 -preset medium` (CPU) | 12 852 ms |
| `h264_nvenc -preset p4` (GPU) | **3 901 ms** |

**Aceleración: 3,3×**, incluyendo decodificación y arranque del proceso. Con decodificación también en GPU (`-hwaccel cuda`) la ventaja crece.

## 2. Arranque en frío — el dato que decide el lenguaje del núcleo

Media de 25 ejecuciones **tras calentamiento** (crítico: sin calentar, Windows Defender inflaba el binario Go recién compilado de 41 ms a 110 ms).

| Proceso | Tiempo | Sobre el suelo |
|---|---|---|
| `cmd /c exit` (suelo de creación de proceso en Windows) | 49 ms | — |
| Go, binario compilado | **41 ms** | ~0 |
| Python, intérprete desnudo | 60 ms | +19 ms |
| Node.js | 74 ms | +33 ms |
| Python + `argparse,json,pathlib,subprocess` | 85 ms | +44 ms |
| **`ffmpeg -version`** (solo arrancar el motor) | **61 ms** | +20 ms |
| **`magick` convirtiendo un PNG 64×64** | **73 ms** | +32 ms |

### Interpretación — corrige la intuición habitual
1. **En Windows, crear un proceso cuesta ~40-50 ms haga lo que haga.** Es el suelo, y no depende del lenguaje.
2. **Elegir Go/Rust en vez de Python ahorra ~44 ms por invocación.** Real, pero modesto.
3. **Cualquier conversión arranca además un motor externo**: ffmpeg cuesta 61 ms solo en existir, magick 73 ms para una imagen de 64×64 (de los cuales ~30 ms son trabajo útil).

Es decir: una invocación de CLI cuesta **núcleo + motor ≈ 100-160 ms**, y el lenguaje del núcleo solo controla ~40 ms de esa cifra.

4. **Para el servidor MCP, el arranque en frío es casi irrelevante**: el proceso arranca una vez y permanece vivo. La ventaja de Rust/Go se cobra solo en la CLI y el watcher.

**Conclusión:** el argumento "Rust por el arranque" es mucho más débil de lo que parecía. La palanca real no es el lenguaje, es **evitar procesos**: mantener vivos el sidecar de IA y los motores caros (LibreOffice tarda segundos en arrancar; Gotenberg existe precisamente para eso).

## 3. Corpus de prueba generado (`corpus/`)
17 ficheros en 5 categorías, incluidos los casos patológicos que separan proyectos:
- `pdf/patologico_escaneado.pdf` — **sin capa de texto** (verificado con `gswin64c -sDEVICE=txtwrite`: salida vacía), inclinado 1,7° y con ruido gaussiano. Caso OCR puro.
- `pdf/tipico_texto.pdf` — con capa de texto extraíble (verificado). Contraste para decidir OCR vs extracción directa.
- `video/patologico_2pistas.mkv` — 2 pistas de audio, para probar el mapeo de flujos.
- `imagen/patologico_16bit.tif` — 4000×3000 a 16 bits, 72 MB. Prueba de memoria y de pérdida de profundidad de color.
- `datos/patologico_bom.csv` — BOM UTF-8, comas dentro de campo, comillas escapadas, salto de línea embebido y caracteres no ASCII.

## 4. Motores presentes y ausentes en la máquina
Instalados: **ffmpeg** (con NVENC y GPL), **ImageMagick 7.1.2**, **Ghostscript 10.07**, Node 22, Go 1.22.5, CUDA toolkit 11.2, Docker, WSL2 (Ubuntu).
Ausentes: **libvips, LibreOffice, Pandoc, Tesseract, qpdf, Calibre, Inkscape, DuckDB, uv, bun, cargo**.

Con ~4 de los ~12 motores del ecosistema presentes, `can_register()` (el patrón de transmute) deja de ser un detalle: **es la diferencia entre arrancar con capacidades reducidas o no arrancar**.
