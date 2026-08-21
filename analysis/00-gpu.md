# GPU: dónde acelera de verdad la RTX 3060 (12 GB, compute capability 8.6)

## El reparto del ecosistema

| Repo | Ficheros con CUDA/NVENC | ¿Acelera? |
|---|---:|---|
| ConvertX | 0 | ❌ |
| VERT | 0 | ❌ (WASM: imposible por diseño) |
| transmute | 0 | ❌ |
| gotenberg | 0 | ❌ |
| morphos | 0 | ❌ |
| Stirling-PDF | 0 | ❌ (571k líneas de Java, ni una) |
| **SnapOtter** | **46** | ✅ parcial |
| docling | 37 | ✅ |
| MinerU | 15 | ✅ |
| surya | 15 | ✅ |
| marker | 7 | ✅ |
| faster-whisper | 5 | ✅ |
| markitdown | 0 | ❌ (no lo necesita) |
| OCRmyPDF | 0 | ❌ (Tesseract es CPU) |

**El ecosistema está partido en dos.** Los orquestadores de conversión ignoran la GPU por completo; los motores de IA documental la usan a fondo. Solo SnapOtter cruza la línea, y de forma incompleta.

## Medido en tu máquina

### Vídeo (ver `bench/results.md`)
| Codificador | Estado | 1080p30, 30 s |
|---|---|---|
| `h264_nvenc` | ✅ | **3 901 ms** |
| `hevc_nvenc` | ✅ | — |
| `av1_nvenc` | ❌ `No capable devices found` | — |
| `libx264` (CPU) | ✅ | 12 852 ms |

**3,3× de aceleración.** Ampere no tiene codificador AV1 por hardware (sí decodificador `av1_cuvid`), pese a que `ffmpeg -encoders` lista `av1_nvenc`: el binario se compiló con soporte que la tarjeta no tiene. **Sondear en ejecución, nunca confiar en la lista de codificadores.**

### Documentos e IA
- **Surya**: `VLLM_DTYPE = "bfloat16"` exige compute capability ≥ 8.0. **Tu 3060 es 8.6**: entra por el camino rápido. Las Turing (T4) no.
- **Docling**: `AcceleratorDevice` con `AUTO/CPU/CUDA/cuda:N/MPS/XPU` y `cuda_use_flash_attention2`, aprovechable en Ampere.
- **Marker**: autodetecta (`torch.cuda.is_available()` → `cuda`).
- **faster-whisper**: `large-v3` en float16 ocupa unos 5 GB. Cabe junto a Surya en 12 GB.

### Presupuesto de VRAM propuesto (12 288 MiB)
| Componente | VRAM aprox. |
|---|---:|
| faster-whisper `large-v3` fp16 | ~5 GB |
| Surya (detección + reconocimiento + maquetación) | ~3-4 GB |
| Margen para NVENC y picos | ~2 GB |
| **Total** | **~11 GB, ajustado pero viable** |

Cargar Docling **y** Surya **y** whisper a la vez es arriesgado. De ahí que el sidecar necesite **descarga por inactividad**: mantener caliente el modelo usado y liberar el resto, en vez de precargar todo.

## Los dos huecos concretos de FileX

1. **OCR en GPU.** SnapOtter bloquea el OCR en CPU por diseño: `ocr-runtime-dispatcher.ts:1033` lanza excepción si `result.device !== "cpu"`. Surya en la 3060 es mucho más rápido y preciso. **Nadie ofrece hoy OCR acelerado en un conversor universal.**
2. **NVENC en conversión de vídeo.** Ningún orquestador lo usa, ni siquiera los que ya integran ffmpeg. Es un cambio de una línea en la invocación con 3,3× de retorno medido.

Ambos son baratos de implementar y ninguno existe en el mercado. Junto con el grafo multi-salto (`00-hueco-multisalto.md`) y MCP, forman los cuatro diferenciadores de FileX.
