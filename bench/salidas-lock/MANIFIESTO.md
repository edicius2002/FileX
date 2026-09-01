# MANIFIESTO — `bench/salidas-lock/`

Informe: **`bench/lock-de-maquina.md`** (agente L1, encargo C26, 23/08/2026).

**Todo son ficheros de texto** (`.sh` y `.log`); no hay binarios. `bench/lock-de-maquina.md`
§10 ya traía esta misma tabla de ficheros — este manifiesto la repite en el formato que
exige CLAUDE.md §6/CONTRIBUTING.md §6 y añade `sha256`.

**Reproducibilidad — declarada, no mecánica:** las cinco pruebas dependen de **Git Bash en
Windows** (`$$` como PID de msys, `/proc/$$/winpid`, `tasklist`, `taskkill /F`, `/tmp` =
`%TEMP%` — todo ello específico de esa combinación de intérprete y SO, ya documentado en
`CLAUDE.md` §2 y en las trampas 41/77/93/94). **No son reproducibles desde este WSL2**: el
propio informe que las originó (`bench/lock-entre-interpretes.md`) mide que WSL no comparte
la noción de "PID de Windows vivo" que estas pruebas necesitan (trampa 90). Repetirlas exige
una sesión de `Git Bash` real en la máquina de Windows del proyecto.

## Ficheros

| Fichero | sha256 | bytes | Orden que lo reproduce |
|---|---|---:|---|
| `harness_viejo.sh` | `23713368667ef884db3b0111e7abef515c96ae3fe83de888703839b0aab70e6a` | 3035 | Copia literal del `bench/lib/harness.sh` **anterior a C26** — verificado byte a byte: coincide con `git show f0a0858:bench/lib/harness.sh` (commit previo a la reescritura del lock). No se regenera con un comando: se recupera con `git show f0a0858:bench/lib/harness.sh > bench/salidas-lock/harness_viejo.sh` |
| `prueba_huerfano_viejo.sh` | `8838d46f7d4daed14596de53ab3f376e8a2e8b06b3ec2754390248bb51a30ce1` | 1580 | `bash bench/salidas-lock/prueba_huerfano_viejo.sh` (Git Bash, Windows) |
| `prueba_huerfano_viejo.log` | `a7634fd159b73a8e9c7b29dc4167eb26c9a4400a09d5d8c8010eefc2301beac8` | 645 | salida de la orden anterior |
| `prueba_harness_nuevo.sh` | `d875aa8d6ddfff59f82c97f508c89655ed5e9e551528cbaa14029e20a1233320` | 5332 | `bash bench/salidas-lock/prueba_harness_nuevo.sh` (Git Bash, Windows; P0–P10 de §4) |
| `prueba_harness_nuevo.log` | `8e56fe6919578677bce48659dc33cb3f8613117f3b36ada0d6934b742d3a89d8` | 10870 | salida de la orden anterior |
| `prueba_legado.sh` | `c0411a0a40d0bec404974116c09f49f7d0fcbd282c9aa10c5c5a4b8dd337898b` | 1350 | `bash bench/salidas-lock/prueba_legado.sh` (Git Bash, Windows; P11–P12 de §4) |
| `prueba_legado.log` | `35b37573cc155782c586f77c9b737c4b0a5b0b92cf8a9fdf4aea89c5328ffc4e` | 699 | salida de la orden anterior |
| `compat-run_a_png.log` | `c5c35dca5a8ca05d1b4a5549eb8591244ec33e8d28ad8913aabc15c8b8717abb` | 1768 | `GPU_LIBRE_MIN_MIB=20000 bash bench/salidas-k-motor/run_a_png.sh` (Git Bash, Windows; §4.1 — un script real y sin modificar, para probar compatibilidad hacia atrás del harness nuevo) |
| `vram-linea-base.log` | `fdde65cec0496dff16ffbc4e934f5fd103d1ad17444022e881c9334f6fec9d73` | 1530 | 90 muestras a 1 s de `nvidia-smi --query-gpu=memory.used,memory.used --format=csv,noheader,nounits` (§2.2), lanzado en un bucle de shell del propio `bench/lib/harness.sh` durante 90 s; depende del estado de escritorio de esa sesión (Chrome, Discord, Wallpaper Engine, etc. — ver §2.2 del informe) y por tanto **no es reproducible al byte**, solo al orden de magnitud declarado |
| `censo-ajeno.log` | `f4fc150bc8b0aed9c3baad2d5fdaed136dfb4691685dc5b5d880c5b33b32e25d` | 1487 | salida de `gpu_censo_ajeno` (`bench/lib/harness.sh`), que invoca `bench/lib/censo_gpu.ps1` vía `powershell.exe` (Git Bash, Windows); **no reproducible al byte**: censa los procesos vivos de la máquina en ese instante (nombres de proyectos, PIDs) |

## Lo que se declara PENDIENTE / no ejecutable en esta máquina de trabajo

- Las diez salidas anteriores **no se pueden regenerar desde este worktree WSL2**: todas
  dependen de Git Bash + `tasklist`/`taskkill`/`powershell.exe` de Windows. Este agente
  (worker2, WSL2) solo pudo **verificar** los ficheros existentes (hashes, tamaños,
  comparación de `harness_viejo.sh` contra el historial de git), no volver a ejecutarlos.
- `vram-linea-base.log` y `censo-ajeno.log` son, por naturaleza, **no reproducibles al
  byte** aunque se relancen en Git Bash: dependen del estado transitorio del escritorio y de
  qué procesos había vivos en ese instante. Lo reproducible es el **procedimiento**, no la
  cifra exacta — igual que `bench/lock-de-maquina.md` §2.2 ya advierte.
- El fichero `ESTADO-antes-sed.bak` que el propio informe (`bench/lock-de-maquina.md` §10)
  lista como parte de las salidas **no existe hoy en el árbol** — probablemente limpiado en
  una pasada posterior de higiene del repositorio. No se recrea aquí: no es un fichero que
  este agente haya generado ni tenga forma de reconstruir sin el `ESTADO-Y-REPARTO.md`
  anterior a la pasada `sed` referida.
