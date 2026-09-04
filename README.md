# FileX

[![integridad](https://github.com/edicius2002/FileX/actions/workflows/integridad.yml/badge.svg?branch=main)](https://github.com/edicius2002/FileX/actions/workflows/integridad.yml)
[![suite](https://github.com/edicius2002/FileX/actions/workflows/suite.yml/badge.svg?branch=main)](https://github.com/edicius2002/FileX/actions/workflows/suite.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**Un conversor universal de ficheros que comprueba que la salida es la que pediste, y lo
dice cuando no lo es.** Local, sin servicios externos, en Python de biblioteca estándar y
sin una sola dependencia. Se usa por línea de comandos, como servidor MCP, como watcher de
carpetas o por una API HTTP local.

FileX **no convierte por su cuenta**: invoca a los motores que ya existen —ffmpeg,
ImageMagick, Ghostscript, LibreOffice, Pandoc, Calibre— y se ocupa de la parte que
ninguno de ellos hace, que es **verificar el resultado**.

```
$ filex convertir corpus/video/patologico_2pistas.mkv salida.mp4
salida.mp4   [ok]
  mkv→mp4 [ffmpeg]  rc=0  3672 ms  contrato 6/6 → ok
      [informativo] N9: el fichero declarado lleva el 100.0 % de los bytes escritos
```

Ese fichero tiene **dos pistas de audio**, y salen dos. ConvertX y SnapOtter, medidos contra
ese mismo fichero, entregan una y declaran éxito.

---

## La tesis, en tres frases

No es *«convierte más cosas más rápido»*: eso se midió, resultó discutible y en parte
replicable por otros. Es esto:

> **Es el único de los evaluados que garantiza que lo que te entrega es lo que pediste.**

El proyecto empezó auditando 22 proyectos del ecosistema —leyendo su código y
**ejecutándolos** contra un corpus de casos patológicos— y encontró **siete fallos
independientes en seis proyectos distintos, todos de la misma familia: el software declara
éxito sobre un resultado incorrecto.** Un `.avif` que por dentro es un PNG, entregado con
estado «Done». Una pista de audio que desaparece en silencio. 16 bits degradados a 8 sin
avisar. Una cadena vacía devuelta con `isError: false`.

**Ninguno de los seis orquestadores analizados verifica su propia salida.** Y verificarla
cuesta el **0,032 %** de lo que cuesta convertir *(MEDIDO — `bench/coste-verificacion.md`
§3; la cifra exige leer cabeceras en proceso, y la salvedad está en
[`BENCHMARKS.md`](BENCHMARKS.md) §1)*.

## Empezar

| Quiero… | Ir a |
|---|---|
| **Instalarlo y convertir mi primer fichero** | [`GUIA-DE-USO.md`](GUIA-DE-USO.md) — requisitos reales, los tres comandos básicos y ejemplos ejecutados de verdad, con su salida tal cual |
| **Ver los números que sostienen el proyecto** | [`BENCHMARKS.md`](BENCHMARKS.md) — las cifras medidas, cada una con el informe y la sección de donde sale |
| **Juzgar si el argumento se sostiene** | [`HUECOS.md`](HUECOS.md) — los cinco diferenciadores candidatos, sometidos a ejecución: cuál se confirmó, cuál se debilitó y cuál quedó refutado |
| **Leer la auditoría del ecosistema** | [`ANALISIS-COMPLETO.md`](ANALISIS-COMPLETO.md) — 22 proyectos, leídos y ejecutados, con licencia y veredicto por repositorio |
| **Leer el código** | [`filex/`](filex/) — 22 módulos, biblioteca estándar, cero dependencias. Empieza por `invocacion.py`, el único sitio que puede lanzar un proceso, y sigue por `verificador.py`, que es el contrato |
| **Contribuir** | [`CONTRIBUTING.md`](CONTRIBUTING.md) — los carriles, las cuatro declaraciones que necesita un recuento de suite y **qué NO puede comprobar la CI**, que es lo primero que hay que saber |
| **Modificar el código sin repetir errores ajenos** | [`CLAUDE.md`](CLAUDE.md) — las reglas de trabajo y las **124 trampas ya pagadas**, cada una con la medida que la respalda. Es el documento más útil del repositorio si vas a tocar algo |
| **Saber qué falta** | [`PENDIENTE.md`](PENDIENTE.md) — la lista corta y accionable |
| **Qué cambió en cada versión** | [`CHANGELOG.md`](CHANGELOG.md) |

## Qué está hecho, y cómo se sabe

**Los siete hitos del plan de construcción están HECHOS** ([`PLAN-ORQUESTADOR.md`](PLAN-ORQUESTADOR.md)):
registro de motores, grafo dirigido con coste por arista, confinamiento, invocación
disciplinada, contrato de verificación, motor documental en contenedor, sidecar de IA, y las
**cuatro superficies** —CLI, MCP, watcher y API HTTP local—, todas sobre el mismo núcleo.

**La suite, con las cuatro declaraciones que exige un recuento** (trampas 94 y 101 de
`CLAUDE.md` — un `0 failed` a secas no dice qué se ejecutó):

```
501 passed · 3 skipped · 0 failed · 179 subtests · 265,49 s
```

1. **Intérprete** — `.venv-mcp-filex\Scripts\python.exe`, **win32, 3.11.9**. Las pruebas
   marcadas `win32` (`os.replace` como cerrojo, mutex `Global\`, DACL, nombres 8.3) **sí**
   corren; con un Python de Linux se saltan, y son casi todo el valor del proyecto.
2. **Entorno** — **Docker 29.4.3 levantado**, así que el hito 5 y la cancelación real de
   contenedor se ejecutan. Corpus de Git LFS materializado
   (`corpus/imagen/tipico.png` = **42 855 B**, no un puntero de 130 B).
3. **Qué quedó fuera** — los 3 saltados, los tres declarados: `test_hito4.py:221` (ningún
   par real rasteriza hacia un destino con texto en esta máquina), `test_hito6.py:186`
   (falta un ráster que hay que generar) y `test_hito6.py:697` (pide la tarjeta y
   `FILEX_PRUEBAS_SIDECAR=1`).
4. **Estado de la máquina** — **NO estaba despejada, y se comprobó en vez de suponerlo**:
   la tanda convivió con tres procesos de análisis del propio repositorio. Tardó **265,49 s**
   frente a los **208,05 s** de la tanda de referencia sobre el mismo recuento. **El tiempo
   no es comparable entre tandas; el recuento sí** — y el recuento reproduce exactamente el
   de `bench/raices-mixtas.md` §8 (501 · 3 · 0 · 179). El lock de GPU quedó libre y no se
   usó la tarjeta.

*(MEDIDO el 04/09/2026. Una prueba de cancelación está documentada como **inestable** bajo
carga —fila `N36` del inventario—: esta pasada salió limpia, y una pasada limpia no cierra
una fila de inestabilidad.)*

**El inventario de trabajo** vive en [`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3 y lo
cuenta a máquina `ci/integridad.py`: **126 filas — 114 🟢 cerradas · 3 🟡 en curso · 3 🔴
abiertas**, más 6 ⚫ históricas que se conservan porque documentan una refutación y no
cuentan como trabajo vivo.

## Integración continua, y lo que NO cubre

Esto va antes que la lista de lo que sí hace, porque **una CI verde que no cubre lo que
importa es peor que no tener CI**: es un falso verde, y este repositorio tiene medido lo que
cuesta uno (trampas 94 y 101).

| Flujo | Qué comprueba |
|---|---|
| **`integridad`** | Las nueve comprobaciones de [`ci/integridad.py`](ci/integridad.py). Cada una nació de un defecto **real** encontrado a mano; ninguna está inventada «por si acaso» |
| **`suite-linux`** | Los módulos de prueba que un runner de Linux puede ejecutar, **medidos uno a uno con tope** por [`ci/sonda_linux.py`](ci/sonda_linux.py) — no deducidos |

Lo que **sólo** corre en la máquina del proyecto, y es casi todo el valor:

- **Las pruebas `win32`** — `os.replace` como cerrojo, el mutex `Global\`, la DACL, los
  nombres 8.3. Un runner alojado de GitHub no tiene NTFS.
- **La GPU** — el lock, los seis motores de OCR, el sidecar. No hay RTX 3060 en la nube de
  Actions.
- **Los contenedores locales** — `filex-c13`, SnapOtter, ConvertX, Gotenberg.
- **El corpus** — 254 MiB en Git LFS, y la cuota gratuita es de 1 GB de ancho de banda **al
  mes**: cuatro ejecuciones con `lfs: true` la agotan. Los flujos bajan el repositorio
  **sin** LFS, a propósito.

**Un `✅` de GitHub dice que la documentación es coherente y que el código sigue importando
en Linux. No dice que la medición esté bien.** Eso lo declara quien abre el PR, con las
cuatro declaraciones que pide la plantilla.

Las comprobaciones se ejecutan igual en local, y tardan segundos:

```sh
python3 ci/integridad.py           # las nueve comprobaciones
python3 ci/integridad.py --lista   # qué comprueba cada una, y el defecto real que la motivó
```

## Estructura

```
filex/       El producto: 22 módulos, biblioteca estándar, cero dependencias
pruebas/     19 ficheros de pruebas
analysis/    Un documento por repositorio auditado, más los transversales
bench/       Las mediciones: 100 informes, con sus scripts y arneses
corpus/      44 ficheros de prueba con los casos patológicos (39 en Git LFS, 254 MiB)
ci/          Las comprobaciones de integridad documental y las sondas de aptitud
docker/      Compose de los competidores, levantados para medirlos
```

**Los binarios de salida no se versionan.** Cada carpeta excluida conserva un
`MANIFIESTO.md` con nombre, `sha256`, tamaño y **la orden exacta que la reproduce** —
`bench/salidas-referencia/referencia.json` guarda 39 de esas órdenes. La evidencia sigue
siendo verificable sin arrastrar el peso.

**La excepción está declarada y razonada.** La regla dice «no versiones salidas binarias
*regenerables*», y hay salidas que **no** lo son: los fallos capturados a ConvertX y
SnapOtter no se regeneran, porque esos contenedores cambian de versión. Viven en
[`ci/evidencia-irreproducible.txt`](ci/evidencia-irreproducible.txt), que **exige un motivo
escrito y el documento que lo sostiene** para cada ruta: una lista de excepciones sin razón
es un agujero; con razón es una afirmación que alguien puede refutar.

## Requisitos

Para **usar** FileX basta Python 3.11+ y los motores que quieras que invoque; está todo en
[`GUIA-DE-USO.md`](GUIA-DE-USO.md) §1.

Para **reproducir las mediciones** hace falta el banco de pruebas en el que se hicieron:
RTX 3060 12 GB (compute 8.6), Windows 10, 12 núcleos, Docker + WSL2, Python 3.11, y de
motores nativos `ffmpeg` (con `--enable-gpl --enable-libx264 --enable-libx265
--enable-cuda-llvm`), ImageMagick 7 Q16-HDRI y Ghostscript 10.

```bash
git clone https://github.com/edicius2002/FileX.git && cd FileX
git lfs pull          # el corpus vive en LFS; no hace falta para usar la herramienta
```

## Convención de los documentos

Cada afirmación va marcada **MEDIDO** (hay un dato en `bench/` que la respalda, con su `n` y
la orden que lo reproduce) o **PENDIENTE** (se cree, se deduce o se ha leído en una
documentación, y no vale como base de una decisión).

Donde un resultado contradice a un documento anterior, **se dice y se señala cuál** en vez
de corregirlo en silencio. **Varias de las conclusiones más útiles del repositorio son
autocorrecciones**, y conservar el error al lado de su refutación es deliberado: es lo que
permite comprobar el razonamiento en vez de creérselo.

## Licencia

[MIT](LICENSE).

Los repositorios auditados **no** forman parte de este proyecto y conservan sus propias
licencias —varias son AGPL—; el análisis distingue explícitamente qué se puede copiar, qué
se puede leer y qué no se puede tocar. Ver [`analysis/00-licencias.md`](analysis/00-licencias.md).
