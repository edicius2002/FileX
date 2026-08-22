# Tablas de `bench/corpus-d4.md`

Generado por `tablas_d4.py` a partir de los `.json` de `json/`. Todo son medianas de n=9 salvo el cribado, que es n=1.

## T1 · Cribado de candidatas (n=1) — CER con acentos

| documento | PaddleOCR v6 medium | RapidOCR v5 mobile | EasyOCR | Docling+RapidOCR torch (v6 small) |
|---|---:|---:|---:|---:|
| `d4_limpio` | 0.00 % | 1.17 % | 0.50 % | 0.00 % |
| `escaneado_d4a` | 0.00 % | 1.51 % | 0.34 % | 7.05 % |
| `escaneado_d4b` | 0.17 % | 2.18 % | 27.68 % | 18.46 % |
| `escaneado_d4c` | 0.67 % | 15.60 % | 15.10 % | 22.99 % |
| `escaneado_d4d` | 19.30 % | 41.78 % | 61.41 % | 36.91 % |
| `escaneado_d4e` | 70.97 % | 92.45 % | 73.32 % | 88.59 % |
| `escaneado_d4f` | 0.67 % | 6.04 % | 17.95 % | 22.15 % |
| `abl_d4d_blur12` | 2.68 % | 19.30 % | 55.37 % | 30.37 % |
| `abl_d4d_jq45` | 24.66 % | 41.95 % | 60.07 % | 34.40 % |
| `abl_d4d_niv20` | 3.69 % | 31.38 % | 56.54 % | 35.40 % |
| `abl_d4d_rui35` | 36.24 % | 35.91 % | 56.54 % | 35.07 % |
| `abl_d4d_ang0` | 8.05 % | 40.60 % | 39.77 % | 36.24 % |

## T2 · Validación de la familia d4 (n=9) — CER con acentos / CER ascii

| documento | PaddleOCR v6 medium | RapidOCR v5 mobile | EasyOCR | Docling+RapidOCR torch |
|---|---:|---:|---:|---:|
| `d4_limpio` | 0.00 / 0.00 | 1.17 / 0.50 | 0.50 / 0.50 | 0.00 / 0.00 |
| `escaneado_d4a` | 0.00 / 0.00 | 1.51 / 0.67 | 0.34 / 0.34 | 7.05 / 6.71 |
| `escaneado_d4b` | 0.17 / 0.00 | 2.18 / 0.34 | 27.68 / 27.18 | 18.46 / 18.12 |
| `escaneado_d4c` | 0.67 / 0.00 | 15.60 / 11.91 | 15.10 / 13.76 | 22.99 / 22.48 |
| `escaneado_d4` | 19.30 / 18.46 | 41.78 / 38.59 | 61.41 / 59.56 | 36.91 / 36.24 |
| `escaneado_d4e` | 70.97 / 70.47 | 92.45 / 92.11 | 73.32 / 72.32 | 88.59 / 88.42 |
| `escaneado_d4f` | 0.67 / 0.00 | 6.04 / 2.18 | 17.95 / 16.11 | 22.15 / 21.98 |

## T3 · Cuánto esconde la métrica sin acentos

`dist_acentos − dist_ascii` = caracteres de error que `ocr_eval.py` **no ve**. `acentos_salida/acentos_ref` = cuántos caracteres acentuados sobreviven.

