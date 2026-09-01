# MANIFIESTO — `bench/salidas-sdk-mcp/`

Informe: **`bench/sdk-mcp-capacidades.md`**.

**Todo son ficheros de texto** (`.py`, `.json`, `.log`, `.txt`); no hay binarios ni
`__pycache__/`.

## 0. Los tres venvs que hacen falta, y su estado

| Venv | `mcp==` | Rama | Estado en esta máquina |
|---|---|---|---|
| `.venv-mcp-sdk-18` | `1.8.1` | "18" | **BORRADO** (`CLAUDE.md` §2, limpieza del 31/08/2026) |
| `.venv-mcp-sdk-1x` | `1.29.0` | "129" / "1x" | **BORRADO** (ídem) |
| `.venv-mcp-sdk-2x` | `2.0.0` | "200" / "2x" | **BORRADO** (ídem) |

**No es evidencia irreproducible ni bloqueo**: `CLAUDE.md` §2 ya deja escrito que estos tres
"eran los arneses de informes MCP ya cerrados y se rehacen con un `pip install`". Se
reconstruyen con:

```bash
python -m venv .venv-mcp-sdk-18 && .venv-mcp-sdk-18/Scripts/pip install mcp==1.8.1
python -m venv .venv-mcp-sdk-1x && .venv-mcp-sdk-1x/Scripts/pip install mcp==1.29.0
python -m venv .venv-mcp-sdk-2x && .venv-mcp-sdk-2x/Scripts/pip install mcp==2.0.0
```

Esta pasada **no ha recreado los tres venvs** (no es una operación de un minuto: instala
tres SDKs completos con sus dependencias) — se documenta la orden exacta y se declara
**PENDIENTE de verificación** que `pip install mcp==1.8.1`/`1.29.0`/`2.0.0` sigan
resolviendo hoy exactamente esas versiones desde PyPI (paquetes ya publicados, así que en
principio estables, pero no reverificado en esta pasada).

## 1. Scripts (autónomos, cada uno documenta su propio uso en el docstring)

| Fichero | sha256 | bytes | Qué hace / cómo se invoca |
|---|---|---:|---|
| `srv_1x.py` | `ce6a82eef3a6ed61eb59530b955e0d3eddb9914e2cb62bb1c02c3753863e909a` | 10173 | Servidor mínimo, API lowlevel, ramas 1.8.1/1.29.0. No se ejecuta suelto: lo lanzan `cli_1x.py`/`interop.py` por stdio con `command=sys.executable` |
| `cli_1x.py` | `eb239e7a17d5066e6df92d8a5b3b52e578dd4281b866cb12f76839e4a634f998` | 7834 | `.venv-mcp-sdk-{18,1x}/Scripts/python.exe cli_1x.py [--roots R1;R2] [--roots-2 ...] --raices-servidor <ruta> [--slow N --slow-timeout M] --stderr <f> --out <f>` |
| `srv_2x.py` | `b115d2fb195158c1d822f035e156b6d763d4c940488910b996f0362bc27d755c` | 8182 | Servidor portado a `mcp 2.0.0` (handlers por constructor). Lanzado por `cli_2x.py`/`interop.py` |
| `cli_2x.py` | `5f9778dbbf98f415782b38d3236ab70df255a9aad3f845d307d5355c038aa314` | 6003 | `.venv-mcp-sdk-2x/Scripts/python.exe cli_2x.py [--roots ...] [--roots-2 ...] --raices-servidor <ruta> [--slow N] --modo auto\|legacy\|2026-07-28 --stderr <f> --out <f>` |
| `srv_2x_resolve.py` | `e0e392c9850cb261da21ec1dfa9d988f36d07b27e4f9a6a3570e74536a52e72a` | 2763 | Servidor 2.x con `MCPServer` + `Resolve(ListRoots)`. Lanzado por `cli_2x_resolve.py` |
| `cli_2x_resolve.py` | `99a12e6587ded57fcc511e0f0cb1d417ed4ab9c52bc684d67571a199da6820d6` | 3086 | `.venv-mcp-sdk-2x/Scripts/python.exe cli_2x_resolve.py --raices-servidor <ruta> --roots "R1;R2" --out <f>` — ejecuta internamente los dos modos `auto` y `legacy` en la misma corrida y escribe `stderr_2x_resolve_auto.txt`/`_legacy.txt` |
| `srv_tasks_129.py` | `9dde8e2587d02104aa7256b76f33d61c6456d6ce1209dd22757888016ea3cb47` | 2906 | Servidor con Tasks (SEP-1686), solo mcp 1.2x. Lanzado por `cli_tasks_129.py` |
| `cli_tasks_129.py` | `52307d775f65b4764ad89f6d060cfd1f55d419fe028c678c1b3491bc3738c049` | 5658 | `.venv-mcp-sdk-1x/Scripts/python.exe cli_tasks_129.py --dur 20 --timeout 8 --out r_tasks_129.json` (valores leídos del propio `r_tasks_129.json`: `dur=20.0`, `timeout_cliente_s=8.0`) |
| `prueba_progreso.py` | `f447817a5df7158342282952552acc6352842e283fc0d74ba49d597d4b7b5c4f` | 3797 | `.venv-mcp-sdk-2x/Scripts/python.exe prueba_progreso.py --modo auto --out r_progreso_2x_auto.json` (usa los valores por defecto `--dur 30 --timeout-largo 45 --timeout-corto 10`, confirmado contra el JSON) |
| `prueba_imagecontent.py` | `8c627bbc2abf4fcb44c462988487ae551010a0a813e474404d810f60b2b16940` | 2693 | Corre en cualquiera de las 3 ramas: `<venv>/Scripts/python.exe prueba_imagecontent.py <salida.json>` |
| `interop.py` | `6a8fae566605dfd40b3a9a3b7308d735942017b6478b4973aad611e5287d844d` | 3684 | `<venv-CLIENTE>/Scripts/python.exe interop.py --server-python <venv-SERVIDOR>/Scripts/python.exe --server-script srv_1x.py\|srv_2x.py --etiqueta cli<X>_srv<Y> --out interop_cli<X>_srv<Y>.json` |
| `sondear_wheels.py` | `40a4e6d0f45e6f3c8b2f646037328bd3e0618d5948e5ece463d9925823e1a898` | 1406 | `python sondear_wheels.py 1.8.1 1.9.0 1.9.4 1.21.0 1.23.0 1.29.0 2.0.0` — descarga con `pip download --no-deps` e inspecciona el `.whl` como ZIP, **no instala nada** y no depende de ningún venv concreto |

