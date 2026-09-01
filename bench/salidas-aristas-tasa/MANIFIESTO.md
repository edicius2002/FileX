# MANIFIESTO — `bench/salidas-aristas-tasa/`

C41. Informe: **`bench/aristas-y-tasa-audio.md`** §"Salidas", que ya trae la
tabla completa; este manifiesto la reproduce en el directorio y confirma que
los hashes coinciden con el árbol actual (regla §6).

**MEDIDO** (`sha256sum`/`stat` verificados contra `bench/aristas-y-tasa-audio.md`,
01/09/2026 — coinciden exactamente).

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `medir.py` | 7 494 | `ffcbc750b39ff5ae05189db0375b59cdcacc225830fbc6d5ce188046ebdf9ba5` | fuente, escrito a mano |
| `resultado.json` | 62 355 | `cd3bf4acb01598901d7544ab5c7310b762a0e447176f6bfc1c8b41654d2c65f6` | `python bench/salidas-aristas-tasa/medir.py` desde Git Bash |

No se versionaron binarios. Cada celda del resultado registra orden, `rc`,
bytes, `stderr` y segundo intento si el primero falló (regla "dos intentos
por problema").
