# MANIFIESTO — `bench/salidas-mcp-refs/`

C41. Datos crudos de tres informes: `bench/mcp-refs-confinamiento.md` (confinamiento de
`@modelcontextprotocol/server-filesystem` y `kordoc`), `bench/mcp-refs-multimedia.md`
(catálogo/fidelidad de `video-audio-mcp`, `ffmpeg-mcp-lite`, `image-worker-mcp`) y, de forma
tangencial, `bench/saturacion-herramientas.md` (usa `_smoke.json`/`_smoke_spec.json` como
humo inicial). Regla §6: nombre, tamaño, sha256 y la orden exacta. **MEDIDO** salvo donde se
indique lo contrario.

**Aviso de seguridad:** varios nombres (`secreto.txt`, `dentro.txtoculto`, ataques de
travesía y symlink) son fixtures deliberadas de un arnés de confinamiento — no son secretos
reales. Dos ficheros versionados llevan un carácter Unicode de área de uso privado
(`U+F03A`) donde debería ir `:` — es la representación en disco de un nombre con dos puntos
literal (simulando un flujo alternativo NTFS), sustituido porque NTFS/Windows no admite `:`
en un componente de ruta normal; git lo versiona tal cual. Existen además, **sin versionar**,
dos ficheros con el `:` real (`dentro.txt:oculto`, `secreto.txt:oculto`, visibles en
`git status` pero no en `git ls-files`) — son residuo de una ejecución anterior en este mismo
*worktree* y no forman parte de este manifiesto ni se han tocado.

## 1. Raíz — humo de `saturacion-herramientas.md`

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `_smoke.json` | 2030 | `d7b79fce6a937d41d83ce190c3d47824684498403b9ec775c89f5c05c9ba27ce` |
| `_smoke_spec.json` | 455 | `c78b4a965029fdc63beb6a35f0f01c3402a6bf450238cb483da17005e178bd55` |

Orden: `python <cliente> bench/scripts/mcp_probe_bin.py _smoke_spec.json _smoke.json` — spec
de humo citado en `bench/saturacion-herramientas.md`; no tiene script generador propio (es un
spec mínimo escrito a mano).

## 2. `confinamiento/` — fuente escrita a mano

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `confinamiento/gen_specs.py` | 9554 | `328e5e2c363c263c7ed1ce6d42d45cf73d6de8be57d76efc2029e60dd482047d` |
| `confinamiento/gen_specs_kordoc.py` | 4070 | `2ee15a649a1eae003fec5a5498c171d651ae0be2cb40a55ee2530155a0dc4d31` |
| `confinamiento/toctou_probe.py` | 10547 | `288b6cadfeb3e0f2579dd9dbfded0777525e3f11167c2c88b13f1a5aae7b1eba` |

`toctou_probe.py` es una **variante declarada** del arnés general (`mcp_probe_bin.py` no
permite mutar el disco entre validar y leer, ni concurrencia — necesarias para la carrera del
§4 del informe); el arnés original no se tocó (`mcp-refs-confinamiento.md` §1.4).

