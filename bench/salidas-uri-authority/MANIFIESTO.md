# `bench/salidas-uri-authority/` — N37, la *authority* de un `file://`

Salidas de `bench/uri-authority.md` (worker7, carril CPU, ronda 17, 04/09/2026).

**Todo es texto**: no hay un solo binario, así que no hay nada que podar (§6 de
`CLAUDE.md`). Los `.json` son resultados y los `.py`/`.js` son los arneses que
los producen.

## Entorno de la medición

| Qué | Valor |
|---|---|
| Intérprete | `.venv-mcp-filex\Scripts\python.exe` — **Python 3.11.9, win32** |
| Runtime del cliente | **Node v22.23.2** (el de Claude Code) |
| Cliente MCP sondeado | **Claude Code 2.1.260**, protocolo `2025-11-25` |
| Docker | 29.4.3, demonio levantado |
| Estado de la máquina | **NO despejada**: otro agente trabajando en documentación |
| `cwd` de las sondas | el *worktree* `agent-a146f8a533c52cb89` |

> El `cwd` importa y no es decoración: media fila de N37 consiste en que
> `os.path.abspath` completa una ruta sin unidad con la del **proceso**, así que
> las rutas `D:\…` que aparecen en los resultados salen de que el árbol vive en
> `D:`. En otra unidad, la fuga apuntaría a otro sitio — pero apuntaría igual.

## Ficheros

| Fichero | `sha256` (12) | Bytes | Orden que lo reproduce |
|---|---|---|---|
| `sonda_uri.py` | `4c1f30bc1b50` | 5 913 | *(arnés)* |
| `sonda_uri_antes.json` | `f6c775b220c0` | 9 127 | `python bench/salidas-uri-authority/sonda_uri.py` **sobre el código de `2498f4b`** |
| `sonda_uri_despues.json` | `269491cd6439` | 6 915 | `python bench/salidas-uri-authority/sonda_uri.py` sobre el árbol de esta rama |
| `tabla_candidatos.py` | `1a22cfcabd69` | 8 236 | *(arnés)* |
| `tabla_candidatos.json` | `243cde988670` | 15 029 | `python bench/salidas-uri-authority/tabla_candidatos.py` |
| `productores_node.js` | `834c3a7d93bb` | 2 320 | *(arnés)* |
| `productores_node.json` | `c2ca7d50dc29` | 2 409 | `node bench/salidas-uri-authority/productores_node.js` |
| `productores_py.py` | `2347349b3ca9` | 2 746 | *(arnés)* |
| `productores_py.json` | `31a5ec45611b` | 2 232 | `python bench/salidas-uri-authority/productores_py.py` |
| `srv_sonda_roots.py` | `349ef6863c14` | 4 104 | *(arnés; lo lanza Claude Code, no se ejecuta a mano)* |
| `cfg_roots.json` | `d5489c6ff4fc` | 470 | *(configuración del arnés)* |
| `r_roots_cliente.jsonl` | `38e635a2962a` | 1 851 | `cd bench/salidas-uri-authority && rm -f r_roots_cliente.jsonl && timeout 300 claude -p "Responde solo con la palabra LISTO." --mcp-config cfg_roots.json --strict-mcp-config --max-turns 1` |
| `sonda_unc.py` | `07f4430ed35b` | 2 360 | *(arnés)* |
| `sonda_unc.json` | `cabcf220e552` | 1 420 | `python bench/salidas-uri-authority/sonda_unc.py` |
| `sonda_c4_unc.py` | `3139098988415` | 4 596 | *(arnés)* |
| `sonda_c4_unc.json` | `20c6a85bd626` | 1 322 | `python bench/salidas-uri-authority/sonda_c4_unc.py` |
| `sonda_alias_destino.py` | `53ff81f11844` | 4 016 | *(arnés)* |
| `sonda_alias_destino.json` | `5844153bc4e3` | 1 752 | `python bench/salidas-uri-authority/sonda_alias_destino.py` |
| `ab_discriminan.py` | `d4a90c4f7eea` | 7 850 | *(arnés)* |
| `ab_discriminan.json` | `5e24d959c0dc` | 6 952 | `python bench/salidas-uri-authority/ab_discriminan.py` |
| `coste_n37.py` | `ba6f1faa37e2` | 5 578 | *(arnés)* |
| `coste_n37.json` | `ea35d7b3ba66` | 839 | `python bench/salidas-uri-authority/coste_n37.py` |
| `coste_n37_tanda2.json` | `ef4ff0aa532d` | 837 | ídem, segunda tanda |
| `coste_n37_tanda3.json` | `fb8154a690c3` | 835 | ídem, tercera tanda |

`python` = `.venv-mcp-filex\Scripts\python.exe`, con `PYTHONIOENCODING=utf-8`
(sin ella, la consola `cp1252` de esta máquina revienta al imprimir un emoji;
es del terminal, no del arnés).

## Dos avisos para quien reproduzca esto

1. **`sonda_uri_antes.json` no se reproduce con el árbol de hoy.** Es la mitad
   «antes» de un A/B, y para regenerarlo hay que montar el código viejo:
   `git show 2498f4b:filex/mcp.py`. El propio JSON trae el `sha256` de la
   función que midió, en `control_de_identidad`, precisamente para que un
   fichero no pueda pasar por el otro (trampa 119).
2. **`ab_discriminan.py` no toca el árbol vivo.** Monta cada versión en una
   copia temporal (trampa 84: no se edita el código bajo medición) y borra la
   copia al terminar, también si falla.

## Los arneses copiados

`srv_sonda_roots.py` es una copia adaptada de
`bench/salidas-tasks-protocolo/srv_sonda_initialize.py` (worker4, ronda 16),
como manda `CLAUDE.md` §1: el arnés compartido no se toca, se copia. Lo que se
le añadió es la emisión de `roots/list` —que es una petición **servidor →
cliente**— y el registro de su respuesta.
