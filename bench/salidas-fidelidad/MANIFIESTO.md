# MANIFIESTO — `bench/salidas-fidelidad/`

Informe: **`bench/fidelidad-caminos.md`**. El propio informe (§7) ya declara que
el directorio se podó una vez (se borraron los ficheros de `entradas/` y
`salidas/` de más de 1 MB y de más de 150 KB, con sus medidas íntegras en
`clasificado.json`); en el árbol actual la poda ha avanzado más: **las
subcarpetas `entradas/` y `salidas/` que describe el informe ya no existen en
absoluto**, solo quedan los cinco instrumentos (`.py`) y los cuatro `.json`
con los resultados agregados. Nada de esto es un hallazgo nuevo — es la regla
§6 de `CLAUDE.md` aplicada a fondo: los binarios/documentos intermedios se
regeneran ejecutando el pipeline, no se versionan.

**MEDIDO el 01/09/2026** (lectura de los cinco scripts fuente para extraer la
orden real, no una suposición): `_caminos.py` y `_entradas.py` fijan
`RAIZ = r"D:\Work\research\FileX"` y escriben con rutas de Windows —el
pipeline exige **Python nativo de Windows**, no WSL2/Git Bash con rutas
POSIX— y `_caminos.py` invoca Gotenberg en `http://localhost:3200`, así que
requiere el contenedor **Gotenberg levantado**.

## Instrumentos (fuente, no se regeneran)

| Fichero | Tamaño | SHA-256 |
|---|---:|---|
| `_grafo.py` | 9 678 B | `63800537537c72d20c451d16387ae21c5c885fa3126f8b0d960f394c1456561d` |
| `_entradas.py` | 11 361 B | `a774d48fc6e642c9d7f48e095f2e7fb5ab34f1e20c2c3071341d85e8cff348cc` |
| `_sonda.py` | 7 902 B | `5e0c299b7e09a904eb32622068462ba8dd52579c9da2a97716b172af02ba91e7` |
| `_caminos.py` | 16 327 B | `84a4bf756721f7f1dd21d31cfc4f73870d5e17dce64e7e81c53ae724363091a5` |
| `_clasifica.py` | 13 783 B | `e90c88b781683fd65614d87fd23abd38be8510a4f47c58b0b9833f22b50b50da` |

## Salidas y la orden que las reproduce, en orden de dependencia

| Fichero | Tamaño | SHA-256 | Orden |
|---|---:|---|---|
| `grafo-resumen.json` | 2 894 B | `3fb8665883344345a78bf13a7a694144eb2b0a3d5f4508b774914021958bcebb` | `python bench/salidas-fidelidad/_grafo.py` (Windows nativo). Lee `repos/orchestrators/{ConvertX,SnapOtter,gotenberg}` (clones de referencia, `.gitignore`, ver `CLAUDE.md` §1) |
| `grafo-popular.json` | 154 B | `3ad037e64add849a7202bbce8471be9d4cacb7d2ee27c35bc20fe2338c226491` | **NO reconstructible mecánicamente — declarado como tal.** Tres de sus seis claves (`pop_1salto`, `pop_23salto`, `pop_inalcanzable`) coinciden con las mismas claves de `grafo-resumen.json`; las otras tres (`pop_total`, `pop_1salto_plausible`, `pop_23salto_plausible`) **no existen en ninguna salida de `_grafo.py`** — comprobado leyendo el fichero: solo hay un `json.dump` en todo el script y no escribe esas claves. Es un extracto/derivado manual sobre la variable `pop_pares` que `_grafo.py` imprime por pantalla (línea 195) y no vuelve a versionar. **PENDIENTE:** reconstruir a mano el filtro "plausible" que produjo estos tres números, o aceptar que se perdió |
| `_entradas.py` → `entradas/` (9 documentos, ya podados) | — | — | `python bench/salidas-fidelidad/_entradas.py`. Sin dependencias externas (`zipfile`+XML a mano); determinista |
| `resultados.json` | 108 212 B | `b79bd014b44fe55bb9ee8c01582f4dd194475152c6f8b6c6740ee79c698165b9` | `python bench/salidas-fidelidad/_caminos.py` (Windows nativo, tras el paso anterior; regenera también `salidas/`, hoy podada). Requiere Gotenberg en `localhost:3200`, ImageMagick, Ghostscript y ffmpeg — los mismos motores que `filex/motores.py` |
| `clasificado.json` | 127 410 B | `709f25feb2d0f3c0862e1164e5edcf878f269bf80e983d5665261ee75abc4cd7` | `python bench/salidas-fidelidad/_clasifica.py`, tras el paso anterior (lee `resultados.json` y los ficheros de `salidas/` para clasificar cada camino) |

## Salvedad de reproducibilidad, declarada

- **No es reproducible al byte fuera de la máquina de Windows del proyecto**:
  `RAIZ` está cableada a `D:\Work\research\FileX` en `_grafo.py`, `_entradas.py`
  y `_caminos.py`, y éste último además depende de qué contenedores/motores
  estén instalados ahí en el momento de ejecutar (regla ya conocida: build y
  entorno forman parte de la arista, trampa 32/58 de `CLAUDE.md`).
- Este agente (worker2, WSL2) **solo pudo verificar** los nueve ficheros que
  quedan en el árbol (hashes, tamaños, lectura de los scripts para extraer la
  orden real) — no pudo reejecutar el pipeline porque exige Windows nativo,
  Gotenberg vivo y los clones de `repos/`.
- `grafo-popular.json` queda **declarado como no reconstruible con la
  información disponible hoy**, no como un vacío silencioso.
