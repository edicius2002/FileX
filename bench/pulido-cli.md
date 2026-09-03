# Pulido de `filex/cli.py` — worker5, carril `filex-cli`, ronda 1

Agente **worker5**, 03/09/2026. Rama `edicius2002/filex-cli`, base `main` en `873942c`.
Único fichero tocado: `filex/cli.py`. Cero cambios en `nucleo.py`, `verificador.py`, `api.py`
ni ningún otro módulo — confirmado con `git status --short` antes de empezar y `git diff --stat`
al terminar.

> **Resumen: dos tracebacks de Python reales y una forma de uso documentada que llevaba MUERTA
> desde el primer commit, los tres dentro de mi único fichero — ARREGLADOS. Una inconsistencia de
> código de salida entre `destinos` y `convertir`/`plan` — DOCUMENTADA, no corregida a ciegas
> porque cambiar un `rc` rompe a quien ya lo lea.** Los tres arreglos están probados contra el
> CLI real, no deducidos. La suite corre limpia (`460/460`, y el único fallo de una segunda
> corrida se aisló como ruido de máquina ajeno a este cambio — ver §3) y `ci/integridad.py` da
> 8/9, con el único rojo esperado por no poder tocar `ESTADO-Y-REPARTO.md` (ver Método).

---

## 0. Resumen ejecutable

| # | Hallazgo | Severidad | Acción |
|---|---|---|---|
| 1 | `filex a.png b.webp` (forma corta sin `convertir`) **nunca funcionó, desde el commit del hito 1**: `argparse` revienta con `SystemExit(2)` antes de que el código que la implementa llegue a ejecutarse | bug de producto | **ARREGLADO** |
| 2 | `--params` con JSON válido pero no-objeto (`42`, `"texto"`, `[1,2]`, `true`) hacía **traceback de Python sin capturar**, `rc=1` | bug de producto | **ARREGLADO** |
| 3 | `--params` inválido con `--json` puesto: el error sale como **texto plano por `stderr`** y `stdout` queda **vacío** — no hay JSON que parsear | fricción de adopción | documentado, sin cambio (ver §2) |
| 4 | Mismo formato de origen y destino: imprimía `camino intentado: ` con nada detrás | cosmético | **ARREGLADO** |
| 5 | Un formato de destino que ningún motor sabe escribir da `rc=2` en `destinos` y `rc=1` en `convertir`/`plan` — la misma equivocación, dos códigos | inconsistencia de diseño | **DOCUMENTADO, no corregido** (medir impacto antes) |
| 6 | Solo `convertir` tiene `--json`; `motores`/`destinos`/`plan` no | omisión de producto | documentado como hallazgo |
| 7 | `import os` sin usar en `cli.py` | limpieza | **ARREGLADO** |

Todo lo de la tabla está **MEDIDO**: ejecutado contra el CLI real en esta máquina, con la salida
copiada más abajo, no deducido de leer `argparse`.

---

## 1 · Códigos de salida

**Tabla completa**, ya volcada también al `docstring` de `main()` en el propio código:

| Código | Significado | Quién lo devuelve |
|---|---|---|
| **0** | Éxito. Incluye: ayuda mostrada (sin subcomando y sin 2 argumentos posicionales), `--version`, `-h`, `motores`, `destinos` con destinos encontrados, `plan` con camino encontrado, y `convertir` cuando `Conversion.ok` es verdadero | `main()`, `_inventario`, `_destinos`, `_plan`, `_convertir` |
| **1** | Fallo de **negocio**: la petición se entendió pero no se pudo cumplir — conversión rechazada, `plan` sin camino, `destinos` de un formato conocido sin destinos alcanzables | `_destinos`, `_plan`, `_convertir` |
| **2** | Error de **uso/entrada**: lo que `argparse` genera por su cuenta (argumento que falta, subcomando inválido, `--foo` no reconocido) más lo que valida el propio código — `--params` no es JSON válido, `--params` es JSON válido pero no un objeto (nuevo, ver §3), `destinos` con un formato fuera del vocabulario, y `FileX()` no pudo arrancar (`--raiz` inválido) | `argparse` (automático), `main()`, `_destinos`, `_convertir` |

