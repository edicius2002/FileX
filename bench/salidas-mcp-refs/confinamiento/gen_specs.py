"""Genera los spec.json de las pruebas de confinamiento contra
@modelcontextprotocol/server-filesystem.

Se usa un script (y no heredocs de shell) porque las rutas de Windows con
barra invertida se destrozan al escaparse en sh. Aqui todo se escribe con
json.dump, que escapa correctamente.

Uso:  python gen_specs.py
Escribe en ./specs/*.json
"""
import json
import os

BASE = "D:/Work/research/FileX/bench/salidas-mcp-refs/confinamiento"
SB = BASE + "/sandbox"
PERM = SB + "/permitido"
PERM_W = PERM.replace("/", "\\")
SB_W = SB.replace("/", "\\")

NPX = "npx.cmd"
PKG = "@modelcontextprotocol/server-filesystem"

SPECS = os.path.join(BASE.replace("/", os.sep), "specs")
os.makedirs(SPECS, exist_ok=True)


def servidor(nombre, raices, log):
    return {
        "nombre": nombre,
        "command": NPX,
        "args": ["-y", PKG] + raices,
        "cwd": BASE,
        "env": {},
        "stderr_log": BASE + "/logs/" + log,
    }


def p(pid, tool, args, nota="", recorte=1200):
    return {"id": pid, "tool": tool, "args": args, "nota": nota, "recorte": recorte,
            "timeout": 60}


def leer(pid, ruta, nota=""):
    return p(pid, "read_text_file", {"path": ruta}, nota)


