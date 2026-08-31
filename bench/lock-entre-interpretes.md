# El lock de GPU no cruza entre intérpretes, y no falla callándose: ROBA

**Fecha:** 29 de agosto de 2026 · **Agente:** master · **Recurso:** ninguno (sonda de shell, sin GPU)
**Salidas:** `bench/salidas-lock-interpretes/` — `sonda_lock.sh`, `cruzar.sh`, `cruce_interpretes.log`
**Motivo:** decidir desde dónde corren los workers de medición cuando la sesión de trabajo es WSL2 y el histórico se midió en Git Bash.

---

## 1. La pregunta, y por qué no era la que yo creía

La sesión de trabajo de esta ronda es **WSL2** (`/mnt/d/Work/research/FileX`), mientras que todo lo publicado se midió desde el **Git Bash de Windows**. Antes de repartir trabajo entre dos workers había que saber si se puede medir desde WSL.

`bench/lib/harness.sh` declara su propio límite en un comentario: *«`%TEMP%` es POR USUARIO y no cruza a la VM de WSL2»*. Ese límite, tal como está escrito, describe un fallo **benigno**: dos ficheros de lock distintos, cada uno excluyendo dentro de su mundo, sin interferencia.

De ahí sale el arreglo obvio, y es el que yo mismo propuse antes de medir: **poner el lock en un sitio que los dos mundos vean** — `GPU_LOCK_DIR=/mnt/c/Users/<usuario>/AppData/Local/Temp`, que **es escribible desde WSL (MEDIDO)**. La hipótesis del riesgo que acompañaba a esa propuesta era la **trampa 41**: que el candado se comportara distinto sobre DrvFs, que no es ni NTFS nativo ni ext4.

**Esa hipótesis era falsa, y el hecho que anticipaba era cierto.** Es la trampa 58 otra vez: acertar el riesgo y errar la causa. El sistema de ficheros no interviene —`noclobber` funciona—; lo que se rompe es el criterio de **vida del dueño**, y el resultado es peor que un candado lento: **es un candado que borra el del otro**.

---

## 2. El mecanismo

El lock lleva dentro lo necesario para saber si su dueño sigue vivo (`harness.sh`, líneas 123-147):

```
etiqueta <TAB> pid_msys <TAB> winpid <TAB> imagen <TAB> epoch <TAB> raiz
```

Guarda **dos** PID a propósito, porque el proyecto ya midió que el `$$` de Git Bash no es el PID de Windows (45 483 frente a 11 656). `_gpu_dueno_vivo()` comprueba el `winpid` con `tasklist`, y además la **imagen**, porque en Windows los PID se reutilizan.

Esa comprobación existe por una razón buena: **un `taskkill /F` no ejecuta el `trap`**, así que sin recuperación de huérfanos un lock abandonado bloquearía la tarjeta para siempre.

Desde WSL fallan las dos piezas que la alimentan, y las dos empujan al mismo veredicto:

| Pieza | En Git Bash | En WSL2 | Consecuencia |
|---|---|---|---|
| `cat /proc/$$/winpid` | devuelve el PID de Windows | **no existe** → `: "${winpid:=$$}"` | el campo `winpid` guarda un **PID de Linux** |
| `tasklist //FI …` | ejecuta | **`No such file or directory`** (hace falta `tasklist.exe` y `/FI`) | la línea sale vacía → nunca coincide |

Con la línea vacía, el `case` no encuentra el `winpid`, `_gpu_dueno_vivo` devuelve 1, y `gpu_acquire` concluye huérfano: **borra el lock ajeno y entra**.

**La recuperación de huérfanos es el arma.** Si el lock simplemente no se viera, habría dos tandas en paralelo: malo, simétrico y detectable. Lo que ocurre es que el intruso *elimina* el fichero del otro, así que la víctima **queda sin protección durante el resto de su tanda y no se entera**. Y el intruso imprime `[lock] HUERFANO detectado … lo libero`, que es exactamente la línea del caso legítimo.

