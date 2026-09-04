# MANIFIESTO — bench/salidas-symlink-toctou

Salidas de `bench/symlink-toctou.md` (worker12, ronda 21, carril `cpu/symlink-toctou`).
Todo es texto (scripts + resultados JSON), así que se versiona entero (`CLAUDE.md` §6).

| Fichero | sha256 (16) | Tamaño | Qué es |
|---|---|---|---|
| `c5_toctou.py` | `53bb666f09eb64ec` | 12 231 B | Arnés: carrera symlink-TOCTOU contra el servidor de referencia `servers/filesystem` + controles |
| `c5_filex.py` | `7215296fc3813146` | 7 524 B | Arnés: la misma carrera contra el primitivo real de FileX (`Confinamiento.resolver`) |
| `c5_toctou.json` | `5620f69e2343775d` | 2 338 B | Resultado de la tanda de 12 s del servidor de referencia |
| `c5_filex.json` | `63a801eceed83035` | 1 826 B | Resultado de la tanda de 12 s del primitivo de FileX |

## Cómo se reproduce (DENTRO de WSL2 — trampa 77: invocar por ruta, no `bash`)

Requisito: el servidor de referencia construido (ya lo estaba, `Aug 20`):
`repos/mcp-refs/servers/src/filesystem/dist/index.js` (`node v24`, `node_modules` presente).
Si faltara: `cd repos/mcp-refs/servers/src/filesystem && npm install && npm run build`.

```sh
# desde Windows, entrando a WSL explícitamente:
wsl.exe -e sh -c 'cd /tmp && C5_DUR=12 timeout -k 5 300 python3 \
  /mnt/d/Work/research/FileX/.claude/worktrees/<worktree>/bench/salidas-symlink-toctou/c5_toctou.py'
wsl.exe -e sh -c 'cd /tmp && C5_DUR=12 timeout -k 5 300 python3 \
  /mnt/d/Work/research/FileX/.claude/worktrees/<worktree>/bench/salidas-symlink-toctou/c5_filex.py'
```

## Advertencia sobre los sha256 de los `.json`

**El número exacto de wins depende del timing y NO es reproducible al byte** (`CLAUDE.md`
§3: las cifras absolutas de tandas distintas no son comparables; las relativas DENTRO de
una tanda, sí). El sha256 de los dos `.json` es el de la tanda commiteada, no una garantía
de reproducibilidad. Lo que SÍ se reproduce es el **signo**: el patrón vulnerable gana
(>0 %) y el patrón seguro gana 0 %, en cada tanda. Medido dos veces cada arnés (2 s y 12 s).

## Sistema de ficheros

`/tmp` en esta WSL2 es **tmpfs** (no ext4), declarado en cada JSON (`fs_tmp`). Para este
vector basta que `rename`/`unlink` sobre directorios y symlinks no tengan bloqueo
obligatorio, que tmpfs cumple igual que ext4 (trampa 41: no se extrapola el rendimiento,
pero la semántica de "sin bloqueo obligatorio" es la misma clase). `/mnt/d` es `v9fs`.
