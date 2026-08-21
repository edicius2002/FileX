# Manifiesto — salidas-fase2

**Generado:** 2026-08-20  
**Ficheros:** 129  ·  **Peso:** 64.8 MB

Salidas de la fase de medición en GPU. Son **artefactos de medición, no evidencia**:
lo que sostiene las conclusiones es el informe `bench/gpu-fase2.md` y los logs, que sí se
conservan versionados.

## Cómo regenerarlo

```bash
# desde la raíz del proyecto
bash bench/scripts/bench_ocr_docling.sh
bash bench/scripts/coexistencia_ocr.sh
bash bench/scripts/ia_coexistencia.sh
bash bench/scripts/gen_corpus_ocr.sh
```

**Aviso:** requieren GPU y el lock de `bench/lib/harness.sh`. Los **tiempos** no se
reproducen exactamente (la sesión de escritorio remoto los etiqueta `SUCIA`); los
**ficheros** sí.

## Inventario

| Fichero | Bytes | sha256 |
|---|---:|---|
| `base_ort_cpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `base_ort_cpu__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `base_ort_cpu__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `base_ort_cpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `base_ort_cpu__resumen.json` | 1488 | `de5b0bf9268c220c…` |
| `coex_nvenc.mp4` | 13430964 | `59ceadc5dc013dbe…` |
| `coex_ocrgpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `coex_ocrgpu__escaneado_d2.pdf.txt` | 90 | `62881f2d5281ce52…` |
| `coex_ocrgpu__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `coex_ocrgpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `coex_ocrgpu__resumen.json` | 1952 | `90fec6542961bbee…` |
| `docling_cpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cpu__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cpu__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `docling_cpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_cpu__resumen.json` | 1828 | `92e011d04255889b…` |
| `docling_cpu_torch__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cpu_torch__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cpu_torch__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `docling_cpu_torch__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_cpu_torch__resumen.json` | 1823 | `44550259d3283498…` |
| `docling_cuda_ocrcpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cuda_ocrcpu__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cuda_ocrcpu__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `docling_cuda_ocrcpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_cuda_ocrcpu__resumen.json` | 1882 | `5e24d103d888c2ed…` |
| `docling_cuda_ocrgpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cuda_ocrgpu__escaneado_d2.pdf.txt` | 90 | `62881f2d5281ce52…` |
| `docling_cuda_ocrgpu__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `docling_cuda_ocrgpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_cuda_ocrgpu__resumen.json` | 2001 | `6c46b49870f00bbb…` |
| `docling_cuda_torch__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cuda_torch__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_cuda_torch__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `docling_cuda_torch__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_cuda_torch__resumen.json` | 1835 | `d2f7c7c0bf0dd639…` |
| `docling_easyocr_cpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_easyocr_cpu__escaneado_d2.pdf.txt` | 85 | `518fbde1860490e0…` |
| `docling_easyocr_cpu__escaneado_d3.pdf.txt` | 22 | `3cb0297f006d96be…` |
| `docling_easyocr_cpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_easyocr_cpu__resumen.json` | 1850 | `9857c39f84bfe388…` |
| `docling_easyocr_gpu__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `docling_easyocr_gpu__escaneado_d2.pdf.txt` | 85 | `518fbde1860490e0…` |
| `docling_easyocr_gpu__escaneado_d3.pdf.txt` | 22 | `3cb0297f006d96be…` |
| `docling_easyocr_gpu__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `docling_easyocr_gpu__resumen.json` | 1854 | `5a2f22143167c4d0…` |
| `lay_cpu__resumen.json` | 1148 | `70326f99b3e243db…` |
| `lay_cpu__tipico_texto.pdf.txt` | 159 | `c5a1bf66f68bfc42…` |
| `lay_cpu__trivial.pdf.txt` | 0 | `e3b0c44298fc1c14…` |
| `lay_cuda__resumen.json` | 1157 | `779c0a2025b30f44…` |
| `lay_cuda__tipico_texto.pdf.txt` | 159 | `c5a1bf66f68bfc42…` |
| `lay_cuda__trivial.pdf.txt` | 0 | `e3b0c44298fc1c14…` |
| `maq_cpu__resumen.json` | 1150 | `b2af603e4b165cfc…` |
| `maq_cpu__tipico_texto.pdf.txt` | 136 | `b5070854b4964dc5…` |
| `maq_cpu__trivial.pdf.txt` | 10 | `5c968c16325c15a7…` |
| `maq_cuda__resumen.json` | 1278 | `e8f62849673c50dd…` |
| `maq_cuda__tipico_texto.pdf.txt` | 136 | `b5070854b4964dc5…` |
| `maq_cuda__trivial.pdf.txt` | 10 | `5c968c16325c15a7…` |
| `motor_easyocr_cpu__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_easyocr_cpu__escaneado_d2.txt` | 80 | `813f79c6609fb6ff…` |
| `motor_easyocr_cpu__escaneado_d3.txt` | 64 | `45dcf6e37b1e9e3e…` |
| `motor_easyocr_cpu__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_easyocr_cpu__resumen.json` | 1552 | `56237f9aa7ba5634…` |
| `motor_easyocr_cuda__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_easyocr_cuda__escaneado_d2.txt` | 80 | `813f79c6609fb6ff…` |
| `motor_easyocr_cuda__escaneado_d3.txt` | 67 | `fb9aaca95cd51d30…` |
| `motor_easyocr_cuda__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_easyocr_cuda__resumen.json` | 1547 | `ff0e2d3b56a01c37…` |
| `motor_paddleocr_cpu__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cpu__escaneado_d2.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cpu__escaneado_d3.txt` | 19 | `9a86f1bb995dbf3f…` |
| `motor_paddleocr_cpu__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cpu__resumen.json` | 1600 | `e040587b21e9ebc3…` |
| `motor_paddleocr_cuda__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cuda__escaneado_d2.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cuda__escaneado_d3.txt` | 19 | `9a86f1bb995dbf3f…` |
| `motor_paddleocr_cuda__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_paddleocr_cuda__resumen.json` | 1596 | `5b087c86e72c508e…` |
| `motor_rapidocr_cpu__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_rapidocr_cpu__escaneado_d2.txt` | 81 | `3145fb5f6393fd17…` |
| `motor_rapidocr_cpu__escaneado_d3.txt` | 23 | `9094ddeb57ae681d…` |
| `motor_rapidocr_cpu__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_rapidocr_cpu__resumen.json` | 1493 | `fe65bf2afb119857…` |
| `motor_rapidocr_cuda__escaneado_d1.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_rapidocr_cuda__escaneado_d2.txt` | 81 | `3145fb5f6393fd17…` |
| `motor_rapidocr_cuda__escaneado_d3.txt` | 27 | `e3aad76c3110e918…` |
| `motor_rapidocr_cuda__patologico_escaneado.txt` | 81 | `b7d0bb79821d94a1…` |
| `motor_rapidocr_cuda__resumen.json` | 1499 | `9fecd92413728f88…` |
| `ort_gpu_cuda__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `ort_gpu_cuda__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `ort_gpu_cuda__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `ort_gpu_cuda__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `ort_gpu_cuda__resumen.json` | 1812 | `35653a76ceafb3bc…` |
| `sonda_cuda__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `sonda_cuda__escaneado_d2.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `sonda_cuda__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `sonda_cuda__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `sonda_cuda__resumen.json` | 1797 | `063557f2de5c3f93…` |
| `sonda_cuda_forzado__escaneado_d1.pdf.txt` | 87 | `91b56f22d3dcb899…` |
| `sonda_cuda_forzado__escaneado_d2.pdf.txt` | 90 | `62881f2d5281ce52…` |
| `sonda_cuda_forzado__escaneado_d3.pdf.txt` | 40 | `7c0320ad7a9e323f…` |
| `sonda_cuda_forzado__patologico_escaneado.pdf.txt` | 81 | `b7d0bb79821d94a1…` |
| `sonda_cuda_forzado__resumen.json` | 1995 | `f49ceb3071e9683b…` |
| `whisper2_distil-large-v3_jfk_limpio.txt` | 108 | `d5607440635b0e07…` |
| `whisper2_distil-large-v3_jfk_ruido.txt` | 108 | `d5607440635b0e07…` |
| `whisper2_distil-large-v3_jfk_telefono.txt` | 108 | `d5607440635b0e07…` |
| `whisper2_distil-large-v3_largo_limpio.txt` | 3184 | `f9069f5cd2f54ac3…` |
| `whisper2_distil-large-v3_largo_ruido.txt` | 3150 | `4b23cf4ac781450f…` |
| `whisper2_distil-large-v3_resumen.json` | 2558 | `93ac517dbc5399db…` |
| `whisper2_large-v3_jfk_limpio.txt` | 108 | `37d003a932256f11…` |
| `whisper2_large-v3_jfk_ruido.txt` | 108 | `37d003a932256f11…` |
| `whisper2_large-v3_jfk_telefono.txt` | 108 | `37d003a932256f11…` |
| `whisper2_large-v3_largo_limpio.txt` | 3051 | `4350536dfcb594cb…` |
| `whisper2_large-v3_largo_ruido.txt` | 3041 | `a7f48b59521d594b…` |
| `whisper2_large-v3_resumen.json` | 2476 | `97d1a3a55daa6a3b…` |
| `audio/jfk_ruido.flac` | 1602709 | `b16656831ed0cdf3…` |
| `audio/jfk_telefono.flac` | 321229 | `0030f2cd2c8369ca…` |
| `audio/largo_ruido.flac` | 44598140 | `f725fef9919b5339…` |
| `img/escaneado_d1.png` | 711071 | `e91bcf0222fa38ec…` |
| `img/escaneado_d2.png` | 431185 | `ad2e6a1a2c734fb9…` |
| `img/escaneado_d3.png` | 486598 | `36f4543e621c4551…` |
| `img/patologico_escaneado.png` | 5286954 | `b36c695bb075d096…` |
| `tmp_corpus/d1_crop.png` | 32130 | `900e22fdfcf05833…` |
| `tmp_corpus/d2_crop.png` | 351031 | `f7d487e173f4f6c7…` |
| `tmp_corpus/d3_crop.png` | 397410 | `f65d662bd9ae4fcb…` |
| `tmp_corpus/escaneado_d1.jpg` | 82034 | `ab09c0093838b7d4…` |
| `tmp_corpus/escaneado_d2.jpg` | 39144 | `f00453acc9dc00ac…` |
| `tmp_corpus/escaneado_d3.jpg` | 38080 | `bb97cdbfdf5204d4…` |
| `tmp_corpus/master.png` | 42151 | `c0965578062b3115…` |
