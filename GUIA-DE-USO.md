# Guía de uso

Esta guía es para quien sólo quiere **usar** FileX: convertir ficheros, no tocar su código.
Si vas a contribuir o a modificar `filex/`, esta guía no es para ti — lee
[`CONTRIBUTING.md`](CONTRIBUTING.md) y [`CLAUDE.md`](CLAUDE.md) en su lugar.

Todo lo que hay aquí abajo se ejecutó de verdad en la máquina de referencia el 03/09/2026,
con el intérprete `.venv-mcp-filex/Scripts/python.exe` (win32, 3.11.9) y Docker levantado. La
salida está copiada tal cual, no reconstruida.

---

## 1 · Qué hace falta tener instalado

**Lo mínimo, siempre:** Python 3.11 o superior. FileX **no tiene dependencias de Python** —
la biblioteca estándar le basta (`pyproject.toml`: `dependencies = []`) — así que
`pip install -e .` no baja nada de internet salvo el propio empaquetado.

**Para que haya algo que convertir de verdad**, además del intérprete hacen falta los
motores, y aquí hay que ser honesto: **FileX no los trae consigo, los invoca**. En la
máquina de referencia:

| Motor | Vía | Para qué |
|---|---|---|
| `ImageMagick` 7 (Q16-HDRI) | nativo, en el `PATH` | imágenes |
| `Ghostscript` 10 | nativo, en el `PATH` | PDF, OCR sin GPU |
| `ffmpeg` (con `--enable-gpl --enable-libx264 --enable-libx265`) | nativo, en el `PATH` | vídeo, audio |
| LibreOffice, Pandoc, Calibre | **contenedor Docker** (`filex-c13`) | ofimática↔PDF, ebooks, markup |

Sin ninguno de los tres nativos instalados, `filex motores` declara el grafo entero **sin
sondear** y cualquier conversión falla con `ningún motor disponible lee '<formato>'` — es un
fallo honesto, no un cuelgue, pero es un fallo. Sin Docker, pierdes el tercio ofimático del
catálogo; el resto (imagen, vídeo, audio, PDF) sigue funcionando igual. No hay gestor de
paquetes que resuelva esto por ti: lo que falte se instala a mano o se levanta en contenedor
(`docker/`).

## 2 · Instalación

Verificado en un venv desechable aparte, para no tocar ninguno de los venvs protegidos del
proyecto:

```
$ python -m venv .venv
$ .venv\Scripts\pip install -e .
Obtaining file:///.../FileX
...
Successfully installed filex-0.1.0
$ .venv\Scripts\filex --version
filex 0.1.0
```

Si no quieres instalarlo, no hace falta: `python -m filex ...` funciona igual desde la raíz
del repositorio clonado, sin ningún paso previo. Todos los ejemplos de esta guía se
ejecutaron así.

```bash
git clone https://github.com/edicius2002/FileX.git
cd FileX
python -m filex --version
```

`git lfs pull` **no hace falta para usar la herramienta** — el corpus de 254 MB en Git LFS es
para reproducir las mediciones de `bench/`, no para convertir tus propios ficheros.

## 3 · Los tres comandos básicos

### `filex motores` — qué hay instalado, ahora mismo

```
$ python -m filex motores
FileX 0.1.0

MOTORES
  ✓ imagemagick    7.1.2-21       67 aristas (67 medidas)
  ✓ ghostscript    10.07.0         4 aristas (4 medidas)
  ✓ ffmpeg         N-121159-g0bd5a7d371-20250921   85 aristas (83 medidas)
  ✓ doc_libreoffice 29.4.3 · filex-c13@6d359bad483e   18 aristas (16 medidas)
  ✓ doc_pandoc     29.4.3 · filex-c13@6d359bad483e   24 aristas (24 medidas)
  ✓ doc_calibre    29.4.3 · filex-c13@6d359bad483e   17 aristas (16 medidas)

GRAFO: 215 aristas, 210 respaldadas por una medición reproducible del patrón oro.
El resto están SIN SONDEAR y se marcan como tal: declarar 'nominal'
como si fuera 'real' es el fallo central del sector (41,0 % de las
aristas que los catálogos declaran no existen).
```

