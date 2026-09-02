# MANIFIESTO — bench/salidas-runner-autoalojado/

Salidas de **`C44`** (`bench/runner-autoalojado.md`, worker1, commit `b582ceb`): el diseño del
runner autoalojado con aprobación manual. **Los tres ficheros son texto y se versionan** —son la
trazabilidad del informe, no bytes regenerables (regla §6 de `CLAUDE.md`)—; se listan aquí con su
`sha256` y la orden que los reproduce.

> **Este manifiesto lo escribió el maestro al consolidar, no worker1.** Lo destapó
> `ci/integridad.py` en la verificación de `C44` (`manifiestos: 1 nuevos`), que es exactamente
> para lo que existe la comprobación.

| Fichero | Bytes | `sha256` |
|---|---:|---|
| `sonda_lock_ci.py` | 5 470 | `cea93d65cd6474985fd98122d2d000dbdac5fc9374a7b4796ceccc8c59147196` |
| `sonda_lock_ci.json` | 1 206 | `34e614bfecc3132153ce665e1bab0a9b03cd825ba07ec0e35c28af1861049f34` |
| `windows-local.json` | 3 704 | `b1252f72d132a46f09b7845cbd234e950d54ac579da09cd4dc274f4ccd099063` |

## Qué es cada uno

- **`sonda_lock_ci.py`** — el arnés. Mide el preflight del lock de GPU tal como lo usaría un job
  de CI: coste de `tomar`/`soltar`, **control negativo** (un dueño vivo real no se roba) y
  **control positivo** (`taskkill /F` sobre un proceso real y el huérfano se recupera). Es
  código, no salida: se versiona por sí mismo.
- **`sonda_lock_ci.json`** — su salida.
- **`windows-local.json`** — el censo de módulos aptos **en Windows local**, producido por
  `ci/sonda_windows.py`. **No es la lista del runner** y por eso `C44` **no** escribió
  `ci/windows-apto.json`: la aptitud de un entorno se mide *en* ese entorno (trampa 104), y el
  runner todavía no existe.

## Órdenes que los reproducen

Desde **Git Bash de Windows** —no WSL, por la trampa 90— en la raíz del repositorio:

```
"/d/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe" \
  bench/salidas-runner-autoalojado/sonda_lock_ci.py

"/d/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe" \
  ci/sonda_windows.py
```

**Los dos `.json` no son bit a bit reproducibles**: llevan tiempos medidos y el estado de la
máquina del momento. Lo que se reproduce es el **veredicto** —los controles positivo y negativo,
y la lista de módulos aptos—, no los milisegundos. Declararlo aquí es la mitad que evita la
trampa 59: comparar un tiempo de este fichero con uno de otra tanda mide dos máquinas.
