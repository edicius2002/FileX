# MANIFIESTO — `bench/salidas-lock-interpretes/`

Informe: **`bench/lock-entre-interpretes.md`** (encargo del cruce WSL2 ↔ Git Bash sobre el
lock de GPU, trampas 90/91 de `CLAUDE.md`).

**Todo son ficheros de texto** (`.sh` y `.py` de arnés, y un `.log` de salida); no hay
binarios.

**Reproducibilidad — parcial, y con la salvedad que el propio informe declara.** La sonda
está pensada exactamente para correr **desde este entorno** (WSL2) y cruzar hacia Git Bash
por ruta resuelta (trampa 77: `bash` a secas desde WSL no es el Git Bash), así que a
diferencia de `bench/salidas-lock/` **sí se pudo intentar volver a ejecutarla** en este
worktree.

## Ficheros

| Fichero | sha256 | bytes | Orden que lo reproduce |
|---|---|---:|---|
| `sonda_lock.sh` | `8c30a66a51310998276fcec3d9fc8ba94ee1d7ca314aff04b004f5c1cae0d6ae` | 3213 | No se ejecuta sola: la invocan `cruzar.sh` (modos `retener`/`evaluar`) tanto en WSL como, vía `GITBASH -c`, en Git Bash |
| `cruzar.sh` | `5ed824b7a1259ae8eb6fe0bc5dcc2278c0e986d6402cf26c5bac122a497b50fc` | 3748 | `cd bench/salidas-lock-interpretes && bash ./cruzar.sh` (lanzado desde WSL2; invoca `/mnt/c/Program Files/Git/bin/bash.exe` por ruta resuelta para la mitad de Git Bash) |
| `cruce_interpretes.log` | `f351d4162af95c512df3ddff739379d4aa346e55f55998ad4787eb5dc7d562ff` | 1616 | salida de la orden anterior — las 4 celdas (A: control positivo Git Bash→Git Bash, B/C: reparto mixto, D: WSL→WSL) |
| `sonda_pid_candado.py` | `71366c036df28d03ea504351d226087a175763fef40e0adaa3586ec87d6b1461` | 2823 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-lock-interpretes/sonda_pid_candado.py` (orden que trae el propio docstring del fichero; es el arnés citado en `CLAUDE.md` trampa 93, "6 de 6 venvs") |

## Verificación en esta máquina (WSL2, worker2, 01/09/2026) — REPRODUCIDO

Se relanzó `bash ./cruzar.sh` desde este worktree, sin tocar los scripts. El Git Bash
existe en la ruta que el script espera (`/mnt/c/Program Files/Git/bin/bash.exe`) y la
corrida terminó sin timeouts, reproduciendo **exactamente el mismo patrón de veredictos**
que el `cruce_interpretes.log` ya versionado:

| Celda | Retiene | Evalúa | Veredicto (log versionado) | Veredicto (esta corrida) |
|---|---|---|---|---|
| A (control positivo) | Git Bash | Git Bash | `DUENO_VIVO (rc=0)` | `DUENO_VIVO (rc=0)` |
| B | Git Bash | WSL2 | `HUERFANO (rc=1)` | `HUERFANO (rc=1)` |
| C | WSL2 | Git Bash | `HUERFANO (rc=1)` | `HUERFANO (rc=1)` |
| D | WSL2 | WSL2 | `HUERFANO (rc=1)` | `HUERFANO (rc=1)` |

Los detalles numéricos (PIDs, `winpid`, milisegundos hasta que aparece el lock) difieren
entre corridas, como es de esperar de una sonda que lanza procesos reales — el propio
`cruce_interpretes.log` no es reproducible al byte por eso, pero **el veredicto de cada
celda sí lo es**, y es la evidencia que sostiene el hallazgo del informe (trampa 90: WSL no
se excluye ni siquiera consigo mismo, celda D).

## Nada declarado PENDIENTE por falta de recursos

A diferencia de `bench/salidas-lock/`, los tres scripts de este directorio (`sonda_lock.sh`,
`cruzar.sh`, `sonda_pid_candado.py`) están diseñados para correr desde WSL2 — es la premisa
del informe — así que no hay aquí una barrera de sistema operativo que declarar como
bloqueo; solo la disponibilidad puntual del Git Bash de la máquina física, que no se ha
vuelto a comprobar en esta pasada por no ser el objetivo del encargo.