| motor | documento | dist. con acentos | dist. ascii | ocultos | acentos recuperados |
|---|---|---:|---:|---:|---:|
| PaddleOCR v6 medium | `d4_limpio` | 0 | 0 | **0** | 35/35 |
| PaddleOCR v6 medium | `escaneado_d4` | 115 | 110 | **5** | 19/35 |
| PaddleOCR v6 medium | `escaneado_d4a` | 0 | 0 | **0** | 35/35 |
| PaddleOCR v6 medium | `escaneado_d4b` | 1 | 0 | **1** | 34/35 |
| PaddleOCR v6 medium | `escaneado_d4c` | 4 | 0 | **4** | 31/35 |
| PaddleOCR v6 medium | `escaneado_d4e` | 423 | 420 | **3** | 4/35 |
| PaddleOCR v6 medium | `escaneado_d4f` | 4 | 0 | **4** | 31/35 |
| RapidOCR v5 mobile | `d4_limpio` | 7 | 3 | **4** | 31/35 |
| RapidOCR v5 mobile | `escaneado_d4` | 249 | 230 | **19** | 0/35 |
| RapidOCR v5 mobile | `escaneado_d4a` | 9 | 4 | **5** | 30/35 |
| RapidOCR v5 mobile | `escaneado_d4b` | 13 | 2 | **11** | 23/35 |
| RapidOCR v5 mobile | `escaneado_d4c` | 93 | 71 | **22** | 6/35 |
| RapidOCR v5 mobile | `escaneado_d4e` | 551 | 549 | **2** | 0/35 |
| RapidOCR v5 mobile | `escaneado_d4f` | 36 | 13 | **23** | 10/35 |
| EasyOCR | `d4_limpio` | 3 | 3 | **0** | 35/35 |
| EasyOCR | `escaneado_d4` | 366 | 355 | **11** | 4/35 |
| EasyOCR | `escaneado_d4a` | 2 | 2 | **0** | 35/35 |
| EasyOCR | `escaneado_d4b` | 165 | 162 | **3** | 33/35 |
| EasyOCR | `escaneado_d4c` | 90 | 82 | **8** | 22/35 |
| EasyOCR | `escaneado_d4e` | 437 | 431 | **6** | 1/35 |
| EasyOCR | `escaneado_d4f` | 107 | 96 | **11** | 20/35 |
| Docling+RapidOCR torch | `d4_limpio` | 0 | 0 | **0** | 35/35 |
| Docling+RapidOCR torch | `escaneado_d4a` | 42 | 40 | **2** | 29/35 |
| Docling+RapidOCR torch | `escaneado_d4b` | 110 | 108 | **2** | 33/35 |
| Docling+RapidOCR torch | `escaneado_d4c` | 137 | 134 | **3** | 23/35 |
| Docling+RapidOCR torch | `escaneado_d4` | 220 | 216 | **4** | 17/35 |
| Docling+RapidOCR torch | `escaneado_d4e` | 528 | 527 | **1** | 2/35 |
| Docling+RapidOCR torch | `escaneado_d4f` | 132 | 131 | **1** | 24/35 |

## T4 · Fase 3 — la asimetría, cruzando tamaño / idioma / tubería

