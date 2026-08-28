# Salidas del agente T — N10, N11 y N13

Informe: `bench/cancelacion-entre-procesos.md`.
Todo es texto: no hay ninguna salida binaria que borrar. **No se usó la GPU y no
se lanzó ningún contenedor** (`docker ps -a` antes y después: los mismos seis de
siempre, `filex-convertx`, `filex-snapotter`, `filex-snapotter-pg`,
`filex-snapotter-redis`, `filex-gotenberg8` y `filex-gotenberg` — cero nuevos,
cero huérfanos).

| Fichero | Bytes | `sha256` |
|---|---:|---|
| `arnes_procesos.py` | 13 929 | `eca6e9b91543007ecb7e636538b2c0f5e7a6811b9a9bc3bae9434bc276d33540` |
| `n10_medidas.json` | 3 461 | `01e59339b45560669bcdc1c37124ab6762e9c07622f08d27d942fd00b7d8c406` |
| `sonda_afinidad.py` | 4 364 | `50295990c79c27ec33d3ceb2eeb672fcc09f6cede4c06706efe3be49670cdc44` |
| `sonda_afinidad.json` | 540 | `0b69c9c824007b5fe4b672f910b5f74d752c10f22153b893b6ac3bb4ac15cb4e` |
| `sonda_posix.py` | 12 119 | `2b0c98edbd361eacebfb45d32887bf0a03815ba4ee64d918be40794016f595b4` |
| `sonda_posix.json` | 1 416 | `00025619e8875dc5c4e126f5e3477a35f043f303e62fc9c6d9cfda7f3922a489` |
| `logs/arnes_procesos.log` | 3 090 | `c76e3b4ee29af10b64eb7bdfde64e037fb724548f4da5e261ca1e2037b3dd4ff` |
| `logs/sonda_afinidad.log` | 542 | `6d10dba305bfbea5f9a5f9b526163dd60d9842ef84105fa5ff0e9fc97f8158e1` |
| `logs/sonda_posix.log` | 1 477 | `cf36e7a36b5a318219b64e983ac70e4151570e91c8faf23c6bbad7fb90a35f39` |
| `logs/sondeo_antes.log` | 33 | `23e5105edf064691e359f6e63466249e1bf69e17575e841a572a93ab72610f00` |
| `logs/sondeo_despues.log` | 203 | `87757088643a495b3c97b813f1e843d5aa8daf1048445faacc8c20cf6274d4c5` |

## Cómo se reproduce cada una — las órdenes EXACTAS

Todas desde la raíz del repositorio (o del *worktree*), con el `python` del
sistema (3.11.9). **`corpus/` tiene que estar descargado de LFS**: si
`corpus/imagen/tipico.png` pesa 130 B en vez de 42 855, `git lfs checkout`
primero (trampa 34).

### `n10_medidas.json` + `logs/arnes_procesos.log`

```
python bench/salidas-cancelacion-procesos/arnes_procesos.py --n 9 --micro 200
```

Tarda ~7 min: la mitad `sin_canal` de M1 deja terminar nueve conversiones de
`corpus/video/tipico.mp4 → webm` enteras, que es justo lo que se está midiendo.
`--n 2 --micro 20` da la misma forma en ~1 min para comprobar que el arnés
corre. El log se obtuvo redirigiendo la salida:

```
python bench/salidas-cancelacion-procesos/arnes_procesos.py --n 9 --micro 200 > bench/salidas-cancelacion-procesos/logs/arnes_procesos.log 2>&1
```

Lanza procesos `filex` de verdad a través de `pruebas/hijo_de_trabajo.py`, que
**es parte del arnés y del conjunto de pruebas a la vez** y por eso vive en
`pruebas/`, no aquí.

### `sonda_afinidad.json` + `logs/sonda_afinidad.log`

```
python bench/salidas-cancelacion-procesos/sonda_afinidad.py
```

Segundos. Windows only: en POSIX la celda C se declara `aplica: false`.

### `sonda_posix.json` + `logs/sonda_posix.log`

**Se ejecuta DENTRO de WSL2**, y desde PowerShell, no desde Git Bash —Git Bash
traduce la ruta `/mnt/...` y el intento falla con un `No such file` que mezcla
las dos rutas—:

```
wsl -e python3 /mnt/d/Work/research/FileX/bench/salidas-cancelacion-procesos/sonda_posix.py
```

Escribe el JSON **junto al script**, es decir en el `/mnt/d` de Windows. Mide
sobre `/tmp/filex-n13`, que es **ext4**, no sobre `/mnt/d`: medir el candado
sobre drvfs sería medir el puente y no POSIX.

### `logs/sondeo_antes.log` y `logs/sondeo_despues.log`

La misma orden, antes y después de tocar `filex/invocacion.py`:

```
python -c "from filex.motores import sondear_todos; from filex.sondeo import diagnostico; import collections,json; ms=sondear_todos(); c=collections.Counter(); [c.update([getattr(a.estado,'name',str(a.estado))]) for m in ms for a in m.aristas]; print(dict(c)); print(json.dumps(diagnostico()['caducados'],ensure_ascii=False))"
```

`sondeo_antes.log` **no se puede reproducir sobre el árbol actual**: mide el
estado previo al cambio, y volver a él es `git stash` o mirar el commit padre.
Se conserva porque es la mitad que da sentido a la otra.