# ---------------------------------------------------------------- SPEC 1
# Bateria principal de ataques. Sin symlinks (van en el spec 3).
pasos1 = [
    p("cat_allowed", "list_allowed_directories", {}, "que publica el servidor sobre su propia allowlist"),

    # --- controles ---
    leer("A_control_dentro", PERM_W + "\\dentro.txt", "(a) CONTROL: existe y esta dentro"),
    leer("A_control_sub", PERM_W + "\\sub\\anidado.txt", "control: subcarpeta permitida"),
    leer("A_noexiste_dentro", PERM_W + "\\no_existe.txt", "existe=NO, dentro de la raiz"),
    leer("A_noexiste_dir_dentro", PERM_W + "\\no_existe_dir\\x.txt", "padre inexistente dentro de la raiz"),

    # --- oraculo de existencia ---
    leer("B_existe_fuera", SB_W + "\\prohibido\\secreto.txt", "(b) existe pero FUERA de la raiz"),
    leer("C_noexiste_fuera", SB_W + "\\prohibido\\no_existe_jamas.txt", "(c) NO existe y FUERA de la raiz"),
    leer("C2_noexiste_fuera_dir", "D:\\no_existe_esta_unidad_dir\\x.txt", "(c') ni el directorio existe"),

    # --- 1. travesia relativa ---
    leer("T1_rel_simple", "..\\prohibido\\secreto.txt", "travesia relativa con backslash"),
    leer("T2_rel_slash", "../prohibido/secreto.txt", "travesia relativa con slash"),
    leer("T3_abs_dotdot", PERM_W + "\\..\\prohibido\\secreto.txt", "absoluta con .. intercalado"),
    leer("T4_rel_larga", "..\\..\\..\\..\\..\\..\\..\\..\\Windows\\win.ini", "cadena larga relativa a win.ini"),
    leer("T5_abs_dotdot_larga", PERM_W + "\\..\\..\\..\\..\\..\\..\\..\\..\\Windows\\win.ini",
         "cadena larga absoluta a win.ini"),
    leer("T6_rel_senuelo", "..\\..\\senuelo_fuera.txt", "senuelo fuera del sandbox"),

    # --- 2. absoluta fuera de la raiz ---
    leer("R1_abs_cwin", "C:\\Windows\\win.ini", "absoluta a fichero real del sistema"),
    leer("R2_abs_dwin", "D:\\Windows\\win.ini", "absoluta a unidad D (no existe D:\\Windows)"),
    leer("R3_abs_senuelo", BASE.replace("/", "\\") + "\\senuelo_fuera.txt", "absoluta al senuelo"),

    # --- 3. prefijo enganyoso ---
    leer("P1_prefijo", SB_W + "\\permitido_secreto\\trampa.txt", "hermano con prefijo comun"),
    p("P2_prefijo_ls", "list_directory", {"path": SB_W + "\\permitido_secreto"},
      "listar el hermano con prefijo comun"),
    leer("P3_prefijo_concat", PERM_W + "_secreto\\trampa.txt", "misma ruta escrita por concatenacion"),

    # --- 6. peculiaridades de Windows ---
    leer("W1_case_min", PERM_W.lower() + "\\dentro.txt", "todo en minusculas: d:\\work\\..."),
    leer("W2_case_unidad", "d:" + PERM_W[2:] + "\\dentro.txt", "solo la unidad en minuscula"),
    leer("W3_slash", PERM + "/dentro.txt", "barras normales en vez de invertidas"),
    leer("W4_slash_fuera", SB + "/prohibido/secreto.txt", "barras normales, fuera de la raiz"),
    leer("W5_unc_q_dentro", "\\\\?\\" + PERM_W + "\\dentro.txt", "prefijo \\\\?\\ dentro de la raiz"),
    leer("W6_unc_q_fuera", "\\\\?\\" + SB_W + "\\prohibido\\secreto.txt", "prefijo \\\\?\\ fuera de la raiz"),
    leer("W7_unc_q_dotdot", "\\\\?\\" + PERM_W + "\\..\\prohibido\\secreto.txt",
         "prefijo \\\\?\\ + .. (Win32 no normaliza .. tras \\\\?\\)"),
    leer("W8_dev_ns", "\\\\.\\" + SB_W + "\\prohibido\\secreto.txt", "espacio de dispositivos \\\\.\\"),
    leer("W9_ads", PERM_W + "\\dentro.txt:oculto", "flujo de datos alternativo (ADS)"),
    leer("W10_ads_fuera", SB_W + "\\prohibido\\secreto.txt:oculto", "ADS sobre fichero prohibido"),
    leer("W11_punto_final", PERM_W + "\\dentro.txt.", "punto final (Win32 lo recorta)"),
    leer("W12_espacio_final", PERM_W + "\\dentro.txt ", "espacio final (Win32 lo recorta)"),
    leer("W13_nul_dispositivo", PERM_W + "\\NUL", "nombre reservado NUL dentro de la raiz"),
    leer("W14_con_dispositivo", PERM_W + "\\CON", "nombre reservado CON dentro de la raiz"),
    leer("W15_byte_nulo", PERM_W + "\\dentro.txt\u0000.png", "byte nulo (truncamiento)"),
    leer("W16_unidad_relativa", "D:..\\prohibido\\secreto.txt", "ruta relativa a la unidad D:"),
    leer("W17_comillas", '"' + SB_W + '\\prohibido\\secreto.txt"',
         "ruta entre comillas (normalizePath las quita)"),
    leer("W18_espacio_inicial", " " + SB_W + "\\prohibido\\secreto.txt",
         "espacio inicial (isAbsolute falla antes del trim)"),
    leer("W19_gitbash", "/d" + PERM[2:] + "/dentro.txt", "estilo /d/Work/... (convertToWindowsPath)"),
    leer("W20_gitbash_fuera", "/d" + SB[2:] + "/prohibido/secreto.txt", "estilo /d/... fuera de la raiz"),
    leer("W21_wsl", "/mnt/d" + SB[2:] + "/prohibido/secreto.txt", "estilo WSL /mnt/d/..."),
    leer("W22_barra_final", PERM_W + "\\sub\\", "barra final en directorio"),

    # --- amplificador de sondeo (index.ts:345) ---
    p("X1_multi", "read_multiple_files", {"paths": [
        PERM_W + "\\dentro.txt",
        SB_W + "\\prohibido\\secreto.txt",
        SB_W + "\\prohibido\\no_existe_jamas.txt",
        "C:\\Windows\\win.ini",
        "C:\\Windows\\no_existe_jamas.ini",
        "C:\\Users\\krato\\NTUSER.DAT",
    ]}, "un solo tools/call = 6 respuestas del oraculo", recorte=3000),

    # --- otras herramientas contra la misma frontera ---
    p("X2_get_info_fuera", "get_file_info", {"path": SB_W + "\\prohibido\\secreto.txt"},
      "get_file_info fuera de la raiz"),
    p("X3_tree_fuera", "directory_tree", {"path": SB_W}, "directory_tree sobre el padre de la raiz"),
    p("X4_search", "search_files", {"path": PERM_W, "pattern": "*.txt"}, "search dentro de la raiz"),
    p("X5_media_fuera", "read_media_file", {"path": SB_W + "\\prohibido\\secreto.txt"},
      "read_media_file fuera de la raiz"),
]

