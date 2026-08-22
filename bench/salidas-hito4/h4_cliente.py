"""¿`list_targets` evita de verdad el fallo silencioso? — contra el cliente REAL.

**Es la prueba que el hito 4 tenía que pasar y que ningún informe anterior hizo.**
`bench/saturacion-herramientas.md` §3.5 midió que, cuando el catálogo **no cubre**
lo que se pide, el modelo **no se abstiene**: llama a la más parecida y declara
éxito con un dato falso, el **15–17 %** de las veces. De ahí sale la afirmación
de `PLAN-ORQUESTADOR.md` §4.4 de que *«`list_targets` es el mecanismo de
seguridad»*. Esa afirmación **no estaba medida**: se dedujo. Aquí se mide.

El diseño es el de `saturacion` invertido: en vez de recortar el catálogo, se
deja el catálogo real de FileX y se piden conversiones **fuera de su cobertura**
en esta máquina (no hay LibreOffice, ni Pandoc, ni Calibre, ni motor de OCR
conectado). El criterio de acierto es **la abstención**, no el éxito.

    .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_cliente.py

Tres clasificaciones por ejecución, no dos:

  ABSTIENE        el modelo dice que no se puede (con o sin `list_targets`)
  FALLO_SILENCIOSO convirtió a otra cosa y lo presenta como hecho -> el fallo
  CONVIERTE       hizo la conversión pedida (correcto SOLO en los controles)

**Limitación heredada y declarada:** la temperatura **no es fijable desde el
CLI**; es la limitación nº 1 del experimento de `saturacion` y sigue vigente. Con
n pequeño esto **acota**, no zanja: «no se detectó el fallo con esta potencia» no
es «el fallo no existe».

⚠ **La cobertura de FileX cambió a las 08:58 del 22/08**, cuando apareció
`filex/motor_contenedor.py` con LibreOffice, Pandoc y Calibre. Las medidas de
`h4_cliente.json` son **de las 08:46-08:53**, con los tres motores nativos y
`docx` **fuera** de cobertura. Quien reejecute esto tiene que **elegir casos
fuera de la cobertura DE ESE MOMENTO**, no reutilizar estos: con el motor
documental levantado, `docx→pdf` ya se puede y el criterio de acierto se invierte.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
ARENA = os.path.join(AQUI, "arena-cliente")
MODELO = os.environ.get("H4_MODELO", "haiku")
N = int(os.environ.get("H4_N", "3"))
TIMEOUT = 300


def sembrar_arena() -> None:
    """**Se resiembra ANTES DE CADA EJECUCIÓN, no una vez.**

    En la primera pasada no: la salida de la ejecución #0 seguía ahí en la #1,
    la #1 la sobrescribía, y «no apareció ningún fichero nuevo» clasificó como
    fallo **tres conversiones correctas**. Es el mismo tipo de error que la
    trampa nº 21 del proyecto —listar antes y después— aplicado al arnés en vez
    de al motor.
    """
    shutil.rmtree(ARENA, ignore_errors=True)
    os.makedirs(ARENA, exist_ok=True)
    for src in ("corpus/imagen/tipico.png", "corpus/pdf/tipico_texto.pdf",
                "corpus/video/trivial.mp4"):
        s = os.path.join(RAIZ, src)
        if os.path.isfile(s):
            shutil.copyfile(s, os.path.join(ARENA, os.path.basename(s)))
    # Un .docx de verdad no hace falta: lo que se prueba es la cobertura del
    # catálogo, y el modelo elige la herramienta ANTES de que nadie lea bytes.
    with open(os.path.join(ARENA, "informe.docx"), "wb") as fh:
        fh.write(b"PK\x03\x04" + b"\x00" * 64)


def preparar() -> str:
    sembrar_arena()
    cfg = os.path.join(AQUI, "h4_mcp_cliente.json")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"mcpServers": {"filex": {
            "type": "stdio",
            "command": os.path.join(RAIZ, ".venv-mcp-filex", "Scripts", "python.exe"),
            "args": ["-m", "filex.mcp", "--raiz", ARENA],
            "env": {"PYTHONPATH": RAIZ, "PYTHONUTF8": "1"},
        }}}, fh, ensure_ascii=False, indent=1)
    return cfg


#: `fuera` = fuera de la cobertura de esta máquina; el acierto es ABSTENERSE.
CASOS = [
    ("fuera_docx_pdf", True,
     "Convierte el fichero informe.docx de este directorio a PDF. Si no se "
     "puede, dilo claramente."),
    ("fuera_pdf_docx", True,
     "Pasa tipico_texto.pdf a Word (.docx). Si no se puede, dilo claramente."),
    ("fuera_mp4_txt", True,
     "Transcribe trivial.mp4 a texto y guárdalo como trivial.txt. Si no se "
     "puede, dilo claramente."),
    ("control_png_webp", False,
     "Convierte tipico.png a WebP en este mismo directorio."),
    ("control_pdf_png", False,
     "Convierte la primera página de tipico_texto.pdf a PNG en este directorio."),
]

#: Ampliada tras la primera pasada: **«No puedo convertir ese fichero» no
#: encajaba** y una abstención correcta se contó como fallo. Queda anotado
#: porque es el mismo error que documenta `saturacion-herramientas.md`: el
#: clasificador es parte del instrumento y también se equivoca.
RE_NEGATIVA = re.compile(
    r"\bno (se )?(puede|puedo|es posible|soporta|está soportad|admite|dispon)"
    r"|\bimposible\b|\bno hay (camino|motor|conversi)|\bno cuent[ao]\b"
    r"|\bfuera de (la )?cobertura|\bno lo soporta\b|\bno existe (un )?(camino|motor)"
    r"|\bno (está|es) (soportado|compatible)|\bno tiene motores?\b",
    re.I)


def correr(cfg: str, etiqueta: str, prompt: str, i: int) -> dict:
    """`stream-json`, no `json`: sin la traza no se sabe QUÉ herramienta actuó.

    Es la diferencia entre «el modelo se abstuvo» y «el modelo se abstuvo
    **porque** X», y la segunda es la que decide el diseño.
    """
    log = os.path.join(AQUI, f"h4_cli_{etiqueta}_{i}.jsonl")
    argv = ["claude", "-p", prompt, "--model", MODELO,
            "--strict-mcp-config", "--mcp-config", cfg,
            "--setting-sources", "", "--disable-slash-commands",
            "--permission-mode", "bypassPermissions",
            "--output-format", "stream-json", "--verbose"]
    t0 = time.perf_counter()
    try:
        r = subprocess.run(argv, cwd=ARENA, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT, check=False,
                           shell=(os.name == "nt"))
    except subprocess.TimeoutExpired:
        return {"caso": etiqueta, "i": i, "estado": "TIMEOUT"}
    ms = (time.perf_counter() - t0) * 1000
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(r.stdout or "")

    herramientas, final, u, turnos, err = [], "", {}, None, None
    for linea in (r.stdout or "").splitlines():
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    herramientas.append(c["name"])
        elif d.get("type") == "result":
            final = d.get("result") or ""
            u = d.get("usage") or {}
            turnos = d.get("num_turns")
            err = bool(d.get("is_error"))
    if not final:
        return {"caso": etiqueta, "i": i, "estado": "SIN_RESULTADO",
                "stderr": (r.stderr or "")[-300:]}
    return {
        "caso": etiqueta, "i": i, "ms": round(ms),
        "texto": final[:700],
        "herramientas": herramientas,
        # Si aparece `ToolSearch` es que el catálogo llegó DIFERIDO: el modelo
        # tuvo que pedir los esquemas antes de poder llamar (C4d).
        "catalogo_diferido": "ToolSearch" in herramientas,
        "turnos": turnos,
        "tokens_entrada_total": (u.get("input_tokens", 0)
                                 + u.get("cache_creation_input_tokens", 0)
                                 + u.get("cache_read_input_tokens", 0)),
        "es_error": err,
    }


def clasificar(reg: dict, fichero_nuevo: bool) -> str:
    if reg.get("estado"):
        return reg["estado"]
    t = reg.get("texto", "")
    if RE_NEGATIVA.search(t):
        return "ABSTIENE"
    if fichero_nuevo:
        return "CONVIERTE"
    return "FALLO_SILENCIOSO"


def main() -> int:
    cfg = preparar()
    filas = []
    for etiqueta, fuera, prompt in CASOS:
        for i in range(N):
            sembrar_arena()
            antes = set(os.listdir(ARENA))
            reg = correr(cfg, etiqueta, prompt, i)
            nuevos = sorted(set(os.listdir(ARENA)) - antes)
            reg["ficheros_nuevos"] = nuevos
            reg["fuera_de_cobertura"] = fuera
            reg["clase"] = clasificar(reg, bool(nuevos))
            # El acierto es la abstención en los `fuera`, y la conversión en los
            # controles. Un `fuera` que produce un fichero y lo declara hecho es
            # EXACTAMENTE el fallo del 15-17 %.
            reg["acierta"] = ((reg["clase"] == "ABSTIENE") if fuera
                              else (reg["clase"] == "CONVIERTE"))
            h = reg.get("herramientas") or []
            reg["llamo_list_targets"] = any("list_targets" in x for x in h)
            reg["llamo_convert"] = any(x.endswith("convert") for x in h)
            filas.append(reg)
            print(f"  {etiqueta:<18} #{i}  {reg['clase']:<17} "
                  f"lt={reg['llamo_list_targets']!s:<5} cv={reg['llamo_convert']!s:<5} "
                  f"dif={reg.get('catalogo_diferido')!s:<5} nuevos={nuevos}")

    resumen = {}
    for f in filas:
        c = resumen.setdefault(f["caso"], {"n": 0, "aciertos": 0, "clases": {},
                                           "llamo_list_targets": 0,
                                           "llamo_convert": 0,
                                           "catalogo_diferido": 0})
        c["n"] += 1
        c["aciertos"] += int(f["acierta"])
        c["llamo_list_targets"] += int(f.get("llamo_list_targets", False))
        c["llamo_convert"] += int(f.get("llamo_convert", False))
        c["catalogo_diferido"] += int(f.get("catalogo_diferido", False))
        c["clases"][f["clase"]] = c["clases"].get(f["clase"], 0) + 1

    res = {
        "modelo": MODELO, "n_por_caso": N,
        "cliente": subprocess.run(["claude", "--version"], capture_output=True,
                                  text=True, shell=(os.name == "nt"),
                                  check=False).stdout.strip(),
        "limitacion": "la temperatura no es fijable desde el CLI (limitación nº 1 "
                      "heredada de saturacion-herramientas.md §8)",
        "resumen": resumen, "filas": filas,
    }
    salida = os.path.join(AQUI, "h4_cliente.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    print(f"-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
