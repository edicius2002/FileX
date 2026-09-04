# MANIFIESTO — salidas de `bench/cancelacion-inestable.md` (N36, worker8, ronda 18)

Todo lo de aquí es **texto** —`.py`, `.json` y `.log`—, que es lo que §6 de
`CLAUDE.md` manda versionar: son la trazabilidad del informe y pesan **241 KB**
los 48 logs. **No hay un solo binario**, así que no hay nada podado ni nada que
esta lista tenga que enseñar a regenerar por ausencia (trampa 95).

**Los logs son el activo, no el subproducto.** La trampa 103 se pagó por
canalizar a `tail` justo la salida de la pasada que falló: aquí cada pasada de
pytest se guarda **íntegra**, y de esos ficheros salen las cinco trazas de §2 del
informe.

---

## 1. Entorno de todas las medidas

| Qué | Valor |
|---|---|
| Intérprete | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` — CPython **3.11.9**, `win32` |
| pytest | **9.1.1**, sin plugins (`pip list \| grep pytest` da una sola línea) |
| Docker | **29.4.3**, levantado (12 imágenes) para la suite completa |
| Corpus | LFS materializado: `corpus/imagen/tipico.png` = **42 855 B** |
| Máquina | **NO tranquila** — procesos de otros proyectos vivos, §0 del informe |
| Fecha | 04/09/2026 |

**Rama:** `cpu/cancelacion-inestable`. El informe **no cita ningún commit de esta
rama** —deliberadamente, por la trampa 115: un `--squash` con borrado de rama
mataría la cita—, así que no hace falta archivarla para que el informe siga
resolviendo.

---

## 2. Arneses

| Fichero | Bytes | `sha256` (16) | Qué hace |
|---|---|---|---|
| `tanda.py` | 6 321 | `c28a052218e9cd6b` | Repite una selección de pytest `n` veces guardando la salida íntegra en `logs/`, con testigos de nivel, deriva y `ffmpeg` vivos, y `--carga N` como variable independiente declarada |
| `sonda_n36.py` | 7 431 | `fb1a94a601f4a75b` | Reproduce **sólo** el escenario N36 fuera de pytest, registrando la traza del sujeto: `aviso_cerrojo`, `cerrojo.esta_libre` antes de cancelar, el dict íntegro de `job(…, "cancelar")` y sus `ms` |
| `sonda_dueno_muerto.py` | 9 629 | `c81b6032a57ab8f3` | A/B causal del kill: variante **A** (`taskkill /F /T` sobre el `Popen`, lo que hacía el arnés) contra **B** (el dueño primero por su PID real). Decide **quién escribió** el estado leyendo el `resultado` del JSON del trabajo |

> **Aviso sobre `sonda_dueno_muerto.py`, y está en su propio docstring:** su primera
> versión censaba los nietos con una consulta CIM **antes** del `taskkill`. Esa
> consulta cuesta ~1 s y **enmascaraba la carrera**: daba 20 de 20 celdas verdes.
> Los ficheros `sonda-dueno-muerto-A-carga0.json` y `-A-carga12.json` son de esa
> versión y **se conservan como el control que no discrimina** (trampa 116), no
> como evidencia del mecanismo. El que reproduce es `-A-carga8-d0.0.json`.

---

## 3. Resultados

| Fichero | Bytes | `sha256` (16) | Saldo |
|---|---|---|---|
| `tanda-piloto-modulo.json` | 1 095 | `02e7f983061a4be6` | módulo, carga 0, n=3 → **3/3** limpias |
| `tanda-modulo.json` | 4 450 | `7cdb999e59e909aa` | módulo, carga 0, n=12 → **10/12** |
| `tanda-modulo-carga8.json` | 3 639 | `d6b59d11c33bddd4` | módulo, carga 8, n=8 → **3/8** (estado heredado) |
| `tanda-control-modulo-killviejo.json` | 2 397 | `8baab7621b87df46` | módulo, carga 8, n=6, **kill viejo sin la fuga** → **6/6** |
| `tanda-control-killviejo.json` | 2 308 | `e7cfe6b90d1fee68` | **sólo** `DuenoMuerto`, carga 8, n=6, kill viejo → **6/6** (el «aislada 3/3» del maestro, con mecanismo) |
| `tanda-arreglo-carga8.json` | 3 033 | `8f3c492ddb43dcc1` | módulo, carga 8, n=8, **arreglo** → **8/8**, huérfanos 0 |
| `sonda-n36-carga0.json` | 5 553 | `65e9a6f0edf617ae` | N36 aislado, sin carga, n=8 → **8/8** |
| `sonda-n36-carga12.json` | 5 573 | `f2d64d22fc53cac4` | N36 aislado, **12 procesos de carga**, n=8 → **8/8** |
| `sonda-dueno-muerto-A-carga0.json` | 4 286 | `2e9afabd309c4a39` | variante A **con la demora CIM**, n=10 → 10/10 `working` (**no discrimina**) |
| `sonda-dueno-muerto-A-carga12.json` | 4 307 | `11e77d92aeba3329` | ídem, carga 12, n=10 → 10/10 (**no discrimina**) |
| `sonda-dueno-muerto-A-carga8-d0.0.json` | 6 256 | `9adc91556cce24dd` | variante A **sin demora**, carga 8 → **reproduce** el fallo fuera de pytest |

**`logs/`** — 48 ficheros, 241 KB. Una pasada de pytest por fichero, con su nombre
`<etiqueta>-<NN>.log`, más `tanda-*.out` (la salida del conductor) y las dos de la
suite completa.

---

## 4. Las órdenes exactas que lo reproducen

Desde la raíz del repositorio, con `PYTHONIOENCODING=utf-8` y
`PY=.venv-mcp-filex\Scripts\python.exe`:

```sh
# El estado heredado (hay que revertir pruebas/ a antes del arreglo para verlo):
$PY bench/salidas-cancelacion-inestable/tanda.py \
    --etiqueta modulo --n 12 --sel pruebas/test_cancelacion_procesos.py
