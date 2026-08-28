# MANIFIESTO — `bench/salidas-watcher/` (agente U, N4 · N5 · N14)

Informe: **`bench/watcher-y-desechables.md`**.

**Aquí no hay ni un byte binario.** 301 610 B en total, todo `.py`, `.json` y
`.log`. Los desechables y ficheros temporales de cada sonda se borran al
terminar; lo único que se conserva es texto, que es lo que `CLAUDE.md` §6 pide
versionar.

Todas las órdenes se lanzan desde la raíz del repositorio (`W` = la raíz en
formato WSL, `%TEMP%` en Windows). **Las de N14 exigen `TMP`/`TEMP` privados**:
sin eso barren desechables de otros agentes.

---

## Resultados

| fichero | bytes | `sha256` (16) | orden que lo reproduce |
|---|---:|---|---|
| `posix_tmpfs.json` | 5 095 | `df320c1d7330db68` | `wsl.exe -e python3 $W/bench/salidas-watcher/sonda_posix.py --origen $W/corpus/imagen/tipico.png --dir /tmp/filex-n4 --etiqueta tmpfs --salida $W/bench/salidas-watcher/posix_tmpfs.json --log $W/bench/salidas-watcher/logs/posix_tmpfs.log` |
| `posix_drvfs.json` | 5 207 | `fc8b098a4347b7d5` | igual, con `--dir $W/bench/salidas-watcher/tmp-n4 --etiqueta drvfs_mnt_d --salida …/posix_drvfs.json --log …/logs/posix_drvfs.log` |
| `cruce.json` | 1 093 | `bb1c2e65b1509da2` | `python bench\salidas-watcher\cruce_win.py --origen corpus\imagen\tipico.png --dir %TEMP%\filex-cruce --salida bench\salidas-watcher\cruce.json --log bench\salidas-watcher\logs\cruce.log --segundos 30` |
| `incompletos.json` | 18 615 | `4fdb2e87c7a2ac54` | `python bench\salidas-watcher\sonda_incompletos.py --tmp %TEMP%\filex-n5 --salida bench\salidas-watcher\incompletos.json --log bench\salidas-watcher\logs\incompletos.log` |
| `residuo.json` | 5 230 | `aa3c2275d7982303` | `python bench\salidas-watcher\sonda_residuo.py --tmp %TEMP%\filex-n5r --salida bench\salidas-watcher\residuo.json --log bench\salidas-watcher\logs\residuo.log` |
| `desechables.json` | 4 942 | `aaa2dfd70f6a1788` | ver «N14 · TEMP privado» abajo |
| `ventana.json` | 1 342 | `898b46ee55d73d25` | `python bench\salidas-watcher\sonda_ventana.py --tmp %TEMP%\filex-n14-ventana --salida bench\salidas-watcher\ventana.json --log bench\salidas-watcher\logs\ventana.log` |
| `censo_temp.json` | 138 068 | `2b0c9e3d6178eb81` | `python bench\salidas-watcher\censo_temp.py --salida bench\salidas-watcher\censo_temp.json` — **solo lectura, no borra nada** |
| `coste_defensas.json` | 1 671 | `648af2d737dc3edf` | `python bench\salidas-watcher\coste_defensas.py --salida bench\salidas-watcher\coste_defensas.json` |

**N14 · TEMP privado** (PowerShell), porque hay otro agente en la máquina:

```powershell
$env:FILEX_TEMP_REAL = $env:TEMP
$P = "$env:TEMP\filex-n14-privado"
Remove-Item -Recurse -Force $P -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $P | Out-Null
$env:TMP = $P; $env:TEMP = $P
python bench\salidas-watcher\sonda_desechables.py `
  --entrada corpus\imagen\patologico_16bit.tif --tmp "$P\salidas" `
  --salida bench\salidas-watcher\desechables.json `
  --log bench\salidas-watcher\logs\desechables.log --matados 5 --espera 1.0
```

---

## Sondas y arneses

| fichero | qué hace |
|---|---|
| `escritor_lento.py` | escritor lento en proceso aparte, con marcadores `ABIERTO`/`PAUSA`/`CERRADO`. Modos `--solo-leer` y `--flock` (el control positivo de los cerrojos cooperativos) |
| `tenedor.py` | proceso que solo TIENE un fichero abierto. Portable: se usa desde Windows y desde WSL2 sin cambiar una letra |
| `sonda_posix.py` | N4: siete primitivos × cinco estados + coste + censo de `/proc`. `--medir-ruta` mide una ruta suelta (es el lado WSL2 del cruce) |
| `prueba_posix.py` | el cuerpo POSIX de `pruebas/test_watcher_n.py::CerrojoPosix`. Usa la función del watcher de verdad, no una copia |
| `cruce_win.py` | N4: las cuatro celdas del cruce Windows↔WSL2, con control positivo en las dos direcciones |
| `sonda_incompletos.py` | N5: matriz de defensas, falsos positivos, bytes vistos y el extremo a extremo con el `Vigilante` en cinco configuraciones |
| `sonda_residuo.py` | N5: el residuo. Fabrica el `mp3 -write_xing 0` que el corpus no tiene |
| `hijo_convierte.py` | un `filex` de verdad que convierte y se deja matar (`LISTO`/`ARRANCA`/`FIN`) |
| `hijo_desechable.py` | un `filex` vivo con su desechable y **el fichero ya cerrado** — la ventana de §3.4 |
| `sonda_desechables.py` | N14: daño, barrido bueno, barrido ingenuo, coste y control negativo |
| `sonda_ventana.py` | N14: el primitivo `rmtree` aislado (Windows vs WSL2) y la ventana del fichero cerrado |
| `censo_temp.py` | N14: censo del `%TEMP%` real. **Solo lectura** |
| `coste_defensas.py` | coste de las tres defensas **tal como quedaron en `filex/watcher.py`** |

## Logs

`logs/posix_tmpfs.log`, `logs/posix_drvfs.log`, `logs/cruce.log`,
`logs/incompletos.log`, `logs/residuo.log`, `logs/desechables.log`,
`logs/ventana.log` — celda a celda, con la `condicion_ok` de cada una.
