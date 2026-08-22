# MANIFIESTO — bench/salidas-mcp-cabos-2/ (agente M1, C4 + C5)

Todo es texto (JSON/JSONL/PY/PS1/LOG/TXT); **~260 KB**, sin binarios. Los directorios de trabajo
(`c4a_trabajo`, `c5_trabajo`, `c5_staging`) se **borraron** al terminar. `.mcp.json` del proyecto
**no se tocó** (las sondas usan `--strict-mcp-config` con configs propias de este directorio).

`sha256` = primeros 16 hex. Entornos: `.venv-mcp-vam` (arnés stdio de video-audio-mcp),
`.venv-mcp-sdk-2x` (generadores/sonda), `claude` 2.1.238, `node` v24.19.0 (WSL2).

## Arneses y generadores (reejecutables)

| Fichero | sha256 | Reproduce |
|---|---|---|
| `c4a_deadlock_resto.py` | 75E5A1EC1A811261 | `C4A_TIMEOUT=18 .venv-mcp-vam/Scripts/python.exe c4a_deadlock_resto.py` → `c4a_resultados.json` |
| `c4a_retry3.py` | 6093C94E8D9D4C45 | `.venv-mcp-vam/Scripts/python.exe c4a_retry3.py` → `c4a_retry3.json` (los 3 fallos tempranos, con audio) |
| `c4_probe_srv.py` | 6D7D08679868EA73 | Servidor MCP stdio de sonda (tools/resources/prompts + log de initialize). Derivado de `salidas-saturacion/stub_mcp.py` |
| `c4_gen_catalogos.py` | 3A4F414C223B64F8 | `.venv-mcp-sdk-2x/Scripts/python.exe c4_gen_catalogos.py` → catálogos pesado/ligero + `c4_mcp_*.json` |
| `c4_correr_claude.ps1` | 06A82B9D35864263 | `./c4_correr_claude.ps1` → las 6 sesiones `claude -p` de C4b/c/d |
| `c5b_cruce_inspect.py` | 8E5F043BB1C1503A | `.venv-mcp-vam/Scripts/python.exe c5b_cruce_inspect.py` → `c5b_cruce_inspect.json` |
| `c5a_symlink_wsl.py` | E48ABD72F1A75BD9 | `wsl bash -lc "C5A_DUR=12 python3 <ruta>/c5a_symlink_wsl.py"` → `c5a_symlink_linux.json` **(bloqueado: VM WSL2 caída, no generado)** |

## Resultados (JSON)

| Fichero | sha256 | Contenido |
|---|---|---|
| `c4a_resultados.json` | EE7599DA06B15697 | 20 herramientas × preexistente: **18 DEADLOCK, 3 RESPONDE(error-ff)** |
| `c4a_retry3.json` | ECEC0F258A943FD2 | Re-ejecución de las 3 con audio: 2 DEADLOCK + 1 error de formato |
| `c4a_cvf_matroska.json` | 90386636A84C3079 | `convert_video_format` con `target_format=matroska`: **DEADLOCK** (cierra la 20.ª) |
| `c4a_stdout.log` | 7BD929D484CD91A3 | Traza en vivo del arnés C4a |
| `c4_out_pmin_{pesado,ligero}_{deftools,notools}.json` | ver §Índice | usage de las 4 sesiones de coste (TOTAL: deftools 26.941=26.941; notools 11.188 vs 7.890) |
| `c4_out_penum_pesado_{deftools,notools}.json` | 40C21A5A…, 28AA8827… | El modelo: `NO_VEO_DESCRIPCION` (deftools) vs descripción pegada (notools); recursos/prompts = «NINGUNO» |
| `c4_out_penum_40_notools.json` | 1905D42A933E334C | 40 herramientas: descripción `[truncated]` incluso sin herramientas internas |
| `c4_log_{pesado,ligero,40}.jsonl` | F629E1CF…, 5F2C36A3…, ACB3B6CF… | Log de sonda: `initialize` (roots.listChanged=true), `tools/list`, `resources/list`, `prompts/list` |
| `c5b_cruce_inspect.json` | DD1E05D4683005C7 | Curva copia (1–256 MB), ffprobe/proceso reales, y el cruce (~70 MB esta tanda) |

## Catálogos y configs (regenerables con `c4_gen_catalogos.py` / bloque inline)

`c4_cat_pesado.json` (2BF3C813), `c4_cat_ligero.json` (3E3DD7AA), `c4_cat_40.json` (1ED573B5),
`c4_mcp_{pesado,ligero,40}.json`, `c4_smoke_log.jsonl`.

## stderr de cada sesión de `video-audio-mcp` (C4a)

`c4a_stderr_*.txt` — uno por herramienta ejecutada (G1/G2/G3), más `retry_*`, `full*_cvf`,
`cvf_matroska`. Cada uno es la traza del servidor `video-audio-mcp` para ese caso (581 B: warnings
de pydantic + `CallToolRequest`). No aportan contenido nuevo sobre el JSON; son la trazabilidad.

## Hechos clave (para citar sin abrir los JSON)

- **C4a:** 26/26 herramientas de `video-audio-mcp` que tocan ffmpeg **cuelgan** con salida
  preexistente. 0 excepciones. Las 3 «respuestas» fueron fallos tempranos por entradas
  (fuente sin audio; `-f mkv` inválido → `matroska`).
- **C4b:** `client_capabilities.roots.listChanged = true` (Claude Code 2.1.238).
- **C4c:** el cliente llama `resources/list` y `prompts/list`, pero el modelo responde «NINGUNO».
- **C4d:** deftools pesado=ligero=**26.941** tok totales (diferido); notools pesado−ligero=**3.298**
  tok (ansioso). El modelo: «*Their schemas are NOT loaded*».
- **C5b:** cruce `copia==ffprobe` ≈ **70 MB** (esta tanda, copia 1.225 MB/s) / **~94 MB** (tanda
  `cabo5`, 1.628 MB/s). `inspect` en proceso: **0,04–0,06 ms**. `ffprobe`: ~57 ms.
- **C5a:** BLOQUEADO por `Wsl/Service/0x8007274c` (VM WSL2, cap 1,9 GiB, `.wslconfig` intocable).
