# `bench/salidas-fix-superficies/` — carril `fix/superficies`

Datos y arneses de `bench/fix-superficies.md`. **Todo es texto**: no hay un
solo binario, así que no hay nada que podar (regla §6 de `CLAUDE.md`).

Intérprete de todas las órdenes:
`.venv-mcp-filex/Scripts/python.exe` (Windows, 3.11.9). Se declara porque una
suite y una huella dicen cosas distintas según el intérprete (trampas 94 y
105).

| Fichero | Bytes | `sha256` (16) | Orden exacta que lo reproduce |
|---|---:|---|---|
| `argv.py` | 5 211 | `cafec95f9f463d09` | *(fuente)* |
| `argv.json` | 6 385 | `a2fb3ef5aaeedcdd` | `python bench/salidas-fix-superficies/argv.py` |
| `reloj.py` | 6 143 | `1f8c6a1a479de740` | *(fuente)* |
| `reloj.json` | 1 983 | `458addde6ac86c23` | `python bench/salidas-fix-superficies/reloj.py` |
| `huella-despues.json` | 1 560 | `2f947268604956b5` | ver abajo |
| `rojo-antes.log` | 13 483 | `c5335826afddbe95` | **no se reproduce sobre este árbol**: ver abajo |

**Cuáles de estos ficheros son reproducibles AL BYTE, medido reejecutando:**
`argv.json` y `huella-despues.json` **sí** —son deterministas, y volvieron con
el mismo `sha256`—; `reloj.json` **no**, porque lleva cocientes de tiempo y
cambia en el último decimal de una tanda a otra. Lo que sí se reproduce de
`reloj.json` son sus tres veredictos: `el_arnes_dispara`,
`todas_responden_lo_correcto` y el reparto 3-de-4 contra 0-de-4. Decirlo
importa: un `sha256` que no vuelve no es aquí una señal de que algo se movió.

## `huella-despues.json`

```
python -c "import json,glob;from filex import huella;print(json.dumps({(d:=json.load(open(f,encoding='utf-8')))['motor']:{'guardada':d['huella'],'actual':(a:=huella.de_motor_por_nombre(d['motor'])),'difs':huella.diferencias(d['huella'],a),'aristas':len(d.get('aristas',{}))} for f in sorted(glob.glob('filex/sondeo/*.json'))},indent=1,ensure_ascii=False))"
```

Los tres componentes de los cinco ficheros de sellos, guardado contra actual.
**15 de 15 idénticos, 0 diferencias, 172 aristas.**

## `rojo-antes.log`

Es la traza del **rojo previo al arreglo**, y por eso es el único fichero de
aquí que **no se regenera con el árbol de hoy**: sobre el código arreglado esas
mismas pruebas salen verdes, que es justo lo que el log demuestra que antes no
pasaba. Se conserva como evidencia de orden temporal, igual que se archivan las
ramas que un informe cita de sí mismo (trampa 115). Para volver a producirlo
hay que revertir los dos ficheros de producto **con `git checkout <commit> --`,
nunca con `git stash push`** (trampa 119: sobre un fichero ya commiteado no
hace nada, devuelve 0 y no avisa):

```
git cat-file blob 95b71ded62394f8b79e963c951f3089676187fa6 > filex/api.py
git cat-file blob 7cf3ed061306ab58bdf841bd0406c5ef78842d20 > filex/cli.py
python -m unittest pruebas.test_cob_superficies.ApiCuerpoLeidoUnaSolaVez \
                   pruebas.test_cob_superficies.CliExtremoAExtremo
git checkout HEAD -- filex/api.py filex/cli.py
```

Se citan los dos **blobs**, no el commit `4333278` que los trae. No es
pedantería: un `--squash` que borre `integra/cobertura` deja ese commit sin
referencia que lo alcance y la cita muere en el `merge` (trampa 115), mientras
que **el blob sobrevive porque su contenido no cambió** (trampa 102). La orden
de arriba es además la que la trampa 119 prescribe para revertir, y da el
control de IDENTIDAD gratis: si los blobs fueran iguales a los de hoy,
`git status` saldría limpio y se vería.

## Los dos arneses declaran su control

Ninguno de los dos publica un veredicto sin comprobar que **puede** dar el
contrario (trampas 116 y 128):

* `reloj.py` conserva el `_rechazo` de antes del arreglo como
  `_Vulnerable` —el SUJETO CON EL DEFECTO, no una variante del doble— y sale
  con `rc=1` si el control positivo no agota el plazo ni una vez.
* `argv.py` conserva el detector de antes como `_viejo` y sale con `rc=1` si
  las dos versiones coinciden en las quince filas.

Los dos dieron `rc=0`.
