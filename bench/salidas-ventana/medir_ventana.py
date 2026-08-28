"""N12 — la ventana entre la DETECCIÓN y el `move`: reproducirla y medirla.

`bench/cerrojo-de-maquina.md` §6.3 la declara PENDIENTE con una frase:
*«entre el `os.replace(p,p)` y el `shutil.move` hay una ventana [...] quien
llegue dentro de esa ventana pisa igual»*. Aquí se hacen dos cosas **en este
orden**, porque el orden es el encargo: primero se demuestra que existe y
cuánto dura, y solo después se arregla.

Tres regímenes, y el tercero es el que hace honesto al segundo:

* **A — pasiva.** Ni tercero ni gancho de sincronización: solo dos relojes
  alrededor de la ventana en una conversión normal. Da la DURACIÓN.
* **B — centinela.** Un tercero de verdad, en otro proceso, que espera a un
  fichero centinela que el gancho escribe justo cuando la detección retorna.
  Es la carrera **fabricada**: da la máxima probabilidad de acierto, y el
  propio centinela infla la ventana (se mide cuánto: `coste_centinela_ns`).
* **C — martillo.** El mismo tercero, pero **sin ningún gancho**: golpea el
  destino en bucle apretado mientras la conversión corre. Si el atropello sale
  también aquí, la ventana no la fabrica el arnés.

Cada celda registra `la_ventana_se_abrio` — la trampa 38 dice que un arnés de
carrera que no comprueba si la condición se dio sale verde sin probar nada.

Escenarios, porque no son el mismo fallo:

* **E1 destino AUSENTE** (el caso normal de un conversor): la detección dice
  «libre» con razón, y el tercero **crea** el fichero dentro de la ventana.
* **E2 destino PRESENTE y libre**: la detección dice «libre» con razón, y el
  tercero lo **abre** dentro de la ventana.

Uso:  python medir_ventana.py --modo A|B|C --n 12 [--escenario E1|E2] [--etiqueta ...]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

TERCERO = os.path.join(AQUI, "tercero.py")
ENTRADA = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")

from filex import nucleo  # noqa: E402

#: Ver el comentario de `tercero.py`: `time.time_ns` tiene 15,625 ms de tic en
#: esta máquina y no puede medir esta ventana. `perf_counter_ns` es QPC crudo.
reloj = time.perf_counter_ns


def sondear_reloj() -> dict:
    """El MECANISMO, no el comportamiento (trampa 40): ¿de verdad
    `perf_counter_ns` es QPC crudo, es decir comparable entre procesos?"""
    import ctypes

    k32 = ctypes.WinDLL("kernel32")
    f = ctypes.c_longlong()
    c = ctypes.c_longlong()
    k32.QueryPerformanceFrequency(ctypes.byref(f))
    k32.QueryPerformanceCounter(ctypes.byref(c))
    p = time.perf_counter_ns()
    return {"QPF": f.value,
            "QPC_x_ns": c.value * (1_000_000_000 // f.value),
            "perf_counter_ns": p,
            "desfase_ns": p - c.value * (1_000_000_000 // f.value),
            "res_time": time.get_clock_info("time").resolution,
            "res_perf": time.get_clock_info("perf_counter").resolution}


# ---------------------------------------------------------------- testigos
def testigo_deriva(vueltas: int = 400_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x += i
    return (time.perf_counter() - t0) * 1000


def testigo_proceso(tope: float = 20.0) -> float:
    """Nivel de carga de la máquina. **Con tope**: un testigo que puede tumbar
    la medición no es un testigo (§3 de CLAUDE.md)."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=tope)
    except Exception:
        return tope * 1000
    return (time.perf_counter() - t0) * 1000


# ------------------------------------------------------- la instrumentación
class Ganchos:
    """Envuelve la detección y el `recoger` para poner relojes en la ventana.

    **No cambia el comportamiento**: llama a los originales y anota. El único
    efecto sobre el reloj es el `open`+`write` del centinela en el modo B, que
    se mide aparte y se publica.
    """

    def __init__(self, centinela: str = "") -> None:
        self.centinela = centinela
        self.marcas: dict = {}
        self._det = nucleo.destino_ocupado_por_un_tercero
        # **El envoltorio va sobre `nucleo.mover_a_destino`, no sobre
        # `DirectorioDeTrabajo.recoger`.** Con `FILEX_MOVE_SEGURO=0` el de
        # dentro es el `shutil.move` de siempre, así que el mismo gancho mide
        # el antes y el después — que es la única forma honesta de comparar en
        # esta máquina.
        self._rec = nucleo.mover_a_destino

    def __enter__(self):
        marcas = self.marcas
        centinela = self.centinela
        det_original = self._det
        rec_original = self._rec

        def deteccion(ruta):
            r = det_original(ruta)
            # **La ventana es la de la SEGUNDA detección, no la de la primera.**
            # `convertir()` llama a la detección dos veces: una antes de gastar
            # 250 ms en convertir y otra justo antes del `move`. Soltar al
            # tercero en la primera lo pone a ocupar el destino **antes** de que
            # exista ventana ninguna, y las 12 celdas salen `fallo` con
            # `la_ventana_se_abrio=False`: doce celdas verdes que no prueban
            # nada, que es la trampa 38 en directo. Costó una tanda entera.
            marcas["llamadas"] = marcas.get("llamadas", 0) + 1
            marcas["det_fin_ns"] = reloj()
            marcas["det_dijo"] = r
            if centinela and not r and marcas["llamadas"] >= 2:
                t0 = time.perf_counter_ns()
                with open(centinela, "wb") as f:
                    f.write(b"1")
                marcas["coste_centinela_ns"] = time.perf_counter_ns() - t0
            return r

        def mover(origen, destino_final):
            marcas["move_ini_ns"] = reloj()
            try:
                return rec_original(origen, destino_final)
            except Exception as e:
                marcas["move_error"] = e.__class__.__name__
                raise
            finally:
                marcas["move_fin_ns"] = reloj()

        nucleo.destino_ocupado_por_un_tercero = deteccion
        nucleo.mover_a_destino = mover
        return self

    def __exit__(self, *_e):
        nucleo.destino_ocupado_por_un_tercero = self._det
        nucleo.mover_a_destino = self._rec


