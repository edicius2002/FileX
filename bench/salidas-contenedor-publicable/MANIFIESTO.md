# MANIFIESTO — salidas de `bench/contenedor-publicable.md`

Ronda 20, worker11, 2026-09-04. Informe: [`bench/contenedor-publicable.md`](../contenedor-publicable.md).

Todo lo de aquí es **texto**, así que se versiona entero (regla §6: se versionan los `.md`,
los scripts, los `.json` de resultados y los logs). **No se borró ningún binario**, porque
no se generó ninguno: la única salida binaria de este trabajo fue una imagen de Docker, que
vive en el demonio y no en el repositorio, y se retiró al terminar (ver abajo).

## Lo que queda

| Fichero | Bytes | sha256 | Orden que lo reproduce |
|---|---:|---|---|
| `sonda_digest.json` | 4 778 | `0f0e492173c75a82…` | escrito a mano desde las órdenes que cita dentro; cada campo lleva su `orden` |
| `aristas_por_imagen.txt` | 693 | `bdc8546458471522…` | `python -m filex motores` y `FILEX_IMAGEN_DOC=filex-c13-w11 python -m filex motores`, en la misma tanda |
| `build-filex-c13-w11.log` | 6 934 | `5a9fec4bdbc9b618…` | `docker build --platform linux/amd64 -f docker/Dockerfile.c13 -t filex-c13-w11 docker/` |

## La imagen que se construyó, y que ya no está

Para verificar el digest **construyendo** (y no sólo consultándolo) se construyó **una vez**
la imagen `filex-c13-w11`, con etiqueta propia para no pisar `filex-c13`, que es la que usa
el motor y la que sellan los `filex/sondeo/doc_*.json`.

| | valor |
|---|---|
| Etiqueta | `filex-c13-w11` |
| Id | `sha256:0210178ee7b33fe6e477edaabd8e6ca9633f6d880ab6dc8efb90a8b7dac98349` |
| Tamaño | 5,78 GB |
| Orden | `docker build --platform linux/amd64 -f docker/Dockerfile.c13 -t filex-c13-w11 docker/` |
| Coste | `rc=0` en **29 s** (histórico comparable: 28,1 s) |
| Retirada | `docker rmi filex-c13-w11` al terminar — 5,78 GB no se dejan tirados |

**No se tocó `filex-c13`.** Si alguien reproduce esto, que use también una etiqueta propia:
construir sobre `filex-c13` cambiaría su id y **caducaría las 40 aristas selladas** del
proyecto, que es justo el efecto que este informe mide.

## Lo que NO se reproduce solo

`aristas_por_imagen.txt` sólo se reproduce si existen **las dos** imágenes: la sellada
(`filex-c13@6d359bad483e`, que no se puede reconstruir porque su capa `apt-get` es de una
fecha que Debian sid ya no sirve) y una reconstruida hoy. **La fila A es irreproducible por
construcción** — es el propio fenómeno que el informe documenta— y por eso el log y la
salida se conservan aquí en vez de borrarse. No se declara en
`ci/evidencia-irreproducible.txt` porque **no es un binario**: son 693 bytes de texto, y esa
lista existe para binarios.