Un `✗` en vez de `✓` significa que ese motor no se encontró: la fila desaparece del grafo,
no se inventa una arista para rellenar el hueco.

### `filex plan origen destino` — qué camino elegiría, y qué descartó

```
$ python -m filex plan corpus/imagen/tipico.png salida.pdf
CAMINO (1 salto(s), coste 1.2):
  png → pdf
      1. png→pdf [imagemagick]

DESCARTADO  png → ico → pdf
  porque válido, pero más caro

DESCARTADO  png → webp → pdf
  porque válido, pero más caro

DESCARTADO  png → avif → pdf
  porque válido, pero más caro

DESCARTADO  png → jpg → pdf
  porque válido, pero más caro

(+3 camino(s) válido(s) y más caro(s))
```

`plan` no toca disco ni lanza ningún motor: es sólo el grafo, para saber qué va a pasar
antes de que pase.

Si el destino no tiene ningún camino, lo dice sin ambigüedad y sale con código de error:

```
$ python -m filex plan corpus/imagen/tipico.png salida.xyz
NO HAY CAMINO — ningún motor disponible escribe 'xyz'
```

### `filex convertir origen destino` — convertirlo de verdad

```
$ python -m filex --raiz corpus --raiz . convertir corpus/video/patologico_2pistas.mkv salida.mp4
salida.mp4   [ok]
  mkv→mp4 [ffmpeg]  rc=0  5273 ms  contrato 6/6 → ok
      [informativo] N9: el fichero declarado lleva el 100.0 % de los bytes escritos (3966842 de 3966842 B)
```

Ese `.mkv` tiene **dos pistas de audio**, y `salida.mp4` sale con las dos. Es el ejemplo que
abre el `README.md`: ConvertX y SnapOtter, medidos frente a este mismo fichero, entregan una
sola pista y declaran éxito igual.

`contrato 6/6 → ok` significa que pasaron las seis casillas de cobertura que el verificador
evalúa *dentro* de la conversión (no después, no con un `ffprobe` aparte). Salen de los
**cinco puntos** del contrato — firma real, flujos, propiedades declaradas frente a
obtenidas, lo pedido frente a lo obtenido, y que el motor no escribió nada fuera de lo
declarado —, con el cuarto contando en dos casillas (lo pedido/obtenido y el canal alfa). Los
cinco puntos están descritos uno por uno en `CLAUDE.md` §5. `[informativo]` es una
observación que no baja el veredicto; `[aviso]` sí lo baja a `ok_parcial`; `[fallo]` lo baja a
`fallo`.

## 4 · El confinamiento: `--raiz`

FileX deniega por defecto: si no le dices qué directorios puede tocar, no confía en ninguno y
te lo avisa en vez de arrancar en silencio sin protección:

```
$ python -m filex convertir corpus/video/patologico_2pistas.mkv salida.mp4
aviso: sin --raiz no hay lista blanca (denegar por defecto está desactivado)
salida.mp4   [ok]
  ...
```

Con `--raiz` (repetible), sólo esos directorios son accesibles — origen y destino tienen que
caer dentro de alguno:

```
$ python -m filex --raiz corpus convertir corpus/imagen/tipico.png fuera-de-la-raiz.pdf
NO CONVERTIDO — ruta no accesible
```

El mensaje es deliberadamente el mismo tanto si la ruta está fuera de la lista blanca como si
no existe: un mensaje distinto en cada caso le regalaría a quien está sondeando la diferencia
entre «prohibido» y «no existe» (`CLAUDE.md`, trampa 28).

## 5 · Qué esperar de la salida

- **`[ok]`** — las casillas de cobertura del contrato pasaron. Lo que tienes es lo que pediste.
- **`[ok_parcial]`** — pasó, pero con un aviso: algo se salió de lo declarado (un fichero
  extra en el directorio de trabajo, por ejemplo) sin que eso invalide el resultado.
- **`[fallo]`** — el contrato no se cumple, aunque el motor no haya devuelto ningún error de
  proceso. Es la tesis del proyecto: un `rc=0` del motor no es un éxito, es sólo que el
  proceso no reventó — lo que declara éxito o fracaso es el contrato, no el motor.

`filex convertir --json` da la misma información en JSON, si vas a consumirla desde otro
programa en vez de leerla en la terminal.
