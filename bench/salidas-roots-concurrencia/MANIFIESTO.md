# Salidas de `bench/roots-concurrencia.md` (N34, ronda 15, worker3)

Informe: [`bench/roots-concurrencia.md`](../roots-concurrencia.md).

**Todo es texto y se versiona entero** (`CLAUDE.md` §6: los `.json` de
resultados, los scripts y los logs son texto barato y son la trazabilidad).
No hay binarios que podar.

**Intérprete y entorno de todas las tandas:**
`.venv-mcp-filex\Scripts\python.exe` — **3.11.9, win32**, `mcp` **2.0.0**,
Docker 29.4.3 con 12 imágenes. Máquina **no despejada**: otro worker en el
mismo carril (CPU 42 %, 424 procesos, 12 `python` vivos).

| Fichero | `sha256` | Bytes | Orden exacta que lo reproduce |
|---|---|---|---|
| `sonda_carrera.py` | `f823cd610f4e3da573b1e4cfe9c358f3a5255775447c49cf4c7379359f018417` | 29 938 | (fuente; se versiona) |
| `carrera_despues.json` | `6ceafee8f80d2a93bf29a3ee703484f51d83f2a4cdef59d396428120be8d835b` | 22 694 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-roots-concurrencia/sonda_carrera.py bench/salidas-roots-concurrencia/carrera_despues.json` |
| `log_despues.txt` | `099e0e69e95f589e607c31664bc13be4c00764dc9cea59c175e3061a6667588b` | 22 944 | la misma orden, con `> bench/salidas-roots-concurrencia/log_despues.txt 2>&1` |
| `carrera_antes.json` | `e04e0df0e477718a70d1538cfbc3a87be02409e188ded318ceb6e86510ccf659` | 17 922 | **ver la nota de abajo**: la misma orden con `filex/mcp.py` **anterior al arreglo** |
| `log_antes.txt` | `32b65eeabd1da37db605cd4fa7b95823e999121dba57a74b1a22900eabd20fdb` | 18 170 | ídem, con la salida redirigida |
| `suite.txt` | `0ef2614b3dfa97e31c59eb8776b87183058c80cb3cf5e39a4c4a36fb12198b75` | 7 529 | `.venv-mcp-filex/Scripts/python.exe -m unittest discover -s pruebas -p "test_*.py"` |

## Los `sha256` identifican ESTAS tandas, no son un objetivo a reproducir

Los JSON llevan **milisegundos, microsegundos y rutas de directorio temporal**,
así que volver a lanzar la orden da un fichero con **otro `sha256`**: el hash
sirve para saber si el fichero que se lee es el que se publicó, no para
verificar una reejecución. **Lo que sí tiene que reproducirse son las celdas
categóricas** —`roots_list_llamadas`, `el_orden_cambia_el_estado_final`,
`sella_un_confinamiento_mas_ancho_que_la_interseccion`, `hay_fuga`—, que son
deterministas y son las que decide la fila. Los tiempos de pared **no son
comparables con los de otra tanda** (`CLAUDE.md` §3).

## La tanda `antes` no se reproduce con la orden sola, y hay que decirlo

`carrera_antes.json` se midió **con `filex/mcp.py` anterior al arreglo de
N34** y con una versión de la sonda que **aún no tenía** las celdas `N8` ni el
sujeto `A_Historico`. Reproducirla byte a byte exige aquel árbol; **lo que sí
se reproduce hoy, y es lo que importa, es su CONTENIDO**: la fila
`A_historico` de `carrera_despues.json` reimplementa el `asegurar` de entonces
y devuelve las mismas respuestas en las celdas que deciden la fila —
`roots/list` 1/2/4/8 con N=1/2/4/8, `el_orden_cambia_el_estado_final: true`,
`sella_un_confinamiento_mas_ancho_que_la_interseccion: true`—.

Es deliberado: **el control positivo del arnés es el sujeto con el defecto,
conservado dentro de la sonda** (informe §1.1, propuesta de trampa 116), justo
para que la evidencia de «cómo era antes» no dependa de un árbol que ya no
existe ni de un hash de commit que un `--squash` mataría (trampa 115).

## Qué hay dentro de cada JSON

Ocho celdas, cada una con lo que la refutaría al lado (trampa 111):

| Celda | Qué mide |
|---|---|
| `N0_*` | El control del arnés: doble que cede contra doble que no cede, **sobre el sujeto histórico** (trampas 114 y 116) |
| `N1_escalado` | `roots/list` con N=1/2/4/8 herramientas concurrentes, por candidato |
| `N2_divergencia` | Las **dos órdenes de terminación** del mismo par de respuestas, y si el estado final cambia |
| `N3_sellado_por_fallo` | Si un `roots/list` fallido sella un confinamiento **más ancho** que la intersección de R13 |
| `N5_cache_caliente` | El coste del camino del 99 % de las llamadas, n=200 |
| `N5_roots_list_que_no_vuelve` | Lo que un candado sostenido durante el `await` hace con un cliente mudo |
| `N6_par_atomico_para_corrutinas` | Sobre el **AST** (trampa 42): si hay algún `await` entre las dos escrituras de estado |
| `N7_raiz_de_unidad` | La fuga del `except ValueError`, con su control de raíz normal al lado |
| `N8_raices_mixtas` | El **precio** del arreglo de N7: una raíz que no confina se lleva por delante a las que sí |
