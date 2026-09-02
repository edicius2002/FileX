# MANIFIESTO — `bench/salidas-acuerdo-y-cruce/`

Ronda 7, worker2. Datos crudos de `bench/acuerdo-y-cruce.md`: `C20` (§1), `C23` (§2) y el
resondeo de los cinco motores tras `C31` (§3). Regla §6: nombre, tamaño, sha256, orden exacta.
Los rásteres PNG (grandes, regenerables) se han borrado; queda su orden. Las salidas binarias
de los motores documentales/ImageMagick/ffmpeg del resondeo **no se versionan aquí** — viven,
igual que antes de esta ronda, borradas, con la orden en `bench/salidas-sondeo-{im,ff,doc}/`.

## 1. `C20` — el acuerdo `spa`/`eng` fuera de Ghostscript

`_c20_acuerdo.py` rasteriza cada documento a **ppp nativos** (`magick -density N -units
PixelsPerInch`) y corre Tesseract 5.5.0 **dos veces** dentro de `filex-c13` (`--psm 3`, `-l spa`
y `-l eng`), vía `docker run --rm --init --entrypoint timeout --workdir /work ...` — el `--init`
evita que `timeout` quede de PID 1 (CLAUDE.md, hallazgo del 28/08); el `--workdir` + rutas
relativas evita un fallo de `tesseract` con rutas absolutas que no se investigó más allá de dos
intentos.

Orden: `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-acuerdo-y-cruce/_c20_acuerdo.py`
(Docker levantado, imagen `filex-c13`).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_c20_acuerdo.py` | 6621 | `2dc802ad…00ba` |
| `acuerdo_c20.json` | resultado agregado | `c93c0ca9…3296` |
| `escaneado_d1_150ppp_spa.txt` / `_eng.txt` | 84 / 84 | `f5593ee4…913a` (los dos idénticos) |
| `patologico_escaneado_200ppp_spa.txt` / `_eng.txt` | 83 / 83 | `b7c05f48…6cf9` (idénticos) |
| `escaneado_d2_100ppp_spa.txt` | 89 | `515748f3…ad560` |
| `escaneado_d2_100ppp_eng.txt` | 88 | `7b042398…06a25` |
| `escaneado_d3_100ppp_spa.txt` / `_eng.txt` | **0 / 0** | `e3b0c442…852855` (sha del vacío — la trampa de silencio, §1.2 del informe) |
| `escaneado_d4a_200ppp_spa.txt` | 615 | `26503416…d91` |
| `escaneado_d4a_200ppp_eng.txt` | 621 | `95f5ff17…ec6` |
| `escaneado_d4c_200ppp_spa.txt` | 611 | `92de9e84…0a2` |
| `escaneado_d4c_200ppp_eng.txt` | 615 | `b083d56c…91` |
| `escaneado_d4_200ppp_spa.txt` | 358 | `605778d4…18b` |
| `escaneado_d4_200ppp_eng.txt` | 347 | `e7fb155d…5c5` |
| `escaneado_d4e_200ppp_spa.txt` / `_eng.txt` | **0 / 0** | `e3b0c442…852855` (vacío otra vez, misma trampa) |
| `psm6_d3_spa.txt` | 151 | `dd9215e6…58a` — control: `--psm 6` sobre `d3` NO da silencio, da alucinación |
| `psm11_d3_spa.txt` | 249 | `1f996e0b…ffd` — control: `--psm 11`, igual |

Rásteres (borrados, se reproducen así): `magick -density <ppp nativos de cada documento,
tabla en el informe §1> corpus/pdf/<doc>.pdf[0] -units PixelsPerInch -flatten <doc>_<ppp>ppp.png`.

## 2. `C23` — la curva de once puntos del cruce en proceso/`magick`

`_c23_cruce.py` fabrica PNG sintéticos (`magick -size WxH -seed 20260903 plasma:fractal +noise
Gaussian -depth 8`, TrueColor, sin entrelazar) en once tamaños (proporción 2:1, 0,0098 a 5,12
Mpx) y mide, mediana de n=9 con calentamiento: `filex.verificador.png_tinta_cajas()` en proceso
contra `magick -crop ... -format "%[fx:standard_deviation]" info:` por subproceso, sobre una
caja PROPORCIONAL (30–70 % del ancho, 46–54 % del alto).

Orden: `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-acuerdo-y-cruce/_c23_cruce.py`

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_c23_cruce.py` | 4621 | `2f46aae7…a2` |
| `cruce_c23.json` | resultado agregado, 11 filas | `5d1949fb…3d3` |