Otras dos dependencias de Git Bash, cosméticas porque son sobrescribibles por entorno: `GPU_PS` apunta a `/c/Windows/…` (en WSL es `/mnt/c/…`, así que `gpu_censo_ajeno` cae a `CENSO_NO_DISPONIBLE`) y `GPU_LOCK_LEGADO` a `D:/Work/…`, que no resuelve.

---

## 3. La medida: cuatro celdas, con control positivo

Sonda: `bench/salidas-lock-interpretes/cruzar.sh`. El dueño se lanza en segundo plano y **se queda vivo** 25 s; sólo cuando el lock existe en disco se evalúa desde el otro intérprete; se registra si el dueño estaba vivo **antes y después** de la evaluación. El Git Bash se invoca por ruta resuelta, nunca por nombre (**trampa 77**).

| Celda | Retiene el lock | Lo evalúa | `winpid` | Veredicto |
|---|---|---|---|---|
| **A** | Git Bash | Git Bash | 36 448 | **`DUENO_VIVO` (rc=0) — respeta** ✅ |
| **B** | Git Bash | **WSL2** | 7 048 | **`HUERFANO` (rc=1) — BORRA y entra** ❌ |
| **C** | **WSL2** | Git Bash | 394 117 | **`HUERFANO` (rc=1) — BORRA y entra** ❌ |
| **D** | **WSL2** | **WSL2** | 394 135 | **`HUERFANO` (rc=1) — BORRA y entra** ❌ |

En las cuatro, `dueño_vivo_ANTES=SI` y `dueño_vivo_DESPUES=SI`. **A es el control positivo**: el mecanismo funciona, y lo que falla es el cruce.

### 3.1 D es el hallazgo mayor, y no estaba en la hipótesis

**WSL2 no se excluye ni consigo mismo.** No hace falta mezclar intérpretes: **dos workers ambos en WSL se roban el lock mutuamente**, porque `tasklist` no se ejecuta allí y *todo* dueño le parece muerto. Eso descarta la tercera opción de reparto —«los dos workers en WSL con el lock redirigido»— que era la única alternativa viva a Git Bash.

### 3.2 El fondo no es un parche de una línea

Un proceso de WSL **no tiene PID de Windows en absoluto**. No es que el harness lo lea mal: no hay nada que leer. Comprobado: `tasklist.exe /FI "PID eq 251620"` responde *«no hay tareas ejecutándose que coincidan»*. El criterio «¿vive el dueño?» **no tiene respuesta que cruce las dos máquinas**, así que arreglarlo exige un primitivo distinto, no una traducción de rutas.

---

## 4. Dos veces la trampa 38 en el propio arnés, y las dos las cazó el control positivo

Vale la pena dejarlo escrito, porque el arnés estuvo **dos versiones** dando un resultado que parecía el bueno.

1. **Primera versión:** un modo `escribir` que escribía el lock y salía. Las **cuatro** celdas dieron `HUERFANO` — y con razón: el dueño estaba muerto. El resultado *parecía* confirmar la hipótesis, sólo que por el motivo trivial.
2. **Segunda versión:** el dueño ya se retenía vivo, pero se lanzaba con `pid="$(ret_git)"`. **La sustitución de órdenes espera a que el hijo cierre `stdout`**, es decir a que muera, así que para cuando se evaluaba el lock el dueño llevaba 25 s muerto. Otra vez las cuatro en `HUERFANO`, y otra vez con la pinta correcta.

Lo único que las destapó fue que **la celda A tenía que salir verde y salía roja**. Sin control positivo, este informe habría publicado tres celdas falsas con la conclusión correcta — que es el peor resultado posible, porque nadie lo revisa.

Corolario, que amplía la trampa 38: **registrar que la condición se dio no basta si el registro también es del arnés.** La primera versión no comprobaba nada; la segunda imprimía `esperé 0ms`, que era *verdad* y significaba lo contrario de lo que parecía. La versión buena comprueba `kill -0` sobre el dueño **antes y después** de la evaluación, que es lo único que no depende de la coreografía.

