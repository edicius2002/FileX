# `bench/salidas-cerrojo/` — MANIFIESTO

Salidas del agente **N-b**, encargo **N1**, 23/08/2026. Informe:
[`bench/cerrojo-de-maquina.md`](../cerrojo-de-maquina.md).

**No hay una sola salida binaria.** Todo es `.py`, `.json` y logs de texto, así
que todo se versiona. Los ficheros que los arneses generan de verdad —copias del
corpus, `.webp` de salida, ficheros de cita— viven en
`bench/salidas-cerrojo/desechable/`, que **cada arnés crea y borra**, y que no
está versionado.

## Requisito previo

En un **worktree recién creado** el `corpus/` son punteros de Git LFS y estos
arneses fallan con `improper image header` (§10 del informe):

```sh
git lfs checkout          # 39 objetos, 266 MB, del almacén local, sin red
```

## Cómo se reproduce cada cosa

Todo desde la raíz del repositorio, con `PYTHONIOENCODING=utf-8` (los logs
llevan tildes y la consola de Windows es cp1252).

| Orden | Qué produce | Informe |
|---|---|---|
| `python bench/salidas-cerrojo/sonda_primitivos.py` | `logs/sonda_primitivos.log` — los tres primitivos de candado sondeados en ejecución, con un hijo real que se mata con `taskkill /F` | §3, §5.1 |
| `python bench/salidas-cerrojo/carrera_destino.py --json bench/salidas-cerrojo/carrera.json` | `carrera.json`, `logs/carrera_destino.log` — el fallo entre procesos y las tres pasadas del cierre | §2 |
| `python bench/salidas-cerrojo/coste_cerrojo.py` | `coste.json`, `logs/coste_cerrojo.log` — n=20 000 por celda, con los dos testigos de ruido | §7 |
| `python bench/salidas-cerrojo/desglose_cerrojo.py` | `desglose.json`, `logs/desglose_cerrojo.log` — dónde se van los µs del candado | §7.2 |
| `python bench/salidas-cerrojo/huerfano_y_deteccion.py` | `huerfano_y_deteccion.json`, `logs/huerfano_y_deteccion.log` — dueño muerto y tercero que no coopera | §4, §5 |
| `python -m pytest pruebas/test_cerrojo.py -q` | 11 pruebas, ~10 s | §9 |
| `python -m pytest pruebas/ -q` | **163 passed, 6 skipped** | §8 |

Los tres arneses que lanzan procesos **matan con `taskkill /F /T`** y tienen
tope explícito (300–600 s). Ninguno usa la GPU.

## La variable que hace reproducible el ANTES

```
FILEX_CERROJO_DESTINO = maquina (defecto) | proceso | ninguno
FILEX_CERROJO_DIR     = dónde viven los candados (defecto: %TEMP%/filex-destinos)
```

`proceso` es **exactamente** el estado del hito 7 (el `set` en memoria y nada
más), y es lo que permite medir el antes y el después **dentro de la misma
tanda**. El defecto es el valor seguro: los otros dos hay que pedirlos a mano.

## Advertencia sobre las cifras

Las medianas de `coste.json` son de **una tanda**, con otro agente trabajando en
la máquina y la sesión de escritorio remoto activa. **Las relativas dentro de la
tanda valen; las absolutas no son comparables con las de otro informe** — y en
particular los 3,2 µs que publicó `hito7-superficies.md` §5.3 **no** son
comparables con los 223,0 µs de aquí, porque además cambió el código (§7.1).