| configuración | d3 (100 ppp) | d4c (200 ppp) | d4 (200 ppp) |
|---|---:|---:|---:|
| `paddleocr_cuda_f3_detM_recS` | 8.86 % | 1.01 % | 17.45 % |
| `paddleocr_cuda_f3_detS_recM` | 3.80 % | 1.01 % | 22.99 % |
| `paddleocr_cuda_f3_lang_en` | 2.53 % | 0.67 % | 19.30 % |
| `paddleocr_cuda_f3_lang_es` | 2.53 % | 0.67 % | 19.30 % |
| `paddleocr_cuda_f3_v5_ch` | 25.32 % | 20.64 % | 40.94 % |
| `paddleocr_cuda_f3_v5_en` | 7.59 % | 3.86 % | 30.37 % |
| `paddleocr_cuda_f3_v5_latin` | 6.33 % | 1.51 % | 17.28 % |
| `paddleocr_cuda_f3_v6med` | 2.53 % | 0.67 % | 19.30 % |
| `paddleocr_cuda_f3_v6small` | 3.80 % | 1.01 % | 19.80 % |
| `paddleocr_cuda_f3_v6tiny` | 43.04 % | 4.87 % | 31.88 % |
| `paddleocr_cuda_f3d_v6med_box05` | 2.53 % | 0.67 % | 19.30 % |
| `paddleocr_cuda_f3d_v6med_lim736` | 3.80 % | 0.67 % | 19.30 % |
| `paddleocr_cuda_f3d_v6sml_lim736` | 5.06 % | 1.01 % | 19.80 % |
| `rapidocr_cuda_f3_v4_detch` | 58.23 % | 18.79 % | 44.30 % |
| `rapidocr_cuda_f3_v4_deten` | 75.95 % | 10.74 % | 44.63 % |
| `rapidocr_cuda_f3_v4_detmul` | 46.84 % | 15.27 % | 61.07 % |
| `rapidocr_cuda_f3_v5m_recch` | 77.22 % | 15.60 % | 41.78 % |
| `rapidocr_cuda_f3_v5m_reclat` | 75.95 % | 9.56 % | 36.24 % |
| `rapidocr_cuda_f3_v6medium` | 3.80 % | 14.09 % | 22.82 % |
| `rapidocr_cuda_f3_v6small` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3_v6tiny` | 43.04 % | 4.19 % | 39.60 % |
| `rapidocr_cuda_f3b_sm_box03` | 75.95 % | 7.05 % | 30.54 % |
| `rapidocr_cuda_f3b_sm_lim1200` | 49.37 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3b_sm_nocls` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3b_sm_score00` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3b_sm_score01` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3b_sm_todo` | 75.95 % | 6.71 % | 30.54 % |
| `rapidocr_cuda_f3b_sm_unc20` | 75.95 % | 29.53 % | 37.25 % |
| `rapidocr_cuda_f3b_v5m_score00` | 77.22 % | 15.10 % | 41.78 % |
| `rapidocr_cuda_f3b_v5m_todo` | 75.95 % | 20.30 % | 41.44 % |
| `rapidocr_cuda_f3c_med_lim1200` | 75.95 % | 14.09 % | 22.82 % |
| `rapidocr_cuda_f3c_sm_lim1200_box03` | 40.51 % | 7.05 % | 30.54 % |
| `rapidocr_cuda_f3c_sm_lim1600` | 51.90 % | 23.83 % | 36.91 % |
| `rapidocr_cuda_f3c_sm_lim2000` | 58.23 % | 12.08 % | 43.79 % |
| `rapidocr_cuda_f3c_sm_lim960` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3c_v5m_lim1200` | 77.22 % | 15.60 % | 41.78 % |
| `rapidocr_cuda_f3c_v5m_lim2000` | 58.23 % | 8.22 % | 42.45 % |
| `rapidocr_cuda_f3d_med_lim64` | 3.80 % | 14.09 % | 22.82 % |
| `rapidocr_cuda_f3d_sm_lim64` | 75.95 % | 29.36 % | 36.91 % |
| `rapidocr_cuda_f3d_sm_lim64_box06` | 75.95 % | 35.91 % | 36.91 % |
| `rapidocr_cuda_f3d_v5m_lim64` | 77.22 % | 15.60 % | 41.78 % |
| `rapidocr_cuda_f3e_med_paddle` | 2.53 % | 9.56 % | 23.15 % |
| `rapidocr_cuda_f3e_sm_normBGR` | 8.86 % | 1.01 % | 18.79 % |
| `rapidocr_cuda_f3e_sm_normRGB` | 11.39 % | 1.01 % | 20.13 % |
| `rapidocr_cuda_f3e_sm_paddle` | 3.80 % | 1.17 % | 18.62 % |
| `rapidocr_cuda_f3e_sm_post` | 75.95 % | 32.21 % | 36.58 % |
| `rapidocr_cuda_f3e_v5m_paddle` | 54.43 % | 8.05 % | 42.62 % |

## T5 · Fase 4 — CPU contra GPU

