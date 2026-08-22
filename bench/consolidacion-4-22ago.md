# Consolidación 4 — los dos informes que D3 no pudo integrar

**Fecha:** 22 de agosto de 2026
**Entrada:** `bench/mcp-cabos-2.md` (M1) y `bench/firmas-contrato.md` (F1)
**Alcance:** solo consolidación documental. **No se ha medido nada nuevo.**

---

## 0. Por qué existe este documento

D3 consolidó **diez** informes del 21 de agosto. Mientras lo hacía, **M1 y F1 seguían midiendo** —lo
detectó en el árbol y los excluyó de su commit, correctamente: no tenían informe que los explicara—.
Cerraron después. **Sus dos informes entraron en el commit `1fb5024` con su evidencia, pero sin
consolidar.** Esto lo cierra.

**Y hay una razón para no dejarlo pendiente: uno de los dos rompe la premisa de coste del hito 4.**

---

## 1. Lo que cambia en el DISEÑO

### 1.1 El coste del catálogo MCP: el ×2,0–2,6 por turno **no es el del despliegue real**

`saturacion-herramientas.md` §3.6 midió, con 540 ejecuciones, que un catálogo se paga **×2,0–2,6 en
cada turno**, y sobre eso descansaba el presupuesto de **≤1.200 tokens** de `RESULTADOS-MCP.md` §4.

**Se midió con `--tools ""`. Ese es el régimen ansioso, y FileX no va a vivir en él.**

| Condición | Herramientas internas | Catálogo | **Total de entrada (tok)** |
|---|---|---|---:|
| `pmin_pesado_deftools` | **sí** (sesión real) | pesado | **26.941** |
| `pmin_ligero_deftools` | **sí** (sesión real) | ligero | **26.941** |
| `pmin_pesado_notools` | no (`--tools ""`) | pesado | 11.188 |
| `pmin_ligero_notools` | no (`--tools ""`) | ligero | 7.890 |

Mismos 6 nombres, mismos esquemas, ~3.300 tokens de diferencia en descripciones. **26.941 = 26.941.**
El cuerpo del catálogo no llega al contexto, y el modelo lo dice literalmente: *«solo veo los nombres
de las herramientas deferred, no sus descripciones»*.

> **Lo que NO hay que concluir**, y por eso va escrito junto: **(1)** los **nombres** sí se inyectan en
> cada turno — el ≤1.200 tokens sobrevive **como higiene de nombres**, no como multiplicador;
> **(2)** es comportamiento de **una versión** (2.1.238) y del **total** de herramientas de la sesión:
> con `--tools ""` y pocas vuelve el régimen ansioso, con 40 el catálogo sale **truncado**;
> **(3)** un catálogo demasiado escueto sigue produciendo **15–17 % de fallos silenciosos**. La
> diferición abarata el catálogo grande; **no** rehabilita recortar la cobertura de `convert`.

**Llevado a:** `RESULTADOS-MCP.md` §4 (recuadro de re-acotación), `PLAN-ORQUESTADOR.md` §4.4 (la
viñeta del ×2,0–2,6 tachada y sustituida), `CLAUDE.md` §5, `bench/saturacion-herramientas.md` §3.6
(aviso al principio de la sección, para que nadie la cite fuera de su condición).

### 1.2 El punto 1 del contrato no aplica al 23,6 % de los formatos — **y ahí tampoco aplican el 2 ni el 3**

El vocabulario de firmas pasa de **24 nombres y 26 extensiones a 147 y 338**, más una tercera tabla de
**112 extensiones declaradas sin marcador**. El punto 1 sube del **12,4 % al 54,2 %** de los destinos,
con **0 falsos positivos** sobre las 53 del patrón oro.

> **Pero la conclusión es la contraria a la que se buscaba: no se pueden verificar 500 firmas porque
> NO EXISTEN 500 FIRMAS.** De 381 formatos con veredicto, **90 (23,6 %) no tienen marcador**. Y donde
> no hay cabecera tampoco hay puntos 2 y 3, **porque los tres se alimentan de lo mismo**. Para esa
> tercera categoría quedan **el punto 4, el punto 5 y G6**.