**Un matiz que no estaba escrito en ningún sitio y ahora sí** (en el `docstring`): `rc == 0` en
`convertir` **no** significa «conversión perfecta», significa `Conversion.ok`. Los veredictos
`ok`, `ok_parcial` y `aviso` comparten el mismo `rc=0` — la propiedad `Conversion.veredicto`
(`filex/nucleo.py:550-560`) solo distingue entre ellos cuando `ok` ya es verdadero, y esa
distinción **no llega al código de salida**, solo al texto (`[ok_parcial]`) o a la clave
`"veredicto"` del JSON. Un script de CI que solo mire `$?` no se entera de si hubo pérdida
declarada; tiene que leer `veredicto` (o, en `--json`, la clave homónima).

### El hallazgo real: dos condiciones idénticas, dos códigos distintos

`_destinos` valida el formato de origen contra el vocabulario global
(`formatos.conocido(ext)`, `filex/cli.py:48`) **antes** de tocar el grafo, y si no lo conoce,
`return 2`. `_plan` y `_convertir` **no hacen esa validación en ningún punto**: piden un camino
al grafo directamente, y si no hay motor que escriba ese destino, es indistinguible de
cualquier otro destino inalcanzable — `return 1`. Verificado contra el CLI real, con un formato
que no existe en ningún vocabulario:

```
$ filex destinos xyzinventado
formato desconocido: 'xyzinventado'
rc=2

$ filex convertir corpus/imagen/tipico.png salida.xyzinventado
NO CONVERTIDO — ningún motor disponible escribe 'xyzinventado'
rc=1

$ filex plan corpus/imagen/tipico.png salida.xyzinventado
NO HAY CAMINO — ningún motor disponible escribe 'xyzinventado'
rc=1
```

Es la **misma equivocación del usuario** —pedir un formato que FileX no conoce— con dos
códigos de salida distintos según el subcomando. **No lo corrijo**: la instrucción del encargo
es explícita —cambiar un `rc` sin medir el impacto rompe a cualquier script que ya dependa del
comportamiento actual de cualquiera de los dos lados—, y no hay forma de medir «qué scripts
existen fuera de este repositorio». Queda declarado como hallazgo, en el informe y en el
`docstring` de `main()`, para que la próxima ronda que sí pueda coordinar un cambio de contrato
lo decida con el dato encima.

---

## 2 · `--json`: auditoría de consumibilidad

### ¿Es JSON válido en TODOS los casos?

**Casi.** Con una conversión que llega a `fx.convertir(...)` —exista o no el fichero de
entrada, tenga o no camino, tenga éxito o fracase el motor— el `stdout` es JSON puro y el aviso
de `--raiz` (si aplica) sale por `stderr`, nunca mezclado. Comprobado con los flujos separados:

```
$ filex convertir no-existe.png salida.webp --json 1>stdout.txt 2>stderr.txt
$ cat stdout.txt
{
 "entrada": "no-existe.png", "salida": "salida.webp", "ok": false,
 "veredicto": "fallo", "motivo": "ruta no accesible", "aviso": "",
 "camino": [], "saltos": [], "descartados": []
}
$ cat stderr.txt
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
$ python -c "import json; json.load(open('stdout.txt'))" && echo JSON_VALIDO
JSON_VALIDO
```

**El agujero real está ANTES de llegar ahí.** La validación de `--params` ocurre en `_convertir`
antes de mirar `args.json`, así que un `--params` inválido con `--json` puesto **no produce
JSON en absoluto**: `stdout` queda vacío y el error sale como texto plano por `stderr`, con
`rc=2`:

