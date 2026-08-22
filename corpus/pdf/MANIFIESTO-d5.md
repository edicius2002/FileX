# MANIFIESTO — familia `d5` del corpus de OCR

**Agente G3**, 22 de agosto de 2026. Generados por
`bench/salidas-corpus-d5/gen_corpus_d5.py`, **copia adaptada** de
`bench/salidas-corpus-d4/gen_corpus_d4.py` (que a su vez lo es de
`bench/scripts/gen_corpus_ocr.sh`). **Ninguno de los dos originales se ha
tocado.** Los diez PDF anteriores de `corpus/pdf/` tampoco.

Informe completo: **`bench/corpus-d5.md`**. Celdas: `bench/salidas-corpus-d5/tablas.md`.

---

## 1. Los doce ficheros

`ppp nativos` NO es un dato declarado a mano: sale de leer el PDF con
`pypdfium2` (ancho en px de la imagen incrustada / ancho de pagina en
pulgadas), igual que hace `bench/salidas-corpus-d4/preparar_img.py`.

| fichero | familia | ppp nativos | px | ancho pagina (pt) | bytes | CER Tesseract (min–max de 6 config.) | sha256 |
|---|---|---:|---|---:|---:|---:|---|
| `escaneado_d5b.pdf` | B15 bajo ppp | 60 | 388x531 | 465.6 | 18870 | 25,34 – 38,09 | `fa9e2d095c2debb9e98db82c00c9bdeee781a9ca62ed3faa992acf5d0d47075a` |
| **`escaneado_d5.pdf`** | B15 bajo ppp | 72 | 465x636 | 465.0 | 25555 | 10,07 – 25,17 | `c04b242c8758ca98fa96a4613c2ca3fb3cc5cadecb20451e17d11cd9845b8dfe` |
| `escaneado_d5c.pdf` | B15 bajo ppp | 80 | 517x708 | 465.3 | 29084 | 2,01 – 19,13 | `762626e157475f299ffbd1d475eff4ecb7f54b638b0efeb3d28283814b5eec23` |
| `escaneado_d5a.pdf` | B15 bajo ppp | 90 | 582x801 | 465.6 | 40551 | 1,17 – 12,58 | `b8f61c83269be9d1147564a37acc4f323351c48b824faf2cba6b1e663ba7a77a` |
| `patologico_d5a.pdf` | B19 patologico | 200 | 1294x1752 | 465.84 | 201924 | 10,74 – 42,95 | `1a99dd3e933ebcd09fb17b7cf353e50b5399f0fe5a38b59df79b530bb383a788` |
| `patologico_d5b.pdf` | B19 patologico | 200 | 1294x1752 | 465.84 | 301364 | 14,60 – 44,63 | `2f1ac7c35a5aa9bda8a012a9ea4144b5d5828312092ced7a79ba6735e1928080` |
| **`patologico_d5.pdf`** | B19 patologico | 200 | 1294x1752 | 465.84 | 362861 | 31,88 – 59,56 | `c2d7f29ba7048d2a7e18bb3b691a5a8c7da5acea7eb5ea234831468fd532d43b` |
| `patologico_d5e.pdf` | B19 patologico | 200 | 1294x1752 | 465.84 | 437167 | 42,79 – 56,21 | `88cc08efc5d66ef93d22b5eb875e57b898ef1aba10d106e2319476bfbaa5662a` |
| `realista_d5a.pdf` | B12 realista | 200 | 1294x1782 | 465.84 | 100797 | 0,17 – 11,24 | `691a6235865f42b0bae2ee4db12355a1e5212ed76329d671037667a11c2572cd` |
| `realista_d5b.pdf` | B12 realista | 200 | 1294x1771 | 465.84 | 97231 | 9,40 – 41,95 | `a787d524456360248a7aaf74366c19123946ae7299fe86b2e6aac73d31d25dd5` |
| **`realista_d5.pdf`** | B12 realista | 200 | 1294x1762 | 465.84 | 84535 | 27,01 – 35,23 | `5ef4b642d45205b53237eae62845e8edfc2387213577d298114a0e4aaad3d0a1` |
| `realista_d5e.pdf` | B12 realista | 200 | 1294x1752 | 465.84 | 68991 | 36,07 – 76,85 | `09a8fccae06604f237309b16bccd64abaa2a3064a484ccde55963dcf7f5665a3` |

Los tres en negrita son los **canonicos** de cada familia. Las 610 caracteres de referencia son los mismos para los doce.

