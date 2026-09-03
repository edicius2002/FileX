# MANIFIESTO — `bench/salidas-aristas-documentales-cierre/`

worker7, carril `edicius2002/filex-aristas-doc`. Cierra el hueco descrito en
`ENCARGO.md` (`fx.destinos('csv')` → `[]`) y RESONDEA de verdad, con
`FileX.convertir()` real, las 55 aristas `REAL` de `doc_libreoffice` (24) y
`doc_pandoc` (31) tras añadir 15 tuplas nuevas a `_DECLARADAS`
(`filex/motor_contenedor.py`). Ver el informe completo en
`bench/aristas-documentales-cierre.md`.

## Qué se versiona

- `_resondeo55.py` — el arnés. Copia de la mecánica de forzar-arista de
  `bench/salidas-sondeo-doc/_sonda23.py` (S3), no la edita (`CLAUDE.md` §1).
  Llama a `filex.nucleo.FileX.convertir()` de verdad: motor.orden(),
  `invocacion.ejecutar()` con Docker real, `contrato.verificar()` de cinco
  puntos y el censo del punto 5.
- `_sellar.py` — construye `filex/sondeo/doc_libreoffice.json` y
  `doc_pandoc.json` a partir de `resondeo55.json`, con la huella nueva
  (`filex.huella.de_motor`) y la nota de RESONDEO.
- `resondeo55.json` — las 55 medidas crudas (rc, ms, bytes, sha256,
  caracteres, centinela, veredicto y hallazgos del contrato).
- `resondeo55.log`, `pytest.log`, `pytest2.log`, `ci-integridad.log` — la
  trazabilidad de esta ronda.

## Qué NO se versiona (binarios regenerables)

`out/` (55 ficheros de salida + 55 copias-espía del desechable, ~710 KB) y
`entradas/entrada.xlsx` / `entrada.pptx` (semillas fabricadas por R01/R02, no
son fuente): se borran al terminar. La orden que los reproduce:

```
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-aristas-documentales-cierre/_resondeo55.py
D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe bench/salidas-aristas-documentales-cierre/_sellar.py
```

(Requiere Docker levantado, el contenedor `filex-c13` disponible y las
semillas de `bench/salidas-hito5/entradas/` y `bench/salidas-sondeo-doc/
entradas/` — ambas ya versionadas por K1 y S3.)

## Las 55 aristas medidas — `rc`, bytes, sha256 (16 hex) y veredicto del contrato

Las tres celdas `aviso` (R29, R40, R55) son el hallazgo P1 ya conocido y
aceptado del proyecto (`bench/sondeo-documental.md` §7.2): el número de
páginas de un PDF de pandoc vive en un flujo `/ObjStm` comprimido y no se
puede contar sin descomprimirlo con `zlib` — **no es un fallo**, es severidad
`aviso`. Las 52 restantes dan `ok` u `ok_parcial`. **0 de 55 dio `rc≠0` ni
`contrato=fallo`.**

