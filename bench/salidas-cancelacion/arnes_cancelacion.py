"""Arnés de C34: cuánto tarda una cancelación en surtir efecto, antes y después.

Uso:

    python bench/salidas-cancelacion/arnes_cancelacion.py [--n 9]

Escribe `bench/salidas-cancelacion/c34_medidas.json`. No usa la GPU.

Las cuatro medidas:

M1  Nivel de INVOCACIÓN. Un `ffmpeg` que no termina solo (`-re` + `-t 3600`,
    que casi no consume CPU) y dos formas de pedirle que pare:
      * `cooperativa`  — lo que había: marcar un `Event` y esperar. La
        invocación no se entera y termina en su `timeout`.
      * `cancelar_hilo` — lo de ahora: alcanzar el `Popen` y matar el árbol.
M2  Extremo a extremo por `servicio.Servicio`, que es la puerta común de las
    cuatro superficies. Control: la misma conversión sin cancelar.
M3  CONTENEDOR. `docker run … sleep 120` y dos formas de matarlo: solo el
    cliente (`_matar_arbol`) o cliente + contenedor. Se comprueba después si el
    contenedor sigue vivo.
M4  Coste del registro en el camino normal, que es el que se paga siempre.

Dos testigos de ruido, como manda `CLAUDE.md` §3: uno de deriva (bucle
monohilo) y otro de nivel (lanzamiento de proceso), este con tope propio.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import invocacion                                    # noqa: E402
from filex import servicio as S                                 # noqa: E402
from filex.nucleo import FileX                                  # noqa: E402

SALIDA = os.path.join(RAIZ, "bench", "salidas-cancelacion", "c34_medidas.json")
VIDEO = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
IMAGEN = "ghcr.io/c4illin/convertx:latest"

#: Tope del `ffmpeg` eterno de M1. Es la cifra que mide la vía cooperativa: sin
#: asa del `Popen`, cancelar tarda lo que le quede al tope. Se usa 5 s para que
#: el arnés no dure una hora; **por MCP el tope real son 300 s**.
TOPE_M1 = 5.0

#: Tope del propio testigo de nivel. Un testigo que puede tumbar la medición no
#: es un testigo (`CLAUDE.md` §3, caso P3: `ffprobe -version` agotó 60 s).
TOPE_TESTIGO = 20.0


# ------------------------------------------------------------------ testigos


def testigo_deriva(n: int = 200_000) -> float:
    """Bucle monohilo: detecta la DERIVA dentro de la tanda."""
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    """Lanzamiento de proceso: detecta el NIVEL de carga de la máquina."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO, check=False)
    except Exception:
        return TOPE_TESTIGO * 1000
    return (time.perf_counter() - t0) * 1000


def _ffmpeg_eterno() -> list[str]:
    return ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-re",
            "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30",
            "-t", "3600", "-f", "null", "-"]


def _espera(cond, tope: float, paso: float = 0.01) -> bool:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < tope:
        if cond():
            return True
        time.sleep(paso)
    return False


def _mediana(v: list[float]) -> float:
    return round(statistics.median(v), 3) if v else float("nan")


# ---------------------------------------------------------------------- M1


def m1(n: int) -> dict:
    """Cancelación a nivel de invocación: cooperativa contra `cancelar_hilo`."""
    out = {"tope_s": TOPE_M1, "cooperativa_ms": [], "cancelar_hilo_ms": [],
           "motivos": []}
    for via in ("cooperativa", "cancelar_hilo"):
        for _ in range(n):
            caja = {}
            listo = threading.Event()

            def corre():
                listo.set()
                caja["r"] = invocacion.ejecutar(_ffmpeg_eterno(), timeout=TOPE_M1)
                invocacion.olvidar_hilo()

            h = threading.Thread(target=corre, daemon=True)
            h.start()
            listo.wait(TOPE_M1)
            _espera(lambda: invocacion.en_vuelo() > 0, tope=TOPE_M1)
            t0 = time.perf_counter()
            if via == "cancelar_hilo":
                invocacion.cancelar_hilo(h.ident)
            # La vía cooperativa no hace NADA sobre el proceso: es exactamente
            # lo que hacía `job(..., "cancelar")` antes de C34.
            h.join(timeout=TOPE_M1 * 4)
            ms = (time.perf_counter() - t0) * 1000
            out[f"{via}_ms"].append(round(ms, 2))
            r = caja.get("r")
            out["motivos"].append(f"{via}:{r.motivo if r else 'sin_resultado'}")
    out["cooperativa_mediana_ms"] = _mediana(out["cooperativa_ms"])
    out["cancelar_hilo_mediana_ms"] = _mediana(out["cancelar_hilo_ms"])
    out["ganancia"] = round(out["cooperativa_mediana_ms"] /
                            max(out["cancelar_hilo_mediana_ms"], 1e-9), 1)
    return out


