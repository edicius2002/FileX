# Cómo se trabaja en FileX

Proyecto de investigación **en español**. Informes, comentarios y mensajes de commit,
en español.

Este fichero es la versión corta y operativa. Las reglas completas —y las **104 trampas ya
pagadas**— están en [`CLAUDE.md`](CLAUDE.md), que es el documento más útil del repositorio
si vas a tocar algo. El reparto del trabajo vive en
[`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md).

---

## 1. Lo primero: qué NO puede comprobar la CI

Esto va delante de todo lo demás, porque una CI verde que no cubre lo que importa es peor
que no tener CI: es un **falso verde**, y el repositorio ya tiene medido lo que cuesta uno
(trampas 94 y 101).

| Lo que se ejecuta en GitHub | Lo que **sólo** se ejecuta en la máquina del proyecto |
|---|---|
| Las nueve comprobaciones de `ci/integridad.py` | **Las pruebas `win32`**: `os.replace` como cerrojo, el mutex `Global\`, la DACL, los nombres 8.3 — es decir, **casi todo el valor del proyecto** |
| La parte de la suite que corre en Linux sin corpus — **hoy informa, no bloquea**: la lista de aptos está medida en WSL2 y en el runner no se sostiene (C42, trampa 104) | Todo lo que toca la **GPU**: el lock, los seis motores de OCR, el sidecar |
| Que el paquete importa y la CLI arranca | Los **contenedores locales**: `filex-c13`, SnapOtter, ConvertX, Gotenberg |
| | Todo lo que lee el **corpus**, que son 254 MB en Git LFS |

**Un `✅` de GitHub no dice que la medición esté bien.** Dice que la documentación es
coherente y que el código sigue importándose en Linux. La medición se acepta ejecutando la
suite en Windows con Docker levantado, y el resultado se declara en el PR.

> **Por qué no hay un runner que lo haga.** Hace falta una RTX 3060 con su driver, un
> Windows con NTFS —para `os.replace`, los ADS y los nombres 8.3—, y cuatro contenedores
> construidos a mano. Un runner alojado de GitHub no tiene ninguna de las tres cosas. Un
> runner **autoalojado** en esta máquina sí podría, y es una decisión abierta: expondría el
> escritorio del usuario a cualquier PR de un tercero, que es exactamente lo que un
> repositorio público no debería hacer sin pensarlo.

---

## 2. Los carriles

El reparto **no se turna, se reparte por recurso**. Es exclusión **estructural** en vez de
cooperativa, que es la lección de las trampas 33 y 90: si dos agentes nunca quieren la
misma tarjeta, no hay lock que coordinar.

| Carril | Recurso | Módulos que POSEE |
|---|---|---|
| `gpu/…` | La RTX 3060, con lock | `filex/gpu.py`, `filex/sidecar.py`, `bench/lib/harness.sh` |
| `cpu/…` | CPU y Docker | `filex/verificador.py`, `filex/motores.py`, `filex/api.py`, `filex/nucleo.py` |
| `nucleo/…` | Ninguno exclusivo | Cambios que cruzan carriles: se acuerdan antes |
| `orden/…` | Ninguno | Sólo documentación e inventario |

**Nadie toca los módulos de otro carril.** Y **un fichero de salida por agente**: dos
agentes no escriben nunca el mismo fichero.

Nombra la rama por su carril: `gpu/psm-suelo-ppp`, `cpu/g6-y-acuerdo-ocr`.

---

## 3. Marca cada afirmación MEDIDO o PENDIENTE

No es opcional: es lo que hace útil este repositorio.

- **MEDIDO** — hay un número, con `n`, y la orden que lo reproduce.
- **PENDIENTE** — se cree, se deduce o se ha leído en una documentación. No vale como base
  de una decisión.

**Reporta los fallos como fallos.** Un «no se pudo instalar» documentado mide el coste real
de integración, que es justo lo que hay que saber. Y **refutar una conclusión propia es el
resultado más valioso que puedes traer**: varios de los mejores hallazgos de aquí son
autocorrecciones.

---

## 4. El recuento de una suite necesita CUATRO declaraciones

Un `0 failed` no significa nada por sí solo. Hace falta decir las cuatro cosas, y esto está
medido (trampas 94 y 101):

1. **El intérprete.** Un `414 passed` con Python de WSL y un `408 passed` con el
   `python.exe` de Windows **miden cosas distintas**: las seis pruebas `win32` sólo corren
   con el segundo.
2. **El entorno.** Sin demonio de Docker, 12 pruebas **se saltan**: el hito 5 entero y la
   cancelación real de contenedor. Con Docker: `420 passed · 2 skipped · 0 failed`.
3. **Qué quedó fuera, y por qué.** Un salto honesto se declara; uno silencioso es un
   agujero.
4. **El estado de la máquina.** `test_cancelacion_procesos` dio **2 failed** en una tanda de
   544 s con la CPU al 50 %, y **15 passed en tres pasadas seguidas** con la máquina
   tranquila. Y el lock de GPU tomado por otro hace caer una prueba **que debe caer**.

Pega las cuatro en el PR. La plantilla ya las pide.

---

## 5. Antes de creerte un rojo

Tres formas de falso rojo, las tres pagadas:

- **El corpus son punteros de LFS.** Un worktree nuevo da `15 failed, 136 passed` sin que
  nadie haya tocado el código. `git lfs checkout` lo arregla, del almacén local y sin red
  (trampa 34).
- **El activo que juzgas no está versionado.** Las 53 salidas del patrón oro no existen en
  un clon: `referencia.json` trae la ruta absoluta y se remapea por nombre base
  (trampa 89).
- **El activo está PODADO CON SU ORDEN.** Mira el `MANIFIESTO.md` antes que el disco. Un
  rojo se investiga; un **bloqueo** se acepta, y esa asimetría lo hace más caro
  (trampa 95).

Y antes de culpar a un cambio: `git diff --stat <antes> <después> -- filex/ pruebas/`. Si
sale vacío, «lo rompió el merge» es imposible.

---

## 6. Peso del repositorio

**No versiones salidas binarias regenerables.** El repositorio ya pagó una vez este error:
986 MB de pack, 99,9 % binario.

Si generas salidas, **borra las grandes al terminar** y deja un `MANIFIESTO.md` con nombre,
`sha256`, tamaño y **la orden exacta que las reproduce**.

`ci/integridad.py` lo comprueba con un **trinquete**: la deuda de hoy —10 binarios sueltos
y 20 directorios sin manifiesto— está congelada en `ci/heredado.json` y no rompe nada, pero
**lo nuevo rompe**. Y lo **arreglado** también, para obligar a encoger la lista: sin esa
tercera mitad el trinquete se afloja solo.

El `corpus/` está en Git LFS. Tras clonar: `git lfs pull`.

---

## 7. El flujo de un cambio

```sh
git switch -c gpu/lo-que-sea        # el prefijo es el carril
python3 ci/integridad.py            # segundos, y evita el 80 % de los rechazos
# … el trabajo, y su informe en bench/ …
git push -u origin gpu/lo-que-sea
gh pr create                        # la plantilla pide las cuatro declaraciones
```

En el PR:

- **El informe va en `bench/`, uno por agente**, y se registra en la tabla de §1 de
  `ESTADO-Y-REPARTO.md`. `ci/integridad.py` falla si no está.
- **Mueve las filas del inventario** que cierres, y actualiza la línea «Salida esperada
  hoy». La CI comprueba que el recuento declarado y el medido coincidan.
- **Si añades una trampa**, va **al final**, nunca en medio: renumerar desplaza citas de
  ocho documentos y este repositorio ya lo pagó una vez. Actualiza el número en `README.md`
  y en §10 de `ESTADO-Y-REPARTO.md`; la CI comprueba que los tres coincidan y que no haya
  huecos.
- **No cites un hash sin comprobarlo.** `git cat-file -e <hash>`. La CI lo hace por ti, y
  si el hash es de otro repositorio decláralo en `ci/citas-ajenas.txt` con una línea que
  diga de dónde sale.

---

## 8. Reglas de invocación que no se negocian

Salen de la evidencia, no del gusto. Están enteras en `CLAUDE.md` §5.

- Motores como **proceso separado, sin shell**, argumentos en array y `stdin=DEVNULL`.
- **Verificar la salida siempre**, en cinco puntos — y el quinto **no se puede verificar a
  posteriori**: hay que estar mirando cuando el motor escribe.
- **Timeouts explícitos, y DENTRO de la orden.** Un tope que sólo mata al cliente no es un
  tope: tres `soffice` colgados sobrevivieron 37 minutos al `taskkill` del padre.
- **Directorio de trabajo desechable por conversión.** Hay motores que escriben en el `cwd`.
- **Sondear capacidades en ejecución, no deducirlas.** `av1_nvenc` aparece listado y no
  funciona.
- **Nunca devolver `stderr` crudo al modelo.**
- **Dos intentos por problema**, luego documenta el error exacto y sigue. Nada de bucles de
  reintento.
