# MANIFIESTO — `bench/salidas-fate-y-aristas/`

Salidas de la ronda 11 (worker2): `C28`-barato (los 8 `sin_clasificar` y 17 de las 23
"con invocación mejor") y `C16` (muestra estratificada con el corpus FATE). Ver
`bench/fate-y-aristas.md`.

**El corpus FATE (`D:\Work\research\fate-suite`, 1,3 GB) no se copia ni se versiona**,
tal como pide el encargo — los scripts de C16 lo referencian por ruta absoluta y no
escriben nada dentro de él.

## Ficheros

| Fichero | Tamaño | sha256 | Orden |
|---|---:|---|---|
| `c28_8_sin_clasificar.py` | 3 564 B | `9c68ef59a2a1682d56cdab7eca0fd1888c5b5d1b173644648dc747da495f40c5` | `python bench/salidas-fate-y-aristas/c28_8_sin_clasificar.py` |
| `c28_8_resultado.json` | 4 988 B | `07f4b84a8eccda87e5ed4cdfc5952e0a9af12e890ee6529a7bc72013205c2a7e` | salida de la orden anterior |
| `c28_17_invocacion.py` | 9 491 B | `178d2b35ae0572c12d489efea6fb9e22f7e47ebd49e4a50205419be3d07abe95` | `python bench/salidas-fate-y-aristas/c28_17_invocacion.py` |
| `c28_17_resultado.json` | 9 244 B | `d080f3c9bd8d55a4aacbaeac074ee494e817df66ea4f7d187c3311da09ecbaa1` | salida de la orden anterior |
| `c16_semi_entrada_fate.py` | 6 509 B | `9f40c873a8fdd46f048bf22ed9ee2801a09fb1c460f5b2fcb6a87494e48cb316` | `python bench/salidas-fate-y-aristas/c16_semi_entrada_fate.py` (exige `D:\Work\research\fate-suite`) |
| `c16_semi_entrada_fate_resultado.json` | 23 404 B | `33282dc3802ba85cb7f1becbe1558ffa56498178b0dd5d05d9a2a60eccbf9795` | salida de la orden anterior |
| `c16_muestra_aristas_fate.py` | 4 989 B | `77de8c6cfbeb74f315214f87a4be806f6e03989d6ef91958b4d555d0d8fe7cf1` | `python bench/salidas-fate-y-aristas/c16_muestra_aristas_fate.py` (lee el resultado anterior) |
| `c16_muestra_aristas_fate_resultado.json` | 59 742 B | `a99d2ab8b87daf8c20ba738e488df791cbb4f1cac9c87ad42b673be959f6ea12` | salida de la orden anterior |

## Notas

- Sin binarios: los directorios temporales de cada script se crean y se borran al
  terminar (`tmp8/`, `tmp16/`, `tmp16b/`, `tmp17/`), y ninguno queda en disco.
- `c28_17_invocacion.py` reconstruye el `argv` que hace falta para cada uno de los 17
  formatos a mano (sondeado en ejecución con `ffmpeg -h muxer=X`/`-h encoder=X` antes
  de escribir el script, no deducido); las dos aristas `rco`/`tco` reutilizan el fix
  de `g723_1` de `bench/salidas-c25-grafos/` (ronda 9).
- `c16_semi_entrada_fate.py` empareja los 445 formatos `no_materializable` de
  `bench/salidas-aristas/semi_entrada.json`/`semi_entrada2.json` contra los
  subdirectorios de FATE por coincidencia de NOMBRE — 69 de 445 (68 ffmpeg + 1
  ImageMagick). Es un sesgo de cobertura declarado en el informe, no un muestreo
  aleatorio sobre los 445.
- `c16_muestra_aristas_fate.py` depende del `.json` que escribe el script anterior
  (lee `c16_semi_entrada_fate_resultado.json` del mismo directorio).
