"""Genera el `spec.json` para `bench/scripts/mcp_probe_bin.py` — el arnés compartido.

**No se copia el arnés: se le da de comer.** El arnés es el mismo que midió los
7.964 tokens de `video-audio-mcp` y los 32 del asa, así que las cifras salen
comparables sin tocar una línea suya.

El spec se genera con un **script de Python**, no con un heredoc: los heredocs de
shell se comen los backslashes de las rutas de Windows (`CLAUDE.md` §4, trampa
19). Aquí se usan barras normales, que Python acepta.

**El cliente es `mcp 1.29.0` (`.venv-mcp-lite`) y el servidor `mcp 2.0.0`
(`.venv-mcp-filex`)**: es a la vez la sonda y la comprobación de que la
restricción de §5.3 se sostiene («un servidor 2.0.0 habla con clientes 1.8.1 y
1.29.0; un servidor 1.8.x muere ante un cliente 2.0.0»).

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_spec_sonda.py
    .venv-mcp-lite/Scripts/python.exe  bench/scripts/mcp_probe_bin.py \\
        bench/salidas-hito4/h4_spec.json bench/salidas-hito4/h4_sonda.json
"""

from __future__ import annotations

import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
RAIZ = os.path.dirname(os.path.dirname(AQUI))
TMP = AQUI + "/tmp-sonda"
os.makedirs(TMP, exist_ok=True)

PNG = RAIZ + "/corpus/imagen/trivial.png"
GRANDE = RAIZ + "/corpus/video/tipico.mp4"          # 15,5 MB: el caso binario

spec = {
    "nombre": "filex-mcp (hito 4)",
    "command": RAIZ + "/.venv-mcp-filex/Scripts/python.exe",
    "args": ["-m", "filex.mcp", "--raiz", RAIZ],
    "cwd": RAIZ,
    "env": {"PYTHONPATH": RAIZ, "PYTHONUTF8": "1"},
    "stderr_log": AQUI + "/h4_sonda_stderr.txt",
    "pasos": [
        {
            "id": "lt_png",
            "tool": "list_targets",
            "args": {"formato_origen": "png"},
            "espera": "prosa",
            "nota": "la respuesta canónica a «¿puedo hacer X?»; mecanismo de "
                    "seguridad contra el 15-17 % de fallos silenciosos",
        },
        {
            "id": "lt_imposible",
            "tool": "list_targets",
            "args": {"formato_origen": "png", "formato_destino": "mp3"},
            "espera": "prosa",
            "nota": "lo imposible se dice, no se sustituye por lo parecido",
        },
        {
            "id": "inspect_png",
            "tool": "inspect",
            "args": {"ruta": PNG},
            "espera": "asa",
            "nota": "exento de R8 y R18: lectura de cabeceras en proceso",
        },
        {
            "id": "inspect_mp4_15MB",
            "tool": "inspect",
            "args": {"ruta": GRANDE},
            "espera": "asa",
            "nota": "el caso binario: 15,5 MB de entrada, respuesta constante",
        },
        {
            "id": "inspect_fuera",
            "tool": "inspect",
            "args": {"ruta": "C:/Windows/win.ini"},
            "espera": "prosa",
            "nota": "R4: mismo mensaje que «no existe», sin lista blanca",
        },
        {
            "id": "inspect_no_existe",
            "tool": "inspect",
            "args": {"ruta": RAIZ + "/corpus/imagen/no_existe.png"},
            "espera": "prosa",
            "nota": "R4: tiene que ser IDÉNTICO al anterior",
        },
        {
            "id": "convert_salida_ya_existe",
            "tool": "convert",
            "args": {"entrada": PNG, "salida": TMP + "/ya_existe.webp"},
            "timeout": 60,
            "espera": "asa",
            "nota": "el disparador exacto de las 26 de 26 que cuelgan la sesión "
                    "MCP entera; aquí devuelve el asa al empezar",
        },
        {
            "id": "convert_video_15MB",
            "tool": "convert",
            "args": {"entrada": GRANDE, "salida": TMP + "/salida.mkv",
                     "parametros": {"copia": True}},
            "timeout": 60,
            "espera": "asa",
            "nota": "15,5 MB: la respuesta no puede crecer con la entrada",
        },
        {
            "id": "convert_imposible",
            "tool": "convert",
            "args": {"entrada": PNG, "salida": TMP + "/x.mp3"},
            "timeout": 60,
            "espera": "prosa",
            "nota": "falla EN EL ACTO y sin gastar un job_id: que no haya camino "
                    "se sabe en microsegundos. El silencio es el modo peligroso",
        },
        {
            "id": "convert_entrada_rota",
            "tool": "convert",
            "args": {"entrada": AQUI + "/h4_roto.png", "salida": TMP + "/roto.webp"},
            "timeout": 60,
            "espera": "asa",
            "nota": "un motor que falla: NUNCA stderr crudo (884-1.228 tokens "
                    "de banner en los tres servidores de referencia)",
        },
        {
            "id": "job_desconocido",
            "tool": "job",
            "args": {"job_id": "no-existe-000000"},
            "espera": "prosa",
            "nota": "no revienta la sesión",
        },
        {
            "id": "batch_dos",
            "tool": "batch",
            "args": {"entradas": [PNG, RAIZ + "/corpus/imagen/tipico.png"],
                     "directorio_salida": TMP, "formato_destino": "jpg"},
            "timeout": 60,
            "espera": "asa",
            "nota": "R5: una entrada rechazada no aborta las demás",
        },
    ],
}

# La salida preexistente que dispara el deadlock de las 26.
with open(TMP + "/ya_existe.webp", "wb") as fh:
    fh.write(b"basura previa" * 8)
with open(AQUI + "/h4_roto.png", "wb") as fh:
    fh.write(b"\x89PNG\r\n\x1a\n" + b"esto no es un png" * 6)

destino = AQUI + "/h4_spec.json"
with open(destino, "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=1)
print(destino)
