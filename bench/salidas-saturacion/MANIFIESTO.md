# MANIFIESTO — `bench/salidas-saturacion/`

Informe: **`bench/saturacion-herramientas.md`** (agente C3, 21/08/2026, Claude Code 2.1.238).

**Todo son ficheros de texto** (`.py`, `.json`, `.jsonl`, `.log`, `.txt`, `.md`); no hay
binarios ni `__pycache__/` en el árbol.

## 1. Cómo se generó, tal como lo documenta el propio informe (§9)

```bash
# catálogos: ya extraídos de bench/salidas-mcp-refs/multimedia/cat_vam.json y cat_lite.json,
# sin reescribir una coma (§1.3) — no hay orden de "generación" propia, son un recorte

# lo medible SIN modelo (determinista, sin LLM, ~1 s)
python bench/salidas-saturacion/estatico.py

# el grid conductual (requiere `claude` autenticado; ~2 h las 540 ejecuciones)
python bench/salidas-saturacion/correr.py --modelo haiku  --reps 10 --hilos 5 --salida grid_haiku.jsonl
python bench/salidas-saturacion/correr.py --modelo sonnet --reps 5  --hilos 4 --salida grid_sonnet.jsonl

# puntuación y tablas
python bench/salidas-saturacion/puntuar.py grid_haiku.jsonl
python bench/salidas-saturacion/puntuar.py grid_sonnet.jsonl
python bench/salidas-saturacion/tablas.py  grid_haiku_puntuado.jsonl  "Haiku 4.5"
python bench/salidas-saturacion/tablas.py  grid_sonnet_puntuado.jsonl "Sonnet"
```

`correr.py` invoca `claude -p` como sujeto (una vez por petición, proceso nuevo, `--tools ""`,
`--strict-mcp-config --mcp-config <catálogo>`, ver §1.2) contra `bench/salidas-saturacion/stub_mcp.py`,
un servidor MCP stdio que sirve el catálogo capturado y registra las llamadas sin ejecutar
`ffmpeg` de verdad (§1.3). **No usa `ANTHROPIC_API_KEY` ni ninguna clave de inferencia**: el
propio informe (§0, §1.1) documenta que en la máquina de medición **no había ninguna clave
de API**, y que el experimento se diseñó alrededor de esa ausencia usando `claude -p` como
sujeto en vez de una llamada directa a la API.

## 2. Verificación intentada en esta máquina (worker2, WSL2, 01/09/2026)

- `python bench/salidas-saturacion/estatico.py` **es reproducible sin más**: es determinista,
  sin LLM, y no toca la red. **No se ha vuelto a ejecutar en esta pasada** porque el objetivo
  del encargo es el manifiesto de trazabilidad, no reverificar el hallazgo — pero no hay
  ningún bloqueo que declarar para este script en concreto.
- **El grid conductual (`correr.py`, 540 ejecuciones, ~2 horas) NO se ha relanzado.** No es
  por falta de clave: `claude` **sí está disponible en este entorno** (`2.1.252`, comprobado),
  distinta de la `2.1.238` con la que se midió el informe. La razón para NO ejecutarlo es de
  alcance y coste: son 540 invocaciones reales de `claude -p` (facturables/con cuota, ~2 h),
  y el encargo pide un manifiesto de trazabilidad, no repetir un experimento de 2 horas con
  llamadas a un modelo. **Se declara PENDIENTE de reejecución**, no bloqueado por entorno.

## 3. Aviso de EVIDENCIA POSIBLEMENTE IRREPRODUCIBLE (no declarada por este agente en `ci/evidencia-irreproducible.txt`)

`grid_haiku.jsonl` y `grid_sonnet.jsonl` son la salida de invocar los alias de modelo
`haiku` y `sonnet` de Claude Code **en una versión concreta de la CLI (2.1.238) y en una
fecha concreta (21/08/2026)**. Un alias de modelo no fija una versión de pesos: si Anthropic
actualiza a qué checkpoint apunta `haiku`/`sonnet`, o si una versión más nueva de Claude Code
cambia el comportamiento de `--tools ""` o de la inyección del catálogo MCP, **relanzar
`correr.py` hoy no reproduciría estos JSONL byte a byte, y podría no reproducir ni siquiera
el patrón de elección que el informe mide** (que 27 herramientas acierte más que 8). Esto
tiene la misma forma que la evidencia forense declarada en `ci/evidencia-irreproducible.txt`
para `bench/salidas-competidores/` (contenedores de terceros que cambian de versión): aquí
el "contenedor de terceros" es el propio modelo detrás del alias. **Se deja constancia aquí
y se avisa en el reporte de esta tarea; no se edita `ci/evidencia-irreproducible.txt`**
—lo centraliza el agente que gestiona `ci/heredado.json`— para que se evalúe si corresponde
añadir esta entrada con su motivo.

## 4. Ficheros

