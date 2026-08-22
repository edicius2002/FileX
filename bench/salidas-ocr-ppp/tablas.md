<!-- generado por 60_tablas.py; no editar a mano -->

### T1 — Tabla canónica: CER % por vía de entrada

| Motor | Documento | ppp nativos | imagen extraída | 200 ppp (control) |
|---|---|---:|---:|---:|
| RapidOCR | patológico (d0) (200 ppp) | **1.3%** | 1.3% | 1.3% |
| RapidOCR | d1 (150 ppp) | **0.0%** | 0.0% | 0.0% |
| RapidOCR | d2 (100 ppp) | **0.0%** | 0.0% | 1.3% |
| RapidOCR | d3 (100 ppp) | **77.2%** | 77.2% | 65.8% |
| PaddleOCR | patológico (d0) (200 ppp) | **0.0%** | 0.0% | 0.0% |
| PaddleOCR | d1 (150 ppp) | **0.0%** | 0.0% | 0.0% |
| PaddleOCR | d2 (100 ppp) | **0.0%** | 0.0% | 0.0% |
| PaddleOCR | d3 (100 ppp) | **2.5%** | 2.5% | 75.9% |
| EasyOCR | patológico (d0) (200 ppp) | **0.0%** | 0.0% | 0.0% |
| EasyOCR | d1 (150 ppp) | **0.0%** | 0.0% | 0.0% |
| EasyOCR | d2 (100 ppp) | **43.0%** | 43.0% | 43.0% |
| EasyOCR | d3 (100 ppp) | **54.4%** | 54.4% | 59.5% |
| Docling+RapidOCR torch | patológico (d0) (200 ppp) | **0.0%** | 0.0% | 0.0% |
| Docling+RapidOCR torch | d1 (150 ppp) | **0.0%** | 0.0% | 0.0% |
| Docling+RapidOCR torch | d2 (100 ppp) | **0.0%** | 0.0% | 0.0% |
| Docling+RapidOCR torch | d3 (100 ppp) | **75.9%** | 75.9% | 58.2% |

### T1b — distancia de edición (mismos datos, en caracteres sobre 79)

| Motor | Documento | ppp nativos | imagen extraída | 200 ppp |
|---|---|---:|---:|---:|
| RapidOCR | patológico (d0) | 1 | 1 | 1 |
| RapidOCR | d1 | 0 | 0 | 0 |
| RapidOCR | d2 | 0 | 0 | 1 |
| RapidOCR | d3 | 61 | 61 | 52 |
| PaddleOCR | patológico (d0) | 0 | 0 | 0 |
| PaddleOCR | d1 | 0 | 0 | 0 |
| PaddleOCR | d2 | 0 | 0 | 0 |
| PaddleOCR | d3 | 2 | 2 | 60 |
| EasyOCR | patológico (d0) | 0 | 0 | 0 |
| EasyOCR | d1 | 0 | 0 | 0 |
| EasyOCR | d2 | 34 | 34 | 34 |
| EasyOCR | d3 | 43 | 43 | 47 |
| Docling+RapidOCR torch | patológico (d0) | 0 | 0 | 0 |
| Docling+RapidOCR torch | d1 | 0 | 0 | 0 |
| Docling+RapidOCR torch | d2 | 0 | 0 | 0 |
| Docling+RapidOCR torch | d3 | 60 | 60 | 46 |

### T2 — Cuánto de la cifra vieja era artefacto

| Motor | Doc | publicado (200 ppp) | reproducido aquí | a ppp nativos | artefacto (pp) |
|---|---|---:|---:|---:|---:|
| RapidOCR | patológico (d0) | 0.0% | 1.3% ≠ | 1.3% | +0.0 |
| RapidOCR | d1 | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| RapidOCR | d2 | 1.3% | 1.3% ✔ | 0.0% | +1.3 |
| RapidOCR | d3 | 65.8% | 65.8% ✔ | 77.2% | -11.4 |
| PaddleOCR | patológico (d0) | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| PaddleOCR | d1 | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| PaddleOCR | d2 | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| PaddleOCR | d3 | 75.9% | 75.9% ✔ | 2.5% | +73.4 |
| EasyOCR | patológico (d0) | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| EasyOCR | d1 | 0.0% | 0.0% ✔ | 0.0% | +0.0 |
| EasyOCR | d2 | 43.0% | 43.0% ✔ | 43.0% | +0.0 |
| EasyOCR | d3 | 59.5% | 59.5% ✔ | 54.4% | +5.1 |

### T3 — Curva de ppp: CER % (celda de ppp nativos en **negrita**)


**patológico (d0)** — nativo 200 ppp

