# MANIFIESTO — `bench/salidas-patron-multi/`

C41. Informe: **`bench/patron-multifichero.md`** (commit `8765303`, 31/08
11:10, "WIP N28/C22"). Su sección "## Salidas reproducibles" ya trae la
tabla completa; este manifiesto la reproduce en el directorio y confirma los
hashes contra el árbol actual.

**MEDIDO** (`sha256sum`/`stat`, 01/09/2026 — coinciden exactamente con el
informe).

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `reproducir.py` | 5 343 | `2431a67b6ccb4780bfdafa8fd1520312dc8d32bed7035171378ed20b4f95374f` | fuente |
| `resultado.json` | 9 756 | `6945f7b51b5fb32859349eef1973c0e1e9f59716681e1efe5a31dfac7d8c209f` | `python3 bench/salidas-patron-multi/reproducir.py`; tope explícito de 180 s por celda |

Cada celda registra `rc`, bytes, orden y `stderr`; se acepta como buena sólo
con `rc == 0` y bytes positivos.

## Nota de veracidad — qué conclusión de este informe sigue vigente

Este informe mide **dos pendientes en la misma tanda, con destinos distintos**:

- **N28** (sección propia del informe): propone descontar
  `n_audio × bitrate_audio_bps` en V10. **SUPERADO/REFUTADO** por el informe
  posterior `bench/bitrate-por-pista.md` (commit `d2bcb7b`, mismo día 31/08,
  13:27 — dos horas más tarde): esa resta puede sobreestimar el vídeo cuando
  `-b:a` pedido queda por debajo de lo obtenido, así que se retiró de `V10` y
  de `decidido`. El inventario cita `bitrate-por-pista.md` para N28, no este
  fichero — correcto, verificado en esta misma auditoría.
- **C22** (sección propia del informe): el criterio de "salida multifichero
  legítima" (HLS `.m3u8` + secuencia `%03d`), con 0 falsos positivos sobre el
  patrón oro. **Este informe SIGUE siendo la evidencia vigente de C22** — no
  lo toca ni lo contradice `bitrate-por-pista.md`, que sólo habla de N28 y
  C25. El código (`DESTINOS_MULTIFICHERO`, `censar_dir` en
  `filex/verificador.py`) sigue intacto en el árbol.
