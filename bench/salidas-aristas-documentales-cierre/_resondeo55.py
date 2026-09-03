# -*- coding: utf-8 -*-
"""worker7 — RESONDEO real de las 55 aristas `real` de `doc_libreoffice` y
`doc_pandoc` tras declarar las 15 nuevas de `bench/aristas-documentales-cierre.md`.

**Por qué existe este fichero y no se reutiliza `_sonda23.py` de S3 tocándolo**:
`CLAUDE.md` §1 pide copiar el arnés ajeno al propio directorio de salidas, no
editarlo — `bench/salidas-sondeo-doc/_sonda23.py` no es de este carril. La
mecánica de forzar la arista (`convertir_forzando`, `busca_arista`,
`DirTrabajoEspia`) y las funciones de lectura de texto (`texto_de`, `sha`) son
una copia literal de ese fichero, que a su vez las copió de `bench/salidas-
hito5/_sonda.py` (K1) por el mismo motivo.

**La conversión la hace el NÚCLEO, no este arnés**: cada caso llama a
`filex.nucleo.FileX.convertir()` de verdad — motor.orden(), invocacion.ejecutar()
con Docker real, contrato.verificar() de cinco puntos y el censo del punto 5 —
y solo se sustituye `fx.planificar` por una `Decision` de un solo paso para que
el grafo no resuelva el par por otro camino ni por otro motor.

**Por qué se resondean también las 40 aristas que ya eran `REAL` antes de esta
ronda** (no solo las 15 nuevas): añadir tuplas a `_DECLARADAS` cambia el AST de
la clase y CADUCA su huella (trampa 32/61 de `CLAUDE.md`). Antes de aceptar
un resello hay que demostrar que el código que decide cada arista sigue dando
el mismo resultado — no basta con argumentar que `_cmd()` no cambió: se mide.

    python bench/salidas-aristas-documentales-cierre/_resondeo55.py [--solo motor:o>d,...]

Salida: `bench/salidas-aristas-documentales-cierre/resondeo55.json` y los
ficheros producidos en `.../out/` (se listan en MANIFIESTO.md y no se
versionan; la orden de arriba los reproduce).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import invocacion  # noqa: E402
from filex import nucleo as _nucleo  # noqa: E402
from filex.grafo import Camino, Decision, Paso  # noqa: E402
from filex.nucleo import FileX  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

SAL = os.path.dirname(os.path.abspath(__file__))
ENT_K1 = os.path.join(RAIZ, "bench", "salidas-hito5", "entradas")
ENT_S3 = os.path.join(RAIZ, "bench", "salidas-sondeo-doc", "entradas")
ENT_MIO = os.path.join(SAL, "entradas")

CENTINELA = "FILEXSENTINELA7743"

#: Igual que `_sonda23.py` de S3: el de dentro dispara a los 90 s (margen ×4,4
#: sobre la arista mas lenta medida, Calibre epub->pdf en 20,6 s).
TIMEOUT = 100.0

#: Tope de lo que el espia copia; un `soffice` colgado escribe cientos de MB.
TOPE_ESPIA = 20 * 1024 * 1024


class DirTrabajoEspia(DirectorioDeTrabajo):
    """El desechable del nucleo, con una copia ANTES de borrarse.

    Copia literal de `bench/salidas-sondeo-doc/_sonda23.py` (S3).
    """

    guardar_en: str | None = None

    def cerrar(self) -> None:
        destino = DirTrabajoEspia.guardar_en
        if destino:
            try:
                os.makedirs(destino, exist_ok=True)
                for n in sorted(os.listdir(self.ruta)):
                    p = os.path.join(self.ruta, n)
                    if not os.path.isfile(p):
                        continue
                    if os.path.getsize(p) > TOPE_ESPIA:
                        with open(os.path.join(destino, n + ".GRANDE.txt"), "w") as f:
                            f.write(f"{os.path.getsize(p)} bytes, no copiado\n")
                        continue
                    shutil.copy2(p, os.path.join(destino, n))
            except Exception:
                pass
        super().cerrar()


# ------------------------------------------------------------ recuperar texto
# (copia literal de bench/salidas-sondeo-doc/_sonda23.py, que a su vez copia
# bench/salidas-hito5/_sonda.py — K1)


def _limpia(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def texto_de(ruta: str) -> str:
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    try:
        if ext == "pdf":
            with DirectorioDeTrabajo() as t:
                dst = t.destino("t.txt")
                r = invocacion.ejecutar(
                    ["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                     "-sDEVICE=txtwrite", f"-sOutputFile={dst}", ruta], timeout=90)
                if not r.ok or not os.path.isfile(dst):
                    return ""
                return _limpia(open(dst, encoding="utf-8", errors="replace").read())
        if ext in ("docx", "odt", "epub", "azw3", "mobi", "xlsx", "pptx", "odp",
                   "ods"):
            if not zipfile.is_zipfile(ruta):
                d = open(ruta, "rb").read()
                return _limpia(d.decode("latin-1", "replace"))
            out = []
            with zipfile.ZipFile(ruta) as z:
                for n in z.namelist():
                    if n.lower().endswith((".xml", ".html", ".xhtml", ".htm")):
                        try:
                            out.append(re.sub(r"<[^>]+>", " ",
                                              z.read(n).decode("utf-8", "replace")))
                        except Exception:
                            pass
            return _limpia(" ".join(out))
        if ext in ("html", "htm", "xhtml"):
            return _limpia(re.sub(r"<[^>]+>", " ",
                                  open(ruta, encoding="utf-8", errors="replace").read()))
        if ext in ("md", "txt", "rtf", "tex", "csv"):
            return _limpia(open(ruta, encoding="utf-8", errors="replace").read())
    except Exception:
        return ""
    return ""


def sha(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------- entradas


def entrada_de(ext: str) -> str:
    """La semilla para un formato. Primero la propia (generada), luego S3, luego K1."""
    for base in (ENT_MIO, ENT_S3, ENT_K1):
        a = os.path.join(base, f"entrada.{ext}")
        if os.path.isfile(a):
            return a
    return os.path.join(ENT_MIO, f"entrada.{ext}")


# -------------------------------------------------------------- forzar arista


def busca_arista(fx: FileX, motor: str, o: str, d: str):
    for a in fx.grafo.aristas:
        if a.motor == motor and a.origen == o and a.destino == d:
            return a
    return None


def convertir_forzando(fx: FileX, arista, entrada: str, salida: str,
                       espia: str | None = None):
    """`FileX.convertir()` con el camino fijado a UNA arista. Copia de S3."""
    dec = Decision(camino=Camino(pasos=[Paso(arista)], coste=arista.coste))
    original = fx.planificar
    fx.planificar = lambda e, s, _d=dec: _d
    clase = _nucleo.DirectorioDeTrabajo
    _nucleo.DirectorioDeTrabajo = DirTrabajoEspia
    DirTrabajoEspia.guardar_en = espia
    try:
        return fx.convertir(entrada, salida, timeout=TIMEOUT)
    finally:
        fx.planificar = original
        _nucleo.DirectorioDeTrabajo = clase
        DirTrabajoEspia.guardar_en = None


def registro(conv, cid: str, motor: str, o: str, d: str, salida: str,
             espia: str | None = None) -> dict:
    reg = {"id": cid, "motor": motor, "origen": o, "destino": d,
           "ok": conv.ok, "veredicto": conv.veredicto, "motivo": conv.motivo}
    s = conv.saltos[0] if conv.saltos else None
    if s is not None:
        reg["rc"] = s.rc
        reg["ms"] = round(s.ms, 1)
        reg["contrato"] = s.veredicto
        reg["cobertura"] = s.cobertura
        reg["sobrantes"] = s.sobrantes
        reg["motivo_salto"] = s.motivo
        reg["err_cola"] = (s.err or "").strip()[-200:]
        reg["hallazgos"] = [{"regla": h.get("regla"), "sev": h.get("severidad"),
                             "msg": h.get("mensaje")} for h in (s.hallazgos or [])]
    else:
        reg["rc"] = None
    ruta = salida if os.path.isfile(salida) else ""
    reg["recogida"] = bool(ruta)
    if not ruta and espia:
        cand = os.path.join(espia, f"salida.{d}")
        if os.path.isfile(cand):
            ruta = cand
    if ruta:
        reg["bytes"] = os.path.getsize(ruta)
        reg["sha256"] = sha(ruta)
        txt = texto_de(ruta)
        reg["caracteres"] = len(txt)
        reg["centinela"] = CENTINELA in txt
        reg["tabla_ax1"] = "AX-1" in txt
    else:
        reg["bytes"] = 0
        reg["caracteres"] = 0
        reg["centinela"] = False
        reg["tabla_ax1"] = False
    if espia and os.path.isdir(espia):
        reg["espia"] = {n: os.path.getsize(os.path.join(espia, n))
                        for n in sorted(os.listdir(espia))
                        if os.path.isfile(os.path.join(espia, n))}
    return reg


# --------------------------------------------------------------- los 55 casos
#
# Orden: primero las dos semillas que fabrican `entrada.xlsx` y `entrada.pptx`
# (ellas mismas son aristas de pleno derecho: R01=csv->xlsx, R25=md->pptx), y
# el resto en el orden del diff de `bench/sondeo-documental.md` §7.3, motor por
# motor, MEDIDAS antes que DECLARADAS.

CASOS = [
    # --- semillas: producen entrada.xlsx y entrada.pptx ---------------------
    ("R01", "doc_libreoffice", "csv", "xlsx"),
    ("R02", "doc_pandoc", "md", "pptx"),

    # --- doc_libreoffice: 10 ya `_MEDIDAS` (K1) ------------------------------
    ("R03", "doc_libreoffice", "docx", "html"),
    ("R04", "doc_libreoffice", "docx", "odt"),
    ("R05", "doc_libreoffice", "docx", "pdf"),
    ("R06", "doc_libreoffice", "docx", "png"),
    ("R07", "doc_libreoffice", "html", "pdf"),
    ("R08", "doc_libreoffice", "odt", "docx"),
    ("R09", "doc_libreoffice", "odt", "pdf"),
    ("R10", "doc_libreoffice", "odt", "txt"),
    ("R11", "doc_libreoffice", "rtf", "pdf"),
    ("R12", "doc_libreoffice", "txt", "pdf"),

    # --- doc_libreoffice: 6 ya `_DECLARADAS` (existían antes de esta ronda) --
    ("R13", "doc_libreoffice", "rtf", "odt"),
    ("R14", "doc_libreoffice", "rtf", "docx"),
    ("R15", "doc_libreoffice", "html", "odt"),
    ("R16", "doc_libreoffice", "txt", "odt"),
    ("R17", "doc_libreoffice", "odt", "html"),
    ("R18", "doc_libreoffice", "docx", "rtf"),

    # --- doc_libreoffice: 8 NUEVAS de esta ronda (7 explícitas + svg->pdf) ---
    ("R19", "doc_libreoffice", "xlsx", "pdf"),
    ("R20", "doc_libreoffice", "xlsx", "csv"),
    ("R21", "doc_libreoffice", "xlsx", "html"),
    ("R22", "doc_libreoffice", "csv", "pdf"),
    ("R23", "doc_libreoffice", "pptx", "pdf"),
    ("R24", "doc_libreoffice", "pptx", "odp"),
    ("R33", "doc_libreoffice", "svg", "pdf"),

    # --- doc_pandoc: 15 ya `_MEDIDAS` (K1) -----------------------------------
    ("R26", "doc_pandoc", "docx", "epub"),
    ("R27", "doc_pandoc", "docx", "html"),
    ("R28", "doc_pandoc", "docx", "md"),
    ("R29", "doc_pandoc", "docx", "pdf"),
    ("R30", "doc_pandoc", "docx", "rtf"),
    ("R31", "doc_pandoc", "epub", "html"),
    ("R32", "doc_pandoc", "epub", "md"),
    ("R34", "doc_pandoc", "html", "docx"),
    ("R35", "doc_pandoc", "html", "md"),
    ("R36", "doc_pandoc", "md", "docx"),
    ("R37", "doc_pandoc", "md", "epub"),
    ("R38", "doc_pandoc", "md", "html"),
    ("R39", "doc_pandoc", "md", "odt"),
    ("R40", "doc_pandoc", "md", "pdf"),
    ("R41", "doc_pandoc", "md", "txt"),

    # --- doc_pandoc: 9 ya `_DECLARADAS` (existían antes de esta ronda) -------
    ("R42", "doc_pandoc", "html", "epub"),
    ("R43", "doc_pandoc", "html", "odt"),
    ("R44", "doc_pandoc", "html", "rtf"),
    ("R45", "doc_pandoc", "docx", "odt"),
    ("R46", "doc_pandoc", "epub", "docx"),
    ("R47", "doc_pandoc", "epub", "txt"),
    ("R48", "doc_pandoc", "rtf", "md"),
    ("R49", "doc_pandoc", "rtf", "html"),
    ("R50", "doc_pandoc", "md", "rtf"),

    # --- doc_pandoc: 7 NUEVAS de esta ronda -----------------------------------
    ("R51", "doc_pandoc", "md", "tex"),
    ("R52", "doc_pandoc", "docx", "tex"),
    ("R53", "doc_pandoc", "tex", "docx"),
    ("R54", "doc_pandoc", "tex", "html"),
    ("R55", "doc_pandoc", "tex", "pdf"),
    ("R56", "doc_pandoc", "pptx", "md"),
]

#: (motor, o, d) -> extensión de la semilla que produce, para copiarla a
#: ENT_MIO tras convertir. Solo R01 y R02 fabrican semillas nuevas.
SEMILLA_DE = {("doc_libreoffice", "csv", "xlsx"): "xlsx",
              ("doc_pandoc", "md", "pptx"): "pptx"}


def contenedores() -> list[str]:
    r = invocacion.ejecutar(
        ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"],
        timeout=45)
    return [x for x in (r.salida_txt or "").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--salida", default=os.path.join(SAL, "resondeo55.json"))
    ap.add_argument("--out", default=os.path.join(SAL, "out"))
    a = ap.parse_args()

    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(ENT_MIO, exist_ok=True)

    antes = contenedores()
    print(f"contenedores vivos ANTES: {len(antes)}")
    for c in antes:
        print("   ", c)

    fx = FileX()
    builds = {m.nombre: m.build for m in fx.disponibles if m.nombre.startswith("doc_")}
    if not builds:
        print("NO hay motores documentales disponibles; nada que sondear")
        return 2
    print("builds:", builds)

    solo = {x.strip() for x in a.solo.split(",") if x.strip()}
    casos = [c for c in CASOS
             if not solo or c[0] in solo or f"{c[1]}:{c[2]}>{c[3]}" in solo]

    previos = {}
    if os.path.isfile(a.salida):
        try:
            with open(a.salida, encoding="utf-8") as f:
                previos = {x["id"]: x for x in (json.load(f).get("casos") or [])}
        except Exception:
            previos = {}

    res = [previos[k] for k in sorted(previos)]
    t0 = time.time()
    for cid, motor, o, d in casos:
        ar = busca_arista(fx, motor, o, d)
        if ar is None:
            previos[cid] = {"id": cid, "motor": motor, "origen": o, "destino": d,
                            "rc": None, "motivo": "la arista no esta en el grafo"}
            res = [previos[k] for k in sorted(previos)]
            print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} SIN ARISTA EN EL GRAFO")
            continue
        ent = entrada_de(o)
        if not os.path.isfile(ent):
            previos[cid] = {"id": cid, "motor": motor, "origen": o, "destino": d,
                            "rc": None, "motivo": f"falta la semilla entrada.{o}"}
            res = [previos[k] for k in sorted(previos)]
            print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} FALTA SEMILLA entrada.{o}")
            continue
        salida = os.path.join(a.out, f"{cid}_{motor[4:]}_{o}2{d}.{d}")
        espia = os.path.join(a.out, f"{cid}_desechable")
        conv = convertir_forzando(fx, ar, ent, salida, espia=espia)
        reg = registro(conv, cid, motor, o, d, salida, espia=espia)
        reg["build"] = builds.get(motor, "")
        reg["estado_arista_antes"] = ar.estado
        previos[cid] = reg
        res = [previos[k] for k in sorted(previos)]
        print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} rc={reg.get('rc')} "
              f"{reg.get('ms', 0):>8.0f} ms {reg.get('bytes', 0):>9} B  "
              f"car={reg.get('caracteres', 0):>6} "
              f"cent={'S' if reg.get('centinela') else 'n'} "
              f"contrato={reg.get('contrato', '-'):<10} "
              f"sobra={len(reg.get('sobrantes') or {})}", flush=True)
        with open(a.salida, "w", encoding="utf-8") as f:
            json.dump({"casos": res}, f, ensure_ascii=False, indent=1)

        semilla_ext = SEMILLA_DE.get((motor, o, d))
        if semilla_ext and os.path.isfile(salida):
            dst = os.path.join(ENT_MIO, f"entrada.{semilla_ext}")
            shutil.copy2(salida, dst)
            print(f"     semilla guardada: {dst} ({os.path.getsize(dst)} B)")

    print(f"\ntotal {time.time() - t0:.1f} s")

    despues = contenedores()
    print(f"contenedores vivos DESPUES: {len(despues)}")
    for c in despues:
        print("   ", c)
    nuevos = [c for c in despues if c.split("|")[0] not in {x.split("|")[0] for x in antes}]
    print(f"contenedores NUEVOS vivos: {len(nuevos)}")
    for c in nuevos:
        print("   !", c)

    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump({"casos": res,
                   "contenedores_antes": antes,
                   "contenedores_despues": despues,
                   "contenedores_nuevos_vivos": nuevos,
                   "builds": builds,
                   "timeout_fuera_s": TIMEOUT}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
