# MANIFIESTO — `bench/salidas-c25-grafos/`

Salidas de `C25` (ronda 9, worker2): las 9 aristas candidatas a otra invocación del
grafo de filtros (`bench/bitrate-por-pista.md`, tercera pasada) y el pendiente 2 de
`bench/invocacion-aristas.md` §11 («la profundidad de los crudos de terceros»). Ver
`bench/psm-gs-y-crudos.md` §2 y §3.

No se versionan binarios: las dos entradas mínimas (`in/`, regenerada por
`c25_grafos.py`) y las salidas de prueba (`out/`, `out_crudos/`) se regeneran al
vuelo con las órdenes de abajo. Sólo se conservan los dos scripts y los dos `.json`
de resultado (texto barato, trazabilidad completa: `argv`, `rc`, bytes, `stderr`
citado y veredicto de `ffprobe`/RMSE por celda).

## Ficheros

| Fichero | Tamaño | sha256 | Orden que lo reproduce |
|---|---:|---|---|
| `c25_grafos.py` | 13 128 B | `e40b324c8178fdb23fee1053238d34870f2a3e34a981f3ebdfcdec8787475fd4` | `python bench/salidas-c25-grafos/c25_grafos.py` |
| `resultado_c25.json` | 12 371 B | `92ad4fa24ed1dc09e809df5e35808f2804b3ce539791d58f0beb7a73e46ff7cd` | salida de la orden anterior |
| `c25_crudos_terceros.py` | 5 466 B | `029d157b548ad9bfd7e78522e01d6f7f68c7a83e2d21073405c1fb9a02b3cf04` | `python bench/salidas-c25-grafos/c25_crudos_terceros.py` |
| `resultado_crudos_terceros.json` | 400 B | `ca3da6835f6d788e4f1d744ed9834fa717eba28fddbb1da31c57e81af079a9f4` | salida de la orden anterior |

## Notas

- `c25_grafos.py` **no** reutiliza `D:\Work\research\FileX\bench\salidas-invocacion\
  _p2_semillas.py` (raíz cableada a ese *worktree*, ajeno): regenera en
  `bench/salidas-c25-grafos/in/` los 9 crudos mínimos que hacen falta, con la misma
  receta de síntesis (`testsrc=352x288` + `sine`) que usa el arnés original para
  `video_cif`.
- `c25_crudos_terceros.py` escribe su crudo de 8 bits/canal con **ffmpeg**, no con
  ImageMagick — es la «otra procedencia» que el pendiente 2 pedía, no una
  simulación.
- Sin `sha256` de los binarios intermedios (se borran cada vez que se regeneran);
  el veredicto de cada uno vive en el `.json`, no en el fichero.
