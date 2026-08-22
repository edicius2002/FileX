# Hito 3 — la mudanza del verificador al núcleo

**Agente:** K2 · **Fecha:** 22/08/2026 · **Sin GPU y sin pedir su lock.**
**Entregables:** `filex/verificador.py`, `bench/scripts/verificador.py` (envoltorio),
`filex/contrato.py`, este informe y los datos crudos en `bench/salidas-hito3/`.

**Sin dependencias nuevas:** el verificador sigue siendo biblioteca estándar de Python 3.11
y nada más.

---

## 0. Resumen en diez líneas

| Qué | Antes | Después |
|---|---|---|
| Dónde vive el contrato | `bench/scripts/verificador.py`, 5 197 líneas | `filex/verificador.py`, **5 197 líneas** |
| `sha256` del código | `b531b4ad…8496c` | **`b531b4ad…8496c`** — el mismo |
| `bench/scripts/verificador.py` | 5 197 líneas de código | **66 líneas de envoltorio** |
| Cómo lo carga el núcleo | `importlib.util.spec_from_file_location` sobre otro árbol | `from . import verificador` |
| `filex/contrato.py` | **36 líneas** de carga por ruta (`importlib`, caché manual, `try/except Exception`) | **1 línea**: `from . import verificador` |
| Veredicto de las 53 del patrón oro | 49 `ok_parcial` · 3 `aviso` · 1 `fallo` | **idéntico, 1 844 hojas comparadas, 0 diferencias** |
| Fallos fabricados | 9/9 atrapados | **9/9** |
| Fidelidad sobre las 53 | 32 `ok` · 8 `aviso` · 13 `ok_parcial` | **idéntico** |
| `pruebas/test_hito1.py` | 32 pasan | **32 pasan** |

**Y el hallazgo principal no es la mudanza: es que la razón por la que no se había hecho
NO EXISTE.** Ver §2.

---

## 1. Hallazgo principal — **la premisa del encargo está REFUTADA, y por dos vías**

`PLAN-ORQUESTADOR.md:927` declara la deuda así:

> *(1) `bench/scripts/verificador.py` se **importa** desde `bench/` en vez de vivir en
> `filex/` — moverlo ahora **rompería las citas `fichero:línea` de doce informes y del
> patrón oro**, así que es trabajo del hito 3*

y `filex/contrato.py` repetía lo mismo en su propio docstring. **Las dos son falsas.**

### 1.1 No hay ni una sola cita `verificador.py:NNN` en el repositorio — MEDIDO

El propio encargo daba la orden de búsqueda. Ejecutada sobre todo el árbol versionado:

```
git grep -n -E "verificador[a-z_0-9]*\.py" -- '*.md' '*.py' '*.json' '*.sh' '*.ps1'
grep -rn "verificador\.py:[0-9]" --include=*.md .
```

**Resultado: 0 coincidencias con el patrón `fichero:línea`.** Ampliando el patrón a
`verificador.py` seguido de `línea`/`line`/`L` y un número, en **cualquier** fichero del
repositorio, sale **una sola**, y es §1.2.

Las 33 referencias reales al verificador que hay en los `.md` son de **cuatro** clases, y
**ninguna es una cita por número de línea**:

| Clase | Ejemplos | ¿La rompe la mudanza? |
|---|---|---|
| **CLI literal** (`python bench/scripts/verificador.py --salida …`) | `verificador-fidelidad.md:227, 232, 249, 258, 272, 294`; `firmas-contrato.md:315` | **No.** El envoltorio conserva la CLI palabra por palabra — verificado, §4.2 |
| **Referencia por nombre de fichero** (entregable, «no editar», «lo lleva P3») | `coste-verificacion.md:5, 23`; `ppp-y-normalizacion.md:964`; `consolidacion-21ago.md:138`; … | **No.** El fichero sigue existiendo en su ruta |
| **Recuento de líneas** (3 035 → 3 859 → 4 185 → 4 792 → 5 197) | `consolidacion-2-21ago.md:278, 326`; `consolidacion-3-21ago.md:285, 345`; `contrato-quinto-punto.md:70`; `firmas-contrato.md:650`; `HUECOS.md:286` | **Sí, y es la única que se rompe.** Ver §3.3 |
| **`sha256` de copias congeladas** | `salidas-aristas/MANIFIESTO.md:146` (`c753ca43…`), `salidas-invocacion/MANIFIESTO.md:147` (`cb3e479b…`) | **No.** Comprobado: los dos ficheros siguen intactos, §3.4 |

### 1.2 La única referencia con número de línea que existe **ya estaba caducada antes de mover nada** — MEDIDO

`bench/firmas-contrato.md:626` reproduce un *traceback*:

```
File "bench/scripts/verificador.py", line 1280, in _datos
    filas = list(csv.reader(io.StringIO(texto, newline="")))
```

Esa línea **hoy es la 1 330**, no la 1 280: el fichero creció 405 líneas *después* de que
F1 escribiera ese informe (4 792 → 5 197). Medido:

```
$ grep -n "csv.reader(io.StringIO" filex/verificador.py
1330:            filas = list(csv.reader(io.StringIO(texto, newline="")))
```

