# MANIFIESTO — `bench/salidas-mcp/`

Informe que consume estas salidas: **`bench/mcp-ergonomia.md`** (confirmado con
`grep -rl "salidas-mcp/" bench/*.md` — también aparece citado, de pasada, en
`bench/mcp-refs-multimedia.md`, pero el generador es `mcp-ergonomia.md`).

**Total en disco: 31 ficheros, 1 188 193 B (~1,13 MB)** (`_pagina_densa.pdf` +
`grande_60p.pdf` + el arnés + specs/salidas/volcados de `markitdown-mcp` y `docling-mcp`).

---

## 0. PENDIENTE / NO REPRODUCIBLE DESDE ESTE ENTORNO (WSL) — léase antes de re-ejecutar nada

Todo lo que sigue exige **Python de Windows con dos venvs concretos, activos y con los
servidores MCP instalados**:

- `D:\Work\research\FileX\.venv-ai\Scripts\docling-mcp-server.exe` (docling-mcp, dentro del
  venv de IA, instalado con `--no-deps` para no tocar `torch`/CUDA — ver `CLAUDE.md` §2 y
  `bench/mcp-ergonomia.md` §1.2).
- `D:\Work\research\FileX\.venv-mcp-md\Scripts\markitdown-mcp.exe` (markitdown-mcp, venv
  propio porque `mcp~=1.8.0` y `mcp>=2.0.0` no coexisten — trampa 14 de `CLAUDE.md`).
- `gswin64c` (Ghostscript de Windows) para regenerar `grande_60p.pdf`.

Ninguno de los tres existe como binario de Linux en este *worktree* de WSL: los
`mcpServers` configurados en `.mcp.json` (`docling`, `filex`, `markitdown`) **no conectan
aquí** — este mismo entorno lo reporta como `ENOENT` sobre esas rutas `D:\…\Scripts\...exe`.
`mcp_probe.py` (el arnés) sí es Python puro y correría en Linux, pero **el sujeto medido son
los servidores de Windows**, así que ejecutarlo aquí no reproduciría nada — mediría, si
acaso, la ausencia del binario. **Declarado, no inventado**: no hay una vía de reproducir
`res_*.json` / `stderr_*.log` / `dl_*.md` / `md_*.md` sin Windows nativo y los dos venvs de
`CLAUDE.md` §2. La orden exacta de cada fichero se documenta abajo para cuando se ejecute
en la máquina de Windows del proyecto.

---

## 1. Arnés (copia local, NO es tuyo modificar el original)

`CLAUDE.md` §1 marca `bench/salidas-mcp/mcp_probe.py` como **arnés compartido**: si hace
falta una variante, se copia a otro directorio de salidas en vez de editar este. Este
directorio **es su sitio canónico** (no una copia), y lo usan también otros informes que
levantan servidores MCP por stdio con specs JSON.

| Fichero | sha256 | Bytes |
|---|---|---:|
| `mcp_probe.py` | `0ed18ddb3e51358a4341fd88f1faed8e00d9b32f6546732d698c66a52f9fe9c3` | 8 724 |

Firma de invocación (confirmada en `bench/mcp-ergonomia.md` §"Reproducir"):

```
<venv>/Scripts/python.exe bench/salidas-mcp/mcp_probe.py <spec.json> <res.json>
```

Lanza el servidor declarado en `spec.json` (`command`/`args`/`env`/`cwd`), hace
`initialize` + `tools/list`, ejecuta cada paso de `"pasos"` y escribe el resultado crudo
(tiempos, tokens, respuesta literal) en `res.json`; el `stderr` del servidor se redirige al
fichero que indique `"stderr_log"` dentro del propio spec.

---

## 2. Entradas generadas para la medida

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `_pagina_densa.pdf` | `41122eb92ef4d7c6184f3f6d5879bfafbbd27c221eab7be91b0408ca00710b1` | 2 588 | **PENDIENTE**: es un PDF de 1 página generado con **ReportLab** (`Producer: ReportLab PDF Library`, cabecera del propio fichero) el 19/08/2026. El informe no conserva el script generador ni describe su contenido exacto más allá de "página densa de texto"; no hay orden exacta que reproducirla byte a byte. |
| `grande_60p.pdf` | `864854f133daee54bb107d16de8f37b85da4f380783a827490cc2e452b72f77` | 58 686 | `gswin64c -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=grande_60p.pdf _pagina_densa.pdf _pagina_densa.pdf ...` (60 repeticiones de `_pagina_densa.pdf` como argumentos posicionales de Ghostscript; `bench/mcp-ergonomia.md` §"Reproducir"). **Requiere Ghostscript nativo de Windows (`gswin64c`)**, no instalado en este WSL. |