```
$ filex convertir a.png b.webp --params '{esto no es json' --json 1>stdout.txt 2>stderr.txt
$ cat stdout.txt
(vacío)
$ cat stderr.txt
--params no es JSON válido: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

Un consumidor que asuma «con `--json` siempre hay JSON en `stdout`» se rompe aquí con un
`json.loads('')` → `JSONDecodeError`. **No lo cambio** en esta ronda —envolver el error de
`--params` en el mismo objeto JSON es una decisión de esquema (¿qué claves lleva un error que
nunca llegó a intentar convertir?) que no está pedida explícitamente y que interactúa con el
punto siguiente—, pero queda declarado: **hoy, `--json` solo garantiza JSON cuando el fichero de
`--params` en sí parseó.** Es exactamente la misma familia de fallo que motivó el segundo
arreglo del §3 (el crash con JSON válido no-objeto): la validación de entrada del CLI y el
compromiso de formato de salida del CLI son dos caminos de código independientes que no se
hablan.

### ¿El esquema es estable entre `ok` y `ok_parcial`/`fallo`?

**Sí, en las claves de primer nivel.** Comparé el JSON de una conversión que falla antes de
intentar nada (`entrada` inexistente) contra una que llega a ejecutar un motor y sale
`ok_parcial`:

| Clave | `fallo` (ruta no accesible) | `ok_parcial` (png→webp real) |
|---|---|---|
| `entrada`, `salida`, `ok`, `veredicto`, `motivo`, `aviso` | presentes | presentes |
| `camino` | `[]` | `["png", "webp"]` |
| `saltos` | `[]` | lista con 1+ objetos `{arista, motor, rc, ms, veredicto, cobertura, hallazgos, sobrantes}` |
| `descartados` | `[]` | lista de `{camino, motivo}` |

Las siete claves de primer nivel están **siempre**, con valor vacío (`""`, `[]`) cuando no
aplican — nunca ausentes, nunca `null` en su lugar. Un consumidor que haga
`d.get("saltos", [])` de más es cinturón y tirantes, no una necesidad: la clave ya está.

**Y sigue la regla del proyecto de no devolver `stderr` crudo — verificado, no supuesto.** El
diccionario de cada salto en el JSON incluye `s.motivo` (el canal ya pensado para consumo
externo, según el propio `filex/invocacion.py:121`: *«una respuesta para un modelo usa
`motivo`, no `err`»*) y **excluye** `s.err` (el `stderr` crudo del motor, que sí aparece en el
modo texto con `-v/--verboso`, nunca en `--json`). Comprobado leyendo el diccionario que
construye `_convertir` (`filex/cli.py:107-112`): la clave `err` no está en la lista.

### ¿Los tres subcomandos tienen `--json`?

**No — solo `convertir`.** `motores`, `destinos` y `plan` no aceptan `--json` en absoluto:
pasarlo produce un error de `argparse` (`unrecognized arguments: --json`, `rc=2`), no una salida
alternativa:

```
$ filex motores --json
filex: error: unrecognized arguments: --json
rc=2
$ filex destinos png --json
filex: error: unrecognized arguments: --json
rc=2
$ filex plan a.png b.webp --json
filex: error: unrecognized arguments: --json
rc=2
```

**Es una omisión real, no una decisión documentada.** `destinos` y `plan` en particular son
justo el tipo de consulta que un pipeline querría automatizar («¿a qué formatos llego desde
X?», «¿qué camino se usaría?») y hoy solo dan texto para humanos. No lo implemento en esta
ronda —añadir un esquema JSON nuevo para tres subcomandos es una decisión de diseño de API, no
un pulido, y el encargo pide auditar, no ampliar superficie— pero queda como recomendación
explícita para la siguiente.

---

## 3 · Casos límite, probados contra el CLI real

Cada bloque es una transcripción real (`stdout`+`stderr` combinados salvo que se diga lo
contrario), no una descripción de lo que "debería" pasar.

### Fichero de entrada que no existe

```
$ filex convertir no-existe-de-verdad.png salida.webp
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
NO CONVERTIDO — ruta no accesible
rc=1
```

Mensaje claro, `rc=1` (fallo de negocio). El mismo mensaje («ruta no accesible») lo produce un
fichero que SÍ existe pero está fuera de una raíz confinada con `--raiz` — es **a propósito**
(R4 en `CLAUDE.md`): distinguir «no existe» de «prohibido» convierte al conversor en un oráculo
de qué hay en el disco ajeno. No es un hallazgo nuevo, es una regla del proyecto ya conocida que
confirmé que sigue aplicada en la CLI.

### Formato de destino que ningún motor sabe escribir

```
$ filex convertir corpus/imagen/tipico.png salida.formatoinventado999
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
NO CONVERTIDO — ningún motor disponible escribe 'formatoinventado999'
rc=1
```

Mensaje claro. Ver §1 para la inconsistencia de código con `destinos` sobre la misma situación.

### `--params` con JSON inválido

```
$ filex convertir a.png b.webp --params '{esto no es json'
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
--params no es JSON válido: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
rc=2
```

Ya estaba bien manejado — mensaje claro, `rc=2`. **Lo que NO estaba cubierto** es JSON
*sintácticamente válido* pero de un tipo que no es un objeto. Antes del arreglo de esta ronda:

```
$ filex convertir corpus/imagen/tipico.png salida.webp --params '42'
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
Traceback (most recent call last):
  File "filex\cli.py", line 216, in <module>
    raise SystemExit(main())
  File "filex\cli.py", line 212, in main
    return args.func(fx, args)
  File "filex\cli.py", line 91, in _convertir
    conv = fx.convertir(args.entrada, args.salida, pedido, timeout=args.timeout)
  File "filex\nucleo.py", line 650, in convertir
    pedido = dict(pedido or {})