**Es decir: la trazabilidad por número de línea que la deuda decía proteger llevaba rota
desde antes de la mudanza, y la rompió el crecimiento normal del fichero, no el traslado.**
Un número de línea sobre un fichero vivo de 5 000 líneas y cuatro agentes no es una cita:
es una fecha de caducidad.

> **La lección, y es general del repositorio:** *no se cita por número de línea un fichero
> que sigue creciendo; se cita por nombre de función y por `sha256`.* Las dos copias
> congeladas (§3.4) están bien hechas justamente porque se citan por `sha256`.

### 1.3 Y aun así la mudanza **conserva** los números de línea — MEDIDO

`filex/verificador.py` es **byte a byte idéntico** al `bench/scripts/verificador.py` que
había antes:

```
# antes de escribir el envoltorio, con las dos copias del original en disco:
$ cp bench/scripts/verificador.py filex/verificador.py
$ cmp filex/verificador.py bench/scripts/verificador.py     -> sin diferencias
$ sha256sum filex/verificador.py bench/scripts/verificador.py
b531b4adac9b6b76b890758040eb56e8acae846bbf1a2a020caafc536a88496c *filex/verificador.py
b531b4adac9b6b76b890758040eb56e8acae846bbf1a2a020caafc536a88496c *bench/scripts/verificador.py
```

Luego **cualquier** número de línea que alguien tuviera anotado sigue apuntando a la misma
línea, sin más que cambiar el directorio: `bench/scripts/verificador.py:NNN` →
`filex/verificador.py:NNN`, para todo `NNN` de 1 a 5 197. La reconciliación de §3 es, por
construcción, la identidad.

---

## 2. Qué se hizo, y por qué así

### 2.1 `filex/verificador.py` — copia byte a byte, cero ediciones

**Decisión: no tocar una sola línea del fichero mudado.** El encargo pedía «ni una regla,
ni un umbral, ni una severidad distinta»; la forma de *demostrarlo* —y no de argumentarlo—
es que el `sha256` no cambie. Tentaciones descartadas a propósito:

- **Actualizar el docstring de cabecera** (dice «Implementa los CUATRO puntos» cuando son
  cinco, y «Uso: `python verificador.py …`»). Cambiarlo habría desplazado todas las líneas
  y habría convertido «idéntico» en «equivalente, créeme». **Queda PENDIENTE como corrección
  de documentación, separada de la mudanza.** Y la línea de uso sigue siendo cierta: la CLI
  funciona por las dos rutas (§4.2).
- **Renombrar a `contrato.py`** o partirlo en módulos. Sería una refactorización, no una
  mudanza, y no se puede probar con un `cmp`.

### 2.2 `bench/scripts/verificador.py` — envoltorio de 66 líneas que aliasea en `sys.modules`

**Justificación por escrito, que el encargo pedía explícitamente.**

Hay **19 arneses** de `bench/salidas-*/` que hacen exactamente esto:

```python
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
import verificador as V
```

(`_vocabulario.py`, `_valida_tabla.py`, `_remuestra.py`, `_regresion53.py`, `_g6.py`,
`_coste.py`, `_categorias.py`, `_categoria3.py`, `senal_alucinacion.py`,
`discrimina_v2_v5.py`, `prueba_alfa.py`, `txtvacio2.py`, `medir_fid.py`, `medir_gs.py`,
`medir_p5.py`, `ratio.py`, `puntos.py`, `medir.py`, `fallos.py`.)

Y del módulo usan **33 nombres**, de los cuales **doce son privados**: `_ffmpeg_framemd5`,
`_ffmpeg_md5_pcm`, `_ffmpeg_psnr`, `_ffprobe_etiquetas`, `_ffprobe_fotogramas`, `_gs_texto`,
`_magick_metrica`, `_paleta_es_rejilla`, `_paleta_gif`, `_pixel_magick`, `_png_bloques_idat`,
`_png_meta`. Censo completo:

```
$ grep -rhoE "\bV\.[A-Za-z_][A-Za-z0-9_]*" bench/salidas-*/*.py | sort -u   -> 33 nombres
```

**Tres opciones, y la tercera es la única correcta:**

| Opción | Por qué no / sí |
|---|---|
| Borrar el fichero y arreglar los 19 arneses | Los arneses son **evidencia congelada** de informes ya publicados. Editarlos es reescribir el registro |
| `from filex.verificador import *` | **`import *` no trae los nombres que empiezan por `_`**, y se usan doce. Habría que enumerarlos a mano, y esa lista envejece con el primer nombre nuevo |
| **`sys.modules[__name__] = _v`** ← **elegida** | Un solo objeto-módulo. Todo lo público y todo lo privado, sin lista que mantener |

**El motivo que decide es el tercero, y no es de comodidad: es de corrección.**
`verificador.v2(False)` existe para apagar la regla V2 desde fuera, y **escribe una bandera
a nivel de módulo**. Con dos objetos-módulo (uno importado como `verificador`, otro como
`filex.verificador`) habría **dos banderas**, y un arnés que apagase V2 por una vía la
dejaría encendida por la otra: un `ffprobe -count_frames` de 3,5 s por vídeo que alguien
creía haber apagado. Aliasando en `sys.modules` **eso es imposible por construcción**:

```
$ python -c "... import verificador as V; from filex import verificador as W; print(V is W)"
True
```