De ahí que la cobertura pase de booleano a **cuatro estados**: `evaluado` / `familia` / `no_aplica` /
`sin_vocabulario`. **Antes `1_firma` valía `True` en el 100 % de los ficheros mientras evaluaba el
12,4 %** — un contrato que aprueba lo que no ha mirado es peor que uno que no mira.

**Llevado a:** `PLAN-ORQUESTADOR.md` §4.2 (subsección nueva) y §5 (dos reglas), `CLAUDE.md` §5,
`bench/aristas-nominales.md` §11.3 (la frase de las «500 firmas», matizada en su sitio).

### 1.3 G6: el fallo emblemático del proyecto lo atrapa una regla que no sabe nada del destino

`magick corpus/imagen/tipico.png -auto-orient salida.group4` → **rc=0 y un PNG de 313 bytes**. Es el
fallo nº 1 de `HUECOS.md` —un PNG entregado con otra extensión y estado «Done»— producido por un motor
de primera línea, **22 veces en la misma sesión**.

| | Vocabulario **viejo** | Vocabulario **nuevo, por firma** | Con **G6** |
|---|---:|---:|---:|
| Detectados de 22 | **0** | **0** | **22** |

**La columna del medio es la que enseña algo: ampliar el vocabulario NO atrapa este caso.** Para
atrapar `.group4` por firma habría que saber qué firma esperar, y `.group4` son datos CCITT crudos:
**no tiene ninguna**. Los otros 21 ni siquiera son formatos de fichero.

> **G6 — la salida tiene la MISMA firma que la entrada y no era eso lo que se pedía.** Cuesta **0**
> (las dos firmas ya están calculadas). Severidad **`aviso`**: está calibrada sobre **un solo motor**.

**Y la consecuencia de catálogo, que es donde de verdad se arregla: esas 22 aristas son nominales y
hay que borrarlas de la cobertura declarada, no verificarlas mejor.**

**Llevado a:** `HUECOS.md` §1 (recuadro tras la tabla de fallos), `PLAN-ORQUESTADOR.md` §4.2 y §5,
`CLAUDE.md` §5, `ESTADO-Y-REPARTO.md` (C14 cerrado, **C27** abierto para subirla a `fallo`).

### 1.4 `inspect` queda exento de R8 **y** de R18, con número

- **R8** protege a un motor externo que va a **leer** el contenido. `inspect` lee cabeceras **en
  proceso**: no entrega la ruta a nadie.
- **R18** abarata el quinto punto para operaciones que **escriben**. `inspect` **no escribe**: no hay
  censo que hacer.

| | Coste |
|---|---:|
| `inspect` en proceso | ~~0,04–0,06 ms~~ → **0,21–0,59 ms** (corregido, ver abajo) |
| Staging que R8 le impondría | **1,7 ms (1 MB) — 166 ms (256 MB)** |

~~De 30× a más de 3.000× la operación~~ → **de 2,0× a 284×, a cambio de cero seguridad.**

> **Corrección del mismo día (`bench/hito4-mcp.md` §6.4).** Los «0,04–0,06 ms» que consolidé aquí medían **abrir + leer 64 KiB de cabecera**, no un `inspect` — que además clasifica el formato y recorre las cajas de un ISOBMFF. El `inspect` real cuesta **0,21–0,59 ms**: la cifra estaba **×4–10 optimista**. **La exención se sostiene igual; su número no.** Y la lección es de consolidación, no de medición: acepté un número sin preguntar qué había medido exactamente el arnés.

Y el cruce copia == `ffprobe` no es una constante de la máquina sino de la tanda:

> **`cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`.** Con `ffprobe` ≈ 57 ms: **~70 MB** con el disco
> contendido (1,2 GB/s) y **~95 MB** holgado (1,6 GB/s). El **1,32×** que midió `cabo5` era el extremo
> rápido de esa misma fórmula, no otra medida.

**Llevado a:** `RESULTADOS-MCP.md` §10 (filas R8 y R18), `PLAN-ORQUESTADOR.md` §4.4, `CLAUDE.md` §5.

---

## 2. Lo que se CIERRA sin cambiar el diseño