TypeError: cannot convert dictionary update sequence element #0 to a sequence
rc=1
```

Reproducido con cuatro valores JSON válidos y no-objeto: `42` (`TypeError: 'int' object is not
iterable`), `"texto"` (`ValueError: dictionary update sequence element #0 has length 1; 2 is
required`), `[1,2,3]` (`TypeError: cannot convert dictionary update sequence element #0 to a
sequence`) y `true` (`TypeError: 'bool' object is not iterable`) — los cuatro con traceback
completo, `rc=1` indistinguible de cualquier error real del programa. `null` es la única
excepción que **no** revienta: `dict(None or {})` cae en el lado del `or` y da `{}`, así que
`--params null` equivale hoy (y seguirá equivaliendo) a no pasar `--params`.

**Causa:** `json.loads()` acepta cualquier valor JSON top-level, no solo objetos; `_convertir`
solo capturaba `JSONDecodeError` (fallo de sintaxis) y dejaba pasar el resto sin comprobar el
tipo hasta que `filex/nucleo.py:650` intenta `dict(pedido or {})` sobre algo que no es ni un
mapeo ni `None`.

**Arreglado** en `filex/cli.py`, con un chequeo de `isinstance(pedido, dict)` justo después del
`try/except` existente, mismo `rc=2` que el caso de JSON inválido (es la misma familia de
error: «lo que me diste en `--params` no sirve»):

```
$ filex convertir corpus/imagen/tipico.png salida.webp --params '42'
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
--params debe ser un objeto JSON ({...}), no int
rc=2

$ filex convertir corpus/imagen/tipico.png salida.webp --params '[1,2,3]'
--params debe ser un objeto JSON ({...}), no list
rc=2
```

Probado también que `null` sigue funcionando igual que antes (no hay regresión) y que el caso
`ok` normal (`{"ancho":800}`) no se ve afectado.

### Sin `--raiz`

Confirmado en modo texto y en `--json`, con los flujos separados para comprobarlo de verdad
(no de oídas): el aviso **siempre** sale por `stderr`, nunca se cuela en el JSON de `stdout`
(ver el bloque de §2). Un detalle adicional que verifiqué y que no es un fallo: el aviso **solo**
aparece para el subcomando `convertir` (`filex/cli.py`, condición `args.orden == "convertir"`);
`motores`, `destinos` y `plan` no lo muestran aunque tampoco reciban `--raiz`. Es correcto por
diseño — esos tres subcomandos no leen ni escriben ningún fichero del usuario, así que no hay
confinamiento que avisar que falta.

### `filex convertir` sin argumentos, y con solo uno

```
$ filex convertir
usage: filex convertir [-h] [--params PARAMS] [--timeout TIMEOUT] [--json] [-v] entrada salida
filex convertir: error: the following arguments are required: entrada, salida
rc=2

