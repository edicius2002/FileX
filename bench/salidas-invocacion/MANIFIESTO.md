# MANIFIESTO — `bench/salidas-invocacion/` (agente P2)

Generado por `_p2_manifiesto.py` el 21/08/2026 12:25.

Informe: **`bench/invocacion-aristas.md`**.

**Total en disco: 1 078 668 B en 111 ficheros.**


## 1. Lo que se borró por regenerable

| Qué | Ficheros | Bytes | Orden que lo reproduce |
|---|---:|---:|---|
| `pool/` | 112 | 225 069 057 | `python _p2_semillas.py` / `_p2_semi_in2.py` / `_p2_crudos.py` |
| `tmp_vbn/` | 8 | 47 861 321 | los directorios de trabajo se recrean solos en cada script |
| `tmp_res2/` | 1 | 36 345 465 | los directorios de trabajo se recrean solos en cada script |
| `tmp_dens/` | 21 | 30 000 000 | los directorios de trabajo se recrean solos en cada script |
| `c13/ (binarios)` | 40 | 27 000 000 | `docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh` |
| `aristas.json` | 1 | 5 759 520 | python _p2_censo.py   (5,8 MB, BORRADO) |
| `tmp_c17/` | 62 | 4 267 160 | los directorios de trabajo se recrean solos en cada script |
| `marco.json` | 1 | 899 446 | python _p2_agrega.py   (0,9 MB, BORRADO) |
| `sem_c17/` | 25 | 613 512 | `python _p2_c17.py` y `_p2_c17b.py` |
| `pool3/` | 24 | 394 403 | `python _p2_semillas.py` / `_p2_semi_in2.py` / `_p2_crudos.py` |
| `tmp_res/` | 1 | 370 070 | los directorios de trabajo se recrean solos en cada script |
| `tmp_val2/` | 3 | 304 128 | los directorios de trabajo se recrean solos en cada script |
| `__pycache__/` | 5 | 278 958 |  |
| `pool2/` | 17 | 185 266 | `python _p2_semillas.py` / `_p2_semi_in2.py` / `_p2_crudos.py` |
| `tmp_val/` | 1 | 127 137 | los directorios de trabajo se recrean solos en cada script |
| `tmp_crudos/` | 33 | 33 343 | los directorios de trabajo se recrean solos en cada script |
| `tmp_in2/` | 2 | 5 577 | los directorios de trabajo se recrean solos en cada script |
| `tmp_out2/` | 1 | 260 | los directorios de trabajo se recrean solos en cada script |

## 2. Lo que queda

