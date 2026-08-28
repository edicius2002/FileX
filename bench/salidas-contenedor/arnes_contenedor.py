"""Arnés a4 — parar un contenedor por el identificador que la ORDEN declara.

Línea base: `bench/cancelacion-y-servicio.md` §3 (agente N-a), que identificaba
el contenedor deduciéndolo del origen de su bind mount de escritura:

    matando solo el cliente ..... contenedor VIVO   9 de 9
    con el remedio de N-a ....... contenedor MUERTO 9 de 9, en 527,2 ms

Aquí se reproducen las dos filas con el identificador declarado (`--name`), se
añade el coste de identificar por las dos vías, y se miden dos cosas que N-a no
pudo: que cancelar una conversión **no toca el contenedor de la de al lado**, y
que la carrera de arranque sigue cerrada.

No usa la GPU. Todos los contenedores llevan un nombre `filex-<pid>-<uuid>` y se
censa `docker ps -a` antes y después.

    python bench/salidas-contenedor/arnes_contenedor.py
    python bench/salidas-contenedor/arnes_contenedor.py --saltar m5,m6

Salida: `a4_medidas.json` en este mismo directorio.
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

from filex import invocacion                     # noqa: E402
from filex.motor_contenedor import LibreOfficeEnContenedor  # noqa: E402

N = 9
IMAGEN = "ghcr.io/c4illin/convertx:latest"
PACIENCIA = 90.0
#: Cuánto se espera tras cancelar antes de declarar «no quedó contenedor». El
#: borrado de `--rm` lo hace el demonio de forma ASÍNCRONA.
GRACIA = 20.0
TOPE_TESTIGO = 20.0


# ----------------------------------------------------------------- testigos

def testigo_deriva(bucles=3):
    """Deriva DENTRO de la tanda: bucle monohilo de Python.

    Ciego a la contención multinúcleo — con 12 núcleos cabe en uno libre —, por
    eso nunca va solo (`CLAUDE.md` §3, tres casos en un día).
    """
    ms = []
    for _ in range(bucles):
        t0 = time.perf_counter()
        s = 0
        for i in range(2_000_000):
            s += i * i
        ms.append((time.perf_counter() - t0) * 1000)
    return ms


def testigo_nivel():
    """Nivel de carga de la MÁQUINA: un lanzamiento de proceso.

    Con tope propio: «un testigo que puede tumbar la medición no es un testigo»
    (P3 agotó un timeout de 60 s midiendo esto).
    """
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO, check=False)
    except Exception:
        return TOPE_TESTIGO * 1000, True
    return (time.perf_counter() - t0) * 1000, False


# ------------------------------------------------------------------ utiles

def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def _docker(sub, tope=25.0):
    try:
        p = subprocess.run(["docker"] + sub, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace",
                           timeout=tope, check=False)
        return p.returncode, (p.stdout or "")
    except Exception:
        return None, ""


def existe(nombre):
    """`-a`: incluye el contenedor CREADO Y NO ARRANCADO, que `docker ps` no
    lista y que la deducción por montajes no podía ver nunca."""
    return bool(_docker(["ps", "-a", "-q", "--filter", f"name=^{nombre}$"])[1].strip())


def vivo(nombre):
    return bool(_docker(["ps", "-q", "--filter", f"name=^{nombre}$"])[1].strip())


def espera(cond, tope=PACIENCIA, paso=0.05):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < tope:
        if cond():
            return True
        time.sleep(paso)
    return False


def censo():
    return [l for l in _docker(
        ["ps", "-a", "--format", "{{.Names}}\t{{.Status}}"])[1].splitlines() if l.strip()]


def argv_de(nombre, d, orden="sleep 120"):
    """La misma forma que construye `_argv_docker`, con `sh` por entrypoint."""
    return ["docker", "run", "--rm", "--init", "--network", "none",
            "--name", nombre,
            "--mount", f"type=bind,source={d.replace(os.sep, '/')},target=/trabajo",
            "-w", "/trabajo", "--entrypoint", "sh", IMAGEN, "-c", orden]


def lanza(argv, caja):
    """Un salto en su propio hilo, como hace `servicio.py`.

    **Espera a que el `Popen` esté REGISTRADO, no a que el hilo arranque.** La
    primera versión de este arnés esperaba solo al hilo, y con eso M4 cancelaba
    *antes* del `Popen`: `cancelar_hilo` devolvía `False` en 0,01 ms, `ejecutar`
    salía por la marca sin lanzar nada y **no llegaba a existir ningún
    contenedor** — 0 huérfanos de 9 que no probaban nada, porque la carrera que
    hay que reproducir es la OTRA: el cliente ya corre y el contenedor todavía
    no existe. Es la trampa 25 en su forma de arnés: dos causas distintas con la
    misma pinta de éxito.
    """
    listo = threading.Event()

    def corre():
        listo.set()
        caja["r"] = invocacion.ejecutar(argv, timeout=PACIENCIA * 2)
        invocacion.olvidar_hilo()

    h = threading.Thread(target=corre, daemon=True)
    h.start()
    listo.wait(PACIENCIA)
    espera(lambda: h.ident in invocacion._EN_VUELO, tope=PACIENCIA, paso=0.001)
    return h


def limpia(h, nombre, d):
    try:
        invocacion.cancelar_hilo(h.ident)
    except Exception:
        pass
    invocacion.barrer_contenedor(nombre)
    h.join(timeout=PACIENCIA)
    shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------- M1 control

def m1_solo_el_cliente(n=N):
    """La línea base de N-a: matar el ÁRBOL del cliente y nada más.

    MEDIDO por ella: contenedor **vivo 9 de 9**. Si esto dejara de reproducirse
    es que la premisa entera dejó de valer, y habría que decirlo antes que nada.
    """
    filas = []
    for i in range(n):
        d = tempfile.mkdtemp(prefix="a4-m1-")
        nom = invocacion.nombre_de_contenedor()
        caja = {}
        h = lanza(argv_de(nom, d), caja)
        arranco = espera(lambda: vivo(nom))
        proc = invocacion._EN_VUELO.get(h.ident, (None, None))[0]
        t0 = time.perf_counter()
        if proc is not None:
            invocacion._matar_arbol(proc)
        ms = (time.perf_counter() - t0) * 1000
        time.sleep(2.0)
        filas.append({"i": i, "arranco": arranco, "ms_matar_cliente": round(ms, 2),
                      "contenedor_vivo_2s_despues": vivo(nom)})
        limpia(h, nom, d)
    return filas


# ----------------------------------------------------- M2 el remedio de a4

def m2_por_nombre_declarado(n=N):
    """`cancelar_hilo` con el identificador declarado. Comparable con los
    527,2 ms de N-a **con la salvedad de tanda**: son dos tandas distintas y
    hay otro agente en la máquina (`CLAUDE.md` §3)."""
    filas = []
    for i in range(n):
        d = tempfile.mkdtemp(prefix="a4-m2-")
        nom = invocacion.nombre_de_contenedor()
        caja = {}
        h = lanza(argv_de(nom, d), caja)
        arranco = espera(lambda: vivo(nom))
        t0 = time.perf_counter()
        habia = invocacion.cancelar_hilo(h.ident)
        ms = (time.perf_counter() - t0) * 1000
        h.join(timeout=PACIENCIA)
        muerto = espera(lambda: not existe(nom), tope=GRACIA)
        filas.append({"i": i, "arranco": arranco, "habia_asa": habia,
                      "ms_cancelar": round(ms, 2),
                      "contenedor_muerto": muerto,
                      "cliente_muerto": not h.is_alive(),
                      "motivo": caja.get("r").motivo if caja.get("r") else None})
        limpia(h, nom, d)
    return filas


# ------------------------------------------- M3 coste de IDENTIFICAR, A/B

def _deduccion_montajes(argv):
    """Copia fiel de la identificación que había en `invocacion` antes del a4
    (`_fuentes_de_montaje` + `_victimas`). Vive aquí y no en el producto porque
    lo que se mide es la vía **sustituida**, no una que siga en uso.
    """
    fuentes = set()
    for i, a in enumerate(argv):
        if a != "--mount" or i + 1 >= len(argv):
            continue
        op = [t.strip() for t in argv[i + 1].split(",")]
        if "readonly" in op or "ro=true" in op or "ro" in op:
            continue
        for trozo in op:
            k, _, v = trozo.partition("=")
            if k.strip() in ("source", "src") and v:
                fuentes.add(os.path.normcase(os.path.normpath(v)))
    if not fuentes:
        return []
    ids = [x for x in _docker(["ps", "-q"])[1].split() if x]
    if not ids:
        return []
    det = _docker(["inspect", "--format",
                   "{{.Id}}\t{{range .Mounts}}{{.Source}}\t{{end}}"] + ids)[1]
    fuera = []
    for linea in det.splitlines():
        campos = [c for c in linea.strip().split("\t") if c]
        if campos and {os.path.normcase(os.path.normpath(c))
                       for c in campos[1:]} & fuentes:
            fuera.append(campos[0])
    return fuera


def m3_coste_de_identificar(n=N):
    """Solo la IDENTIFICACIÓN, con un contenedor real en pie y los del proyecto.

    No incluye el `docker kill`, que es el mismo por las dos vías. Lo que se
    compara es lo que la declaración se ahorra: leer el demonio entero.
    """
    d = tempfile.mkdtemp(prefix="a4-m3-")
    nom = invocacion.nombre_de_contenedor()
    caja = {}
    h = lanza(argv_de(nom, d), caja)
    espera(lambda: vivo(nom))
    argv = argv_de(nom, d)
    ded, dec = [], []
    aciertos_ded = aciertos_dec = 0
    try:
        for _ in range(n):
            t0 = time.perf_counter()
            v = _deduccion_montajes(argv)
            ded.append((time.perf_counter() - t0) * 1000)
            aciertos_ded += 1 if v else 0
            t0 = time.perf_counter()
            x = invocacion._nombre_contenedor_de(argv)
            dec.append((time.perf_counter() - t0) * 1000)
            aciertos_dec += 1 if x == nom else 0
    finally:
        limpia(h, nom, d)
    return {"n": n, "contenedores_en_la_maquina": len(censo()),
            "deduccion_por_montajes_ms": med(ded),
            "declaracion_por_nombre_ms": med(dec),
            "aciertos_deduccion": aciertos_ded, "aciertos_declaracion": aciertos_dec,
            "veces": round(med(ded) / med(dec), 1) if med(dec) else None}


# ------------------------------------------------- M4 carrera de arranque

def m4_carrera_de_arranque(n=N):
    """Cancelar SIN esperar a que el contenedor exista.

    N-a: 1 huérfano de 9 en la primera tanda, 0 de 9 tras su arreglo. Aquí se
    cuenta con `docker ps -a`, que ve además el estado **creado y no
    arrancado** — el que `docker ps` nunca listó.
    """
    filas = []
    for i in range(n):
        d = tempfile.mkdtemp(prefix="a4-m4-")
        nom = invocacion.nombre_de_contenedor()
        caja = {}
        # `lanza` deja el `Popen` ya registrado: el cliente CORRE. Lo que no
        # está es el contenedor, y ésa es la ventana.
        h = lanza(argv_de(nom, d), caja)
        antes = existe(nom)
        t0 = time.perf_counter()
        habia = invocacion.cancelar_hilo(h.ident)
        ms = (time.perf_counter() - t0) * 1000
        h.join(timeout=PACIENCIA)
        limpio = espera(lambda: not existe(nom), tope=GRACIA)
        filas.append({"i": i, "ms_cancelar": round(ms, 2), "habia_asa": habia,
                      "huerfano": not limpio,
                      "existia_al_cancelar": antes,
                      "motivo": caja.get("r").motivo if caja.get("r") else None})
        limpia(h, nom, d)
    return filas


# --------------------------------------------------------------- M5 vecino

def m5_el_vecino_sobrevive(n=N):
    """Lo que N-a no pudo comprobar.

    Las dos conversiones comparten hasta el directorio de trabajo — el peor
    caso, que en producción no ocurre porque el desechable de R18 es privado —
    y aun así solo debe morir la cancelada.
    """
    filas = []
    for i in range(n):
        d = tempfile.mkdtemp(prefix="a4-m5-")
        n1 = invocacion.nombre_de_contenedor()
        n2 = invocacion.nombre_de_contenedor()
        c1, c2 = {}, {}
        h1 = lanza(argv_de(n1, d), c1)
        h2 = lanza(argv_de(n2, d), c2)
        arrancaron = espera(lambda: vivo(n1) and vivo(n2))
        invocacion.cancelar_hilo(h1.ident)
        h1.join(timeout=PACIENCIA)
        muerto1 = espera(lambda: not existe(n1), tope=GRACIA)
        filas.append({"i": i, "arrancaron_los_dos": arrancaron,
                      "cancelado_muerto": muerto1,
                      "vecino_vivo": vivo(n2)})
        for h, nom in ((h1, n1), (h2, n2)):
            try:
                invocacion.cancelar_hilo(h.ident)
            except Exception:
                pass
            invocacion.barrer_contenedor(nom)
            h.join(timeout=PACIENCIA)
        shutil.rmtree(d, ignore_errors=True)
    return filas


# -------------------------------- M7 las DOS defensas, una contra la otra

def m7_espera_frente_a_barrido(n=N):
    """¿Qué aporta cada mitad? Se apagan por separado y se cuentan huérfanos.

    En M4 el barrido **nunca llega a dispararse**: la espera encuentra el
    contenedor y `docker kill` lo mata, así que M4 no mide el barrido, mide la
    espera. Para que el barrido tenga algo que hacer hay que devolver la
    cancelación al régimen de antes de N-a —`ESPERA_CONTENEDOR = 0`—, que es
    justo el que le dejó 1 huérfano de 9.

    Tres brazos, con el cliente ya corriendo y el contenedor todavía no:

      * `sin_nada`   — ni espera ni barrido: el comportamiento de antes de C34.
      * `solo_barrido` — sin espera, con `docker rm -f` del nombre declarado.
      * `solo_espera`  — lo que va en producción (ESPERA_CONTENEDOR = 3 s).
    """
    def una(brazo, espera_s, con_barrido):
        filas = []
        guard_e = invocacion.ESPERA_CONTENEDOR
        guard_b = invocacion._barrer_contenedor_de
        invocacion.ESPERA_CONTENEDOR = espera_s
        if not con_barrido:
            invocacion._barrer_contenedor_de = lambda argv: []
        try:
            for i in range(n):
                d = tempfile.mkdtemp(prefix=f"a4-m7{brazo[:3]}-")
                nom = invocacion.nombre_de_contenedor()
                caja = {}
                h = lanza(argv_de(nom, d), caja)
                antes = existe(nom)
                t0 = time.perf_counter()
                invocacion.cancelar_hilo(h.ident)
                ms = (time.perf_counter() - t0) * 1000
                h.join(timeout=PACIENCIA)
                # Se espera a que el demonio termine de decidir, y ENTONCES se
                # mira. Un `--rm` asíncrono no es un huérfano.
                quedo = espera(lambda: not existe(nom), tope=GRACIA)
                estado = _docker(["ps", "-a", "--format", "{{.Status}}",
                                  "--filter", f"name=^{nom}$"])[1].strip()
                filas.append({"i": i, "brazo": brazo, "ms_cancelar": round(ms, 2),
                              "existia_al_cancelar": antes,
                              "huerfano": not quedo, "estado": estado})
                limpia(h, nom, d)
        finally:
            invocacion.ESPERA_CONTENEDOR = guard_e
            invocacion._barrer_contenedor_de = guard_b
        return filas

    return {"sin_nada": una("sin_nada", 0.0, False),
            "solo_barrido": una("solo_barrido", 0.0, True),
            "solo_espera": una("solo_espera", 3.0, False)}


# ------------------------------------------ M6 coste en el camino normal

def m6_coste_normal(n=2001):
    """Lo que cuesta DECLARAR el identificador en cada conversión.

    Es lo único del a4 que se paga siempre; todo lo demás solo corre al
    cancelar o al agotarse el tope.
    """
    m = LibreOfficeEnContenedor()
    m.imagen = IMAGEN
    ac, arg = [], []
    for _ in range(n):
        t0 = time.perf_counter()
        invocacion.nombre_de_contenedor()
        ac.append((time.perf_counter() - t0) * 1e6)
        t0 = time.perf_counter()
        m._argv_docker("D:/tmp/e.docx", "D:/tmp/t", "e.docx", ["soffice"], 100)
        arg.append((time.perf_counter() - t0) * 1e6)
    return {"n": n, "acuñar_el_nombre_us": med(ac),
            "_argv_docker_completo_us": med(arg)}


# ------------------------------------------------------------------- main

def main():
    saltar = set()
    for a in sys.argv[1:]:
        if a.startswith("--saltar"):
            saltar = {x.strip() for x in a.split("=", 1)[-1].split(",") if x.strip()}

    res = {"n": N, "imagen": IMAGEN, "censo_antes": censo()}
    d0 = testigo_deriva()
    niv0, tope0 = testigo_nivel()

    if "m6" not in saltar:
        res["M6_coste_normal"] = m6_coste_normal()
    if "m1" not in saltar:
        res["M1_solo_el_cliente"] = m1_solo_el_cliente()
    if "m2" not in saltar:
        res["M2_por_nombre_declarado"] = m2_por_nombre_declarado()
    if "m3" not in saltar:
        res["M3_coste_de_identificar"] = m3_coste_de_identificar()
    if "m4" not in saltar:
        res["M4_carrera_de_arranque"] = m4_carrera_de_arranque()
    if "m5" not in saltar:
        res["M5_vecino"] = m5_el_vecino_sobrevive()
    if "m7" not in saltar:
        res["M7_espera_frente_a_barrido"] = m7_espera_frente_a_barrido()

    d1 = testigo_deriva()
    niv1, tope1 = testigo_nivel()
    deriva = med(d1) / med(d0) if med(d0) else None
    res["testigos"] = {
        "deriva_antes_ms": med(d0), "deriva_despues_ms": med(d1),
        "deriva": round(deriva, 3) if deriva else None,
        "nivel_antes_ms": round(niv0, 2), "nivel_despues_ms": round(niv1, 2),
        "testigo_agotado": bool(tope0 or tope1),
        # `CLAUDE.md` §3: con la sesión de escritorio remoto activa TODO sale
        # `SUCIA`. Es estructural, no un fallo.
        "etiqueta": "SUCIA",
    }
    res["censo_despues"] = censo()
    # Un huérfano MÍO tiene la forma que acuña `nombre_de_contenedor()`. El
    # prefijo a secas no vale: los cinco contenedores permanentes del proyecto
    # (`filex-snapotter`, `filex-gotenberg`…) también empiezan por `filex-`.
    res["huerfanos_de_filex"] = [
        l for l in res["censo_despues"]
        if invocacion._RE_NOMBRE.match(l.split("\t")[0])]

    with open(os.path.join(AQUI, "a4_medidas.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

    print(json.dumps(res, indent=1, ensure_ascii=False))
    for clave, campo in (("M1_solo_el_cliente", "contenedor_vivo_2s_despues"),
                         ("M2_por_nombre_declarado", "contenedor_muerto"),
                         ("M4_carrera_de_arranque", "huerfano"),
                         ("M5_vecino", "vecino_vivo")):
        if clave in res:
            v = [f[campo] for f in res[clave]]
            print(f"{clave}.{campo}: {sum(1 for x in v if x)} de {len(v)}")
    for brazo, filas in (res.get("M7_espera_frente_a_barrido") or {}).items():
        h = sum(1 for f in filas if f["huerfano"])
        print(f"M7.{brazo}: huerfanos {h} de {len(filas)}")


if __name__ == "__main__":
    main()