# ---------------------------------------------------------------------- M2


def m2(n: int, trabajo: str) -> dict:
    """Extremo a extremo por el servicio: cancelar contra dejar terminar."""
    out = {"sin_cancelar_ms": [], "cancelar_ms": [], "estados": []}
    fx = FileX()
    sv = S.Servicio(fx, S.Trabajos(os.path.join(trabajo, "trabajos")))
    for i in range(n):
        r = sv.convert(VIDEO, os.path.join(trabajo, f"ctrl{i}.webm"))
        t = sv.trabajos.get(r["job_id"])
        t0 = time.perf_counter()
        _espera(lambda: t.estado != S.TRABAJANDO, tope=300)
        out["sin_cancelar_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
        out["estados"].append("ctrl:" + t.estado)
    for i in range(n):
        r = sv.convert(VIDEO, os.path.join(trabajo, f"canc{i}.webm"))
        t = sv.trabajos.get(r["job_id"])
        _espera(lambda: invocacion.en_vuelo() > 0, tope=30)
        t0 = time.perf_counter()
        c = sv.job(r["job_id"], "cancelar")
        _espera(lambda: t.estado != S.TRABAJANDO, tope=300)
        out["cancelar_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
        out["estados"].append(f"canc:{t.estado}:motor_detenido={c.get('motor_detenido')}")
    out["sin_cancelar_mediana_ms"] = _mediana(out["sin_cancelar_ms"])
    out["cancelar_mediana_ms"] = _mediana(out["cancelar_ms"])
    out["ganancia"] = round(out["sin_cancelar_mediana_ms"] /
                            max(out["cancelar_mediana_ms"], 1e-9), 1)
    return out


# ---------------------------------------------------------------------- M3


def _hay_docker() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=TOPE_TESTIGO, check=False)
        return p.returncode == 0
    except Exception:
        return False


def _vivos(fuentes: set) -> bool:
    ids = [x for x in invocacion._docker(["ps", "-q"]).split() if x]
    if not ids:
        return False
    det = invocacion._docker(["inspect", "--format",
                             "{{range .Mounts}}{{.Source}}\t{{end}}"] + ids)
    for linea in det.splitlines():
        m = {os.path.normcase(os.path.normpath(c))
             for c in linea.strip().split("\t") if c}
        if m & fuentes:
            return True
    return False


def m3(n: int, trabajo: str) -> dict:
    """Contenedor: matar solo el cliente contra matar también el contenedor.

    `CLAUDE.md` §3, MEDIDO: *matar el `docker run` NO mata el contenedor, y
    `--rm` tampoco*. Aquí se reproduce y se mide el remedio.
    """
    out = {"solo_cliente": [], "cliente_y_contenedor": [],
           "matar_contenedor_ms": []}
    for via in ("solo_cliente", "cliente_y_contenedor"):
        for i in range(n):
            d = os.path.join(trabajo, f"doc-{via}-{i}")
            os.makedirs(d, exist_ok=True)
            argv = ["docker", "run", "--rm", "--init", "--network", "none",
                    "--mount",
                    f"type=bind,source={d.replace(os.sep, '/')},target=/trabajo",
                    "-w", "/trabajo", "--entrypoint", "sh", IMAGEN,
                    "-c", "sleep 120"]
            fuentes = set(invocacion._fuentes_de_montaje(argv))
            caja = {}
            listo = threading.Event()

            def corre():
                listo.set()
                caja["r"] = invocacion.ejecutar(argv, timeout=180)
                invocacion.olvidar_hilo()

            h = threading.Thread(target=corre, daemon=True)
            h.start()
            listo.wait(30)
            if not _espera(lambda: _vivos(fuentes), tope=60):
                out[via].append("no_arranco")
                invocacion.cancelar_hilo(h.ident)
                h.join(timeout=30)
                continue
            if via == "solo_cliente":
                # Lo que hacía `_matar_arbol` por su cuenta.
                with invocacion._CERROJO_VUELO:
                    par = invocacion._EN_VUELO.get(h.ident)
                if par:
                    invocacion._matar_arbol(par[0])
            else:
                t0 = time.perf_counter()
                invocacion.cancelar_hilo(h.ident)
                out["matar_contenedor_ms"].append(
                    round((time.perf_counter() - t0) * 1000, 1))
            h.join(timeout=60)
            # Dos segundos de gracia: se pregunta por el contenedor DESPUÉS de
            # que el cliente haya muerto del todo.
            time.sleep(2.0)
            out[via].append("contenedor_vivo" if _vivos(fuentes)
                            else "contenedor_muerto")
            # Limpieza pase lo que pase: nada de contenedores huérfanos.
            invocacion._matar_contenedor_de(argv)
            invocacion.olvidar_hilo(h.ident)
    out["matar_contenedor_mediana_ms"] = _mediana(out["matar_contenedor_ms"])
    return out


# ---------------------------------------------------------------------- M4


def m4(n: int) -> dict:
    """Lo que cuesta el registro en el camino que se paga SIEMPRE."""
    reg = []
    for _ in range(n * 1000):
        t0 = time.perf_counter_ns()
        ident = threading.get_ident()
        with invocacion._CERROJO_VUELO:
            tarde = ident in invocacion._CANCELADOS
            if not tarde:
                invocacion._EN_VUELO[ident] = (None, [])
        with invocacion._CERROJO_VUELO:
            invocacion._EN_VUELO.pop(ident, None)
        reg.append(time.perf_counter_ns() - t0)
    invocacion.olvidar_hilo()
    inv = []
    for _ in range(n):
        r = invocacion.ejecutar(["ffmpeg", "-hide_banner", "-version"], timeout=30)
        inv.append(r.ms)
    return {"registro_us": round(statistics.median(reg) / 1000, 3),
            "invocacion_trivial_ms": _mediana(inv),
            "fraccion_pct": round(
                (statistics.median(reg) / 1e6) / max(_mediana(inv), 1e-9) * 100, 6)}


# ---------------------------------------------------------------------- M5


#: Semilla de M5. Se escribe aquí y no se toma del corpus porque el corpus **no
#: tiene documentos**: las aristas documentales se sondean con ficheros
#: generados. `html→pdf` la sirve LibreOffice en contenedor, que es el caso que
#: interesa: un salto cuyo trabajo real ocurre en OTRO proceso.
SEMILLA_HTML = ("<html><head><meta charset='utf-8'><title>c34</title></head>"
                "<body><h1>C34</h1><p>" + ("cancelar de verdad. " * 400) +
                "</p></body></html>")


def m5(n: int, trabajo: str) -> dict:
    """Un salto EN CONTENEDOR, extremo a extremo por el servicio."""
    ent = os.path.join(trabajo, "semilla.html")
    with open(ent, "w", encoding="utf-8") as fh:
        fh.write(SEMILLA_HTML)
    fx = FileX()
    sv = S.Servicio(fx, S.Trabajos(os.path.join(trabajo, "trabajos5")))
    out = {"sin_cancelar_ms": [], "cancelar_ms": [], "estados": [],
           "contenedores_vivos_despues": []}
    for i in range(n):
        r = sv.convert(ent, os.path.join(trabajo, f"c5ctrl{i}.pdf"))
        if "job_id" not in r:
            return {"error": r}
        t = sv.trabajos.get(r["job_id"])
        t0 = time.perf_counter()
        _espera(lambda: t.estado != S.TRABAJANDO, tope=300)
        out["sin_cancelar_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
        out["estados"].append("ctrl:" + t.estado)
    antes = set(invocacion._docker(["ps", "-q"]).split())
    for i in range(n):
        r = sv.convert(ent, os.path.join(trabajo, f"c5canc{i}.pdf"))
        t = sv.trabajos.get(r["job_id"])
        _espera(lambda: invocacion.en_vuelo() > 0, tope=30)
        time.sleep(1.0)                  # que el contenedor llegue a existir
        t0 = time.perf_counter()
        c = sv.job(r["job_id"], "cancelar")
        _espera(lambda: t.estado != S.TRABAJANDO, tope=300)
        out["cancelar_ms"].append(round((time.perf_counter() - t0) * 1000, 1))
        out["estados"].append(f"canc:{t.estado}:motor_detenido={c.get('motor_detenido')}")
        time.sleep(2.0)
        ahora = set(invocacion._docker(["ps", "-q"]).split())
        out["contenedores_vivos_despues"].append(len(ahora - antes))
    out["sin_cancelar_mediana_ms"] = _mediana(out["sin_cancelar_ms"])
    out["cancelar_mediana_ms"] = _mediana(out["cancelar_ms"])
    out["ganancia"] = round(out["sin_cancelar_mediana_ms"] /
                            max(out["cancelar_mediana_ms"], 1e-9), 1)
    return out


# --------------------------------------------------------------------- main


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=9)
    p.add_argument("--saltar", default="", help="lista separada por comas: m1,m2,m3,m4")
    args = p.parse_args()
    saltar = {x.strip() for x in args.saltar.split(",") if x.strip()}

    trabajo = tempfile.mkdtemp(prefix="c34-bench-")
    antes_raiz = sorted(os.listdir(RAIZ))          # R21: listar antes y después
    res = {"n": args.n, "cwd": os.getcwd(), "trabajo": trabajo,
           "testigo_deriva_ini_ms": round(testigo_deriva(), 2),
           "testigo_nivel_ini_ms": round(testigo_nivel(), 2)}
    try:
        if "m1" not in saltar:
            res["m1_invocacion"] = m1(args.n)
        if "m2" not in saltar and os.path.isfile(VIDEO):
            res["m2_servicio"] = m2(args.n, trabajo)
        if "m3" not in saltar and _hay_docker():
            res["m3_contenedor"] = m3(args.n, trabajo)
        elif "m3" not in saltar:
            res["m3_contenedor"] = {"error": "no hay demonio de docker"}
        if "m4" not in saltar:
            res["m4_coste_registro"] = m4(args.n)
        if "m5" not in saltar and _hay_docker():
            res["m5_contenedor_extremo_a_extremo"] = m5(args.n, trabajo)
    finally:
        shutil.rmtree(trabajo, ignore_errors=True)

    res["testigo_deriva_fin_ms"] = round(testigo_deriva(), 2)
    res["testigo_nivel_fin_ms"] = round(testigo_nivel(), 2)
    res["deriva"] = round(res["testigo_deriva_fin_ms"] /
                          max(res["testigo_deriva_ini_ms"], 1e-9), 3)
    # Con la sesión de escritorio remoto activa TODO sale `SUCIA`. Es
    # estructural, no un fallo: se etiqueta y se sigue.
    res["etiqueta"] = "SUCIA"
    res["ficheros_no_pedidos_en_la_raiz"] = sorted(
        set(os.listdir(RAIZ)) - set(antes_raiz))

    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items()
                      if not isinstance(v, dict)}, ensure_ascii=False))
    for k in ("m1_invocacion", "m2_servicio", "m3_contenedor",
              "m4_coste_registro", "m5_contenedor_extremo_a_extremo"):
        if k in res:
            print(k, json.dumps({a: b for a, b in res[k].items()
                                 if not isinstance(b, list)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