| Fichero | Bytes | sha256 | Orden que lo reproduce |
|---|---:|---|---|
| ~~`Dockerfile.c13`~~ | 367 | `268e4f2c2f95676a…` | **TRASLADADO a `docker/Dockerfile.c13`** el 04/09/2026 |
| `_extrae.py` | 3 570 | `63ee5b94c6f8b032…` | — |
| `_p2_agrega.py` | 3 929 | `d1ee03b2404c5f52…` | — |
| `_p2_c17.py` | 10 716 | `100f6d4b25c6880d…` | — |
| `_p2_c17b.py` | 4 090 | `272cd87fdcd9f0ec…` | — |
| `_p2_censo.py` | 10 534 | `9ad99e050550aec7…` | — |
| `_p2_crudos.py` | 10 004 | `e5f7c2311c8eb31f…` | — |
| `_p2_crudos2.py` | 3 048 | `dd3f08b3bdd59971…` | — |
| `_p2_densidad.py` | 4 780 | `c3702847d878b074…` | — |
| `_p2_desglose.py` | 2 692 | `6b589d9c511cd764…` | — |
| `_p2_final.py` | 11 918 | `4be0701f7a78e86b…` | — |
| `_p2_lib.py` | 17 127 | `91ca20b589a10038…` | — |
| `_p2_manifiesto.py` | 8 207 | `9ab52f15cf4f2fb9…` | — |
| `_p2_resid.py` | 7 130 | `9931c25087d4cf06…` | — |
| `_p2_resid2.py` | 7 304 | `b24446a526b7034c…` | — |
| `_p2_resumen.py` | 4 688 | `819ab2dcf80a729a…` | — |
| `_p2_semi_in.py` | 5 541 | `52b5c4b39b8a3f54…` | — |
| `_p2_semi_in2.py` | 6 525 | `82b648d4610af321…` | — |
| `_p2_semi_out.py` | 4 767 | `7f0e6f693097a408…` | — |
| `_p2_semi_out2.py` | 7 187 | `e4f77ae476800392…` | — |
| `_p2_semillas.py` | 6 601 | `5eb960fba96d9e72…` | — |
| `_p2_testigo.py` | 1 773 | `ac04ec1e2a735c89…` | — |
| `_p2_valida.py` | 3 788 | `271421d933af5159…` | — |
| `agregado.json` | 127 | `ac1c76605dac1923…` | python _p2_agrega.py |
| `c13/c13_dentro.sh` | 2 032 | `ac41fd432cb94a9b…` | — |
| `c13/c13_ocr.sh` | 1 053 | `abe69dc35f150ec5…` | — |
| `c13/out/chk.txt` | 195 | `cb4299243e75b655…` | — |
| `c13/out/escaneado_d1.txt` | 84 | `f5593ee44bf2ab81…` | — |
| `c13/out/escaneado_d2.txt` | 84 | `f5593ee44bf2ab81…` | — |
| `c13/out/escaneado_d3.txt` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/escaneado_d4.txt` | 135 | `82aa5b473c4d7fe8…` | — |
| `c13/out/gs_raster_escaneado_d1.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/gs_raster_escaneado_d2.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/gs_raster_escaneado_d3.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/gs_raster_escaneado_d4.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/gs_raster_patologico_escaneado.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/j.json` | 4 333 | `53e3b52f7651ffd4…` | — |
| `c13/out/patologico_escaneado.txt` | 83 | `b7c05f48189224b7…` | — |
| `c13/out/qpdf_check.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_decrypt.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_encrypt.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_json.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_linearize.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_merge.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/qpdf_split.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_pdf_escaneado_d1.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_pdf_escaneado_d2.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_pdf_escaneado_d3.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_pdf_escaneado_d4.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_pdf_patologico_escaneado.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_txt_escaneado_d1.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_txt_escaneado_d2.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_txt_escaneado_d3.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_txt_escaneado_d4.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out/tess_txt_patologico_escaneado.log` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out2/escaneado_d1.txt` | 84 | `f5593ee44bf2ab81…` | — |
| `c13/out2/escaneado_d2.txt` | 90 | `515748f3d82858c5…` | — |
| `c13/out2/escaneado_d3.txt` | 0 | `e3b0c44298fc1c14…` | — |
| `c13/out2/escaneado_d4.txt` | 372 | `605778d46db4ade7…` | — |
| `c13/out2/patologico_escaneado.txt` | 83 | `b7c05f48189224b7…` | — |
| `c13/res.tsv` | 700 | `003289d7a9d0ca57…` | docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh |
| `c13/res_ocr.tsv` | 139 | `2436d9f4b6a9303d…` | docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_ocr.sh |
| `c13_cer.json` | 295 | `2d18fe379e540e5c…` | ver log-p2-c13-cer.txt (script en linea) |
| `c13_dentro.sh` | 2 032 | `ac41fd432cb94a9b…` | — |
| `c13_ocr.sh` | 1 053 | `abe69dc35f150ec5…` | — |
| `c17.json` | 21 777 | `ec6f1a3852ec2c4f…` | python _p2_c17.py |
| `c17b.json` | 2 980 | `f67c10bddcd1561e…` | python _p2_c17b.py |
| `cache_muxers.json` | 23 042 | `3c5a85f4968aa316…` | se regenera solo la primera vez que se usa _p2_lib.muxer_de |
| `censo.json` | 4 065 | `66542fc43c1b5869…` | python _p2_censo.py |
| `crudos_ideal.json` | 947 | `9cb06b7a233ef1d0…` | python _p2_crudos2.py |
| `crudos_p2.json` | 22 765 | `9f9aeb4c4dced947…` | python _p2_crudos.py |
| `densidad_p2.json` | 8 920 | `102f16ed8022aff6…` | python _p2_semillas.py && python _p2_densidad.py |
| `final_p2.json` | 899 | `d1bf7a3ad0b83896…` | python _p2_final.py |
| `inventario_e1.json` | 81 827 | `0a342e6785c51a3d…` | python _extrae.py |
| `log-extrae.txt` | 6 374 | `6082c6030628ddc9…` | — |
| `log-p2-agrega.txt` | 386 | `346f2f3ca33575a7…` | — |
| `log-p2-c13-cer.txt` | 569 | `c0eb41bb7aff9ddd…` | — |
| `log-p2-c13-ocr.txt` | 224 | `5b6c4ea3ae0c3aea…` | — |
| `log-p2-c13.txt` | 1 253 | `ea42087f6b103f29…` | — |
| `log-p2-c17.txt` | 3 552 | `7a0d121e5616e957…` | — |
| `log-p2-c17b.txt` | 967 | `9aff7695bc305370…` | — |
| `log-p2-censo.txt` | 493 | `e97ce5b2f5a3801e…` | — |
| `log-p2-crudos.txt` | 2 261 | `9f33e2f75d108e9b…` | — |
| `log-p2-crudos2.txt` | 387 | `ef37e1fbd07b8c4d…` | — |
| `log-p2-densidad.txt` | 961 | `6498e5dba6253aa6…` | — |
| `log-p2-desglose.txt` | 819 | `3e21187bde8fbbda…` | — |
| `log-p2-final.txt` | 997 | `59d0883af0987886…` | — |
| `log-p2-resid.txt` | 871 | `5201dc68d9b24a95…` | — |
| `log-p2-resid2.txt` | 1 580 | `24820b716693b333…` | — |
| `log-p2-resumen.txt` | 6 220 | `6d1c59861a462c85…` | — |
| `log-p2-semi-in.txt` | 2 328 | `bbfe926e9f497f75…` | — |
| `log-p2-semi-in2.txt` | 1 437 | `1d5ac59ad5714e84…` | — |
| `log-p2-semi-out.txt` | 3 356 | `8b33183a57ae7070…` | — |
| `log-p2-semi-out2.txt` | 2 033 | `e4ab2e159ea5b2fe…` | — |
| `log-p2-semillas.txt` | 142 | `d05e3df1757fcd8a…` | — |
| `log-p2-valida.txt` | 2 810 | `7784dc3e3bb0b036…` | — |
| `log-p2-valida2.txt` | 966 | `33ff812375901ed9…` | — |
| `log-p2-valida3.txt` | 1 196 | `1b7691b84841873f…` | — |
| `ocr_eval_p2.py` | 2 453 | `5b5bce72dea7d3e4…` | — |
| `pool_indice.json` | 20 187 | `d41cd69c310c2c60…` | python _p2_semillas.py   (regenera pool/, 225 MB, BORRADO) |
| `resid_p2.json` | 171 642 | `65395c786f8c23b2…` | python _p2_resid.py |
| `resid_p2b.json` | 197 288 | `2bf56977d481d8bf…` | python _p2_resid2.py |
| `resumen_p2.json` | 9 394 | `e62b437b4f506aa2…` | python _p2_resumen.py |
| `semi_in_p2.json` | 26 313 | `98073c69d22c050b…` | python _p2_semi_in.py |
| `semi_in_p2b.json` | 10 154 | `f01b67041175a6f0…` | python _p2_semi_in2.py |
| `semi_out_p2.json` | 69 904 | `c7d6a73dee77efdf…` | python _p2_semi_out.py |
| `semi_out_p2b.json` | 24 315 | `faed71888f230d3e…` | python _p2_semi_out2.py |
| `testigo.jsonl` | 408 | `c41b5ef85f1162de…` | python _p2_testigo.py <etiqueta> |
| `validacion_p2.json` | 8 806 | `4b4f2e9379da49d6…` | python _p2_valida.py |
| `validacion_p2_extra.json` | 1 316 | `b4a220db611aa683…` | ver log-p2-valida2.txt (script en linea) |
| `verificador_p2.py` | 167 824 | `cb3e479b6a75dddf…` | copia congelada de bench/scripts/verificador.py (P3 lo edita en paralelo) |

