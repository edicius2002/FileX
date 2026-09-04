# `bench/salidas-aristas-escribibles/` — C50 + residuo de C28 (worker10, ronda 20)

Informe: [`bench/aristas-escribibles.md`](../aristas-escribibles.md).

**Todo lo de este directorio se regenera en menos de dos minutos, sin red y sin GPU.**
No hay una sola salida binaria versionada: las 53 muestras escritas (31 679 355 B) se
podaron según la regla §6, y sus `sha256` quedan más abajo y en
`muestras_manifiesto.json`.

## Qué se versiona

| Fichero | Qué es |
|---|---|
| `escribe_ff.py` | pasada 1: escribe los 73 `ff_declarado_muxer` (nominal y `-f muxer`, 4 semillas) |
| `remedios_ff.py` | pasada 2: remedios dirigidos por el `rc` de la pasada 1 |
| `remedios2_ff.py` | pasada 3: los mismos remedios **con el `-f` que la pasada 2 perdió** |
| `contenedor.py` / `contenedor2.py` | dispositivos de Linux, la otra build de ffmpeg, `oeb`, `msgconvert`. La 2 corrige dos defectos de la 1, y las dos se conservan porque la diferencia es el dato |
| `cierres.py` / `cierres2.py` | `chk`, `clip`, `mask`, `gsm` remediado, `eml` |
| `lectura.py` | la segunda mitad: leer las 53 muestras (318 celdas) |
| `recuento50.py` | el número del estrato, con sus dos controles de reproducción |
| `rehace_aristas_copia.py` | copia del arnés de worker9 (`CLAUDE.md` §1 prescribe copiar, no editar el original) que reconstruye `aristas_A.json` |
| `_manifiesto50.py` | genera la tabla de abajo antes de podar |
| `*.json`, `log-*.txt` | las medidas y su traza: `rc` por celda, `argv`, bytes, `stderr` completo |

## Qué NO se versiona, y con qué se rehace

| Activo | Tamaño | Orden que lo reproduce |
|---|---:|---|
| `muestras/` (53 ficheros) | 31 679 355 B | `python escribe_ff.py && python remedios_ff.py && python remedios2_ff.py` |
| `semillas/` (CIF 352×288, wav 48 kHz, srt) | ~90 KB | las crea `escribe_ff.semillas()` en el primer arranque |
| `trabajo/` | 0 B | desechable por celda; el arnés lo borra al terminar cada una |
| `aristas_A.json` | ~6 MB | `python rehace_aristas_copia.py` — no ejecuta ningún motor |
| `crudo/` | ~120 KB | `cp -r ../salidas-aristas-reclasificacion/crudo .` |

## Orden completa, de cero

```sh
cd bench/salidas-aristas-escribibles
cp -r ../salidas-aristas-reclasificacion/crudo .
python rehace_aristas_copia.py
python escribe_ff.py && python remedios_ff.py && python remedios2_ff.py
python contenedor2.py && python cierres.py && python cierres2.py
python lectura.py && python recuento50.py
```

`contenedor2.py` necesita el contenedor `filex-convertx` levantado; los demás, no.

## Las 53 muestras

Cada fila lleva la pasada que la escribió. El `argv` completo de cada una está en
`muestras_manifiesto.json`, campo `orden`. «lectura nominal» es si ffmpeg la vuelve a
leer con la invocación del censo; «estado» es lo que decide el grafo A.