## 2. Texto de referencia

**`corpus/pdf/REFERENCIA-d5.txt`** — 610 caracteres crudos, 35 acentuados,
cuatro bloques. Es **exactamente** el de `escaneado_d4`, a proposito: asi los
doce documentos nuevos son comparables celda a celda con las 396 de
`bench/k-por-motor.md` y con las 28 de `bench/corpus-d4.md`. Fuente unica de
verdad: `bench/salidas-corpus-d4/d4_texto.py` (copiado byte a byte a
`bench/salidas-corpus-d5/d4_texto.py`), que importan el generador Y el
evaluador.

**Evaluador obligatorio: `bench/salidas-corpus-d4/ocr_eval_d4.py` con
`rid="d4"`.** `bench/scripts/ocr_eval.py` es ciego a las tildes y sobre este
texto mide de menos.

## 3. La orden exacta que los reproduce

```
cd D:\Work\research\FileX\bench\salidas-corpus-d5
python gen_corpus_d5.py --corpus d5_limpio escaneado_d5 escaneado_d5a \
    escaneado_d5b escaneado_d5c patologico_d5a patologico_d5b patologico_d5 \
    patologico_d5e realista_d5a realista_d5b realista_d5 realista_d5e
python gen_corpus_d5.py --corpus patologico_d5   # solo uno
# SIN nombres regenera tambien las 7 ablaciones y los 13 puntos de barrido,
# que no van al corpus: se quedan en tmp/.
```
El generador usa `magick -seed 20260822`. **Sin esa semilla `+noise` es
aleatorio y el fichero no es reproducible.**

Parametros de cada variante (los mismos que estan en `CANDIDATAS`):

| fichero | receta | parametros |
|---|---|---|
| `escaneado_d5b` | bajo_ppp | `ppp=60`, `ang=1`, `blur=0.3`, `nivel=10%,92%`, `ruido=0.15`, `jq=60` |
| `escaneado_d5` | bajo_ppp | `ppp=72`, `ang=1`, `blur=0.3`, `nivel=10%,92%`, `ruido=0.15`, `jq=60` |
| `escaneado_d5c` | bajo_ppp | `ppp=80`, `ang=1`, `blur=0.3`, `nivel=10%,92%`, `ruido=0.15`, `jq=60` |
| `escaneado_d5a` | bajo_ppp | `ppp=90`, `ang=0.5`, `blur=0.2`, `nivel=6%,94%`, `ruido=0.1`, `jq=70` |
| `patologico_d5a` | patologico | `ppp=200`, `ang=-2`, `blur=1.0`, `nivel=24%,80%`, `vinieta=78`, `lampara=85`, `impulso=0.12`, `ruido=0.25`, `jq=40`, `rayas=[[0.31, 35], [0.62, 84]]` |
| `patologico_d5b` | patologico | `ppp=200`, `ang=-2`, `blur=1.0`, `nivel=24%,80%`, `vinieta=78`, `lampara=85`, `impulso=0.25`, `ruido=0.25`, `jq=40`, `rayas=[[0.31, 35], [0.62, 84]]` |
| `patologico_d5` | patologico | `ppp=200`, `ang=-2`, `blur=1.0`, `nivel=24%,80%`, `vinieta=78`, `lampara=85`, `impulso=0.35`, `ruido=0.25`, `jq=40`, `rayas=[[0.31, 35], [0.62, 84]]` |
| `patologico_d5e` | patologico | `ppp=200`, `ang=-2`, `blur=1.0`, `nivel=24%,80%`, `vinieta=78`, `lampara=85`, `impulso=0.5`, `ruido=0.25`, `jq=40`, `rayas=[[0.31, 35], [0.62, 84]]` |
| `realista_d5a` | realista | `ppp=200`, `ang=0.5`, `onda=6`, `onda_long=2600`, `reverso_nivel=88`, `lomo=72`, `lomo_frac=0.18`, `blur=0.5`, `nivel=10%,92%`, `ruido=0.15`, `jq=60` |
| `realista_d5b` | realista | `ppp=200`, `ang=1`, `onda=12`, `onda_long=2600`, `reverso_nivel=80`, `lomo=58`, `lomo_frac=0.2`, `blur=0.9`, `nivel=18%,86%`, `ruido=0.25`, `jq=45` |
| `realista_d5` | realista | `ppp=200`, `ang=-1.5`, `onda=20`, `onda_long=2600`, `reverso_nivel=72`, `lomo=45`, `lomo_frac=0.22`, `blur=1.2`, `nivel=26%,80%`, `ruido=0.35`, `jq=33` |
| `realista_d5e` | realista | `ppp=200`, `ang=2`, `onda=28`, `onda_long=2600`, `reverso_nivel=64`, `lomo=34`, `lomo_frac=0.24`, `blur=1.5`, `nivel=32%,74%`, `ruido=0.45`, `jq=25` |

