# -*- coding: utf-8 -*-
"""
FileX - Banco de pruebas del COSTE de la validacion de rutas en Python.

Objetivo: medir cuanto cuesta cada primitiva de validacion de rutas
(normcase / normpath / abspath / realpath / is_relative_to / startswith)
en funcion del numero de componentes y de la longitud total, y medir el
limite del SO para cadenas de enlaces simbolicos. A partir de ahi se
recomiendan topes numericos que FileX debe imponer ANTES de llamar a
realpath, para que la propia validacion no sea el vector de DoS.

Solo stdlib. No toca nada fuera de su directorio de salida.
"""

import json
import os
import os.path
import pathlib
import platform
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
LINKTMP = os.path.join(AQUI, "linktmp")
SALIDA_JSON = os.path.join(AQUI, "resultados.json")
SALIDA_TXT = os.path.join(AQUI, "resultados.txt")

# ---------------------------------------------------------------------------
# Motor de medicion
# ---------------------------------------------------------------------------

def medir(fn, objetivo_s=0.03, repeticiones=7, max_n=200000, tope_total_s=6.0):
    """Devuelve (mediana_seg_por_llamada, n_por_lote, repeticiones_reales).

    Calibra n para que cada lote dure ~objetivo_s, luego ejecuta
    `repeticiones` lotes y devuelve la MEDIANA del tiempo por llamada.
    """
    # calibracion
    n = 1
    while True:
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        dt = time.perf_counter() - t0
        if dt >= objetivo_s or n >= max_n:
            break
        # estimacion del siguiente n (con margen)
        if dt <= 0:
            n *= 8
        else:
            n = min(max_n, max(n * 2, int(n * objetivo_s / dt * 1.2) + 1))
    muestras = []
    t_ini = time.perf_counter()
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        muestras.append((time.perf_counter() - t0) / n)
        if time.perf_counter() - t_ini > tope_total_s:
            break
    muestras.sort()
    mediana = muestras[len(muestras) // 2]
    return mediana, n, len(muestras)


def us(segundos):
    return segundos * 1e6


def fmt_t(segundos):
    """Formatea un tiempo por llamada de forma legible."""
    u = us(segundos)
    if u < 1000:
        return "%.3f us" % u
    if u < 1_000_000:
        return "%.3f ms" % (u / 1000.0)
    return "%.3f s" % (u / 1e6)


def tabla(cabeceras, filas):
    anchos = [len(h) for h in cabeceras]
    for f in filas:
        for i, c in enumerate(f):
            anchos[i] = max(anchos[i], len(str(c)))
    linea = lambda cs: "| " + " | ".join(str(c).ljust(anchos[i]) for i, c in enumerate(cs)) + " |"
    sep = "|" + "|".join("-" * (a + 2) for a in anchos) + "|"
    out = [linea(cabeceras), sep]
    for f in filas:
        out.append(linea(f))
    return "\n".join(out)


LOG = []

def log(s=""):
    print(s)
    LOG.append(s)


# ---------------------------------------------------------------------------
# Construccion de rutas sinteticas
# ---------------------------------------------------------------------------

RAIZ = "C:/" if os.name == "nt" else "/"
BASE = "C:/base" if os.name == "nt" else "/base"


def ruta_simple(n):
    """C:/comp/comp/.../comp  con n componentes."""
    return RAIZ + "/".join(["comp"] * n)


def ruta_dotdot(n):
    """C:/base/a/../a/../...  con n pares (a, ..) -> 2n componentes."""
    return BASE + "/" + "/".join(["a", ".."] * n)


def ruta_solo_dotdot(n):
    """C:/base/../../../...  con n '..' seguidos."""
    return BASE + "/" + "/".join([".."] * n)


def ruta_larga_1comp(chars):
    """C:/base/<un unico componente de `chars` caracteres>."""
    return BASE + "/" + ("x" * chars)


# ---------------------------------------------------------------------------
# Operaciones bajo medicion
# ---------------------------------------------------------------------------

def hacer_ops(p, base_pura, base_prefijo):
    """Devuelve dict nombre -> callable sin argumentos."""
    pp_base = base_pura
    return {
        "normcase": lambda: os.path.normcase(p),
        "normpath": lambda: os.path.normpath(p),
        "abspath": lambda: os.path.abspath(p),
        "realpath": lambda: os.path.realpath(p),
        "PurePath.is_relative_to": lambda: pathlib.PurePath(p).is_relative_to(pp_base),
        "startswith": lambda: p.startswith(base_prefijo),
    }


OPS = ["normcase", "normpath", "abspath", "realpath",
       "PurePath.is_relative_to", "startswith"]


# ---------------------------------------------------------------------------
# PARTE 1 y 2
# ---------------------------------------------------------------------------

def parte1(resultados):
    log("=" * 78)
    log("PARTE 1 - Coste por operacion vs numero de componentes (MEDIDO)")
    log("=" * 78)
    log("Python %s | %s" % (sys.version.split()[0], platform.platform()))
    log("Todas las celdas = tiempo MEDIANO por llamada.")
    log("")

    base_pura = pathlib.PurePath(BASE)
    base_prefijo = os.path.normcase(BASE) + os.sep

    for etiqueta, gen, descr in [
        ("simple", ruta_simple, "C:/comp/comp/... (N componentes, sin '..')"),
        ("con-dotdot", ruta_dotdot, "C:/base/a/../a/../... (N pares 'a','..' = 2N componentes)"),
    ]:
        log("--- Variante: %s -> %s" % (etiqueta, descr))
        filas = []
        crudo = {}
        for n in (10, 100, 1000, 10000):
            p = gen(n)
            ops = hacer_ops(p, base_pura, base_prefijo)
            fila = [str(n), str(len(p))]
            crudo[n] = {"len_chars": len(p)}
            for nombre in OPS:
                t, lote, reps = medir(ops[nombre])
                fila.append(fmt_t(t))
                crudo[n][nombre] = {"seg_por_llamada": t, "us_por_llamada": us(t),
                                    "n_lote": lote, "repeticiones": reps}
            filas.append(fila)
        log(tabla(["N comp", "len(chars)"] + OPS, filas))
        log("")
        # escalado
        log("Escalado (tiempo(N) / tiempo(N/10), ideal lineal = 10x):")
        fesc = []
        for n in (100, 1000, 10000):
            f = [str(n)]
            for nombre in OPS:
                a = crudo[n][nombre]["seg_por_llamada"]
                b = crudo[n // 10][nombre]["seg_por_llamada"]
                f.append("%.2fx" % (a / b) if b > 0 else "n/a")
            fesc.append(f)
        log(tabla(["N comp"] + OPS, fesc))
        log("")
        resultados["parte1"][etiqueta] = crudo


def parte2(resultados):
    log("=" * 78)
    log("PARTE 2 - Rutas con MUCHOS '..' seguidos: normpath (MEDIDO)")
    log("=" * 78)
    filas = []
    crudo = {}
    for n in (10, 100, 1000, 10000, 100000):
        p = ruta_solo_dotdot(n)
        t_np, _, _ = medir(lambda: os.path.normpath(p))
        t_rp, _, _ = medir(lambda: os.path.realpath(p))
        r = os.path.normpath(p)
        filas.append([str(n), str(len(p)), fmt_t(t_np), fmt_t(t_rp),
                      (r[:40] + "..." if len(r) > 43 else r)])
        crudo[n] = {"len_chars": len(p), "normpath_s": t_np, "realpath_s": t_rp,
                    "normpath_resultado": r}
    log(tabla(["N '..'", "len(chars)", "normpath", "realpath", "normpath(p) ->"], filas))
    log("")
    log("Escalado normpath (t(N)/t(N/10), ideal lineal = 10x):")
    f = []
    for n in (100, 1000, 10000, 100000):
        f.append([str(n), "%.2fx" % (crudo[n]["normpath_s"] / crudo[n // 10]["normpath_s"])])
    log(tabla(["N '..'", "factor"], f))
    log("")
    resultados["parte2"] = crudo


# ---------------------------------------------------------------------------
# PARTE 3 - cadena de enlaces simbolicos
# ---------------------------------------------------------------------------

def limpiar_linktmp():
    if not os.path.isdir(LINKTMP):
        return
    for nombre in sorted(os.listdir(LINKTMP), reverse=True):
        ruta = os.path.join(LINKTMP, nombre)
        try:
            if os.path.islink(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    os.rmdir(ruta)
            elif os.path.isdir(ruta):
                os.rmdir(ruta)
            else:
                os.remove(ruta)
        except OSError as e:
            print("  aviso: no se pudo borrar %s: %r" % (ruta, e))
    try:
        os.rmdir(LINKTMP)
    except OSError:
        pass


def parte3(resultados):
    log("=" * 78)
    log("PARTE 3 - Cadena de enlaces simbolicos encadenados (MEDIDO)")
    log("=" * 78)
    r = {"soportado": False, "error_symlink": None, "medidas": [],
         "primer_fallo_realpath_strict": None,
         "primer_fallo_open": None,
         "primer_resultado_incorrecto": None,
         "max_enlaces_creados": 0}
    resultados["parte3"] = r

    limpiar_linktmp()
    os.makedirs(LINKTMP, exist_ok=True)
    real = os.path.join(LINKTMP, "objetivo_real.txt")
    with open(real, "w", encoding="utf-8") as fh:
        fh.write("FileX target\n")
    real_resuelto = os.path.realpath(real)

    # comprobar si podemos crear symlinks
    prueba = os.path.join(LINKTMP, "prueba_symlink")
    try:
        os.symlink(real, prueba)
        os.remove(prueba)
        r["soportado"] = True
    except (OSError, NotImplementedError, AttributeError) as e:
        r["error_symlink"] = repr(e)
        log("os.symlink NO disponible: %r" % (e,))
        log("(en Windows requiere Modo Desarrollador o privilegio SeCreateSymbolicLink)")
        log("")
        return

    log("os.symlink disponible. Construyendo cadena l_1 -> l_2 -> ... -> objetivo_real.txt")
    log("realpath(l_k) debe atravesar k enlaces.")
    log("")

    MAX = 300
    anterior = real
    checkpoints = set([1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 61, 62, 63,
                       64, 65, 70, 80, 100, 120, 150, 200, 250, 300])
    # todos los k entre 55 y 70 para localizar el limite exacto
    checkpoints |= set(range(55, 72))
    filas = []
    for k in range(1, MAX + 1):
        enlace = os.path.join(LINKTMP, "l_%04d" % k)
        try:
            os.symlink(anterior, enlace)
        except OSError as e:
            log("  os.symlink fallo al crear el enlace nº %d: %r" % (k, e))
            break
        anterior = enlace
        r["max_enlaces_creados"] = k

        if k not in checkpoints:
            continue

        fila = [str(k)]
        # 1) realpath por defecto (strict=False) - nunca lanza
        try:
            t, _, _ = medir(lambda: os.path.realpath(enlace), objetivo_s=0.02,
                            repeticiones=5, tope_total_s=3.0)
            res = os.path.realpath(enlace)
            ok = os.path.normcase(res) == os.path.normcase(real_resuelto)
            fila.append(fmt_t(t))
            fila.append("SI" if ok else "NO")
            if not ok and r["primer_resultado_incorrecto"] is None:
                r["primer_resultado_incorrecto"] = k
        except OSError as e:
            t = None
            ok = False
            fila.append("EXC %s" % type(e).__name__)
            fila.append("NO")
            if r["primer_resultado_incorrecto"] is None:
                r["primer_resultado_incorrecto"] = k

        # 2) realpath strict=True
        try:
            os.path.realpath(enlace, strict=True)
            strict_ok = True
            strict_err = None
        except OSError as e:
            strict_ok = False
            strict_err = "%s errno=%s winerror=%s" % (type(e).__name__, e.errno,
                                                      getattr(e, "winerror", None))
            if r["primer_fallo_realpath_strict"] is None:
                r["primer_fallo_realpath_strict"] = k
        fila.append("ok" if strict_ok else strict_err)

        # 3) el SO abriendo de verdad el fichero
        try:
            with open(enlace, "rb"):
                pass
            open_ok = True
            open_err = None
        except OSError as e:
            open_ok = False
            open_err = "%s errno=%s winerror=%s" % (type(e).__name__, e.errno,
                                                    getattr(e, "winerror", None))
            if r["primer_fallo_open"] is None:
                r["primer_fallo_open"] = k
        fila.append("ok" if open_ok else open_err)

        filas.append(fila)
        r["medidas"].append({"enlaces": k, "realpath_s": t,
                             "realpath_resuelve_bien": ok,
                             "strict_ok": strict_ok, "strict_err": strict_err,
                             "open_ok": open_ok, "open_err": open_err})

    log(tabla(["K enlaces", "realpath(l_K)", "resuelve OK", "realpath(strict=True)", "open()"],
              filas))
    log("")
    log("Enlaces creados con exito: %d" % r["max_enlaces_creados"])
    log("Primer K en que realpath(strict=True) falla: %s" % r["primer_fallo_realpath_strict"])
    log("Primer K en que open() falla:                %s" % r["primer_fallo_open"])
    log("Primer K en que realpath(strict=False) devuelve algo distinto del objetivo real: %s"
        % r["primer_resultado_incorrecto"])
    log("")

    # escalado del coste por enlace, en el tramo que funciona
    ok_med = [m for m in r["medidas"] if m["realpath_s"] and m["open_ok"]]
    if len(ok_med) >= 2:
        a, b = ok_med[0], ok_med[-1]
        dk = b["enlaces"] - a["enlaces"]
        if dk > 0:
            por_enlace = (b["realpath_s"] - a["realpath_s"]) / dk
            log("Coste marginal MEDIDO por enlace adicional (tramo K=%d..%d): %s por enlace"
                % (a["enlaces"], b["enlaces"], fmt_t(por_enlace)))
            r["coste_marginal_por_enlace_s"] = por_enlace
    log("")


# ---------------------------------------------------------------------------
# PARTE 4 - longitud pura
# ---------------------------------------------------------------------------

def parte4(resultados):
    log("=" * 78)
    log("PARTE 4 - Coste por LONGITUD pura (1 sola componente) (MEDIDO)")
    log("=" * 78)
    filas = []
    crudo = {}
    base_pura = pathlib.PurePath(BASE)
    base_prefijo = os.path.normcase(BASE) + os.sep
    for chars in (100, 1000, 10000, 100000, 1000000):
        p = ruta_larga_1comp(chars)
        ops = hacer_ops(p, base_pura, base_prefijo)
        fila = [str(chars), str(len(p))]
        crudo[chars] = {"len_chars": len(p)}
        for nombre in ("normcase", "normpath", "abspath", "realpath",
                       "PurePath.is_relative_to", "startswith"):
            t, _, _ = medir(ops[nombre], objetivo_s=0.02, repeticiones=5, tope_total_s=4.0)
            fila.append(fmt_t(t))
            crudo[chars][nombre] = {"seg_por_llamada": t, "us_por_llamada": us(t)}
        filas.append(fila)
    log(tabla(["chars de la componente", "len total"] + OPS, filas))
    log("")

    # Comparativa directa: mismo numero total de caracteres, distinto reparto
    log("Comparativa a IGUAL longitud total (~50.000 chars): muchas componentes vs una sola")
    p_muchas = RAIZ + "/".join(["comp"] * 10000)          # ~50.000 chars, 10.000 comps
    p_una = ruta_larga_1comp(len(p_muchas) - len(BASE) - 1)  # misma longitud, 1 comp
    filas2 = []
    for etiqueta, p in (("10.000 componentes", p_muchas), ("1 componente", p_una)):
        f = [etiqueta, str(len(p))]
        ops = hacer_ops(p, base_pura, base_prefijo)
        for nombre in ("normcase", "normpath", "abspath", "realpath"):
            t, _, _ = medir(ops[nombre], objetivo_s=0.02, repeticiones=5, tope_total_s=4.0)
            f.append(fmt_t(t))
        filas2.append(f)
    log(tabla(["reparto", "len total", "normcase", "normpath", "abspath", "realpath"], filas2))
    log("")
    resultados["parte4"] = {"una_componente": crudo}


# ---------------------------------------------------------------------------

def parte5(resultados):
    """Verificacion detallada de la cadena de enlaces: que devuelve realpath
    exactamente en cada regimen, y donde esta el limite real del SO."""
    log("=" * 78)
    log("PARTE 5 - Verificacion detallada de la cadena de enlaces (MEDIDO)")
    log("=" * 78)
    limpiar_linktmp()
    os.makedirs(LINKTMP, exist_ok=True)
    real = os.path.join(LINKTMP, "objetivo_real.txt")
    with open(real, "w", encoding="utf-8") as fh:
        fh.write("FileX target\n")
    real_resuelto = os.path.realpath(real)
    log("objetivo real resuelto: %s" % real_resuelto)

    try:
        prueba = os.path.join(LINKTMP, "prueba_symlink")
        os.symlink(real, prueba)
        os.remove(prueba)
    except OSError as e:
        log("os.symlink no disponible: %r" % (e,))
        limpiar_linktmp()
        return

    filas = []
    detalle = []
    anterior = real
    # linea base: coste de realpath sobre una ruta REAL existente, sin enlaces
    t_base, _, _ = medir(lambda: os.path.realpath(real), objetivo_s=0.02,
                         repeticiones=5, tope_total_s=3.0)
    t_base_dir, _, _ = medir(lambda: os.path.realpath(AQUI), objetivo_s=0.02,
                             repeticiones=5, tope_total_s=3.0)
    log("LINEA BASE realpath sobre fichero real existente (8 componentes): %s" % fmt_t(t_base))
    log("LINEA BASE realpath sobre directorio real existente:              %s" % fmt_t(t_base_dir))
    log("")
    resultados.setdefault("linea_base", {})["realpath_fichero_existente_s"] = t_base
    resultados["linea_base"]["realpath_dir_existente_s"] = t_base_dir

    puntos = set(list(range(1, 46)) + [50, 62, 63, 64, 80, 120])
    MAXK = 120
    for k in range(1, MAXK + 1):
        enlace = os.path.join(LINKTMP, "m_%04d" % k)
        try:
            os.symlink(anterior, enlace)
        except OSError as e:
            log("symlink fallo en k=%d: %r" % (k, e))
            break
        anterior = enlace
        if k not in puntos:
            continue
        res = os.path.realpath(enlace)
        igual = os.path.normcase(res) == os.path.normcase(real_resuelto)
        try:
            os.path.realpath(enlace, strict=True)
            st = "ok"
        except OSError as e:
            st = "winerror=%s" % getattr(e, "winerror", None)
        try:
            with open(enlace, "rb"):
                pass
            op = "ok"
        except OSError as e:
            op = "errno=%s" % e.errno
        # ¿lstat/readlink funcionan?
        try:
            os.readlink(enlace)
            rl = "ok"
        except OSError as e:
            rl = "errno=%s" % e.errno
        filas.append([str(k), os.path.basename(res), "SI" if igual else "NO", st, op, rl])
        detalle.append({"k": k, "realpath_basename": os.path.basename(res),
                        "igual_al_objetivo": igual, "strict": st, "open": op,
                        "readlink": rl})
    log(tabla(["K", "basename(realpath(l_K))", "== objetivo real", "strict=True",
               "open()", "readlink()"], filas))
    log("")
    resultados["parte5"] = detalle
    limpiar_linktmp()


def parte6(resultados):
    """Barrido fino del coste de realpath vs numero de componentes, para
    localizar el PICO de coste y explicar el colapso en N grande."""
    log("=" * 78)
    log("PARTE 6 - Barrido fino de os.path.realpath vs nº de componentes (MEDIDO)")
    log("=" * 78)
    log("Mecanismo: en Windows ntpath.realpath llama a _getfinalpathname(ruta);")
    log("si falla (ruta inexistente) entra en _getfinalpathname_nonstrict, que")
    log("va PARTIENDO la ruta componente a componente y hace UNA SYSCALL POR")
    log("COMPONENTE. Coste = O(nº de componentes) en llamadas al sistema.")
    log("")
    base_existente = AQUI  # este directorio SI existe
    filas = []
    crudo = {}
    for n in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 4000, 6000, 8000, 10000):
        p_c = RAIZ + "/".join(["comp"] * n)
        p_b = base_existente.replace("\\", "/") + "/" + "/".join(["comp"] * n)
        t_c, _, rc = medir(lambda: os.path.realpath(p_c), objetivo_s=0.02,
                           repeticiones=3, tope_total_s=4.0)
        t_b, _, rb = medir(lambda: os.path.realpath(p_b), objetivo_s=0.02,
                           repeticiones=3, tope_total_s=4.0)
        r_c = os.path.realpath(p_c)
        colapso = "SI (ruta demasiado larga, devuelta sin resolver)" if len(p_c) > 32760 else ""
        filas.append([str(n), str(len(p_c)), fmt_t(t_c), fmt_t(t_b),
                      "%.2f" % (us(t_c) / n), colapso])
        crudo[n] = {"len_chars": len(p_c), "realpath_raiz_s": t_c,
                    "realpath_base_existente_s": t_b,
                    "us_por_componente": us(t_c) / n,
                    "resultado_len": len(r_c)}
    log(tabla(["N comp", "len(chars)", "realpath bajo C:/", "realpath bajo dir existente",
               "us/componente", "nota"], filas))
    log("")
    # comprobacion explicita del umbral de longitud
    log("Umbral de longitud de Windows (por que N=10000 'se abarata'):")
    fl = []
    for L in (1000, 8000, 16000, 32000, 32760, 32768, 40000, 60000):
        p = RAIZ + "x" * L
        try:
            t, _, _ = medir(lambda: os.path.realpath(p), objetivo_s=0.01,
                            repeticiones=3, tope_total_s=2.0)
            res = os.path.realpath(p)
            nota = "devuelta sin resolver" if len(res) >= len(p) else "resuelta"
        except OSError as e:
            t = float("nan")
            nota = "OSError winerror=%s" % getattr(e, "winerror", None)
        fl.append([str(L), fmt_t(t), nota])
    log(tabla(["len ruta (chars)", "realpath", "resultado"], fl))
    log("")
    resultados["parte6"] = crudo


MAX_CHARS = 4096
MAX_COMPONENTES = 128
MAX_ENLACES = 16


def guardian(p):
    """Guardian barato que FileX debe ejecutar ANTES de tocar el disco.
    Devuelve True si la ruta es aceptable para pasar a realpath."""
    if len(p) > MAX_CHARS:
        return False
    # contar separadores es O(n) en C, muchisimo mas barato que normpath
    if p.count("/") + p.count("\\") > MAX_COMPONENTES:
        return False
    return True


def parte7(resultados):
    log("=" * 78)
    log("PARTE 7 - Coste del GUARDIAN previo propuesto (MEDIDO)")
    log("=" * 78)
    log("guardian(): len(p) <= %d chars y separadores <= %d, antes de tocar disco."
        % (MAX_CHARS, MAX_COMPONENTES))
    log("")
    casos = [
        ("ruta normal (8 comps, 60 chars)", AQUI + "\\resultados.json"),
        ("hostil: 10.000 componentes", ruta_simple(10000)),
        ("hostil: 10.000 '..'", ruta_solo_dotdot(10000)),
        ("hostil: 1.000.000 chars, 1 comp", ruta_larga_1comp(1000000)),
    ]
    filas = []
    crudo = {}
    for etiqueta, p in casos:
        t, _, _ = medir(lambda: guardian(p))
        acepta = guardian(p)
        filas.append([etiqueta, str(len(p)), fmt_t(t), "ACEPTA" if acepta else "RECHAZA"])
        crudo[etiqueta] = {"len": len(p), "seg": t, "acepta": acepta}
    log(tabla(["caso", "len(chars)", "coste guardian", "veredicto"], filas))
    log("")
    resultados["parte7"] = crudo


def main():
    resultados = {
        "meta": {
            "python": sys.version,
            "plataforma": platform.platform(),
            "os_name": os.name,
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cwd_salida": AQUI,
        },
        "parte1": {},
    }
    sel = set(sys.argv[1:]) or {"1", "2", "3", "4", "5", "6", "7"}
    t0 = time.perf_counter()
    try:
        if "1" in sel:
            parte1(resultados)
        if "2" in sel:
            parte2(resultados)
        if "3" in sel:
            parte3(resultados)
        if "4" in sel:
            parte4(resultados)
        if "5" in sel:
            parte5(resultados)
        if "6" in sel:
            parte6(resultados)
        if "7" in sel:
            parte7(resultados)
    finally:
        limpiar_linktmp()
        log("linktmp limpiado: %s" % (not os.path.isdir(LINKTMP)))
    resultados["meta"]["duracion_total_s"] = time.perf_counter() - t0
    log("Duracion total del banco: %.1f s" % resultados["meta"]["duracion_total_s"])

    with open(SALIDA_JSON, "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, indent=2, ensure_ascii=False)
    with open(SALIDA_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")
    print("\nEscrito: %s" % SALIDA_JSON)
    print("Escrito: %s" % SALIDA_TXT)


if __name__ == "__main__":
    main()
