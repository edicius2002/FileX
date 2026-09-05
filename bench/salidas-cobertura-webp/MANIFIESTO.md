# `bench/salidas-cobertura-webp/` — carril `cob/webp`

Informe: `bench/cobertura-webp.md`. Rama `cob/webp`, 05/09/2026.

**Intérprete y entorno de todas las cifras** (trampas 94 y 101):
`.venv-mcp-filex\Scripts\python.exe`, CPython **3.11.9 win32**; `magick` 7.1.2
Q16-HDRI con **libwebp 1.6.0**; `coverage` 7.16.0 con `--branch`. Sin GPU, sin
Docker, sin lock. **No se lanzó la suite completa** (cinco workers más en la
máquina, trampas 101 y 123): todo sale de
`python -m unittest pruebas.test_cob_webp`.

**Aquí no hay un solo binario.** Los trece ficheros WebP del carril viajan como
literal base64 dentro de `pruebas/fixtures_cob_webp.py`, con su `sha256`
declarado, y `generar_fixtures.py` los reproduce y los verifica.

---

## Ficheros

| Fichero | Qué es | Orden que lo reproduce |
|---|---|---|
| `generar_fixtures.py` | **Reproduce los 13 fixtures desde cero** con `magick` y **falla si algún `sha256` se mueve**. Es la orden exacta que pide `CLAUDE.md` §6 | `python bench/salidas-cobertura-webp/generar_fixtures.py` |
| `cobertura.json` | Cobertura de `filex/` que da **este módulo solo**, con ramas | `python -m coverage run --branch --include="*/filex/*" -m unittest pruebas.test_cob_webp` y luego `python -m coverage json -o bench/salidas-cobertura-webp/cobertura.json` |
| `base-cobertura.json` | **Recorte** de la cobertura base que midió el maestro el 04/09 sobre la suite entera (517 pruebas): sólo la entrada de `filex/verificador.py`, que es lo único que lee `ganancia.py`. `totals` es el del paquete sin recortar | medido por el maestro; aquí sólo se recorta |
| `ganancia.py` / `ganancia.json` | **Ganancia NETA contra la unión base ∪ `cob/png`**, y el solape declarado | `python bench/salidas-cobertura-webp/ganancia.py` |
| `discriminacion.py` / `discriminacion.json` | **40 mutaciones de una línea** sobre `filex/verificador.py`, con control de identidad por `sha256` y restauración con `git checkout --` | `python bench/salidas-cobertura-webp/discriminacion.py` |
| `cruce_libwebp.py` / `cruce-libwebp.json` | Cruce del plano alfa y del RGBA entero contra **libwebp** sobre los 13 fixtures y los 4 filtros del `ALPH` | `python bench/salidas-cobertura-webp/cruce_libwebp.py` |
| `alcance_modo13.py` / `alcance-modo13.json` | **Alcance real del defecto del predictor 13** sobre 50 imágenes escritas por `magick`, con el control de alfa plano que reproduce el camino de `cob/png` | `python bench/salidas-cobertura-webp/alcance_modo13.py` |

`discriminacion.py` **modifica `filex/verificador.py`** mientras corre y lo
restaura con `git checkout --`. No lo lances con cambios sin guardar en ese
fichero, y comprueba `git status -- filex/` al terminar (el propio script se
niega a seguir si el `sha256` no vuelve al original).

---

## Cifras publicadas y dónde se comprueban

| Afirmación del informe | Fichero | Cómo se relee |
|---|---|---|
| 272 líneas del encargo → 3 | `cobertura.json`, `base-cobertura.json` | `ganancia.py`, columnas `base` y `quedan` |
| ganancia NETA **138**; solape con `cob/png` **310**; bruta sobre la base sola **448** | `ganancia.json` | `ganancia.py` |
| **40 mutaciones, 40 rojas, 0 sin detectar** | `discriminacion.json` | campo `estado` de cada entrada |
| plano alfa 15/16 y RGBA 6/7 idénticos a libwebp | `cruce-libwebp.json` | campo `resumen` |
| modo 13: **11 de 40** con alfa con textura lo disparan, **10** mueven `alfa_min`, **0** difieren sin él; con alfa plano **3 de 10** lo disparan y **0** mueven nada | `alcance-modo13.json` | campo `resumen` y las filas |
| los 13 fixtures reproducen su `sha256` | — | `generar_fixtures.py`, que lo comprueba y devuelve `rc=1` si falla |

---

## Los trece fixtures

`sha256` y tamaño también en `MANIFIESTO` dentro de
`pruebas/fixtures_cob_webp.py`, que la suite verifica en
`test_el_manifiesto_cuadra_con_los_bytes`.

| Nombre | B | Qué ejercita |
|---|---:|---|
| `LL_TRANSFORMACIONES` | 414 | predictor + color cruzado + restar verde, referencias hacia atrás, caché de color |
| `LL_META_HUFFMAN` | 2 410 | imagen meta-Huffman (más de un grupo de códigos) |
| `LL_PALETA_ANCHA` | 742 | paleta con `bits=0`, un índice por píxel (24 colores) |
| `LL_PALETA_EMPAQUETADA` | 56 | paleta con `bits=3`, ocho índices por byte (3 colores) |
| `LL_OPACO` | 44 | atajo por cabecera `alpha_is_used=0` |
| `LL_DAMERO` | 104 | predictor 12 sobre 64×64 |
| `DEFECTO_MODO13` | 1 748 | **el defecto del predictor 13**: libwebp mide 60, FileX publica 53 |
| `PERDIDA_ALPH_CRUDO` | 492 | `ALPH` sin comprimir; base de las cuatro mutaciones de filtro |
| `PERDIDA_ALPH_VP8L` | 132 | `ALPH` comprimido como VP8L, filtro 1 |
| `PERDIDA_ALPH_DIAG` | 152 | predictor 1 |
| `PERDIDA_ALPH_OPACO` | 82 | con pérdida, alfa totalmente opaco |
| `PERDIDA_SIN_ALFA` | 120 | retorno por cabecera, sin `ALPH` |
| `ANIMADO` | 200 | dos trozos `ANMF`: **el defecto del N+1** |

**Total: 6 672 B.** No van a `corpus/` a propósito — sería Git LFS, con su cuota
de 1 GB/mes (trampa 103) y la trampa 34 encima.

**Aviso reproducido y arreglado (informe §7.1):** tres de estas recetas eran
**no deterministas** en su primera versión porque el `-seed` iba **detrás** del
generador de `magick`, donde no surte efecto. Con el `-seed` delante, los trece
reproducen. Los blobs del módulo de fixtures se generan **desde
`generar_fixtures.py`**, para que no puedan separarse de su orden.
