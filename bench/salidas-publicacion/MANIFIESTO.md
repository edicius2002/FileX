# Publicación del repositorio — 31/08/2026

## `commit-map-20260831.txt`

Las **64 parejas `viejo → nuevo`** que produjo el `git filter-repo --replace-text` con el
que se borró la credencial de SnapOtter de las 65 revisiones. Copiado de
`.git/filter-repo/commit-map`, que **no se versiona y se pierde con cualquier clon nuevo**.

**Por qué está aquí.** La reescritura mató **todos** los hashes anteriores al 31/08, y el
repositorio los citaba: 16 citas en 9 ficheros, **0 de ellas resolvía**. Con este mapa se
repararon las cuatro que eran de FileX; la quinta —`e1a6226`— **no es de este repositorio**,
es del clon de marker, y por eso no resuelve y no hay que repararla. Sin el mapa, ninguna
de las dieciséis se podía reparar sin adivinar.

| Vieja | Nueva | Commit |
|---|---|---|
| `1fb5024` | `dcd4057` | Doce mediciones y la consolidación de los maestros |
| `3707751` | `c2f6a59` | Hitos 3 y 4, y W9 cerrado dentro del propio núcleo de FileX |
| `69f08df` | `13181f6` | La arista tenía una sexta dimensión y le faltaba: la huella |
| `7b90175` | `907de96` | LOS SIETE HITOS, HECHOS |

## Lo que se borró de `.git/filter-repo/`, y por qué — MEDIDO

`fast-export.original` (57 110 035 B) **conservaba las 48 ocurrencias de la credencial**:
exactamente las que el `--replace-text` había quitado del historial. No está en la base de
objetos y **no se empuja**, pero vive dentro de `.git`, así que viaja en cualquier copia del
directorio o `tar` del repositorio. `fast-export.filtered` (56 902 401 B) tiene **0**, y es
peso muerto igual.

**Borrar el historial no borra el residuo de la herramienta que lo borró.** Se conserva
`commit-map` —5 293 B, `0` ocurrencias, comprobado— porque es la única trazabilidad de la
operación, y se copia aquí para que sobreviva al clon.

Reproduce el control:

```sh
grep -c 'FileXBench2026aZ' .git/filter-repo/fast-export.original   # 48
grep -c 'FileXBench2026aZ' .git/filter-repo/commit-map             # 0
```

> **La credencial sigue viva en el contenedor.** Borrarla del repositorio no la cambia en
> SnapOtter: eso es una acción aparte y **sigue PENDIENTE**.
