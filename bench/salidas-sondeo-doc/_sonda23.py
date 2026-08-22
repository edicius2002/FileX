# -*- coding: utf-8 -*-
"""S3 — sonda de las 23 aristas `sin_sondear` del motor documental en contenedor.

**La conversión la hace el NÚCLEO, no este arnés.** Cada caso llama a
`filex.nucleo.FileX.convertir()`, que es quien monta el directorio desechable,
lanza el contenedor con el tope por dentro, toma el censo del punto 5 *dentro*
del mismo `with` y pasa el contrato de cinco puntos. Aquí solo se **fuerza la
arista**: se sustituye `fx.planificar` por una `Decision` de un solo paso, para
que el grafo no resuelva el par por otro camino (que es justo lo que haría:
`rtf→odt` tiene competencia, y `epub→epub` ni siquiera llega a planificarse
porque origen y destino coinciden).

Forzar la arista es la única manera de sondear UNA arista. Dejar que el grafo
elija mediría el grafo, no la arista.

    python bench/salidas-sondeo-doc/_sonda23.py [--solo motor:o>d,...]

Salida: `bench/salidas-sondeo-doc/sonda23.json` y los ficheros producidos en
`bench/salidas-sondeo-doc/out/` (que se borran al terminar; queda el
`MANIFIESTO.md`).

Las funciones `texto_de`/`sha` son una COPIA de `bench/salidas-hito5/_sonda.py`
(K1): CLAUDE.md §1 pide copiar el arnés ajeno a tu directorio, no editarlo.
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

SAL = os.path.join(RAIZ, "bench", "salidas-sondeo-doc")
ENT_K1 = os.path.join(RAIZ, "bench", "salidas-hito5", "entradas")
ENT_MIO = os.path.join(SAL, "entradas")

CENTINELA = "FILEXSENTINELA7743"

#: Tope de FUERA. `motor_contenedor` deriva el de DENTRO restándole
#: `MARGEN_TOPE`=10, así que dentro dispara a los 90 s. La arista documental más
#: lenta medida por K1 es Calibre `epub→pdf` con 20,6 s: margen ×4,4.
#: Y hay una razón concreta para no subirlo: `soffice` colgado escribe hasta
#: 1,97 MB/s de `.tmp` en el desechable (K1, §4.2). 90 s acota la fuga.
TIMEOUT = 100.0


#: Tope de lo que el espía copia. Un `soffice` colgado escribe cientos de MB de
#: `.tmp`: copiarlos sería reproducir la fuga en el repositorio.
TOPE_ESPIA = 20 * 1024 * 1024


class DirTrabajoEspia(DirectorioDeTrabajo):
    """El desechable del núcleo, con una copia ANTES de borrarse.

    **Por qué hace falta:** cuando el contrato dice `fallo`, `nucleo._un_salto`
    NO recoge la salida, y el `finally` borra el desechable. Sin esto, de una
    arista rechazada solo queda el veredicto — y justo ahí es donde hay que
    mirar qué escribió el motor: un `rc=0` con 0 bytes y un `rc=0` con el
    documento entero son cosas distintas y el veredicto las iguala.

    No toca `filex/`: se sustituye el nombre en `filex.nucleo` desde el arnés.
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
# (copia literal de bench/salidas-hito5/_sonda.py — K1)