Es el patrón de `six.moves`, y CPython lo soporta a propósito: `importlib._bootstrap._load`
**relee `sys.modules[spec.name]` después de ejecutar el módulo**, así que la sustitución
desde dentro del propio módulo es la vía documentada.

**Coste medido: ninguno.** Las tres tandas de §4.1 dan hojas idénticas.

### 2.3 `filex/contrato.py` — deuda cerrada

Fuera `importlib.util.spec_from_file_location`, `sys.modules["filex_verificador"] = mod`, la
ruta calculada con dos `os.path.dirname` y el `try/except Exception` que se tragaba
cualquier fallo de carga. Dentro, un `from . import verificador as _verificador`.

**Lo que NO se cambió, y es deliberado:** la función `contrato.verificador()` sigue
existiendo y sigue pudiendo devolver `None`. **No es mía la razón: `filex/trabajo.py:42-44`
la llama así** para reutilizar `censar_dir` y no tener dos censos divergiendo, y
`trabajo.py` es de otro agente. Cambiar la firma habría sido tocar un fichero ajeno por la
puerta de atrás. La política del núcleo (devolver `no_verificado` en vez de reventar,
resumir en una línea para el humano y entregar el `dict` entero al modelo) se queda donde
estaba: **eso** es lo que `contrato.py` aporta sobre el verificador, y es lo que justifica
que siga siendo un módulo aparte en vez de un alias.

---

## 3. Tabla de reconciliación de citas

**Regla general, y hace la tabla casi trivial: la copia es byte a byte, luego para todo
`NNN`, `bench/scripts/verificador.py:NNN` → `filex/verificador.py:NNN`.**

### 3.1 CLI literal — **no hay que cambiar nada** (MEDIDO, §4.2)

| Cita | Dónde | Estado |
|---|---|---|
| `python bench/scripts/verificador.py --salida z.rgb --entrada … --destino rgb` | `firmas-contrato.md:315` | **Sigue valiendo** |
| `python bench/scripts/verificador.py \ …` (bloque del grupo A) | `verificador-fidelidad.md:232` | **Sigue valiendo** |
| `python bench/scripts/verificador.py --alfa-min corpus/imagen/alpha.png` | `verificador-fidelidad.md:249` | **Sigue valiendo** |
| `python bench/scripts/verificador.py --salida … --destino jpg --alfa` | `verificador-fidelidad.md:258` | **Sigue valiendo** |
| `python bench/scripts/verificador.py \ …` (fidelidad) | `verificador-fidelidad.md:272, 294` | **Sigue valiendo** |
| `python verificador.py --help` | `verificador-fidelidad.md:227` | **Sigue valiendo** |

**Y ahora hay dos vías más, las dos MEDIDAS con salida idéntica:**

```
$ python filex/verificador.py    --alfa-min corpus/imagen/alpha.png   -> rc=0
$ python -m filex.verificador    --alfa-min corpus/imagen/alpha.png   -> rc=0
```

La ruta canónica para un informe nuevo es `python -m filex.verificador …`; la de `bench/`
se conserva por compatibilidad con los informes ya publicados.

### 3.2 Referencia por nombre de fichero — **no hay que cambiar nada**

`coste-verificacion.md:5, 23` · `verificador-fidelidad.md:5, 449` ·
`verificador-ghostscript.md:11, 760, 873` · `firmas-contrato.md:10, 650` ·
`contrato-quinto-punto.md:10, 70` · `consolidacion-21ago.md:138` ·
`consolidacion-2-21ago.md:375` · `consolidacion-3-21ago.md:315, 317, 398` ·
`ppp-y-normalizacion.md:115, 964` · `aristas-nominales.md:12, 13` ·
`mcp-cabos-2.md:21` · `salidas-ppp-norm/MANIFIESTO.md:135` ·
`analysis/00-matriz-formatos.md:112` · `ESTADO-Y-REPARTO.md:36, 59, 244, 481, 716, 759, 918, 960`
· `HUECOS.md:286`.

El fichero sigue en esa ruta. Todas son ciertas. Las de `ESTADO-Y-REPARTO.md` y
`consolidacion-*.md` son además **actas históricas** («conviene esperar a que ese agente
cierre»): reescribirlas sería falsificar el registro.

### 3.3 Recuento de líneas — **la única cita que la mudanza sí altera**

| Cita | Valor publicado | Qué mide hoy |
|---|---|---|
| `consolidacion-2-21ago.md:278, 326` | 3 035 → 3 859 | Estado que dejó **V1**. Sigue siendo cierto *como acta* |
| `consolidacion-3-21ago.md:285, 345` | 3 859 → 4 185 (y «hoy 4 567 y creciendo») | Estado que dejó **P3**. Ídem |
| `contrato-quinto-punto.md:70` | 4 185 | Estado que dejó **P3** |
| `firmas-contrato.md:650` | 4 792 | Estado que dejó **F1** |
| `HUECOS.md:286` | discrepancia 3 859 / 4 185 / 4 567 | Nota de trazabilidad, ya declarada |
| `ESTADO-Y-REPARTO.md:960` | «`bench/scripts/verificador.py` (4 185 líneas) es ya un prototipo funcional del hito 3» | **Aquí es donde la ruta cambia de significado** |