| fichero | bytes | sha256 (12) | pasada | lectura nominal | estado |
|---|---:|---|:--:|:--:|---|
| `m.3g2` | 18698 | `af8a497a4c6b` | 2 | sí | viva |
| `m.3gp` | 18698 | `1cc0e14e249f` | 2 | sí | viva |
| `m.alaw` | 48000 | `8aad261181bc` | 1 | no | muerta |
| `m.alp` | 11041 | `c586b956cded` | 3 | sí | viva |
| `m.amr` | 1638 | `f7da76ab4dde` | 2 | sí | viva |
| `m.argo_asf` | 25544 | `225170ea7f3a` | 1 | sí | viva |
| `m.dash` | 1881 | `68c8860ac1eb` | 1 | no | muerta |
| `m.daud` | 1728192 | `31ff95a246d2` | 3 | sí | viva |
| `m.dirac` | 3131607 | `e50822fdf456` | 1 | sí | viva |
| `m.dnxhd` | 4710400 | `7c92ec665263` | 2 | sí | viva |
| `m.dts` | 177096 | `4cd69ff5b279` | 2 | sí | viva |
| `m.dv` | 3480000 | `5087b1f5a924` | 2 | sí | viva |
| `m.f32be` | 192000 | `ced3dc72bb2d` | 1 | no | muerta |
| `m.f32le` | 192000 | `ceb02d176ea8` | 1 | no | muerta |
| `m.f64be` | 384000 | `c550beca59bc` | 1 | sí | viva |
| `m.f64le` | 384000 | `ac71569b7349` | 1 | sí | viva |
| `m.ffmetadata` | 104 | `051abb6c1c65` | 1 | no | muerta |
| `m.film_cpk` | 219873 | `c2df07cc595f` | 1 | sí | viva |
| `m.filmstrip` | 10137636 | `7053364d3477` | 3 | no | muerta |
| `m.g723_1` | 816 | `9e2d31c7919f` | 3 | sí | viva |
| `m.g726` | 2000 | `8636f8de6b69` | 3 | no | muerta |
| `m.g726le` | 2000 | `14a9b95f6a83` | 3 | no | muerta |
| `m.gxf` | 262052 | `d7731ba5ab9f` | 2 | sí | viva |
| `m.h264` | 7674 | `4421ddd9dd22` | 1 | sí | viva |
| `m.hls` | 112 | `26a9701f80d4` | 1 | no | muerta |
| `m.image2` | 60382 | `dd6d8bcf06d1` | 1 | sí | viva |
| `m.kvag` | 24014 | `d16143e3e62b` | 1 | sí | viva |
| `m.mlp` | 35060 | `da31dddf15ca` | 2 | sí | viva |
| `m.mmf` | 22619 | `762bd4bba491` | 2 | sí | viva |
| `m.mpjpeg` | 163537 | `1f4635e73639` | 1 | sí | viva |
| `m.mulaw` | 48000 | `281582f023e3` | 1 | no | muerta |
| `m.rawvideo` | 3801600 | `712e3796eaf3` | 1 | no | muerta |
| `m.roq` | 100517 | `07c9af47d1cf` | 2 | sí | viva |
| `m.rtp` | 96172 | `3089d95871ed` | 1 | no | muerta |
| `m.s16be` | 96000 | `724f5e489caa` | 1 | no | muerta |
| `m.s16le` | 96000 | `b211f5b9fb00` | 1 | no | muerta |
| `m.s24be` | 144000 | `03289bff3f31` | 1 | no | muerta |
| `m.s24le` | 144000 | `24ec2344f20a` | 1 | no | muerta |
| `m.s32be` | 192000 | `4a57d4b39305` | 1 | no | muerta |
| `m.s32le` | 192000 | `784535318ae4` | 1 | no | muerta |
| `m.s8` | 48000 | `aed744fc9f37` | 1 | no | muerta |
| `m.smjpeg` | 259025 | `38564109850d` | 1 | sí | viva |
| `m.truehd` | 35060 | `0d698520ced1` | 3 | sí | viva |
| `m.u16be` | 96000 | `c22d346710f4` | 1 | no | muerta |
| `m.u16le` | 96000 | `ec76a0218810` | 1 | no | muerta |
| `m.u24be` | 144000 | `9ea4475a7c16` | 1 | no | muerta |
| `m.u24le` | 144000 | `5be8ffc565ce` | 1 | no | muerta |
| `m.u32be` | 192000 | `aed3001b42b7` | 1 | no | muerta |
| `m.u32le` | 192000 | `977e5578709b` | 1 | no | muerta |
| `m.u8` | 48000 | `cf4267b112ae` | 1 | no | muerta |
| `m.vidc` | 48000 | `a1681abad839` | 1 | no | muerta |
| `m.webvtt` | 103 | `a623a28b659d` | 1 | sí | viva |
| `m.wsaud` | 24204 | `150a23da31b5` | 1 | sí | viva |

**53 muestras, 31 679 355 B.** 26 vivas y 27 muertas con la invocación nominal.

> Dos muestras que la tabla marca `muerta` lo son **por un límite declarado del
> arnés, no del formato**: `m.hls` y `m.dash` son la playlist sin sus segmentos,
> porque el arnés copia el fichero nominal y no el directorio. Está escrito en
> `aristas-escribibles.md` §2 y §10.
