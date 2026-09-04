# Salidas de `bench/ci-windows-trazas.md` — las TRAZAS de `windows-latest`

Todo lo de aquí se mide **dentro de un runner `windows-latest` hospedado por
GitHub**, nunca en la máquina del proyecto: la aptitud de un entorno se mide
**en** ese entorno (trampa 104). Ejecutarlo aquí sólo vale como control de que
el instrumento funciona, y así se usó (ver abajo).

## Qué hay versionado

| Fichero | Qué es | Cómo se reproduce |
|---|---|---|
| `sonda_causa_windows.py` | Sonda de **causa**: somete a control las dos hipótesis que salen de las trazas (nombre corto 8.3, punteros de Git LFS), más Docker y los motores. C1 lleva control negativo y positivo; C5 separa las dos capas. | `python bench/salidas-ci-windows-trazas/sonda_causa_windows.py --json sonda-causa-windows.json` |
| `sonda-causa-windows.json` | Su salida **en el runner**, ejecución **33830183459**. | El paso «Sondear la CAUSA…» de `.github/workflows/windows-tests.yml` con `workflow_dispatch` y `medir: true` |
| `windows-hosted-medido.json` | Salida de `ci/sonda_windows_hosted.py` **con trazas**, ejecución **33830183459** (la que respalda `ci/windows-hosted-apto.json`). | El paso «Medir módulo a módulo…» del mismo *workflow* |
| `windows-hosted-medido-33826410849.json` | La misma sonda en la ejecución **33826410849**, ANTES de las guardas de LFS. Se conserva porque es el estado que clasifica el informe: 5 módulos no aptos, 36 trazas. | Ídem, sobre el commit `94995f8` |
| `logs-33826410849/` | La salida **íntegra** de `unittest -v` de los 18 módulos en esa ejecución. | Ídem (`--logs`) |

**Los `.log` y los `.json` se versionan a propósito**: son texto barato y son la
trazabilidad del informe (`CLAUDE.md` §6). No hay un solo binario aquí.

## Las órdenes exactas

Disparar la medida (necesita `gh` autenticado y que el *workflow* exista en la
rama por defecto):

```
gh workflow run windows-tests.yml --ref <rama> -f medir=true
gh run download <run_id> --repo edicius2002/FileX --name windows-hosted-medido
```

Control del instrumento en la máquina del proyecto — **tiene que dar
`el 8.3 NO explica el fallo` y `es_puntero_lfs: false`**, porque aquí el
`%TEMP%` es largo y el corpus está descargado. Una sonda que dijera «sí» en las
dos máquinas estaría rota (trampa 66):

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ^
  bench\salidas-ci-windows-trazas\sonda_causa_windows.py --json local.json
```

## Qué NO hay, y por qué

No hay salidas de conversión ni rásteres: nada de lo que se mide aquí produce
bytes que haya que guardar. El artefacto de Actions caduca solo; lo que importa
—el JSON y los logs— está versionado.
