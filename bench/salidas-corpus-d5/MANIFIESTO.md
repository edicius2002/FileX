# MANIFIESTO — `bench/salidas-corpus-d5/` (agente G3, 22 de agosto de 2026)

Informe: **`bench/corpus-d5.md`**. Tablas completas: **`tablas.md`**.
Corpus producido: **`corpus/pdf/MANIFIESTO-d5.md`**.

**GPU: no usada, lock no tomado.** Todo es CPU (`magick`, `gswin64c`, `tesseract`).

---

## 1. Lo que se ha borrado y por qué

**157,3 MB de intermedios borrados al terminar**, según `CLAUDE.md` §6:

| directorio | qué contenía | MB |
|---|---|---:|
| `tmp/` | las dos páginas maestras a 600 ppp, el reverso para la transparencia, los PNG intermedios de cada receta (base, viñeta, lámpara, iluminación, pre, curvado, encuadernación), los JPEG y los PDF de cribado | 104,4 |
| `img/` | todas las rasterizaciones a PNG de las nueve tandas (ImageMagick y Ghostscript, de 60 a 300 ppp) | 52,9 |

**Todo se regenera** con las órdenes de §3. Lo que se conserva es texto: los `.py`, los
`.json`, las 220 salidas literales de OCR y los registros.

## 2. Los ficheros que se conservan

| fichero | `sha256` | bytes |
|---|---|---:|
| `d4_texto.py` | `fa4b8d5d74980b29f0e640911c42ea07e59ca3910f364bd599407cb79c3cf011` | 2 837 |
| `ocr_eval_d4.py` | `350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82` | 6 418 |
| `d5_texto.py` | `ff03627aa6053ec55801533f6e12ad7b7987862a40fe2dc2f374a0af8613b176` | 4 102 |
| `gen_corpus_d5.py` | `c7cf8e175fdbfdd888dda32a9dc0a41c0c8e76dbb382ec973f6d92bfdb70ceda` | 18 943 |
| `tess_lote_d5.py` | `ee05d8ba3b8bfda8807a3a622476f3602dbbff2a82caa54c508d8dc9c15ddd76` | 7 325 |
| `sonda_densidad.py` | `c4a037826f664bc98bfb28a114f46a988917cca0b2f268747d49ed867f2b5159` | 4 567 |
| `sonda_degradacion.py` | `2ff699cc3aa3d9c56a441fc3646d10469a53cdff991381810faee0d54c9ab20b` | 4 963 |
| `manifiesto_d5.py` | `8919d50ebb7185bb296cb7ee0464bd2f77f2258214b4d099589a2c22ca0f8881` | 3 817 |
| `tablas_d5.py` | `5a8c49c431eb71137a0b863a7ace5d202448ab9352a6158ccd67d61055320d93` | 14 762 |

**`d4_texto.py` y `ocr_eval_d4.py` son copias BYTE A BYTE** de
`bench/salidas-corpus-d4/`. Los dos `sha256` coinciden con los de los originales:
comprobado. **Los originales no se han modificado.**

## 3. Las órdenes exactas que reproducen todo

Desde `D:\Work\research\FileX\bench\salidas-corpus-d5`, con
`..\..\.venv-ai\Scripts\python.exe`:

```
:: 1 · el corpus (12 PDF a corpus/pdf/ + el control d5_limpio a tmp/)
python gen_corpus_d5.py --corpus d5_limpio escaneado_d5 escaneado_d5a escaneado_d5b ^
    escaneado_d5c patologico_d5a patologico_d5b patologico_d5 patologico_d5e ^
    realista_d5a realista_d5b realista_d5 realista_d5e

:: 2 · las ablaciones y los barridos (no van al corpus, se quedan en tmp/)
python gen_corpus_d5.py abl_p5b_imp02 abl_p5b_ilum abl_p5b_blur06 abl_p5b_jq60 ^
    abl_p5b_niv12 abl_p5b_rui10 abl_p5b_sinray abl_r5_sinonda
python gen_corpus_d5.py cand_p5_v78 cand_p5_v74 cand_p5_v70 cand_p5_v66 ^
    cand_p5_v62 cand_p5_v56 cand_p5_v50
python gen_corpus_d5.py cand_p5_i045 cand_p5_i080 cand_p5_i120 cand_p5_i180 ^
    cand_p5_i250 cand_p5_i350

:: 3 · las nueve tandas de OCR (variables de entorno RASTER, PSM, LANGS)
set RASTER=magick& set PSM=3,11& set LANGS=spa& python tess_lote_d5.py cribado <12 docs>
set PSM=3,11& python tess_lote_d5.py ablacion abl_p5b_*
set PSM=3,11& python tess_lote_d5.py barrido_ilum cand_p5_v*
set PSM=3,11& python tess_lote_d5.py barrido_polvo cand_p5_i*
set PSM=3,6,11& set LANGS=spa,eng& python tess_lote_d5.py v1_canonica <15 docs>
set RASTER=gs& set PSM=3,11& set LANGS=spa& python tess_lote_d5.py v2_gs <13 docs>
set RASTER=magick& python tess_lote_d5.py v3_ppp escaneado_d5b:60 escaneado_d5b:75 ...
set PSM=3,11& python tess_lote_d5.py control_onda abl_r5_sinonda

:: 4 · las dos sondas
python sonda_densidad.py
python sonda_degradacion.py

:: 5 · manifiestos y tablas
python manifiesto_d5.py
python tablas_d5.py
```

`tess_lote_d5.py` acepta `doc` o `doc:ppp` (`nativo` es el valor por defecto).
**El rasterizado se borra con `img/`, así que hay que rehacer el paso 1 antes de
cualquier tanda de OCR.**

## 4. Los `.json` (13 ficheros, 266 celdas de OCR)

| fichero | celdas | qué mide |
|---|---:|---|
| `candidatas_d5.json` | 13 | parámetros, píxeles, `sha256` de `.jpg` y `.pdf` de cada variante generada |
| `manifiesto_d5.json` | 12 | ppp nativos leídos del PDF, `sha256`, bytes |
| `tess_cribado.json` | 28 | primer cribado de las 12 candidatas + `d4` y `d4c` de referencia |
| `tess_ablacion.json` | 14 | las cinco patologías de escáner, una apagada cada vez (§3.1) |
| `tess_barrido_ilum.json` | 14 | los 7 puntos del barrido de iluminación — el interruptor (§3.2) |
| `tess_barrido_polvo.json` | 12 | los 6 puntos del barrido de polvo — la escalera buena (§3.3) |
| `tess_escalera.json` | 16 | la escalera intermedia descartada, con sus tres controles de reproducción |
| `tess_v1_canonica.json` | **90** | la validación: 15 docs × 3 `--psm` × 2 idiomas (§6.1, §6.2) |
| `tess_v2_gs.json` | 26 | los 12 del corpus + `d4` rasterizados con Ghostscript |
| `tess_v3_ppp.json` | **64** | el barrido de ppp sobre B15 — la medida del suelo (§2.2) |
| `tess_control_onda.json` | 2 | el control de curvatura `onda = 0` |
| `sonda_densidad.json` | 16 | el A/B del `pHYs`: mismo PNG con y sin densidad declarada (§4) |
| `sonda_degradacion.json` | 9 | sombra, curvatura y transparencia medidas en el píxel (§5) |

`texto/` guarda las **220** salidas literales de Tesseract, con el nombre
`<doc>__<raster>__ppp<N>__psm<M>__<lang>.txt`.

## 5. Advertencias para quien reutilice esto

1. **Use `ocr_eval_d4.py` con `rid="d4"`.** `bench/scripts/ocr_eval.py` es ciego a las
   tildes y sobre estos 610 caracteres (35 acentuados) mide de menos.
2. **Declare con qué rasterizó Y si el raster llevaba la densidad escrita.** No es lo
   mismo: sobre `escaneado_d4` con `psm 3` son **33,22 puntos** de diferencia con los
   **mismos píxeles** (`bench/corpus-d5.md` §4).
3. **Declare el `--psm`.** Sobre `patologico_d5` mueve 24,16 puntos y sobre
   `realista_d5e` 38,76.
4. **El PNG maestro y el PDF NO son reproducibles bit a bit; el JPEG intermedio SÍ.**
   Verificado con cinco ficheros regenerados en tandas distintas.
5. **`bench/salidas-referencia/referencia.json` no se ha abierto**, y
   `bench/scripts/mcp_probe_bin.py` ni `bench/salidas-mcp/mcp_probe.py` tampoco.
