# MANIFIESTO — `bench/salidas-verificador-gs/`

Salidas del agente **V1 · Verificador y OCR de Ghostscript**
(informe: `bench/verificador-ghostscript.md`).

**Las binarias NO se versionan.** Aquí están su `sha256`, su tamaño y la orden
exacta que las reproduce. Todo se regenera desde este directorio, en este orden:

```
python bench/salidas-verificador-gs/gen_fixtures.py      # TIFF, GIF y PNG Adam7 con magick
python bench/salidas-verificador-gs/gen_predictor.py     # TIFF con Predictor=2, escrito a mano
python bench/salidas-verificador-gs/gen_adam7_4b.py      # PNG de paleta de 2 bits entrelazado
python bench/salidas-verificador-gs/prueba_alfa.py       # contraste contra magick (0 discrepancias)
python bench/salidas-verificador-gs/medir_gs.py cobertura
python bench/salidas-verificador-gs/medir_gs.py reglas
python bench/salidas-verificador-gs/medir_gs.py contrato
python bench/salidas-verificador-gs/medir_gs.py fidelidad
python bench/salidas-verificador-gs/medir_gs.py fallos
python bench/salidas-verificador-gs/discrimina_v2_v5.py
python bench/salidas-verificador-gs/ocr_gs.py sonda
python bench/salidas-verificador-gs/ocr_gs.py cer
python bench/salidas-verificador-gs/ocr_gs.py ppp
python bench/salidas-verificador-gs/ocr_gs.py tiempo
python bench/salidas-verificador-gs/ocr_gs.py reparacion
python bench/salidas-verificador-gs/ocr_gs.py acentos
python bench/salidas-verificador-gs/senal_alucinacion.py
```

**Requisito previo de todo lo de OCR:** el directorio `tessdata/`, que se
reconstruye con tres copias (no hay que descargar nada en esta máquina):

```
copy "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" tessdata\
copy "C:\Program Files\Tesseract-OCR\tessdata\osd.traineddata" tessdata\
copy "C:\Program Files\PDFgear\tessdata\spa.traineddata"       tessdata\
```

Y `TESSDATA_PREFIX` apuntando a ese directorio **en el entorno del proceso
hijo**, nunca en la máquina: los scripts lo hacen solos.

---

## Lo que SÍ queda versionado

| Fichero | Qué es |
|---|---|
| `gen_fixtures.py`, `gen_predictor.py`, `gen_adam7_4b.py` | Generadores de los ficheros de prueba |
| `prueba_alfa.py` | Contraste de `min(alfa)` en proceso contra `magick` |
| `medir_gs.py` | Banco de medida (copia adaptada de `medir_fid.py`, que no se toca) |
| `discrimina_v2_v5.py` | Los cuatro fallos fabricados que V2 y V5 deben atrapar |
| `ocr_gs.py` | Banco del OCR embebido de Ghostscript |
| `ocr_eval_tildes.py` | Evaluador de OCR **sensible a las tildes** (copia de `ocr_eval.py`) |
| `senal_alucinacion.py` | La señal que separa texto recuperado de ruido con forma de texto |
| `*.json` | Todos los datos crudos |
| `ocr/*.txt` | El texto que devolvió cada OCR |

---

## Binarias borradas, con su reproducción


