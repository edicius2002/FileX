# MANIFIESTO — `bench/salidas-oraculo-n9/`

Salidas de `N9` (ronda 10, worker2): mide el oráculo temporal de R4 (trampa 28) en esta
máquina y verifica el suelo `ecualizar_temporal` de `Confinamiento.resolver()`. Ver
`bench/oraculo-y-gotenberg.md` §1.

## Ficheros

| Fichero | Tamaño | sha256 | Orden |
|---|---:|---|---|
| `medir_oraculo.py` | 5 381 B | `dbb4ff1039c549a2873272b78745bee5285facdc334c2374640aae8d76178bd7` | `python bench/salidas-oraculo-n9/medir_oraculo.py` |
| `resultado.json` | 1 123 B | `66d914fb4e5cbfb4835ee4d34c4f1ff568dd11cf5dd50b1c2340676a2cce077b` | salida de la orden anterior |
| `medir_convertir.py` | 3 886 B | `babee895f35a5d4000835d4d7c3d57af0f9639e42393658fc4bda80e9c2b63a6` | `python bench/salidas-oraculo-n9/medir_convertir.py` |
| `resultado_convertir.json` | 567 B | `ab57003bbc571b6529f5ca2d5e16c6880176476b50b01bcd4ae7413cbf7b10fd` | salida de la orden anterior |

## Notas

- `medir_oraculo.py` mide `Confinamiento.resolver()` en aislado (n=2000 por celda,
  in-process): reproduce la asimetría de trampa 28 en esta máquina (ratio 12,75× a
  17,53× según la tanda; no comparable con el ×20,6 de `D:`) y confirma que el suelo
  ecualizado converge las tres vías a la misma mediana (ratio→1,00).
- `medir_convertir.py` mide al nivel de `FileX.convertir()`, que llama a
  `Confinamiento.resolver()` DOS veces (entrada + directorio de salida). Documenta el
  residuo de ~2,1× entre «prohibido» (una sola llamada, corta antes) y «válido» (dos
  llamadas) que el suelo no cierra — y que sí cierra el oráculo de EXISTENCIA
  («no existe» vs «existe» convergen a 0,985×, prácticamente 1).
- Sin binarios: los directorios temporales de cada tanda se crean y se borran dentro
  del propio script.
