# MANIFIESTO — `bench/salidas-ppp-norm/` (agente P1)

Informe: **`bench/ppp-y-normalizacion.md`**. Fecha: 2026-08-21, 11:10–13:40.

**Qué se versiona:** los `.py`, los `.sh`, los `.json` de resultados, los `.txt` de
salida de OCR, los `.log` y `tablas.md`. **Qué NO:** las imágenes rasterizadas, los pesos
descargados y los PDF derivados — **675 MB regenerables, borrados al terminar**, con la
orden exacta de cada uno abajo.

---

## 1. Lo que queda en disco

| directorio | contenido | tamaño aprox. |
|---|---|---|
| `json/` | 22 ficheros de resultados (`*__cer.json`, `survey_cuda.json`, `probe_norm.json`, `sonda_detector_*.json`, `geometria_pn.json`) | 548 KB |
| `texto/` | salidas de OCR crudas, una por (configuración, imagen) | 479 KB |
| `logs/` | los registros completos de las seis tandas | 508 KB |
| raíz | 10 scripts + `tablas.md` + este fichero | 90 KB |

## 2. Lo que se borró, y cómo se regenera

| borrado | tamaño | orden exacta que lo reproduce |
|---|---:|---|
| `modelos/` (pesos ONNX de RapidOCR: v4/v5/v6 × mobile/server/small/medium/tiny) | **564 MB** | se descargan solos: cualquier tanda con `RO_ROOT=D:/Work/research/FileX/bench/salidas-ppp-norm/modelos`. **Van ahí a propósito, para no escribir dentro de `.venv-ai`** |
| `img/` (17 rasterizaciones de `escaneado_d4`, 100–400 ppp) | 21 MB | `python preparar_pn.py 100,125,150,175,200,225,250,280,320,360,400 escaneado_d4` + `python preparar_pn.py 255,260,265,270,275,300 escaneado_d4` |
| `img_docs/` (`d3`, `d4c`, `d4f`) | 19 MB | `python preparar_pn.py 100,150,200,240,280,336,400 escaneado_d4f` · `… 150,200,250,280,320 escaneado_d4c` · `… 75,100,125,140,160,200,280 escaneado_d3`, con `IMGDIR=…/img_docs` |
| `img_docs2/` (`patologico` + refinamiento de `d4`) | 39 MB | `IMGDIR=…/img_docs2 python preparar_pn.py 100,150,200,250,280,320,400 patologico_escaneado` + copiar `img/ppp{0250,0255,0260,0265,0270,0275,0280,0300}__escaneado_d4.png` |
| `img_pg/` (12 rasterizaciones de los tres PDF derivados) | 14 MB | ver §3 |
| `img_b10/` (15 documentos a ppp nativos + patrón oro) | 13 MB | ver §4 |
| `img_b10r/` (6 documentos, subconjunto del cribado) | 6,8 MB | copia de 6 ficheros de `img_b10/` |
| `tmp/` (JPEG extraído + 3 PDF derivados) | 412 KB | ver §3 |

## 3. Los tres PDF derivados de §2.4 del informe — cómo se construyen

**Mismo mapa de bits, tres tamaños de página.** Es el experimento que prueba que los ppp
no son la unidad.

```bash
# 1) extraer el JPEG incrustado de escaneado_d4.pdf (100 545 B, 1294x1716)
python - <<'EOF'
import pypdfium2 as pdfium
d = pdfium.PdfDocument(r"D:\Work\research\FileX\corpus\pdf\escaneado_d4.pdf")
p = d[0]
for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
    img = pdfium.PdfImage(obj.raw, obj.page, obj.pdf, obj.level)
    open("tmp/d4_extraido.jpg", "wb").write(img.get_data())
    break
d.close()
EOF

# 2) empaquetarlo a tres densidades — MISMA orden que gen_corpus_d4.py
for D in 100 200 400; do
  magick tmp/d4_extraido.jpg -units PixelsPerInch -density $D tmp/d4_pg$D.pdf
done

# 3) rasterizar a las anchuras 647 / 1294 / 1812 / 2588 px en cada geometria
IMGDIR=.../img_pg python preparar_pn.py  50,100,140,200 d4_pg100
IMGDIR=.../img_pg python preparar_pn.py 100,200,280,400 d4_pg200
IMGDIR=.../img_pg python preparar_pn.py 200,400,560,800 d4_pg400
```

| fichero | bytes | sha256 |
|---|---:|---|
| `tmp/d4_extraido.jpg` | 100 545 | `60e57028a4b90c652690785c9c695da45156c4cec5d83f576e6a7838481e569d` |
| `tmp/d4_pg100.pdf` | 103 372 | `64761b6ba9b822d1a43e78cfefdfd2ca2a19229987d02d21357fe8b5fbec808e` |
| `tmp/d4_pg200.pdf` | 103 369 | `ff074c2b6ffe7d5b9f1ca689b9cbf5bfc63d39d883e79821157888aff6263a58` |
| `tmp/d4_pg400.pdf` | 103 369 | `4f19a0c7484d4ce51e156094a073546940a1f3609ca031817b9ce391c41a2d51` |

> **Los `sha256` de los PDF NO son reproducibles**: ImageMagick estampa `/CreationDate` y
> **no honra `SOURCE_DATE_EPOCH`** (ya documentado en `corpus/pdf/MANIFIESTO-d4.md` §3;
> aquí se reconfirma). El **JPEG interior sí lo es**, y es lo que decide el resultado.

## 4. El corpus de B10 y las rasterizaciones del patrón oro