| Fichero | sha256 | bytes | Orden que lo reproduce |
|---|---|---:|---|
| `_ensamblar.py` | `9c38161269a73bf67e0a1a130e04ad1d22c98c0569f3e9b4cb1216436047f643` | 1070 | ensambla `bench/saturacion-herramientas.md` a partir de las secciones `_seccion*.md` — script de redacción, no de medición |
| `_seccion3.md` | `1d73997867390a34cd54fdb864905c36c69d5aebb2136da5e51cf8155aad25d6` | 7369 | fuente del informe, sección 3 |
| `_seccion678.md` | `e4597f2134ded707f08de1a31c058bffb89fd8afb14e4bd3091b80e659552139` | 3337 | fuente del informe, secciones 6–8 |
| `_seccion7.md` | `be83d644fbc4da52a90d05e3c0222ff26136fc1c548f40453dfe94db3de6f1e3` | 5255 | fuente del informe, sección 7 |
| `_seccion8.md` | `ffda90376927fd4e36866ee6c613c4e3936c7004125f155fe3badd9ba1b6c269` | 2855 | fuente del informe, sección 8 |
| `catalogo_A_vam27.json` | `b188f8011cd7dadeac980099cafbaa3319ee8c1ea5821f5371bd3a678f0228e0` | 38700 | recorte de `bench/salidas-mcp-refs/multimedia/cat_vam.json` (27 herramientas), sin reescribir |
| `catalogo_B_lite8.json` | `f189006375b9612c4f78262b4b0c9034116b725b6b39c5662929200a8c99f434` | 11347 | recorte de `.../cat_lite.json` (8 herramientas) |
| `catalogo_C_vam14.json` | `cee95db1bbc7835ffcc1e3152fdc3fa0a13af18a21d0a4b0a8eb27e3b06509f7` | 22759 | subconjunto de 14 herramientas de `cat_vam.json`, catálogo "C" del diseño (§2.2), no existe como servidor real |
| `correr.py` | `d18c0a9882c6943bca35e965a634534ee859ff4988793d37e6f8f9e92d0b2565` | 5659 | el arnés — invocado como en §1 |
| `estatico.json` | `dcdb4a968233376f09d7f5a9d621e2ee6996ce0bd185cf378bf27ef49fe34ccd` | 23521 | `python bench/salidas-saturacion/estatico.py` |
| `estatico.py` | `386225cfb0d0084080d90b89ba4de577060dc6248eaf01ccb76dd54ae665a246` | 9633 | determinista, sin LLM — reproducible tal cual |
| `grid_haiku.jsonl` | `aa51e51515e097c129add00462462e2ab930510a1cf94106b10bd68d2e4e9124` | 430029 | `python bench/salidas-saturacion/correr.py --modelo haiku --reps 10 --hilos 5 --salida grid_haiku.jsonl` — ver §2/§3, PENDIENTE de reejecución y potencialmente irreproducible al byte |
| `grid_haiku.log` | `0370fbfede4399c57387a184df1aa9ee00d50fa9384d671351991e2fcd8752b0` | 20800 | log de la orden anterior (incluye el fallo de arnés de §8: `FileNotFoundError` en la iteración 274/360 con 5 hilos, relanzado con 3) |
| `grid_haiku_puntuado.jsonl` | `5d3cb5df927b590decc4485feedc7f54a2e6fd440bf94f1cb71c0710b75ed1b4` | 114978 | `python bench/salidas-saturacion/puntuar.py grid_haiku.jsonl` |
| `grid_sonnet.jsonl` | `f6c0a3413ae03d4d9f787c561885701210c5b74ad46741fced10594ab08889f5` | 218698 | `python bench/salidas-saturacion/correr.py --modelo sonnet --reps 5 --hilos 4 --salida grid_sonnet.jsonl` |
| `grid_sonnet.log` | `0f1c7e335b6a4998d32a69cc0f6db6520faeac7a69f730c8a4f87aab3d05458b` | 9460 | log de la orden anterior |
| `grid_sonnet_puntuado.jsonl` | `30ed39002a3f77437e6bcdb1a722d25799785bef4f18e7b8a61c7f5284050a2b` | 58011 | `python bench/salidas-saturacion/puntuar.py grid_sonnet.jsonl` |
| `piloto_haiku.jsonl` | `a6854793c67f7ec01ce1e4960a53cbf3e6c8b13715f12e5e0f46d338bd9c9c6a` | 21404 | piloto de 18 ejecuciones que validó el arnés antes del grid completo (mismo `correr.py`, `--reps` reducido) |
| `puntuar.py` | `eeec7c98cb0c9ba478a51ce2048d839813c7b9b9053a4a7b65b3b02090082112` | 8139 | script de puntuación — determinista sobre un `.jsonl` ya generado |
| `resumen_haiku.txt` | `3dc02dc2047450f14e6afe32507c16ebff80d6339b8853d9eb6cc738d5494fe3` | 7172 | salida por stdout de `puntuar.py grid_haiku.jsonl`, redirigida a fichero |
| `resumen_sonnet.txt` | `dffaddcff163adbae2d5ac7ae2be4ae935971f1dc49750821e88733662162321` | 7108 | salida por stdout de `puntuar.py grid_sonnet.jsonl`, redirigida a fichero |
| `stub_mcp.py` | `cc512818dc718ed05397be86d284f7c640ef3c5e780cbfae34367f66e9d93c31` | 4661 | servidor MCP stub invocado por `correr.py`, no se ejecuta suelto |
| `tablas.py` | `65a90a6b3b1fac89b1c03f7aea96da9c3685fae7a153cb867308ad9a9b04b623` | 4518 | `python bench/salidas-saturacion/tablas.py grid_haiku_puntuado.jsonl "Haiku 4.5"` / con `grid_sonnet_puntuado.jsonl "Sonnet"` |
| `tablas_haiku.md` | `d7d88afd42e917d515dbb1d1849820d363d053bfc232a73b2520dc50c2f43690` | 3769 | salida de la orden anterior (Haiku) |
| `tablas_sonnet.md` | `02911d35f553b40a3b453a02212b31688f16e2a4d5c5fde4c7cc6a4aae528069` | 3769 | salida de la orden anterior (Sonnet) |
| `tareas.json` | `bfff5cd5468cd43ae48055db8c2231e75826f0e3c28f486283919949cbc06450` | 12486 | las 12 peticiones y el criterio de acierto declarado de antemano — escrito a mano, no generado |
