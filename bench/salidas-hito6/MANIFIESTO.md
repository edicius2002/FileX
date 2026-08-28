# MANIFIESTO — `bench/salidas-hito6/` (agente S6, hito 6)

Informe: `bench/hito6-sidecar.md`.

**Qué se borra y qué se queda.** Los **PNG del rasterizado (7,2 MB)** son
binarios regenerables y se borran; la orden exacta y su `sha256` están abajo. Se
quedan los `.json` de resultados, los `.log` y **todas las salidas de OCR y de
transcripción en texto** (`texto/`, 294 KB): son la trazabilidad de cada celda de
CER, y un informe que borra su texto no es auditable (fila N17).

---

## 1. Los rásteres borrados, y la orden que los reproduce

Rasterizador: **Ghostscript 10.07** (`gswin64c.exe`). ImageMagick no tiene
rasterizador de PDF propio: delega en él (trampa 8). **No** se declara `pHYs`:
los motores de este informe son inmunes a él (trampa 29) y la omisión es
deliberada.

```
python bench/salidas-hito6/preparar_h6.py bench/salidas-hito6/img
```

El script deja además `img/indice.json` con la orden completa de cada fichero.

| fichero | px | Mpx | bytes | `sha256` (16) | ¿mismo `sha256` que G5? |
|---|---|---:|---:|---|---|
| `escaneado_d4_r100.png` | 647×858 | 0,555 | 373 589 | `68e8a434f394c461` | **sí** |
| `escaneado_d4_r150.png` | 970×1287 | 1,248 | 760 570 | `e199d9cc5f555253` | **sí** |
| `escaneado_d4_r200.png` | 1294×1716 | 2,221 | 1 179 035 | `99613281cc45f7a6` | **sí** |
| `escaneado_d4_r280.png` | 1812×2402 | 4,352 | 1 449 399 | `6b145e7b0426febd` | **sí** |
| `escaneado_d4_r400.png` | 2588×3432 | 8,882 | 1 592 617 | `3d010eaba780bdf0` | **sí** |
| `escaneado_d1_r150.png` | 970×1300 | 1,261 | 596 280 | `4e86f2ffdad3c4c2` | — (no lo tenía) |
| `escaneado_d2_r100.png` | 647×850 | 0,550 | 322 014 | `215b41e64b342645` | — |
| `patologico_escaneado_r200.png` | 1294×1792 | 2,319 | 1 181 954 | `190e9bad2c710d23` | — |

**Las cinco filas comparables coinciden al `sha256` con las de
`bench/salidas-ocr-produccion/img/indice.json`**: la parte de VRAM de este
informe corre sobre exactamente los mismos píxeles que la de G5 (§1.5).

Los tres últimos van a sus **ppp NATIVOS** (`ocr-ppp-nativos.md` §2): 200 el
patológico, **150** `d1` —no 100— y 100 `d2`.

---

## 2. Cómo se reproduce cada tanda

Todas toman el **lock de GPU** con `filex/gpu.py` (protocolo de
`bench/lib/harness.sh`) y aplican `GPU_GUARD` antes de cada corrida. El
intérprete de los motores es `D:/Work/research/FileX/.venv-ai/Scripts/python.exe`
y va **dentro del plan**, no en el código.

```
# 0 · los rasteres
python bench/salidas-hito6/preparar_h6.py bench/salidas-hito6/img

# 1 · los planes
python bench/salidas-hito6/plan_gen.py

# 2 · las tandas (cada una toma el lock una vez)
python bench/salidas-hito6/run_h6.py bench/salidas-hito6/plan_a.json   # A: el fallo 10/10
python bench/salidas-hito6/run_h6.py bench/salidas-hito6/plan_f.json   # F: el factorial PUBLICADO
python bench/salidas-hito6/run_h6.py bench/salidas-hito6/plan_g.json   # G: large-v3
python bench/salidas-hito6/run_h6.py bench/salidas-hito6/plan_h.json   # H: large-v3 + audio de 308 s

# 3 · las tablas
python bench/salidas-hito6/analisis_h6.py F
python bench/salidas-hito6/analisis_h6.py G

# 4 · el mecanismo del fallo de coresidencia
.venv-ai/Scripts/python.exe bench/salidas-hito6/sonda_cudnn.py inventario
.venv-ai/Scripts/python.exe bench/salidas-hito6/sonda_cudnn.py orden_ocr     # rc=0
.venv-ai/Scripts/python.exe bench/salidas-hito6/sonda_cudnn.py orden_audio   # rc=0xC0000409

# 5 · la verificacion del criterio
python bench/salidas-hito6/verificar_criterio.py     # V1, V3, V4, V5
python bench/salidas-hito6/orden_lote.py 5           # V2, n=5
python bench/salidas-hito6/precision_h6.py cuda      # V6

# 6 · las pruebas del sidecar (sin tarjeta)
python -m pytest pruebas/test_hito6.py -q
```

Con `HF_HUB_OFFLINE=1` en el entorno: los pesos de `distil-large-v3` y
`large-v3` ya están en la caché local de Hugging Face y **no hace falta red**.

**Aviso sobre la tanda E** (`json/E_*.json`): se conserva y **no se publica**.
Se rompió por editar `filex/sidecar.py` con la tanda corriendo, y sus corridas
de `dos_procesos` midieron dos versiones distintas del código (informe §8.1). La
tanda buena es la **F**.

---

## 3. Qué hay en `texto/`

- `*__ocr.txt` — la salida de RapidOCR sobre el folio de 8,882 Mpx en cada
  corrida del factorial (483 caracteres, constante).
- `*__audio.txt` — la transcripción de `habla_jfk.flac` (110 caracteres) o de
  `habla_largo.flac` (3 052).
- `precision_*_cuda.txt` — las tres salidas de la cláusula de precisión, las que
  dan **distancia de edición 0** contra la referencia de 79 caracteres de
  `bench/scripts/ocr_eval.py` con la métrica **`acentos`**.

---

## 4. Entorno de estas tandas

RTX 3060 12 288 MiB · base de escritorio **1 582-1 709 MiB** durante las tandas
(no los 3 292-3 448 documentados: las cifras de coste propio son `delta` sobre la
base del propio proceso, y el presupuesto absoluto se calcula aparte con la base
documentada) · `.venv-ai` con `torch 2.6.0+cu124`, `onnxruntime-gpu 1.22.0`,
`ctranslate2` y `rapidocr`, **sin instalar nada** · métrica de CER **`acentos`**
· dispositivo **`cuda`** · vía de entrada **`ruta`**.