$PY bench/salidas-cancelacion-inestable/tanda.py \
    --etiqueta modulo-carga8 --n 8 --carga 8 --sel pruebas/test_cancelacion_procesos.py

# El arreglo, misma carga:
$PY bench/salidas-cancelacion-inestable/tanda.py \
    --etiqueta arreglo-carga8 --n 8 --carga 8 --sel pruebas/test_cancelacion_procesos.py

# N36 aislado, con y sin carga declarada:
$PY bench/salidas-cancelacion-inestable/sonda_n36.py --n 8 --carga 0
$PY bench/salidas-cancelacion-inestable/sonda_n36.py --n 8 --carga 12

# El A/B del kill. `--demora 0` es obligatorio: con demora no discrimina.
$PY bench/salidas-cancelacion-inestable/sonda_dueno_muerto.py \
    --n 12 --variante A --carga 8 --demora 0

# La suite completa (Docker levantado):
$PY -m pytest pruebas -q -rs -p no:cacheprovider
```

**Para reproducir el estado heredado** hay que volver `pruebas/` a antes del
arreglo. La forma correcta es `git checkout <commit> -- pruebas/` o
`git show <commit>:<fichero> >`, **nunca `git stash push <fichero>`**, que sobre un
fichero ya commiteado no hace nada y devuelve 0 sin avisar (trampa 119). Y después
hay que **comprobar interrogando al fichero** que la reversión ocurrió, no al
mandato que se creía que la hacía.

---

## 5. Un aviso para quien repita esto

**El estado heredado del arnés dejaba 3 `ffmpeg.exe` codificando VP9 a `-threads 4`
por cada pasada del módulo**, vivos ~20-60 s después de que pytest terminara. Si
reviertes `pruebas/` para reproducirlo, **cuenta los huérfanos antes y después**
—`tanda.py` ya lo hace— y bárrelos antes de medir otra cosa, o estarás midiendo
tus propios restos. Con el arreglo puesto son **0**.
