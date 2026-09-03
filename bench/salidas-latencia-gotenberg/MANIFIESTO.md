# MANIFIESTO — `bench/salidas-latencia-gotenberg/`

Salidas de `C35` (ronda 10, worker2): la latencia limpia n≥9 con testigos que
`bench/gotenberg-y-mcp.md` dejó PENDIENTE. Ver `bench/oraculo-y-gotenberg.md` §2.

## Ficheros

| Fichero | Tamaño | sha256 | Orden |
|---|---:|---|---|
| `medir_latencia.py` | 7 719 B | `c6b27b643ac318d99dcfa3fcd97c08b40ff40d48e2b11a1b078e65e381667aec` | `python bench/salidas-latencia-gotenberg/medir_latencia.py` |
| `resultado.json` | 3 125 B | `477194d52df30926bb9ef93dc817f7222864b7117d7e261c0439e614b30e6841` | salida de la orden anterior |

## Notas

- `n=11` por vía, `txt → pdf` por LibreOffice en las dos (mismo motor subyacente en
  Gotenberg y en `filex-c13`, para que la diferencia medida sea la arquitectura —
  servicio vivo contra contenedor efímero por conversión — no el motor).
- **No reimplementa el `argv` de `docker run` a mano**: llama a `filex.nucleo.FileX.
  convertir()` de verdad (trampa 79), con una única instancia de `FileX` construida
  una vez y reutilizada, igual que hace `filex/api.py` en producción.
- Los PDF de salida de cada conversión se escriben en un directorio temporal que el
  propio script crea y borra (`shutil.rmtree` en el `finally`); no se versiona
  ninguno. `docker ps -a` antes/después confirma 0 huérfanos de esta tanda (trampa 37).