---

## 5. Lo que sí sobrevive: la mitad de DETECCIÓN

`nvidia-smi` responde desde los dos mundos (**MEDIDO**: 3 149 / 12 288 MiB por `nvidia-smi.exe` y 3 110 por el `nvidia-smi` nativo de WSL). Así que `GPU_GUARD` **sigue funcionando desde WSL** y abortaría por debajo de los 6 000 MiB libres.

Pero eso deja abierta justo la ventana entre **tomar el lock** y **reservar la VRAM**, cuando no hay nada que ver en la tarjeta. Es la forma inversa de lo que el proyecto aprendió con el intruso de ASR (`lock-de-maquina.md`): allí la exclusión no bastaba y la salvó la detección; aquí la exclusión se rompe y queda sólo la detección, que **ya está documentada como insuficiente por su cuenta**.

---

## 6. Consecuencia para el reparto

**Los dos workers de medición van en Git Bash.** Es la única celda de las cuatro donde el lock excluye.

- **No** el reparto mixto (uno en cada sitio): celdas B y C.
- **No** los dos en WSL: celda D.
- WSL se queda con lo que sólo se puede hacer allí: **C5**, la carrera de symlinks, cuyo arnés existe en `bench/salidas-mcp-cabos-2/c5a_symlink_wsl.py`.

Y **arreglar el harness para WSL no es un preliminar: es C38**, que ya estaba abierto por *«el lock de GPU sólo existe en shell; 0 de 15 arneses `.py` lo toman»*. Este informe le añade un caso que su enunciado no cubría —el cruce de intérpretes— y refuerza hacia dónde va la solución: el mutex con nombre en `Global\` de `filex/cerrojo.py`, que ya está escrito, es **de máquina de verdad**, cuesta **18,1 µs** y **no depende de que el dueño tenga PID de Windows** (`cerrojo-unico.md`).

---

## 7. Lo que NO afecta

Todo lo demás de la interoperabilidad WSL→Windows funciona, y está medido en esta misma tanda:

| Necesidad | Resultado |
|---|---|
| Venvs CUDA | `./.venv-ai/Scripts/python.exe` → `3.11.9 · torch 2.6.0+cu124 · cuda True` |
| Traducción de rutas | Automática, **también desde el worktree**: lanzado en `.ccb/workspaces/worker1`, el `.exe` ve `D:\Work\research\FileX\.ccb\workspaces\worker1` |
| Docker | `docker.exe` (el `docker` de WSL no existe: integración desactivada). 5 contenedores arriba |
| `ffmpeg` · `magick` · `gs` | `.exe` vía interop |

**Un worker de WSL puede invocar cualquier motor de Windows sin fricción de rutas.** Lo único que no puede es tomar el lock de GPU — y por eso el reparto lo manda a trabajo de CPU o a Git Bash.

---

## 8. Reproducir

```sh
cd bench/salidas-lock-interpretes
bash ./cruzar.sh          # desde WSL2; invoca el Git Bash por ruta resuelta
```

No toca el lock real (`/tmp/filex-gpu.lock`): trabaja sobre `sonda-lock-interpretes.lock` en `%TEMP%` y lo borra al terminar. No usa la GPU, así que no necesita el lock.

## 9. Pendientes que abre

- **`C39`** — decidir el sustituto del criterio de vida del dueño para que cruce intérpretes. El candidato medido es el mutex `Global\` de `filex/cerrojo.py`, pero **tomarlo desde shell añade una dependencia** que el harness no tiene hoy, y eso no está medido. **PENDIENTE.**
- Si alguna vez se mide desde WSL con GPU, hace falta además `GPU_PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe` o el censo de ajenos sale `CENSO_NO_DISPONIBLE`. **PENDIENTE**, no probado.
