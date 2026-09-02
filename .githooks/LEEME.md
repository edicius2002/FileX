# `.githooks/` — los hooks, versionados

```sh
git config core.hooksPath .githooks
```

**Esa línea hay que ejecutarla en cada clon.** Es la mitad que git no sabe versionar:
`core.hooksPath` es configuración **local**, así que los *scripts* viajan con el repositorio
y **el cable que los enchufa, no**. Decirlo aquí es más honesto que fingir que el problema
no existe — es exactamente el reparto que la auditoría del 02/09 encontró en la otra
dirección (los hooks estaban enchufados y sin versionar).

Compruébalo con `git config core.hooksPath`, que debe devolver `.githooks`.

## Qué hace cada uno

| Hook | Qué hace |
|---|---|
| `pre-push` | **Git LFS**, y después `ci/integridad.py` |
| `post-checkout`, `post-commit`, `post-merge` | **Git LFS**, y nada más |

## Por qué los cuatro llaman a Git LFS

**Porque fijar `core.hooksPath` apaga los de LFS, en silencio.** `git lfs install` escribe sus
cuatro hooks en `.git/hooks/`, y en cuanto `core.hooksPath` apunta a otro sitio **git deja de
leer ese directorio entero**. Sin la delegación:

- los binarios de `corpus/` (266 MB en LFS) **no se suben** en un `push`, y
- tras un `checkout` se quedan como **punteros de 130 B**.

Eso último es la **trampa 34** de `CLAUDE.md`: `magick` dice `improper image header`, la suite
da `15 failed, 136 passed`, **y nadie ha tocado el código**. Lo pagaron tres de los cuatro
agentes de la primera ronda. Por eso los cuatro ficheros existen aunque tres no hagan nada
propio: **un hook que falta no avisa, y este falla como un fallo de corpus.**

## Por qué la puerta está en `pre-push` y no en `pre-commit`

`ci/integridad.py` tarda unos **15 s** y comprueba cosas del **repositorio entero** —el recuento
del inventario, las citas de commit, los manifiestos, los binarios sueltos—, no del cambio que
estás haciendo. Ponerlo en `pre-commit` cobraría 15 s por cada commit de una tanda para
comprobar lo mismo n veces. En `pre-push` se paga una vez, y antes de gastar un runner.

El 02/09, sin esta puerta, dos fallos de integridad se cazaron **después** de escribir: el
recuento del inventario y un `bench/salidas-*` sin `MANIFIESTO.md`.

## Salidas de emergencia

- **Sin `git-lfs` en el PATH:** los hooks **fallan con 2 y un mensaje**, no lo pasan por alto.
  Un LFS ausente es un problema, no un detalle.
- **Sin Python:** `pre-push` lo dice y **sale con 0**. Un clon recién hecho no puede quedar
  bloqueado por una herramienta que aún no tiene, y la CI lo comprueba igual.
- **Para saltárselo a propósito:** `git push --no-verify`.
