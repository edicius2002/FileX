# MANIFIESTO — `bench/salidas-fate-completo/`

Salidas de worker11 (ronda 1, carril CPU/Docker nuevo): `C28` (los 12 formatos
restantes del techo de 15/56) y `C16` (ampliación de la muestra con alias). Ver
`bench/fate-completo.md`.

**El corpus FATE (`D:\Work\research\fate-suite`, 1,3 GB) no se copia ni se versiona** —
los scripts lo referencian por ruta absoluta y no escriben nada dentro de él.

## Ficheros

| Fichero | Tamaño | sha256 | Orden |
|---|---:|---|---|
| `c28_12_restantes_fate.py` | 11 764 B | `0d0e111b79d661713cf919966a89a19f619d892b4993a5a1ad7f567d18bc3792` | `python bench/salidas-fate-completo/c28_12_restantes_fate.py` |
| `c28_12_restantes_fate_resultado.json` | 9 305 B | `ad92103adde92e25f0091b2758fb298eda6e8492d2220af99ef4d2c604a37315` | salida de la orden anterior |
| `_faltan.json` | 4 185 B | `3458aa72737cb56cfc770eac57ae663fce851096872385ebdf92a8ac8ca556b3` | lista de los 376 formatos "no_materializables" sin emparejar por nombre de directorio exacto — generada inline al explorar (ver `bench/fate-completo.md` §2.1) |
| `_sondeo_alias.py` | 2 388 B | `c51247ef7b7db88bd7c7c4434a972ed7ef768b787c58d54eb03392ad13282633` | sonda previa (no oficial): `python bench/salidas-fate-completo/_sondeo_alias.py` — confirma con `ffprobe` natural que cada alias candidato es genuino antes de gastar la tanda completa |
| `c16_alias_fate.py` | 7 902 B | `8fa78045fe2969ed14a9f20850d09563f5fd88be6d793aa64332f45bf6c5b015` | `python bench/salidas-fate-completo/c16_alias_fate.py` |
| `c16_alias_fate_resultado.json` | 13 648 B | `43f0a3ef7babd536c534497e7a5bc6cc557f095e4e7ae02ab1e7012ae17302cf` | salida de la orden anterior |
| `c16_alias_fate_imagemagick.py` | 5 686 B | `e4b95b6168a951cf12f2c5eee5605ebbd796225a91784d2c49c8c75ff4b18cdb` | `python bench/salidas-fate-completo/c16_alias_fate_imagemagick.py` |
| `c16_alias_fate_imagemagick_resultado.json` | 1 531 B | `fb15428e7166a635fce9d46264faae812387f14ecd52b46f53b4be0c54a4981f` | salida de la orden anterior |
| `c16_alias_nivel2.py` | 4 475 B | `d55b1634b38669109707c5e641fdd3e8f237b015a33addc7209e79dec8583a07` | `python bench/salidas-fate-completo/c16_alias_nivel2.py` (lee los dos resultados anteriores) |
| `c16_alias_nivel2_resultado.json` | 21 899 B | `37e846802fed58a84e80cdb630f7f93497a1332f484f9626fa006694c83cce81` | salida de la orden anterior |

## Notas

- Sin binarios: los directorios temporales de cada script (`tmp_c28_12/`, `tmp16b/`,
  `tmp16c/`, `tmp16im/`) se crean y se borran al terminar cada corrida.
- `c28_12_restantes_fate.py` busca los 12 formatos del techo de `firmas-cierre.md`
  §4.4 primero por directorio de FATE con el mismo nombre y, si no hay, por extensión
  en todo el corpus, sondeando con `ffprobe` cada candidato antes de aceptarlo (evita
  la colisión de `.bit` con HEVC/VVC/MP3 de conformidad).
- `c16_alias_fate.py` prueba 24 alias de ffmpeg (23 con autodetección natural + `asf_o`
  forzado con `-f`) verificados uno a uno en `_sondeo_alias.py` antes de correr la
  tanda oficial.
- `c16_alias_fate_imagemagick.py` prueba `heic` y `3gp` (encontrados por extensión, no
  por directorio) y declara `raw` como colisión de extensión sin contarlo como acierto.
- `c16_alias_nivel2.py` repite el nivel 2 de `c16_muestra_aristas_fate.py` (6 destinos
  por origen) sobre los 24 orígenes vivos de los dos scripts de alias.
