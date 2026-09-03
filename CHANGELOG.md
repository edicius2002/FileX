# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/). El proyecto
sigue en `0.1.0` (`pyproject.toml`) desde el primer commit — **no hay ni un tag ni un
release en GitHub todavía**. Este documento no cambia eso: sólo ordena lo que ya pasó, para
que la decisión de versionar se tome con la lista delante.

Fuente de cada entrada: `git log --oneline` y los informes de `bench/` que cita cada hito en
[`PLAN-ORQUESTADOR.md`](PLAN-ORQUESTADOR.md) §7. No se han inventado fechas ni alcance — donde
un hito se marcó HECHO días después de cerrarse de verdad, se usa la fecha del propio
`PLAN-ORQUESTADOR.md`, no la del commit del marcador.

## [Sin publicar]

Todo lo de abajo vive en `main`, sin tag. El repositorio arrancó el 20/08/2026 con el commit
`f0a0858` (*«Investigación del ecosistema de conversión de archivos»*) y sigue activo hoy,
03/09/2026 — 174 commits.

### Añadido

- **Los siete hitos del plan de construcción, todos HECHOS** — commit `907de96`, 28/08/2026,
  *«LOS SIETE HITOS, HECHOS — y el último se cerró refutando su propia premisa»*:
  - **Hito 1 — Registro, grafo y CLI** (22/08, commit `6e66406`). El registro de motores, el
    grafo dirigido con coste por arista, y `filex convertir/motores/plan/destinos` por línea
    de comandos. Con ffmpeg e ImageMagick cubre ~75 % de los formatos. Resuelve caminos de
    dos saltos explicando por qué descarta uno que rasteriza cuando el destino admite texto.
  - **Hito 2 — NVENC con sondeo y degradación** (28/08, commit `c980927`). `hevc_nvenc` por
    defecto en destino HEVC; `av1_nvenc` se sondea, falla si no está disponible y degrada a
    `libsvtav1` sin intervención, dejando constancia (`filex.degradado_de=...`) en el
    fichero de salida.
  - **Hito 3 — Contrato de verificación** (22/08, commit `c2f6a59`). Cinco puntos de
    verificación que corren dentro de la conversión, no después: firma real, flujos,
    propiedades declaradas frente a obtenidas, y que el motor no escribió nada fuera de lo
    declarado. Reproduce y atrapa los tres fallos de verificación encontrados en los
    competidores (extensión falsa, pista de audio perdida, degradación de bits silenciosa).
  - **Hito 4 — Capa MCP** (22/08, commit `c2f6a59`). Servidor MCP con cinco herramientas
    escritas a mano, catálogo generado desde el mismo registro que usa la CLI (añadir un
    motor no toca esta capa) y lista blanca de rutas con denegación por defecto.
  - **Hito 5 — Motor documental en contenedor** (22/08, commit `0c35af2`).
    `docx/xlsx/pptx/odt/epub → pdf` vía un contenedor con LibreOffice, Pandoc y Calibre
    (`filex-c13`), con el tope de tiempo puesto dentro del contenedor.
  - **Hito 6 — Sidecar de IA para OCR y transcripción** (28/08, commit `2a939ef`). Proceso
    Python persistente con registro LRU por VRAM, TTL y admisión por una recta de coste
    medida antes de cada página; faster-whisper y Docling+RapidOCR, un trabajador por
    (motor, dispositivo) tras medir que dos modelos en el mismo proceso pueden matarlo en
    silencio.
  - **Hito 7 — Watcher de carpetas y API HTTP local** (23/08, commit `5ff449a`). Las cuatro
    superficies completas (CLI, MCP, watcher, API HTTP), todas sobre el mismo núcleo — una
    prueba estructural comprueba que ninguna reimplementa la resolución de rutas o la
    invocación de motores por su cuenta.
- **Confinamiento por lista blanca de raíces** (`--raiz`, repetible), con denegación por
  defecto y mensaje opaco compartido entre «ruta prohibida» y «ruta inexistente», para no
  filtrar esa diferencia a quien esté sondeando el sistema.
- **CI en GitHub Actions**, dos flujos (commit `62ba538`, 01/09/2026): `integridad` (las
  nueve comprobaciones documentales de `ci/integridad.py`, en cada push y PR) y `suite` (los
  módulos de prueba que un runner de Linux puede ejecutar de verdad, medidos uno a uno con
  `ci/sonda_linux.py` en vez de deducidos).
- **`ci/integridad.py`**: nueve comprobaciones —citas de commit vivas, inventario contado a
  máquina, un emoji de estado por fila, trampas sin huecos, informes registrados,
  manifiestos de las salidas binarias, ausencia de secretos, binarios sueltos fuera de LFS y
  ausencia de cabeceras «en curso»— cada una nacida de un defecto real encontrado a mano.

### Cambiado

- **El corpus de pruebas se movió a Git LFS** y el repositorio se preparó para hacerse
  público (commit `710d4ab`, 31/08/2026): la credencial de un contenedor de investigación
  local se borró del repositorio y de las 65 revisiones de su historia
  (`git filter-repo --replace-text`), y se liberaron 598 MB de entornos virtuales ya
  cerrados.
- **La huella del código pasó a declarar el intérprete de sellado** en vez de comparar entre
  versiones de Python distintas sin decirlo (commit `42f090d`, 02/09/2026) — antes, cambiar
  de intérprete caducaba las 215 aristas selladas sin que el código hubiera cambiado una
  línea.
- **El runner de CI para lo que sólo corre en la máquina del proyecto** (GPU, NTFS,
  contenedores locales) se decidió **autoalojado, con aprobación manual para PRs de
  terceros** (02/09/2026) — el registro del runner en GitHub queda fuera de este repositorio,
  es una acción del usuario.

### Corregido

- Tres fallos de verificación reproducidos y cerrados contra los propios competidores
  (`ConvertX`, `SnapOtter`): una extensión de salida que no coincide con el contenido real,
  una pista de audio que desaparece en silencio al convertir un `.mkv` con dos pistas, y una
  degradación de profundidad de bits de 16 a 8 sin aviso — los tres declarados «éxito» por
  el software que los produjo, los tres detectados por el contrato de FileX.

## Cómo se cuenta esto

Cada hito, commit y cifra de esta lista se puede volver a comprobar: `git log --oneline` y
los informes de `bench/` citados en `PLAN-ORQUESTADOR.md` §7 son la fuente, no este fichero.
Si una cifra de aquí y una de `bench/` no coinciden, la de `bench/` es la que manda —
avísalo en vez de corregir este fichero en silencio (es la misma regla que sigue el resto del
proyecto: ver la «Convención de los documentos» de `README.md`).