**Reconciliación, en una frase que se puede copiar:** *desde el 22/08/2026 las 5 197 líneas
del contrato están en `filex/verificador.py`, con el `sha256`
`b531b4adac9b6b76b890758040eb56e8acae846bbf1a2a020caafc536a88496c`;
`bench/scripts/verificador.py` son 66 líneas de envoltorio que aliasean ese mismo módulo.*

**No se ha editado ninguno de esos `.md`.** Son actas de lo que midió cada agente sobre el
fichero que tenía delante, y siguen siendo ciertas como tales. La corrección es este
informe, y el cambio que **sí** hay que hacer es el de §7.

### 3.4 `sha256` de las copias congeladas — **intactas, verificado**

| Fichero | `sha256` publicado | Medido hoy |
|---|---|---|
| `bench/salidas-aristas/verificador_congelado.py` | `c753ca43…` (`salidas-aristas/MANIFIESTO.md:146`) | `c753ca43aa3e5e24eeac5f9c10228c58cde4bdd61fc0acd6d7d4749ef1799447` ✅ |
| `bench/salidas-invocacion/verificador_p2.py` | `cb3e479b6a75dddf…` (`salidas-invocacion/MANIFIESTO.md:147`) | `cb3e479b6a75dddf3fe337b2efa92f0e97213aaeaf029993957b007e91587268` ✅ |

Y **siguen conviviendo** con el mudado, que era el riesgo real del alias en `sys.modules`
(un arnés que importa los dos). MEDIDO:

```
V  = filex.verificador              -> len(FIRMAS) = 116
VC = verificador_congelado          -> len(FIRMAS) =  14
V is not VC -> True
```

Es decir, `bench/salidas-firmas/_coste.py` —que compara el vocabulario ampliado contra el
que usó E1— **sigue midiendo lo que medía**, y el alias no contamina la copia congelada.

### 3.5 El *traceback* de `firmas-contrato.md:626` — **se deja como está, a propósito**

Es la reproducción literal de una salida de error de agosto, no una cita. Corregir el número
que imprimió el intérprete sería inventar una salida que nunca ocurrió. Lo que hace falta es
el dato de §1.2: **esa línea es hoy la 1 330 de `filex/verificador.py`, y la función sigue
llamándose `_datos`.**

---

## 4. La prueba: las 53 salidas del patrón oro, antes y después

### 4.1 Método y resultado — **MEDIDO, 0 diferencias en 1 844 hojas**

Arnés: `bench/salidas-hito3/_reg53_hito3.py`, derivado de
`bench/salidas-firmas/_regresion53.py` y **copiado a mi directorio de salidas** (no se ha
tocado el de F1). Vuelca un JSON deliberadamente **determinista** —sin un solo milisegundo
dentro; los testigos van a un fichero aparte— para poder compararlo con `diff`.

Lo que se ejerce en cada tanda:

1. **Las 53 salidas del patrón oro**, con `TABLA` de `bench/salidas-verificacion/trabajos.py`,
   **con los DOS motores de sondeo** (`proceso` y `subproceso`) y `alfa=True`.
   Se registra veredicto, `punto1`, `firma_real`, **cobertura completa** y **todos** los
   hallazgos con punto, regla, severidad, mensaje, esperado y obtenido — no solo los de
   severidad `fallo`/`aviso`: si la mudanza hubiera movido un `informativo`, se vería.
2. **Los 9 fallos fabricados**, incluido el emblemático (PNG entregado con extensión `.avif`).
3. **El punto 5 con censo real** — que las 53 *no* ejercen, porque no lo tienen: dos casos,
   un motor limpio y uno que deja un sobrante en el `cwd`.
4. **El grupo C de fidelidad** sobre las 53, con `--sin-v2`.

Tres tandas:

| Tanda | Cómo se carga el módulo | Fichero |
|---|---|---|
| **ANTES** | `sys.path.insert(bench/scripts)` + `import verificador` **con el fichero original de 5 197 líneas** | `reg53_antes.json` |
| **DESPUÉS** | `from filex import verificador` | `reg53_despues.json` |
| **ENVOLTORIO** | `sys.path.insert(bench/scripts)` + `import verificador`, **ya con el envoltorio** | `reg53_envoltorio.json` |

**Resultado — `bench/salidas-hito3/_compara.py`:**

```
=== reg53_antes.json  vs  reg53_despues.json ===
  hojas comparadas: 1844 / 1844
  IDENTICOS: 0 diferencias
=== reg53_antes.json  vs  reg53_envoltorio.json ===
  hojas comparadas: 1844 / 1844
  IDENTICOS: 0 diferencias
TOTAL DIFERENCIAS: 0
```

Y el `diff` crudo, sin ignorar nada, sobre los ficheros enteros:

```
$ diff reg53_antes.json reg53_despues.json
133c133
<  "fichero": ".../bench/scripts/verificador.py"
---
>  "fichero": ".../filex/verificador.py"
955,956c955,956
<  "fuente": "bench",  "modulo": "verificador",
---
>  "fuente": "filex",  "modulo": "filex.verificador",
```

**Dos bloques, cuatro líneas, y las cuatro dicen de dónde se cargó el módulo — que es
exactamente lo que la mudanza cambia.** Nada más difiere en 61 574 bytes de veredictos.

Veredictos, para el registro:

