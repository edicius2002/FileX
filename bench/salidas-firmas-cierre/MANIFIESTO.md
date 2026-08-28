# Manifiesto — salidas de F2 (`bench/firmas-cierre.md`)

**Generado:** 2026-08-28 · **Ficheros:** 53 (21 `.json`, 21 `.py`, 11 logs) · **Peso:** 1336.5 KB · **todo texto, nada binario**

Los binarios —las 53 del patrón oro regeneradas (204,9 MB), las 345 salidas locales y las 864 celdas del contenedor— viven en un directorio desechable **fuera del repositorio** y se borran al terminar. Aquí solo hay texto.

En las órdenes, `<TMP>`, `<ANCHA>`, `<REF53>` y `<C30>` son directorios desechables cualesquiera; los que se usaron fueron
`%TEMP%\claude\...\scratchpad\F2_TMP`, `%TEMP%\claude\...\scratchpad\F2_ANCHA`, `%TEMP%\claude\...\scratchpad\REF53` y `%TEMP%\claude\...\scratchpad\F2_C30`.


## Resultados (`.json`)

| Fichero | Bytes | sha256 | Qué es | Orden exacta |
|---|---:|---|---|---|
| `c28_banner.json` | 5901 | `5ac790e832665846…` | los 17 «banner del escritor», con su prefijo y sus escritores | `python bench/salidas-firmas-cierre/_c28_banner.py` |
| `c28_censo.json` | 18958 | `4fef91c5fee204dc…` | los 86 indeterminados, con sus escritores reales | `python bench/salidas-firmas-cierre/_c28_censo.py` |
| `c28_huerfanas.json` | 438 | `c33138cfd4ad8ff1…` | firmas que la sonda sabe dar y ninguna extension acepta | `python bench/salidas-firmas-cierre/_c28_huerfanas.py` |
| `c28_los56.json` | 9515 | `e60b5f834bace2b7…` | los 56 inescribibles, clasificados por su `rc` | `python bench/salidas-firmas-cierre/_c28_los56.py` |
| `c28_motivos.json` | 1872 | `062b134149703981…` | el reparto real de los 86: 56 / 17 / 13 | `python bench/salidas-firmas-cierre/_c28_motivos.py` |
| `c28_prueba21.json` | 2857 | `c90104817d136da9…` | 6 de ellos escritos DE VERDAD con la invocacion correcta | `python bench/salidas-firmas-cierre/_c28_prueba21.py <TMP>` |
| `c30_contenedor.json` | 462274 | `bfe1763a2daee29c…` | 864 celdas dentro de filex-c13, primera pasada | `python bench/salidas-firmas-cierre/_c30_escribe.py <C30>   (primera pasada, verificador 1812df12...)` |
| `c30_contenedor_v2.json` | 398829 | `d44f88161db933c2…` | las mismas 864 celdas con los cuatro arreglos puestos | `python bench/salidas-firmas-cierre/_c30_escribe.py <C30>   (segunda pasada, verificador c023a9bc...)` |
| `c30_triaje.json` | 21364 | `32ba4237c124efdf…` | triaje con testigo externo: falso positivo frente a captura legitima | `python bench/salidas-firmas-cierre/_c30_triaje.py <C30>` |
| `c37_ancha_local.json` | 145766 | `bf01d214055e990c…` | 345 salidas locales legitimas, evaluadas con HEAD y con el arbol | `python bench/salidas-firmas-cierre/_c37_ancha_local.py <ANCHA>` |
| `c37_bucles.json` | 400 | `93bb73e26d8a657c…` | busqueda del defecto de la trampa 48 en 8 modulos, con control positivo | `python bench/salidas-firmas-cierre/_c37_bucles.py` |
| `c37_caducidad.json` | 1160 | `26ec3f8aa2392235…` | que aristas caduca el cambio (172) y cuantas puede mover (0) | `python bench/salidas-firmas-cierre/_c37_caducidad.py` |
| `c37_coste.json` | 1303 | `7c9c0d0ae51dea34…` | coste de la ventana larga: primitivo aislado, firma_real pareada, y disparo | `python bench/salidas-firmas-cierre/_c37_coste.py <TMP>` |
| `c37_deuda12.json` | 5947 | `80f3a947bef9ab22…` | los 12 de la deuda de firmas, con su prefijo comun y su n | `python bench/salidas-firmas-cierre/_c37_deuda12.py` |
| `c37_reproduce_antes.json` | 2136 | `73c88c4a721a3cbc…` | la medida de firmas-contrato.md 3.2/10.3, reproducida sobre HEAD | `git stash && python bench/salidas-firmas-cierre/_c37_reproduce.py <TMP>` |
| `c37_reproduce_despues.json` | 1736 | `3b4520627ca4efdc…` | la misma, con el arreglo puesto | `python bench/salidas-firmas-cierre/_c37_reproduce.py <TMP>` |
| `muestra_pict_pcd.json` | 45544 | `8f54d112ae8f882f…` | censo de 3 semillas: donde esta el marcador de PICT y de PCD | `python bench/salidas-firmas-cierre/_muestra_pict_pcd.py <TMP>` |
| `regenera53.json` | 44778 | `0ae8698e0c263277…` | las 53 del patron oro regeneradas fuera del repo, con su sha256 | `python bench/salidas-firmas-cierre/_regenera53.py <REF53>` |
| `regresion_antes.json` | 17453 | `32538ae4f226df1b…` | contrato + fidelidad sobre las 53, con el verificador de HEAD | `F2_REF53=<REF53> python bench/salidas-firmas-cierre/_regresion_53_f2.py --antes` |
| `regresion_despues.json` | 17453 | `6a79992229bdfffc…` | lo mismo con el del arbol de trabajo | `F2_REF53=<REF53> python bench/salidas-firmas-cierre/_regresion_53_f2.py` |
| `vocabulario_f2.json` | 1673 | `06c24741d94e54c1…` | las tablas del vocabulario, con tamano Y con elementos | `python bench/salidas-firmas-cierre/_vocabulario_f2.py` |

