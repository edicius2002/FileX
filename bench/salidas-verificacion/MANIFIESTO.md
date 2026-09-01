# MANIFIESTO — `bench/salidas-verificacion/`

Informe: **`bench/coste-verificacion.md`** (índice de datos crudos en su §9).
Todo el contenido es texto (`.py`/`.json`/`.txt`/`.log`) y se versiona entero
(regla §6): no hay binarios que podar — las conversiones que estos scripts
producen para medir se escriben en un directorio temporal y se borran solas.

**MEDIDO** (`sha256sum`/`wc -c` sobre el árbol en `ccb/worker2`, 01/09/2026).
Único commit del directorio: `f0a0858` ("Investigación del ecosistema de
conversión de archivos").

## Fuentes (escritas a mano, no regenerables — son el programa)

| Fichero | Tamaño (B) | SHA-256 |
|---|---:|---|
| `trabajos.py` | 7 887 | `caed92d6cc0ba350ca645ab01bfd35897070e248fd10c7e7bd08874614dbec71` |
| `medir.py` | 13 103 | `d5fc984852d206efa6b7eaa4bf74dc2a110d004a9d973fc98ecc202c063ab6d3` |
| `puntos.py` | 3 548 | `f6c599d2596615a4359e2cf5775b7f03d50328c2465111cff4195ce52b26cd81` |
| `convertir.py` | 4 656 | `3c043954451f5bfc7770374157d3818ec44ce9d42a3c44d44608df70debbffc3` |
| `conv_datos.py` | 1 645 | `c29c50450d7f0199b70d3361d6c643dabb79ebc78c5f72e463dc91daafb75a29` |
| `ratio.py` | 3 712 | `672e20ad372e5863df33dc626958318c4023922ad3056342a8fa6aa2c66e5dad` |
| `fallos.py` | 6 739 | `c90c9d2110e6df872b1a3c2a727f7a22ba3ee601e6265a287d799429048d4605` |

`trabajos.py` es una librería (`trabajos()`, `cargar_referencia()`) que
reconstruye las 53 salidas del patrón oro con su **pedido** —a partir de
`bench/salidas-referencia/referencia.json`, que no se toca (regla §1)—;
la importan `medir.py`, `puntos.py`, `ratio.py` y `fallos.py`. Todos hacen
`sys.path.insert(..., "bench/scripts")` e importan `verificador` de ahí
(`bench/scripts/verificador.py`, anterior a la mudanza a `filex/verificador.py`
de `bench/hito3-mudanza.md` — este informe es de una ronda anterior).

## Salidas generadas — orden exacta (leída del código)

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `correccion.json` | 27 641 | `f39406318ec9a2663821a4afb290cd35d5600478acbe498c00331123884478e6` | `python bench/salidas-verificacion/medir.py correccion` |
| `correccion.txt` | 1 112 | `8ce7247bad2b80881685c39978a68a70bcb60a34b507d9530026e14d9b02eae2` | mismo comando, stdout capturado: `python bench/salidas-verificacion/medir.py correccion > correccion.txt` |
| `unitario.json` | 10 563 | `f389fc3a8db060a71f9e6eaf617ef9aba5879618089d3ed75d066c26124160ec` | `python bench/salidas-verificacion/medir.py unitario` |
| `lote.json` | 6 527 | `2a0a144f411ba79297c9b45f371ce7428b7e58f6cb32f6852a2cbc4da44d047a` | `python bench/salidas-verificacion/medir.py lote` |
| `puntos.json` | 9 070 | `de336f013ddcc1a8c151f22ff8dc060f667b24c6d6c8bdfa675c4523920cf22e` | `python bench/salidas-verificacion/puntos.py` |
| `conversion.json` | 6 823 | `edda6c2942bce8186a9bd3453113f109ab7119a1b3b520465c804b2b77814491` | `python bench/salidas-verificacion/convertir.py` (ejecuta las 39 `ordenes` de `referencia.json`; las 3 de `datos` las relanza vía `python conv_datos.py <id> <entrada> <salida>`) |
| `conversion.log` | 4 938 | `c35a5f35682684bb9e3d63fc1c451f8211c2db82ebb0a0a669eef25312e911a4` | mismo comando, stdout capturado: `python bench/salidas-verificacion/convertir.py > conversion.log` |
| `ratio.json` | 25 584 | `f5c534443993891c6bfdbfac20d364ff8c8b1775178fb183bbd01ec9f10a604c` | `python bench/salidas-verificacion/ratio.py` — **requiere que `conversion.json` ya exista** (lo lee, no lo regenera) |
| `fallos.json` | 5 241 | `e38d266f893532c8d6897de4188c734d65de39b44f1bff272c130a82de487a2c` | `python bench/salidas-verificacion/fallos.py` |
| `fallos.txt` | 3 038 | `de1e40157b4d36a704447fed283e28ce467167f88e4eb6715faf64c1f5342210` | mismo comando, stdout capturado: `python bench/salidas-verificacion/fallos.py > fallos.txt` |

`trabajos.py` no genera fichero: su `__main__` (`python
bench/salidas-verificacion/trabajos.py`) solo imprime a stdout el recuento de
trabajos y las rutas que faltasen (comprobación de integridad, no un
generador).

## PENDIENTE: `bytes_leidos.json` no lo reproduce ningún script del directorio

Contenido real: una lista de `{fichero, bytes, leidos}` (p. ej.
`{"fichero": "16bit_tif-to-d16.png", "bytes": 61849791, "leidos": 133}`) —
cuántos bytes tuvo que leer el sondeo **en proceso** frente al tamaño total
del fichero, que es la evidencia detrás de la afirmación de
`bench/coste-verificacion.md` de que "leer cabeceras en proceso" no recorre el
fichero entero. **Ni `bench/scripts/verificador.py` ni ningún `.py` de este
directorio expone o registra un contador `leidos`/`bytes_leidos`**
(`grep -n "leidos" bench/scripts/verificador.py` no da nada). El campo tiene
toda la pinta de haber salido de una sesión interactiva que envolvió
`open()`/`.read()` con un contador de bytes durante una pasada de
`V.sondear()` sobre las 53 salidas, y ese envoltorio no se guardó como
script. Es el mismo patrón que `grafo-popular.json` en
`bench/salidas-fidelidad/`: el dato es plausible y consistente con lo que el
informe describe, pero no hay una orden de una sola línea que lo reproduzca
hoy. Declarado como deuda conocida, no inventado.

## Salvedad de reproducibilidad, declarada

`convertir.py` invoca literalmente las 39 `orden` de
`bench/salidas-referencia/referencia.json`, que incluyen `gswin64c` (Ghostscript
**nativo de Windows**, no el `gs` de este WSL) y usa `FILEX_TMP` o el
temporal del sistema para escribir y borrar las conversiones; `medir.py lote`
usa además `cmd /c exit` como suelo de coste de proceso, que es **específico
de Windows** y no tiene equivalente directo en este entorno. En este WSL están
disponibles `magick`, `ffmpeg` y `python3`, pero no `gswin64c` ni `cmd`, así
que no re-ejecuté estos cinco scripts para verificar bit a bit sus JSON; las
órdenes de arriba se deducen con confianza de leer el código y de contrastar
`correccion.txt`/`fallos.txt`/`conversion.log` (que son exactamente el stdout
que cada script imprime), no de una reproducción confirmada en esta sesión.
`bench/scripts/verificador.py` referenciado por todos ellos sigue presente sin
cambios posteriores registrados en este directorio.
