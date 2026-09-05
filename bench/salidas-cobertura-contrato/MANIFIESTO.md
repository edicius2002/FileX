# MANIFIESTO — `bench/salidas-cobertura-contrato/` (carril `cob/contrato`)

Informe: **`bench/cobertura-contrato.md`**.

Medido el **04-05/09/2026** en la máquina del proyecto.

**Declaraciones que un recuento necesita (trampas 94 y 101):**

| Qué | Valor |
|---|---|
| Intérprete | `.venv-mcp-filex\Scripts\python.exe` — CPython **3.11.9**, `win32` |
| Entorno | ImageMagick 7.1.2 Q16-HDRI, ffmpeg/ffprobe N-121159, Ghostscript 10.07 — los tres en el PATH. **Sin Docker** y **sin GPU**: ninguna prueba de este fichero los pide |
| Corpus | `corpus/` materializado con `git lfs checkout` (`corpus/imagen/tipico.png` = 42 855 B, no 130) |
| Estado de la máquina | había otros agentes trabajando; **no se publica ni un tiempo absoluto** en el informe, por §3 |
| Qué quedó fuera | nada saltó en esta tanda: **91 corridas, 91 pasadas, 0 saltadas** |
| Instrumento | `coverage` **7.16.0 con `--branch`**, el mismo que midió la base. Sin `--branch` el `percent_covered` mide otra cosa y los dos números no son comparables (trampa 59) |

**Nada de lo que hay aquí es un binario.** Los cuatro ficheros son texto (dos
scripts y dos JSON de resultados), que es lo que §6 manda versionar.

## Ficheros

**Los `sha256` se dan DOS veces, y no es adorno.** Los tres JSON los escribe
Python en Windows con **CRLF**, y `.gitattributes` los normaliza a **LF** al
versionarlos: quien clone el repositorio y compruebe la suma contra la columna
«en disco» obtendrá un fallo que no es de integridad, sino de fin de línea. La
columna que hay que usar tras un clon es **`sha256` LF**; la de disco es la que
reproduce la orden en esta máquina. Los dos `.py` no se mueven porque git no
los toca.

| Fichero | Bytes disco | sha256 (12) disco | Bytes LF | sha256 (12) LF | Qué es |
|---|---:|---|---:|---|---|
| `cobertura.json` | 2 255 604 | `b5beddc94d17` | 2 183 932 | `9f6532efe60b` | Salida de `coverage json --branch` sobre `filex/` ejecutando **solo** `pruebas/test_cob_contrato.py` |
| `discriminacion.json` | 18 537 | `e1bd448a4231` | 17 860 | `0fd441e4e245` | Las **49 mutaciones** del control de discriminación, con las pruebas que se pusieron rojas en cada una |
| `ppp-inalcanzable.json` | 6 694 | `44e77eb79396` | 6 364 | `bbd24de7c8e4` | Barrido de 22 formatos para responder por qué quedan sin ejecutar las líneas 3320-3321 |
| `mutaciones.py` | 16 320 | `f7c8bf209461` | 16 320 | `f7c8bf209461` | El arnés que produce `discriminacion.json` |
| `sonda_ppp.py` | 5 785 | `7bdd3d65a983` | 5 785 | `7bdd3d65a983` | El barrido que produce `ppp-inalcanzable.json` |

`cobertura.json` son 2,26 MB **de texto**, no un binario: es JSON repetitivo y
comprime a una fracción en el pack. Se versiona entero y no recortado a
`verificador.py` porque recortarlo dejaría de ser la salida de `coverage json`
y no se podría comparar con la base del maestro.

## Órdenes que lo reproducen

`coverage` **7.16.0 vive fuera de los venvs** (§1 prohíbe instalar en ellos):
se usa por `PYTHONPATH`. Sustituir `<PYLIBS>` por el directorio que lo
contiene y `<PY>` por `.venv-mcp-filex\Scripts\python.exe` de la raíz del
repositorio.

```sh
# 1. cobertura.json  (el .coverage es SQLite y NO se versiona: se manda fuera
#    del árbol con COVERAGE_FILE)
PYTHONPATH=<PYLIBS> COVERAGE_FILE=<TMP>/.coverage-cob \
  <PY> -m coverage run --branch --source=filex -m unittest pruebas.test_cob_contrato
PYTHONPATH=<PYLIBS> COVERAGE_FILE=<TMP>/.coverage-cob \
  <PY> -m coverage json -o bench/salidas-cobertura-contrato/cobertura.json --pretty-print

# 2. discriminacion.json  (son 49 pasadas de la suite del fichero)
<PY> bench/salidas-cobertura-contrato/mutaciones.py

# 3. ppp-inalcanzable.json
<PY> bench/salidas-cobertura-contrato/sonda_ppp.py
```

`mutaciones.py` **escribe en `filex/verificador.py` y lo restaura con
`git checkout -- filex/verificador.py`**, nunca con `git stash push`
(trampa 119). Comprueba el `sha256` antes y después de cada celda y termina
imprimiendo si el árbol quedó limpio; devuelve `rc=1` si alguna mutación no
discrimina **o** si el árbol no quedó limpio. En la tanda publicada:
`49/49 discriminan`, `arbol_limpio_al_terminar: true`.

## Lo que no se versiona

- `.coverage` — es una base SQLite y es regenerable con la orden 1.
- Los directorios desechables de las pruebas: cada una crea el suyo con
  `tempfile.mkdtemp` y lo borra en `addCleanup` (regla R18).