| Qué | Estado anterior | Ahora |
|---|---|---|
| **El deadlock de `video-audio-mcp`** | «reproducido en 6, las 20 restantes PENDIENTE» | **26/26 por ejecución, cero excepciones.** 18 directas; las 3 que respondieron lo hicieron en <105 ms **con la basura intacta** —fallos tempranos por entradas del arnés—, y corregida la causa cuelgan también |
| **`resources` y `prompts`** | «cero lecturas, no se pidió» | **El cliente SÍ los enumera; el modelo NO los ve.** Declararlos es coste sin retorno |
| **`notifications/roots/list_changed`** | PENDIENTE | **Capacidad MEDIDA:** `roots.listChanged: true`. Se puede cachear por sesión. *Emisión real*, PENDIENTE acotado |
| **El `.html` clasificado como CSV** | «material para C14» | **CERRADO:** `xml`, `html`, `svg`, `postscript` y `rtf` tienen firma y categoría propias |

Y un matiz que conviene no perder: **`_run_ffmpeg_with_fallback` convierte el deadlock en error solo
cuando ffmpeg falla ANTES de llegar al muxer.** En cuanto el formato es válido y el grafo escribe, el
deadlock reaparece. No cambia la conclusión; delimita dónde el envoltorio la enmascara.

---

## 3. Un sesgo de medición nuevo, y **no es de ruido**

La metodología del proyecto lleva dos testigos: uno de deriva y uno de nivel. **Ninguno de los dos
habría visto este.**

> Con dos semillas de markdown que empezaban por un **título**, **42 formatos de pandoc parecían tener
> marcador**. Con una tercera que empieza por **prosa**, **ninguno lo tiene.**

El marcador no era del formato: era de la semilla. **Cuando midas una propiedad del FORMATO, varía la
entrada; si no, estás midiendo tu entrada.**

**Llevado a:** `CLAUDE.md` §3, junto a los dos testigos.

---

## 4. Salvedades que se declaran en vez de resolverse

1. **`analysis/00-matriz-formatos.md` dice 896/503; la reextracción con el mismo parser da 895/502.**
   La diferencia de uno en cada columna **no se ha localizado**. No cambia ninguna conclusión —los
   porcentajes coinciden a la décima— pero se deja escrita.
2. **Los ~15.700 tokens de diferencia entre `deftools` y `notools`** son las herramientas internas de
   Claude Code, no el catálogo de la sonda. La comparación válida es **dentro** de cada fila.
3. **La carrera de symlinks en Linux (C5a) sigue bloqueada.** El arnés está listo; la VM de WSL2 cae
   con `0x8007274c` bajo contención. **No es un resultado negativo: es una medición no hecha.**

---

## 5. Lo que este trabajo deja ABIERTO

Cinco entradas nuevas en `ESTADO-Y-REPARTO.md` §3.C, todas de F1:

| # | Qué |
|---|---|
| **C27** | Subir **G6** de `aviso` a `fallo`. Hoy calibrada sobre 22 casos de **un solo motor**; hay que comprobar que no marca `png` → `apng` ni `mkv` → `mka` |
| **C28** | Los **86 destinos indeterminados** del censo de firmas. Mismo corpus FATE que **C16** |
| **C29** | Llevar el nivel de **`familia`** al veredicto (hoy `G5` es informativo) |
| **C30** | Repetir la prueba ancha de falsos positivos **dentro del contenedor** (cubre 385 destinos locales, no los 162 del contenedor) |
| **C31** | `_datos` lee el fichero **entero** en memoria (156 MB para contar comas), y dos colisiones declaradas sin falso positivo hoy: `.pcd` → `mpegaudio` y **TGA/CUR** comparten `00 00 02 00` |

Y de M1, una sola: **observar una emisión real de `list_changed`**, que en headless no se puede.

---

## 6. Cómo verificar este documento

```bash
git show 1fb5024 --stat | tail -3          # el commit que trajo los dos informes
git diff 1fb5024 -- CLAUDE.md HUECOS.md PLAN-ORQUESTADOR.md RESULTADOS-MCP.md
grep -n "RE-ACOTADO" RESULTADOS-MCP.md bench/saturacion-herramientas.md
grep -n "G6" PLAN-ORQUESTADOR.md CLAUDE.md HUECOS.md
```

**Nada de lo que hay aquí es una medición propia.** Cada cifra sale de `bench/mcp-cabos-2.md` o de
`bench/firmas-contrato.md`, y las dos frases obligatorias de cada informe siguen en su sitio, sin
reescribir.