| | proceso | subproceso |
|---|---|---|
| **53 del patrón oro** | 49 `ok_parcial` · 3 `aviso` · 1 `fallo` · **FP=0 FN=0** | 48 `ok_parcial` · 4 `aviso` · 1 `fallo` · **FP=0 FN=0** |
| **9 fallos fabricados** | 9/9 correctos | — |
| **punto 5 con censo** | limpio `ok_parcial`, sucio `aviso` | — |
| **fidelidad (grupo C, sin V2)** | 32 `ok` · 8 `aviso` · 13 `ok_parcial` | — |

Los 49 `ok_parcial` de 53 son la cifra conocida de CLAUDE.md: **sin censo, el punto 5 no se
da por bueno.** Confirmada aquí como control de que el arnés mide lo que cree medir.

**Ninguna de las 53 cambió de veredicto.** El encargo decía que si una cambiaba era un
hallazgo mayor que la mudanza limpia; no cambió ninguna, y §5 explica por qué era esperable.

### 4.2 La CLI del envoltorio — MEDIDO

```
$ python bench/scripts/verificador.py --salida bench/salidas-referencia/imagen/tipico_png-to.webp \
                                      --entrada corpus/imagen/tipico.png --destino webp
CONTRATO (grupo A)     OK_PARCIAL bench/salidas-referencia/imagen/tipico_png-to.webp
  [p4 I5 informativo] reduccion de profundidad inevitable en webp (techo 8 bits)  esperado=16 obtenido=8
  [p4 I2 informativo] se descarta el canal alfa y min(alfa) de la entrada no esta calculado …
  punto 1: evaluado
  cobertura: PARCIAL (sin cubrir: 4_alfa, 5_escritura)
  ms: {'sonda_salida': 0.372, …, 'total': 0.87, 'logica': 0.126}
rc=0
```

Salida y código de retorno idénticos a los del fichero original.

### 4.3 `pruebas/test_hito1.py` — MEDIDO

```
32 passed in 34.90s
```

(Ejecutado, no editado: `pruebas/` no es mío.)

### 4.4 Coste de las tandas, con la salvedad de CLAUDE.md

| Tanda | ms totales | testigos |
|---|---|---|
| ANTES | 49 684 | deriva ×1,21 · nivel ×3,63 → **SUCIA** |
| DESPUÉS | 78 246 | deriva ×1,47 · nivel ×2,27 → **SUCIA** |
| ENVOLTORIO | 45 286 y 49 906 (dos ejecuciones) | deriva ×1,08 / ×0,89 · nivel ×1,38 / ×2,10 → **SUCIA** |

**Estas tres cifras NO son comparables entre sí y no se usan para nada.** Hay tres agentes
más trabajando (K1, K3, M1) y la sesión remota está activa, así que `SUCIA` es estructural.
Se publican solo porque el encargo pedía timeouts explícitos y coste declarado: la suite
entera cabe holgadamente en el timeout de 900 s con el que se lanzó. **La afirmación «el
envoltorio no cuesta nada» NO se apoya en estos milisegundos** —el rango 45–78 s los
invalida como medida— **sino en que las 1 844 hojas coinciden y en que el objeto-módulo es
el mismo (`V is W → True`): no hay indirección que cronometrar.**

---

## 5. Por qué NO hubo dependencia del entorno de `bench/` — y qué habría pasado si la hubiera

El encargo apostaba a que la mudanza descubriera una fragilidad: una ruta relativa, un
`cwd`, un fichero de al lado. **No la hay, y el motivo está MEDIDO, no supuesto:**

```
$ grep -n "__file__\|os.getcwd\|sys.path\|^RAIZ\|^ROOT" filex/verificador.py
(sin coincidencias)
```

**Cero.** En 5 197 líneas el verificador no sabe dónde está, no lee ningún fichero de
configuración, no tiene datos junto al código y no depende del directorio de trabajo. Lo
único externo que toca son **binarios resueltos por `PATH`** (`ffprobe`, `magick`,
`gswin64c`) a través de `_correr`, y eso es indiferente a dónde viva el `.py`.

**Eso convierte un resultado negativo en un dato de diseño:** el verificador se podía mudar
porque se escribió **como una función pura del fichero que se le pasa**. La regla que se
lleva el proyecto:

> **Un módulo que no sabe dónde está se puede mover; uno que sí, no.** Los 5 197 líneas del
> contrato no tienen un solo `__file__`, y por eso la mudanza es un `cmp` en vez de una
> negociación. **El contraejemplo está en el mismo repositorio:** los 19 arneses de
> `bench/salidas-*/` empiezan todos con `RAIZ = r"D:\Work\research\FileX"` **cableado**, y
> por eso no se pueden mover a ningún sitio. La diferencia entre el producto y el arnés no
> es la calidad del código: es si conoce su propia ruta.

**Y la contrapartida honesta:** que el verificador sea puro no significa que el *contrato*
lo sea. El punto 5 **exige** contexto externo (el censo del directorio de trabajo) y por eso
`filex/nucleo.py` lo toma dentro del mismo `with` que lanza el motor. Mudar el verificador
no ha tocado eso, y sigue siendo el punto frágil.

---

## 6. Los dos fallos conocidos: **medidos los tres, arreglado ninguno** — y uno REFUTA lo publicado

