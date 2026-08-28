# MANIFIESTO — `bench/salidas-metrica-ocr/` (agente A7, informe `bench/metrica-ocr.md`)

Todo lo de aquí es **texto y aritmética sobre texto**. No se usó la GPU, no se
tomó el lock de GPU y no se invocó ni un motor externo: las entradas son las
**2 917 salidas de OCR que ya estaban en disco** en `bench/salidas-*/texto/`.
Por eso no hay censo de ficheros huérfanos que declarar (R21): `git status`
al terminar sólo muestra `bench/scripts/ocr_eval.py` modificado y este
directorio nuevo.

## Cómo se reproduce, en orden

```bash
cd bench/salidas-metrica-ocr
python 01_inventario.py          # ~3 s   -> inventario.json
python 02_recalculo.py           # ~40 s  -> recalculo.json
python 03_control_publicado.py   # ~2 s   -> control_publicado.json
python 04_impacto.py             # ~5 s   -> impacto.json
python 05_conclusiones.py        # ~30 s  -> conclusiones_d4ac.json, conclusiones_tildes.json
python 06_mecanismo.py           # ~10 s  -> mecanismo.json
python 07_factorial.py           # ~60 s  -> factorial.json
python 08_regresion.py           # ~90 s  -> regresion.json
```

`02`, `07` y `08` usan `rapidfuzz` 3.14.5 (ya instalado). `02_recalculo.py`
lleva un **control positivo** que comprueba que `rapidfuzz.Levenshtein`
coincide con el `lev` en Python puro de los tres evaluadores; si no, aborta.

## Ficheros

| fichero | qué es |
|---|---|
| `01_inventario.py` … `08_regresion.py` | los ocho pasos, en orden |
| `ocr_eval_ciego.py` | **copia byte a byte de `bench/scripts/ocr_eval.py` ANTES de tocarlo** (`sha256 fc641c63874a70f0…`). Es el testigo de la regresión: sin él no se puede demostrar que la vía ciega sigue dando lo mismo |
| `ocr_eval_d4.py`, `d4_texto.py` | copias byte a byte de `bench/salidas-corpus-d4/` (`9cf596be08db5477…`, `77bc1223b891d02d…`). Se importan, no se modifican |
| `ocr_eval_tildes.py` | copia byte a byte de `bench/salidas-verificador-gs/` (`dec03caa2fac55f6…`) |
| `recalculo.json` | **la evidencia**: las 2 917 celdas con su CER bajo las tres métricas |
| `impacto.json`, `conclusiones_*.json`, `control_publicado.json`, `mecanismo.json`, `regresion.json` | los resúmenes de cada paso |

## Lo que NO se versiona (regenerable, y pesa)

| fichero | tamaño | orden que lo reproduce |
|---|---:|---|
| `inventario.json` | 854 KB | `python 01_inventario.py` |
| `factorial.json` | 760 KB | `python 07_factorial.py` |
| `__pycache__/` | — | se regenera solo |

`inventario.json` es **entrada** de `02`, `07` y `08`: hay que generarlo antes.

## `sha256` de lo que sí se versiona

```
2a4131660f702cc3…  bench/scripts/ocr_eval.py        (MODIFICADO por A7)
fc641c63874a70f0…  ocr_eval_ciego.py                (el original, testigo)
9cf596be08db5477…  ocr_eval_d4.py
dec03caa2fac55f6…  ocr_eval_tildes.py
77bc1223b891d02d…  d4_texto.py
16168e27c04b26b5…  recalculo.json
```

## Nada de esto se ha tocado

`bench/scripts/mcp_probe_bin.py`, `bench/salidas-mcp/mcp_probe.py`,
`bench/lib/harness.sh`, `bench/salidas-referencia/referencia.json`,
`bench/scripts/ocr_motor.py`, ningún fichero de `filex/`, ningún informe de
`bench/` que no sea `bench/metrica-ocr.md`, y ninguna de las copias
`ocr_eval_d4.py` / `ocr_eval_tildes.py` / `ocr_eval_p2.py` / `ocr_eval_km.py` /
`ocr_eval_pn.py` / `ocr_eval_psm.py` / `ocr_eval_pm.py` en sus directorios de
origen. El único fichero compartido modificado es `bench/scripts/ocr_eval.py`,
que **es el encargo**.
