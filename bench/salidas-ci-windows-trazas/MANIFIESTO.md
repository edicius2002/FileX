# Salidas de `bench/ci-windows-trazas.md` — las TRAZAS de `windows-latest`

Todo lo de aquí se mide **dentro de un runner `windows-latest` hospedado por
GitHub**, nunca en la máquina del proyecto: la aptitud de un entorno se mide
**en** ese entorno (trampa 104). Ejecutarlo aquí sólo vale como control de que
el instrumento funciona, y así se usó (ver abajo).

## Qué hay versionado

| Fichero | Qué es | Ejecución |
|---|---|---|
| `sonda_causa_windows.py` | Sonda de **causa**: somete a control las hipótesis que salen de las trazas (nombre corto 8.3, punteros de Git LFS), más Docker y los motores. C1 lleva tres celdas y un control positivo; C5 separa las dos capas. | — |
| `windows-hosted-medido-33826410849.json` | `ci/sonda_windows_hosted.py` **con trazas**, ANTES de las guardas: 5 módulos no aptos, **36 trazas** con su traceback. Es el estado que el informe clasifica. | 33826410849 |
| `logs-33826410849/` | La salida **íntegra** de `unittest -v` de los 18 módulos en esa ejecución. | 33826410849 |
| `sonda-causa-windows-33827215958.json` | La sonda de causa **que refutó la primera hipótesis** con su propio control negativo (`puede_leer_con_raiz_RESUELTA: false`). Se conserva porque la refutación es el resultado, no un borrador. | 33827215958 |
| `windows-hosted-medido-33827476219.json` | La medida **que respalda `ci/windows-hosted-apto.json`**: 14 aptos, 23 trazas. | 33827476219 |
| `sonda-causa-windows-33827476219.json` | La sonda de causa **con la tercera celda**, la que fija el mecanismo (`puede_leer_TODO_RESUELTO: true`). | 33827476219 |
| `logs-33827476219/` | Salida íntegra de los 18 módulos en la ejecución que se congela. | 33827476219 |

**Los `.log` y los `.json` se versionan a propósito**: son texto barato y son la
trazabilidad del informe (`CLAUDE.md` §6). No hay un solo binario aquí, y las
396 KB del directorio son texto comprimible.

## Las órdenes exactas

Disparar la medida (necesita `gh` autenticado y que el *workflow* exista en la
rama por defecto — worker4 lo midió: si no está en `main`, la API responde
`HTTP 404: not found on the default branch`):

```
gh workflow run windows-tests.yml --ref <rama> -f medir=true
gh run download <run_id> --repo edicius2002/FileX --name windows-hosted-medido
```

El artefacto trae `ci-windows-hosted-medido.json`, `sonda-causa-windows.json` y
`ci-windows-hosted-logs/`; aquí se guardan renombrados con el número de
ejecución delante, porque **una tabla sin su ejecución no es comparable**.

Control del instrumento en la máquina del proyecto — **tiene que dar
`el 8.3 NO explica el fallo` y `es_puntero_lfs: false`**, porque aquí el
`%TEMP%` es largo y el corpus está descargado. Una sonda que dijera «sí» en las
dos máquinas estaría rota (trampa 66), y ese control se corrió:

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe ^
  bench\salidas-ci-windows-trazas\sonda_causa_windows.py --json local.json
```

## Qué NO hay, y por qué

No hay salidas de conversión ni rásteres: nada de lo que se mide aquí produce
bytes que haya que guardar. El artefacto de Actions caduca solo; lo que importa
—los JSON y los logs— está versionado.
