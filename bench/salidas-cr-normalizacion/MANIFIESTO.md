# MANIFIESTO — CR-007

Informe: `bench/salidas-cr-normalizacion/INFORME-CR-007.md`.

Todos los artefactos son texto reproducible. No hay muestras, binarios ni salidas de
conversión. El manifiesto no se autorreferencia.

| Fichero | Bytes | SHA-256 | Reproducción |
|---|---:|---|---|
| `clasificacion.json` | 621307 | `07c6cac3d170cf24c5b316575965fe4cbc0c5eddb3464fcea8fa3e7db2bc9283` | `python -B -X utf8 generar_clasificacion.py` |
| `generar_clasificacion.py` | 10944 | `8c54b2c23393db7ad7e8385996b74074f704107bc641666ffcf5e47f9fc5a43c` | fuente mantenida |
| `test_clasificacion.py` | 4777 | `3a146a8683f8492dfae5e2b52d77e8da7e5fb67a2de60fceb8f67f9c52a3f8a1` | fuente mantenida |
| `INFORME-CR-007.md` | — | — | síntesis humana de `clasificacion.json` |

Órdenes de verificación desde la raíz:

```powershell
python -B -X utf8 bench/salidas-cr-normalizacion/test_clasificacion.py
python -B -X utf8 bench/salidas-cr-normalizacion/generar_clasificacion.py --comprobar
```