## 2. Datos crudos de las ramas sueltas (§2/§3/§4 del informe)

| Fichero | sha256 | bytes | Orden exacta (argv tomado del propio JSON cuando existe) |
|---|---|---:|---|
| `r_181_sin_roots.json` | `12eff3a342e4e836d781a904fe8844ba343f5e2e3094b76819cca0d76391abd8` | 3579 | `.venv-mcp-sdk-18/Scripts/python.exe cli_1x.py --raices-servidor <RAIZ>/raiz_srv --stderr stderr_181_sin_roots.txt --out r_181_sin_roots.json` |
| `r_181_slow.json` | `d196099a11dfa80e441fae30f12745d104f4d2463bd09f2bf30e0acb94ad96a2` | 4759 | `.venv-mcp-sdk-18/Scripts/python.exe cli_1x.py --raices-servidor <RAIZ>/raiz_srv --slow 12 --slow-timeout 20 --stderr stderr_181_slow.txt --out r_181_slow.json` |
| `r_129_con_roots.json` | `41831644543d4b9a5f35a0465ee3edba0823dcce71dcea81012d0e7a6eb87fab` | 5217 | `.venv-mcp-sdk-1x/Scripts/python.exe cli_1x.py --raices-servidor <RAIZ>/raiz_srv --roots "<RAIZ>/raiz_srv/sub;<RAIZ>/raiz_fuera" --roots-2 "<RAIZ>/raiz_srv" --stderr stderr_129_con_roots.txt --out r_129_con_roots.json` |
| `r_129_sin_roots.json` | `0fdedc8099867fddae3f8af76a5b0cd39e4a302fdf8eaaaaf9908142073b0a85` | 3663 | `.venv-mcp-sdk-1x/Scripts/python.exe cli_1x.py --raices-servidor <RAIZ>/raiz_srv --stderr stderr_129_sin_roots.txt --out r_129_sin_roots.json` |
| `r_129_slow.json` | `f394f25a20e9b89b83045cb4ee599f9999308c937c99be8f549a6ddc2607f48b` | 15486 | `.venv-mcp-sdk-1x/Scripts/python.exe cli_1x.py --raices-servidor <RAIZ>/raiz_srv --roots "<RAIZ>/raiz_srv" --slow 60 --slow-timeout 90 --stderr stderr_129_slow.txt --out r_129_slow.json` |
| `r_200_con_roots.json` | `eaa7a6d47f1c7857567df2af394340a5cea0ffdce5c970a9b7d5d457f2cd1556` | 6081 | `.venv-mcp-sdk-2x/Scripts/python.exe cli_2x.py --raices-servidor <RAIZ>/raiz_srv --roots "<RAIZ>/raiz_srv/sub;<RAIZ>/raiz_fuera" --roots-2 "<RAIZ>/raiz_srv" --slow 5 --stderr stderr_200_con_roots.txt --out r_200_con_roots.json` (modo por defecto `auto`) |
| `r_200_legacy.json` | `c80f70ca4d4a8990f2832a3cc4d9f2995dcd59d8ff6e02498a3d4cd9ee4d2dd2` | 6843 | igual que la anterior con `--modo legacy` añadido, `--out r_200_legacy.json` |
| `r_2x_resolve.json` | `ed8b52458bd65575e6e812543b3dfcd9107f558b3e4230b2b4db5f449a4d726a` | 3228 | `.venv-mcp-sdk-2x/Scripts/python.exe cli_2x_resolve.py --raices-servidor <RAIZ>/raiz_srv --roots "<RAIZ>/raiz_srv/sub;<RAIZ>/raiz_fuera" --out r_2x_resolve.json` (2 roots del lado cliente, deducido del contenido: `"cliente": [".../sub", ".../raiz_fuera"]`) |
| `r_2x_resolve_sin_roots.json` | `049b88eb9ff272a4b18682674a4dde4ece2156b3ffb3a50b785cbe2f2f22fa3c` | 2035 | igual, con `--roots ""` (sin declarar capacidad roots) — confirmado por el contenido: `MCPError(-32021, "Client did not declare the roots capability...")`, `--out r_2x_resolve_sin_roots.json` |
| `r_2x_resolve_warn.json` | `d3184957b3d428477e43050a378ed9fd4c05afa4dc18a19610a283a059bdf15d` | 2878 | **No citado en `bench/sdk-mcp-capacidades.md`.** Mismo arnés que `r_2x_resolve.json` pero con **un solo root** declarado del lado cliente (`--roots "<RAIZ>/raiz_srv/sub"`, sin `raiz_fuera` — verificado comparando los dos JSON campo a campo). Parece una corrida anterior a que el experimento añadiera el segundo root, conservada sin editar. No se borra (no es basura de `__pycache__`) pero se deja constancia de que **no respalda ninguna cifra publicada en el informe actual** |
| `r_imagecontent_.venv-mcp-sdk-18.json` | `02e1cd0b9a211a3fa76939096c17aa7552343cefd6109127b3dfc09318a8516b` | 3241 | `.venv-mcp-sdk-18/Scripts/python.exe prueba_imagecontent.py r_imagecontent_.venv-mcp-sdk-18.json` |
| `r_imagecontent_.venv-mcp-sdk-1x.json` | `f2cd1af616390468562ef148ae0d573d9c8445db75f9a715a597f47615f3e132` | 3242 | `.venv-mcp-sdk-1x/Scripts/python.exe prueba_imagecontent.py r_imagecontent_.venv-mcp-sdk-1x.json` |
| `r_imagecontent_.venv-mcp-sdk-2x.json` | `c995033e26b0f030b1e35320240a0f12ee5d668cbaff27cec9114c7fc302b95b` | 3242 | `.venv-mcp-sdk-2x/Scripts/python.exe prueba_imagecontent.py r_imagecontent_.venv-mcp-sdk-2x.json` |
| `r_progreso_2x_auto.json` | `f5526ccfc892271f404e986c607dd9eab9915ccc4c1212ab79454addbeff4888` | 1990 | `.venv-mcp-sdk-2x/Scripts/python.exe prueba_progreso.py --modo auto --out r_progreso_2x_auto.json` |
| `r_tasks_129.json` | `a75601051266a366641ed91e5810328b2c7653dba63f5bed7e3782a45c3baba9` | 2268 | `.venv-mcp-sdk-1x/Scripts/python.exe cli_tasks_129.py --dur 20 --timeout 8 --out r_tasks_129.json` |
| `stderr_181_sin_roots.txt` … `stderr_tasks_129.txt` (17 ficheros) | ver árbol | ver árbol | `stderr` del servidor correspondiente, capturado por la orden que genera su `.json` hermano vía `--stderr <f>` (o el nombre fijo que cada script deriva de su propio argumento, p. ej. `stderr_2x_resolve_{auto,legacy}.txt`, `stderr_tasks_129.txt`, `stderr_progreso_auto.txt`) |

