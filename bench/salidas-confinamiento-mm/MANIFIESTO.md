# MANIFIESTO — `bench/salidas-confinamiento-mm/`

C41. Datos crudos de `bench/confinamiento-multimedia.md` (confinamiento de los tres MCP de
multimedia, TOCTOU en Linux/WSL2 y coste de validación de rutas en Python). Regla §6:
nombre, tamaño, sha256 y la orden exacta que reproduce cada fichero. Todo lo de abajo es
texto barato (`.py`, `.json`, `.log`, fixtures diminutas) — no hay binarios grandes que podar.

**MEDIDO** salvo donde se indique lo contrario.

## 1. Fuente escrita a mano (no se regenera, se edita)

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `gen_specs_mm.py` | 9384 | `62e3bda613498085763882a45a12f2faad67d0c5e396b89e8d1119347b78ee20` |
| `py-validacion/bench_validacion.py` | 24169 | `5f76f95206a198795feab1a1bea11da54709de8e10f5c3a25bf140fc5df82917` |
| `toctou-linux/toctou_probe_linux.py` | 7734 | `02c1b9e3aa32831bdead2a61f15d512c48027fef6043ce5f0177d2d472dfebd5` |

## 2. `specs/*.json` — generados por `gen_specs_mm.py`

Orden: `python gen_specs_mm.py` (venv `.venv-mm-ffmpeg`, ver §5).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `specs/A_ffmpeg.json` | 4321 | `1e94d5cc69851f8b31af3fcaf63b5297e8376b5c865876983255804e47aa458e` |
| `specs/B_video_audio.json` | 2530 | `f6c25408bc4f858e3baf2d700b402fb3689816c73b52c8dc2f1cff03f42710c7` |
| `specs/C_image_worker.json` | 3313 | `b1a8dc5df29297e620110f7340752b7f2fb93679bd82d10d5da99bf48b1dce94` |

## 3. Fixtures de entrada del sandbox (contenido literal, fijado a mano)

Descritas en `bench/confinamiento-multimedia.md` §1.2. `entrada.png:oculto` y
`secreto.txt:oculto` (flujos NTFS alternativos, `ADS_OCULTO_MM_777` / `ADS_OCULTO_FUERA_888`)
**no están versionados** — un ADS no sobrevive un `git add` normal en este árbol y el informe
ya lo declara así; no forman parte de este manifiesto porque `git ls-files` no los lista.

| Fichero | Bytes | SHA-256 | Orden |
|---|---:|---|---|
| `sandbox/raiz/video.mp4` | 13865 | `67ba7e307e309f973e464f9a265b148172302925652464cb02e528e93e68ee2e` | fixture de vídeo real, colocada a mano antes del ataque |
| `sandbox/raiz/video2.mp4` | 13888 | `935f1647e26010e809a6300c2ae0d291b2a20799e5a9e4536f7cdbec970f0c85` | ídem |
| `sandbox/raiz/entrada.png` | 531 | `2e34e6300fc3b94139636741f3c98bd4334ed7c2141ae9f6f291adbc7fac3984` | ídem |
| `sandbox/raiz/subs.srt` | 37 | `b47654b285b25adcf04490a18a4b19400871befd5ce46b7caa396e0fc363589d` | ídem |
| `sandbox/fuera/secreto.txt` | 54 | `19545b670a888ddf38f88e706e18aa0f3d50a33e67051992935c00f7d5b03005` | señuelo de texto, contenido fijo declarado en §1.2 |
| `sandbox/fuera/secreto.png` | 428 | `b2c975c49d0b6de20f56bca5e2f21efb9a61c14a0fffd2ba63a8db027d376cbc` | señuelo de imagen |
| `sandbox/fuera/video_fuera.mp4` | 2845 | `0c56329e0f05aed84f484c3f64d189c1ede376afc385e0b3080b9f57f6b91f6e` | señuelo de vídeo |

## 4. Salidas de la invocación real contra los tres MCP (fugas confirmadas y controles)

Estos ficheros son el **efecto secundario** de ejecutar los specs de §2 contra los tres
servidores vulnerables — no se generan por separado, se generan al correr el arnés del §5.
Cada uno corresponde a una fila de la tabla de ataques de `confinamiento-multimedia.md` §2
(citada entre paréntesis).

