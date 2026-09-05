# Salidas del carril `cob/tiffgif`

Cobertura de los lectores de TIFF y GIF escritos a mano de `filex/verificador.py`.
Informe: `bench/cobertura-tiffgif.md`.

## Qué hay aquí

| Fichero | Bytes | Qué es |
|---|---|---|
| `cobertura.json` | 320 062 | salida de `coverage json` tras ejecutar **sólo** `pruebas.test_cob_tiffgif` |

**No hay binarios.** Los fixtures de TIFF y GIF **no se versionan como ficheros**:
se construyen con `struct` en `pruebas/fixtures_cob_tiffgif.py`, que es texto.
Los tres testigos externos de ImageMagick van dentro de ese módulo como literales
base64 con su `sha256` (ver abajo), porque son el único punto que un constructor
propio no puede cubrir.

**El `.coverage` NO se versiona**: es SQLite y ya está en `.gitignore:13`.

## Orden exacta que lo reproduce

Desde la raíz del repositorio, con el intérprete de Windows del proyecto
(`coverage` 7.16.0 vive fuera de los venvs — §1 prohíbe instalar en ellos):

```
PYTHONPATH=<RUTA-A>/pylibs \
  .venv-mcp-filex/Scripts/python.exe -m coverage run --source=filex \
  -m unittest pruebas.test_cob_tiffgif
PYTHONPATH=<RUTA-A>/pylibs \
  .venv-mcp-filex/Scripts/python.exe -m coverage json \
  -o bench/salidas-cobertura-tiffgif/cobertura.json
```

**No se ejecuta la suite completa a propósito.** Había cinco carriles más
trabajando en la máquina; seis suites a la vez fabrican la carga que pone roja
`test_cancelacion_procesos` sin que nadie toque el código (trampas 101 y 123).
Por eso el `percent_covered` global de este JSON (**9 %**) NO es el del proyecto:
es el de una sola tanda de un solo módulo, y **sólo sirve para el delta por
función**, que es lo que se publica.

## Huellas

El `sha256` del fichero entero **no es reproducible**: `meta.timestamp` cambia en
cada pasada. Lo que sí es estable es el contenido medido.

| Qué | Valor |
|---|---|
| `sha256` del fichero, esta pasada | `c939628835349ec6ddf2a770213c7989cb5fbb3b7692016c2dcce53cde9d2507` |
| `sha256(files + totals)` canónico, **reproducible** | `641fc5e602129f9c72f725a67c1974cfcbfd5883e8cf98cca27508600526f595` |
| `verificador.py` en esta tanda | 3 259 sentencias · 654 ejecutadas · 2 605 sin ejecutar |

Que la huella canónica sirve **está medido, no supuesto**: entre la penúltima
pasada y ésta se añadió una prueba entera (73 → 74). El `sha256` del fichero
cambió (`b7c90a26…` → `c9396288…`) por el `timestamp`; el canónico **no se
movió**, porque la prueba nueva no ejecuta ninguna línea que no se ejecutara ya.
Eso es exactamente lo que un fichero de resultados tiene que distinguir.

La huella reproducible se recalcula con:

```python
import hashlib, json
d = json.load(open("bench/salidas-cobertura-tiffgif/cobertura.json", encoding="utf-8"))
canon = json.dumps({"files": d["files"], "totals": d["totals"]},
                   sort_keys=True, separators=(",", ":"))
print(hashlib.sha256(canon.encode()).hexdigest())
```

## Los tres testigos externos, y cómo se reproducen

Viven empotrados en `pruebas/fixtures_cob_tiffgif.py` (`TESTIGOS`), en base64.
Se generaron una vez con **ImageMagick 7.1.2 Q16-HDRI** en un directorio
desechable. `+noise Gaussian` **exige `-seed`** o no se reproducen (trampa 22).

| Clave | Fichero | Bytes | `sha256` | Orden |
|---|---|---|---|---|
| `tiff_gris_plano` | `n32.tiff` | 618 | `473f9449ce33e6e5048c85adb451e3fa9242954b58a49ecbb36457ab5f8d979c` | `magick -size 32x14 -seed 7 xc:gray +noise Gaussian -depth 8 -alpha off -compress none n32.tiff` |
| `tiff_gris_lzw` | `l32.tiff` | 692 | `33af940e2383d3a1bfb250e7765a86b7107736bf61cf3ce358ae102fd5566d31` | `magick n32.tiff -depth 8 -compress LZW -define tiff:predictor=1 l32.tiff` |
| `gif_transparente` | `tr2.gif` | 49 | `a8aa1c21aa1a2a091e8882007828f00c09371f3cae4298b1aeb48cdc575a33f5` | `magick -size 8x4 xc:none -fill red -draw "rectangle 0,0 3,3" tr2.gif` |

El flujo LZW de `l32.tiff` son **510 B** y llega a códigos de **10 bits**, así que
ejercita el cambio de ancho — que es donde vive el dialecto y lo único que un
codificador propio no puede validar.

`pruebas/test_cob_tiffgif.py` **comprueba los tres `sha256` antes de usarlos**:
si alguien cambia un literal, la prueba lo dice en vez de medir otra cosa.