## 3. La matriz de interoperabilidad (§1.4), 9 celdas

Mapeo verificado leyendo el campo `server_script`/`rama_cliente` de cada JSON: el sufijo
`18`/`129` del lado servidor siempre corresponde a `srv_1x.py` (API lowlevel, compatible con
`1.8.1` y `1.29.0`) y el sufijo `200` a `srv_2x.py`.

| `cliente_venv` | `servidor_venv` | `--server-script` | Fichero |
|---|---|---|---|
| `.venv-mcp-sdk-18` | `.venv-mcp-sdk-18` | `srv_1x.py` | `interop_cli18_srv18.json` |
| `.venv-mcp-sdk-18` | `.venv-mcp-sdk-1x` | `srv_1x.py` | `interop_cli18_srv129.json` |
| `.venv-mcp-sdk-18` | `.venv-mcp-sdk-2x` | `srv_2x.py` | `interop_cli18_srv200.json` |
| `.venv-mcp-sdk-1x` | `.venv-mcp-sdk-18` | `srv_1x.py` | `interop_cli129_srv18.json` |
| `.venv-mcp-sdk-1x` | `.venv-mcp-sdk-1x` | `srv_1x.py` | `interop_cli129_srv129.json` |
| `.venv-mcp-sdk-1x` | `.venv-mcp-sdk-2x` | `srv_2x.py` | `interop_cli129_srv200.json` |
| `.venv-mcp-sdk-2x` | `.venv-mcp-sdk-18` | `srv_1x.py` | `interop_cli200_srv18.json` |
| `.venv-mcp-sdk-2x` | `.venv-mcp-sdk-1x` | `srv_1x.py` | `interop_cli200_srv129.json` |
| `.venv-mcp-sdk-2x` | `.venv-mcp-sdk-2x` | `srv_2x.py` | `interop_cli200_srv200.json` |