El encargo los daba como opcionales y avisaba de que «cada arreglo necesita su prueba y su
verificación contra el patrón oro». **Se han medido los tres. No se ha aplicado ninguno,
para que la mudanza siga siendo demostrable con un `cmp`.** Los datos crudos van en
`bench/salidas-hito3/datos_ram.json` y `colisiones.json`.

### 6.1 `_datos` no cuesta ×1 la RAM del fichero: cuesta **×21,3** — MEDIDO, y corrige `firmas-contrato.md` §10

`firmas-contrato.md` §10 lo declara como «`_datos` lee el fichero entero en memoria — 156 MB
de RAM para contar comas en el TXT de ImageMagick». **La primera mitad es cierta; la cifra
se queda muy corta.** Medido con `tracemalloc` (`_datos_ram.py`), CSV sintéticos
deterministas, dos regímenes:

| Fichero | Rama | Pico de RAM | Ratio sobre el fichero | ms |
|---|---|---|---|---|
| 1 MB | CSV normal | 22 402 562 B | **×21,36** | 1 952 |
| 8 MB | CSV normal | 178 961 119 B | **×21,33** | 22 177 |
| 32 MB | CSV normal | 715 959 591 B | **×21,34** | 65 004 |
| 1 MB | campo largo (degradada) | 7 865 707 B | **×7,50** | 125 |
| 8 MB | campo largo (degradada) | 59 246 179 B | **×7,06** | 867 |
| 32 MB | campo largo (degradada) | 235 406 947 B | **×7,02** | 3 707 |

**Dos correcciones al informe original:**

1. **El culpable no es el `fh.read()`.** Es `d["csv_filas"] = filas`: la lista de listas de
   `str` con el CSV **entero materializado**, que se queda dentro de la sonda. El `read()`
   es ×1; el ratio ×21,3 es el coste por objeto de Python de cada campo.
2. **El caso concreto del informe —el TXT de ImageMagick— va por la rama degradada**, la que
   `csv.Error` corta antes de construir `filas`. Ahí el ratio es **×7,0**, no ×1: sobre los
   **156 520 548 bytes** que midió E1 son **≈1,1 GB de pico**, no 156 MB. Y la rama que *no*
   se corta costaría **≈3,3 GB**.

**Y una escala que importa más que la RAM:** ×21,3 es lineal, pero **el tiempo no**:
65 s para 32 MB en la rama normal. Un CSV de 100 MB en el camino caliente del contrato es
minutos, no segundos.

**PENDIENTE, con el arreglo ya localizado:** el arreglo no es hacer el `read()` perezoso, es
**dejar de guardar `csv_filas`** y publicar solo los agregados que las reglas consumen
(`csv_n_filas`, `csv_cabecera`, `csv_n_campos_por_fila`, `filas_datos`), calculados en un
solo recorrido de `csv.reader` sobre un fichero abierto en modo texto. **No se aplica aquí
porque cambia lo que la sonda devuelve** —y hay reglas de los puntos 3 y 4 y de fidelidad
que leen la sonda—, así que es un cambio semántico con su propia regresión, no una
refactorización.

### 6.2 `.pcd` → `mpegaudio`: **NO es «una colisión sin falso positivo». Es un falso positivo vivo** — MEDIDO

`firmas-contrato.md` §10 las declara como «dos colisiones declaradas **sin falso positivo
hoy**». **Refutado para `.pcd`, y con un fichero real, no sintético: este ImageMagick 7.1.2
ESCRIBE PhotoCD.**

```
$ magick corpus/imagen/tipico.png real.pcd     ->  rc=0, 788 480 bytes
$ head -c 8 real.pcd | xxd                     ->  ff ff ff ff ff ff ff ff
```

Una conversión **PNG → PCD legítima, hecha por un motor de primera, con `rc=0`**, pasada por
el contrato:

```
firma_real : mpegaudio        categoria: av        n_pistas: 1
punto 1    : sin_vocabulario
veredicto  : FALLO
  [p1 G3 informativo] extension sin firma conocida: .pcd
  [p2 V3 informativo] sin referencia de entrada: no se puede comparar el numero de pistas
  [p3 G4 FALLO]       duracion nula o ilegible
  [p3 G4 aviso]       bitrate no positivo
```

**Y lo importante es POR DÓNDE se escapa, porque no es por donde se creía.** La cadena
medida es:

1. La cabecera de PhotoCD es el sector 0 relleno de `0xFF`. La heurística de
   `firma_real` («`0xFF` + `0xEx` = MPEG audio», `verificador.py:376`) la captura → `mpegaudio`.
2. `CAT_POR_FIRMA["mpegaudio"] = "av"` → **la sonda parsea el PCD como MP3** e inventa una
   pista de audio mono a 44 100 Hz y 0 bps.
3. El **punto 3** encuentra `duracion = None` y dispara `G4` con severidad **`fallo`**.

> **El punto 1 acierta.** Dice `sin_vocabulario`, que es exactamente la respuesta honesta.
> **El falso positivo lo produce el punto 3**, porque la firma equivocada no se queda en el
> punto 1: **contamina la CATEGORÍA, y la categoría decide qué sonda se ejecuta.** Un
> vocabulario que «no conoce» una extensión no protege de nada si la firma ya mandó el
> fichero a la sonda equivocada.