## 4. Aviso de reproducibilidad — MEDIDO

Igual que en `d4`: **el JPEG intermedio es reproducible bit a bit; el PDF no**,
porque ImageMagick estampa `/CreationDate` y no honra `SOURCE_DATE_EPOCH`.
**Y esta vez tambien se midio el PNG maestro, que TAMPOCO lo es**: su `sha256`
cambio en las seis ejecuciones y los JPEG derivados salieron identicos, asi
que la diferencia esta en los metadatos del PNG, no en los pixeles.

Comprobado en **cinco** ficheros regenerados en tandas distintas: `patologico_d5a`, `patologico_d5b`, `patologico_d5`, `realista_d5` y
`realista_d5e` dieron el **mismo sha256 de `.jpg`** y **distinto sha256 de
`.pdf`**.

| fichero | sha256 del `.jpg` (**reproducible**) | bytes del `.jpg` |
|---|---|---:|
| `escaneado_d5b` | `fc650e26461ef76ee69012365b260560f6b83205c4a7203531bf6808bbaf070f` | 16092 |
| `escaneado_d5` | `3211b0f6b5c6aaac1c8f5a897446512173fbbbfcf08732f45857dfbf08c83b70` | 22785 |
| `escaneado_d5c` | `9d86f1800a8c71d149786ec15ed8eef02738691fd58678b7d748267e66b3d640` | 26311 |
| `escaneado_d5a` | `8436773eede223e91766a0e815d74340de5bff9c109a871f409e6eaafba30fa0` | 37731 |
| `patologico_d5a` | `e5001274ad254669039e7ee0a1524c8d8ce4034ff8157fcf680d2b96dfe9069d` | 199104 |
| `patologico_d5b` | `9e4094a7495c0f903f6798e0735a095527d591fa3943aee0916f76addbd3f74d` | 298505 |
| `patologico_d5` | `9d4d2e869cbebf523a4c0b7967e6af0008c699371ca7fd83425db240b2e84428` | 360187 |
| `patologico_d5e` | `6ff6642f53d30710edcbf0d4e2db0bf9db71c4e0c5af4b3564310b237a8f8beb` | 434585 |
| `realista_d5a` | `9fe1345fde0bbf8b71f1901c7b519828adfc4849e2168ee419cbd75700effa36` | 97977 |
| `realista_d5b` | `dda8a6960fa6d086ac4547f07c712100c8142bf6f9c1bf4b46e9af4fdf08a580` | 94477 |
| `realista_d5` | `5c7ad5e175e4f116ab474b99b5a9dd383baf27724916f1832b86a8542a9196f9` | 81753 |
| `realista_d5e` | `03bec2d76b445b5e587ab2014bf8cf59279eaceba14c632a99d2131896e0869d` | 66242 |

El `sha256` del PDF de la tabla 1 identifica **estos** ficheros concretos y
sirve para detectar corrupcion, no para verificar una regeneracion.

## 5. Como medir con ellos

- **ppp:** los de la columna 3. Y **lea `bench/corpus-d5.md` §2 antes de
  aplicar la regla vigente**: sobre `escaneado_d5b` (60 ppp nativos) la formula
  `min(max(n,100), n x 1,25)` devuelve **75 ppp**, y eso cuesta **hasta 16,8
  puntos** de CER frente a rasterizar a los 100 del suelo. **El suelo de 100 es
  aritmeticamente inalcanzable por debajo de 80 ppp nativos.**
- **Declare la densidad en el raster.** Escribir `-units PixelsPerInch
  -density N` en el PNG **sin tocar un pixel** mueve el CER de Tesseract hasta
  **33,22 puntos** (`bench/corpus-d5.md` §4). Sin declararla, Tesseract la
  estima — y sobre `escaneado_d4` estima **403 ppp** donde hay 200.
- **Declare el `--psm`.** Sobre estos doce documentos el `--psm` mueve hasta
  **38,8 puntos** (`patologico_d5e`, 92,62 vs 53,02 en el cribado).