---

## 3. Specs (entradas del arnés, deterministas)

| Fichero | sha256 | Bytes |
|---|---|---:|
| `spec_docling.json` | `e6bc109192f6628180d2b914e1e78d0c63c75f8d946ec8a60d9a7053794604d` | 5 464 |
| `spec_docling_conv.json` | `680b5213c845206e80a1542d75d8210f15d955462720d6a1796953dfa57f3e2` | 657 |
| `spec_docling_frio.json` | `3ffdd7c5365fca3421424d45e2d8f43816695d4503827323fa79cda14e7ffb0` | 1 053 |
| `spec_docling_frio_ligero.json` | `5169d074756bd98c8bceab24a4e4213909dad55d91a8b99b34ca3831af1c39c` | 619 |
| `spec_markitdown.json` | `8ef8e6c99ebe5ff1a0368cd1d50100ac719c406e4682a448f4da5e5c744b8c2` | 3 868 |
| `spec_markitdown_frio.json` | `b7fe799dad4c4de3abc057bdc5093c7e621ecfacd0f64872798ae4affe105ea` | 806 |

## 4. Resultados crudos, `stderr` y volcados de contenido

`(*)` = requiere el lock de GPU (`gpu_acquire "mcp"` / `gpu_release`, `bench/lib/harness.sh`)
porque `docling-mcp` carga modelos en la RTX 3060.

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `res_docling.json` | `5c1147947de6bc5edc3f6b176f6c0c95571c587976c82bc6290e9053edd0eca` | 33 206 | `(*)` `.venv-ai/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_docling.json bench/salidas-mcp/res_docling.json` |
| `stderr_docling.log` | `4c456438e5381badab003c6b48184399f57ca0c3055abb1d3c0458866f18f0b` | 105 539 | idem (lo escribe el propio servidor docling-mcp durante esa ejecución) |
| `dl_peq.md` | `ef720109c2d8d20a15b8055e485b636800b40bf1abc70e58df139e128f8a0ff` | 233 | idem — paso `export_peq` de `spec_docling.json` (`document_key` de `peq_1_frio`) |
| `dl_grande.md` | `96875ff37957445c1e0b6af5dfe39f75ec117d2600beb35f927047887d8de50` | 410 290 | idem — paso de exportación del PDF de 60 páginas |
| `dl_grande_anclas.txt` | `06b16f3d7456572dbe001441144e62196759dad70735b32ad0ea3f6ca078412` | 7 769 | idem — paso de recorte/anclas sobre el mismo documento grande |
| `res_docling_conv.json` | `de1c6e7c8f87fb81099e3b0b76ba6b1ac5ff097f6b2119f47697be59382729d` | 3 346 | `.venv-ai/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_docling_conv.json bench/salidas-mcp/res_docling_conv.json` (llamada trivial `is_document_in_local_cache`, sin GPU — así lo anota el propio spec) |
| `stderr_docling_conv.log` | `eb228f0563311cf5b5c0a4f62f65c0c3a5a59c65d0e0e214b57ad42045b1cc0` | 223 | idem |
| `res_dl_frio_1.json` | `b821d8b493f709a336d842b0843354527e6d6b08052c71bd76ec1278389988f` | 14 714 | `(*)` `.venv-ai/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_docling_frio.json bench/salidas-mcp/res_dl_frio_1.json` — **1.ª de 2 relanzamientos completos** del proceso (mide arranque en frío, §5 de `mcp-ergonomia.md`) |
| `res_dl_frio_2.json` | `98e2b5418554036efc733390ab550fd9f0d7f2a517412b34e2993c1cf0aca58` | 14 714 | `(*)` idem, **2.ª** repetición, mismo spec, fichero de salida distinto |
| `stderr_docling_frio.log` | `10ba9f9bdedb13019d42037a5e376359fead096ed9e3d3359d0abd57038b3bd` | 43 928 | el `stderr` queda del último de los dos relanzamientos (el spec fija siempre la misma ruta de log; se sobrescribe) |
| `res_dl_frioligero_1.json` | `276dffe86f718567604b57ef6c93d30dac4487095b95e22ebf61644415e67d5` | 13 302 | `.venv-ai/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_docling_frio_ligero.json bench/salidas-mcp/res_dl_frioligero_1.json` — variante "sin conversión" (solo `is_document_in_local_cache`), **1.ª de 3** repeticiones para acotar el arranque en frío sin pagar el coste de convertir |
| `res_dl_frioligero_2.json` | `abc10a78c6bcd71d4d8f71178d6d5fdc579f9c6163ae530c01a3a4b214a3b2c` | 13 302 | idem, **2.ª** |
| `res_dl_frioligero_3.json` | `f9bab1886757e8d31f21a8289dff790b59f8b41a67250ae486cd6904124a531` | 13 302 | idem, **3.ª** |
| `stderr_docling_frio_ligero.log` | `0efa376ad9a9294e2e17d12aa1dfda22d00a9b763d1a077e565690dd218ed45` | 375 | `stderr` de la última de las tres (misma ruta fija, se sobrescribe) |
| `res_markitdown.json` | `de251ec671960daecc3d85bcef3cf675ed34a48f45537b13e7bcf4479a05821` | 12 369 | `.venv-mcp-md/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_markitdown.json bench/salidas-mcp/res_markitdown.json` |
| `stderr_markitdown.log` | `3b2cdf58bee28bac9ea3cb1fa8dd0d2c6bb748dbc0108994e8e0219eb57041c` | 1 242 | idem |
| `md_peq.md` | `7349ddc01325e64aca866b69216a1fde3f61c345da81ccc8ba89668106711e1` | 175 | idem — paso `peq_1_frio` de `spec_markitdown.json` |
| `md_grande.md` | `3d19c63e57d9eead91e5f7a6f941fd55599267a0c290161ee2abdc801d608f9` | 409 859 | idem — paso `grande_1` (PDF de 60 páginas) |
| `res_md_frio_1.json` | `e3d08a10716e912694deeddf8f9feb8ea9bc66414c563ceb963a8a3eaec225e` | 2 386 | `.venv-mcp-md/Scripts/python.exe bench/salidas-mcp/mcp_probe.py bench/salidas-mcp/spec_markitdown_frio.json bench/salidas-mcp/res_md_frio_1.json` — **1.ª de 3** relanzamientos completos del proceso |
| `res_md_frio_2.json` | `578fd7af428b5e44dfc62e41c2493a51f8ce1a9b9ed84617ce7929b92f78915` | 2 385 | idem, **2.ª** |
| `res_md_frio_3.json` | `67525c5fae9686d8cda8210d6aaf2b87ec2c0edb9c3e51261e9c289eb4c6ea5` | 2 386 | idem, **3.ª** |
| `stderr_md_frio.log` | `bd9be20326f42eba0861ebc8fcf41fdf0dd9a55674692458ebf92b2ff48f562` | 683 | `stderr` de la última de las tres |

**Sobre las repeticiones (2 para docling-frío, 3 para docling-frío-ligero y para
markitdown-frío):** `bench/mcp-ergonomia.md` §5.2 publica pares/tríos de cifras por celda
("7 213 / 6 998 ms", "91 / 74 / 87 ms"), es decir **cada número de la tabla sale de relanzar
el proceso entero desde cero**, no de repetir una llamada dentro del mismo proceso — el
arranque en frío solo se puede medir una vez por vida del proceso. De ahí el sufijo `_N` en
los nombres de fichero.

---

## 2b. Verificación de tamaño

1 arnés + 2 entradas + 6 specs + 22 salidas/logs/volcados = **31 ficheros**, que coincide
con `find bench/salidas-mcp -maxdepth 1 -type f | wc -l` (excluyendo este propio
`MANIFIESTO.md`). Dos ficheros de muestra de la tabla del §4, para no repetir el error de la
trampa 48: `res_docling.json` (33 206 B) y `md_grande.md` (409 859 B).
