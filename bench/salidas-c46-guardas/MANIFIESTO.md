# MANIFIESTO — `bench/salidas-c46-guardas/`

worker9, carril CPU/Docker. Datos crudos de `bench/cierre-watcher-y-acuerdo.md` §1 (`C46`):
remedición del acuerdo `spa`/`eng` (`bench/acuerdo-y-cruce.md` §2) con las dos guardas que el
informe original dejó pendientes. Regla §6 de `CLAUDE.md`: nombre, tamaño, sha256, orden exacta.

Los rásteres PNG (11 MB, regenerables, deterministas) se han borrado tras medir; queda su orden
en `_c46_guardas.py::rasterizar()`. Los `.txt` de salida de Tesseract **sí se versionan**: son
texto barato (CLAUDE.md §6) y permiten releer el error exacto (reordenamiento en `d2`,
alucinación en `d4`) sin volver a lanzar Docker.

Orden completa (Docker levantado, imagen `filex-c13:latest` ya presente,
`magick.exe` de ImageMagick 7.1.2-21 en el PATH del sistema):

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-c46-guardas/_c46_guardas.py
```

## Ficheros

| Fichero | Bytes | SHA-256 (primeros/últimos 8) |
|---|---:|---|
| `_c46_guardas.py` | 10179 | `4dd5536f…d027` |
| `acuerdo_c46.json` | 3066 | `3e2ae8c6…4ef5` |
| `patologico_escaneado_200ppp_spa.txt` / `_eng.txt` | 83 / 83 | `b7c05f48…6cf9` (idénticos entre sí, e idénticos byte a byte a los de `bench/salidas-acuerdo-y-cruce/` — Tesseract 5.5.0 standalone es determinista sobre el mismo ráster) |
| `escaneado_d1_150ppp_spa.txt` / `_eng.txt` | 84 / 84 | `f5593ee4…9139` (idénticos entre sí y con la ronda 7) |
| `escaneado_d2_100ppp_spa.txt` | 90 | `515748f3…d560` |
| `escaneado_d2_100ppp_eng.txt` | 88 | `7b042398…6a25` |
| `escaneado_d3_100ppp_spa.txt` / `_eng.txt` | 0 / 0 | `e3b0c442…8558` (sha del vacío — silencio, guarda 1 lo atrapa ahora) |
| `escaneado_d4a_200ppp_spa.txt` | 615 | `26503416…d91` |
| `escaneado_d4a_200ppp_eng.txt` | 621 | `95f5ff17…ec6` |
| `escaneado_d4c_200ppp_spa.txt` | 611 | `92de9e84…0a2` |
| `escaneado_d4c_200ppp_eng.txt` | 615 | `b083d56c…91` |
| `escaneado_d4_200ppp_spa.txt` | 358 | `605778d4…18b` |
| `escaneado_d4_200ppp_eng.txt` | 347 | `e7fb155d…5c5` |
| `escaneado_d4e_200ppp_spa.txt` / `_eng.txt` | 0 / 0 | `e3b0c442…8558` (vacío otra vez — guarda 1) |

Rásteres (borrados, se reproducen así, mismos ppp nativos que la ronda 7): `magick -density
<ppp> corpus/pdf/<doc>.pdf[0] -units PixelsPerInch -flatten <doc>_<ppp>ppp.png`.

**Verificación de determinismo, de propina**: los `sha256` de las cinco salidas que se solapan
con `bench/salidas-acuerdo-y-cruce/` (ronda 7) son **idénticos byte a byte**, en una máquina
distinta ejecución y con Docker recién arrancado — confirma que Tesseract 5.5.0 standalone
dentro de `filex-c13` es determinista sobre el mismo ráster, tal como asumía el método original.