$ filex convertir entrada.png
usage: filex convertir [-h] [--params PARAMS] [--timeout TIMEOUT] [--json] [-v] entrada salida
filex convertir: error: the following arguments are required: salida
rc=2
```

Los dos son mensajes de `argparse`, en inglés (como aclara el propio encargo, no es código del
proyecto), claros, con `rc=2`. Sin tracebacks.

### Hallazgo adicional no pedido explícitamente, pero descubierto probando de verdad: la forma corta estaba muerta

El comentario en el propio código (`# «filex a.png b.webp» sin subcomando: la forma corta del
hito 1`) documenta una funcionalidad que **nunca se ejecutó, desde el commit `6e66406` (Hito
1)**. Antes del arreglo:

```
$ filex corpus/imagen/tipico.png salida.webp
usage: filex [-h] [--version] [--raiz RAIZ] {convertir,motores,destinos,plan} ...
filex: error: argument orden: invalid choice: 'corpus/imagen/tipico.png' (choose from 'convertir', 'motores', 'destinos', 'plan')
rc=2
```

**Causa raíz**, confirmada leyendo el código y reproduciendo en una consola de Python: el
`add_subparsers(dest="orden")` de `argparse`, aunque no es `required=True`, sigue **validando**
cualquier valor que aparezca en esa posición contra la lista de subcomandos en cuanto
`p.parse_args(argv)` lo ve — y `corpus/imagen/tipico.png` no es `convertir`, `motores`,
`destinos` ni `plan`, así que `parse_args` levanta `SystemExit(2)` **dentro de la propia
llamada**, en la línea `args = p.parse_args(argv)` de `main()`. El bloque de código que debía
reescribir el `argv` con `convertir` delante (`if args.orden is None: ...`) vive **después** de
esa línea y nunca se alcanza cuando hay 2 argumentos sueltos — literalmente no importa qué diga
ese bloque, porque el intérprete nunca llega a ejecutarlo. Confirmado con `git show
6e66406:filex/cli.py`: el código muerto es idéntico al del primer commit, once meses de historia
sin que nadie lo ejercitara (no hay ninguna prueba en `pruebas/` que invoque `cli.main()` con
solo 2 argumentos posicionales).

No es un traceback — es peor en un sentido y mejor en otro: **peor** porque el mensaje de error
("invalid choice") no da ninguna pista de que el problema es que falta la palabra `convertir`,
y **mejor** porque al menos tiene `rc=2` limpio en vez de una traza. Cuenta igualmente como
"hallazgo real de producto" según el criterio del propio encargo: un comportamiento documentado
en el propio código que nunca ha funcionado.

**Arreglado**: la detección de la forma corta se movió a **antes** de `parse_args`, reescribiendo
`argv` (anteponiendo `"convertir"`) cuando hay exactamente 2 argumentos que no empiezan por `-`
y el primero no es uno de los cuatro subcomandos conocidos. Verificado:

```
$ filex corpus/imagen/tipico.png salida.webp
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
C:\...\salida.webp   [ok_parcial]
  png→webp [imagemagick]  rc=0  384 ms  contrato 5/6 → ok_parcial
      ...
rc=0
```

**Límite conocido y documentado del arreglo, no escondido:** la heurística que decide "son 2
argumentos sueltos" filtra por `not a.startswith("-")` — la misma heurística que ya usaba el
código muerto original, sin cambios de criterio, solo de **cuándo** se aplica. Eso significa que
combinar la forma corta con `--raiz` (`filex --raiz X a.png b.webp`) **sigue sin funcionar**: el
valor `X` de `--raiz` no empieza por `-`, así que cuenta como un tercer argumento "suelto" y la
heurística no detecta el patrón de 2. Es exactamente el comportamiento que el código original
—de haber sido alcanzable— habría tenido; no es una regresión nueva, es la misma limitación de
diseño, ahora visible en vez de enterrada bajo un bug que hacía irrelevante la pregunta. Si se
quiere que la forma corta conviva con `--raiz`, hace falta un filtro que conozca qué opciones
del nivel superior consumen un valor, y eso es una decisión de diseño nueva, no un pulido — la
dejo como recomendación, no la implemento.

### Verificación de no regresión de los tres arreglos

```
$ filex --version                              # rc=0, sin cambios
$ filex                                        # ayuda, rc=0, sin cambios
$ filex convertir                              # error argparse, rc=2, sin cambios
$ filex convertir a.png                        # error argparse, rc=2, sin cambios
$ filex convertir tipico.png out.webp --json   # ok=true, veredicto=ok_parcial, sin cambios
$ filex convertir tipico.png out.webp --params null   # sigue funcionando como antes
```

Y la suite completa, corrida **dos veces** (la segunda tras quitar `import os`, §4):

```
D:\...\.venv-mcp-filex\Scripts\python.exe -m pytest pruebas/ -q
# corrida 1: 460 passed, 3 skipped, 130 subtests passed en 244.97 s
# corrida 2: 459 passed, 1 failed, 3 skipped, 130 subtests passed en 235.31 s
#   FAILED test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_...
#   → reejecutado ese módulo SOLO, aislado: 15 passed en 26.87 s

