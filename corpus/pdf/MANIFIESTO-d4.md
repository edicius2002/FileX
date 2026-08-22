# MANIFIESTO — familia `escaneado_d4` del corpus de OCR

**Agente G1**, 21 de agosto de 2026. Generados por
`bench/salidas-corpus-d4/gen_corpus_d4.py`, que es una **copia adaptada** de
`bench/scripts/gen_corpus_ocr.sh` (el original no se tocó: sigue regenerando
`d1`/`d2`/`d3`, que son la base de 296 celdas ya medidas).

Los cuatro escaneados anteriores (`patologico_escaneado`, `escaneado_d1`,
`escaneado_d2`, `escaneado_d3`) **no se han tocado**.

---

## 1. Qué es cada fichero

`escaneado_d4.pdf` es **el documento canónico**: la candidata que ganó el cribado
(era `d4d` durante el barrido). Las otras cinco son la **escala de degradación**
completa, de más fácil a más difícil, y sirven para calibrar heurísticas.

| fichero | ppp nativos | px | ángulo | ruido | `+level` | blur | JPEG q | bytes | sha256 |
|---|---:|---|---:|---:|---|---:|---:|---:|---|
| `escaneado_d4a.pdf` | 200 | 1294×1752 | 2 | 0,20 | `12%,90%` | 0,4 | 60 | 122 577 | `602e87b430f26b2b31bafbc3fb9f8839e20183bf7820d081f4f1d438b909bb43` |
| `escaneado_d4b.pdf` | 200 | 1294×1734 | −3 | 0,35 | `20%,84%` | 0,8 | 45 | 129 390 | `62e12565ff4c01bd2d40a255383fc8f440238bd69322fd1af151a650451742be` |
| `escaneado_d4c.pdf` | 200 | 1294×1734 | 3 | 0,50 | `28%,78%` | 1,2 | 32 | 116 902 | `b566c9a31d0836ae9cf9a67c6780d7fc1f08fc3bc992d0d2c76b31caaa32d2c0` |
| **`escaneado_d4.pdf`** | **200** | **1294×1716** | **−4** | **0,65** | **`34%,72%`** | **1,6** | **24** | **103 365** | `644ea27431e1508ea342cbf55216a368244c9d0d10bc928c79e4e7715643af02` |
| `escaneado_d4e.pdf` | 200 | 1294×1716 | 4 | 0,80 | `40%,68%` | 2,0 | 18 | 86 659 | `3a11d9af97f96fa5ba4070184105eb6cde3c6766a04f9b5504320c8867789068` |
| `escaneado_d4f.pdf` | 240 | 1552×2080 | 3 | 0,55 | `30%,76%` | 1,4 | 28 | 151 807 | `e6f8eb2f3b60da075907cd308a3e9a51f8f75ce5f50a5b726d3ae6b2e97d2e3b` |

**Texto de referencia** (610 caracteres, castellano con tildes, ñ/Ñ, ü, ¿ ¡, cifras y
puntuación; **distinto del de d1-d3**, que son 79 caracteres sin tildes). Fuente única
de verdad: `bench/salidas-corpus-d4/d4_texto.py`. Cuatro bloques de tamaño de letra
decreciente: título 24 pt, subtítulo 13 pt, cuerpo 11 pt (6 líneas), letra pequeña
7 pt (4 líneas).

```
INFORME DE DIGITALIZACIÓN
Expediente núm. 4.827/2026 - Archivo Histórico
El día 14 de marzo se recibió la solicitud de análisis
técnico sobre veintiún volúmenes encuadernados en piel.
La comisión determinó que la reproducción fotográfica
debía realizarse con iluminación difusa y sin contacto,
según la norma UNE 15-402, para evitar daños añadidos
en los pliegos más frágiles del año 1893.
¿Quién autorizó la excepción? El párrafo tercero señala
que la revisión ortográfica y lingüística del legajo
es responsabilidad del área de conservación preventiva.
¡Atención! Los códigos 7-B, 9-Ñ y 12-K quedan anulados.
```

## 2. La orden exacta que los reproduce

```
cd D:\Work\research\FileX\bench\salidas-corpus-d4
python gen_corpus_d4.py                 # todas las candidatas + las de ablación
python gen_corpus_d4.py escaneado_d4    # solo la canónica
```

El generador usa `magick -seed 20260821`. **Sin esa semilla `+noise Gaussian` es
aleatorio y el fichero no es reproducible**; con ella, sí.

La cadena por variante, en este orden (el mismo del generador original):

```
magick -seed 20260821 tmp/d4_master.png -background white -rotate <ang> \
       -resize <ancho>x [-blur 0x<blur>] -colorspace Gray [+level <nivel>] \
       -attenuate <ruido> +noise Gaussian -quality <jq> tmp/<nombre>.jpg
magick tmp/<nombre>.jpg -units PixelsPerInch -density <ppp> corpus/pdf/<nombre>.pdf
```

La página maestra (`tmp/d4_master.png`, 3882×5376, 600 ppp,
sha256 `32daa9b3fb956f309146660d1710f7e1d90752ac424aee021ab2046934732a58`) se
renderiza con una sola orden `magick -annotate` por línea; la maqueta está en
`d4_texto.py`.

## 3. Aviso de reproducibilidad — MEDIDO

**El JPEG intermedio es reproducible bit a bit; el PDF no.** Dos ejecuciones
consecutivas dan el mismo `sha256` de `.jpg` y **distinto** `sha256` de `.pdf`:
ImageMagick estampa un `/CreationDate` en el PDF y **no honra `SOURCE_DATE_EPOCH`**
(comprobado: dos PDF con la misma variable de entorno dan hashes distintos).

Por eso la columna de comprobación fiable es la del JPEG:

| fichero | sha256 del `.jpg` (reproducible) |
|---|---|
| `escaneado_d4` | `4d1f4502db1ed605c632b51c962d692b582a4ae16c7a38f0372ec7e5d4000888` |
| `escaneado_d4a` | `8c95312ef9500dacfab7b562ffea86f075cd60199235fe73b5fdc6e45cb232aa` |
| `escaneado_d4b` | `2e2b87b3c3d94b9fcdee2651ee7e85da2978c698f64cc0bd5e9a40a2625e81cb` |
| `escaneado_d4c` | `2474f5a5d7692f9f88860a9d64fa2147c0955f1092b45743214a1583c676ed33` |
| `escaneado_d4e` | `cc00aaef2876194b8865ecde34edc53332695b1efb91ad31dc4852548872798a` |
| `escaneado_d4f` | `63165ffbfd93e4fe87882f951b51ba7141f4c4c81f3010557f136b25e7e620a0` |

El `sha256` de los PDF de la tabla 1 es el de **estos** ficheros concretos, los que
están en el repositorio, y sirve para detectar corrupción, no para verificar una
regeneración.

## 4. Cómo medir con ellos

- **Evaluador:** `bench/salidas-corpus-d4/ocr_eval_d4.py`, **no**
  `bench/scripts/ocr_eval.py`. El segundo normaliza quitando los acentos y sobre
  este corpus mide de menos: en las 28 celdas de la validación esconde hasta
  **6 caracteres de error** por documento.
- **ppp:** la regla R1 da 200 (nativos) para toda la familia salvo `d4f`, que da 240.
  **Ojo:** el techo ×1,4 de R1 **no es seguro aquí** — a 280 ppp PaddleOCR pasa de
  19,30 % a 36,24 % de CER. Ver `bench/corpus-d4.md` §7.
- Resultados completos: **`bench/corpus-d4.md`** y `bench/salidas-corpus-d4/tablas.md`.
