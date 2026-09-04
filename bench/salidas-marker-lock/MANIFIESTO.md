# Salidas de `bench/marker-con-lock.md` — B3 con el lock de GPU tomado

Carril `gpu/`, ronda 14, worker1. Rama `gpu/marker-con-lock`.

**Todo lo de este directorio es texto** (scripts, JSON y logs), que es lo que `CLAUDE.md` §6
manda versionar. **No hay ningún binario**: el intento 1 no produjo `.md` de salida —ese es su
resultado— y los desechables se borran solos al terminar cada tanda.

---

## Cómo se reproduce cada fichero

### Requisitos comunes

- Intérprete: **`D:\Work\research\FileX\.venv-marker\Scripts\python.exe`** (Windows, 3.11.9).
  El venv está **protegido** (`CLAUDE.md` §1): estos scripts sólo EJECUTAN lo ya instalado y
  no instalan nada. `filex` se importa por `sys.path`, no se instala en el venv.
- Entrada: `corpus/pdf/tipico_texto.pdf`, **3 219 B** tras `git lfs checkout` (trampa 34; el
  arnés comprueba el **tamaño**, no la existencia — trampa 107).
- `PYTHONIOENCODING=utf-8` si la consola es cp1252.
- **Cada tanda toma el lock de GPU** con `filex.gpu.Lock.tomar()`/`soltar()`.

| Fichero | `sha256` | Bytes | Orden exacta que lo reproduce |
|---|---|---|---|
| `medir_marker_lock.py` | `93adb1dc90e48f5a4e052fd1e5f2f774c9a02a76416e016981b21ad9d1a3abde` | 21018 | fuente (copia propia de `bench/salidas-suelo-n32/medir_marker.py`, `CLAUDE.md` §1) |
| `sonda_vllm.py` | `19c6b75a693ee0fdb19fd029ccacd452ece2b07d4715766aab8ca0eedff1d33a` | 7833 | fuente |
| `medir_lock.py` | `367d18f4dd7bfd68216f97c9601f352dfcc46af015d325b4d44fa730794f1edf` | 2635 | fuente |
| `hacer_manifiesto.py` | `e429332e5e397eb35122ba8dd50979f2f3dc7802df5e532e7ad6c98b9911f322` | 994 | fuente (genera la columna `sha256` de esta tabla) |
| `resultado_i1.json` | `a89a9dcd88f39ce26ae7b28b644293e48430acf5527b5d980f4ab0a39d07988a` | 12995 | `python bench/salidas-marker-lock/medir_marker_lock.py --etiqueta i1 --tope 1500 --espera-lock 300` |
| `log_i1.txt` | `115ed62d37156f75433b74357185296791167f45ab2b8e0b196f2e8ee7d97a5e` | 1344 | (lo escribe la misma orden de arriba) |
| `resultado_sonda_vllm.json` | `9dc1ff02657865248bc338c2fdf208c4c0905638b8595f7c3871e74a2147c6b2` | 6129 | `python bench/salidas-marker-lock/sonda_vllm.py` |
| `log_contenedor_sonda.txt` | `31e379a71d1e7c2a4cc29abbbec7e34898bc3f54debfe21275d1e9d8a312095c` | 20282 | (lo escribe la misma orden: es `docker logs -f` grabado en continuo) |
| `resultado_lock.json` | `910ea5bdda2c54d318a7cb4c397c30eb2893a981325600dd8f89d35e891e1af5` | 417 | `GPU_LOCK=%TEMP%/filex-gpu-CONTROL-w1.lock python bench/salidas-marker-lock/medir_lock.py` |

---

## Advertencias de reproducción

1. **Los `sha256` de los `.json` y los `.txt` NO son estables entre ejecuciones.** Llevan
   marcas de tiempo, PID, nombres de contenedor con `epoch`, puertos y series de VRAM. Los
   hashes identifican **estas** salidas, no un resultado esperado. Lo reproducible es el
   **veredicto**: `rc=1`, sin `.md`, `ExitCode=1` del contenedor y el `RuntimeError` del driver.

2. **`resultado_i1.json` tarda 643,87 s en producirse**, y la mayor parte es
   `SURYA_INFERENCE_STARTUP_TIMEOUT=600` esperando el `/health` de un contenedor **que ya
   murió**. No es un cuelgue del arnés.

3. **`log_contenedor_sonda.txt` sólo existe porque la sonda lanza el contenedor SIN `--rm`.**
   Con la orden original de surya (`--rm`) el contenedor se borra al morir y sus logs se
   pierden — le pasa al propio `surya` (`spawn.py:141-151` devuelve `No such container`) y me
   pasó a mí antes de escribir la sonda. Es la razón de ser de este fichero.

4. **La sonda deja el contenedor sin `--rm`, así que SE BORRA A MANO.** Lo hace ella en su
   `finally` con `docker rm -f` (nunca `docker kill`: sobre un contenedor `Created` falla —
   trampa 37), y comprueba después con `docker ps -a` que no sobrevive. Si la sonda muriera a
   media ejecución, quedaría un contenedor `filex-b3-sonda-<epoch>` que hay que borrar con
   `docker rm -f`.

5. **`medir_lock.py` usa `GPU_LOCK` para apuntar a un fichero de CONTROL.** Sin esa variable
   tomaría y soltaría el lock real 18 veces seguidas, molestando a quien esté midiendo.

6. **Ninguna de estas órdenes reproduce el `.md` de `marker`**, porque no lo hubo. Si alguien lo
   consigue —actualizando el driver, o con una imagen `cu12x` en `VLLM_DOCKER_IMAGE`—, la
   comparación de calidad la da la lista `ESPERADO` y el evaluador CER que ya están dentro de
   `medir_marker_lock.py`, heredados sin tocar de `bench/salidas-suelo-n32/medir_marker.py`.
