# MANIFIESTO — `bench/salidas-corpus-d4/`

**Agente G1**, 21 de agosto de 2026, 07:20–09:15. Informe:
**`bench/corpus-d4.md`**. Tablas completas: **`tablas.md`** (generado por
`tablas_d4.py`).

---

## 1. Qué se conserva y qué se borró

| categoría | tamaño | estado |
|---|---:|---|
| scripts (`.py`, `.sh`) | 88 KB | **conservado** — son la trazabilidad |
| `json/` (75 ficheros de resultados) | 737 KB | **conservado** |
| `texto/` (320 salidas de OCR) | 440 KB | **conservado** |
| `logs/` (86 registros) | 561 KB | **conservado** |
| `modelos/` (14 `.onnx` descargados) | **217 MB** | **BORRADO** — regenerable, ver §3 |
| `img/`, `img_f3/`, `img_f4/` (PNG rasterizados) | **18,7 MB** | **BORRADO** — regenerable, ver §3 |
| `tmp/` (maestro, JPEG y PDF intermedios) | **3,4 MB** | **BORRADO** — regenerable, ver §3 |

**240 MB → 1,9 MB.** Nada de lo borrado es un resultado: son entradas y pesos.

Los PDF nuevos **sí** se versionan porque son corpus:
`corpus/pdf/escaneado_d4*.pdf` (711 KB en total, Git LFS) con su
`corpus/pdf/MANIFIESTO-d4.md`.

---

## 2. Orden de ejecución

```
# 1. generar el corpus (deja los .pdf en corpus/pdf y los intermedios en tmp/)
python gen_corpus_d4.py

# 2. rasterizar a ppp nativos (regla R1)
python preparar_img.py nativo d4_limpio escaneado_d4a escaneado_d4b \
        escaneado_d4c escaneado_d4 escaneado_d4e escaneado_d4f
IMGDIR=.../img_f3 python preparar_img.py nativo escaneado_d3 escaneado_d4 escaneado_d4c
IMGDIR=.../img_f4 python preparar_img.py nativo patologico_escaneado escaneado_d1 \
        escaneado_d2 escaneado_d3 escaneado_d4
IMGDIR=.../img_f4 python preparar_img.py 200 escaneado_d1 escaneado_d2 escaneado_d3
IMGDIR=.../img_f4 python preparar_img.py 280 escaneado_d4

# 3. las nueve tandas, cada una con su lock de GPU
bash run_cribado.sh     # elegir candidata          (n=1)
bash run_fase2.sh       # validar la elegida        (n=9, dos pasadas)
bash run_fase3.sh       # tamaño / idioma rec / idioma det
bash run_fase3b.sh      # umbrales y filtros de la tuberia
bash run_fase3c.sh      # barrido de Det.limit_side_len
bash run_fase3d.sh      # A/B causal del reescalado, en los dos sentidos
bash run_fase3e.sh      # A/B causal de la NORMALIZACION  <- la respuesta
bash run_fase4.sh       # CPU contra GPU
python sonda_cajas.py rapidocr ; python sonda_cajas.py paddleocr   # recuento de cajas

# 4. tablas
python tablas_d4.py
```

Intérpretes: `.venv-ai/Scripts/python.exe` para rapidocr / easyocr / docling,
`.venv-paddle/Scripts/python.exe` para paddleocr. **No se instaló nada en ninguno
de los dos.**

---

## 3. Cómo regenerar lo borrado

- **`tmp/`, los PDF y las imágenes:** `python gen_corpus_d4.py` + los
  `preparar_img.py` de §2. El generador lleva `magick -seed 20260821`, así que los
  **JPEG salen bit a bit iguales**; los PDF no, por el `/CreationDate` de ImageMagick
  (detalle y hashes en `corpus/pdf/MANIFIESTO-d4.md` §3).
  - `tmp/d4_master.png`, 3882×5376, 485 380 bytes,
    sha256 `32daa9b3fb956f309146660d1710f7e1d90752ac424aee021ab2046934732a58`.
