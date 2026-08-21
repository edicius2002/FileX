# FileX

Conversor universal de archivos, **local-first**, que se entrega como **servidor MCP + CLI + watcher de carpetas + API HTTP local**. Sobre Windows con Docker/WSL2, aprovechando una RTX 3060 de 12 GB.

Cubre 12 categorías: ofimática↔PDF, markup, operaciones PDF, ebooks, imágenes normales y especiales, vídeo, audio, documento→texto para LLM, OCR, datos tabulares y audio/vídeo→texto.

> **Estado: investigación completada, construcción no empezada.** Este repositorio contiene la auditoría de 22 repositorios del ecosistema —leídos a nivel de código y ejecutados en la máquina real— y el plan de construcción que sale de ella. Todavía no hay código de FileX.

---

## La tesis

No es *«convierte más cosas más rápido»* — eso resultó ser discutible y en parte replicable. Es:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

Siete fallos independientes, en seis proyectos distintos, todos del mismo tipo: **el software declara éxito sobre un resultado incorrecto**. Un `.avif` que es un PNG entregado con estado «Done». Una pista de audio perdida en silencio. 16 bits degradados a 8 sin avisar. Una cadena vacía con `isError: false`.

**Ninguno de los seis orquestadores analizados verifica su propia salida.** Y verificarla cuesta el **0,032 %** de lo que cuesta convertir.

## Por dónde empezar

| Si quieres… | Lee |
|---|---|
| **Ponerte a construir** | [`PLAN-ORQUESTADOR.md`](PLAN-ORQUESTADOR.md) — secciones 1, 2 y 3, y arranca por el hito 1 de la §7 |
| Entender **por qué** FileX y no otra cosa | [`HUECOS.md`](HUECOS.md) — los cinco diferenciadores, reevaluados tras ejecutar |
| El análisis completo del ecosistema | [`ANALISIS-COMPLETO.md`](ANALISIS-COMPLETO.md) — 22 repos, 21 tablas comparativas |
| Diseñar la capa MCP | [`RESULTADOS-MCP.md`](RESULTADOS-MCP.md) — incluye las 15 reglas de confinamiento |
| Los motores de IA que faltan por probar | [`AGENTES-PRUEBAS-PENDIENTES.md`](AGENTES-PRUEBAS-PENDIENTES.md) |
| Las reglas y trampas al trabajar aquí | [`CLAUDE.md`](CLAUDE.md) |

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
git clone <url> && cd FileX
git lfs pull          # el corpus vive en LFS
```

## Convención de los documentos

Cada afirmación va marcada **MEDIDO** (hay un dato en `bench/` que la respalda) o **PENDIENTE** (no se ha comprobado). Donde un resultado contradice a un documento anterior, **se dice y se señala cuál** en vez de corregirlo en silencio. Varias de las conclusiones más útiles del repositorio son autocorrecciones.

## Licencia

[MIT](LICENSE).

Los repositorios auditados en `repos/` **no** forman parte de este proyecto y conservan sus propias licencias — varias son AGPL, y el análisis distingue explícitamente qué se puede copiar, qué se puede leer y qué no se puede tocar. Ver `analysis/00-licencias.md`.