Orden general para regenerar cualquier celda:

```bash
<CLIENTE>/Scripts/python.exe interop.py \
  --server-python <SERVIDOR>/Scripts/python.exe \
  --server-script <srv_1x.py|srv_2x.py> \
  --etiqueta cli<X>_srv<Y> \
  --out interop_cli<X>_srv<Y>.json
```

(el `stderr` de cada celda, cuando existe como fichero separado — `stderr_interop_cli*_srv*.txt`
— lo escribe el propio proceso servidor lanzado por `interop.py`).

| Fichero | sha256 | bytes |
|---|---|---:|
| `interop_cli129_srv129.json` | `89c6139abffbe3edc1b955e29a2edce80178d2401e422d0c19de95630dffd846` | 439 |
| `interop_cli129_srv18.json` | `45316fc062c09f81a0fec7e147bb66c391445f56a3b798dd8625529b50d74452` | 438 |
| `interop_cli129_srv200.json` | `4c0c14212cd47c671a1d9bdb52e6070ed7b4b11d100543ffaae2def3a4619c7b` | 439 |
| `interop_cli18_srv129.json` | `ee96ded4a0093a7fa4b538c3084078d15e2af830b702d01c861dc867b654382c` | 375 |
| `interop_cli18_srv18.json` | `e383cc5990fc7c7ffa2a3eb7999e8194ee7c22a6b934ebc6be2300899d17800b` | 374 |
| `interop_cli18_srv200.json` | `593d7799e8998f27e32c2bc8c729ab1a138ea7fc86f789e2e7a6df46cd31ff56` | 375 |
| `interop_cli200_srv129.json` | `f32e43a3744359c72087d61d2043565b674803e2976721537d247e77171c56ca` | 465 |
| `interop_cli200_srv18.json` | `f0dcd6d6f060afc100e59879ca2437f3497e183d26dd3774dd375494c2d02a83` | 319 |
| `interop_cli200_srv200.json` | `ab9b494ca1b983f8f0dd6d8ab843dd022f2f21ed7a717ae316a374b8a7285541` | 441 |
| `stderr_interop_cli129_srv129.txt` | `1ed8b89d192ddd454eb79eb719a4a5c3392800eb64ef79c6584dfbc9d6336d6c` | 215 |
| `stderr_interop_cli129_srv18.txt` | `c34c0aa25a9996103ffe950a7394fa4aac716509e8d2509253e043e6ad3b4553` | 215 |
| `stderr_interop_cli129_srv200.txt` | `abc505da97eb4afc75272217211fe757ec7ef97dcf6c23e12243d782ad01a597` | 323 |
| `stderr_interop_cli18_srv129.txt` | `e085f4a175bf64c12321c5a4cf1f8d43708db2ce465286734c10cba42393b9c4` | 215 |
| `stderr_interop_cli18_srv18.txt` | `683b595e0a297d46f3a53deaa519b03a06ddbb20ecd2023d8d3b1de787926142` | 215 |
| `stderr_interop_cli18_srv200.txt` | `3d1eeee83b2122a02d84ddcbc62d8c19dd7a1f84a3a175b1643ff0948db23d07` | 323 |
| `stderr_interop_cli200_srv129.txt` | `29940a7292a53bcec69cc3111ffd1a707323206c453cb888991712aa33129db3` | 7008 |
| `stderr_interop_cli200_srv18.txt` | `1f9ca00a281011a6b75c1c093aa5e77d335cd6d1fc14144cf182a4d13a15b4dc` | 9873 |
| `stderr_interop_cli200_srv200.txt` | `039fccf2ffe6eb030b3f7d780062e5f82b02e58d2e3bd556f54081ff1f9d32dd` | 323 |