| Fichero | Bytes | sha256 (12) | Orden que lo reproduce |
|---|---:|---|---|
| `fixtures/acentos_150ppp.pdf` | 17271 | `81612c79b9de` | ``ocr_gs.py acentos`` |
| `fixtures/acentos_150ppp.png` | 16746 | `84fd40444537` | ``ocr_gs.py acentos`` |
| `fixtures/adam7_4b_esquina.png` | 151 | `d164609aaa2a` | `gen_adam7_4b.py` |
| `fixtures/adam7_4b_opaco.png` | 151 | `d9d00030de60` | `gen_adam7_4b.py` |
| `fixtures/alpha_adam7.png` | 3335 | `305766d92b50` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -interlace PNG PNG:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\alpha_adam7.png` |
| `fixtures/alpha_adam7_4b.png` | 1736 | `df847c52b956` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -colors 12 -define png:color-type=3 -define png:bit-depth=4 -interlace PNG PNG:D:\Work\resear...` |
| `fixtures/alpha_adam7_rgba.png` | 5238 | `16059d815a69` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define png:color-type=6 -define png:bit-depth=8 -interlace PNG PNG:D:\Work\research\FileX\be...` |
| `fixtures/alpha_adam7_rgba16.png` | 6712 | `894686c46324` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define png:color-type=6 -define png:bit-depth=16 -interlace PNG PNG:D:\Work\research\FileX\b...` |
| `fixtures/alpha_gif.gif` | 2598 | `0affa2852391` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png GIF:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\alpha_gif.gif` |
| `fixtures/alpha_tiff_lzw.tif` | 4344 | `60af9ab9152b` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -compress LZW TIFF:D:\Work\research\FileX\bench\salidas-verif...` |
| `fixtures/alpha_tiff_lzw16.tif` | 6012 | `52a9c6117708` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -depth 16 -define tiff:alpha=unassociated -compress LZW TIFF:D:\Work\research\FileX\bench\sal...` |
| `fixtures/alpha_tiff_lzw_p1.tif` | 3272 | `4fe7c3a9aafb` | `gen_predictor.py` |
| `fixtures/alpha_tiff_lzw_pred.tif` | 4344 | `60af9ab9152b` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -define tiff:predictor=2 -compress LZW TIFF:D:\Work\research\...` |
| `fixtures/alpha_tiff_lzw_pred2.tif` | 3767 | `4da11c01fdca` | `gen_predictor.py` |
| `fixtures/alpha_tiff_none.tif` | 160290 | `589dc3611e6b` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -compress None TIFF:D:\Work\research\FileX\bench\salidas-veri...` |
| `fixtures/alpha_tiff_planar.tif` | 5956 | `31b2fa4f6069` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -interlace Plane -compress LZW TIFF:D:\Work\research\FileX\be...` |
| `fixtures/alpha_tiff_rle.tif` | 26608 | `34e48eba06de` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -compress RLE TIFF:D:\Work\research\FileX\bench\salidas-verif...` |
| `fixtures/alpha_tiff_zip.tif` | 3746 | `68888a656180` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -compress Zip TIFF:D:\Work\research\FileX\bench\salidas-verif...` |
| `fixtures/alpha_tiff_zip_pred.tif` | 3746 | `68888a656180` | `magick D:\Work\research\FileX\corpus\imagen\alpha.png -define tiff:alpha=unassociated -define tiff:predictor=2 -compress Zip TIFF:D:\Work\research\...` |
| `fixtures/alpha_tiff_zip_pred2.tif` | 3279 | `2d79ea5de3ff` | `gen_predictor.py` |
| `fixtures/plano_4b_esquina.png` | 124 | `f40a0757908a` | `gen_adam7_4b.py` |
| `fixtures/tipico_adam7.png` | 54646 | `639527e538ce` | `magick D:\Work\research\FileX\corpus\imagen\tipico.png -interlace PNG PNG:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\tipico_adam7...` |
| `fixtures/tipico_adam7_8b.png` | 27299 | `b8c2a54ddc29` | `magick D:\Work\research\FileX\corpus\imagen\tipico.png -depth 8 -interlace PNG PNG:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\tip...` |
| `fixtures/tipico_gif_opaco.gif` | 99971 | `bd50e2463fb3` | `magick D:\Work\research\FileX\corpus\imagen\tipico.png -alpha off GIF:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\tipico_gif_opaco...` |
| `fixtures/tipico_tiff_lzw.tif` | 62780 | `8657fd0ee6c3` | `magick D:\Work\research\FileX\corpus\imagen\tipico.png -define tiff:alpha=unassociated -compress LZW TIFF:D:\Work\research\FileX\bench\salidas-veri...` |
| `fixtures/tipico_tiff_zip16.tif` | 46986 | `b4798f6f194b` | `magick D:\Work\research\FileX\corpus\imagen\tipico.png -define tiff:alpha=unassociated -compress Zip TIFF:D:\Work\research\FileX\bench\salidas-veri...` |
| `fixtures/trivial_gif_opaco.gif` | 110 | `329fae3b346f` | `magick D:\Work\research\FileX\corpus\imagen\trivial.png GIF:D:\Work\research\FileX\bench\salidas-verificador-gs\fixtures\trivial_gif_opaco.gif` |
| `ocr/escaneado_d1_directo.docx` | 9837 | `2f08b600e624` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d1_ocr.docx` | 10157 | `920b1580257e` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d1_ocr_spa.pdf` | 651016 | `de2469513c93` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d1_pdfocr8.pdf` | 651016 | `8917b472c82b` | ``ocr_gs.py tiempo`` |
| `ocr/escaneado_d2_directo.docx` | 9837 | `c12f4754b34e` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d2_ocr.docx` | 10160 | `c7b2d18b50c6` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d2_ocr_spa.pdf` | 358432 | `9b35425db5ef` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d2_pdfocr8.pdf` | 358432 | `062d2dc801c6` | ``ocr_gs.py tiempo`` |
| `ocr/escaneado_d3_directo.docx` | 9837 | `c12f4754b34e` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d3_ocr.docx` | 10622 | `80850ac1b5b9` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d3_ocr_spa.pdf` | 403868 | `8f3d39175c57` | ``ocr_gs.py reparacion`` |
| `ocr/escaneado_d3_pdfocr8.pdf` | 403868 | `1ad791170ed2` | ``ocr_gs.py tiempo`` |
| `ocr/i1_rasterizado.pdf` | 8643 | `ca0aa2103bdf` | ``ocr_gs.py reparacion` (cadena I1)` |
| `ocr/i1_rasterizado.png` | 15804 | `cfb4324c638d` | ``ocr_gs.py reparacion` (cadena I1)` |
| `ocr/patologico_escaneado_directo.docx` | 9837 | `2f08b600e624` | ``ocr_gs.py reparacion`` |
| `ocr/patologico_escaneado_ocr.docx` | 10150 | `41e1537b4b88` | ``ocr_gs.py reparacion`` |
| `ocr/patologico_escaneado_ocr_spa.pdf` | 1091107 | `c416c06dbb95` | ``ocr_gs.py reparacion`` |
| `ocr/patologico_escaneado_pdfocr8.pdf` | 1091107 | `62590b289dde` | ``ocr_gs.py tiempo`` |
| `tessdata/eng.traineddata` | 4113088 | `7d4322bd2a77` | `copia del tessdata del sistema (ver arriba)` |
| `tessdata/osd.traineddata` | 10562727 | `9cf5d576fcc4` | `copia del tessdata del sistema (ver arriba)` |
| `tessdata/spa.traineddata` | 2294433 | `6f2e04d02774` | `copia del tessdata del sistema (ver arriba)` |

**Total borrado: 48 ficheros, 21.6 MB.**