| ppp | RapidOCR | PaddleOCR | EasyOCR | Docling+RapidOCR torch |
|---:|---:|---:|---:|---:|
| 75 | 0.0% | 0.0% | 0.0% | 0.0% |
| 100 | 1.3% | 0.0% | 0.0% | 0.0% |
| 125 | 1.3% | 0.0% | 0.0% | 0.0% |
| 150 | 1.3% | 0.0% | 0.0% | 0.0% |
| 175 | 1.3% | 0.0% | 0.0% | 0.0% |
| **200** | **1.3%** | **0.0%** | **0.0%** | **0.0%** |
| 250 | 0.0% | 0.0% | 0.0% | 0.0% |
| 300 | 1.3% | 0.0% | 0.0% | 0.0% |
| extraída | 1.3% | 0.0% | 0.0% | 0.0% |
| docling por defecto (216 ppp) | — | — | — | 0.0% |

**d1** — nativo 150 ppp

| ppp | RapidOCR | PaddleOCR | EasyOCR | Docling+RapidOCR torch |
|---:|---:|---:|---:|---:|
| 75 | 1.3% | 0.0% | 12.7% | 0.0% |
| 100 | 0.0% | 0.0% | 15.2% | 0.0% |
| 125 | 0.0% | 0.0% | 0.0% | 0.0% |
| **150** | **0.0%** | **0.0%** | **0.0%** | **0.0%** |
| 175 | 0.0% | 0.0% | 0.0% | 0.0% |
| 200 | 0.0% | 0.0% | 0.0% | 0.0% |
| 250 | 0.0% | 0.0% | 0.0% | 0.0% |
| 300 | 0.0% | 0.0% | 0.0% | 0.0% |
| extraída | 0.0% | 0.0% | 0.0% | 0.0% |
| docling por defecto (216 ppp) | — | — | — | 0.0% |

**d2** — nativo 100 ppp

| ppp | RapidOCR | PaddleOCR | EasyOCR | Docling+RapidOCR torch |
|---:|---:|---:|---:|---:|
| 75 | 44.3% | 0.0% | 43.0% | 0.0% |
| **100** | **0.0%** | **0.0%** | **43.0%** | **0.0%** |
| 125 | 0.0% | 0.0% | 40.5% | 0.0% |
| 150 | 0.0% | 0.0% | 39.2% | 0.0% |
| 175 | 1.3% | 0.0% | 44.3% | 0.0% |
| 200 | 1.3% | 0.0% | 43.0% | 0.0% |
| 250 | 0.0% | 0.0% | 34.2% | 0.0% |
| 300 | 0.0% | 0.0% | 40.5% | 0.0% |
| extraída | 0.0% | 0.0% | 43.0% | 0.0% |
| docling por defecto (216 ppp) | — | — | — | 0.0% |

**d3** — nativo 100 ppp

| ppp | RapidOCR | PaddleOCR | EasyOCR | Docling+RapidOCR torch |
|---:|---:|---:|---:|---:|
| 75 | 75.9% | 11.4% | 58.2% | 75.9% |
| **100** | **77.2%** | **2.5%** | **54.4%** | **75.9%** |
| 125 | 75.9% | 5.1% | 50.6% | 75.9% |
| 150 | 75.9% | 31.6% | 54.4% | 65.8% |
| 175 | 75.9% | 75.9% | 54.4% | 39.2% |
| 200 | 65.8% | 75.9% | 59.5% | 58.2% |
| 250 | 70.9% | 75.9% | 51.9% | 51.9% |
| 300 | 77.2% | 75.9% | 53.2% | 48.1% |
| extraída | 77.2% | 2.5% | 54.4% | 75.9% |
| docling por defecto (216 ppp) | — | — | — | 58.2% |

### T4 — Coste: mediana de tiempo (ms, n=9) por vía

| Motor | Doc | ppp nativos | imagen extraída | 200 ppp | 300 ppp |
|---|---|---:|---:|---:|---:|
| RapidOCR | patológico (d0) | 559.3 | 323.0 | 559.3 | 1546.2 |
| RapidOCR | d1 | 243.0 | 169.7 | 259.2 | 402.4 |
| RapidOCR | d2 | 139.3 | 125.1 | 281.0 | 305.8 |
| RapidOCR | d3 | 93.2 | 125.4 | 274.6 | 312.8 |
| PaddleOCR | patológico (d0) | 439.3 | 326.4 | 439.3 | 729.8 |
| PaddleOCR | d1 | 205.0 | 186.8 | 437.0 | 688.8 |
| PaddleOCR | d2 | 135.5 | 131.3 | 312.4 | 610.9 |
| PaddleOCR | d3 | 107.1 | 107.1 | 323.9 | 604.2 |
| EasyOCR | patológico (d0) | 1117.3 | 664.8 | 1117.3 | 2531.7 |
| EasyOCR | d1 | 352.2 | 381.8 | 600.3 | 2379.0 |
| EasyOCR | d2 | 222.3 | 278.9 | 684.4 | 3231.8 |
| EasyOCR | d3 | 590.9 | 700.1 | 933.3 | 3289.9 |
| Docling+RapidOCR torch | patológico (d0) | 1175.7 | 637.8 | 1175.7 | 1174.8 |
| Docling+RapidOCR torch | d1 | 540.3 | 361.7 | 629.0 | 935.5 |
| Docling+RapidOCR torch | d2 | 425.8 | 1221.7 | 590.4 | 955.2 |
| Docling+RapidOCR torch | d3 | 417.4 | 835.8 | 609.0 | 777.4 |

