"""Genera los spec.json de las pruebas de kordoc (errores + confinamiento)."""
import json
import os

BASE = "D:/Work/research/FileX/bench/salidas-mcp-refs/confinamiento"
K = (BASE + "/sandbox/kordoc").replace("/", "\\")
PROH = (BASE + "/sandbox/prohibido").replace("/", "\\")
SPECS = os.path.join(BASE.replace("/", os.sep), "specs")
os.makedirs(SPECS, exist_ok=True)

NPX = "npx.cmd"
ARGS = ["-y", "-p", "kordoc@4.9.0", "kordoc-mcp"]


def p(pid, tool, args, nota="", recorte=1500):
    return {"id": pid, "tool": tool, "args": args, "nota": nota,
            "recorte": recorte, "timeout": 180}


def parse(pid, ruta, nota=""):
    return p(pid, "parse_document", {"file_path": ruta}, nota)


# ---- SPEC 4: errores, sin KORDOC_ROOT (comportamiento por defecto)
pasos = [
    parse("K_control", K + "\\ok.pdf", "CONTROL: PDF valido del corpus"),
    parse("K_noexiste", K + "\\no_existe.pdf", "fichero inexistente"),
    parse("K_ext_no_soportada", K + "\\noformato.ini", "extension no soportada"),
    parse("K_magico_falso", K + "\\falso.pdf", "texto plano con extension .pdf"),
    parse("K_truncado", K + "\\truncado.pdf", "PDF truncado a 1200 bytes"),
    parse("K_docx_vacio", K + "\\vacio.docx", "ZIP valido sin estructura OOXML"),
    parse("K_directorio", K, "una ruta de directorio, no un fichero"),
    parse("K_imagen", K + "\\imagen.png", "PNG: dispara la ruta de OCR (descarga de modelo)"),
    parse("K_travesia", K + "\\..\\..\\..\\..\\..\\..\\..\\Windows\\win.ini",
          "travesia relativa a win.ini"),
    parse("K_abs_fuera", "C:\\Windows\\win.ini", "ruta absoluta a fichero real del sistema"),
    parse("K_prohibido", PROH + "\\secreto.txt", "fichero fuera del arbol de kordoc"),
    parse("K_vacio", "", "ruta vacia"),
    p("K_detect", "detect_format", {"file_path": K + "\\falso.pdf"},
      "deteccion de formato por magic bytes sobre extension mentirosa"),
    p("K_detect_noexiste", "detect_format", {"file_path": K + "\\no_existe.pdf"},
      "detect_format sobre inexistente"),
    p("K_meta", "parse_metadata", {"file_path": K + "\\ok.pdf"}, "metadatos del control"),
    p("K_tabla_mala", "parse_table", {"file_path": K + "\\truncado.pdf"},
      "otra herramienta sobre la misma entrada corrupta"),
]
spec4 = {"nombre": "kordoc-mcp-errores", "command": NPX, "args": ARGS,
         "cwd": BASE, "env": {"KORDOC_OFFLINE": "1"},
         "stderr_log": BASE + "/logs/kordoc_errores.stderr.log", "pasos": pasos}

# ---- SPEC 5: confinamiento con KORDOC_ROOT
KR = K  # la raiz declarada es sandbox/kordoc
pasos5 = [
    parse("R_control", KR + "\\ok.pdf", "(a) CONTROL: existe y dentro de KORDOC_ROOT"),
    parse("R_noexiste_dentro", KR + "\\no_existe.pdf", "no existe, dentro de la raiz"),
    parse("R_existe_fuera", PROH + "\\secreto.txt",
          "(b) EXISTE pero fuera de KORDOC_ROOT"),
    parse("R_noexiste_fuera", PROH + "\\no_existe_jamas.txt",
          "(c) NO existe y fuera de KORDOC_ROOT"),
    parse("R_existe_fuera_ext_ok", (BASE + "/sandbox/permitido").replace("/", "\\") + "\\..\\..\\..\\..\\..\\..\\ok.pdf",
          "travesia fuera con extension permitida"),
    parse("R_abs_win", "C:\\Windows\\win.ini", "absoluta a win.ini con KORDOC_ROOT puesto"),
    parse("R_abs_win_pdf", "C:\\Windows\\no_existe.pdf",
          "absoluta inexistente con extension permitida"),
    parse("R_travesia", KR + "\\..\\prohibido\\secreto.txt", "travesia relativa"),
    parse("R_case", KR.lower() + "\\ok.pdf", "todo en minusculas (case-insensitivity)"),
    parse("R_symlink", KR + "\\link_fuera.pdf", "enlace dentro de la raiz apuntando fuera"),
]
spec5 = {"nombre": "kordoc-mcp-KORDOC_ROOT", "command": NPX, "args": ARGS,
         "cwd": BASE,
         "env": {"KORDOC_OFFLINE": "1", "KORDOC_ROOT": KR},
         "stderr_log": BASE + "/logs/kordoc_root.stderr.log", "pasos": pasos5}

for n, s in [("04_kordoc_errores", spec4), ("05_kordoc_root", spec5)]:
    r = os.path.join(SPECS, n + ".json")
    json.dump(s, open(r, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("escrito", r, len(s["pasos"]), "pasos")