| Fichero | Bytes | SHA-256 | Fila del informe |
|---|---:|---|---|
| `sandbox/raiz/iw_control_out.png` | 982 | `548ac0fc09fbe820126149f8e02f9fe98c98539b6651ddbf3989484fb43db538` | IW-1 (control, dentro de la raíz) |
| `sandbox/raiz/video_converted.mp3` | 8897 | `73d5b0193594ef76cd09cc5189a891159e26cdf04d62ed5180d02d6e33318ce1` | FF-E1 (confinada por ausencia de parámetro) |
| `sandbox/fuera/iw_read_LEAK.png` | 566 | `86b88f7fda987e6f163898a7120072204c4c8e0839fdecf9d2615b501dbc96f6` | IW-2 (fuga de lectura+escritura) |
| `sandbox/fuera/iw_trav_LEAK.png` | 566 | `86b88f7fda987e6f163898a7120072204c4c8e0839fdecf9d2615b501dbc96f6` | IW-6 (travesía `..`) — mismo `sha256` que IW-2: mismo fichero fuente, misma fuga |
| `sandbox/fuera/iw_write_LEAK.png` | 833 | `ebd340a8131e16e84fe0ab3ea3d286136b12650f7e0d33a67aa06711f3da36b3` | IW-5 (escritura fuera de la raíz) |
| `sandbox/fuera/merged_LEAK.mp4` | 26411 | `9a3e0cd1bd37e0efac15407a1f602d516eba374ae6044c3f0565566c93e28c1b` | FF-E2 (`merge` con `output_path` arbitrario) |
| `sandbox/fuera/va_write_LEAK.mp3` | 8897 | `73d5b0193594ef76cd09cc5189a891159e26cdf04d62ed5180d02d6e33318ce1` | VA-4 (escritura fuera de la raíz); mismo `sha256` que `video_converted.mp3`: mismo audio origen, dos motores distintos lo producen igual |

Orden para regenerar **toda** la sección 3 y 4 (sandbox + specs + salidas): ver §5, con la
`$CLI` y `$PYFF`/`$PYVA` allí declaradas — es una única corrida por servidor, no operaciones
independientes por fichero.

## 5. `salidas/*.json` y `logs/*.stderr.log` — resultado crudo del arnés MCP

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `salidas/A_ffmpeg.json` | 30041 | `556b024280477b798c5bc954049aca04d233b8199bafc851f44871efe7f159e9` |
| `salidas/B_video_audio.json` | 61012 | `542307f8c0f23d0b8afbe257285942af68e49f21a14c71723012d229fb9c91cd` |
| `salidas/C_image_worker.json` | 15786 | `5811dd05ee1f87f9951fd1bc1497878f6ae2d11cdf7de0797be9bea510efcc6d` |
| `logs/ffmpeg.stderr.log` | 987 | `2ce0989db5bfe7b4c5a0e1e52a4df20f2784c9b7b40993e3d2f8feb7f173a33c` |
| `logs/image-worker.stderr.log` | 41 | `f1f1c90a968e198572d2a8c920454a5e70682d89053a6a795f5ed7f1c98740ad` |
| `logs/video-audio.stderr.log` | 1858 | `e569b95d3d8c099a045a719009852b58c73dc3ce33e6aaa1f6b3d94ad25d50e6` |

Orden completa (citada tal cual en `bench/confinamiento-multimedia.md` §7):

```sh
PYFF=D:/Work/research/FileX/.venv-mm-ffmpeg/Scripts/python.exe   # mcp<2 + (nada más)
PYVA=D:/Work/research/FileX/.venv-mm-vamcp/Scripts/python.exe    # mcp<2 + ffmpeg-python
CLI=D:/Work/research/FileX/.venv-mcp-md/Scripts/python.exe       # cliente (no modificar)
cd bench/salidas-confinamiento-mm
$PYFF gen_specs_mm.py
$CLI ../scripts/mcp_probe_bin.py specs/A_ffmpeg.json        salidas/A_ffmpeg.json
$CLI ../scripts/mcp_probe_bin.py specs/C_image_worker.json  salidas/C_image_worker.json
rm -f sandbox/fuera/va_*
timeout 180 $CLI ../scripts/mcp_probe_bin.py specs/B_video_audio.json salidas/B_video_audio.json
taskkill //F //IM ffmpeg.exe
```

**PENDIENTE (declarado, no bloqueante):** esta orden no se reejecutó en esta ronda. Dos motivos
concretos, no una suposición:

