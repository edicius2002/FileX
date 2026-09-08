# MANIFIESTO — cierre global

Todo lo versionado en este directorio es texto. Las salidas binarias y semillas
se generaron bajo `%TEMP%/filex-resondeo-global-20260907` y quedaron fuera del
repositorio. No se habilitó GPU, OpenCL ni aceleración hardware.

| fichero | contenido | reproducción |
|---|---|---|
| `resondeo-ffmpeg.json` | 70 conversiones reales, una por arista | `preparar_fuentes.py` y `sondear_ff.py <temporal> 1` |
| `resondeo-imagemagick.json` | 124 celdas: 62 pares por dos semillas | `sonda_im.py <semillas> <salidas> <json>` con OpenCL apagado |
| `resondeo-ico256.json` | 7 controles adicionales de escritura ICO | `_ico256_r7.py <semillas> <salidas> <json>` |
| `resondeo-documentos.json` | 40 conversiones sobre `filex-c13@6d359bad…` | `_resondeo40.py --salida <json> --out <temporal>` |
| `n38-windows-34175258765.json` | artefacto hospedado: 100 intentos N38 sobre Windows | workflow `windows-tests`, run 34175258765 |
| `sellar.py` | valida claves, conteos, builds y resultados antes de escribir los cinco sellos | ver orden siguiente |

Sellado reproducible a partir de los registros crudos:

```powershell
python bench/salidas-cierre-global/sellar.py `
  --ffmpeg <temporal>/ffmpeg/resultados.json `
  --imagemagick <temporal>/imagemagick/reducido.json `
  --documentos <temporal>/documentos/resondeo40.json
```

El script exige exactamente `70 + 62 + 16 + 16 + 8 = 172` claves y que
coincidan con las tablas anteriores. También exige el mismo build y `rc=0` más
contrato no fallido para toda arista declarada real. Escribe de forma atómica.

SHA-256 de los cuatro registros: FFmpeg
`c5bec8775786765a376971b7337e320914d94b6c277cfb1d100c601ae2a18b91`;
ImageMagick `384901ae12ff6326c065ae216d3605624ae24ad0e2df437906e08b280ff964b2`;
ICO `6a03fe513e9a5d816f9ed1c3fcd5255edbafebccd6cda583bf776da95a22339f`;
documentos `dd4d5e9d2cf79efad6d04c14c63a4cbcd1be4a6e7c159e85e103e9d55ee9095`.
El artefacto N38 tiene SHA-256
`c4c1e1293591fa4fa268915c3b3da9aafb5901337c9fcc1c8aa35cfdbfbc39d7`.
