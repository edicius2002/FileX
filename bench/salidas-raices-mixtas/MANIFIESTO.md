# MANIFIESTO — `bench/salidas-raices-mixtas/`

Salidas de **N35** (`bench/raices-mixtas.md`), worker5, ronda 16, 04/09/2026.
Rama `nucleo/raices-mixtas`.

**Todo lo de aquí es texto** —arneses `.py` y resultados `.json`—, así que se
versiona entero según §6 de `CLAUDE.md`: *«lo que sí se versiona: los `.md`,
los scripts, los `.json` de resultados, y los logs»*. **No hay un solo binario
ni ninguna salida grande que podar.**

## Cómo se reproduce todo

Intérprete: `.venv-mcp-filex\Scripts\python.exe` (**win32, 3.11.9**), que vive
en la **raíz del repositorio**, no en el *worktree*.

`sonda_superficies.py` **importa de `sonda_candidatos.py`**, así que las órdenes
se lanzan **desde este directorio**:

```sh
cd bench/salidas-raices-mixtas
PY=../../../.venv-mcp-filex/Scripts/python.exe      # ajusta la profundidad si no es un worktree

PYTHONIOENCODING=utf-8 $PY sonda_vocabulario.py     # -> vocabulario.json
PYTHONIOENCODING=utf-8 $PY sonda_mecanismo.py       # -> mecanismo.json
PYTHONIOENCODING=utf-8 $PY sonda_candidatos.py      # -> candidatos.json
PYTHONIOENCODING=utf-8 $PY sonda_unc.py             # -> unc.json
PYTHONIOENCODING=utf-8 $PY sonda_superficies.py     # -> superficies.json  (construye un FileX: tarda)
PYTHONIOENCODING=utf-8 $PY sonda_escritura.py       # -> escritura.json
PYTHONIOENCODING=utf-8 $PY sonda_coste.py           # -> coste.json        (renombrar a coste_tandaN.json)
```

`PYTHONIOENCODING=utf-8` no es decoración: la consola de esta máquina es
**cp1252** y las tablas llevan `→`, `·` y acentos. Sin él, `UnicodeEncodeError`.

### El par antes/después (§5 del informe)

Las dos corridas tienen que compartir la **misma base de rutas** o las celdas no
son comparables; por eso `--base` es un parámetro y no un `mkdtemp`:

```sh
cd bench/salidas-raices-mixtas
BASE="C:/Users/<usuario>/AppData/Local/Temp/filex-n35-fijo"

PYTHONIOENCODING=utf-8 $PY sonda_regresion.py --salida regresion_despues.json --base "$BASE"
cd ../.. && git checkout a4dc3f3 -- filex/confinamiento.py    # el commit ANTERIOR al arreglo
cd bench/salidas-raices-mixtas
PYTHONIOENCODING=utf-8 $PY sonda_regresion.py --salida regresion_antes.json  --base "$BASE"
cd ../.. && git checkout HEAD -- filex/confinamiento.py       # restaurar
cd bench/salidas-raices-mixtas
PYTHONIOENCODING=utf-8 $PY comparar.py                        # -> comparacion.json ; rc=0 si no hay fuga
```

> **`git stash push filex/confinamiento.py` NO sirve aquí y no avisa** (trampa
> propuesta 119): sobre un fichero ya commiteado no stashea nada, devuelve 0, y
> la sonda mide el código nuevo creyendo que mide el viejo. **Se revierte con
> `git checkout <commit> --`, y se comprueba con `inspect.getsource` que el
> código cargado es el que se cree.**

### Las pruebas y su discriminación (§7 del informe)

```sh
# con el arreglo: 12 passed
PYTHONIOENCODING=utf-8 $PY -m unittest pruebas.test_hito1.RaicesMixtasN35 \
                                       pruebas.test_hito4.RaicesMixtasPorMCP

# ¿discriminan? -> discriminacion_{antes,despues}.json
PYTHONIOENCODING=utf-8 $PY sonda_discriminacion.py --salida discriminacion_despues.json
# ... revertir filex/confinamiento.py al commit a4dc3f3 y volver a lanzarla:
PYTHONIOENCODING=utf-8 $PY sonda_discriminacion.py --salida discriminacion_antes.json
# ... y restaurarlo. Cada JSON registra QUE codigo midio (`codigo_medido`),
# asi que las dos corridas no se pueden confundir aunque se olvide revertir.
#   despues: 12 verdes    antes: 8 rojas / 4 verdes

# y que las 8 de N34 siguen siendo discriminantes: 4 de 8 caen
git checkout 82cf1f3 -- filex/mcp.py
PYTHONIOENCODING=utf-8 $PY -m unittest pruebas.test_hito4.RaicesEnConcurrencia \
                                       pruebas.test_hito4.RootsCacheYFallo
git checkout HEAD -- filex/mcp.py
```

