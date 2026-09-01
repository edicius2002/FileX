#!/usr/bin/env python3
"""Comprobaciones de integridad del repositorio. Biblioteca estándar, sin
dependencias — la misma decisión que `pyproject.toml` toma para `filex`.

    python3 ci/integridad.py            # todas
    python3 ci/integridad.py --lista    # qué comprueba y por qué
    python3 ci/integridad.py citas      # sólo una

**Cada comprobación sale de un defecto REAL, encontrado a mano el 01/09.** No
hay ninguna inventada «por si acaso»: las ocho de este fichero son las ocho que
un barrido manual destapó, y el barrido costó una tarde. Ése es el punto —
encontrarlas a mano no escala, y el repositorio ya demostró que un defecto
documental sobrevive **nueve días** si nadie lo busca a propósito.

Dos severidades, y la diferencia importa:

- `FALLO`  rompe la CI. Es algo que hoy está bien y no puede empeorar.
- `AVISO`  informa y **no** rompe. Es algo que hoy ya está mal y cuyo arreglo
           es trabajo, no un `sed`. Un aviso que se queda en aviso para siempre
           es deuda que al menos está contada.

Poner en `FALLO` algo que ya falla deja la CI roja desde el primer día, y una
CI que siempre está roja no la mira nadie: es la trampa 51 —un umbral generoso
no es más seguro, es una regresión con mejor pinta— aplicada al propio arnés.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ESTADO = RAIZ / "ESTADO-Y-REPARTO.md"
CLAUDE = RAIZ / "CLAUDE.md"
LEEME = RAIZ / "README.md"

# Directorios que no son contenido del repositorio.
EXCLUIDOS = {".git", "repos", ".ccb", "node_modules", ".claude"}

VERDE, ROJO, AMBAR, GRIS, FIN = (
    ("\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m")
    if sys.stdout.isatty() and os.name != "nt" else ("", "", "", "", "")
)

_COMPROBACIONES = []


def comprobacion(nombre, porque, severidad="FALLO"):
    def envoltorio(f):
        _COMPROBACIONES.append((nombre, porque, severidad, f))
        return f
    return envoltorio


def _md():
    """Los .md VERSIONADOS, y sale de `git ls-files`, no de un `rglob`.

    Recorrer el árbol entero tarda minutos —`repos/` son clones y los venvs
    pesan gigas— y además metería en la comprobación ficheros que no son del
    repositorio. Lo que se comprueba es lo que se publica."""
    for rel in _git("ls-files", "-z", "*.md").stdout.split("\x00"):
        if not rel:
            continue
        if EXCLUIDOS & set(pathlib.PurePosixPath(rel).parts):
            continue
        p = RAIZ / rel
        if p.exists():
            yield p


def _git(*args):
    return subprocess.run(("git",) + args, cwd=RAIZ, capture_output=True,
                          text=True, errors="replace")


# --------------------------------------------------------------- trinquete --

HEREDADO = RAIZ / "ci" / "heredado.json"


def _heredado():
    import json
    if not HEREDADO.exists():
        return {}
    return json.loads(HEREDADO.read_text(encoding="utf-8"))


def _trinquete(clave, actuales, unidad):
    """Compara contra la deuda CONGELADA, no contra cero.

    El repositorio llega a la CI con deuda ya contraída: 10 binarios sueltos y
    20 directorios de salidas sin `MANIFIESTO.md`. Poner esas dos en `FALLO`
    contra cero deja la CI roja el primer día, y una CI siempre roja no la mira
    nadie —trampa 51: un umbral generoso no es más seguro, es una regresión con
    mejor pinta—. Pero dejarlas en `AVISO` para siempre es peor: la deuda deja
    de contarse y crece sin que nadie lo note.

    El trinquete hace las dos cosas y sólo aprieta:

    - lo que ya estaba **no rompe**, pero sale contado en cada pasada;
    - lo **NUEVO** rompe, siempre;
    - lo **ARREGLADO** rompe también, y pide encoger la lista. Sin esta tercera
      mitad el trinquete se afloja solo: alguien arregla un fichero, la lista
      sigue perdonándolo, y el hueco queda disponible para el siguiente.
    """
    base = set(_heredado().get(clave, []))
    actuales = set(actuales)
    nuevos = sorted(actuales - base)
    resueltos = sorted(base - actuales)

    problemas = []
    if nuevos:
        problemas += ["NUEVO: %s" % x for x in nuevos]
    if resueltos:
        problemas += ["ARREGLADO, quítalo de ci/heredado.json: %s" % x
                      for x in resueltos]
    detalle = "%d %s heredados · %d nuevos · %d arreglados" % (
        len(actuales & base), unidad, len(nuevos), len(resueltos))
    return not problemas, detalle, problemas


# ---------------------------------------------------------------- 1. citas --

def _ajenas():
    """Hashes que NO son de este repositorio y por eso no tienen que resolver."""
    f = RAIZ / "ci" / "citas-ajenas.txt"
    fuera = {}
    if f.exists():
        for linea in f.read_text(encoding="utf-8").splitlines():
            linea = linea.split("#")[0].strip()
            if linea:
                partes = linea.split(None, 1)
                fuera[partes[0].lower()] = partes[1] if len(partes) > 1 else ""
    return fuera


@comprobacion(
    "citas",
    "El filter-repo del 31/08 mató 16 citas de hash en 9 ficheros y NO hubo un "
    "solo error: un hash muerto se lee igual que uno vivo.",
)
def citas():
    patron = re.compile(r"(?:commit|revisi[oó]n)e?s? +`([0-9a-f]{7,40})`", re.I)
    ajenas = _ajenas()
    muertas, vivas, saltadas = [], 0, 0
    for p in _md():
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for h in patron.findall(linea):
                if h.lower() in ajenas:
                    saltadas += 1
                    continue
                if _git("cat-file", "-e", h).returncode == 0:
                    vivas += 1
                else:
                    muertas.append("%s:%d  `%s`" % (p.relative_to(RAIZ), n, h))
    detalle = "%d vivas · %d ajenas declaradas · %d muertas" % (
        vivas, saltadas, len(muertas))
    return not muertas, detalle, muertas


# ----------------------------------------------------------- 2. inventario --

_FILA = re.compile(r"^\| (~~)?\*\*[ABCN][0-9]+")


def _seccion_3():
    dentro, filas = False, []
    for linea in ESTADO.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## 3. Inventario"):
            dentro = True
            continue
        if linea.startswith("## 4. El reparto"):
            break
        if dentro:
            filas.append(linea)
    return filas


@comprobacion(
    "inventario",
    "El recuento declarado en §3 y el que da el grep tienen que coincidir. La "
    "línea estuvo TRES DÍAS diciendo 95 filas con la leyenda diciendo 107.",
)
def inventario():
    filas = [l for l in _seccion_3() if _FILA.match(l)]
    cuenta = {e: 0 for e in "🔴🟡🟢⚫"}
    for l in filas:
        for e in re.findall(r"🔴|🟡|🟢|⚫", l):
            cuenta[e] += 1
    medido = "%d ⚫ · %d 🔴 · %d 🟡 · %d 🟢" % (
        cuenta["⚫"], cuenta["🔴"], cuenta["🟡"], cuenta["🟢"])

    texto = ESTADO.read_text(encoding="utf-8")
    m = re.search(r"Salida esperada hoy: `([^`]+)` sobre \*\*(\d+)\*\* filas", texto)
    if not m:
        return False, "no encuentro la línea «Salida esperada hoy»", []
    declarado, filas_declaradas = m.group(1), int(m.group(2))

    problemas = []
    if declarado != medido:
        problemas.append("declara `%s` y mide `%s`" % (declarado, medido))
    if filas_declaradas != len(filas):
        problemas.append("declara %d filas y hay %d" % (filas_declaradas, len(filas)))
    return not problemas, "%s sobre %d filas" % (medido, len(filas)), problemas


@comprobacion(
    "un-emoji-por-fila",
    "Una fila = un identificador = exactamente un emoji de estado. Sin esto el "
    "grep no significa nada, que es como estaba antes del barrido del 23/08.",
)
def un_emoji_por_fila():
    malas = []
    for l in [l for l in _seccion_3() if _FILA.match(l)]:
        n = len(re.findall(r"🔴|🟡|🟢|⚫", l))
        if n != 1:
            malas.append("%d emojis: %s" % (n, l[:110]))
    return not malas, "%d filas, todas con un emoji" % len(
        [l for l in _seccion_3() if _FILA.match(l)]), malas


# -------------------------------------------------------------- 3. trampas --

@comprobacion(
    "trampas",
    "El número de trampas se cita en tres sitios. §10 de ESTADO decía 24 con "
    "102 en el fichero: setenta y ocho de desfase, y nadie lo vio.",
)
def trampas():
    numeros = [int(m) for m in re.findall(r"^(\d+)\. ", CLAUDE.read_text(encoding="utf-8"),
                                          re.M)]
    if not numeros:
        return False, "no encuentro trampas numeradas en CLAUDE.md", []
    ultima = max(numeros)
    problemas = []

    # Las trampas se numeran sin huecos y sin repetir: renumerar desplaza citas
    # de ocho documentos, y este fichero ya lo pagó una vez el 22/08.
    faltan = sorted(set(range(1, ultima + 1)) - set(numeros))
    repes = sorted({n for n in numeros if numeros.count(n) > 1})
    if faltan:
        problemas.append("huecos en la numeración: %s" % faltan)
    if repes:
        problemas.append("números repetidos: %s" % repes)

    for fichero in (LEEME, ESTADO):
        for citado in re.findall(r"las \*\*(\d+)\*\* trampas|las (\d+) trampas",
                                 fichero.read_text(encoding="utf-8")):
            n = int(citado[0] or citado[1])
            if n != ultima:
                problemas.append("%s cita %d trampas y hay %d"
                                 % (fichero.name, n, ultima))
    return not problemas, "%d trampas, sin huecos" % ultima, problemas


# ------------------------------------------------------------- 4. informes --

@comprobacion(
    "informes-registrados",
    "Siete informes no figuraban en la tabla de §1, entre ellos el resultado de "
    "la ronda 2. Un inventario que no registra el trabajo hecho hace que el "
    "proyecto se planifique como si no existiera.",
)
def informes_registrados():
    texto = ESTADO.read_text(encoding="utf-8")
    fuera = [p.name for p in sorted((RAIZ / "bench").glob("*.md"))
             if p.name not in texto]
    return not fuera, "%d informes, todos citados" % len(
        list((RAIZ / "bench").glob("*.md"))), fuera


@comprobacion(
    "manifiestos",
    "Regla §6: si generas salidas, borra las grandes y deja un MANIFIESTO.md "
    "con la orden exacta que las reproduce. Sin él, un activo podado parece un "
    "bloqueo — la trampa 95, que es más cara que un falso rojo.",
)
def manifiestos():
    sin = [str(d.relative_to(RAIZ)).replace("\\", "/")
           for d in sorted((RAIZ / "bench").glob("salidas-*"))
           if d.is_dir() and not (d / "MANIFIESTO.md").exists()]
    return _trinquete("manifiestos", sin, "sin MANIFIESTO")


# ---------------------------------------------------------------- 5. peso ---

@comprobacion(
    "secretos",
    "Borrar el historial no borra el residuo de la herramienta que lo borró: "
    "fast-export.original conservaba las 48 ocurrencias de la credencial "
    "dentro de .git. Trampa 102.",
)
def secretos():
    patrones = [re.compile(p) for p in (
        r"FileXBench\w+",
        r"(?i)(password|contrase[nñ]a|token|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}",
    )]
    # Lo que el propio repositorio declara como redactado no es un secreto.
    permitido = re.compile(r"REDACTADA|<secreto>|xxx|CAMBIAME|\.\.\.")
    hallazgos = []
    r = _git("ls-files", "-z")
    for rel in r.stdout.split("\0"):
        if not rel or rel.endswith((".png", ".jpg", ".pdf", ".gif", ".zip")):
            continue
        p = RAIZ / rel
        try:
            texto = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            if permitido.search(linea):
                continue
            for pat in patrones:
                if pat.search(linea):
                    hallazgos.append("%s:%d" % (rel, n))
                    break
    return not hallazgos, "%d hallazgos" % len(hallazgos), hallazgos[:20]


@comprobacion(
    "binarios",
    "El repositorio ya pagó una vez este error: 986 MB de pack, 99,9 % binario. "
    "Las salidas regenerables no se versionan; el corpus va en LFS.",
)
def binarios():
    TOPE = 512 * 1024
    lfs = set()
    r = _git("lfs", "ls-files", "-n")
    if r.returncode == 0:
        lfs = {l.strip() for l in r.stdout.splitlines() if l.strip()}
    gordos = []
    for rel in _git("ls-files", "-z").stdout.split("\0"):
        if not rel or rel in lfs:
            continue
        p = RAIZ / rel
        try:
            if p.stat().st_size > TOPE and b"\0" in p.open("rb").read(8192):
                gordos.append(rel)
        except OSError:
            continue
    return _trinquete("binarios", gordos, "binarios sueltos")


# ---------------------------------------------------------------- 6. curso --

@comprobacion(
    "en-curso",
    "Tres cabeceras seguían diciendo «en curso», y la nota «hay un agente "
    "escribiéndolo ahora» de phys-multimotor.md sobrevivió NUEVE DÍAS al "
    "agente. Trampa 44: una nota falsa al lado de un campo honesto.",
    severidad="AVISO",
)
def en_curso():
    patron = re.compile(r"(?i)^#{2,4} .*(en curso|EN CURSO)")
    abiertas = []
    for p in _md():
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if patron.match(linea):
                abiertas.append("%s:%d  %s" % (p.relative_to(RAIZ), n, linea[:80]))
    return not abiertas, "%d cabeceras «en curso»" % len(abiertas), abiertas


# ------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("solo", nargs="*", help="nombres de comprobación a ejecutar")
    ap.add_argument("--lista", action="store_true", help="qué comprueba y por qué")
    args = ap.parse_args()

    if args.lista:
        for nombre, porque, sev, _ in _COMPROBACIONES:
            print("%s%-22s%s [%s]\n    %s\n" % (VERDE, nombre, FIN, sev, porque))
        return 0

    pendientes = [c for c in _COMPROBACIONES
                  if not args.solo or c[0] in args.solo]
    if args.solo and not pendientes:
        print("no hay ninguna comprobación llamada %s" % args.solo, file=sys.stderr)
        return 2

    rotas, avisadas = [], []
    for nombre, _porque, severidad, f in pendientes:
        try:
            ok, detalle, problemas = f()
        except Exception as e:                                   # noqa: BLE001
            ok, detalle, problemas = False, "la comprobación reventó", [repr(e)]
        if ok:
            print("%s  OK  %s%-22s%s %s" % (VERDE, FIN, nombre, GRIS, detalle) + FIN)
        else:
            marca, color = ((" AVISO", AMBAR) if severidad == "AVISO"
                            else ("  MAL ", ROJO))
            print("%s%s%s %-22s %s" % (color, marca, FIN, nombre, detalle))
            for x in problemas[:12]:
                print("        %s%s%s" % (GRIS, x, FIN))
            if len(problemas) > 12:
                print("        %s… y %d más%s" % (GRIS, len(problemas) - 12, FIN))
            (avisadas if severidad == "AVISO" else rotas).append(nombre)

    print()
    if rotas:
        print("%sFALLA:%s %s" % (ROJO, FIN, ", ".join(rotas)))
    if avisadas:
        print("%sAVISA:%s %s  (no rompe la CI: es deuda contada, no regresión)"
              % (AMBAR, FIN, ", ".join(avisadas)))
    if not rotas and not avisadas:
        print("%sTodo en orden.%s" % (VERDE, FIN))
    return 1 if rotas else 0


if __name__ == "__main__":
    sys.exit(main())
