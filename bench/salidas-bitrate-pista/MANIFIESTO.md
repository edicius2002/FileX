# MANIFIESTO — `bench/salidas-bitrate-pista/`

C41. Informe: **`bench/bitrate-por-pista.md`** (N28, segunda vía — sustituye
al enfoque de `bench/salidas-cota-audio/` y `bench/salidas-patron-multi/`
sobre el mismo N28, ver `MANIFIESTO.md` de ese directorio para la cronología)
y C25 (segunda y tercera pasada). Su sección "## Salidas" ya trae la tabla
completa; este manifiesto la reproduce en el directorio y confirma los hashes
contra el árbol actual.

**MEDIDO** (`sha256sum`/`stat`, 01/09/2026 — coinciden exactamente con
`bench/bitrate-por-pista.md`).

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `sondar.py` | 2 826 | `c8158c35b1004385971b872f3c1e2de7ef70a30f9e266af24c527ceb12a4651a` | fuente |
| `resultado.json` | 69 905 | `682a76a6b3d27e7f4bd1005c095eae042f873fce64083f05aea4aabbe911d1ca` | `python bench/salidas-bitrate-pista/sondar.py` desde Git Bash |
| `reintento_c25.py` | 5 038 | `0f5dbebc4584c6d59eee0557a29e265a10c00898a738c250b14ff3a84ee82e1a` | fuente; `--clasificar` no reejecuta ffmpeg |
| `c25-segunda-pasada.json` | 19 703 | `f1ab471bf98688a2fbd9cc055ea79dc52778a4e12b003f1fdc3fb11e0bdcaa8e` | `python bench/salidas-bitrate-pista/reintento_c25.py` desde Git Bash — reejecuta las 15 filas cuyo `err` contiene `received no packets` con `-t 8` y timeout exterior de 20 s |
| `c25-clases.json` | 6 509 | `d5625aca72dfdabe746b78f09f04f832d4f9de59c55a1fc8a63dad85d7378fd4` | `python bench/salidas-bitrate-pista/reintento_c25.py --clasificar` — clasificación posterior de las 15 salidas anteriores por `rc`; no ejecuta ffmpeg |

No se versionaron binarios regenerables; cada celda conserva orden, `rc`,
bytes y `stderr`.