| motor · dispositivo | imagen | CER acentos | ms mediana | etiqueta |
|---|---|---:|---:|---|
| `docling_onnxruntime_cpu_f4_cpu_onnxruntime` | `nativo__patologico_escaneado` | 0.00 % | 1735.3 | SUCIA(pico 55%) |
| `docling_onnxruntime_cpu_f4_cpu_onnxruntime` | `nativo__escaneado_d1` | 0.00 % | 1258.5 | SUCIA(pico 55%) |
| `docling_onnxruntime_cpu_f4_cpu_onnxruntime` | `nativo__escaneado_d2` | 0.00 % | 1056.7 | SUCIA(pico 55%) |
| `docling_onnxruntime_cpu_f4_cpu_onnxruntime` | `nativo__escaneado_d3` | 75.95 % | 1063.2 | SUCIA(pico 55%) |
| `docling_onnxruntime_cpu_f4_cpu_onnxruntime` | `nativo__escaneado_d4` | 36.91 % | 1962.1 | SUCIA(pico 55%) |
| `docling_torch_cpu_f4_cpu_torch` | `nativo__patologico_escaneado` | 0.00 % | 2167.9 | SUCIA(pico 33%) |
| `docling_torch_cpu_f4_cpu_torch` | `nativo__escaneado_d1` | 0.00 % | 1468.7 | SUCIA(pico 33%) |
| `docling_torch_cpu_f4_cpu_torch` | `nativo__escaneado_d2` | 0.00 % | 1135.8 | SUCIA(pico 33%) |
| `docling_torch_cpu_f4_cpu_torch` | `nativo__escaneado_d3` | 75.95 % | 1075.7 | SUCIA(pico 33%) |
| `docling_torch_cpu_f4_cpu_torch` | `nativo__escaneado_d4` | 36.91 % | 2237.9 | SUCIA(pico 33%) |
| `docling_torch_cuda_f4_cuda_torch` | `nativo__patologico_escaneado` | 0.00 % | 736.0 | SUCIA(pico 30%) |
| `docling_torch_cuda_f4_cuda_torch` | `nativo__escaneado_d1` | 0.00 % | 474.7 | SUCIA(pico 30%) |
| `docling_torch_cuda_f4_cuda_torch` | `nativo__escaneado_d2` | 0.00 % | 399.3 | SUCIA(pico 30%) |
| `docling_torch_cuda_f4_cuda_torch` | `nativo__escaneado_d3` | 75.95 % | 370.6 | SUCIA(pico 30%) |
| `docling_torch_cuda_f4_cuda_torch` | `nativo__escaneado_d4` | 36.91 % | 680.9 | SUCIA(pico 30%) |
| `easyocr_cpu_f4_cpu` | `ppp100__escaneado_d3` | 54.43 % | 1908.3 | SUCIA(pico 31%) |
| `easyocr_cpu_f4_cpu` | `ppp200__escaneado_d3` | 56.96 % | 6474.2 | SUCIA(pico 31%) |
| `easyocr_cpu_f4_cpu` | `ppp200__escaneado_d4` | 62.08 % | 7676.1 | SUCIA(pico 31%) |
| `easyocr_cuda_f4_cuda` | `ppp100__escaneado_d3` | 54.43 % | 292.0 | SUCIA(pico 54%) |
| `easyocr_cuda_f4_cuda` | `ppp200__escaneado_d3` | 59.49 % | 537.7 | SUCIA(pico 54%) |
| `easyocr_cuda_f4_cuda` | `ppp200__escaneado_d4` | 61.41 % | 1139.1 | SUCIA(pico 54%) |
| `paddleocr_cpu_f4_cpu` | `ppp100__escaneado_d2` | 0.00 % | 1017.5 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp100__escaneado_d3` | 2.53 % | 879.6 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp150__escaneado_d1` | 0.00 % | 1609.1 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp200__escaneado_d1` | 0.00 % | 2727.5 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp200__escaneado_d2` | 0.00 % | 2953.5 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp200__escaneado_d3` | 75.95 % | 2539.9 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp200__escaneado_d4` | 19.63 % | 5418.1 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp200__patologico_escaneado` | 0.00 % | 3112.9 | SUCIA(pico 36%) |
| `paddleocr_cpu_f4_cpu` | `ppp280__escaneado_d4` | 36.24 % | 5809.0 | SUCIA(pico 36%) |
| `paddleocr_cuda_f4_cuda` | `ppp100__escaneado_d2` | 0.00 % | 98.3 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp100__escaneado_d3` | 2.53 % | 89.9 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp150__escaneado_d1` | 0.00 % | 162.0 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp200__escaneado_d1` | 0.00 % | 255.4 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp200__escaneado_d2` | 0.00 % | 233.8 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp200__escaneado_d3` | 75.95 % | 212.8 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp200__escaneado_d4` | 19.30 % | 393.2 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp200__patologico_escaneado` | 0.00 % | 296.1 | SUCIA(pico 22%) |
| `paddleocr_cuda_f4_cuda` | `ppp280__escaneado_d4` | 36.24 % | 545.3 | SUCIA(pico 22%) |
| `rapidocr_cpu_f4_cpu` | `ppp100__escaneado_d2` | 0.00 % | 262.6 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp100__escaneado_d3` | 77.22 % | 219.9 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp150__escaneado_d1` | 0.00 % | 460.6 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp200__escaneado_d1` | 0.00 % | 750.7 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp200__escaneado_d2` | 1.27 % | 720.6 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp200__escaneado_d3` | 70.89 % | 727.6 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp200__escaneado_d4` | 41.78 % | 1192.0 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp200__patologico_escaneado` | 1.27 % | 995.1 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4_cpu` | `ppp280__escaneado_d4` | 41.95 % | 1338.9 | SUCIA(pico 34%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp100__escaneado_d2` | 0.00 % | 323.9 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp100__escaneado_d3` | 3.80 % | 380.4 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp150__escaneado_d1` | 0.00 % | 531.6 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp200__escaneado_d1` | 0.00 % | 800.9 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp200__escaneado_d2` | 0.00 % | 772.3 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp200__escaneado_d3` | 53.16 % | 723.5 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp200__escaneado_d4` | 18.62 % | 1177.6 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp200__patologico_escaneado` | 0.00 % | 1024.3 | SUCIA(pico 33%) |
| `rapidocr_cpu_f4corr_cpu` | `ppp280__escaneado_d4` | 28.86 % | 1335.4 | SUCIA(pico 33%) |
| `rapidocr_cuda_f4_cuda` | `ppp100__escaneado_d2` | 0.00 % | 95.1 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp100__escaneado_d3` | 77.22 % | 75.6 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp150__escaneado_d1` | 0.00 % | 136.1 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp200__escaneado_d1` | 0.00 % | 203.8 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp200__escaneado_d2` | 1.27 % | 192.3 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp200__escaneado_d3` | 65.82 % | 208.8 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp200__escaneado_d4` | 41.78 % | 454.3 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp200__patologico_escaneado` | 1.27 % | 433.5 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4_cuda` | `ppp280__escaneado_d4` | 41.95 % | 465.1 | SUCIA(pico 35%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp100__escaneado_d2` | 0.00 % | 78.1 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp100__escaneado_d3` | 3.80 % | 82.2 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp150__escaneado_d1` | 0.00 % | 124.6 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp200__escaneado_d1` | 0.00 % | 193.3 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp200__escaneado_d2` | 0.00 % | 177.4 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp200__escaneado_d3` | 53.16 % | 174.7 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp200__escaneado_d4` | 18.62 % | 339.6 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp200__patologico_escaneado` | 0.00 % | 445.8 | SUCIA(pico 31%) |
| `rapidocr_cuda_f4corr_cuda` | `ppp280__escaneado_d4` | 28.86 % | 534.6 | SUCIA(pico 31%) |

## T6 · VRAM y carga en frío (pasada con muestreador)

| motor | base MiB | tras carga MiB | pico MiB | coste propio MiB | carga frío s |
|---|---:|---:|---:|---:|---:|
| `docling_torch_cuda_vram` | 2897 | None | 4381 | 1484 | None |
| `easyocr_cuda_vram` | 2907 | 3145 | 7337 | 4430 | 6.99 |
| `paddleocr_cuda_vram` | 2878 | 3157 | 5586 | 2708 | 5.53 |
| `rapidocr_cuda_vram` | 2906 | 3076 | 5471 | 2565 | 3.91 |