```bash
IMGDIR=.../img_b10 python preparar_pn.py nativo \
  patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3 \
  escaneado_d4 escaneado_d4a escaneado_d4b escaneado_d4c escaneado_d4e escaneado_d4f
IMGDIR=.../img_b10 python preparar_pn.py 150 tipico_texto

# El patron oro se LEE, no se toca. Solo se le aplica la misma conversion a gris
# que al resto del arnes, para que la unica variable sea el origen del rasterizado.
O=bench/salidas-referencia/pdf
magick $O/patologico_escaneado_pdf-to-p1.png -colorspace Gray -alpha remove \
       -background white -flatten img_b10/oro__patologico_escaneado_p1.png
magick $O/tipico_texto_pdf-to-p1.png  … img_b10/oro__tipico_texto_p1.png
magick $O/tipico_texto_pdf-to-p1.jpg  … img_b10/oro__tipico_texto_p1jpg.png
magick $O/trivial_pdf-to-p1.png       … img_b10/oro__trivial_p1.png
```

## 5. Orden de ejecución de las seis tandas

```bash
bash run_a_barrido.sh        # barrido de ppp sobre d4, 4 configuraciones, n=9   [GPU]
bash run_b_docs.sh           # d3/d4c/d4f (tanda B) + los 3 PDF derivados (C)    [GPU]
bash run_d_b10.sh            # D1 cribado n=1 · D2 validacion n=9 · D3 docling   [GPU]
bash run_f_resto.sh          # patologico + refinamiento 250-300 de PaddleOCR    [GPU]
bash run_e_easy_docling.sh   # docling barrido + EasyOCR con muestreador de VRAM [GPU]

# sondas de instrumentacion, CPU, sin lock (no producen ninguna cifra de CER):
python probe_norm.py
python sonda_detector.py rapidocr  .../img "ppp*__escaneado_d4.png"   # .venv-ai
python sonda_detector.py paddleocr .../img "ppp*__escaneado_d4.png"   # .venv-paddle

python tablas_pn.py > /dev/null   # regenera tablas.md desde json/
```

## 6. sha256 de lo que se versiona

| fichero | sha256 |
|---|---|
| `d4_texto.py` | `fa4b8d5d74980b29f0e640911c42ea07e59ca3910f364bd599407cb79c3cf011` |
| `ocr_eval_d4.py` | `350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82` |
| `ocr_eval_pn.py` | `4c86a550a9523c9d55f9edad6ea03a2b675d5385130193c3f80b835e9243c894` |
| `preparar_pn.py` | `2e9194cc96035d0506155e49d3b6e8fb4688980ac174735fc727f44a1b668b08` |
| `ocr_lote_pn.py` | `3752f0a5b5bf511ab41274ea198a96c4233055d14af1833c93e2bb7db993381e` |
| `docling_lote_pn.py` | `0887b2b9a462f27d2f156911654b6e05858a0b79c616b15873e0bf31643c4f27` |
| `survey_norm.py` | `5307b4d0034c778c5b8a7a5b4a61b04e54549836c8bd969a89b3fed3c81005c0` |
| `probe_norm.py` | `a8b2f43e7b67676509552c31ad393bed51550488b36c2c0e113411dcd989f669` |
| `sonda_detector.py` | `23bf2cc2fa09ac70d9409c680547a73a3b5afa520f60935a6dc4b2279d4e75c9` |
| `tablas_pn.py` | `6e9497961b004cbd91adf5195178181df8c4298c89b668e97bca967a341dfeec` |
| `run_a_barrido.sh` | `01404d92b9762deaf030be002d82e6edae8121eb4a86d8b5a9239f4ee261105c` |
| `run_b_docs.sh` | `28902164d239f12c7f02cea7bfc1cb463c25be2cb7094e2f3085ef5c23103b39` |
| `run_d_b10.sh` | `51136bcf35a1ed9bc050bf7c5708aabc28d42c8fd49457c6df728dd843d241c1` |
| `run_e_easy_docling.sh` | `5461459e3308bbe625eac3b42102eb99ef13e90a842774d3b1754955c3a3efab` |
| `run_f_resto.sh` | `2ad4322ab41d8bae2098424af8ab89fac0c3f41c1d085380e00efe3a72af7888` |

**`ocr_eval_d4.py` y `d4_texto.py` son copias BYTE A BYTE de
`bench/salidas-corpus-d4/`** — los `sha256` coinciden con los originales, comprobado.
Son el evaluador que produjo las cifras de d4 y por tanto el único comparable con ellas.

## 7. Lo que NO se tocó

- `bench/scripts/ocr_eval.py`, `ocr_motor.py`, `gen_corpus_ocr.sh`, `verificador.py`
  (este último lo lleva P3): **intactos**, fecha del 19 de agosto.
- `bench/salidas-referencia/referencia.json` y `bench/salidas-referencia/pdf/`: **solo
  lectura**, fecha del 19 de agosto.
- `bench/salidas-corpus-d4/`, `corpus/`, `analysis/`, los documentos maestros y los
  informes de los demás agentes: **sin tocar**.
- `.venv-ai/Lib/site-packages/rapidocr/models/`: **sus 10 ficheros conservan la fecha del
  19 de agosto**. Los pesos nuevos fueron a `bench/salidas-ppp-norm/modelos/` vía
  `Global.model_root_dir`, y los de PaddleX a `~/.paddlex/official_models/` — los dos
  **fuera de los venv**.
- **Verificado al terminar:** `.venv-ai` → `torch 2.6.0+cu124`, `cuda True`,
  `NVIDIA GeForce RTX 3060`, `onnxruntime 1.22.0`, `docling 2.120.3`.
  `.venv-paddle` → `paddle 3.2.0` compilado con CUDA, 1 dispositivo, `paddleocr 3.7.0`.