## 3. `confinamiento/sandbox/` — fixtures de entrada (contenido literal, `mcp-refs-confinamiento.md` §1.3)

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `confinamiento/sandbox/kordoc/falso.pdf` | 45 | `348ada0c6df121e66ba9afab50b17ac940e420d3dcc0aa12c234b7ad61c7e424` |
| `confinamiento/sandbox/kordoc/imagen.png` | 42855 | `e645f85a6eec4e4d50f29f6b5336cf4916f2ed196e43913f04ca80e9bc1d0953` |
| `confinamiento/sandbox/kordoc/noformato.ini` | 22 | `a84fc3d922bd25e24cd59d2a6a71f239f851702786b454213095f059bd63120f` |
| `confinamiento/sandbox/kordoc/ok.pdf` | 3219 | `a99692f0985e6f8ae9ed0d3b1bccbc996791a574839d3ec6840913ec658b313d` |
| `confinamiento/sandbox/kordoc/truncado.pdf` | 1200 | `2bad26175a3f1fa8b2208a24a313c0735da91479fe572f889f32386a191fcef2` |
| `confinamiento/sandbox/kordoc/vacio.docx` | 128 | `162243e0945eb0e7f7e2c87c9f9a37214ecc0db5fbcb97b88f4d50d7779770d7` |
| `confinamiento/sandbox/permitido/dentro.txt` | 29 | `c0d43e6606918483a8a22621d301eae1f2069a25f833b355207a92b83eaebe85` |
| `confinamiento/sandbox/permitido/dentro.txt<U+F03A>oculto` | 22 | `931899f3d9f0e9b8fe2f7b4448a1e9a301efb551e878dc5179e0f71df9c201ab` |
| `confinamiento/sandbox/permitido/sub/anidado.txt` | 24 | `00db70a4d15c47151ba05365d036e35a0224016dd456d0c4aacdf252262a7bdb` |
| `confinamiento/sandbox/permitido_secreto/trampa.txt` | 61 | `7b9ef130380a7ae546113e0a0a9c3a96bf89b016499c19bdba2cb57e85bfa66d` |
| `confinamiento/sandbox/prohibido/secreto.txt` | 24 | `70c46a32b9f8d1bc76a3954ad6d96334e23f95a02df79145020d32feb33e8f64` |
| `confinamiento/sandbox/prohibido/secreto.txt<U+F03A>oculto` | 25 | `e13bf73ff1569bb2b8b38cbbda97609d8ac76d522ce8f6b077bbe56ae2d212b4` |
| `confinamiento/senuelo_fuera.txt` | 31 | `5996217aed99416dd43f13068250ac5cf39d46fe92150f2cd1867b60deec3647` |

Orden: contenido literal fijado a mano, citado en `mcp-refs-confinamiento.md` §1.3 (los
`<U+F03A>oculto` con `Set-Content -Stream 'oculto'` de PowerShell sobre el fichero base). Los
enlaces simbólicos y la unión (`link_interno.txt`, `link_fuera.txt`, `link_win.txt`,
`junc_fuera`) usados en la sección de symlinks previos **no se versionan a propósito** — el
árbol se entrega sin enlaces para que sea portable; se recrean con los cuatro `mklink`
citados en `mcp-refs-confinamiento.md` §1.3.

## 4. `confinamiento/specs/*.json` — generados

Orden: `python confinamiento/gen_specs.py && python confinamiento/gen_specs_kordoc.py`.

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `confinamiento/specs/01_ataques.json` | 13405 | `b82fb08da8f1815917945fa1cc956cd96ada55ecb4c1d284821dbc21a6f911f1` |
| `confinamiento/specs/02_escritura.json` | 2673 | `ee5b161679e059edb1e62c55f6c1cadcc0bb62a53131790382499c7ac6051ef9` |
| `confinamiento/specs/03_symlinks_previos.json` | 2074 | `6d2d2b463e3664724696d60920244b1d4e3f3d9ca970e14083738742372771b3` |
| `confinamiento/specs/04_kordoc_errores.json` | 4692 | `ae91ee94e31272d8532f78245af5ff3232b7f4b18796b3fa4798abf94d81eeae` |
| `confinamiento/specs/05_kordoc_root.json` | 3227 | `ff2643aac6c363976fbe70c017324c9a0791b00fae42fe934497065dc09c3920` |
| `confinamiento/specs/06_83.json` | 1254 | `73dea23534bc0bff3801cffbcfcfeb7a65448dc82dc9748e77e54c5a92615913` |

## 5. `confinamiento/salidas/*.json` y `logs/` — resultado crudo del arnés

Orden completa, citada literal en `bench/mcp-refs-confinamiento.md` §1.4:

