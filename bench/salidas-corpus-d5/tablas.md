# Tablas completas — corpus d5 (G3)

Evaluador: `bench/salidas-corpus-d4/ocr_eval_d4.py`, copia byte a byte en este
directorio, `rid="d4"`. Toda cifra es **CER con acentos**, en por ciento.
Motor: **Tesseract 5.5.0, CPU**. Rasterizador declarado en cada tabla.

## T1 · Tanda V1 — 15 documentos x 3 `--psm` x 2 idiomas, ppp nativos, rasterizador ImageMagick

| documento | ppp nat | px | psm 3 spa | psm 6 spa | psm 11 spa | psm 3 eng | psm 6 eng | psm 11 eng | min | max |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5` | 72 | 465x636 | 10,07 | 21,14 | 10,23 | 17,79 | 25,17 | 17,45 | **10,07** | 25,17 |
| `escaneado_d5a` | 90 | 582x801 | 1,17 | 5,70 | 1,17 | 7,55 | 12,58 | 7,55 | **1,17** | 12,58 |
| `escaneado_d5b` | 60 | 388x531 | 28,69 | 36,74 | 25,34 | 33,22 | 38,09 | 31,04 | **25,34** | 38,09 |
| `escaneado_d5c` | 80 | 517x708 | 2,52 | 9,73 | 2,01 | 9,73 | 19,13 | 10,23 | **2,01** | 19,13 |
| `patologico_d5a` | 200 | 1294x1752 | 16,28 | 30,87 | 10,74 | 24,50 | 42,95 | 20,47 | **10,74** | 42,95 |
| `patologico_d5b` | 200 | 1294x1752 | 32,05 | 34,73 | 14,60 | 38,93 | 44,63 | 22,15 | **14,60** | 44,63 |
| `patologico_d5` | 200 | 1294x1752 | 56,04 | 36,74 | 31,88 | 59,56 | 43,12 | 38,42 | **31,88** | 59,56 |
| `patologico_d5e` | 200 | 1294x1752 | 49,33 | 42,79 | 53,02 | 54,19 | 46,98 | 56,21 | **42,79** | 56,21 |
| `realista_d5a` | 200 | 1294x1782 | 0,17 | 4,19 | 0,17 | 7,55 | 11,24 | 7,55 | **0,17** | 11,24 |
| `realista_d5b` | 200 | 1294x1771 | 37,92 | 19,30 | 9,40 | 41,95 | 24,16 | 15,60 | **9,40** | 41,95 |
| `realista_d5` | 200 | 1294x1762 | 31,71 | 30,03 | 27,01 | 35,23 | 34,23 | 29,87 | **27,01** | 35,23 |
| `realista_d5e` | 200 | 1294x1752 | 74,83 | 71,31 | 36,07 | 76,85 | 72,48 | 40,10 | **36,07** | 76,85 |
| `d5_limpio` | 72 | 465x644 | 6,21 | 10,74 | 6,38 | 13,93 | 22,48 | 13,59 | **6,21** | 22,48 |
| `escaneado_d4` | 200 | 1294x1716 | 84,56 | 55,70 | 41,78 | 84,40 | 61,07 | 46,14 | **41,78** | 84,56 |
| `escaneado_d4c` | 200 | 1294x1734 | 1,85 | 6,54 | 2,68 | 12,08 | 14,93 | 11,91 | **1,85** | 14,93 |

## T2 · Desglose por tamaño de letra (el GRADIENTE), `psm 11`, `spa`, ppp nativos, ImageMagick

| documento | titulo | subtitulo | cuerpo | letra pequeña | ¿monotono? | config. (de 6) con las 4 cifras distintas |
|---|---:|---:|---:|---:|---|---:|
| `escaneado_d5` | 0,00 | 0,00 | 0,64 | 45,54 | si | 4/6 |
| `escaneado_d5a` | 0,00 | 0,00 | 0,00 | 5,16 | si | 4/6 |
| `escaneado_d5b` | 0,00 | 0,00 | 5,77 | 74,65 | si | 3/6 |
| `escaneado_d5c` | 0,00 | 0,00 | 0,32 | 10,33 | si | 4/6 |
| `patologico_d5a` | 8,00 | 41,86 | 5,45 | 20,19 | no | 6/6 |
| `patologico_d5b` | 24,00 | 9,30 | 9,94 | 27,23 | no | 6/6 |
| `patologico_d5` | 32,00 | 32,56 | 15,38 | 69,01 | no | 6/6 |
| `patologico_d5e` | 4,00 | 58,14 | 32,05 | 74,65 | no | 6/6 |
| `realista_d5a` | 0,00 | 0,00 | 0,00 | 3,29 | si | 4/6 |
| `realista_d5b` | 8,00 | 4,65 | 7,69 | 37,56 | no | 6/6 |
| `realista_d5` | 24,00 | 16,28 | 24,04 | 65,73 | no | 6/6 |
| `realista_d5e` | 32,00 | 18,60 | 36,54 | 70,89 | no | 6/6 |
| `d5_limpio` | 0,00 | 0,00 | 0,00 | 30,99 | si | 4/6 |
| `escaneado_d4` | 12,00 | 9,30 | 35,90 | 72,77 | no | 6/6 |
| `escaneado_d4c` | 12,00 | 9,30 | 1,92 | 9,86 | no | 5/6 |

## T3 · Tanda V3 — barrido de ppp sobre B15 (`spa`, ImageMagick). **La medida del suelo de 100.**


**`--psm 3`**

| documento | ppp nativos | regla vigente | 60 ppp | 72 ppp | 75 ppp | 80 ppp | 90 ppp | 100 ppp | 125 ppp | 150 ppp | 200 ppp | 300 ppp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5b` | 60 | 75 | 28,69 | — | 25,50 | — | 12,75 | 8,72 | 6,88 | 7,89 | 9,90 | 9,56 |
| `escaneado_d5` | 72 | 90 | — | 10,07 | 7,55 | — | 2,35 | 3,02 | 2,35 | 2,18 | 2,68 | 2,52 |
| `escaneado_d5c` | 80 | 100 | — | — | 12,92 | 2,52 | 2,01 | 1,34 | 0,84 | 0,84 | 0,84 | 1,51 |
| `escaneado_d5a` | 90 | 100 | — | — | 25,00 | — | 1,17 | 2,68 | 0,50 | 0,67 | 0,67 | 0,67 |