| id | motor | origen>destino | bytes | sha256 (16 hex) | contrato |
|---|---|---|---|---|---|
| R01 | doc_libreoffice | csv>xlsx | 5790 | `663d0e891cf20104...` | ok_parcial |
| R02 | doc_pandoc | md>pptx | 28169 | `38bf3bfed0fe341b...` | ok_parcial |
| R03 | doc_libreoffice | docx>html | 2399 | `b2b2b31ae926929d...` | ok |
| R04 | doc_libreoffice | docx>odt | 13561 | `612f06c9b669ad45...` | ok_parcial |
| R05 | doc_libreoffice | docx>pdf | 22820 | `057b1c40a98b652d...` | ok |
| R06 | doc_libreoffice | docx>png | 38798 | `7e4bb0c2864c4d20...` | ok |
| R07 | doc_libreoffice | html>pdf | 32807 | `4ad26047be1b537e...` | ok |
| R08 | doc_libreoffice | odt>docx | 6063 | `984a5f2544ab5a1f...` | ok_parcial |
| R09 | doc_libreoffice | odt>pdf | 31976 | `8f98fd501edb9db0...` | ok |
| R10 | doc_libreoffice | odt>txt | 458 | `80d4fe7cad8d9eb7...` | ok |
| R11 | doc_libreoffice | rtf>pdf | 21412 | `1a3daeee8b3b1fad...` | ok |
| R12 | doc_libreoffice | txt>pdf | 16940 | `f6f1afa6c5f4e0d0...` | ok |
| R13 | doc_libreoffice | rtf>odt | 14173 | `37e814a5347df31f...` | ok_parcial |
| R14 | doc_libreoffice | rtf>docx | 5293 | `d27ec6f9cccd3254...` | ok_parcial |
| R15 | doc_libreoffice | html>odt | 8124 | `a9e5f1e8cca8a894...` | ok_parcial |
| R16 | doc_libreoffice | txt>odt | 12117 | `b4ac1eb99de24b8f...` | ok_parcial |
| R17 | doc_libreoffice | odt>html | 2476 | `a9e64ee428e3c21e...` | ok |
| R18 | doc_libreoffice | docx>rtf | 8213 | `6625c6c16010f425...` | ok |
| R19 | doc_libreoffice | xlsx>pdf | 27403 | `f64f87300b34f817...` | ok |
| R20 | doc_libreoffice | xlsx>csv | 109 | `c19d31f488b5f0ba...` | ok |
| R21 | doc_libreoffice | xlsx>html | 2902 | `f33778451253dfcd...` | ok |
| R22 | doc_libreoffice | csv>pdf | 20944 | `b132482fcb42737c...` | ok |
| R23 | doc_libreoffice | pptx>pdf | 24534 | `1d0563debc28e3c0...` | ok |
| R24 | doc_libreoffice | pptx>odp | 32668 | `66b9abed8ef2ca05...` | ok_parcial |
| R26 | doc_pandoc | docx>epub | 5242 | `1623e11f68dd1349...` | ok_parcial |
| R27 | doc_pandoc | docx>html | 4487 | `f618673cac084894...` | ok |
| R28 | doc_pandoc | docx>md | 566 | `9b4bb779f5b8e7c6...` | ok |
| R29 | doc_pandoc | docx>pdf | 8159 | `26798c893e10c33e...` | aviso |
| R30 | doc_pandoc | docx>rtf | 1634 | `9045a7b88b8598c3...` | ok |
| R31 | doc_pandoc | epub>html | 4629 | `cf055a01032163a9...` | ok |
| R32 | doc_pandoc | epub>md | 585 | `b1d024c7b12e2b80...` | ok |
| R33 | doc_libreoffice | svg>pdf | 12500 | `3215aecdc5dd9d24...` | ok |
| R34 | doc_pandoc | html>docx | 10881 | `ce0948e13e8df149...` | ok_parcial |
| R35 | doc_pandoc | html>md | 568 | `54f71421a0895bbe...` | ok |
| R36 | doc_pandoc | md>docx | 10862 | `43a0ea34d2277f0b...` | ok_parcial |
| R37 | doc_pandoc | md>epub | 5275 | `15c4c3fa9bee2f24...` | ok_parcial |
| R38 | doc_pandoc | md>html | 4525 | `7d4c69233c6cce69...` | ok |
| R39 | doc_pandoc | md>odt | 7303 | `3abd88432272439c...` | ok_parcial |
| R40 | doc_pandoc | md>pdf | 10366 | `47cb6bb27bec7559...` | aviso |
| R41 | doc_pandoc | md>txt | 535 | `e936439bd27a42ce...` | ok |
| R42 | doc_pandoc | html>epub | 5284 | `90fdef118fb0e93b...` | ok_parcial |
| R43 | doc_pandoc | html>odt | 7285 | `0802feca25bae006...` | ok_parcial |
| R44 | doc_pandoc | html>rtf | 1756 | `a89e37f5d3731e7d...` | ok |
| R45 | doc_pandoc | docx>odt | 7202 | `2ec4cea3dbd828c7...` | ok_parcial |
| R46 | doc_pandoc | epub>docx | 10992 | `f64bd3764452cac4...` | ok_parcial |
| R47 | doc_pandoc | epub>txt | 566 | `9b4bb779f5b8e7c6...` | ok |
| R48 | doc_pandoc | rtf>md | 471 | `b7f1b3f7c07d3116...` | ok |
| R49 | doc_pandoc | rtf>html | 4324 | `d190a684c87c1faf...` | ok |
| R50 | doc_pandoc | md>rtf | 1700 | `a70efd2528eca365...` | ok |
| R51 | doc_pandoc | md>tex | 2748 | `2a2b2b9a26cd3095...` | ok |
| R52 | doc_pandoc | docx>tex | 2698 | `3669682677bcf4a7...` | ok |
| R53 | doc_pandoc | tex>docx | 10771 | `103af000b1ead37f...` | ok_parcial |
| R54 | doc_pandoc | tex>html | 4651 | `2196e8bd81dda130...` | ok |
| R55 | doc_pandoc | tex>pdf | 9754 | `f738858a6db44efa...` | aviso |
| R56 | doc_pandoc | pptx>md | 549 | `5e9b6868661ba5e3...` | ok |

Los `sha256` completos y el resto de campos (motivo del salto, hallazgos,
cobertura, censo de sobrantes) están en `resondeo55.json`.
