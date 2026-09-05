# MANIFIESTO — `bench/salidas-cobertura-png/`

Salidas del carril `cob/png` (rama `cob/png`). Informe: `bench/cobertura-png.md`.

**Entorno de todas las medidas de aquí** (trampas 94 y 101: el recuento de una
suite necesita cuatro declaraciones):

| Qué | Valor |
|---|---|
| Intérprete | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` — CPython **3.11.9**, `win32` |
| `coverage` | 7.16.0, cargado con `PYTHONPATH=<scratchpad>\pylibs` (regla §1: no se instala en ningún `.venv-*`) |
| Módulo medido | **sólo** `pruebas.test_cob_png` — la suite completa NO se lanzó (había cinco workers más en la máquina; trampas 101 y 123) |
| Qué quedó fuera | nada, con `magick` presente: **54 pruebas, 0 saltadas, 0 fallos**. Sin `magick`, se salta la clase `Vp8lDeVerdad` (1 prueba) |
| Estado de la máquina | compartida. **Por eso no se publica un solo tiempo**: todos los veredictos son deterministas (líneas, `md5`, `rc`) |
| `sha256` de `filex/verificador.py` | `fc0385500de90f1f…` (declarado entero en `discriminacion.json`); el fichero **no se modificó**: `git status` limpio al terminar |

`filex/` no se tocó. Los únicos ficheros del carril fuera de este directorio son
`pruebas/test_cob_png.py`, `pruebas/fixtures_cob_png.py` y `bench/cobertura-png.md`.

---

## Ficheros

| Fichero | Qué es | Orden que lo reproduce |
|---|---|---|
| `base-verificador.json` | La cobertura **base** del maestro (suite completa, 517 pruebas) restringida a `filex/verificador.py`, más el total de `filex/`. Congelada aquí a propósito: la medida original vivía en un scratchpad de sesión y se pierde (trampa 95) | `python bench/salidas-cobertura-png/_congela_base.py` — **ya no se puede volver a ejecutar**: su origen era el scratchpad. Este fichero es el registro |
| `cobertura.json` | `coverage json` de `filex/verificador.py` bajo `pruebas.test_cob_png` completo | `bash bench/salidas-cobertura-png/medir.sh` |
| `cobertura-sin-magick.json` | Lo mismo **sin** la clase `Vp8lDeVerdad` (el suelo de un entorno sin ImageMagick) | `bash bench/salidas-cobertura-png/medir_sin_magick.sh` |
| `ganancia.json` | El titular: líneas ganadas por función | `python bench/salidas-cobertura-png/compara.py` |
| `suelo.json` | Ganancia con y sin `magick`, y las líneas que sólo se alcanzan con él | `python bench/salidas-cobertura-png/_suelo.py` |
| `discriminacion.json` | **El control que hace que esto valga algo**: 29 mutaciones de una línea de `filex/verificador.py`, con qué pruebas se pusieron rojas en cada una | `python bench/salidas-cobertura-png/discriminacion.py` |
| `barrido.json` | 212 PNG generados, sujeto contra oráculo. Es donde salió el defecto D1 | `python bench/salidas-cobertura-png/_barrido.py` |
| `vp8l.json` | 4 000 vecindades × 14 predictores VP8L, sujeto contra oráculo de libwebp. Es donde salió D2 | `python bench/salidas-cobertura-png/_vp8l.py` |
| `webp_ida_vuelta.json` | PNG → WebP sin pérdida con `magick` → `alfa_minimo`, 8 imágenes | `python bench/salidas-cobertura-png/_webp_ida_vuelta.py` |
| `webp_modos.json`, `webp_modos2.json` | Censo de qué predictores VP8L usa de verdad `magick`, con un espía sobre `_predice` | `python bench/salidas-cobertura-png/_webp_modos.py`, `..._modos2.py` |

### Sondas sin fichero de salida (imprimen y ya)

| Script | Qué contesta |
|---|---|
| `_humo.py` | Que el CONSTRUCTOR de fixtures escribe PNG válidos, juzgado por un tercero (`magick identify`): 44 de 44, y 0 discrepancias contra el oráculo |
| `_paeth_simetria.py` | Que `_paeth(a,b,c) == _paeth(b,a,c)` en los **8 355 840** tercetos con `a<b` — la prueba de que la mutación M04 es un mutante EQUIVALENTE y no un hueco |
| `_zlib_flush.py` | Que `zlib.decompressobj().flush()` **no lanza** `zlib.error` con este build sobre ningún flujo truncado — la razón de que las 2 líneas del encargo que quedan sean código muerto |
| `_pendientes.py` | Qué líneas del encargo siguen sin ejecutar, con su texto |
| `_congela_base.py` | Escribió `base-verificador.json` |

**Los PNG y los WebP no se versionan y no hay que hacerlo**: no existen como
ficheros. `pruebas/fixtures_cob_png.py` los construye byte a byte con `zlib` y
`struct` de la biblioteca estándar. Meterlos en `corpus/` habría sido Git LFS
(cuota de 1 GB/mes contra 254 MB de corpus, trampa 103) y la trampa 34 en cada
*worktree* nuevo.

## Cómo ejecutar el módulo suelto

```
PYTHONPATH= D:/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe \
    -m unittest pruebas.test_cob_png
```

`magick` en el PATH ⇒ 54 pruebas. Sin él, 53 y una saltada con motivo declarado.
