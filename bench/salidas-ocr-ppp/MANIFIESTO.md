# MANIFIESTO — `bench/salidas-ocr-ppp/`

Qué hay aquí, qué se retiró y cómo se regenera. El repositorio pasó de 986 MB a 25 MB en
un saneado; este directorio no lo deshace.

## Retirado

| ruta | qué era | tamaño | cómo se regenera |
|---|---|---:|---|
| `img/` | 40 PNG: barrido 75–300 ppp × 4 documentos + 8 imágenes incrustadas extraídas | **40 MB** | `bash 10_preparar.sh` (ImageMagick + `11_extraer.py`) |
| `img2/` | 4 PNG del refinado de la rodilla (110/130/140/160 ppp sobre d3) | **1,7 MB** | primer bloque de `40_run_cierre.sh` |

**Total retirado: 42 960 534 bytes (41,0 MiB).** Son derivados puros de
`corpus/pdf/*.pdf`, que sigue en el repositorio y es la fuente. Regenerarlos es
determinista: la orden de ImageMagick está fijada en `10_preparar.sh` y produjo tamaños
en píxeles idénticos a los de `bench/salidas-fase2/img/` (comprobado: 1293×1733,
1294×1700, 1294×1792).

## Conservado — es la evidencia

| ruta | qué es | tamaño |
|---|---|---:|
| `texto/` | 296 `.txt`: la salida literal de cada motor sobre cada entrada | 392 KB |
| `json/` | 12 `.json`: CER, distancia de edición, medianas de tiempo, VRAM, determinismo — 296 celdas, todas deterministas | 168 KB |
| `logs/` | 15 registros: traza de cada tanda, con las cabeceras de motor y el estado de la GPU | 148 KB |
| `tablas.md` | todas las tablas del informe, generadas por `60_tablas.py` | 12 KB |
| `geometria.json` | ppp nativos medidos de los cuatro documentos | 4 KB |
| `modelos_ai.json`, `modelos_paddle.json` | resolución de la discrepancia PP-OCRv5/v6 | 5 KB |
| `*.py`, `*.sh` | los 13 scripts, ejecutables en orden | 80 KB |

## Orden de ejecución

```
00_geometria.py        ppp nativos reales del corpus            (.venv-ai)
10_preparar.sh         barrido de ppp + extracción sin rasterizar
  └ 11_extraer.py      vía B con pypdfium2 (no hay pdfimages en Windows)
30_run_matriz.sh       la matriz: 4 motores x 40 entradas       [lock de GPU]
  ├ 20_ocr_lote.py     motores aislados (rapid/paddle/easy)
  └ 21_docling_lote.py docling + RapidOCR torch, con sonda de píxeles
40_run_cierre.sh       rodilla + docling por imagen extraída    [lock de GPU]
  └ 22_docling_img.py  vía B para docling (InputFormat.IMAGE, escala 1.0)
41_run_tiempos.sh      segunda pasada, sin muestreador de VRAM  [lock de GPU]
42_control_fase2.sh    control sobre las imágenes de la fase 2  [lock de GPU]
50_modelos.py          fase 3: qué checkpoint corre cada motor  (sin GPU)
60_tablas.py           genera tablas.md                          (sin GPU)
70_cierre.sh           verificación de venv, lock y disco
```

`60_tablas.py` necesita `PYTHONIOENCODING=utf-8` en esta consola (cp1252 no codifica `≠`).

## Nada instalado

Regla 3 del encargo cumplida: no se instaló ni actualizó ningún paquete en
`.venv-ai`, `.venv-paddle` ni ningún otro entorno. `pypdfium2` ya estaba en los dos que
hacían falta. Verificación posterior en `70_cierre.sh`: `.venv-ai` conserva
`torch 2.6.0+cu124` con `torch.cuda.is_available() == True`.
