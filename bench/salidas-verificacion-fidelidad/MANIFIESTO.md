# MANIFIESTO — `bench/salidas-verificacion-fidelidad/`

Informe: **`bench/verificador-fidelidad.md`** (entregables declarados en su
línea 5 y §"Todo en `bench/salidas-verificacion-fidelidad/`" en la línea 483).

**MEDIDO el 01/09/2026** (lectura de `medir_fid.py`, no una suposición): el
script es un único banco con seis subcomandos (`alfa`, `contrato`, `reglas`,
`fidelidad`, `texto`, `fallos`, ver su docstring, líneas 5-11); cada uno
escribe su propio `<subcomando>.json` con `guardar()` (línea 77-81, solo
JSON) y el `.txt` homónimo es la captura del `stdout` de esa misma
invocación (el script imprime cada fila con `print()` según corre). No usa
GPU. Importa `verificador` desde `bench/scripts/verificador.py` (**no**
`filex/verificador.py`) y `trabajos` desde `bench/salidas-verificacion/`
(línea 22-27), y varios subcomandos leen `corpus/` (Git LFS) y
`bench/salidas-referencia/` (rutas remapeadas por nombre base, trampa 89).

## Fuente

| Fichero | Tamaño | SHA-256 |
|---|---:|---|
| `medir_fid.py` | 19 592 B | `a60eaa20fb38cd333cbf9291314a266f9dd5f96c3c7a7acf69f6f15a92c9ca35` |

## Salidas — orden exacta por subcomando

| Fichero (.json + .txt) | Tamaño JSON | SHA-256 JSON | Tamaño TXT | SHA-256 TXT | Orden |
|---|---:|---|---:|---|---|
| `alfa` | 6 485 B | `aa9d009130deed5a7491bcaec7c0dd5445345188cef47667814df361c63de03e` | 1 480 B | `05ff3d3ee789331b7cf0a5e14c7f49e051d6fb55bc4e9edf82fd4f044d457491` | `python bench/salidas-verificacion-fidelidad/medir_fid.py alfa > bench/salidas-verificacion-fidelidad/alfa.txt` (el `.json` lo escribe el propio script) |
| `contrato` | 68 381 B | `7fada118123e49224fce2282fa561a4fb7349a238257dec885950a8470518b28` | 495 B | `fa12468046deced4a90474df18982d0592fdaf8033ed8a66f6732a3c325c9deb` | `python bench/salidas-verificacion-fidelidad/medir_fid.py contrato > bench/salidas-verificacion-fidelidad/contrato.txt` |
| `reglas` | 3 432 B | `fda15b946f8155c18cef1b2a53aff8243876887aeab619140079b140ef1d2a8d` | 1 567 B | `2bfabfc543121bb4287f3fa97896d845185f21a131b2a960f642ed0339713e41` | `python bench/salidas-verificacion-fidelidad/medir_fid.py reglas > bench/salidas-verificacion-fidelidad/reglas.txt` (medianas n≥9) |
| `fidelidad` | 25 477 B | `a5e17f304bf602d57729f406d936bc2b16c74819663940ba836745258410e18e` | 4 224 B | `cd0bf52d74cd236183ee6026a734bf654109dd4e5bb3321a303e022ac72ed0d0` | `python bench/salidas-verificacion-fidelidad/medir_fid.py fidelidad > bench/salidas-verificacion-fidelidad/fidelidad.txt` |
| `texto` | 2 246 B | `7b376f63643e7a305508fb865ac11140b8380a79eb658d174cb7177bd48e7acc` | 1 113 B | `861f52c7b847dc3c3fa3a71dcb048dfa4e4497ba31e35fd3dc2c6e0f029a517d` | `python bench/salidas-verificacion-fidelidad/medir_fid.py texto > bench/salidas-verificacion-fidelidad/texto.txt` |
| `fallos` | 4 993 B | `a58d50ff42a6bb98187e27fbb7eec50759611af308d6e4400015ef269c817572` | 1 059 B | `bfa3a10484b939fd4204fc14a6eeea7132ff7cc2674c198034438a26ec0b99d2` | `python bench/salidas-verificacion-fidelidad/medir_fid.py fallos > bench/salidas-verificacion-fidelidad/fallos.txt` |

## Salvedad de reproducibilidad, declarada

- `reglas.json`/`reglas.txt` traen medianas de tiempo (n≥9): **no reproducibles
  al milisegundo** entre máquinas o tandas (regla del proyecto: las cifras
  absolutas de tandas distintas no son comparables), solo el orden de
  magnitud y el ranking entre reglas.
- Depende de `bench/scripts/verificador.py` (viejo, no `filex/verificador.py`)
  y de `bench/salidas-verificacion/trabajos.py`: si cualquiera de los dos
  cambia de comportamiento, la salida deja de reproducirse byte a byte aunque
  el comando sea el mismo (huella de código, trampa 32).
- Este agente (worker2, WSL2) verificó los hashes/tamaños sobre el árbol
  actual pero no reejecutó el banco completo (requiere `corpus/` vía Git LFS
  y las 53 salidas del patrón oro).