Los once PNG sintéticos (`sint_<ancho>x<alto>.png`, borrados) se reproducen con la orden citada
arriba, con el `-seed` fijo declarado — determinista (trampa 22 de `CLAUDE.md`: sin `-seed`, el
ruido gaussiano no sería reproducible).

## 3. El resondeo de los cinco motores tras `C31` (ronda 6)

**Por qué:** `C31` (ronda 6) tocó `FIRMAS` (discriminante TGA/CUR) y `_datos()` (RAM) dentro del
cierre de llamadas de `verificar()`, así que el componente `contrato` de la huella de los cinco
`filex/sondeo/*.json` caducó — confirmado con `bench/salidas-huella/resellar.py --comprobar`
(las cinco huellas dan `coincide_con_algoritmo_viejo=False`: no es un cambio de algoritmo, hacía
falta RESONDEAR). Ver `bench/acuerdo-y-cruce.md` §3 para el resultado (**0 diferencias de
veredicto REAL/NOMINAL en las 172 aristas**) y la interacción con `C43` (granularidad del campo
`interprete`, §3.3 del informe).

### 3.1 ImageMagick — 62 aristas (`bench/salidas-sondeo-im/`, arnés no tocado, solo copiado)

Semillas reproducidas al byte (`sha256` verificado contra `bench/salidas-sondeo-im/MANIFIESTO.md`,
salvo `D.png`: mismo tamaño, `sha256` distinto — metadato de PNG con marca de tiempo, no
contenido, trampa 22). Orden, con `$S`/`$O` desechables fuera del repositorio:

```
python bench/salidas-acuerdo-y-cruce/_sonda_im_r7.py   $S $O bench/salidas-acuerdo-y-cruce/barrido_im.json
python bench/salidas-acuerdo-y-cruce/_ico256_r7.py     $S $O bench/salidas-acuerdo-y-cruce/ico256.json
python bench/salidas-acuerdo-y-cruce/_hacer_json_im_r7.py \
       bench/salidas-acuerdo-y-cruce/barrido_im.json bench/salidas-acuerdo-y-cruce/ico256.json \
       bench/salidas-acuerdo-y-cruce/imagemagick_nuevo.json
python bench/salidas-acuerdo-y-cruce/_sellar_r7.py imagemagick \
       bench/salidas-acuerdo-y-cruce/imagemagick_nuevo.json bench/acuerdo-y-cruce.md
```

`_sonda_im_r7.py`/`_hacer_json_im_r7.py` son **copias literales** de
`bench/salidas-sondeo-im/{sonda_im.py,hacer_json.py}` con solo `RAIZ` editado a este *worktree*
(regla de "un fichero de salida por agente" — el arnés ajeno no se toca). `_ico256_r7.py` es
nuevo: reproduce el bloque de remedida de `bench/sondeo-imagemagick.md` §3.2, que no había
quedado guardado como script.

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_sonda_im_r7.py` | 8508 (con RAIZ editado) | `b66dc65a…225d` |
| `_hacer_json_im_r7.py` | 3879 (con RAIZ editado) | `aadd4de5…9b81` |
| `_ico256_r7.py` | 1876 | `d752b92e…0047` |
| `barrido_im.json` | 124 filas | `0d43904f…4cb` |
| `ico256.json` | 7 filas | `41b56732…3b7` |
| `imagemagick_nuevo.json` | 62 aristas, 62 real / 0 nominal | `ec4723cd…0b1` |

### 3.2 ffmpeg — 70 aristas (`bench/salidas-sondeo-ff/`, arnés no tocado, solo copiado)

```
python bench/salidas-acuerdo-y-cruce/_preparar_fuentes_r7.py $FD/fuentes
python bench/salidas-acuerdo-y-cruce/_sondear_ff_r7.py       $FD 3
python bench/salidas-acuerdo-y-cruce/_escribir_json_ff_r7.py $FD
python bench/salidas-acuerdo-y-cruce/_sellar_r7.py ffmpeg filex/sondeo/ffmpeg.json bench/acuerdo-y-cruce.md
```

`_escribir_json_ff_r7.py` escribe **directamente** en `filex/sondeo/ffmpeg.json` (así lo hace su
original, `DESTINO` autoderivado de `RAIZ`): es el propio destino, no un intermedio. 68 real, 2
nominal (`mkv>m4a`, `mov>m4a` — mismo motivo que ya declaraba el fichero: tolerancia de duración
del contrato, sin cambio).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_preparar_fuentes_r7.py` | copia literal | `58819ce4…6b0` |
| `_sondear_ff_r7.py` | copia literal | `207e476d…215` |
| `_escribir_json_ff_r7.py` | copia literal | `a6647885…298` |