## 4. Instalación de los venvs

| Fichero | sha256 | bytes | Orden que lo reproduce |
|---|---|---:|---|
| `pip_18.log` | `4000303b8864a96d1f16eb8f9a706187c8361ad6d10009643c1622fafd6adcd0` | 173 | `.venv-mcp-sdk-18/Scripts/pip install mcp==1.8.1` (stdout/stderr redirigido) |
| `pip_1x.log` | `6d505127ce8d6287d9064f3ccb65ccf5f6c93f5dca06716563b810f03823797d` | 173 | `.venv-mcp-sdk-1x/Scripts/pip install mcp==1.29.0` |
| `pip_2x.log` | `74549f5ac2baf3917600a1fd0567774b0f1d46db52ecd6599084533b17c96b47` | 173 | `.venv-mcp-sdk-2x/Scripts/pip install mcp==2.0.0` |

## 5. Resto de `stderr_*.txt` sueltos de las ramas 1.x/2.x

| Fichero | sha256 | bytes |
|---|---|---:|
| `stderr_129_con_roots.txt` | `970c775a306159e95585a8bcbb61a45b4aff48bbcf0b26227815dd42be68541e` | 763 |
| `stderr_129_sin_roots.txt` | `becd9384e1a0abcbad700e41dcacdfddacf586d64b250a23384e2cb5283c7063` | 442 |
| `stderr_129_slow.txt` | `ff9ac51d3efbcc0916f53931c0eeb8eb9e8177aa57ddeaeb437dc6ad0d2cd762` | 461 |
| `stderr_181_sin_roots.txt` | `c172c221c0cedd31262260b9845f8e1a900f20c4b3ab73a75f39c4e4172dc5c2` | 442 |
| `stderr_181_slow.txt` | `758fec72812bce95aabb9b2d8515c97f9079c41acc65dc78f76d26e283823204` | 546 |
| `stderr_200_con_roots.txt` | `f503c8469e3cc41e16b7ad9a216e0b1fd415d413b6c61bfd9e4916946aba1a12` | 1572 |
| `stderr_200_legacy.txt` | `5083510374d42ff4782e2fd5706fd78e262f96fc58aa2b842dbfc48014ef43db` | 1206 |
| `stderr_2x_resolve_auto.txt` | `3b2d3e2cb67db4b118b3230af5fa9fab39870bb15a2af43fa987bcaf8cd42859` | 435 |
| `stderr_2x_resolve_legacy.txt` | `846fd58da503694c67d54fbd2a4949ba59672b0c0b710ec9c491ced3ffcd6207` | 309 |
| `stderr_progreso_auto.txt` | `c55ec3501038fe5eeed87c8ef8c792a1a35d17fee287fa499a4f3a80e2fc55ac` | 788 |
| `stderr_tasks_129.txt` | `0c6e54a61240b6beba9a7c278805c3e1c8990680a4743ce2c6c49ccac9b27781` | 963 |

## 6. Lo que queda PENDIENTE

1. **Los tres venvs SDK no se han recreado en esta pasada** (§0) — orden documentada, no
   ejecutada, por el coste de instalar tres SDKs completos solo para un manifiesto de
   trazabilidad.
2. **`r_2x_resolve_warn.json` no está citado en el informe** y parece una corrida anterior
   con un solo root del lado cliente (§2). No se ha podido confirmar la orden exacta más
   allá de lo que el propio contenido permite deducir por comparación.
