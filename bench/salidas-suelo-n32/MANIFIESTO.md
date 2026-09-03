# MANIFIESTO — `bench/salidas-suelo-n32/`

Salidas de `N32`/`C36`/`B3` (worker10, carril `edicius2002/filex-suelo-y-mcp`). Ver
`bench/suelo-y-mcp.md`. Sin binarios: `marker_out/` se creó vacío (dos intentos de `B3`
abortados antes de producir salida, ver §3 del informe) y se borró.

## Ficheros

| Fichero | Bytes | sha256 | Orden |
|---|---:|---|---|
| `remedir_oraculo.py` | 6155 | `45a5dad3c68e54e602c6590ca872e67bd915677bec94b8209aa0a820c0f933e6` | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-suelo-n32/remedir_oraculo.py` |
| `resultado_fresco.json` | 7194 | `216afa7381e7c2771362c8ee58e95b9fdbfe388e3a931383171880b9233a2c34` | salida de la orden anterior (la última de las dos corridas de 5 tandas; las 5 "limpias" citadas en el informe §1.1 se leyeron de consola y no se guardaron por separado — la orden es determinista en método, no en resultado, porque depende del estado de la máquina en cada tanda) |
| `medir_suelo_alto.py` | 4578 | `038fbfcba77cf6b1689f66a246f8af6d421385000eef8e7fb95367856c07283f` | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-suelo-n32/medir_suelo_alto.py` |
| `resultado_suelo_alto.json` | 856 | `0ea85b13ec245dd0fa66c0a7fc047bb0804e9a3741cde49b6ceb8dc1f9efe948` | salida de la orden anterior |
| `medir_operacion.py` | 4726 | `e66665c1365c4a618dfa9677d9e798bba4a8d88bc70e21586cf9824e0f1cf89a` | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-suelo-n32/medir_operacion.py` |
| `resultado_operacion.json` | 828 | `e6eb56dbb36c887130ee0a315b7a29f764a06bcaee53cd5a8ceae23486074637` | salida de la orden anterior (última de 4 tandas; las 4 están citadas en la tabla del informe §1.3) |
| `medir_job_denegado.py` | 6707 | `99ea9ba005b0f7f30ee2d117310eb239709f043bdeaca3d05dd966ea3f0f902f` | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-suelo-n32/medir_job_denegado.py` |
| `resultado_job_denegado.json` | 759 | `44c7c27bfa5b3ee5d6a860bc26032d1cefe4f1ceb6239f01a2b977af298de3ed` | salida de la orden anterior |
| `medir_catalogo_proyectado.py` | 4951 | `2dc5a5a763dc9d3aa8de6f143e98d5748afb40cdcdd1d0c20d1bf1d1d36478d5` | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-suelo-n32/medir_catalogo_proyectado.py` (necesita Docker arriba y Gotenberg vivo en `:3200`) |
| `resultado_catalogo_proyectado.json` | 713 | `601b969264eb94a399589dfedd57f389188f9dd0334b2e9ddf782077d6a2a1fe` | salida de la orden anterior |
| `medir_marker.py` | 8711 | `305384a699fd580714d2409a1a2ccc50de43ccfbcea5bfb0394c3cb3bb3ca3b3` | `D:\Work\research\FileX\.venv-marker\Scripts\python.exe bench/salidas-suelo-n32/medir_marker.py` — **AVISO DE SEGURIDAD**: en esta máquina, esta orden ha lanzado dos veces un `docker run --runtime nvidia --gpus device=0` sin que nadie tomara el lock de GPU (ver `bench/suelo-y-mcp.md` §3). El script trae un guardián que mata el árbol en cuanto detecta un hijo `docker*`, pero **no lo ejecutes sin tomar el lock de GPU primero** o sin comprobar que sigue reproduciéndose antes de confiar en el guardián. |
| `resultado_marker.json` | 1316 | `604f1c60e8f68b12bafa2e9026fc4e02a5042a0cbf44cdc385df2bdc3a98a162` | salida de la orden anterior (segundo intento, `--mode fast`; el resultado es el bloqueo abortado, no una medida de `marker`) |

## Notas

- `remedir_oraculo.py` y `medir_suelo_alto.py` miden `Confinamiento.resolver()` en aislado
  (in-process, n=2000/celda) — misma metodología que `bench/salidas-oraculo-n9/medir_oraculo.py`
  de la ronda anterior, sin escribir sobre sus ficheros.
- `medir_operacion.py` mide `FileX.convertir()` completo (n=500), misma metodología que
  `bench/salidas-oraculo-n9/medir_convertir.py`, YA con el suelo por operación implementado en
  `filex/confinamiento.py`/`filex/nucleo.py` — es la medida de DESPUÉS; el ANTES se cita del
  `resultado_convertir.json` de la ronda anterior (no se reproduce aquí para no duplicar un
  fichero de otro agente).
- `medir_job_denegado.py` mide `Servicio.convert()` con `fx.convertir` monkeypatcheado a un stub
  rápido (para no gastar Docker/CPU real en 400 llamadas) y con `Trabajos()` apuntando a un
  directorio propio (no al `%TEMP%/filex-trabajos` compartido por la máquina).
- `medir_catalogo_proyectado.py` NO modifica `filex/motores.py`: añade aristas sintéticas al
  grafo sólo dentro del propio proceso del script, para proyectar el catálogo sin registrar
  motores nuevos en producción.
- `medir_marker.py` es el único que NO produjo la medida que se pedía (B3): los dos intentos
  documentados en `bench/suelo-y-mcp.md` §3 se abortaron por seguridad antes de que el
  contenedor de GPU llegara a crearse. `docker ps -a` y `docker images` se comprobaron limpios
  después de cada aborto (sin contenedor `surya-vllm-*`, sin imagen `vllm/*`).
