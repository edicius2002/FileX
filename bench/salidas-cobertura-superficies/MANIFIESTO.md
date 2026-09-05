# Salidas del carril `cob/superficies`

Cobertura de código de las cuatro superficies de usuario (`filex/cli.py`,
`filex/__main__.py`, `filex/api.py`, `filex/watcher.py`). Informe:
`bench/cobertura-superficies.md`.

## Entorno declarado (trampas 94, 101, 105)

| Qué | Valor |
|---|---|
| Intérprete | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` — CPython **3.11.9**, `win32` |
| `coverage` | **7.16.0**, fuera de los venvs, en el *scratchpad* de la sesión (§1: no se instala en ningún `.venv-*`) |
| Motores presentes | `imagemagick`, `ffmpeg`, `ghostscript`, `doc_calibre`, `doc_libreoffice`, `doc_pandoc` — **0 ausentes** |
| Corpus | materializado (`corpus/imagen/tipico.png` = 42 855 B, no los 130 del puntero LFS) |
| Docker | **no hace falta**: ninguna de las 75 pruebas de este módulo lo usa |
| Estado de la máquina | **cinco agentes más trabajando**. Por eso **no se publica ni un tiempo** y todos los veredictos son deterministas (§3) |

## Ficheros

| Fichero | `sha256` | bytes |
|---|---|---|
| `cobertura.json` | `dcfb8efb713ee8e6f8342e8be0144386c3e5bbbe51b9206c4b7157bf7946fa94` | 196 418 |
| `delta.json` | `0de6d4b8a13948aa51c43deffb6ee04d6795598897f53fc2220ddf4f88292a56` | 10 731 |
| `discriminacion.json` | `ab1252b04ae0ede491c7bd616724fc9b8e75dd1322200c81aae154ffbb688682` | 29 005 |

El `.coverage-cob-ramas` **no se versiona**: es SQLite y es regenerable.

**`cobertura.json` se mide con `--branch`**, igual que la base del maestro. No
es un detalle: el porcentaje que publica `coverage` con ramas activadas es el
**combinado** de sentencias y ramas, y compararlo contra un porcentaje de
sentencias sería mezclar dos métricas (trampa 55). `cli.py` tenía el 42,6 % de
sentencias y el 15,4 % de ramas; el **35,2 %** del que parte el informe es la
mezcla de los dos.

## Órdenes exactas que los reproducen

Desde la raíz del *worktree*, con `PYLIBS` apuntando al directorio donde vive
`coverage` 7.16.0:

```sh
export PYLIBS="<ruta al scratchpad>/pylibs"
export PY="D:/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe"

# 1) cobertura.json
PYTHONIOENCODING=utf-8 PYTHONPATH="$PYLIBS" COVERAGE_FILE=".coverage-cob-ramas" \
  "$PY" -m coverage run --branch --source=filex -m unittest pruebas.test_cob_superficies
PYTHONPATH="$PYLIBS" COVERAGE_FILE=".coverage-cob-ramas" \
  "$PY" -m coverage json \
  --include="filex/cli.py,filex/__main__.py,filex/api.py,filex/watcher.py" \
  -o bench/salidas-cobertura-superficies/cobertura.json --pretty-print

# 2) delta.json  (instantáneo)
"$PY" bench/salidas-cobertura-superficies/delta.py \
  <base-cobertura.json del maestro> \
  bench/salidas-cobertura-superficies/cobertura.json \
  bench/salidas-cobertura-superficies/delta.json

# 3) discriminacion.json  (72 mutaciones, una prueba por mutación)
"$PY" bench/salidas-cobertura-superficies/discriminacion.py

# 4) el desglose por función que abre el informe
"$PY" bench/salidas-cobertura-superficies/funciones_de_cero.py \
  <base-cobertura.json del maestro> \
  bench/salidas-cobertura-superficies/cobertura.json
```

`delta.py` necesita la cobertura BASE de la suite entera, que midió el maestro
antes de la ronda y **no la produce este carril**: no se puede reejecutar la
suite completa con cinco agentes más en la máquina (trampas 101 y 123). Sus
cifras por módulo están transcritas en `bench/cobertura-superficies.md` §1, así
que el informe se lee sin ese fichero.

## Sondas de exploración

`explorar.py` … `explorar5.py` **no son medidas publicables**: sirvieron para
elegir los casos de prueba (qué pares dan `aviso`, qué formatos conocidos no
tienen destino, qué `--raiz` provoca `ValueError`). Se conservan porque tres de
sus resultados **son afirmaciones del informe** —0 pares con aviso de 1 122,
0 motores ausentes, 6 formatos conocidos sin destino— y sin la orden que los
produce serían números sin respaldo.

`ver_base.py` imprime las líneas sin ejecutar de la base, por módulo.