`resultados.json` (97 649 B, el crudo del barrido) se generó en `$FD` (desechable fuera del
repositorio) y no se copió aquí — está resumido en el propio `bench/acuerdo-y-cruce.md` §3 y
reproducible con la orden de arriba.

### 3.3 Los tres motores de contenedor — 40 aristas (`bench/salidas-sondeo-doc/`, EN SITIO)

**Aquí no se copió nada**: `bench/salidas-sondeo-doc/_*.py` autoderivan su `RAIZ` desde su
propia ubicación (3 niveles arriba), así que ejecutarlos en su directorio original ya apunta a
este *worktree* — es la ubicación canónica que su propio `MANIFIESTO.md` documenta como
reproducible, y `C31`/`C43` no tocan ninguna lógica de ese directorio. Orden, la que ya
documentaba `bench/salidas-sondeo-doc/MANIFIESTO.md` (Docker levantado, imagen `filex-c13`):

```
python bench/salidas-sondeo-doc/_sonda23.py
python bench/salidas-sondeo-doc/_sonda_p5.py
python bench/salidas-sondeo-doc/_d2.py
python bench/salidas-sondeo-doc/_repro.py
python bench/salidas-sondeo-doc/_tabla_sondeo.py
python bench/salidas-acuerdo-y-cruce/_sellar_r7.py doc_calibre     filex/sondeo/doc_calibre.json     bench/acuerdo-y-cruce.md
python bench/salidas-acuerdo-y-cruce/_sellar_r7.py doc_libreoffice filex/sondeo/doc_libreoffice.json bench/acuerdo-y-cruce.md
python bench/salidas-acuerdo-y-cruce/_sellar_r7.py doc_pandoc      filex/sondeo/doc_pandoc.json      bench/acuerdo-y-cruce.md
```

Las salidas binarias (`out/`, `out-p5/`, `out-d2/`, `out-repro/`, 313+277+144+300 KB) y las
cuatro semillas fabricadas (`entradas/entrada.{mobi,azw3,pptx,xlsx}`) **se borraron al
terminar** — mismo criterio que ya aplicaba el directorio antes de esta ronda. `d2.json`,
`sonda-p5.json`, `sonda23.json` y `repro.json` quedaron **actualizados en sitio** (misma regla
que aplica a `filex/sondeo/doc_*.json`: es infraestructura compartida diseñada para
re-ejecutarse, no un artefacto nuevo por agente).

`doc_{calibre,libreoffice,pandoc}_crudo.json` son la **copia previa al sellado** de
`filex/sondeo/doc_*.json` (antes de que `_sellar_r7.py` añadiera `huella`/`interprete`) — se
conservan aquí porque `_tabla_sondeo.py` escribe directo sobre el destino y sin esta copia no
quedaría rastro del crudo.

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `doc_calibre_crudo.json` | 8 aristas, 8 real | `e6fee421…4ac` |
| `doc_libreoffice_crudo.json` | 16 aristas, 16 real | `e4fb9067…094` |
| `doc_pandoc_crudo.json` | 16 aristas, 16 real | `d8539c59…8e5` |

### 3.4 El sellado — `_sellar_r7.py`

Añade `huella` (`filex.huella.de_motor_por_nombre`, calculada AHORA) e `interprete`
(`filex.huella.interprete_actual()`, la granularidad mayor.menor de `C43` en esta ronda) a cada
JSON crudo, con `nota_huella` declarando explícitamente **RESONDEO, no resellado por
algoritmo** (trampa 44: la nota es parte del contrato y tiene que decir la verdad).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_sellar_r7.py` | 1912 | `affb8e48…00c` |
