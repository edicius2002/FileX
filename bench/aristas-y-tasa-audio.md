# Tanda B — tasa real de audio y C25

**Entorno MEDIDO:** Git Bash de Windows, `D:\\utils\\ffmpeg\\bin\\ffmpeg.EXE`, build N-121159-g0bd5a7d371-20250921. CPU solamente; GPU no usada. Procesos finitos (`-t 8` o `-t 2`) y tope del arnés 20 s. Directorio temporal listado antes/después. Tanda **SUCIA**: no hubo medianas n>=9 ni testigos, así que los ms sólo son trazabilidad.

## N28 — `-b:a` pedido no es una cota superior

**MEDIDO.** Barrido de 45 celdas: AAC, libopus y libmp3lame; tasas 8/32/96/128/192 kb/s; WAV mono, FLAC y MKV de dos pistas. Buenas (`rc=0`, bytes>0): 40/45; los cinco fallos son MP3 con dos pistas.

| Códec | Celdas | Desvío por pista mínimo…máximo | Signo |
|---|---:|---:|---|
| AAC | 15 | −54,79 % … **+112,62 %** | mixto |
| libopus | 15 | −21,31 % … **+50,48 %** | mixto |
| libmp3lame | 10 | +0,57 % … **+302,29 %** | positivo |

AAC pedido 8 kb/s en dos pistas entrega 15,6 y 17,0 kb/s; Opus pedido 32 entrega hasta 48,2; MP3 pedido 8 se fija en 32,2. **REFUTADO:** `contenedor − n_audio × bitrate_audio_bps` puede sobreestimar vídeo.

**Conclusión MEDIDA:** la resta N28 no aguanta como demostración general y `BITRATE_VIDEO_TOL=0,60` no lo absorbe. Opus a 96 kb/s supera hasta +25,74 % por pista: sobre vídeo 200 kb/s añade 12,36 puntos; sumado al máximo legítimo de vídeo conocido (+56,30 %) rebasa 60 %. **PENDIENTE:** publicar/medir bitrate obtenido por pista, o conservar `informativo` con audio. No cambié V10 sin decidir esa política.

## C25

| Salida | Resultado | rc | Bytes | Estado |
|---|---|---:|---:|---|
| `gxf` | escribe | 0 | 206 416 | **CERRADO** |
| `mlp` | experimental; `-strict -2` escribe | 0 | 62 410 | **CERRADO** |
| `thd` | experimental; `-strict -2` escribe | 0 | 62 410 | **CERRADO** |
| `amv` | dos intentos, incluido perfil 160×120/15 fps/mono 22 050 | −22 EINVAL | 0 | **PENDIENTE** |

MLP/THD refutan «ningún motor lo escribe»: el rc `-733130664 (Experimental feature)` pedía `-strict -2`. AMV llega a `block_size 1470` y EINVAL tras el perfil; dos intentos agotados.

**Crudos MEDIDO.** RGB de tercero: 64×48, 8 bits, 3 B/píxel (9 216 B). `-depth 8` da rc=0 y RMSE normalizado 0,00110054; `-depth 16` da `unexpected end-of-file`, rc=1, 0 B. Se deriva profundidad de bytes/píxel y se elige por RMSE, no rc.

**Bayer MEDIDO/PENDIENTE.** `bayer` y `bayera` escriben/leen rc=0 (3 072 B crudo; 1 049 B PNG), pero no hay referencia CFA independiente: no se declara fidelidad.

**`received no packets` MEDIDO.** El `resid_p2b.json` vigente tiene **15**, no 11: 14 rc −22 y 1 rc −40. Ya llevan reglas P2 M/R/C/F-out (una M/C/F-out); no son una causa única. Semillas P2 podadas: reejecución **PENDIENTE**, no se declaran muertas de nuevo.

## Salidas

| Fichero | Tamaño | SHA-256 | Orden |
|---|---:|---|---|
| `bench/salidas-aristas-tasa/medir.py` | 7 494 B | `ffcbc750b39ff5ae05189db0375b59cdcacc225830fbc6d5ce188046ebdf9ba5` | `python bench/salidas-aristas-tasa/medir.py` desde Git Bash |
| `bench/salidas-aristas-tasa/resultado.json` | 62 355 B | `cd3bf4acb01598901d7544ab5c7310b762a0e447176f6bfc1c8b41654d2c65f6` | salida de la orden anterior |

No se versionaron binarios. Cada celda registra orden, rc, bytes, stderr y segundo intento si falla.
