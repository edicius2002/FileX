# FileX

Conversor universal de archivos, **local-first**, que se entrega como **servidor MCP + CLI + watcher de carpetas + API HTTP local**. Sobre Windows con Docker/WSL2, aprovechando una RTX 3060 de 12 GB.

Cubre 12 categorías: ofimática↔PDF, markup, operaciones PDF, ebooks, imágenes normales y especiales, vídeo, audio, documento→texto para LLM, OCR, datos tabulares y audio/vídeo→texto.

> **Estado: los siete hitos, hechos.** Este repositorio contiene la auditoría de 22 repositorios del ecosistema —leídos a nivel de código y ejecutados en la máquina real—, el plan de construcción que sale de ella, y **el producto**: registro, grafo con coste por arista, confinamiento, invocación disciplinada, y **cuatro superficies** —CLI, MCP, watcher de carpetas y API HTTP local—, con la verificación DENTRO de la conversión.
>
> **22 módulos, biblioteca estándar, cero dependencias. 16 ficheros de pruebas.** Suite verificada el 31/08/2026 con `.venv-mcp-filex/Scripts/python.exe` (win32, 3.11.9) y Docker levantado: **424 passed · 2 skipped · 0 failed · 116 subtests** en 156,51 s. Los dos saltados van declarados: uno pide un ráster que hay que generar y el otro la tarjeta (`FILEX_PRUEBAS_SIDECAR=1`). **Un recuento de suite declara su intérprete, su entorno y qué quedó fuera, o no dice qué se ejecutó.**

```
$ filex convertir corpus/video/patologico_2pistas.mkv salida.mp4
salida.mp4   [ok]
  mkv→mp4 [ffmpeg]  rc=0  3672 ms  contrato 6/6 → ok
      [informativo] N9: el fichero declarado lleva el 100.0 % de los bytes escritos
```

Ese fichero tiene **dos pistas de audio**, y salen dos. ConvertX y SnapOtter entregan una y declaran éxito.

---

## La tesis

No es *«convierte más cosas más rápido»* — eso resultó ser discutible y en parte replicable. Es:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

Siete fallos independientes, en seis proyectos distintos, todos del mismo tipo: **el software declara éxito sobre un resultado incorrecto**. Un `.avif` que es un PNG entregado con estado «Done». Una pista de audio perdida en silencio. 16 bits degradados a 8 sin avisar. Una cadena vacía con `isError: false`.

**Ninguno de los seis orquestadores analizados verifica su propia salida.** Y verificarla cuesta el **0,032 %** de lo que cuesta convertir.

## Por dónde empezar

| Si quieres… | Lee |
|---|---|
| **Usarlo** | `python -m filex motores` para ver qué hay, `python -m filex plan a.png b.pdf` para ver qué haría, `python -m filex convertir a.png b.pdf` para hacerlo |
| **Leer el código** | [`filex/`](filex/) — 22 módulos, biblioteca estándar, cero dependencias. Empieza por `invocacion.py`, que es el único sitio que puede lanzar un proceso, y sigue por `verificador.py`, que es el contrato |
| **Seguir construyendo** | [`ESTADO-Y-REPARTO.md`](ESTADO-Y-REPARTO.md) §3 — el inventario vivo: **107 filas, 72 cerradas, 23 abiertas**, agrupadas por el recurso que las limita. Los siete hitos de [`PLAN-ORQUESTADOR.md`](PLAN-ORQUESTADOR.md) están hechos |
| Entender **por qué** FileX y no otra cosa | [`HUECOS.md`](HUECOS.md) — los cinco diferenciadores, reevaluados tras ejecutar |
| El análisis completo del ecosistema | [`ANALISIS-COMPLETO.md`](ANALISIS-COMPLETO.md) — 22 repos, 21 tablas comparativas |
| Diseñar la capa MCP | [`RESULTADOS-MCP.md`](RESULTADOS-MCP.md) — incluye las 15 reglas de confinamiento |
| Los motores de IA que faltan por probar | [`AGENTES-PRUEBAS-PENDIENTES.md`](AGENTES-PRUEBAS-PENDIENTES.md) |
| Las reglas y **las 103 trampas ya pagadas** | [`CLAUDE.md`](CLAUDE.md) — cada una con la medida que la respalda. Es el documento más útil del repositorio si vas a tocar algo |
| **Contribuir** | [`CONTRIBUTING.md`](CONTRIBUTING.md) — los carriles, las cuatro declaraciones que necesita un recuento de suite, y **qué NO puede comprobar la CI**, que es lo primero que hay que saber |