1. `gen_specs_mm.py` tiene la ruta base **grabada a fuego** (`BASE = "D:/Work/research/FileX/bench/salidas-confinamiento-mm"`, líneas 21-22): ejecutarla desde este *worktree* (`…/​.ccb/workspaces/worker2/…`) escribiría los `specs/*.json` apuntando al checkout principal, no a este árbol. Hay que editar `BASE` o ejecutar desde el clon principal.
2. Los venvs `.venv-mm-ffmpeg` y `.venv-mm-vamcp` que la orden necesita **ya no existen**: `CLAUDE.md` §2 los lista entre los borrados el 31/08 («eran los arneses de informes MCP ya cerrados y se rehacen con un `pip install`»). Rehacerlos exige clonar `repos/mcp-refs` (ya está, es clon de referencia) e instalar `ffmpeg-mcp-lite`/`video-audio-mcp` en un venv nuevo con `mcp<2`, tal como documenta `confinamiento-multimedia.md` §1.1 y §7 — reproducible en principio, con el coste de reinstalación declarado, no con una orden de una línea hoy.

## 6. `py-validacion/` — coste de validar rutas en Python

Orden: `python py-validacion/bench_validacion.py` (sin dependencias externas, solo `os.path` /
`ntpath` de la biblioteca estándar — no hereda el bloqueo de venvs de la sección 5).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `py-validacion/resultados.json` | 38356 | `ec5ccdbc2249aafdc0c2b619cd399e07d1bab0a162d44082e881b2600be93845` |
| `py-validacion/resultados.txt` | 19925 | `7e2d6d06fe0348bc96f52d413fd3f93a8e891e52f93b244161a52a5fe2521175` |

**PENDIENTE (declarado):** no reejecutado en esta ronda (§4 del informe advierte que el barrido
de `realpath` hasta 6000 componentes tarda hasta 16 s por celda; la tanda completa no es
instantánea). El código no depende de nada frágil ni pruned: `python py-validacion/bench_validacion.py`
debería bastar en cualquier Windows con Python 3.11+.

## 7. `toctou-linux/` — carrera TOCTOU repetida en WSL2/ext4

Orden: `python3 toctou_probe_linux.py` **dentro de WSL2**, sobre un sandbox en ext4 nativo bajo
`$HOME` (no `/mnt/d`, ver `confinamiento-multimedia.md` §3 — DrvFs sesgaría la medida).

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `toctou-linux/RESUMEN_toctou_linux.json` | 3308 | `30636b1a6582381b96516c08c7a6f9620680f74a9f1491173d74739b248198be` |
| `toctou-linux/calibracion_B.json` | 1109 | `699c606c6499ad24a94aab0fb9bbb3c94e44df7e91faeebac43ae4ffad657424` |
| `toctou-linux/grande_B.json` | 1478 | `42ce1d3d3fbb977a1883e14ba3e4e1b3b24fbeafb402ff95afa21eb0d071dfbb` |
| `toctou-linux/grande_B2.json` | 1328 | `a4525a53b7da22118947134810728a81bd2b9cafa60ea74badb0d4b192d6e2d3` |
| `toctou-linux/logs/toctou_B_carrera_normal.stderr.log` | 174 | `d180236f5aee26565e4c685040a8bc4f7b4b76659fab7868d6c63bc59bc18e2e` |
| `toctou-linux/logs/toctou_B2_carrera_ventana_ensanchada.stderr.log` | 437 | `348cc48d50ec1841730a679204bf506d8aa139539f6a2998adf91406579c4352` |

**PENDIENTE (declarado):** no reejecutado — la tanda `grande_B`/`grande_B2` mueve **51 200** y
**48 000** llamadas MCP (108 s y 76 s medidos en el informe original) y requiere Node dentro de
WSL2 más un cliente MCP en un venv Python propio de esa VM; es una carga real de máquina, no
una comprobación de segundos. El resultado es **no determinista por diseño** (es una carrera):
una reejecución dará cifras de "swaps"/"denegadas" distintas y el propio informe ya lo declara
como medida de una sola tanda, sin testigos de ruido — es correcto no perseguir bit-a-bit
idéntico aquí.

## Verificación de este manifiesto

`sha256sum` y tamaño de los 34 ficheros de `git ls-files bench/salidas-confinamiento-mm`
recalculados el 01/09/2026 contra el árbol de trabajo actual — **MEDIDO**, no copiado a ciegas
del informe original (que no traía una tabla de hashes propia; los cita aquí por primera vez).