## Instrumentos (`.py`)

| Fichero | Bytes | sha256 |
|---|---:|---|
| `_c28_banner.py` | 4010 | `41347ba53ddbef28…` |
| `_c28_censo.py` | 3118 | `31983a619fcdced1…` |
| `_c28_huerfanas.py` | 2462 | `a52d2ada8c0e8243…` |
| `_c28_los56.py` | 5688 | `360ed21586bc127b…` |
| `_c28_motivos.py` | 2757 | `aeccd06746793b28…` |
| `_c28_prueba21.py` | 3691 | `fafe6d256be5274d…` |
| `_c30_cierra.py` | 8550 | `b3687d80f9d1d41b…` |
| `_c30_compara.py` | 4740 | `3999cc8bfc355c3b…` |
| `_c30_escribe.py` | 18961 | `7ce46d1edcbe1440…` |
| `_c30_triaje.py` | 5801 | `189c9bcaafa5b6bc…` |
| `_c37_ancha_local.py` | 6188 | `8c0f36b48a3287a3…` |
| `_c37_bucles.py` | 4809 | `39c8741856bd9ece…` |
| `_c37_caducidad.py` | 3253 | `7d2dce971362f0c7…` |
| `_c37_coste.py` | 7162 | `12a0ae9c70876d65…` |
| `_c37_deuda12.py` | 4077 | `7eb227cbee8a29aa…` |
| `_c37_reproduce.py` | 2808 | `5a52c6e9aeadc50c…` |
| `_manifiesto.py` | 7705 | `3c95d0e2b7840a84…` |
| `_muestra_pict_pcd.py` | 4039 | `3bc0f2efda954c2d…` |
| `_regenera53.py` | 23322 | `e7ba958f6939e5c5…` |
| `_regresion_53_f2.py` | 6368 | `7855ee113d2abda7…` |
| `_vocabulario_f2.py` | 2658 | `5a9680561f9a6089…` |

## Logs

| Fichero | Bytes |
|---|---:|
| `log-c30-compara.txt` | 1633 |
| `log-c30-dentro-v2.txt` | 2416 |
| `log-c30-dentro.txt` | 2419 |
| `log-c30-humo.txt` | 1519 |
| `log-c37-ancha.txt` | 0 |
| `log-c37-coste.txt` | 0 |
| `log-desechable-antes.txt` | 0 |
| `log-muestra.txt` | 0 |
| `log-reg53-antes.txt` | 5220 |
| `log-reg53-despues.txt` | 5224 |
| `log-regenera53.txt` | 10610 |

## Lo que NO está aquí, y dónde se regenera

- **Las 53 salidas del patrón oro** (204,9 MB): `python bench/salidas-firmas-cierre/_regenera53.py <REF53>`. 35 de 53 reproducen el `sha256` de `referencia.json`; las 18 que no, con su mecanismo, en `regenera53.json`.
- **Las 345 salidas locales**: las escribe `_c37_ancha_local.py` en `<ANCHA>` y no las borra, para poder evaluarlas dos veces con el mismo byte a byte.
- **Las 864 celdas del contenedor**: las escribe `_c30_escribe.py` dentro de `filex-c13` y las recoge en `<C30>`.
