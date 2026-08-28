# `bench/salidas-hito2/` — manifiesto

Agente **H2**, 28/08/2026. Hito 2 (NVENC con sondeo y degradación), B6 (el lote
sobre una carpeta real) y N7 (el lock de GPU dentro de `filex/`).

**Las salidas binarias NO se versionan.** Se borraron al terminar; lo que queda
son los `.py`, los `.json` de resultados y los logs, que son texto barato y son
la trazabilidad. Aquí está lo que hace falta para reproducir cada una.

## Cómo se reproduce todo

Requiere `ffmpeg` en el PATH, `nvidia-smi`, y el corpus con LFS resuelto
(`git lfs checkout`; `corpus/imagen/tipico.png` debe pesar **42 855 B**, no 130).
Todos los guiones toman el lock de GPU de `bench/lib/harness.sh` y lo sueltan.

| Orden (desde la raíz del repositorio) | Qué produce | Cuánto tarda |
|---|---|---|
| `bash bench/salidas-hito2/sonda_nvenc.sh` | `desechable/*.mkv`, `desechable/salida_*.log` | ~5 s |
| `python bench/salidas-hito2/sonda_rc.py` | `sonda_rc.json` (20 celdas: 5 códecs × 4 destinos) | ~30 s |
| `python bench/salidas-hito2/sonda_frames.py` | `sonda_frames.json` (24 celdas: 3 × 8 duraciones) | ~40 s |
| `python bench/salidas-hito2/sonda_geometria.py` | `sonda_geometria.json` (36 celdas: 3 × 12 tamaños) | ~60 s |
| `python bench/salidas-hito2/sonda_frontera.py` | `sonda_frontera.json` (bisección del mínimo por eje) | ~90 s |
| `python bench/salidas-hito2/matriz_tasa.py` | `matriz_tasa.json` (14 celdas: 7 códecs × 2 modos) | ~2 min |
| `python bench/salidas-hito2/medir_hito2.py suelta bitrate lote` | `medicion_hito2.json`, `log_campana.txt` | ~13 min |
| `python bench/salidas-hito2/medir_n7.py` | `medicion_n7.json` | ~7 min |
| `python bench/salidas-hito2/medir_b6_batch.py` | `medicion_b6_batch.json` | ~5 min |
| `python bench/salidas-hito2/medir_huella.py` | `huella_impacto.json` | ~3 s |

Los tres `dbg_*.py` son las sondas que destaparon que **`bash` a secas desde
Python es el `bash.exe` de WSL2 y no el Git Bash** (§5.1). Se conservan porque
sin ellas ese hallazgo no es reproducible:
`python bench/salidas-hito2/dbg_quebash.py`.

## Binarios BORRADOS, con su `sha256`

Los cuatro son de `sonda_nvenc.sh` sobre un `testsrc` sintético de 320×240 a
25 fps, 25 fotogramas — **no del corpus**, así que no hay nada que recuperar.
Son deterministas salvo por la marca de tiempo del contenedor Matroska, así que
el `sha256` **no** se reproduce bit a bit; el tamaño y el `rc` sí.

| Fichero | Bytes | `sha256` | Orden exacta |
|---|---:|---|---|
| `desechable/sal_av1_nvenc.mkv` | **0** | `e3b0c442…7852b855` (el del fichero vacío) | `ffmpeg -hide_banner -nostdin -y -f lavfi -i testsrc=size=320x240:rate=25 -frames:v 25 -c:v av1_nvenc -f matroska sal_av1_nvenc.mkv` → `rc=-542398533` |
| `desechable/sal_hevc_nvenc.mkv` | 48 270 | `dc5ac1a6…c3b38b58` | ídem con `-c:v hevc_nvenc` → `rc=0` |
| `desechable/sal_h264_nvenc.mkv` | 98 538 | `04f4b81d…8e353b5b` | ídem con `-c:v h264_nvenc` → `rc=0` |
| `desechable/sal_libsvtav1.mkv` | 7 530 | `f1582743…cd79cfeb` | ídem con `-c:v libsvtav1` → `rc=0` |

**El de 0 bytes es el dato, no un residuo.** `av1_nvenc` deja el fichero creado
y vacío, que es exactamente el caso de la trampa 25: sin registrar el `rc` no se
distingue de un silencio legítimo ni de un proceso que no arrancó.

Las salidas de vídeo de las campañas de medición (`medir_hito2.py`,
`medir_n7.py`, `medir_b6_batch.py`) nunca llegaron a este directorio: viven en
un `tempfile.mkdtemp()` que los propios guiones borran con `shutil.rmtree` al
terminar. Los `.json` guardan de cada una el tamaño, el bitrate real, el
veredicto del contrato y el `comment` que FileX le escribió dentro.