**`--psm 11`**

| documento | ppp nativos | regla vigente | 60 ppp | 72 ppp | 75 ppp | 80 ppp | 90 ppp | 100 ppp | 125 ppp | 150 ppp | 200 ppp | 300 ppp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5b` | 60 | 75 | 25,34 | — | 17,79 | — | 13,76 | 8,56 | 8,56 | 6,21 | 9,40 | 8,72 |
| `escaneado_d5` | 72 | 90 | — | 10,23 | 7,21 | — | 2,35 | 1,85 | 1,85 | 2,52 | 2,85 | 2,35 |
| `escaneado_d5c` | 80 | 100 | — | — | 12,08 | 2,01 | 2,35 | 1,34 | 0,84 | 1,01 | 1,34 | 1,17 |
| `escaneado_d5a` | 90 | 100 | — | — | 11,58 | — | 1,17 | 1,51 | 0,50 | 0,67 | 0,84 | 0,67 |

## T4 · Ablacion de las cinco patologias de escaner (partiendo de la primera pared, `spa`, ImageMagick)

| variante | que cambia | psm 3 | psm 11 | Δ psm 11 frente a la base |
|---|---|---:|---:|---:|
| *(base)* | — | 92,62 | 86,41 | — |
| `abl_p5b_imp02` | polvo 0,10 -> **0,02** | 42,45 | 35,40 | -51,01 |
| `abl_p5b_ilum` | iluminacion 58/68 -> **85/90** (casi uniforme) | 17,28 | 11,74 | -74,67 |
| `abl_p5b_blur06` | desenfoque 1,0 -> **0,6** | 66,61 | 71,31 | -15,10 |
| `abl_p5b_jq60` | JPEG 40 -> **60** | 100,00 | 77,85 | -8,56 |
| `abl_p5b_niv12` | contraste `24%,80%` -> **`12%,90%`** | 82,89 | 66,28 | -20,13 |
| `abl_p5b_rui10` | ruido gaussiano 0,25 -> **0,10** | 100,00 | 88,93 | +2,52 |
| `abl_p5b_sinray` | **sin** rayas de sensor | 92,62 | 87,75 | +1,34 |

## T5 · Los dos barridos de una sola perilla (`spa`, ImageMagick)

**Iluminacion** (polvo fijo en 0,045). Da un INTERRUPTOR, no un gradiente.

| viñeta/lampara | psm 3 | psm 11 |
|---|---:|---:|
| 78 | 5,20 | 3,69 |
| 74 | 5,03 | 4,36 |
| 70 | 72,82 | 60,07 |
| 66 | 79,36 | 46,48 |
| 62 | 82,21 | 37,25 |
| 56 | 78,36 | 64,43 |
| 50 | 54,87 | 38,93 |

**Polvo** (iluminacion fija en 78/85). Da la escalera que se uso.

| `-attenuate` del impulso | psm 3 | psm 11 | va al corpus como |
|---|---:|---:|---|
| 0,045 | 5,20 | 3,69 | — |
| 0,080 | 4,70 | 5,87 | — |
| 0,120 | 16,28 | 10,74 | `patologico_d5a` |
| 0,180 | 25,00 | 18,12 | — |
| 0,250 | 32,05 | 14,60 | `patologico_d5b` |
| 0,350 | 56,04 | 31,88 | **`patologico_d5`** |

## T6 · El "efecto del rasterizador", desmontado (`spa`)

`A` = PNG de ImageMagick tal cual (unidades `Undefined`). `B` = **el mismo PNG** con `-units PixelsPerInch -density N`, **sin tocar un pixel**. `C` = PNG de Ghostscript.

| documento | psm | A ImageMagick | B ImageMagick + dpi | C Ghostscript | ¿B = C? | ¿pixeles identicos? | A − C |
|---|---:|---:|---:|---:|---|---|---:|
| `escaneado_d4` | 3 | 84,56 | 51,34 | 51,34 | **si** | **si** | +33,22 |
| `escaneado_d4` | 11 | 41,78 | 40,60 | 40,60 | **si** | **si** | +1,18 |
| `patologico_d5` | 3 | 56,04 | 54,53 | 54,53 | **si** | **si** | +1,51 |
| `patologico_d5` | 11 | 31,88 | 32,55 | 32,55 | **si** | **si** | -0,67 |
| `patologico_d5b` | 3 | 32,05 | 31,04 | 31,04 | **si** | **si** | +1,01 |
| `patologico_d5b` | 11 | 14,60 | 12,75 | 12,75 | **si** | **si** | +1,85 |
| `realista_d5` | 3 | 31,71 | 25,17 | 25,17 | **si** | **si** | +6,54 |
| `realista_d5` | 11 | 27,01 | 18,29 | 18,29 | **si** | **si** | +8,72 |
| `realista_d5b` | 3 | 37,92 | 23,66 | 23,66 | **si** | **si** | +14,26 |
| `realista_d5b` | 11 | 9,40 | 10,07 | 10,07 | **si** | **si** | -0,67 |
| `realista_d5e` | 3 | 74,83 | 90,27 | 90,27 | **si** | **si** | -15,44 |
| `realista_d5e` | 11 | 36,07 | 33,72 | 33,72 | **si** | **si** | +2,35 |
| `escaneado_d5` | 3 | 10,07 | 10,07 | 10,07 | **si** | **si** | +0,00 |
| `escaneado_d5` | 11 | 10,23 | 10,23 | 10,23 | **si** | **si** | +0,00 |
| `escaneado_d5b` | 3 | 28,69 | 28,69 | 28,69 | **si** | **si** | +0,00 |
| `escaneado_d5b` | 11 | 25,34 | 25,34 | 25,34 | **si** | **si** | +0,00 |

## T7 · Tanda V2 — los 12 del corpus con Ghostscript, ppp nativos, `spa`

| documento | psm 3 gs | psm 11 gs | psm 3 magick | psm 11 magick |
|---|---:|---:|---:|---:|
| `escaneado_d5` | 10,07 | 10,23 | 10,07 | 10,23 |
| `escaneado_d5a` | 1,17 | 1,17 | 1,17 | 1,17 |
| `escaneado_d5b` | 28,69 | 25,34 | 28,69 | 25,34 |
| `escaneado_d5c` | 2,52 | 2,01 | 2,52 | 2,01 |
| `patologico_d5a` | 15,60 | 11,24 | 16,28 | 10,74 |
| `patologico_d5b` | 31,04 | 12,75 | 32,05 | 14,60 |
| `patologico_d5` | 54,53 | 32,55 | 56,04 | 31,88 |
| `patologico_d5e` | 47,99 | 45,64 | 49,33 | 53,02 |
| `realista_d5a` | 0,17 | 0,17 | 0,17 | 0,17 |
| `realista_d5b` | 23,66 | 10,07 | 37,92 | 9,40 |
| `realista_d5` | 25,17 | 18,29 | 31,71 | 27,01 |
| `realista_d5e` | 90,27 | 33,72 | 74,83 | 36,07 |
| `escaneado_d4` | 51,34 | 40,60 | 84,56 | 41,78 |
