# MANIFIESTO — `bench/salidas-mcp-cabos-techos/`

Salidas de **`bench/mcp-cabos-y-techos.md`** (worker2, carril CPU/Docker, ronda
14, rama `cpu/mcp-cabos-y-techos`). Cierran los ítems **2, 5 y 6** de `C36` e
instrumentan el **3**.

**Todo lo de aquí es texto** (`.py` y `.json`): se versiona entero, por §6 de
`CLAUDE.md`. No hay un solo binario, así que no hay nada que podar.

## Cómo se reproduce todo

**Intérprete obligatorio: `.venv-mcp-filex`**, el único con `mcp>=2.0.0`
(trampa 14). Desde la raíz del repositorio:

```sh
git lfs checkout                        # trampa 34: el corpus, o la sonda mide punteros
.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_protocolo.py
.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/subsuncion.py
.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_idempotencia.py
```

Las tres son **deterministas** y **no tocan la GPU**: no toman el lock ni lo
necesitan. `sonda_idempotencia.py` invoca ImageMagick a través de `FileX`, así
que necesita `magick` en el `PATH`; las otras dos, sólo el SDK.

## Los ficheros

| Fichero | `sha256` | bytes | Orden exacta que lo reproduce |
|---|---|---:|---|
| `sonda_protocolo.py` | `d854e7b2548629e09ab12008c809a1c40157bd0a72b3f0f2c60bba6822d08eed` | 5 952 | *(fuente, escrito a mano)* |
| `protocolo.json` | `65d45a04ade07d503b0d18f9a1dc054f074b3a081a8ae99eb5b6427190ebe6a1` | 4 618 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_protocolo.py` |
| `subsuncion.py` | `3360d4b249fedb8fedef922ca3604a860de754672f3038d3daa1a926d38d5f21` | 12 986 | *(fuente, escrito a mano)* |
| `subsuncion.json` | `dbf5647d5b8221849a86af8f581f819def97314d6a57cd4bb4f8bb2419241120` | 4 009 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/subsuncion.py` |
| `sonda_idempotencia.py` | `fb2f15c2a85b876ffca8c019a61b79393be94fec92a0bb91600398a7868c8834` | 10 921 | *(fuente, escrito a mano)* |
| `idempotencia.json` | `c6051a7a0647df5f69060513333db52de2bc7f0d3e55a7741c35863c3086354b` | 2 178 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-mcp-cabos-techos/sonda_idempotencia.py` **con el arreglo de M3 puesto** |
| `idempotencia_antes.json` | `df6f608fbbd06b3fbd6794f66213300fbc9782dcc6c44e66c2acf864a7fa88db` | 1 825 | la misma orden **sobre el commit `ee749a1`**, es decir antes del arreglo de `Raices.asegurar()` |

Los `sha256` de los tres `.json` valen para **esta** máquina y **este** árbol:
`protocolo.json` guarda la versión del intérprete, y `idempotencia.json` guarda
`job_id` y rutas temporales, que cambian en cada corrida. **Lo que se reproduce
son los VEREDICTOS, no el `sha256`** — y los veredictos están tabulados en el
informe, celda a celda.

## Dependencias externas, declaradas

- **`repos/mcp-refs/video-audio-mcp/server.py`** — el control positivo de
  `subsuncion.py`. Está en **`.gitignore`** (son clones de referencia), así que
  **en un clon limpio no existe** y la sonda lo dice en su salida
  (`{"error": "no está …", "nota": "repos/ está en .gitignore"}`) en vez de
  reventar. Es la trampa 104: lo que se comprueba es lo que se versiona — por
  eso el control positivo de la **suite** (`pruebas/test_hito4.py`, clase
  `Subsuncion`) es **sintético y hermético**, y esta sonda es la que mide contra
  el servidor real.
- **`corpus/imagen/tipico.png`** (42 855 B, Git LFS) — entrada de
  `sonda_idempotencia.py`, que **publica su tamaño** en el JSON
  (`entrada_bytes`, `entrada_es_puntero_lfs`) para que un puntero de 130 B no
  pase por bueno (trampas 34 y 107).

## Lo que NO está aquí, a propósito

- **`bench/salidas-mcp/mcp_probe.py` y `bench/scripts/mcp_probe_bin.py`** son
  arneses compartidos y no se han tocado (§1 de `CLAUDE.md`). Estas tres sondas
  son propias y no derivan de ellos.
- **Ninguna emisión real de `notifications/roots/list_changed`.** No se puede
  forzar y no se ha fabricado: lo que hay es la instrumentación en
  `filex/mcp.py` (`Raices.emisiones` y `FILEX_MCP_REGISTRO_ROOTS`) y la
  declaración `PENDIENTE` en §4 del informe.