def _limpia(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def texto_de(ruta: str) -> str:
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    try:
        if ext == "pdf":
            # Ghostscript NATIVO de Windows. Trampa 4: `txtwrite` emite 1-3
            # caracteres de basura en un PDF sin texto; el umbral es >=10.
            with DirectorioDeTrabajo() as t:
                dst = t.destino("t.txt")
                r = invocacion.ejecutar(
                    ["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                     "-sDEVICE=txtwrite", f"-sOutputFile={dst}", ruta], timeout=90)
                if not r.ok or not os.path.isfile(dst):
                    return ""
                return _limpia(open(dst, encoding="utf-8", errors="replace").read())
        # `xlsx`/`pptx`/`odp` los añade S3: el pendiente 5 los necesita y el
        # original de K1 no los tenía.
        if ext in ("docx", "odt", "epub", "azw3", "mobi", "xlsx", "pptx", "odp",
                   "ods"):
            if not zipfile.is_zipfile(ruta):
                # mobi/azw3 no son zip: se lee el binario y se busca el centinela.
                # TRAMPA CONOCIDA: comprimen el texto (PalmDoc/LZ77), así que
                # esta sonda es CIEGA para ellos y el resultado no dice nada.
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
    """La semilla para un formato. Las siete de K1 se REUSAN sin copiarlas."""
    a = os.path.join(ENT_MIO, f"entrada.{ext}")
    if os.path.isfile(a):
        return a
    return os.path.join(ENT_K1, f"entrada.{ext}")


# -------------------------------------------------------------- forzar arista


def busca_arista(fx: FileX, motor: str, o: str, d: str):
    for a in fx.grafo.aristas:
        if a.motor == motor and a.origen == o and a.destino == d:
            return a
    return None


def convertir_forzando(fx: FileX, arista, entrada: str, salida: str,
                       espia: str | None = None):
    """`FileX.convertir()` con el camino fijado a UNA arista.

    No se toca `filex/`: se sustituye el método en la INSTANCIA y la clase del
    desechable en el MÓDULO. El resto del núcleo —censo, contrato, recogida—
    corre entero.
    """
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
        # `err` NO va al JSON crudo: R «nunca stderr crudo al modelo». Se guarda
        # una clasificación y las 200 últimas letras SOLO para el humano.
        reg["motivo_salto"] = s.motivo
        reg["err_cola"] = (s.err or "").strip()[-200:]
        reg["hallazgos"] = [{"regla": h.get("regla"), "sev": h.get("severidad"),
                             "msg": h.get("mensaje")} for h in (s.hallazgos or [])]
    else:
        reg["rc"] = None
    # La salida vive donde el núcleo la dejó: en el destino si el contrato la
    # aceptó, y **solo en la copia del espía** si la rechazó.
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
        # TRAMPA CONOCIDA (`formatos.py`): MOBI y AZW3 comprimen el texto, así
        # que `centinela=False` en ellos NO significa que se haya perdido.
        reg["sonda_texto_ciega"] = d in ("mobi", "azw3")
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


# ---------------------------------------------------------------- los 23 casos

CASOS = [
    ("S01", "doc_libreoffice", "rtf", "odt"),
    ("S02", "doc_libreoffice", "rtf", "docx"),
    ("S03", "doc_libreoffice", "html", "odt"),
    ("S04", "doc_libreoffice", "txt", "odt"),
    ("S05", "doc_libreoffice", "odt", "html"),
    ("S06", "doc_libreoffice", "docx", "rtf"),
    ("S07", "doc_pandoc", "html", "epub"),
    ("S08", "doc_pandoc", "html", "odt"),
    ("S09", "doc_pandoc", "html", "rtf"),
    ("S10", "doc_pandoc", "docx", "odt"),
    ("S11", "doc_pandoc", "epub", "docx"),
    ("S12", "doc_pandoc", "epub", "txt"),
    ("S13", "doc_pandoc", "rtf", "md"),
    ("S14", "doc_pandoc", "rtf", "html"),
    ("S15", "doc_pandoc", "md", "rtf"),
    ("S16", "doc_calibre", "mobi", "epub"),
    ("S17", "doc_calibre", "azw3", "epub"),
    ("S18", "doc_calibre", "mobi", "pdf"),
    ("S19", "doc_calibre", "azw3", "pdf"),
    ("S20", "doc_calibre", "txt", "epub"),
    ("S21", "doc_calibre", "md", "epub"),
    ("S22", "doc_calibre", "epub", "epub"),
    ("S23", "doc_calibre", "mobi", "azw3"),
]

#: Semillas que hay que FABRICAR antes de sondear, con una arista ya `real`.
#: `epub→mobi` (C03) y `epub→azw3` (C04) están medidas por K1.
SEMILLAS = (("doc_calibre", "epub", "mobi"), ("doc_calibre", "epub", "azw3"))


def contenedores() -> list[str]:
    r = invocacion.ejecutar(
        ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}"],
        timeout=45)
    return [x for x in (r.salida_txt or "").splitlines() if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--salida", default=os.path.join(SAL, "sonda23.json"))
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

    # --- semillas mobi/azw3, con aristas REALES -----------------------------
    # Solo se fabrica la que hace falta: cada una cuesta un Calibre.
    necesarios = {c[2] for c in casos}
    for motor, o, d in SEMILLAS:
        dst = os.path.join(ENT_MIO, f"entrada.{d}")
        if d not in necesarios or os.path.isfile(dst):
            continue
        ar = busca_arista(fx, motor, o, d)
        conv = convertir_forzando(fx, ar, entrada_de(o), dst)
        print(f"semilla {o}→{d}: ok={conv.ok} {conv.veredicto} "
              f"{os.path.getsize(dst) if os.path.isfile(dst) else 0} B")

    # Con `--solo`, lo que no se repite se CONSERVA: volcar solo lo seleccionado
    # borraría el resto del fichero, que es perder medidas en silencio.
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
                            "rc": None, "motivo": "la arista no está en el grafo"}
            res = [previos[k] for k in sorted(previos)]
            continue
        ent = entrada_de(o)
        if not os.path.isfile(ent):
            previos[cid] = {"id": cid, "motor": motor, "origen": o, "destino": d,
                            "rc": None, "motivo": f"falta la semilla entrada.{o}"}
            res = [previos[k] for k in sorted(previos)]
            continue
        salida = os.path.join(a.out, f"{cid}_{motor[4:]}_{o}2{d}.{d}")
        espia = os.path.join(a.out, f"{cid}_desechable")
        conv = convertir_forzando(fx, ar, ent, salida, espia=espia)
        reg = registro(conv, cid, motor, o, d, salida, espia=espia)
        reg["build"] = builds.get(motor, "")
        previos[cid] = reg
        res = [previos[k] for k in sorted(previos)]
        print(f"{cid:<4} {motor:<16} {o:>5}→{d:<5} rc={reg.get('rc')} "
              f"{reg.get('ms', 0):>8.0f} ms {reg.get('bytes', 0):>9} B  "
              f"car={reg.get('caracteres', 0):>6} "
              f"cent={'S' if reg.get('centinela') else 'n'} "
              f"contrato={reg.get('contrato', '-'):<10} "
              f"sobra={len(reg.get('sobrantes') or {})}", flush=True)
        with open(a.salida, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)

    print(f"\ntotal {time.time() - t0:.1f} s")

    despues = contenedores()
    print(f"contenedores vivos DESPUÉS: {len(despues)}")
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