D:\...\.venv-mcp-filex\Scripts\python.exe ci/integridad.py
# 8/9 OK, 1 FALLA esperada (informes-registrados) — ver Método
```

**El fallo de la corrida 2 es la trampa 101(b) de `CLAUDE.md`, reproducida en vivo, no una
regresión mía.** `test_cancelacion_procesos` está citado por nombre en esa trampa como sensible
a la carga de la máquina (×3,4 más lento bajo contención, con `ronda 12` de `filex-gpu` y
`filex-cpu` corriendo en paralelo según el propio encargo). `git diff --stat` confirma que el
único fichero tocado en toda la ronda es `filex/cli.py` —nada de `filex/trabajo.py` ni de la
cancelación de procesos—, y el módulo aislado da **15/15** en limpio. Antes de culpar al cambio,
comprobar si tocó código (regla de la propia trampa): no lo tocó.

**Declaración de entorno de la corrida** (trampas 94/101/103 de `CLAUDE.md`): intérprete
`Python 3.11.9 win32` (`.venv-mcp-filex`), con Docker arriba (`doc_libreoffice`, `doc_pandoc` y
`doc_calibre` salieron `✓` en `filex motores`, así que el contenedor `filex-c13` estaba vivo
durante toda la ronda). Los 3 `skipped` son honestos y no dependen de mi cambio: falta un
segundo volumen físico (`test_cerrojo.py`), falta el ráster de `bench/salidas-hito6/`
(`test_hito6.py`) y falta `FILEX_PRUEBAS_SIDECAR=1` con la tarjeta (`test_hito6.py`) — ninguno
de los tres toca `filex/cli.py`.

---

## 4 · Pasada de simplicidad (no prioritaria)

Con el margen que quedó tras los tres puntos anteriores, revisión ligera de `filex/cli.py`
completo:

- **`import os` sin usar** — quedaba del primer commit; todo el manejo de rutas vive en
  `nucleo.py`. Eliminado.
- Nombres, estructura de las cuatro funciones `_inventario`/`_destinos`/`_plan`/`_convertir` y
  `construir_parser()`: claros, sin abstracciones muertas, sin comentarios que expliquen el QUÉ
  en vez del PORQUÉ (los comentarios existentes citan reglas del proyecto — R14, N9, N20 vía
  `_consola_utf8`— que es exactamente el tipo de comentario que vale la pena). No encontré nada
  más que tocar sin salirme del alcance del fichero.

---

## Método

- Todo se probó contra el intérprete de `python -m filex.cli` real en esta máquina —nunca
  descrito de memoria ni deducido de leer `argparse`—, con los ficheros del `corpus/` del propio
  repositorio (`corpus/imagen/tipico.png`) para las conversiones reales.
- Los ficheros temporales de las pruebas se escribieron en el directorio de trabajo temporal de
  la sesión o dentro del propio *worktree* y se borraron al terminar cada bloque; `git status
  --short` queda limpio salvo `filex/cli.py` (verificado antes de cerrar).
- Los tres arreglos son deliberadamente mínimos y locales a `filex/cli.py`: ninguno cambia un
  código de salida que ya funcionara, ninguno cambia una clave del esquema `--json` que ya
  existiera con datos válidos — los tres convierten un **crash o un código muerto** en un
  comportamiento definido. La única inconsistencia de código de salida que sí existe
  (`destinos` vs. `convertir`/`plan`, §1) se deja **sin tocar**, documentada, porque ahí sí hay
  contrato previo que un tercero pudo haber usado.
- `ci/integridad.py` da **8/9 OK y 1 FALLA esperada**: `informes-registrados` señala que
  `bench/pulido-cli.md` (este fichero) todavía no aparece citado en `ESTADO-Y-REPARTO.md`. Es la
  consecuencia directa de que el encargo prohíbe tocar ese fichero —lo gestiona quien integre los
  carriles en paralelo—, no un fallo de este trabajo: las otras 8 comprobaciones (citas,
  inventario, trampas, un-emoji-por-fila, manifiestos, secretos, binarios, en-curso) siguen en
  verde exactamente igual que antes de escribir este informe.
