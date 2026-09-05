# MANIFIESTO — salidas del carril `cob/fidelidad`

Respalda [`bench/cobertura-fidelidad.md`](../cobertura-fidelidad.md).

**Intérprete:** `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`
(Python 3.11.9, win32). **Motores:** `magick` 7.1.2 Q16-HDRI (RSVG 2.40.20),
`gswin64c` 10.07, `ffmpeg`/`ffprobe` N-121159. **Docker no interviene.**
**`coverage` 7.16.0** vive **fuera de los venvs** (§1 de `CLAUDE.md`: en ningún
entorno virtual se instala nada); `cubrir.py` lo mete en `sys.path` y delega en
su CLI, de modo que **no hace falta ninguna variable de entorno**. Si el
scratchpad de la sesión ya no existe, apúntalo con `FILEX_PYLIBS=<ruta>`.

Todas las órdenes se lanzan **desde la raíz del repositorio**.

## Lo versionado

| Fichero | Bytes | `sha256` (16) | Orden que lo reproduce |
|---|---:|---|---|
| `cobertura.json` | 564 369 | `e6634d17e6d73f72` | ① y ② |
| `delta.json` | 2 104 | `ce4eb9e12c6bd04f` | ③ |
| `discriminacion.json` | 9 983 | `fff68443f1f473d2` | ④ |
| `solape.json` | — | — | ⑤ |
| `sonda_i9_transform.json` | 489 | `1f4c77d7f61742d4` | ⑥ |
| `sonda_v5_orden.json` | 1 094 | `40ee6669ade6185a` | ⑦ |
| `suite.log` | 19 080 | `0981f8d8d015f4b7` | ⑧ |
| `cuelgue-dispositivo-CON.log` | 6 423 | `147f66ac33998b23` | evidencia, **no regenerable**: ver abajo |

Los `sha256` y los tamaños son los del momento de escribir el manifiesto.
**`cobertura.json`, `delta.json` y `discriminacion.json` NO son
byte-a-byte reproducibles**: `cobertura.json` lleva rutas absolutas de esta
máquina, y los tres llevan el orden de iteración de sus diccionarios. **Lo que
sí es reproducible es su contenido**: los recuentos por función, los 37 `ok` de
discriminación y la lista vacía de líneas que quedan.

```
① python bench/salidas-cobertura-fidelidad/cubrir.py run --branch \
      --source=filex --data-file=bench/salidas-cobertura-fidelidad/.coverage \
      -m unittest pruebas.test_cob_fidelidad

② python bench/salidas-cobertura-fidelidad/cubrir.py json \
      --data-file=bench/salidas-cobertura-fidelidad/.coverage \
      -o bench/salidas-cobertura-fidelidad/cobertura.json

③ python bench/salidas-cobertura-fidelidad/delta.py \
      <base-cobertura.json> bench/salidas-cobertura-fidelidad/cobertura.json \
      bench/salidas-cobertura-fidelidad/delta.json --ref main

④ python bench/salidas-cobertura-fidelidad/discriminacion.py \
      bench/salidas-cobertura-fidelidad/discriminacion.json

⑤ python bench/salidas-cobertura-fidelidad/solape.py cpu/fidelidad-impl

⑥ python bench/salidas-cobertura-fidelidad/sonda_i9_transform.py

⑦ python bench/salidas-cobertura-fidelidad/sonda_v5_orden.py

⑧ python -m unittest pruebas.test_cob_fidelidad -v \
      > bench/salidas-cobertura-fidelidad/suite.log 2>&1
```

`<base-cobertura.json>` es la cobertura de la suite completa sobre `main` que
midió el maestro; vive fuera del repositorio (scratchpad de la sesión). Se
regenera con la misma orden ① cambiando `-m unittest pruebas.test_cob_fidelidad`
por un `discover` de la suite entera — **que este carril no debe lanzar**
mientras haya otros midiendo (trampas 101 y 123).

## Lo NO versionado, a propósito

* **`.coverage`** — es **SQLite**, no texto (`CLAUDE.md` §6). Está en el
  `.gitignore` de este directorio. Se regenera con ①.
* **Los clips, PNG, GIF, SVG y PDF de las pruebas** — se construyen **en
  proceso** dentro de un desechable por clase (R18) y se borran al terminar.
  No hay un solo binario que versionar: los constructores viven en
  `pruebas/test_cob_fidelidad.py` (`escribe_png`, `png_gris`, `escribe_gif`,
  `escribe_svg`, `escribe_pdf`) y los clips los genera `ffmpeg` con
  `-frames:v`/`-t` **dentro de la orden**.
* **Los logs intermedios de las pasadas 2 a 5** — se borraron: no aportan nada
  que `suite.log` no diga mejor.

## `cuelgue-dispositivo-CON.log` — evidencia irreproducible por diseño

Es la salida truncada de la pasada que se colgó porque una prueba escribía en
un fichero llamado `con.txt`, que en Windows es el **dispositivo de consola**
(informe §6). **No se regenera**: el defecto está corregido en el módulo, y
recrearlo exigiría reintroducirlo. Se conserva porque el cuadro clínico —un
hilo, cero hijos, 0,45 s de CPU en diez minutos, ni un error— es lo único que
distingue este cuelgue de «la máquina va lenta», y eso no se puede parafrasear.
Pesa 6,4 KB de texto.