> **`Dockerfile.c13` ya no está en este directorio.** El 04/09/2026 se trasladó a
> **`docker/Dockerfile.c13`**, donde un tercero lo encuentra, y allí quedó fijado por
> digest en vez de por `:latest` (informe `bench/contenedor-publicable.md`). Lo que se
> midió aquí el 21/08/2026 fueron **367 B**,
> `sha256:268e4f2c2f95676ac8a225d65d5bf85b0f7cdb38f29bc83f65350a1918ebbe66`, con
> `FROM ghcr.io/c4illin/convertx:latest`; el contenido de hoy es distinto y el histórico
> vive en git. Los informes de bench anteriores a esa fecha lo citan por su ruta vieja.

## 3. Orden de ejecución completo

```
python _p2_censo.py            # reproduce las 138 501 aristas de E1
python _p2_agrega.py           # reproduce 40 252 / 22 235 / 75 874 / 140
python _extrae.py              # inventario de los fallos de E1
python _p2_semillas.py         # reconstruye el pool (225 MB)
python _p2_semi_in.py          # semiaristas de entrada, 1a vuelta
python _p2_semi_in2.py         # 2a vuelta con semilla del motor lector
python _p2_crudos.py           # los 20 crudos, con fidelidad RMSE
python _p2_crudos2.py          # referencia ideal degradada
python _p2_semi_out.py         # semiaristas de salida, 1a vuelta
python _p2_semi_out2.py        # 2a vuelta con perfiles de codec
python _p2_resid.py            # las 118 nominales de la muestra
python _p2_resid2.py           # 2a vuelta con las reglas U, C2 y R2
python _p2_valida.py           # control antifalso positivo
python _p2_c17.py              # censo de gs y gotenberg
python _p2_c17b.py             # 2a vuelta de semillas de LibreOffice
docker build --platform linux/amd64 \
    -f docker/Dockerfile.c13 -t filex-c13 docker/   # trasladado 04/09
docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_dentro.sh
docker run --rm --entrypoint sh -v <SAL>/c13:/w filex-c13 /w/c13_ocr.sh
python _p2_final.py            # LA CIFRA
python _p2_resumen.py          # resumen consolidado
python _p2_manifiesto.py       # este fichero
```
