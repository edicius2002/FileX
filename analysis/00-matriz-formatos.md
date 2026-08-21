# Matriz de formatos — extraída del código, no de los README

Fuente: parseo automático de las declaraciones `properties.from` / `properties.to` de los 20 adaptadores de ConvertX (`repos/orchestrators/ConvertX/src/converters/*.ts`). Son las tablas que el código consulta en tiempo de ejecución.

## Cobertura declarada por motor

| Motor | Formatos entrada | Formatos salida | Entradas exclusivas |
|---|---:|---:|---:|
| ffmpeg | 473 | 202 | **422** |
| imagemagick | 245 | 183 | 78 |
| graphicsmagick | 167 | 130 | 29 |
| assimp | 77 | 23 | 69 |
| vips | 45 | 23 | 17 |
| libreoffice | 41 | 22 | 29 |
| pandoc | 40 | 58 | 31 |
| calibre | 26 | 20 | 16 |
| libheif | 11 | 3 | 4 |
| libjxl | 11 | 10 | 0 |
| vtracer | 8 | 1 | 0 |
| inkscape | 7 | 17 | 0 |
| markitdown | 6 | 1 | 3 |
| dasel | 5 | 4 | 2 |
| dvisvgm | 4 | 2 | 2 |
| potrace | 4 | 11 | 0 |
| xelatex | 2 | 1 | 1 |
| msgconvert | 1 | 1 | 1 |
| resvg | 1 | 1 | 0 |
| vcf | 1 | 1 | 1 |

**Totales canónicos:** **896 formatos de entrada únicos, 503 de salida.**

> **Corrección metodológica.** Una primera extracción dio 893/496 porque la expresión regular limitaba los identificadores a 12 caracteres y descartaba 7 dialectos largos de pandoc (`markdown_strict`, `markdown_phpextra`, `asciidoc_legacy`, `jats_archiving`, `jats_articleauthoring`, `jats_publishing`, `pandoc native`). Las cifras de este documento son las de la extracción sin límite de longitud, confirmadas por una segunda extracción independiente vía AST.

## El agujero que nadie menciona: ConvertX no convierte hojas de cálculo

Búsqueda de `xlsx`, `xls` y `ods` en los 20 adaptadores: **cero apariciones**, ni como entrada ni como salida. Tampoco `ppt` ni `odp`; `pptx` solo entra por markitdown y sale por pandoc.

La causa está en `libreoffice.ts`: registra **únicamente la familia `text:`** (líneas 6 y 51), aunque el binario `soffice` que invoca convierte hojas de cálculo y presentaciones sin problema. **Es una limitación de la tabla declarada, no del motor.**

Un proyecto de 18 500 estrellas que anuncia "1000+ formatos" no puede convertir un Excel. Refuerza la tesis central de esta investigación: **las cifras de cobertura del sector describen tablas declaradas, no capacidades reales**, y por eso todo aquí se ha extraído del código.

## Dos conclusiones que cambian las prioridades

### 1. El "1000+ formatos" del marketing son en realidad dos binarios
**ffmpeg e ImageMagick juntos cubren 675 de los 896 formatos de entrada: el 75%.** Todo el resto del ecosistema aporta el 24% restante. Integrar bien esos dos motores es el 76% del trabajo de cobertura.

### 2. Los motores irremplazables se identifican por sus formatos exclusivos
- **ffmpeg** (422 exclusivos): insustituible. `264`, `265`, `3dostr`, `4xm`, `669`...
- **imagemagick** (78): `ai`, `bayer`, `bgra`, `bmp2`...
- **assimp** (69): todo el 3D (`3ds`, `3mf`, `ac3d`, `ase`). *Categoría excluida por decisión tuya, pero el adaptador existe si algún día interesa.*
- **pandoc** (31): el markup académico (`bibtex`, `biblatex`, `commonmark`, `djot`, `creole`).
- **libreoffice** (29): la ofimática heredada (`doc`, `docm`, `dot`, `abw`, `cwk`, `602`).
- **calibre** (16): ebooks y cómic (`azw4`, `cbr`, `cbz`, `cb7`, `chm`, `djvu`).
- **vips** (17): imagen científica y microscopía (`mrxs`, `ndpi`, `nia`, `svs`).

Ninguno de estos siete se puede suprimir sin perder una categoría entera.

## El cálculo que justifica el grafo de conversión

Con las mismas 20 tablas, se comparó la cobertura del despacho de un salto (lo que hace todo el ecosistema) contra un grafo dirigido recorrido hasta 3 saltos:

| Estrategia | Pares (origen, destino) alcanzables |
|---|---:|
| **1 salto** (ConvertX, transmute, SnapOtter, todos) | 152 584 |
| **Grafo, hasta 3 saltos** | **447 398** |
| **Conversiones nuevas que hoy no puede hacer nadie** | **294 814** |

**Multiplicador: 2,93× la cobertura, con exactamente los mismos motores instalados.**

Ejemplos verificados sobre el grafo real:

| Conversión | Estado hoy | Con grafo |
|---|---|---|
| `epub` a `png` | ❌ imposible | ✅ 2 saltos |
| `docx` a `webp` | ❌ imposible | ✅ 2 saltos |
| `tex` a `docx` | ❌ imposible | ✅ 2 saltos |
| `cbz` a `pdf` | ✅ ya directo | igual |
| `heic` a `avif` | ✅ ya directo | igual |

### Salvedad honesta
La cifra de 447 398 es un **límite superior de alcanzabilidad, no una promesa de fidelidad**. Encadenar degrada: pasar por un formato rasterizado pierde el texto seleccionable, y algunos pares declarados son nominales (un motor "acepta" un formato con soporte parcial). Por eso el grafo necesita **coste por arista** —velocidad, pérdida de calidad, si preserva texto— y no solo conectividad. Un camino de 3 saltos que destruye el contenido debe puntuar peor que "no se puede".

Aun descontando agresivamente, el margen sobre 152 584 es enorme, y **es puramente algorítmico: no requiere ni un motor más.**