spec1 = servidor("filesystem-confinamiento", [PERM_W], "fs_ataques.stderr.log")
spec1["pasos"] = pasos1

# ---------------------------------------------------------------- SPEC 2
# Escritura: solo DENTRO del sandbox. Comprueba si el servidor deja escribir
# fuera de la raiz permitida.
pasos2 = [
    p("E1_write_dentro", "write_file",
      {"path": PERM_W + "\\escrito_por_mcp.txt", "content": "escrito dentro de la raiz\n"},
      "control de escritura dentro de la raiz"),
    p("E2_write_fuera", "write_file",
      {"path": SB_W + "\\prohibido\\escrito_fuera.txt", "content": "NO DEBERIA EXISTIR\n"},
      "escritura fuera de la raiz, pero dentro del sandbox"),
    p("E3_write_travesia", "write_file",
      {"path": "..\\prohibido\\escrito_travesia.txt", "content": "NO DEBERIA EXISTIR\n"},
      "escritura por travesia relativa"),
    p("E4_mkdir_fuera", "create_directory", {"path": SB_W + "\\prohibido\\dir_nuevo"},
      "crear directorio fuera de la raiz"),
    p("E5_move_fuera", "move_file",
      {"source": PERM_W + "\\escrito_por_mcp.txt", "destination": SB_W + "\\prohibido\\movido.txt"},
      "mover de dentro a fuera de la raiz"),
    p("E6_sobrescribe", "write_file",
      {"path": PERM_W + "\\dentro.txt", "content": "SOBRESCRITO SIN AVISAR\n"},
      "sobrescritura silenciosa dentro de la raiz (lib.ts:167-180)"),
    leer("E7_verifica", PERM_W + "\\dentro.txt", "confirma que E6 destruyo el original"),
]
spec2 = servidor("filesystem-escritura", [PERM_W], "fs_escritura.stderr.log")
spec2["pasos"] = pasos2

# ---------------------------------------------------------------- SPEC 3
# Symlinks / junctions creados ANTES de arrancar (los crea prep_symlinks.py).
pasos3 = [
    p("cat_allowed", "list_allowed_directories", {}, "allowlist tras resolver symlinks al arrancar"),
    leer("S1_control_interno", PERM_W + "\\link_interno.txt",
         "CONTROL: symlink dentro->dentro, debe funcionar"),
    leer("S2_link_fuera", PERM_W + "\\link_fuera.txt",
         "symlink dentro->fuera (creado ANTES de arrancar)"),
    leer("S3_junc_fuera", PERM_W + "\\junc_fuera\\secreto.txt",
         "junction de directorio dentro->fuera (creada ANTES)"),
    leer("S4_link_win", PERM_W + "\\link_win.txt",
         "symlink dentro->C:\\Windows\\win.ini"),
    p("S5_ls", "list_directory", {"path": PERM_W}, "que ve el servidor en la raiz"),
]
spec3 = servidor("filesystem-symlinks-previos", [PERM_W], "fs_symlinks_previos.stderr.log")
spec3["pasos"] = pasos3

for nombre, spec in [("01_ataques", spec1), ("02_escritura", spec2), ("03_symlinks_previos", spec3)]:
    ruta = os.path.join(SPECS, nombre + ".json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print("escrito", ruta, len(spec["pasos"]), "pasos")
