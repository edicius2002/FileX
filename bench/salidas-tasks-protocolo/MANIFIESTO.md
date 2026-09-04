# Salidas de `bench/tasks-protocolo.md` — fila `C48`

worker4, carril CPU, ronda 15, 04/09/2026. Rama `cpu/tasks-protocolo`.

**Todo lo de aquí es TEXTO** (arneses `.py`, resultados `.json`/`.jsonl`): se versiona
entero, según `CLAUDE.md` §6. **No hay binarios y no hay nada podado.**

## Entorno de todas las órdenes

| | |
|---|---|
| Intérprete | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` — **3.11.9, win32** |
| Paquetes | `mcp 2.0.0` · `mcp-types 2.0.0` · `tiktoken 0.14.0` |
| Cliente MCP | **Claude Code 2.1.260** (`claude --version`) |
| Raíz | el *worktree*; las órdenes se lanzan desde su raíz |
| Docker | **no hace falta** para ninguna de estas medidas |

Las órdenes van con `PYTHONIOENCODING=utf-8` porque la consola `cp1252` de esta máquina
revienta al imprimir acentos y emojis. Los topes van **dentro** de la orden (trampa 52).

## Ficheros

| Fichero | `sha256` | Bytes | Orden exacta que lo reproduce |
|---|---|---:|---|
| `sonda_tasks.py` | `130e8922e6f17cb3cb19f8c5d1585ce0d716fca6c0afd092b25b1b61c7bd90d2` | 6 861 | *(arnés, escrito a mano)* |
| `sonda_tasks.json` | `0b4ea21d2cac64d7968c02c153202a239464000cae409dadb8d46c117f32e750` | 6 679 | `PYTHONIOENCODING=utf-8 timeout 120 .venv-mcp-filex/Scripts/python.exe bench/salidas-tasks-protocolo/sonda_tasks.py` |
| `srv_sonda_initialize.py` | `7e54e23ee073903062d793d3f67975cd519bfadd2050fb627da2e16ec6b5f879` | 3 180 | *(arnés; lo lanza Claude Code, no se ejecuta a mano)* |
| `cfg_sonda.json` | `2ada9505e970f1c4bb139be57ba8970173607b96028eb9b3caa8d6d9723589f6` | 476 | *(configuración de la celda A)* |
| `r_cliente_2_1_260.jsonl` | `4236f279527fc0211b46a0c40f0334a98575a5ae1db144deb23597d55a6bcde1` | 1 140 | `cd bench/salidas-tasks-protocolo && rm -f r_cliente_2_1_260.jsonl && timeout 240 claude -p "Responde solo con la palabra LISTO." --mcp-config cfg_sonda.json --strict-mcp-config --max-turns 1` |
| `cfg_sonda_2026.json` | `8c635a6f265434bfbb6f555205d41031f4aa6de393e09cde41d1e1e6db162e80` | 516 | *(configuración de la celda B: fija `FILEX_SONDA_PROTO=2026-07-28`)* |
| `r_cliente_2026.jsonl` | `6a0dbcd3a2d36098a5b3167dfca7ee61460df34e6581fba688a3a51861b63b5f` | 921 | `cd bench/salidas-tasks-protocolo && rm -f r_cliente_2026.jsonl && timeout 240 claude -p "Responde solo con la palabra LISTO." --mcp-config cfg_sonda_2026.json --strict-mcp-config --max-turns 1` |
| `sonda_viabilidad_codigo.py` | `0f2b20480d8d82d147bfee3745efcdefa1e931130a2b22461cc1c45e2207906d` | 4 141 | *(arnés, escrito a mano)* |
| `sonda_viabilidad_codigo.json` | `19c2120cba3e006b241d5ada5e5a4043871dfa3713ac5cb6fcf4803d9bcb5cee` | 1 955 | `PYTHONIOENCODING=utf-8 timeout 120 .venv-mcp-filex/Scripts/python.exe bench/salidas-tasks-protocolo/sonda_viabilidad_codigo.py` |
| `srv_tasks_20.py` | `bb0762445a62d82bcb8344e385336d030f166cc15c7434b2faa6e7d8025632eb` | 2 191 | *(arnés; lo lanza `cli_tasks_20.py`)* |
| `cli_tasks_20.py` | `64a49b75fa08b932d03bb60bfc8672de56baa875bbec51ecbac8741c67bdbf09` | 3 183 | *(arnés, escrito a mano)* |
| `r_tasks_20.json` | `dc4ab2a4f4438807e89cd7ad8f4ff3aa2020fd9de0c0b3a9c11d142a2a98c662` | 2 478 | `PYTHONIOENCODING=utf-8 timeout 90 .venv-mcp-filex/Scripts/python.exe bench/salidas-tasks-protocolo/cli_tasks_20.py` |
| `coste_catalogo_tasks.py` | `f1c88403957583358cb3bc7d9f59d1b87cf9680a957eb7711ba1659f1f46de25` | 4 332 | *(arnés, escrito a mano)* |
| `coste_catalogo_tasks.json` | `d0df6671f7b2c37af34fe7252a437cc9668901c7f03f34f2b63194a5b0a20079` | 1 027 | `PYTHONIOENCODING=utf-8 timeout 180 .venv-mcp-filex/Scripts/python.exe bench/salidas-tasks-protocolo/coste_catalogo_tasks.py` |

## Dos avisos para quien repita esto

1. **Los dos `.jsonl` NO son deterministas en el número de líneas.** Registran una sesión real
   de Claude Code; el `initialize` y sus capacidades sí se reproducen, pero el `t_ms` y el
   cierre de `stdin` dependen de la sesión. **Lo que se publica del fichero son los campos
   `protocolVersion` y `capabilities`, que son estables.**
2. **`coste_catalogo_tasks.json` depende del REGISTRO, no sólo del código.** Esta tanda mide
   **232 aristas / 34 orígenes / 34 destinos / 6 motores → 1 650 tokens**. El histórico de
   `bench/gotenberg-y-mcp.md` midió 215 aristas → 1 605. **Si el registro crece, la cifra
   crece con él** (≈2,6 tokens por arista), así que la orden se reproduce pero el número no es
   una constante del proyecto. Los tres escenarios E0/E1/E2 sí son comparables entre sí porque
   salen de la misma ejecución.
