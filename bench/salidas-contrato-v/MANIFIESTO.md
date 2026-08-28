# Manifiesto — salidas del agente V (C19, C21, C27, C29)

**Generado:** 2026-08-28 · **Informe:** `bench/contrato-familia-resvg.md`

**Todo lo que hay aquí es TEXTO y está versionado**: 18 ficheros, 192 KB. No hay
ni un byte binario.

Lo que **no** se versiona son los desechables que producen estos arneses, que
suman **836 MB** y se borran al terminar (§6 de `CLAUDE.md`):

| Desechable | Peso | Lo produce |
|---|---:|---|
| `%TEMP%\filex_v8` | 673 MB | `calibrar_v8.py` |
| `%TEMP%\filex_g6` | 148 MB | `medir_g6.py` |
| `%TEMP%\filex_a7_asim` | 8,9 MB | `calibrar_a7_asimetria.py` |
| `%TEMP%\filex_c19` | 3,6 MB | `fabricar_c19.py` |
| `%TEMP%\filex_a7_agresivo` | 2,8 MB | `calibrar_a7.py` |
| `%TEMP%\filex_a7_ciego` | 448 KB | `a7_margenes.py` |

Cada arnés los **lista antes y después** (R21) y guarda los dos censos en su JSON
(`censo_antes` / `censo_despues`). Ninguno dejó un fichero no declarado.

## Requisito previo

Las 53 salidas del patrón oro tienen que estar en
`bench/salidas-referencia/{audio,datos,imagen,pdf,video}`. No están versionadas;
`bench/salidas-referencia/MANIFIESTO.md` lleva las **39 órdenes exactas** que las
reproducen. Desde un *worktree*, además: `git lfs checkout` (trampa 34).

Motores: `ffmpeg` N-121159, ImageMagick 7.1.2-21 Q16-HDRI, Ghostscript 10.07,
contenedor `filex-convertx` en marcha. **Sin GPU.**

## Cómo se reproduce, en orden

```
python bench/salidas-contrato-v/fabricar_c19.py --antes   -> c19_antes.json
python bench/salidas-contrato-v/fabricar_c19.py           -> c19_despues.json
python bench/salidas-contrato-v/calibrar_a7.py            -> a7_calibracion.json
python bench/salidas-contrato-v/calibrar_a7_asimetria.py  -> a7_asimetria.json
python bench/salidas-contrato-v/a7_margenes.py            -> a7_margenes.json
python bench/salidas-contrato-v/calibrar_v8.py            -> v8_calibracion.json
python bench/salidas-contrato-v/medir_g6.py               -> g6.json
python bench/salidas-contrato-v/medir_familia.py          -> familia.json
python bench/salidas-contrato-v/regresion_53.py --antes   -> regresion_antes.json
python bench/salidas-contrato-v/regresion_53.py           -> regresion_despues.json
python bench/salidas-contrato-v/regresion_53.py --diff    (imprime; no escribe)
python -m pytest pruebas/test_contrato_v.py -q            (19 pruebas)
```

`a7_margenes.py` **lee** `a7_calibracion.json` y `a7_asimetria.json`, así que van
antes. `medir_familia.py` lee `g6.json` para su conjunto ancho.

`--antes` en `fabricar_c19.py` y en `regresion_53.py` carga el verificador con
`git show HEAD:filex/verificador.py`: la tabla del «antes» se regenera **después**
de aplicar el arreglo. Una comparación que no se puede volver a hacer no es una
comparación.

## Inventario

| Fichero | Bytes | sha256 |
|---|---:|---|
| `a7_asimetria.json` | 13068 | `2dec3eec4b2459b8…` |
| `a7_calibracion.json` | 21784 | `5cf887c1d0736e66…` |
| `a7_margenes.json` | 2465 | `184a7bb0e55468af…` |
| `a7_margenes.py` | 4792 | `2e617d6345d122a0…` |
| `c19_antes.json` | 5037 | `655a24b29365152c…` |
| `c19_despues.json` | 6473 | `4ff6e68b7ae177b6…` |
| `calibrar_a7.py` | 8801 | `b5196dee09d45d65…` |
| `calibrar_a7_asimetria.py` | 6446 | `59c1fc7e7f5f25d2…` |
| `calibrar_v8.py` | 6972 | `49e318add2f0eb12…` |
| `fabricar_c19.py` | 6798 | `416446f9b7911152…` |
| `familia.json` | 11157 | `15e9e567e906553d…` |
| `g6.json` | 30877 | `0317de899d3b0237…` |
| `medir_familia.py` | 5101 | `8278dc280df208f1…` |
| `medir_g6.py` | 14029 | `0b826162e843fac1…` |
| `regresion_53.py` | 5863 | `1d0cc47cf6da5123…` |
| `regresion_antes.json` | 17167 | `744b74ceb073713f…` |
| `regresion_despues.json` | 17453 | `1b3552d6e23ec249…` |
| `v8_calibracion.json` | 8642 | `fa79306b2b4b934f…` |

Los `sha256` de los `.json` **no son estables entre tandas** donde aparece un
tiempo (`a7_calibracion.json` lleva las medianas de `astats`,
`regresion_*.json` lleva `total_ms`). Los veredictos y los niveles en dB sí son
deterministas y se reproducen al centésimo; es lo que hay que comparar.

## Aviso sobre `medir_g6.py`

Usa `docker exec` sobre `filex-convertx`, que **ya tiene que estar en marcha**. No
crea ningún contenedor. El tope va **dentro** (`timeout -k 5 60`), y el censo de
`docker ps -a` —con `-a`, trampa 37— se guarda en `g6.json` antes y después:
6 contenedores antes, 6 después, **cero huérfanos**.