# ------------------------------------------------------------------ la celda
def _lanzar_tercero(modo, ruta, registro, **extra):
    argv = [sys.executable, TERCERO, "--modo", modo, "--ruta", ruta,
            "--registro", registro]
    for k, v in extra.items():
        argv += [f"--{k}", str(v)]
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _leer(registro):
    try:
        with open(registro, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


BYTES_TERCERO = 4014


def una_celda(fx, tmp: str, i: int, modo: str, escenario: str) -> dict:
    sub = os.path.join(tmp, f"celda{i:03d}")
    os.makedirs(sub)
    destino = os.path.join(sub, "salida.webp")
    registro = os.path.join(sub, "tercero.json")
    centinela = os.path.join(sub, "centinela")

    celda: dict = {"i": i, "modo": modo, "escenario": escenario}

    if escenario == "E2":
        with open(destino, "wb") as f:
            f.write(b"V" * BYTES_TERCERO)
        celda["destino_antes_B"] = BYTES_TERCERO
    else:
        celda["destino_antes_B"] = None

    p = None
    if modo == "B":
        p = _lanzar_tercero("esperar", destino, registro, centinela=centinela,
                            tope=30)
        # Que el tercero esté ya en su bucle: si arranca tarde, la ventana se
        # habrá cerrado y la celda no probaría nada — trampa 38.
        fin = time.monotonic() + 20
        while time.monotonic() < fin and not _leer(registro):
            time.sleep(0.005)
        celda["tercero_listo"] = bool(_leer(registro))
    elif modo == "C":
        p = _lanzar_tercero("martillo", destino, registro, tope=3, pausa=0.002)
        time.sleep(0.05)
        celda["tercero_listo"] = True

    g = Ganchos(centinela if modo == "B" else "")
    with g:
        t0 = reloj()
        conv = fx.convertir(ENTRADA, destino)
        t1 = reloj()

    celda["conv_ms"] = round((t1 - t0) / 1e6, 3)
    celda["veredicto"] = conv.veredicto
    celda["motivo"] = conv.motivo
    m = g.marcas
    celda["deteccion_dijo_ocupado"] = m.get("det_dijo")
    celda["coste_centinela_ns"] = m.get("coste_centinela_ns")
    if "det_fin_ns" in m and "move_fin_ns" in m:
        celda["ventana_ns"] = m["move_fin_ns"] - m["det_fin_ns"]
        celda["hasta_move_ns"] = m["move_ini_ns"] - m["det_fin_ns"]
        celda["move_ns"] = m["move_fin_ns"] - m["move_ini_ns"]
    else:
        celda["ventana_ns"] = None

    if p is not None:
        try:
            p.wait(timeout=45)
        except subprocess.TimeoutExpired:
            p.kill()
        d = _leer(registro)
        celda["tercero"] = {k: v for k, v in d.items()
                            if k not in ("aperturas_ns", "cierres_ns")}
        # ¿SE ABRIÓ la ventana? No es «hubo tercero»: es que el tercero tocó el
        # destino con su reloj DENTRO de [det_fin, move_fin].
        abre = []
        if d.get("abierto_ns"):
            abre = [d["abierto_ns"]]
        abre += d.get("aperturas_ns", [])
        cierra = d.get("cierres_ns", [])
        ini, fin_v = m.get("det_fin_ns"), m.get("move_fin_ns")
        hay_ventana = ini is not None and fin_v is not None
        dentro = [a for a in abre if hay_ventana and ini <= a <= fin_v]
        celda["la_ventana_se_abrio"] = bool(dentro)
        celda["aperturas_dentro"] = len(dentro)
        celda["aperturas_totales"] = len(abre)
        # Y la distinción que decide qué cubre el arreglo: ¿el tercero tenía el
        # fichero abierto DURANTE la ventana, o solo lo abrió y lo cerró dentro?
        # `os.replace` solo puede negarse al primero.
        solapa_v = solapa_m = 0
        mv0, mv1 = m.get("move_ini_ns"), m.get("move_fin_ns")
        for k, a in enumerate(abre):
            c = cierra[k] if k < len(cierra) else float("inf")
            if hay_ventana and a <= fin_v and c >= ini:
                solapa_v += 1
            if mv0 is not None and mv1 is not None and a <= mv1 and c >= mv0:
                solapa_m += 1
        celda["abierto_durante_la_ventana"] = solapa_v
        celda["abierto_durante_el_move"] = solapa_m
    else:
        celda["la_ventana_se_abrio"] = None

    celda["destino_existe_al_final"] = os.path.exists(destino)
    celda["destino_final_B"] = (os.path.getsize(destino)
                                if os.path.exists(destino) else None)
    # ¿Quién ganó? El fichero del tercero es todo `T`; el de FileX es un WEBP.
    if celda["destino_final_B"]:
        with open(destino, "rb") as f:
            cab = f.read(16)
        celda["cabecera"] = cab[:12].hex()
        celda["es_webp"] = cab[:4] == b"RIFF" and cab[8:12] == b"WEBP"
        celda["es_del_tercero"] = cab[:4] == b"TTTT"
    else:
        celda["es_webp"] = celda["es_del_tercero"] = None

    # **El atropello: la ventana se abrió y FileX dijo que todo bien.** El
    # criterio NO puede ser «el fichero final es un WEBP»: con el martillo, el
    # tercero vuelve a escribir después del `move` y borra la evidencia — el
    # atropello ya ha ocurrido y la cabecera dice que no. Lo que define el
    # fallo es que FileX declare éxito habiendo pisado a alguien.
    celda["atropello"] = bool(celda["la_ventana_se_abrio"] and conv.ok)
    return celda


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", required=True, choices=("A", "B", "C"))
    ap.add_argument("--escenario", default="E1", choices=("E1", "E2"))
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--etiqueta", default="")
    a = ap.parse_args(argv)

    if not os.path.isfile(ENTRADA):
        print(f"falta {ENTRADA}: ¿corpus en punteros de LFS? (trampa 34)")
        return 2

    fx = nucleo.FileX()
    tmp = tempfile.mkdtemp(prefix="filex-ventana-")
    antes = sorted(os.listdir(tmp))
    d0, pr0 = testigo_deriva(), testigo_proceso()

    # Calentar: la trampa 7 (Defender) y el primer `sondear_todos`.
    calent = os.path.join(tmp, "calent.webp")
    fx.convertir(ENTRADA, calent)

    celdas = []
    try:
        for i in range(a.n):
            celdas.append(una_celda(fx, tmp, i, a.modo, a.escenario))
            print(f"  celda {i}: ventana={celdas[-1]['ventana_ns']} ns "
                  f"abrió={celdas[-1]['la_ventana_se_abrio']} "
                  f"ver={celdas[-1]['veredicto']} "
                  f"atropello={celdas[-1]['atropello']}")
    finally:
        d1, pr1 = testigo_deriva(), testigo_proceso()
        ventanas = sorted(c["ventana_ns"] for c in celdas if c["ventana_ns"])
        res = {
            "cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modo": a.modo, "escenario": a.escenario, "n": a.n,
            "etiqueta": a.etiqueta,
            "reloj": sondear_reloj(),
            "modo_cerrojo": os.environ.get("FILEX_CERROJO_DESTINO", "(defecto)"),
            "move_seguro": os.environ.get("FILEX_MOVE_SEGURO", "(defecto)"),
            "testigos": {"deriva_ini_ms": round(d0, 1), "deriva_fin_ms": round(d1, 1),
                         "deriva": round(d1 / d0, 2) if d0 else None,
                         "proceso_ini_ms": round(pr0, 1),
                         "proceso_fin_ms": round(pr1, 1),
                         "limpia": bool(d0 and 0.5 < d1 / d0 < 2.0
                                        and max(pr0, pr1) < 2000)},
            "ventana_ns": {
                "n": len(ventanas),
                "mediana": ventanas[len(ventanas) // 2] if ventanas else None,
                "min": ventanas[0] if ventanas else None,
                "max": ventanas[-1] if ventanas else None,
                "p90": ventanas[int(len(ventanas) * 0.9)] if ventanas else None,
            },
            "se_abrio": sum(1 for c in celdas if c["la_ventana_se_abrio"]),
            "atropellos": sum(1 for c in celdas if c["atropello"]),
            "veredictos": {},
            "listado_antes": antes,
            "celdas": celdas,
        }
        for c in celdas:
            res["veredictos"][c["veredicto"]] = res["veredictos"].get(c["veredicto"], 0) + 1
        nombre = f"ventana_{a.modo}{a.escenario}{('_' + a.etiqueta) if a.etiqueta else ''}.json"
        with open(os.path.join(AQUI, nombre), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(json.dumps({k: v for k, v in res.items() if k != "celdas"},
                         ensure_ascii=False, indent=1))
        # R21: listar el desechable antes de borrarlo.
        print("desechable al terminar:", len(os.listdir(tmp)), "entradas")
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
