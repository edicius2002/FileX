# MANIFIESTO — `bench/salidas-hito3/`

C41. Todo el contenido es texto (`.py`/`.json`) y por eso se versiona entero
(regla §6). Este manifiesto documenta, por fichero, tamaño, `sha256` y la
orden exacta que lo reproduce — la mayoría **ya estaba escrita** en
`bench/hito3-mudanza.md` §8 ("Manifiesto de `bench/salidas-hito3/`"); aquí se
verifica contra el árbol actual y se completa con hash y tamaño.

**MEDIDO** (`sha256sum`/`stat` sobre el árbol en `ccb/worker2`, 01/09/2026).

## Fuentes (escritas a mano, no regenerables — son el programa)

| Fichero | Tamaño (B) | SHA-256 |
|---|---:|---|
| `_colisiones.py` | 4 542 | `867901972d54a4abfc93ff544326215cafe9379f895a716307fe5c43b804dc04` |
| `_compara.py` | 1 928 | `c92b9bee0d00f71e7e1a6a8f46d5c5414bdfef719326efbc15b295d65f2838a5` |
| `_datos_ram.py` | 3 322 | `644e5696c9438e2e1bf863f913a2b49408f382b7b302da3a0cd8e6c3ceb0e5d7` |
| `_reg53_hito3.py` | 11 579 | `ee8aac81683e801997c146a271dc909fe9be72b692682b68aada9ec940b7291f` |

Último commit que los tocó: `c2f6a59` ("Hitos 3 y 4, y W9 cerrado dentro del
propio núcleo de FileX"). `_reg53_hito3.py` deriva de
`bench/salidas-firmas/_regresion53.py` (F1) sin tocarlo ni importarlo, como
manda CLAUDE.md.

## Salidas generadas — orden exacta (`bench/hito3-mudanza.md` §8)

| Fichero | Tamaño (B) | SHA-256 | Orden |
|---|---:|---|---|
| `reg53_antes.json` | 58 573 | `0d86c2f9dce9764f740e0d2c878592271a1e3e03db75d7255d6d77b1db43da19` | `python bench/salidas-hito3/_reg53_hito3.py --fuente bench --con-fidelidad` *(con el verificador aún en `bench/scripts/verificador.py`, que sigue existiendo hoy)* |
| `reg53_antes_testigos.json` | 253 | `352627b69a74acafb96c96f343b985c5753a1ce5f8af7c8b7dc8f9d289cea27c` | lo escribe el mismo arnés que `reg53_antes.json`, aparte, para no contaminar el diff |
| `reg53_despues.json` | 58 570 | `9856637c9bf1f741d5b535ed9d426bba16a1d2e280ec7b7725fcdf602406f35f` | `python bench/salidas-hito3/_reg53_hito3.py --fuente filex --con-fidelidad` |
| `reg53_despues_testigos.json` | 255 | `fa6882d0950f91b893c5ead72e5b2a7f5d5453a77128d28baa0d22d07221f990` | lo escribe el mismo arnés que `reg53_despues.json` |
| `reg53_envoltorio.json` | 58 570 | `56477b9594391e452d93bdadf30e7fb8369517e6d527678f4fea104184fe3773` | `python bench/salidas-hito3/_reg53_hito3.py --fuente bench --con-fidelidad --salida-json reg53_envoltorio.json` *(con el envoltorio de 66 líneas ya puesto en `bench/scripts/verificador.py`)* |
| `reg53_envoltorio_testigos.json` | 255 | `259db4d70a8dbd87aa4a1b5427005217c3cf3d2f8cac841118507439c9680cb7` | lo escribe el mismo arnés que `reg53_envoltorio.json` |
| `datos_ram.json` | 1 077 | `ded6c59fe59162bd1456020621ec3bc07974236cef2d439ea2e9a82f8d650036` | `python bench/salidas-hito3/_datos_ram.py --mb 1 8 32` |
| `colisiones.json` | 2 596 | `ffae676da533325257ffc60ed856acb406ff0bef5fc636d828bdf9c33f379157` | `python bench/salidas-hito3/_colisiones.py` |

## No genera fichero (es la comparación, imprime a `stdout`)

`_compara.py`: `python bench/salidas-hito3/_compara.py reg53_antes.json reg53_despues.json reg53_envoltorio.json` — compara los tres volcados ignorando sólo las claves `fuente`, `modulo`, `fichero` (que tienen que diferir por construcción) y sale `1` si hay alguna otra diferencia. El resultado ("1 844 hojas comparadas, 0 diferencias") está citado en `bench/hito3-mudanza.md` §568 y §319 y no se vuelve a versionar aparte.

## Salvedad de reproducibilidad, declarada

`reg53_antes.json` y `reg53_envoltorio.json` dependen de qué haya hoy en
`bench/scripts/verificador.py` (que sigue existiendo, `git log -1` sin
commits posteriores a `c2f6a59` sobre ese fichero) y `reg53_despues.json`
depende de `filex/verificador.py`, que SÍ ha cambiado desde entonces (carril
CPU de rondas posteriores). **PENDIENTE:** re-ejecutar hoy los tres no
reproduce necesariamente el mismo byte a byte que el committeado — el
manifiesto documenta la orden que los generó el 22/08, no una garantía de
identidad futura. Esto es coherente con la trampa 32/49 de `CLAUDE.md`: la
huella del código, no el `sha256` del volcado, es lo que certifica que
"nada cambió" entre `antes`/`después`/`envoltorio`.