Ese es el hallazgo transferible, y vale más que el arreglo: **una colisión de firma no está
contenida por el estado de cobertura del punto 1.** La cobertura en cuatro estados protege
al punto 1 de sí mismo; no protege a los puntos 2 y 3 de él.

**PENDIENTE, y con la tensión de diseño explícita — por eso no lo arreglo de tapadillo:**

- **Opción A (correcta, cara):** la firma de PhotoCD real es `PCD_IPI` **en el desplazamiento
  2048**. Pero `_NCAB = 512` y el comentario del código dice literalmente *«Un solo read, una
  sola página»*. Leer hasta 2 055 bytes **cambia el modelo de coste del punto 1**, que está
  medido en otro informe (0,094 ms). Es una decisión de arquitectura, no un parche.
- **Opción B (barata, con efecto colateral):** añadir `(0, b"\xff"*32, "pcd")` a `FIRMAS`,
  que se consulta **antes** de la heurística. Arregla el PCD **y rompe otra cosa**: un
  volcado **RGB crudo de una imagen blanca** también empieza por 32 bytes `0xFF` y pasaría de
  `mpegaudio` a `pcd`. Hoy `.rgb` está en `EXT_SIN_FIRMA` y sale `no_aplica`, así que
  probablemente no haría daño — **«probablemente» no es una medida**, y esa medida necesita
  corpus propio.
- **Opción C (mínima y honesta):** dejar la firma como está y **no dejar que la categoría se
  derive de una firma que el punto 1 ya ha marcado `sin_vocabulario` o dudosa**. Ataca la
  causa (§paso 2) en vez del síntoma. Es la que recomiendo, y es la que más regresión exige.

### 6.3 TGA/CUR comparten `00 00 02 00`: la declaración es correcta, y el agujero también — MEDIDO

| Caso | firma_real | punto 1 | veredicto |
|---|---|---|---|
| TGA real de `magick`, extensión `.tga` | `cur` | `no_aplica` (G4: TGA no tiene marcador) | `ok_parcial` |
| **TGA real entregado como `.cur`** | `cur` | **`evaluado`** | **`ok_parcial`, 0 hallazgos** |
| CUR sintético, extensión `.cur` | `cur` | `evaluado` | `ok_parcial` |

**Confirmado en ejecución lo que el comentario del código ya anticipaba** (`verificador.py:111-113`):
*«No produce falso positivo porque `.tga` está en `EXT_SIN_FIRMA`, pero un TGA con extensión
`.cur` pasaría»*. Pasa: **cero hallazgos**, indistinguible de un cursor auténtico.

Es un **falso negativo**, no un falso positivo, y por tanto **no viola el listón de las 53**
(0 FP). Pero conviene medirlo y anotarlo: el discriminante existe y es barato —el byte 2 de
un TGA es el tipo de imagen (`0x02` = RGB sin comprimir) y el 3 es la longitud del mapa de
color, mientras que en un `.cur` los bytes 4-5 son el **número de imágenes** y **no puede ser
0**. `00 00 02 00 00 00 …` (cuenta = 0) **es imposible en un CUR válido** y es justo lo que
escribe `magick` para un TGA. **Es exactamente la misma forma que ya usa el código para
separar JBIG de ICO** (`verificador.py:106-109`: *«Un ICO válido no puede llevar 0 imágenes»*).
**PENDIENTE**: aplicar el mismo predicado a CUR. Coste estimado: dos líneas. Regresión
necesaria: las 53 más un corpus de CUR reales, que este proyecto no tiene.

---

## 7. Cambios que pido en ficheros que no son míos

Uno solo, y es el que cierra la contradicción de §1.

**Fichero:** `PLAN-ORQUESTADOR.md`, línea 927. **Diff exacto:**

```diff
-> **Deuda declarada:** (1) `bench/scripts/verificador.py` se **importa** desde `bench/` en vez de vivir en `filex/` — moverlo ahora rompería las citas `fichero:línea` de doce informes y del patrón oro, así que es trabajo del hito 3; (2) las aristas `sin_sondear` son 132 de 156: el sondeo real de capacidades por arista está **pendiente**, y hasta entonces cuestan +2,0 para no adelantar nunca a una medida; (3) `Ghostscript.orden` escribe **un solo fichero** y un PDF de varias páginas necesita `%d`, que es una salida multifichero y **el patrón oro no tiene ni una** (C22).
+> **Deuda declarada:** ~~(1) `bench/scripts/verificador.py` se **importa** desde `bench/` en vez de vivir en `filex/` — moverlo ahora rompería las citas `fichero:línea` de doce informes y del patrón oro~~ — **CERRADA en el hito 3, y el motivo que la sostenía era falso: en todo el repositorio no hay ni una sola cita `verificador.py:NNN`, y la única referencia con número de línea que existe (`bench/firmas-contrato.md:626`) ya estaba caducada por el crecimiento del propio fichero. El verificador vive en `filex/verificador.py`, byte a byte idéntico (`sha256 b531b4ad…8496c`), y `bench/scripts/verificador.py` son 66 líneas de envoltorio que aliasean el mismo objeto-módulo. 53/53 veredictos idénticos, 1 844 hojas comparadas, 0 diferencias (`bench/hito3-mudanza.md`)**; (2) las aristas `sin_sondear` son 132 de 156: el sondeo real de capacidades por arista está **pendiente**, y hasta entonces cuestan +2,0 para no adelantar nunca a una medida; (3) `Ghostscript.orden` escribe **un solo fichero** y un PDF de varias páginas necesita `%d`, que es una salida multifichero y **el patrón oro no tiene ni una** (C22).
```

