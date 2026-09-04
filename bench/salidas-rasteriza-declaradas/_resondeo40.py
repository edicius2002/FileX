# -*- coding: utf-8 -*-
"""worker14 — RESONDEO real de las 40 aristas que `filex/sondeo/*.json` cubre
para los tres motores documentales, tras convertir `_DECLARADAS` en un `dict`
`{(o, d): rasteriza}` y meter `pptx→png` y `svg→png` con `rasteriza=True`.

**Por qué 40 y no 55 ni 73.** Lo que el cambio CADUCA es exactamente lo que los
tres ficheros de sondeo aplican: 16 entradas de `doc_libreoffice`, 16 de
`doc_pandoc` y 8 de `doc_calibre`. Las `_MEDIDAS` nacen `REAL` en `_aristas()`
sin pasar por `sondeo.aplicar()`, así que ninguna huella las gobierna y
remedirlas no cierra ninguna deuda — worker7 las remidió de más, y decirlo es
más honesto que copiar su alcance sin pensarlo. Las 8 de Calibre, en cambio,
NADIE las había remedido en la ronda anterior y aquí sí entran.

**Y mide una segunda cosa que ningún resondeo anterior medía: si la arista
RASTERIZA.** El criterio no es «el motor sabe escribir un PNG» —eso es el hecho
por la causa, trampa 58— sino **si el texto de la entrada sobrevive en la
salida**. Se decide con el centinela y el recuento de caracteres, con el umbral
≥10 de la trampa 4 (`txtwrite` emite 1-3 caracteres de basura en un PDF sin
texto). Para `mobi`/`azw3` la sonda es CIEGA (comprimen el texto) y se declara
como tal en vez de concluir.

**Por qué este fichero y no se reutiliza `_resondeo55.py` de worker7**:
`CLAUDE.md` §1 pide copiar el arnés ajeno al propio directorio de salidas, no
editarlo. La mecánica de forzar la arista (`convertir_forzando`, `busca_arista`,
`DirTrabajoEspia`) y las de lectura de texto (`texto_de`, `sha`) son copia
literal de `bench/salidas-aristas-documentales-cierre/_resondeo55.py`, que a su
vez las copió de `bench/salidas-sondeo-doc/_sonda23.py` y éste de
`bench/salidas-hito5/_sonda.py`.

**La conversión la hace el NÚCLEO**: cada caso llama a
`filex.nucleo.FileX.convertir()` de verdad —`motor.orden()`,
`invocacion.ejecutar()` con Docker real, `contrato.verificar()` de cinco puntos
y el censo del punto 5— y solo se sustituye `fx.planificar` por una `Decision`
de un salto para que el grafo no resuelva el par por otro camino ni otro motor.

    python bench/salidas-rasteriza-declaradas/_resondeo40.py [--solo id,...]

Salida: `resondeo40.json` y los ficheros de `out/` (no se versionan; el
MANIFIESTO lleva la orden que los reproduce).
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

#: El de dentro dispara a los 90 s (margen ×7 sobre la arista más lenta medida,
#: Calibre `mobi→pdf` en 12,5 s).
TIMEOUT = 100.0

#: Tope de lo que el espía copia; un `soffice` colgado escribe cientos de MB.
TOPE_ESPIA = 20 * 1024 * 1024

#: Trampa 4: `txtwrite` emite 1-3 caracteres de basura en un PDF sin texto, así
#: que «conserva texto» es **≥10 caracteres**, no >0.
UMBRAL_TEXTO = 10

#: Formatos cuya sonda de texto es CIEGA: comprimen el texto (PalmDoc/LZ77), y
#: un `centinela=False` en ellos NO significa que se haya perdido.
SONDA_CIEGA = ("mobi", "azw3")


class DirTrabajoEspia(DirectorioDeTrabajo):
    """El desechable del núcleo, con una copia ANTES de borrarse."""

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


def veredicto_rasteriza(destino: str, caracteres: int, centinela: bool) -> str:
    """`si` / `no` / `ciego`. **El criterio es el TEXTO, no el formato.**

    Una arista rasteriza si el texto de la entrada —que lleva el centinela— no
    sobrevive en la salida. Eso cubre los dos casos de la misma familia: el
    destino que no puede llevar texto (`png`) y el destino que sí puede y aun
    así llegó sin él, que es el fallo de `resvg` y el que nadie ve.
    """
    if destino in SONDA_CIEGA:
        return "ciego"
    return "no" if (centinela and caracteres >= UMBRAL_TEXTO) else "si"


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
    else:
        reg["bytes"] = 0
        reg["caracteres"] = 0
        reg["centinela"] = False
    reg["sonda_texto_ciega"] = d in SONDA_CIEGA
    reg["rasteriza_medido"] = veredicto_rasteriza(
        d, reg["caracteres"], reg["centinela"])
    if espia and os.path.isdir(espia):
        reg["espia"] = {n: os.path.getsize(os.path.join(espia, n))
                        for n in sorted(os.listdir(espia))
                        if os.path.isfile(os.path.join(espia, n))}
    return reg


# ------------------------------------------------------------- los 40 casos
#
# Son EXACTAMENTE las claves de los tres `filex/sondeo/doc_*.json`, que es lo
# que el cambio caduca. Primero las semillas que fabrican `entrada.xlsx`,
# `entrada.pptx`, `entrada.mobi` y `entrada.azw3`.

CASOS = [
    # --- doc_libreoffice: 14 que ya estaban en `_DECLARADAS` -----------------
    ("W01", "doc_libreoffice", "csv", "xlsx"),      # fabrica entrada.xlsx
    ("W02", "doc_libreoffice", "rtf", "odt"),
    ("W03", "doc_libreoffice", "rtf", "docx"),
    ("W04", "doc_libreoffice", "html", "odt"),
    ("W05", "doc_libreoffice", "txt", "odt"),
    ("W06", "doc_libreoffice", "odt", "html"),
    ("W07", "doc_libreoffice", "docx", "rtf"),
    ("W08", "doc_libreoffice", "xlsx", "pdf"),
    ("W09", "doc_libreoffice", "xlsx", "csv"),
    ("W10", "doc_libreoffice", "xlsx", "html"),
    ("W11", "doc_libreoffice", "csv", "pdf"),
    ("W12", "doc_libreoffice", "pptx", "pdf"),
    ("W13", "doc_libreoffice", "pptx", "odp"),
    ("W14", "doc_libreoffice", "svg", "pdf"),
    # --- doc_libreoffice: las DOS NUEVAS, las que rasterizan ----------------
    ("W15", "doc_libreoffice", "pptx", "png"),
    ("W16", "doc_libreoffice", "svg", "png"),

    # --- doc_pandoc: las 16 de `_DECLARADAS` --------------------------------
    ("W17", "doc_pandoc", "md", "pptx"),           # fabrica entrada.pptx
    ("W18", "doc_pandoc", "html", "epub"),
    ("W19", "doc_pandoc", "html", "odt"),
    ("W20", "doc_pandoc", "html", "rtf"),
    ("W21", "doc_pandoc", "docx", "odt"),
    ("W22", "doc_pandoc", "epub", "docx"),
    ("W23", "doc_pandoc", "epub", "txt"),
    ("W24", "doc_pandoc", "rtf", "md"),
    ("W25", "doc_pandoc", "rtf", "html"),
    ("W26", "doc_pandoc", "md", "rtf"),
    ("W27", "doc_pandoc", "md", "tex"),
    ("W28", "doc_pandoc", "docx", "tex"),
    ("W29", "doc_pandoc", "tex", "docx"),
    ("W30", "doc_pandoc", "tex", "html"),
    ("W31", "doc_pandoc", "tex", "pdf"),
    ("W32", "doc_pandoc", "pptx", "md"),

    # --- doc_calibre: las 8 de `_DECLARADAS`; NADIE las remidió en la ronda 12
    ("W33", "doc_calibre", "mobi", "epub"),
    ("W34", "doc_calibre", "azw3", "epub"),
    ("W35", "doc_calibre", "mobi", "pdf"),
    ("W36", "doc_calibre", "azw3", "pdf"),
    ("W37", "doc_calibre", "txt", "epub"),
    ("W38", "doc_calibre", "md", "epub"),
    ("W39", "doc_calibre", "epub", "epub"),
    ("W40", "doc_calibre", "mobi", "azw3"),
]

#: Casos que además dejan una semilla para los siguientes.
SEMILLA_DE = {("doc_libreoffice", "csv", "xlsx"): "xlsx",
              ("doc_pandoc", "md", "pptx"): "pptx"}

#: Semillas que hay que fabricar ANTES de nada, con aristas `_MEDIDAS` reales
#: (C03 y C04). El orden importa: `entrada.pptx` la fabrica W17 y la consumen
#: W12/W13/W15, así que los casos de pandoc van antes que esos tres en la
#: reordenación de `main()`.
SEMILLAS_PREVIAS = (("doc_calibre", "epub", "mobi"),
                    ("doc_calibre", "epub", "azw3"))


def contenedores(todos: bool = False) -> list[str]:
    """Trampa 37: `docker ps` NO lista el estado `Created`. Se cuentan los
    huérfanos con `docker ps -a`, y se declaran los dos recuentos."""
    argv = ["docker", "ps"] + (["-a"] if todos else [])
    r = invocacion.ejecutar(
        argv + ["--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"], timeout=45)
    return [x for x in (r.salida_txt or "").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--salida", default=os.path.join(SAL, "resondeo40.json"))
    ap.add_argument("--out", default=os.path.join(SAL, "out"))
    a = ap.parse_args()

    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(ENT_MIO, exist_ok=True)

    vivos_antes = contenedores()
    todos_antes = contenedores(todos=True)
    print(f"contenedores VIVOS antes: {len(vivos_antes)} · TODOS (-a): "
          f"{len(todos_antes)}")
    for c in todos_antes:
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

    # El pptx lo fabrica W17 (pandoc) y lo consumen W12/W13/W15 (LibreOffice):
    # se reordena para que los productores vayan primero, sin tocar los ids.
    orden = {"W01": 0, "W17": 1}
    casos.sort(key=lambda c: (orden.get(c[0], 2), CASOS.index(c)))

    # --- semillas mobi/azw3, con aristas REALES de `_MEDIDAS` ---------------
    necesarios = {c[2] for c in casos}
    for motor, o, d in SEMILLAS_PREVIAS:
        dst = os.path.join(ENT_MIO, f"entrada.{d}")
        if d not in necesarios or os.path.isfile(dst):
            continue
        ar = busca_arista(fx, motor, o, d)
        if ar is None:
            print(f"semilla {o}->{d}: NO hay arista en el grafo")
            continue
        conv = convertir_forzando(fx, ar, entrada_de(o), dst)
        print(f"semilla {o}->{d}: ok={conv.ok} {conv.veredicto} "
              f"{os.path.getsize(dst) if os.path.isfile(dst) else 0} B", flush=True)

    previos = {}
    if os.path.isfile(a.salida):
        try:
            with open(a.salida, encoding="utf-8") as f:
                previos = {x["id"]: x for x in (json.load(f).get("casos") or [])}
        except Exception:
            previos = {}

    t0 = time.time()
    for cid, motor, o, d in casos:
        ar = busca_arista(fx, motor, o, d)
        if ar is None:
            previos[cid] = {"id": cid, "motor": motor, "origen": o, "destino": d,
                            "rc": None, "motivo": "la arista no esta en el grafo"}
            print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} SIN ARISTA EN EL GRAFO")
            continue
        ent = entrada_de(o)
        if not os.path.isfile(ent):
            previos[cid] = {"id": cid, "motor": motor, "origen": o, "destino": d,
                            "rc": None, "motivo": f"falta la semilla entrada.{o}"}
            print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} FALTA SEMILLA entrada.{o}")
            continue
        salida = os.path.join(a.out, f"{cid}_{motor[4:]}_{o}2{d}.{d}")
        espia = os.path.join(a.out, f"{cid}_desechable")
        conv = convertir_forzando(fx, ar, ent, salida, espia=espia)
        reg = registro(conv, cid, motor, o, d, salida, espia=espia)
        reg["build"] = builds.get(motor, "")
        reg["estado_arista_antes"] = ar.estado
        reg["rasteriza_declarado"] = ar.rasteriza
        previos[cid] = reg
        # `newline="\n"` en todo volcado: `.gitattributes` fija LF en el arbol
        # de trabajo y el `open()` de Windows traduce a CRLF por defecto, lo
        # que saca el fichero entero como modificado y entierra el diff real.
        print(f"{cid:<4} {motor:<16} {o:>5}->{d:<5} rc={reg.get('rc')} "
              f"{reg.get('ms', 0):>8.0f} ms {reg.get('bytes', 0):>9} B  "
              f"car={reg.get('caracteres', 0):>6} "
              f"cent={'S' if reg.get('centinela') else 'n'} "
              f"rast_med={reg.get('rasteriza_medido'):<5} "
              f"rast_dec={str(reg.get('rasteriza_declarado')):<5} "
              f"contrato={reg.get('contrato', '-'):<10} "
              f"sobra={len(reg.get('sobrantes') or {})}", flush=True)
        with open(a.salida, "w", encoding="utf-8", newline="
") as f:
            json.dump({"casos": [previos[k] for k in sorted(previos)]}, f,
                      ensure_ascii=False, indent=1)

        semilla_ext = SEMILLA_DE.get((motor, o, d))
        if semilla_ext and os.path.isfile(salida):
            dst = os.path.join(ENT_MIO, f"entrada.{semilla_ext}")
            shutil.copy2(salida, dst)
            print(f"     semilla guardada: {dst} ({os.path.getsize(dst)} B)")

    print(f"\ntotal {time.time() - t0:.1f} s")

    vivos_despues = contenedores()
    todos_despues = contenedores(todos=True)
    ids_antes = {x.split("|")[0] for x in todos_antes}
    nuevos = [c for c in todos_despues if c.split("|")[0] not in ids_antes]
    print(f"contenedores VIVOS despues: {len(vivos_despues)} · TODOS (-a): "
          f"{len(todos_despues)} · NUEVOS (-a): {len(nuevos)}")
    for c in nuevos:
        print("   !", c)

    with open(a.salida, "w", encoding="utf-8", newline="
") as f:
        json.dump({"casos": [previos[k] for k in sorted(previos)],
                   "contenedores_vivos_antes": vivos_antes,
                   "contenedores_todos_antes": todos_antes,
                   "contenedores_vivos_despues": vivos_despues,
                   "contenedores_todos_despues": todos_despues,
                   "contenedores_nuevos": nuevos,
                   "builds": builds,
                   "timeout_fuera_s": TIMEOUT,
                   "umbral_texto": UMBRAL_TEXTO}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