### T4b — VRAM: pico total de la tarjeta y coste propio, sobre TODO el barrido

| Motor | carga en frío | VRAM base | pico | coste propio | pico util. |
|---|---:|---:|---:|---:|---:|
| RapidOCR | 4.46 s | 2067 MiB | **3424 MiB** | +1357 MiB | 72 % |
| PaddleOCR | 17.31 s | 2071 MiB | **7442 MiB** | +5371 MiB | 100 % |
| EasyOCR | 13.77 s | 2066 MiB | **11877 MiB** | +9811 MiB | 100 % |
| Docling+RapidOCR torch | — s | 835 MiB | **2820 MiB** | +1985 MiB | 100 % |

### T4c — Tiempos sin el muestreador de VRAM (los buenos), ms mediana n=9

| Motor | Doc | ppp nativos | imagen extraída | 200 ppp | ahorro nativo vs 200 |
|---|---|---:|---:|---:|---:|
| RapidOCR | patológico (d0) | 465.3 | 221.4 | 465.3 | 1.00x |
| RapidOCR | d1 | 149.3 | 132.5 | 221.3 | 1.48x |
| RapidOCR | d2 | 82.1 | 80.5 | 214.9 | 2.62x |
| RapidOCR | d3 | 69.1 | 68.6 | 216.5 | 3.13x |
| PaddleOCR | patológico (d0) | 270.6 | 227.9 | 270.6 | 1.00x |
| PaddleOCR | d1 | 151.3 | 147.0 | 226.2 | 1.50x |
| PaddleOCR | d2 | 90.7 | 87.3 | 216.7 | 2.39x |
| PaddleOCR | d3 | 82.6 | 82.9 | 197.2 | 2.39x |
| EasyOCR | patológico (d0) | 537.4 | 450.6 | 537.4 | 1.00x |
| EasyOCR | d1 | 276.6 | 281.7 | 426.2 | 1.54x |
| EasyOCR | d2 | 183.8 | 180.1 | 459.7 | 2.50x |
| EasyOCR | d3 | 309.2 | 309.4 | 530.2 | 1.71x |

### T5 — Sonda: píxeles que llegan de verdad al motor dentro de docling

| configuración | escala | ppp nominal | px al motor |
|---|---:|---:|---|
| d3 @ 75 ppp | 1.0417 | 75.0 | [485, 638] |
| d3 @ 100 ppp | 1.3889 | 100.0 | [647, 850] |
| d3 @ 125 ppp | 1.7361 | 125.0 | [809, 1062] |
| d3 @ 150 ppp | 2.0833 | 150.0 | [970, 1275] |
| d3 @ 175 ppp | 2.4306 | 175.0 | [1132, 1487] |
| d3 @ 200 ppp | 2.7778 | 200.0 | [1294, 1700] |
| d3 @ 250 ppp | 3.4722 | 250.0 | [1617, 2125] |
| d3 @ 300 ppp | 4.1667 | 300.0 | [1941, 2550] |
| d3 @ **por defecto** | 3.0 | 216.0 | [1398, 1836] |
| d3 imagen extraída | 1.0 | — | [647, 850] (png [647, 850]) |

### T6 — Qué texto sale de verdad en d3

Referencia: `documento escaneado texto que solo existe como pixeles debe recuperarse con ocr` (79 caracteres normalizados)

| Motor | vía | CER | texto recuperado (normalizado) |
|---|---|---:|---|
| RapidOCR | 100 ppp (nativo) | 77.2% | `documentoescaneado` |
| RapidOCR | 200 ppp | 65.8% | `documentoescaneado oue ooer` |
| RapidOCR | extraída | 77.2% | `documentoescaneado` |
| PaddleOCR | 100 ppp (nativo) | 2.5% | `documento escaneado texto que sola existe como pikeles debe recuperarse con ocr` |
| PaddleOCR | 200 ppp | 75.9% | `documento escaneado` |
| PaddleOCR | extraída | 2.5% | `documento escaneado texto que sola existe como pikeles debe recuperarse con ocr` |
| EasyOCR | 100 ppp (nativo) | 54.4% | `documento escaneado 4e s0ic 4e cat ar cxsr 1rxf 4ues croeaecon8e` |
| EasyOCR | 200 ppp | 59.5% | `documento escaneado nue 5u rueats shontote qortcnan iurf 2566 o2oe` |
| EasyOCR | extraída | 54.4% | `documento escaneado 4e s0ic 4e cat ar cxsr 1rxf 4ues croeaecon8e` |
| Docling+RapidOCR torch | 100 ppp (nativo) | 75.9% | `documento escaneado` |
| Docling+RapidOCR torch | 200 ppp | 58.2% | `documento escaneado texto que sulo` |
| Docling+RapidOCR torch | extraída | 75.9% | `documento escaneado` |
