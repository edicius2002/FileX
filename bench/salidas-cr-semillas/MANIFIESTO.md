# MANIFIESTO — CR-010

Informe: `bench/salidas-cr-semillas/INFORME-CR-010.md`.

Todos los artefactos son texto pequeño y reproducible. No se conserva ningún binario ni
corpus. Los hashes siguientes se obtienen sobre los bytes versionados; el manifiesto no
se autorreferencia.

| Fichero | Bytes | SHA-256 | Reproducción |
|---|---:|---|---|
| `indice-semillas.json` | 160881 | `c4eb1733e5deef879557a6418d9f0d423a51093f17ea1b778cfecea77bba1b9c` | `python -B -X utf8 generar_indice.py` |
| `generar_indice.py` | 12273 | `9a9faffd30123c8c126f869352a48512d300d4254e6477dfc38c664f24af2566` | fuente mantenida |
| `test_indice_semillas.py` | 4452 | `c55f9246235be506cc8df53b2beb82e64d63c6170ad78592bfa6d5bdf5abe4c7` | fuente mantenida |
| `INFORME-CR-010.md` | — | — | síntesis humana de `indice-semillas.json` |

Órdenes de verificación desde la raíz:

```powershell
python -B -X utf8 bench/salidas-cr-semillas/test_indice_semillas.py
python -B -X utf8 bench/salidas-cr-semillas/generar_indice.py --comprobar
```