### La suite

```sh
PYTHONIOENCODING=utf-8 $PY -m pytest pruebas -q -rs   # -> suite.txt
# 500 passed · 3 skipped · 0 failed · 179 subtests · 252,62 s
```

## Inventario

`sha256` y tamaño **de la corrida publicada**. Los `.json` traen dentro rutas
absolutas de directorios temporales y la mediana de tiempos, así que **una
reejecución NO reproduce el `sha256`**: reproduce los **veredictos**, que es lo
que sostiene el informe. Se dice aquí para que nadie lo tome por una
regresión.

<!-- INVENTARIO:INICIO -->

| fichero | bytes | sha256 | qué es |
|---|---|---|---|
| `sonda_vocabulario.py` | 3 508 | `cb2412ccb592925c3d2293af24bac3eee5437f4c8d27a8ada5107dc0aa271f67` | arnés: qué cuenta como raíz que no confina |
| `vocabulario.json` | 4 811 | `6aa59c5954629cf6f09ccebad55b6a5467067f5e37f41a8b870ca263c234754c` | 17 candidatas; raíz de unidad **y** de recurso UNC |
| `sonda_mecanismo.py` | 4 438 | `27bc76f766217d73b8a5bed6b9fa886ba3fe712b51654e1946b0d7c212d30023` | arnés: por qué `C:\` no abre nada |
| `mecanismo.json` | 1 526 | `cd58382eb21feb97bc2e94be24260867ca31eb5fabc4ab918bef332d0190ee62` | la barra doble, con control positivo y negativo |
| `sonda_candidatos.py` | 10 330 | `63f62c10611abc8f4367c287d30460a74ee8000da164ebbae6cd614931612aa0` | arnés: 8 filas × 4 candidatos (lectura) |
| `candidatos.json` | 27 565 | `3b1154c2df67f2c84d7bde303ad653879d66cd1c8ba2a1c50a016b8e5653017c` | la tabla de lectura: la meseta |
| `sonda_superficies.py` | 10 381 | `e5176935f1b4186a0a150930bba674e21b8b4c1c90d9bad4feeda992db9da2d9` | arnés: núcleo y MCP |
| `superficies.json` | 19 108 | `f09b724d30dbcbaa26058d3ecbf1264c7b6700c51c8e0af3b76510fa1d61d7cc` | 32 celdas: el eje que decide |
| `sonda_unc.py` | 2 919 | `da8a1e7fd03ce14fca8ca79ae6f4d2d23f7f899c513e443d844bc69761e9e0b9` | arnés: el viaje de una ruta por el cable MCP |
| `unc.json` | 2 371 | `72363cf6b1209f1bd5718ec82342022b33a900e7645f43d38aed7a9332f3c145` | el defecto de mi doble + el de `_uri_a_ruta` |
| `sonda_cli.py` | 4 189 | `698558a71ed1850d46897f313e6fe03768f46ed4e529d08fb645ce3164ff5212` | arnés: la CLI real, de extremo a extremo, como proceso |
| `cli.json` | 3 083 | `cdbe8fd7db56c43aefcb17e28807da6a1138753927c2625adaedd0b07455a916` | 3 rc distintos: convierte / deniega / no arranca |
| `sonda_escritura.py` | 5 894 | `d00fccbf148be5c31a29c09c189d1eecd3a0f065481934d20c5d0e041d897ec8` | arnés: B1 contra B2, con el control de hoy |
| `escritura.json` | 6 451 | `a97562bc18b47c209d05f4076a8e8da855447f1963ac01045f4650d0050228b0` | 6 filas × 3 candidatos + control |
| `sonda_bordes.py` | 3 569 | `555948beca06ef13b3755ebb0741e6cc9f61bb96526a1444428a6782e6c9a267` | arnés: 9 formas raras de raíz; rc=1 si alguna concede |
| `bordes.json` | 3 624 | `174e410c7a4ac681930225c63729c3b41618be0051b9b72d3b8859ba3524fa62` | 0 accesos indebidos sobre 9 formas |
| `sonda_regresion.py` | 5 158 | `32d4f451e96a87c437f9ecc1d6af3c6b0e2807e1a620ceef8a070a3ecf1b721f` | arnés del par antes/después, clase REAL |
| `regresion_antes.json` | 6 917 | `f5b07b46252aae0da0648aaca817de4d95dc5c134b164a07d758173a0397a176` | 11 filas sobre el código de antes |
| `regresion_despues.json` | 7 517 | `43f39fe474bd12ced5381e70945758aab3230d0a823d1e4ca3a40b7262c3c5d8` | 11 filas sobre el código de después |
| `comparar.py` | 3 772 | `384028dd7e57f569be092fa32164db51d41bf22afd9742c6c9d537f60914417a` | el diff celda a celda; `rc=0` si no hay fuga |
| `comparacion.json` | 3 661 | `21a3e906f4f8147c003b315bc9bfecebc538108dfec449da2faf9f5da2f24d2a` | **7 SIN_CAMBIO · 4 RECUPERA · 0 fugas** |
| `sonda_coste.py` | 8 990 | `cbcea6a4168eb9c48b590472223f0f574e3084cdc591d954c6dad3beea2a9c84` | arnés de coste: las dos versiones intercaladas |
| `coste_tanda1.json` | 3 362 | `2a30bd6d3143d16f406e2aefb70a27650f3fdb6d14f18366e33bcdccd66c111a` | tanda 1, n=9 × 2000 |
| `coste_tanda2.json` | 3 362 | `83a08614a93b35a1d80adc44c2ad89b0d01d8b7cb3effe2f464411ec47da9366` | tanda 2, n=9 × 2000 |
| `coste_tanda3.json` | 3 361 | `c5fe557b1009a8f51b5393103c0278a7fe401d370de6cae15bc3194d8d1d891d` | tanda 3, n=9 × 2000 |
| `sonda_discriminacion.py` | 4 160 | `02849ce0a787bec7d8106acf8cfa485b849bfe05b7843ad0bbb672ff96537072` | arnés: ¿discriminan las pruebas? por NOMBRE de test |
| `discriminacion_antes.json` | 2 346 | `f5145917bafb3d904d3de8e6e0150311ea3c2fe16e41eb7759080c7b8e2b006a` | 8 rojas / 4 verdes contra el código de antes |
| `discriminacion_despues.json` | 2 311 | `3ea1db5696cdc272f314c0aff7d874a6ac6f5d84f44e4a9ea1ec8ef079f6524c` | 12 verdes con el arreglo |
| `suite.txt` | 1 601 | `511df4c1fb12dbe02ef4ff4c2e6a84668eaba308ae0dff68354aca529e23db57` | la suite completa |
| `hacer_inventario.py` | 3 591 | `831aab412fd629d923e05573625d82910a210e1068c488cc0f0b71062663995a` | este generador (se incluye para no mentir por omisión) |

<!-- INVENTARIO:FIN -->

> **La tabla la genera `hacer_inventario.py`, no la escribo a mano.** La
> primera version de este manifiesto llevaba hashes de relleno, y un hash
> inventado es peor que ninguno: parece verificable y no lo es. Se regenera
> con `python hacer_inventario.py`, y el script **se niega a inventar** la
> fila de un fichero que no encuentre: la lista y avisa.
>
> Los `sha256` son de los ficheros **en disco**. La normalizacion de finales
> de linea al registrarlos hace que el del blob no coincida con el del arbol
> de trabajo en Windows; el que vale para verificar es el del fichero tal
> como queda tras extraerlo en esta plataforma.


## Lo que NO hay aquí, y por qué

- **Ningún binario.** Los cuatro «objetivos» que las sondas leen son ficheros de
  unos pocos bytes creados en un directorio temporal en cada corrida, más dos
  que ya existen en la máquina (`corpus/imagen/tipico.png` y
  `C:\Windows\win.ini`). Ninguno se copia aquí.
- **Los directorios temporales `filex-n35-*`** quedan en `%TEMP%` a propósito
  para poder inspeccionarlos, y son de unos pocos KB. No son huérfanos de R18:
  los crea el arnés, no una conversión.