```sh
PY=D:/Work/research/FileX/.venv-mcp-md/Scripts/python.exe
cd bench/salidas-mcp-refs/confinamiento
$PY gen_specs.py && $PY gen_specs_kordoc.py
$PY ../../scripts/mcp_probe_bin.py specs/01_ataques.json          salidas/01_ataques.json
$PY ../../scripts/mcp_probe_bin.py specs/02_escritura.json        salidas/02_escritura.json
$PY ../../scripts/mcp_probe_bin.py specs/03_symlinks_previos.json salidas/03_symlinks_previos.json
$PY ../../scripts/mcp_probe_bin.py specs/04_kordoc_errores.json   salidas/04b_kordoc_errores.json
$PY ../../scripts/mcp_probe_bin.py specs/05_kordoc_root.json      salidas/05_kordoc_root.json
$PY ../../scripts/mcp_probe_bin.py specs/06_83.json               salidas/06_83.json
$PY toctou_probe.py salidas/04_toctou.json          # A,C,B,B2 — ~50 s
```

`salidas/07_kordoc_cli_vs_mcp.txt` es la transcripción literal de comparar la CLI de kordoc
contra el MCP (§6 del informe), tecleada a mano sobre la salida de ambos, no generada por
`mcp_probe_bin.py`. `salidas/stderr_*.txt` son **copias** de `logs/*.log` hechas para que
git las versione (los `.log` de `logs/` no van a `.gitignore`, pero el informe declara la
duplicación intencional en §1.4: "copia no ignorada por git de los `logs/*.log`").

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `confinamiento/salidas/01_ataques.json` | 67126 | `493ec7d6e43ba9a5b780b3454ab0dce0a6f1c2dea08cde0acb98c1ef03a523c4` |
| `confinamiento/salidas/02_escritura.json` | 28228 | `0e34f9075ad342a2307de73233c43ed89ae1dd2fc0801a15a4e1617369abc386` |
| `confinamiento/salidas/03_symlinks_previos.json` | 26849 | `90e3c5bc93a2191cfaa638f0e2463b8ae5dd1db6413cc3236da964eb0d139b5b` |
| `confinamiento/salidas/04_toctou.json` | 6544 | `3225d4e0aaf5f13d232ac0aac973628a363d1511a70ee8acc5d045a77b39c549` |
| `confinamiento/salidas/04b_kordoc_errores.json` | 52249 | `c2b4f1c0ff13b4fd856a7b40d1a3c24c350e04bf65eac6a2463964111355949a` |
| `confinamiento/salidas/05_kordoc_root.json` | 47260 | `be06e79d4d77dfb1c7059fca7e7f36037244fda5300fbcf8acb659cf1345853c` |
| `confinamiento/salidas/06_83.json` | 25683 | `f56f139ece4d067a2b94a4eb6b3d77bd3d2c20441837b265c10647af55a86373` |
| `confinamiento/salidas/07_kordoc_cli_vs_mcp.txt` | 1781 | `05c20d859b91b5f82fed164126c47f55804961127046fb2f9a725f20cb569d9e` |
| `confinamiento/salidas/stderr_fs_83.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_fs_ataques.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_fs_escritura.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_fs_npm_install.txt` | 41 | `d9d773c02223048d599e103c58aed492d08e5ed984c05380f15fe9e62384900c` |
| `confinamiento/salidas/stderr_fs_symlinks_previos.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_kordoc_errores.stderr.txt` | 36 | `fb264e9fc2f73ff4234a57a90f587e7d115bfe82bc57aa8651006f265b7def45` |
| `confinamiento/salidas/stderr_kordoc_npx.txt` | 141 | `a6b9013ea8b08cdc6d9533dd43565a8feaa8f6e983a386ccd39ad88360417f4c` |
| `confinamiento/salidas/stderr_kordoc_root.stderr.txt` | 117 | `8313187851ebdeb3dbc82313f19afa4dc53fec13c7a1ed1fc04a258605fc8200` |
| `confinamiento/salidas/stderr_toctou.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_toctou_AC.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_toctou_B2_carrera_ventana_ensanchada.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/salidas/stderr_toctou_B_carrera_normal.stderr.txt` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/fs_83.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/fs_ataques.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/fs_escritura.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/fs_npm_install.log` | 41 | `d9d773c02223048d599e103c58aed492d08e5ed984c05380f15fe9e62384900c` |
| `confinamiento/logs/fs_symlinks_previos.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/kordoc_errores.stderr.log` | 36 | `fb264e9fc2f73ff4234a57a90f587e7d115bfe82bc57aa8651006f265b7def45` |
| `confinamiento/logs/kordoc_npx.log` | 141 | `a6b9013ea8b08cdc6d9533dd43565a8feaa8f6e983a386ccd39ad88360417f4c` |
| `confinamiento/logs/kordoc_root.stderr.log` | 117 | `8313187851ebdeb3dbc82313f19afa4dc53fec13c7a1ed1fc04a258605fc8200` |
| `confinamiento/logs/toctou.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/toctou_AC.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/toctou_B2_carrera_ventana_ensanchada.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |
| `confinamiento/logs/toctou_B_carrera_normal.stderr.log` | 134 | `e2aed70495ea695899aa3f0204bb53a1ba6d19e963e6665af4f8d6a1df975d64` |

