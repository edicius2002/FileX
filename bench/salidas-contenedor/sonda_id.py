"""Sonda S — ¿cómo se comportan de verdad `--cidfile` y `--name`?

`CLAUDE.md` §5: *«Sondear capacidades en ejecución, no deducirlas»*. La
documentación de Docker dice qué hacen las dos banderas; lo que decide cuál
sirve para identificar un contenedor que hay que MATAR es **cuándo** el
identificador está disponible y **qué pasa cuando el cliente muere**.

No usa la GPU. Todos los contenedores llevan `--name filexq-sonda-*` y se
censan al final: R7 del encargo (no dejar huérfanos) también vale para la sonda.

Salida: `sonda_id.json` en este mismo directorio.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
IMAGEN = "alpine:latest"          # barata: la sonda mide semántica de Docker, no motores
TOPE = 30.0


def docker(*args, tope=TOPE):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(["docker", *args], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace",
                           timeout=tope, check=False)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip(), \
            (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return None, "", "TIMEOUT", (time.perf_counter() - t0) * 1000


def lanzar(args):
    """Cliente `docker run` en segundo plano, sin shell, con stdin cerrado."""
    return subprocess.Popen(["docker", *args], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, errors="replace")


def limpiar(nombre):
    docker("kill", nombre, tope=15)
    docker("rm", "-f", nombre, tope=15)


def s1_nombre_unico():
    """¿Docker RECHAZA un segundo contenedor con el mismo `--name`?

    Si lo rechaza, la unicidad no es una promesa del generador de nombres: la
    impone el demonio, y una colisión sería un error visible, no un atropello
    silencioso (que es la forma de la trampa 26).
    """
    n = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
    p = lanzar(["run", "--rm", "--name", n, IMAGEN, "sleep", "20"])
    time.sleep(2.0)
    rc, out, err, _ = docker("run", "--rm", "--name", n, IMAGEN, "true")
    res = {"nombre": n, "rc_segundo": rc, "err_segundo": err[:300],
           "rechaza_duplicado": rc not in (0, None)}
    limpiar(n)
    try:
        p.wait(timeout=15)
    except Exception:
        p.kill()
    return res


def s2_kill_por_nombre():
    """¿`docker kill <nombre>` mata igual que `docker kill <id>`?"""
    n = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
    p = lanzar(["run", "--rm", "--name", n, IMAGEN, "sleep", "60"])
    time.sleep(2.0)
    rc, out, err, ms = docker("kill", n)
    time.sleep(1.5)
    rc2, out2, _, _ = docker("ps", "-q", "--filter", f"name=^{n}$")
    res = {"nombre": n, "rc_kill": rc, "ms_kill": round(ms, 1),
           "err_kill": err[:200], "vivo_despues": bool(out2.strip())}
    limpiar(n)
    try:
        p.wait(timeout=15)
    except Exception:
        p.kill()
    return res


def s3_cidfile():
    """`--cidfile`: cuándo aparece, qué trae, y si Docker se niega si ya existe.

    Tres preguntas que la documentación no contesta para este caso de uso:
    1. ¿El fichero está escrito ANTES de que el contenedor exista?
    2. ¿Lo borra el cliente al salir con `--rm`? Si lo borra, quien cancele
       tarde se queda sin identificador.
    3. ¿Se niega Docker si el fichero ya existe? Si se niega, el fichero es
       un recurso más que hay que gestionar antes de arrancar.
    """
    d = tempfile.mkdtemp(prefix="filexq-cid-")
    cid = os.path.join(d, "cid")
    n = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
    t0 = time.perf_counter()
    p = lanzar(["run", "--rm", "--cidfile", cid, "--name", n, IMAGEN, "sleep", "25"])

    # ¿Cuándo aparece el fichero, y cuándo el contenedor está matable?
    ms_fichero = ms_contenido = ms_matable = None
    contenido = ""
    limite = time.perf_counter() + 20.0
    while time.perf_counter() < limite:
        if ms_fichero is None and os.path.exists(cid):
            ms_fichero = (time.perf_counter() - t0) * 1000
        if ms_fichero is not None and not contenido:
            try:
                contenido = open(cid, encoding="utf-8").read().strip()
            except Exception:
                contenido = ""
            if contenido:
                ms_contenido = (time.perf_counter() - t0) * 1000
        if ms_matable is None:
            rc, out, _, _ = docker("ps", "-q", "--filter", f"name=^{n}$", tope=10)
            if out.strip():
                ms_matable = (time.perf_counter() - t0) * 1000
        if ms_contenido is not None and ms_matable is not None:
            break
        time.sleep(0.05)

    # ¿Docker se niega si el cidfile ya existe?
    rc_ex, _, err_ex, _ = docker("run", "--rm", "--cidfile", cid, IMAGEN, "true")

    # ¿Sobrevive el cidfile a la muerte del contenedor con `--rm`?
    docker("kill", n)
    try:
        p.wait(timeout=20)
    except Exception:
        p.kill()
    time.sleep(1.0)
    sobrevive = os.path.exists(cid)

    res = {"ms_fichero_existe": None if ms_fichero is None else round(ms_fichero, 1),
           "ms_fichero_con_id": None if ms_contenido is None else round(ms_contenido, 1),
           "ms_nombre_matable": None if ms_matable is None else round(ms_matable, 1),
           "id_len": len(contenido), "id_prefijo": contenido[:12],
           "rc_si_el_cidfile_existe": rc_ex,
           "rechaza_si_existe": rc_ex not in (0, None),
           "err_si_existe": err_ex[:300],
           "cidfile_sobrevive_al_rm": sobrevive}
    limpiar(n)
    try:
        os.remove(cid)
    except Exception:
        pass
    try:
        os.rmdir(d)
    except Exception:
        pass
    return res


def s4_carrera_arranque(n=9):
    """La ventana de arranque, medida por las TRES vías a la vez.

    N-a midió que `docker ps` no ve el contenedor durante cientos de ms tras
    lanzar el cliente, y eso le costó 1 huérfano de 9. Aquí se cronometra
    cuánto tarda cada identificador en ser utilizable, sobre la MISMA
    invocación: nombre (`docker ps --filter name=`), cidfile (fichero con
    contenido) y barrido de montajes (`docker ps -q` + `docker inspect`).
    """
    filas = []
    for i in range(n):
        d = tempfile.mkdtemp(prefix="filexq-car-")
        cid = os.path.join(d, "cid")
        montaje = os.path.join(d, "m")
        os.makedirs(montaje, exist_ok=True)
        src = montaje.replace("\\", "/")
        nom = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
        t0 = time.perf_counter()
        p = lanzar(["run", "--rm", "--init", "--network", "none",
                    "--cidfile", cid, "--name", nom,
                    "--mount", f"type=bind,source={src},target=/trabajo",
                    IMAGEN, "sleep", "25"])
        m_nom = m_cid = m_mnt = None
        limite = time.perf_counter() + 20.0
        while time.perf_counter() < limite:
            if m_cid is None and os.path.exists(cid):
                try:
                    if open(cid, encoding="utf-8").read().strip():
                        m_cid = (time.perf_counter() - t0) * 1000
                except Exception:
                    pass
            if m_nom is None:
                _, out, _, _ = docker("ps", "-q", "--filter", f"name=^{nom}$", tope=10)
                if out.strip():
                    m_nom = (time.perf_counter() - t0) * 1000
            if m_mnt is None:
                _, ids, _, _ = docker("ps", "-q", tope=10)
                lista = [x for x in ids.split() if x]
                if lista:
                    _, det, _, _ = docker(
                        "inspect", "--format",
                        "{{.Id}}\t{{range .Mounts}}{{.Source}}\t{{end}}", *lista, tope=15)
                    for linea in det.splitlines():
                        campos = [c for c in linea.strip().split("\t") if c]
                        srcs = {os.path.normcase(os.path.normpath(c)) for c in campos[1:]}
                        if os.path.normcase(os.path.normpath(montaje)) in srcs:
                            m_mnt = (time.perf_counter() - t0) * 1000
                            break
            if m_nom is not None and m_cid is not None and m_mnt is not None:
                break
            time.sleep(0.03)
        filas.append({"i": i,
                      "ms_nombre": None if m_nom is None else round(m_nom, 1),
                      "ms_cidfile": None if m_cid is None else round(m_cid, 1),
                      "ms_montaje": None if m_mnt is None else round(m_mnt, 1)})
        docker("kill", nom)
        try:
            p.wait(timeout=20)
        except Exception:
            p.kill()
        limpiar(nom)
        for f in (cid,):
            try:
                os.remove(f)
            except Exception:
                pass
        try:
            os.rmdir(montaje)
            os.rmdir(d)
        except Exception:
            pass
    return filas


def s5_kill_por_nombre_sin_cliente():
    """¿Se puede matar por nombre cuando el CLIENTE ya está muerto?

    Es el caso real: `_matar_arbol` puede llegar antes. Si el nombre dejara de
    resolver al morir el cliente, la vía no valdría para nada.
    """
    n = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
    p = lanzar(["run", "--rm", "--name", n, IMAGEN, "sleep", "60"])
    time.sleep(2.5)
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=15, check=False)
    else:
        p.kill()
    time.sleep(1.5)
    _, vivo, _, _ = docker("ps", "-q", "--filter", f"name=^{n}$")
    rc, _, err, ms = docker("kill", n)
    time.sleep(1.5)
    _, vivo2, _, _ = docker("ps", "-q", "--filter", f"name=^{n}$")
    res = {"vivo_tras_matar_al_cliente": bool(vivo.strip()),
           "rc_kill_por_nombre": rc, "ms_kill": round(ms, 1), "err": err[:200],
           "vivo_despues_del_kill": bool(vivo2.strip())}
    limpiar(n)
    try:
        p.wait(timeout=10)
    except Exception:
        pass
    return res


def s6_estado_creado_y_no_arrancado():
    """El estado que `docker ps` NO lista, sondeado a propósito y sin carreras.

    En M7 aparece de forma intermitente y los dos observadores del arnés llegan
    a discrepar sobre él —dos `docker ps -a` consecutivos, uno lo ve y el otro
    no—, así que apoyarse en esa observación sería apoyarse en una carrera.
    Aquí se construye el estado a mano con `docker create`, que es exactamente
    lo que deja el cliente de `docker run` cuando lo matan entre el **create** y
    el **start**, y se pregunta lo único que importa:

      * ¿lo lista `docker ps`?   -> si no, el censo de huérfanos que use `ps`
        (sin `-a`) es ciego a él.
      * ¿lo mata `docker kill`?  -> si no, la vía de cancelación no lo alcanza.
      * ¿lo borra `docker rm -f`? -> si sí, ésa es la única vía, y **exige tener
        un identificador**, que es justo lo que la deducción por bind mount
        perdía al morir el cliente.
    """
    n = f"filexq-sonda-{uuid.uuid4().hex[:12]}"
    rc_crear, _, err_crear, _ = docker("create", "--name", n, IMAGEN, "sleep", "60")
    _, ps, _, _ = docker("ps", "-q", "--filter", f"name=^{n}$")
    _, psa, _, _ = docker("ps", "-a", "-q", "--filter", f"name=^{n}$")
    _, estado, _, _ = docker("ps", "-a", "--format", "{{.Status}}",
                             "--filter", f"name=^{n}$")
    rc_kill, _, err_kill, ms_kill = docker("kill", n)
    rc_rm, _, err_rm, ms_rm = docker("rm", "-f", n)
    _, queda, _, _ = docker("ps", "-a", "-q", "--filter", f"name=^{n}$")
    res = {"rc_create": rc_crear, "err_create": err_crear[:200],
           "lo_lista_docker_ps": bool(ps.strip()),
           "lo_lista_docker_ps_a": bool(psa.strip()),
           "estado": estado.strip(),
           "rc_kill": rc_kill, "err_kill": err_kill[:200],
           "ms_kill": round(ms_kill, 1),
           "rc_rm_f": rc_rm, "err_rm_f": err_rm[:200], "ms_rm_f": round(ms_rm, 1),
           "queda_despues": bool(queda.strip())}
    limpiar(n)
    return res


def censo():
    _, out, _, _ = docker("ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}")
    return [l for l in out.splitlines() if l.strip()]


def main():
    res = {"imagen": IMAGEN, "censo_antes": censo()}
    res["S1_nombre_unico"] = s1_nombre_unico()
    res["S2_kill_por_nombre"] = s2_kill_por_nombre()
    res["S3_cidfile"] = s3_cidfile()
    res["S4_carrera_arranque"] = s4_carrera_arranque(9)
    res["S5_kill_sin_cliente"] = s5_kill_por_nombre_sin_cliente()
    res["S6_creado_y_no_arrancado"] = s6_estado_creado_y_no_arrancado()
    res["censo_despues"] = censo()
    with open(os.path.join(AQUI, "sonda_id.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "S4_carrera_arranque"},
                     indent=1, ensure_ascii=False))
    print("S4 (ms hasta que cada identificador sirve):")
    for fila in res["S4_carrera_arranque"]:
        print(" ", fila)


if __name__ == "__main__":
    main()