## Integración continua, y lo que NO cubre

Esto va primero, porque **una CI verde que no cubre lo que importa es peor que no tener
CI**: es un falso verde, y este repositorio tiene medido lo que cuesta uno (trampas 94
y 101).

| | |
|---|---|
| **`integridad`** | Las nueve comprobaciones de [`ci/integridad.py`](ci/integridad.py). Cada una sale de un defecto **real** encontrado a mano el 01/09; ninguna está inventada «por si acaso» |
| **`suite-linux`** | Los módulos de prueba que un runner de Linux puede ejecutar, **medidos uno a uno con tope** por [`ci/sonda_linux.py`](ci/sonda_linux.py) — no deducidos |

Lo que **sólo** corre en la máquina del proyecto, y es casi todo el valor:

- **Las pruebas `win32`** — `os.replace` como cerrojo, el mutex `Global\`, la DACL, los
  nombres 8.3. Un runner alojado de GitHub no tiene NTFS.
- **La GPU** — el lock, los seis motores de OCR, el sidecar. No hay RTX 3060 en la nube de
  Actions.
- **Los contenedores locales** — `filex-c13`, SnapOtter, ConvertX, Gotenberg.
- **El corpus** — 254 MB en Git LFS, y la cuota gratuita es de 1 GB de ancho de banda **al
  mes**: cuatro ejecuciones con `lfs: true` la agotan. Los flujos bajan el repositorio
  **sin** LFS, a propósito.

**Un `✅` de GitHub dice que la documentación es coherente y que el código sigue importando
en Linux. No dice que la medición esté bien.** Eso lo declara quien abre el PR, con las
cuatro declaraciones que pide la plantilla.

Se ejecutan igual en local, y tardan segundos:

```sh
python3 ci/integridad.py           # las nueve comprobaciones
python3 ci/integridad.py --lista   # qué comprueba cada una y por qué
```

## Estructura

```
analysis/    Un documento por repositorio auditado, más los transversales
bench/       Mediciones reproducibles: informes, scripts y arneses
corpus/      20 ficheros de prueba con los casos patológicos (en Git LFS)
docker/      Compose de los competidores levantados para medirlos
```

**Los binarios de salida no se versionan.** Cada carpeta excluida conserva un `MANIFIESTO.md` con nombre, `sha256`, tamaño y **la orden exacta que la reproduce** — `bench/salidas-referencia/referencia.json` guarda 39 de ellas. La evidencia sigue siendo verificable sin arrastrar el peso.

## Requisitos para reproducir las mediciones

Verificado en la máquina de referencia: RTX 3060 12 GB (compute 8.6), Windows 10, 12 núcleos, Docker + WSL2, Python 3.11.

Nativos: `ffmpeg` (con `--enable-gpl --enable-libx264 --enable-libx265 --enable-cuda-llvm`), ImageMagick 7 Q16-HDRI, Ghostscript 10. Lo que falta va en contenedor, no instalado a mano.

```bash
git clone https://github.com/edicius2002/FileX.git && cd FileX
git lfs pull          # el corpus vive en LFS
```

## Convención de los documentos

Cada afirmación va marcada **MEDIDO** (hay un dato en `bench/` que la respalda) o **PENDIENTE** (no se ha comprobado). Donde un resultado contradice a un documento anterior, **se dice y se señala cuál** en vez de corregirlo en silencio. Varias de las conclusiones más útiles del repositorio son autocorrecciones.

## Licencia

[MIT](LICENSE).

Los repositorios auditados en `repos/` **no** forman parte de este proyecto y conservan sus propias licencias — varias son AGPL, y el análisis distingue explícitamente qué se puede copiar, qué se puede leer y qué no se puede tocar. Ver `analysis/00-licencias.md`.
