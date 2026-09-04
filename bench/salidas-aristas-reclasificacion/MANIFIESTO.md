# `bench/salidas-aristas-reclasificacion/` — C43, worker9, ronda 19

Salidas de `bench/aristas-reclasificacion.md`: reclasificación de los **445**
`no_materializable` de `bench/salidas-aristas/semi_entrada.json`.

**Este directorio no escribe nada en `bench/salidas-aristas/`**, que es la salida medida
de otro agente (`CLAUDE.md` §1: un fichero de salida por agente). Todo lo de aquí es
derivado y de sólo lectura sobre aquello.

---

## 1. Cómo se reproduce, en orden

```sh
# (0) los siete listados de metadatos -- instantáneos, sólo lectura, sin conversión
magick -list format                > crudo/im-format.txt
magick -list delegate              > crudo/im-delegate.txt
ffmpeg -hide_banner -protocols     > crudo/ff-protocols.txt
ffmpeg -hide_banner -devices       > crudo/ff-devices.txt
ffmpeg -hide_banner -demuxers      > crudo/ff-demuxers.txt
ffmpeg -hide_banner -muxers        > crudo/ff-muxers.txt
ffmpeg -hide_banner -formats       > crudo/ff-formats.txt

# (1) cruce de los 445 contra esos listados      -> cruce.json
python bench/salidas-aristas-reclasificacion/reclasifica.py

# (2) detalle de los cubos y control contra censo.json
python bench/salidas-aristas-reclasificacion/buckets.py

# (3) por qué 73 tokens que ffmpeg declara muxer salieron no_materializables
python bench/salidas-aristas-reclasificacion/gate.py

# (4) reconstruye el grafo A (138 501) SIN ejecutar motores -> aristas_A.json
python bench/salidas-aristas-reclasificacion/rehace_aristas.py

# (5) clasificación + recuento del 54,78 %       -> clasificacion.json, recuento.json
python bench/salidas-aristas-reclasificacion/recuento.py

# (6) cuántas aristas cuelgan de cada clase
python bench/salidas-aristas-reclasificacion/premio.py
```

El paso **(4) es obligatorio antes del (5) y del (6)**: los dos leen `aristas_A.json`.

---

## 2. Lo que se borró al terminar, y qué lo regenera

| Fichero | Bytes | Orden que lo reproduce |
|---|---:|---|
| `aristas_A.json` | 2 914 041 | `python bench/salidas-aristas-reclasificacion/rehace_aristas.py` |

Es el producto cartesiano de los conjuntos declarados, texto regenerable en **~2 s y sin
tocar un solo motor** (regla §6). No se ha podado nada más.

> **Por qué existe `rehace_aristas.py` en vez de usar `bench/salidas-aristas/aristas.json`:**
> aquel está podado con su orden (`_censo.py`) y esa orden relanza **~590 sondas
> `ffmpeg -h demuxer=…/muxer=…`**, que es justo el gasto de máquina que esta ronda tenía
> prohibido. El grafo A es un producto cartesiano de conjuntos **declarados**, así que se
> reconstruye desde ficheros (`ConvertX/src/converters/ffmpeg.ts`), desde
> `crudo/im-format.txt` y desde los conjuntos que `censo.json` ya publica
> (`ghostscript.salidas_mapeadas`, `gotenberg_lo_ext`). Reproduce **138 501 exactas**.

---

## 3. Inventario

| Fichero | Bytes | `sha256` |
|---|---:|---|
| `_hashes.py` | 468 | `0e40eb60cbfc246c…` |
| `buckets.py` | 1496 | `094d28e9c8ded3d4…` |
| `clasificacion.json` | 81886 | `d5a3d32fc1ef9da1…` |
| `cruce.json` | 110834 | `ede39a14c042b029…` |
| `gate.py` | 1744 | `379cf380032b6537…` |
| `log-buckets.txt` | 1193 | `92577a2c61d89e89…` |
| `log-gate.txt` | 517 | `e87df22dbe7857b9…` |
| `log-premio.txt` | 1314 | `ed6036f37ef12b29…` |
| `log-reclasifica.txt` | 1962 | `8c1d3b85aeed5e62…` |
| `log-recuento.txt` | 1311 | `20af045fa90f0130…` |
| `log-rehace.txt` | 230 | `b0291c44628d7f2f…` |
| `premio.py` | 3003 | `319337f9408f6b6d…` |
| `reclasifica.py` | 5993 | `89c0e371a3464017…` |
| `recuento.json` | 702 | `36edda92a4812d06…` |
| `recuento.py` | 8814 | `25f20bdc2f5d5bcb…` |
| `rehace_aristas.py` | 4275 | `83172558ed9e65ca…` |
| `crudo/ff-demuxers.txt` | 15360 | `d7d709ffdf153168…` |
| `crudo/ff-devices.txt` | 299 | `8eca428ca3314c95…` |
| `crudo/ff-formats.txt` | 17672 | `fbdbc3f312f3fb91…` |
| `crudo/ff-muxers.txt` | 8057 | `d6fe29c3f60aff12…` |
| `crudo/ff-protocols.txt` | 705 | `6618f71b95e6f7f9…` |
| `crudo/im-delegate.txt` | 3086 | `e0e75af15089b102…` |
| `crudo/im-format.txt` | 18469 | `e0043b8d2ecdd390…` |

Las filas las emite `python bench/salidas-aristas-reclasificacion/_hashes.py`, que se
ejecuta a mano y se pega aquí. Los hashes de esta tabla son los de **antes** de podar
`aristas_A.json`, que ya no está en el inventario.

---

## 4. Controles que tienen que salir verdes

Están en los logs y son la condición para creerse el resto:

| Control | Dónde | Qué exige |
|---|---|---|
| Sonda de ImageMagick reproduce la del censo | `log-reclasifica.txt` | `246` formatos, `difieren NINGUNA` |
| Control positivo de sonda (trampa 66) | `log-reclasifica.txt` | `png` ≠ `xc` en módulo, modo y descripción |
| Grafo A reconstruido | `log-rehace.txt` | `138501`, `COINCIDE` |
| Agregación reproducida (trampa 58) | `log-recuento.txt` | `138501 / 40252 / 22235 / 75874 / 140`, `COINCIDE` |

---

## 5. Máquina consumida

Siete listados de metadatos (`magick -list ×2`, `ffmpeg -hide_banner ×5`), instantáneos y
de sólo lectura, **una vez cada uno**. Ninguna conversión, ningún contenedor, ninguna
suite, ninguna GPU, ningún fichero del `corpus/` leído. El resto es Python sobre JSON y
texto ya en disco.