Los `stderr` idénticos (`e2aed704…`, 134 B) son el banner de arranque fijo de
`server-filesystem` (*"Secure MCP Filesystem Server running on stdio\nFailed to request
initial roots..."*) — es correcto que 13 ficheros distintos compartan ese `sha256`: cada
arranque del mismo binario imprime el mismo texto.

**PENDIENTE (declarado):** no reejecutado en esta ronda. `gen_specs.py` graba `BASE =
"D:/Work/research/FileX/bench/salidas-mcp-refs/confinamiento"` (ruta absoluta del checkout
principal, no de este *worktree*); reproducirlo aquí exige editar `BASE` o correr desde el
checkout principal. `toctou_probe.py` además depende de que el árbol de symlinks del §3 se
recree a mano antes de correr (los `mklink` citados arriba). El cliente `.venv-mcp-md` sigue
activo (`CLAUDE.md` §2), así que esta parte no depende de un venv podado.

## 6. `multimedia/` — fuente escrita a mano

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/gen_specs.py` | 11429 | `2e5c8ab5a78f2ce32c760486396aafb64203beda2775ae038ff415f32e4fcb22` |
| `multimedia/verificar_salidas.py` | 5332 | `8df5e563ef38f88e38bc02e649b425bd14ce0f036d2e2c4c709e6c8b213751ca` |

Orden para las 6 fases: `python multimedia/gen_specs.py <fase>` con `<fase>` en
`catalogo | conversion | errores` (o `todas`), citado en la propia cabecera del script.

## 7. `multimedia/*.spec.json`, `*.json`, `*.stderr.log` — resultado por fase

Orden por spec (patrón repetido, `mcp-refs-multimedia.md` §10):
`python <cliente-del-servidor> bench/scripts/mcp_probe_bin.py multimedia/<nombre>.spec.json multimedia/<nombre>.json 2> multimedia/<nombre>.stderr.log`.

| Fichero (spec) | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/cat_img.spec.json` | 511 | `a7a3fe04fbda9e0bfb803898ea9b4f4430b2018c6a02acc5ae0086c18d00c20d` |
| `multimedia/cat_lite.spec.json` | 408 | `8c5dbef52deb031ef1f11bb742c4c085bcbb98a02b4f3f17e143bce0234c0924` |
| `multimedia/cat_vam.spec.json` | 349 | `4ac3d9e43ead90a2ea46a10287d440488290ac2eb8c604acf92229fa62a93003` |
| `multimedia/conv_img.spec.json` | 2994 | `1c33e07d1de8a61a16918dc4a0d5fc7114e14a6c5c223ac15b08fe6efeeeb38c` |
| `multimedia/conv_lite.spec.json` | 1955 | `c1673972919f51cc363816e44c6a172bee65e140e826c80a0f1c093eeecbd526` |
| `multimedia/conv_vam.spec.json` | 2303 | `d2c4535bb06712030409e8b690335dc4b92f5250ce0f047bc349470bf6c1c4dc` |
| `multimedia/deadlock_vam.spec.json` | 784 | `c3d47a8da3fa605a874a39c0a2c52722223db62ded9763ffedbc308e85dd5a05` |
| `multimedia/err_img.spec.json` | 1413 | `0ca9468d5d07b25aca8ecb723a96f0b7d05618ad9f040e8effcd529c5e982471` |
| `multimedia/err_lite.spec.json` | 1034 | `ce02daedca99a55bf47996c90586f06758ad2e7989a6f33ab84254a73ee67299` |
| `multimedia/err_vam.spec.json` | 1338 | `ea63d9e89afb9e73a1ef9012884ffc858c071950128ce249de9b765cc1ba5e52` |

| Fichero (resultado) | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/cat_img.json` | 7774 | `08b7691ea37668e08ad5602f28c66c57d813b39c35d25cafac847c7ef3ed72eb` |
| `multimedia/cat_lite.json` | 14827 | `1aff1a91d21caa0af6df26392e9237a547b9ba9bc7d6c43da3d06a506babf0bd` |
| `multimedia/cat_vam.json` | 46332 | `1e02926e22e3cf631c9dbadb6a31aa775ab788979748521d464dbadace1d96c3` |
| `multimedia/conv_img.json` | 20488 | `b08a124e60a3619ff70361a9a5dc2848a1d7acca8e65675e1f325aae9912f15e` |
| `multimedia/conv_lite.json` | 24990 | `a5f738b65d24b220b859f1c965d5ac3a08e62383f3534840c6aa0b0659f50408` |
| `multimedia/conv_vam.json` | 55276 | `603c61474c5ff1b34a0637097a2facbec843d2b8551888d65dcc0c2263ef527b` |
| `multimedia/err_img.json` | 10979 | `6dd6400b3dc030c0c010a19f02003101e9f8745885c57a848bc3b35c8bdf3dcc` |
| `multimedia/err_lite.json` | 20037 | `1cca8c6630ba1ab8cd3d3d34841b664f04029516fb793a0bc1555dd79d12f6ab` |
| `multimedia/err_vam.json` | 56035 | `f67b4e3e142c6e6dfab1b27c8d3bba0b9ca6e9f132afbe7a7130e3e83d1f894b` |
| `multimedia/verificacion.json` | 5848 | `0442620b323f32682a00b2dd6bbd10f715fe895452268c8de6ba25e2c8501fba` |

`verificacion.json` es la salida de `python multimedia/verificar_salidas.py` (fase 2c,
bytes mágicos + `ffprobe`/`magick` sobre `salidas/` y `salidas_lite/`), no de
`mcp_probe_bin.py`. **`deadlock_vam.json` no existe a propósito**: la sesión murió antes de
poder escribirlo — esa ausencia es la evidencia del bloqueo de §4.1 del informe, y por eso no
aparece en esta tabla (no falta un fichero: nunca lo hubo).

| Fichero (stderr) | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/cat_img.stderr.log` | 41 | `f1f1c90a968e198572d2a8c920454a5e70682d89053a6a795f5ed7f1c98740ad` |
| `multimedia/cat_lite.stderr.log` | 556 | `cbf340bcbff24d7ee3da10f5929841cc01685a837d5b9b7c192d37b53d199c20` |
| `multimedia/cat_vam.stderr.log` | 897 | `6ff171beb18c4b7591dce9c99223ef9cf8888e8b76537be15d2dd5cf9c0d60d8` |
| `multimedia/conv_img.stderr.log` | 41 | `f1f1c90a968e198572d2a8c920454a5e70682d89053a6a795f5ed7f1c98740ad` |
| `multimedia/conv_lite.stderr.log` | 857 | `53f8b151e24238fc531d6d20e02ca1a2646425167224646d3262206978775c1e` |
| `multimedia/conv_vam.stderr.log` | 1857 | `ba5963fc05c28dadadfd2bf92fa730e84c4afb68641ae494ac37f405925d44fa` |
| `multimedia/deadlock_vam.stderr.log` | 1057 | `7aa1bada84c19d197f3675f813c75984ce384a9285d140e755833c8a76ea55d7` |
| `multimedia/err_img.stderr.log` | 41 | `f1f1c90a968e198572d2a8c920454a5e70682d89053a6a795f5ed7f1c98740ad` |
| `multimedia/err_lite.stderr.log` | 685 | `247d33fbdcb964da5de630b3341d53290424c42cc2cbc3b03b8e09d2a814d511` |
| `multimedia/err_vam.stderr.log` | 1377 | `41c1ab5bf40d46ae28227ac7656396d5d4a146047cf26ca314ad0cc2b2054aad` |

Los tres `stderr.log` de 41 B idénticos (`f1f1c9…`) son de `image-worker-mcp` (`npx`), que no
escribe nada por `stderr` en ejecución normal salvo su banner mínimo.

## 8. `multimedia/corrupto/` — fixtures truncadas a mano

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/corrupto/truncado.jpg` | 200 | `e4d76b5b54cf7c830d4b03af8c9116925c3843bd41dba36db7d30e897ea8ffe9` |
| `multimedia/corrupto/truncado.mp4` | 40000 | `9e43490f1df7bac24d95fed6a8d5bee939f5170e3b21f0fdeedfe5eaab4df429` |
| `multimedia/corrupto/truncado.png` | 150 | `3253964d7644a4749eeb2bbac026d4bc06e3d08572076b7ad80c0c8700f07ea4` |

**PENDIENTE (declarado):** el informe no fija el punto de corte exacto de cada truncado
(cuántos bytes se retienen de qué fuente); no hay una orden de una línea que reproduzca estos
tres bytes a bytes. Se conservan por ser las fixtures reales usadas en la fase 4 de errores.

## 9. `multimedia/repro/` y `multimedia/salidas*/` — reproducción del deadlock y conversiones

| Fichero | Bytes | SHA-256 | Origen |
|---|---:|---|---|
| `multimedia/repro/t.gif` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `ffmpeg -i trivial.mp4 -c:v copy -c:a copy -f gif t.gif` **sin** `-y`, stdin=tubería abierta y muda → intento primario falla, deja 0 B (§4.1) |
| `multimedia/repro/dead.gif` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | mismo mecanismo, a través del protocolo MCP real (spec `deadlock_vam.spec.json`) |
| `multimedia/repro/stderr_ffmpeg_tipico.txt` | 2992 | `6209248614f79a73891a13a1c15786371c536271d56a49ed0266b70cb8efcb59` | volcado de banner ffmpeg de 1037 tokens citado en §7.1 |
| `multimedia/salidas/vam_dead.gif` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | mismo 0 B, vía spec de conversión real |

`e3b0c442…` es el `sha256` del fichero vacío (0 B) — coincide en los tres por construcción,
no por copia: cada uno es la evidencia independiente de un intento que se quedó en 0 bytes.

Conversiones completas (con `-y`, terminan en 1,4 s según el informe):

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `multimedia/salidas/img_tipico.png` | 7008 | `7cd9b280d311f7e787614dd0d907a35d163fcb811213533108a03cf1dd3bee5d` |
| `multimedia/salidas/img_tipico.webp` | 3564 | `2a7a15b6db43409a31a6ec4fa3f56e4babd5f983098fa8edd3fb1718a0192426` |
| `multimedia/salidas/img_tipico_c.png` | 7008 | `7cd9b280d311f7e787614dd0d907a35d163fcb811213533108a03cf1dd3bee5d` |
| `multimedia/salidas/img_tipico_c.webp` | 3564 | `2a7a15b6db43409a31a6ec4fa3f56e4babd5f983098fa8edd3fb1718a0192426` |
| `multimedia/salidas/img_trivial.webp` | 1214 | `15466de1aeffcf867cf7a1fd28894e0dc5b400df0755478e2b4d7b6eccef2b5b` |
| `multimedia/salidas/img_trivial_c.webp` | 1214 | `15466de1aeffcf867cf7a1fd28894e0dc5b400df0755478e2b4d7b6eccef2b5b` |
| `multimedia/salidas_lite/tipico_converted.mp3` | 160825 | `b4001e575dc11358d49020c9a1f9bf912a4f8713b18a8cd45962a0b1919b24bf` |
| `multimedia/salidas_lite/trivial_converted.flac` | 104318 | `b4950a7155d749deb68c894e96143194e1b6767895549ad33a9c3ec05717e684` |

Los pares `_c` con el mismo `sha256` que su original (`img_tipico.png`≡`img_tipico_c.png`,
`img_tipico.webp`≡`img_tipico_c.webp`) son el control-vs-catálogo de §6.0 del informe: la
misma conversión pedida de dos formas distintas produce bytes idénticos, que es justo lo que
esa sección mide.

~~**Deuda YA congelada, no de este manifiesto:** `multimedia/salidas/vam_trivial.mkv` (552079 B),
`multimedia/salidas_lite/trivial_converted.gif` (2290244 B) y
`multimedia/salidas_lite/trivial_converted.webm` (559046 B) son los **3 binarios sueltos**
que `ESTADO-Y-REPARTO.md` fila **C40** deja abiertos a propósito: *"salidas de terceros con
byte declarado y sin orden que las reproduzca"*. Siguen listados en
`ci/heredado.json["binarios"]`; este manifiesto **no** inventa una orden bit-exacta para
ellos — `video-audio-mcp`/`ffmpeg-mcp-lite` invocan códecs con metadatos de timestamp que no
garantizan reproducibilidad byte a byte, y C40 ya lo declaró así. Se listan aquí por
completitud del directorio, con sha256/tamaño (**MEDIDO**) y la orden *en principio* que las
produjo (`python multimedia/gen_specs.py conversion` → specs `conv_vam`/`cat_vam`/`err_lite`
→ `mcp_probe_bin.py`), marcada explícitamente **sin garantía de bit-exactitud**.~~

**C40 CERRADO el 03/09/2026 por worker2 (ronda 6), y por las DOS vías, no por una — trampa 106
obliga a decidir cada uno, no a perdonarlos en bloque:**

- **`trivial_converted.gif` estaba mal clasificado y se BORRÓ.** `ffmpeg-mcp-lite` no invoca
  códecs con parámetros propios para GIF: su fuente (`repos/mcp-refs/ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/tools/convert.py`)
  arma el comando `[ffmpeg, -i, <entrada>, -y, <salida>]` **sin un solo flag de códec o filtro**
  cuando no se piden — MEDIDO leyendo la fuente, no adivinando. Con el `ffmpeg` nativo de este
  proyecto (N-121159) y `corpus/video/trivial.mp4`, `ffmpeg -i corpus/video/trivial.mp4 -y
  <salida>.gif` reproduce el fichero **byte a byte**: mismo tamaño (2 290 244 B) y **mismo
  `sha256`** (`03f07fa2…`) que el que estaba versionado, sin necesitar el venv `.venv-mcp-lite`
  que `CLAUDE.md` §2 ya lista como borrado. El fichero se quitó de `git` (regla §6: es
  regenerable) y la orden de arriba es la que lo reproduce.
- **`vam_trivial.mkv` y `trivial_converted.webm` SÍ son irreproducibles, y ahora con mecanismo
  medido, no supuesto.** El muxer Matroska (WebM es su mismo perfil) de `libavformat` escribe un
  **UID EBML aleatorio** en cada mux — MEDIDO el 03/09/2026: dos conversiones `mp4→mkv` **con
  `-c copy`** (sin reencodificar, con el `ffmpeg` nativo de este proyecto, mismo comando, mismo
  fichero de entrada) dan el **mismo tamaño exacto** (552 079 B, igual que `vam_trivial.mkv`) y
  **`sha256` distinto**, con el primer byte que difiere siempre en el mismo desplazamiento
  relativo (el campo `SegmentUID`/`TrackUID`, offset ~0xDA). No es un problema de venv ni de
  versión de `ffmpeg`: **el formato en sí no garantiza reproducibilidad byte a byte**, ni con
  `-c copy`. Pasan a `ci/evidencia-irreproducible.txt`, con la medida citada
  (`bench/pcd-y-memoria.md` §4). `ci/heredado.json["binarios"]` queda **vacío**.

| Fichero | Bytes | SHA-256 | Estado |
|---|---:|---|---|
| `multimedia/salidas/vam_tipico.mp3` | 160825 | `b4001e575dc11358d49020c9a1f9bf912a4f8713b18a8cd45962a0b1919b24bf` | versionado |
| `multimedia/salidas/vam_trivial.flac` | 104318 | `b4950a7155d749deb68c894e96143194e1b6767895549ad33a9c3ec05717e684` | versionado |
| `multimedia/salidas/vam_trivial.mkv` | 552079 | `46eaa170a8ba11c560913430004e7da4723ec8c135919ec5574bc9a95df4bc82` | versionado — declarado en `ci/evidencia-irreproducible.txt` |
| `multimedia/salidas/vam_wav.mp3` | 64591 | `04b12a569ebe74fbda11b5e8b72e8e848fd6ae0eaec8ad4633d0bb902d087549` | versionado |
| ~~`multimedia/salidas_lite/trivial_converted.gif`~~ | ~~2290244~~ | ~~`03f07fa28389cb574bb995ba91a3747409888dca9378da4eff07de2cb99927e7`~~ | **BORRADO 03/09/2026 — reproducible, ver arriba** |
| `multimedia/salidas_lite/trivial_converted.webm` | 559046 | `430f474f66582865d3820dcf63a60dd857ad6f96deac13042e7a7a1cea0c8436` | versionado — declarado en `ci/evidencia-irreproducible.txt` |

**PENDIENTE (declarado, todo §6-9):** no reejecutado en esta ronda. `multimedia/gen_specs.py`
graba `RAIZ = "D:/Work/research/FileX"` y lanza `.venv-mcp-vam/Scripts/python.exe` y
`.venv-mcp-lite/Scripts/python.exe` — **los dos venvs están en la lista de borrados de
`CLAUDE.md` §2** (`.venv-mcp-vam`, `.venv-mcp-lite`, 31/08). Reproducir esta sección hoy pide,
en este orden: (1) editar `RAIZ` para apuntar a este *worktree* o correr desde el checkout
principal, y (2) rehacer ambos venvs con un `pip install` (mismo patrón que
`confinamiento-multimedia.md` §7 documenta para `.venv-mm-ffmpeg`/`.venv-mm-vamcp`) — coste
declarado, no bloqueo silencioso.

## Verificación de este manifiesto

`sha256sum` y tamaño de los 109 ficheros de `git ls-files bench/salidas-mcp-refs`
recalculados el 01/09/2026 contra el árbol de trabajo actual — **MEDIDO**. Cobertura: 109/109
ficheros versionados aparecen en alguna tabla de este documento (verificado con un script que
compara el conjunto de `git ls-files` contra el conjunto de filas emitidas).