- **`modelos/` (217 MB):** los descarga solo RapidOCR la primera vez que se le pide una
  configuración que no tiene en disco, si se le pasa
  `Global.model_root_dir = D:/Work/research/FileX/bench/salidas-corpus-d4/modelos`
  (variable `RO_ROOT` en los `run_fase3*.sh`). **Ese parámetro es obligatorio**: sin él
  RapidOCR escribe dentro de `.venv-ai\Lib\site-packages\rapidocr\models\`, y los venv
  no se tocan. Los 14 ficheros que llegó a descargar:

  ```
  PP-OCRv6_det_{tiny,small,medium}.onnx      PP-OCRv6_rec_{tiny,small,medium}.onnx
  ch_PP-OCRv4_det_mobile.onnx                ch_PP-OCRv4_rec_mobile.onnx
  ch_PP-OCRv5_det_mobile.onnx                ch_PP-OCRv5_rec_mobile.onnx
  en_PP-OCRv3_det_mobile.onnx                multi_PP-OCRv3_det_mobile.onnx
  latin_PP-OCRv5_rec_mobile.onnx             ch_ppocr_mobile_v2.0_cls_mobile.onnx
  ```

  Origen: `https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/...`,
  según `rapidocr/default_models.yaml`.
- **Los pesos de PaddleOCR** (`PP-OCRv6_{tiny,small,medium}_{det,rec}`,
  `PP-OCRv5_server_det`, `latin_/en_PP-OCRv5_mobile_rec`, …) están en
  `C:\Users\krato\.paddlex\official_models\`, **fuera del repositorio y fuera de los
  venv**. No se han borrado: PaddleX los cachea ahí y son suyos.

---

## 4. Qué hay en `json/`

| patrón | qué contiene |
|---|---|
| `*_criba__cer.json` | cribado de las 12 candidatas, n=1 (copia también en `json/criba/`) |
| `*_vram__cer.json` | fase 2, pasada **con** muestreador: pico de VRAM válido, tiempos inflados |
| `*_t__cer.json` | fase 2, pasada **sin** muestreador: tiempos válidos, sin pico de VRAM |
| `*_f3*__cer.json` | fases 3, 3b, 3c, 3d y 3e — 47 configuraciones sobre d3 / d4c / d4 |
| `*_f4*__cer.json` | fase 4 — CPU contra GPU, 11 tandas |
| `cajas_{rapidocr,paddleocr}.json` | recuento de cajas detectadas (informe §7.6) |
| `geometria_d4.json` | ppp nativos calculados desde la geometría de cada PDF |
| `candidatas.json` | parámetros, tamaño y `sha256` de cada candidata generada |

Cada `*__cer.json` lleva `cabecera` (motor, dispositivo, modelos cargados de verdad,
VRAM base, quietud de GPU, etiqueta `limpia`/`SUCIA`, carga en frío), `fin` (pico de
VRAM y coste propio) y `res` (por imagen: **las dos** métricas de CER, distancias,
desglose por bloque de tamaño de letra, acentos recuperados, mediana/mín/máx de n=9 y
si la salida fue determinista).

---

## 5. Avisos

1. **La sonda de carga de CPU falló** en las 11 tandas de la fase 4 (`cpu_pico_pct: -1`)
   por `FileNotFoundError [WinError 2]` al invocar `powershell` sin ruta absoluta desde
   Git Bash. Corregida en `ocr_lote_d4.py`, **pero las medidas no se repitieron**: las
   medianas de CPU del informe §9 no llevan línea base de ocupación y hay que leerlas
   como **cota superior**. Detalle en `bench/corpus-d4.md` §12.
2. **`rapidocr` 3.9.2 no expone `__version__`** y su `model_info` es un diccionario
   anidado: la columna `modelos.text_det/cls/rec` de los `.json` **del cribado** contiene
   basura truncada. Corregido a partir de la fase 2 (extracción por expresión regular).
   No afecta a ninguna cifra de CER ni de tiempo.
3. **Todas las tandas salieron `SUCIA`** (picos de utilización de GPU del 22 al 61 %).
   Es estructural: la sesión de escritorio remoto estuvo activa a propósito.