**Y una corrección que pido a `bench/firmas-contrato.md` §10**, que no es mío y cuyo autor
(F1) debería revisar: las dos afirmaciones de §6.1 y §6.2 de este informe lo contradicen con
medida —el ratio de RAM es ×21,3 / ×7,0, no ×1, y `.pcd` **sí** produce un falso positivo—.
No lo he editado.

---

## 8. Ficheros

### Tocados

| Fichero | Antes | Después |
|---|---|---|
| `filex/verificador.py` | *(no existía)* | **5 197 líneas**, `sha256 b531b4ad…8496c` |
| `bench/scripts/verificador.py` | 5 197 líneas, `sha256 b531b4ad…8496c` | **66 líneas** de envoltorio |
| `filex/contrato.py` | 79 líneas, 36 de carga por ruta | 79 líneas, **0** de carga por ruta: `from . import verificador` |
| `bench/hito3-mudanza.md` | *(no existía)* | este informe |
| `bench/salidas-hito3/` | *(no existía)* | 4 scripts + 8 JSON, 235 KB, todo texto |

### NO tocados (y comprobados intactos)

`bench/salidas-referencia/referencia.json` (el patrón oro: **leído, nunca escrito**) ·
`bench/salidas-aristas/verificador_congelado.py` (`c753ca43…`) ·
`bench/salidas-invocacion/verificador_p2.py` (`cb3e479b…`) ·
`bench/salidas-verificacion/trabajos.py` (importado, no editado) ·
`bench/salidas-firmas/_regresion53.py` (**derivado a mi directorio, no editado**) ·
`filex/motores.py`, `filex/nucleo.py`, `filex/grafo.py`, `pruebas/test_hito1.py` (de K1/K3) ·
los `.md` de `bench/` (ninguno editado) · `PLAN-ORQUESTADOR.md` (ver §7).

**Sin `git add` ni `git commit`.**

### Manifiesto de `bench/salidas-hito3/`

Todo es texto y se versiona (CLAUDE.md §6). Órdenes exactas que lo reproducen:

| Fichero | Orden |
|---|---|
| `reg53_antes.json` | `python bench/salidas-hito3/_reg53_hito3.py --fuente bench --con-fidelidad` *(con el verificador aún en `bench/scripts/`)* |
| `reg53_despues.json` | `python bench/salidas-hito3/_reg53_hito3.py --fuente filex --con-fidelidad` |
| `reg53_envoltorio.json` | `python bench/salidas-hito3/_reg53_hito3.py --fuente bench --con-fidelidad --salida-json reg53_envoltorio.json` |
| `*_testigos.json` | *(los escribe el mismo arnés, aparte, para no contaminar el diff)* |
| `datos_ram.json` | `python bench/salidas-hito3/_datos_ram.py --mb 1 8 32` |
| `colisiones.json` | `python bench/salidas-hito3/_colisiones.py` |
| *(la comparación)* | `python bench/salidas-hito3/_compara.py reg53_antes.json reg53_despues.json reg53_envoltorio.json` |

---

## 9. Lo que se lleva el proyecto

1. **Una deuda declarada no es una deuda medida.** La razón por la que el verificador no se
   había mudado —«rompe las citas `fichero:línea` de doce informes»— **no resistió el primer
   `grep`**: esas citas no existen. Costó una orden comprobarlo y llevaba escrita desde el
   hito 1 en dos sitios distintos. **Antes de pagar una deuda, mide que sea deuda.**
2. **No se cita por número de línea un fichero vivo.** La única que había caducó sola, por
   crecimiento del fichero, sin que nadie moviera nada. Se cita por **nombre de función y
   `sha256`** — que es justo lo que hacen bien las dos copias congeladas.
3. **Un módulo que no sabe dónde está se puede mover; uno que sí, no.** Cero `__file__` en
   5 197 líneas es lo que convierte esta mudanza en un `cmp`. Los 16 arneses de `bench/`, con
   su `RAIZ` cableada, son el contraejemplo en el mismo repositorio.
4. **Cuando el mismo módulo se importa por dos nombres, aliasea en `sys.modules`.** No es
   estilo: `v2()` escribe una bandera global, y dos objetos-módulo son dos banderas y una
   mentira.
5. **La cobertura en cuatro estados protege al punto 1 de sí mismo, no a los puntos 2 y 3.**
   Una firma equivocada decide la **categoría**, la categoría decide **qué sonda corre**, y
   la sonda equivocada inventa datos que el punto 3 juzga. El PCD sale `fallo` con el punto 1
   diciendo, correctamente, «no sé».
6. **Y la prueba de que no cambió nada tiene que poder fallar.** Un arnés que solo mira
   `veredicto` habría dicho «idéntico» igual. Este compara 1 844 hojas incluyendo los
   hallazgos `informativo`, con los dos motores de sondeo, y **habría visto** una severidad
   movida.
