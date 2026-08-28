"""Las dos preguntas que un cerrojo entre procesos tiene que contestar.

**A. ¿Y si el dueño se muere?** `taskkill /F` no ejecuta ningún `finally`. Con
el lock de GPU viejo eso dejaba un huérfano y el siguiente agente esperaba
**900 s** (`bench/lock-de-maquina.md` §1.2). Aquí se mata a un `filex` **a
mitad de la conversión** y se mide cuánto tarda el siguiente en entrar.

**B. ¿Y el que no coopera?** Es la lección que dejó escrita L1: mover el
fichero de sitio no excluye a quien nunca lo iba a tomar. Un proceso que NO es
FileX abre la ruta de salida y la mantiene abierta; se mide qué hace FileX
antes y después del arreglo.

    python bench/salidas-cerrojo/huerfano_y_deteccion.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))

TOPE = 600


def _sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


# ------------------------------------------------------------------- papeles

def papel_convertidor(entrada: str, salida: str, dir_raiz: str, listo: str) -> int:
    """Un `filex` de verdad. Avisa cuando arranca la conversión."""
    sys.path.insert(0, RAIZ)
    from filex.nucleo import FileX

    fx = FileX(raices_lectura=[dir_raiz])
    open(listo, "w").close()
    print("CONVIRTIENDO", flush=True)
    t0 = time.perf_counter()
    conv = fx.convertir(entrada, salida, {}, timeout=300)
    print(json.dumps({"ok": conv.ok, "motivo": conv.motivo,
                      "veredicto": conv.veredicto,
                      "ms": round((time.perf_counter() - t0) * 1000, 1)},
                     ensure_ascii=False), flush=True)
    return 0


def papel_tercero(ruta: str) -> int:
    """Un proceso que NO es FileX y escribe en la misma ruta. No toma candados
    ni sabe que existen: es el `chrome.exe` bajando un fichero."""
    f = open(ruta, "wb")
    f.write(b"SOY-UN-TERCERO" + b"\0" * 4000)
    f.flush()
    print("TERCERO: fichero abierto y ocupado", flush=True)
    time.sleep(120)
    return 0


def _lanzar(argv: list[str], entorno=None) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, os.path.abspath(__file__)] + argv,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", cwd=RAIZ,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", **(entorno or {})))


def _matar(p: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    else:
        p.kill()
    try:
        p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        pass


# ------------------------------------------------------------------- escenas

def escena_huerfano(base: str, res: dict) -> None:
    sys.path.insert(0, RAIZ)
    from filex import nucleo

    print("\n===== A. EL DUEÑO MUERE A MITAD DE LA CONVERSIÓN =====")
    dsal = os.path.join(base, "sal_a")
    shutil.rmtree(dsal, ignore_errors=True)
    os.makedirs(dsal)
    salida = os.path.join(dsal, "s.webp")
    grande = os.path.join(base, "patologico_16bit.tif")
    listo = os.path.join(base, "_listo_a")
    if os.path.exists(listo):
        os.remove(listo)

    import glob
    import tempfile

    def _desechables() -> int:
        # R18 deja un `mkdtemp(prefix="filex-")` por conversión y lo borra en su
        # `finally`. Un `taskkill /F` no ejecuta ningún `finally`: cuento antes
        # y después para SABER si el matado se lleva la basura por delante.
        return len([x for x in glob.glob(os.path.join(tempfile.gettempdir(), "filex-*"))
                    if os.path.isdir(x) and "-" not in os.path.basename(x)[6:]])

    desechables_antes = _desechables()
    p = _lanzar(["--papel", "convertidor", "--entrada", grande,
                 "--salida", salida, "--dir", base, "--listo", listo],
                {"FILEX_CERROJO_DESTINO": "maquina"})
    p.stdout.readline()                       # "CONVIRTIENDO"
    time.sleep(0.35)                          # a mitad: el TIFF tarda ~1,5 s
    fichero_lock = nucleo._fichero_cerrojo(nucleo._clave_destino(salida))
    tomado_por_el = os.path.exists(fichero_lock)
    contenido = ""
    if tomado_por_el:
        with open(fichero_lock, "rb") as f:
            contenido = f.read(120).decode("utf-8", "replace").strip()
    print(f"  candado tomado por el que va a morir: {tomado_por_el}  -> {contenido!r}")
    _matar(p)
    sobrevive = os.path.exists(fichero_lock)
    # ¿Murió DE VERDAD a mitad? Si hubiera terminado, su `finally` habría
    # soltado el candado y esto no probaría nada. La prueba es que no llegó a
    # imprimir su línea de resultado.
    resto = (p.stdout.read() or "").strip()
    a_mitad = "ok" not in resto
    print(f"  muerto con taskkill /F (rc={p.returncode}); murió a mitad de la "
          f"conversión: {a_mitad} (dijo {resto[:60]!r})")
    print(f"  el fichero de candado sigue ahí: {sobrevive}")

    # El siguiente: mismo destino, otra entrada.
    t0 = time.perf_counter()
    ok = nucleo._reservar_destino(salida)
    dt = (time.perf_counter() - t0) * 1e6
    nucleo._soltar_destino(salida)
    print(f"  el SIGUIENTE toma el candado: {ok}   en {dt:.1f} us")

    listo2 = os.path.join(base, "_listo_a2")
    if os.path.exists(listo2):
        os.remove(listo2)
    q = _lanzar(["--papel", "convertidor", "--entrada",
                 os.path.join(base, "tipico.png"), "--salida", salida,
                 "--dir", base, "--listo", listo2],
                {"FILEX_CERROJO_DESTINO": "maquina"})
    out, _ = q.communicate(timeout=TOPE)
    fila = json.loads(out.strip().splitlines()[-1])
    print(f"  y CONVIERTE de verdad: {fila}")
    sobras = sorted(os.listdir(dsal))
    print(f"  en el destino: {sobras}")
    fugados = _desechables() - desechables_antes
    print(f"  desechables de R18 que el taskkill dejó sin borrar: {fugados}")
    res["A_desechables_fugados"] = fugados
    res["A_huerfano"] = {
        "candado_existia_antes_de_matar": tomado_por_el,
        "contenido_del_candado": contenido,
        "murio_a_mitad": a_mitad,
        "fichero_de_candado_sobrevive_al_taskkill": sobrevive,
        "el_siguiente_lo_toma": ok,
        "recuperacion_us": round(dt, 1),
        "conversion_siguiente": fila,
        "ficheros_en_destino": sobras,
    }


def escena_tercero(base: str, res: dict) -> None:
    print("\n===== B. UN TERCERO QUE NO TOMA EL CANDADO =====")
    for modo in ("proceso", "maquina"):
        dsal = os.path.join(base, f"sal_b_{modo}")
        shutil.rmtree(dsal, ignore_errors=True)
        os.makedirs(dsal)
        salida = os.path.join(dsal, "s.webp")

        t = _lanzar(["--papel", "tercero", "--ruta", salida])
        t.stdout.readline()
        antes = (os.path.getsize(salida), _sha(salida))

        listo = os.path.join(base, f"_listo_b_{modo}")
        if os.path.exists(listo):
            os.remove(listo)
        p = _lanzar(["--papel", "convertidor", "--entrada",
                     os.path.join(base, "tipico.png"), "--salida", salida,
                     "--dir", base, "--listo", listo],
                    {"FILEX_CERROJO_DESTINO": modo})
        out, err = p.communicate(timeout=TOPE)
        try:
            fila = json.loads(out.strip().splitlines()[-1])
        except Exception:
            fila = {"error": out[-200:], "stderr": err[-300:]}
        despues = ((os.path.getsize(salida), _sha(salida))
                   if os.path.exists(salida) else (None, None))
        _matar(t)
        pisado = antes != despues
        print(f"  [{modo:<8}] filex dice {fila}")
        print(f"  [{modo:<8}] el fichero del tercero: antes {antes} -> después "
              f"{despues}   PISADO={pisado}")
        res[f"B_tercero[{modo}]"] = {"filex": fila, "antes": antes,
                                     "despues": despues, "pisado": pisado}

    # Control: sin nadie delante, la conversión tiene que salir.
    dsal = os.path.join(base, "sal_b_control")
    shutil.rmtree(dsal, ignore_errors=True)
    os.makedirs(dsal)
    salida = os.path.join(dsal, "s.webp")
    listo = os.path.join(base, "_listo_b_control")
    if os.path.exists(listo):
        os.remove(listo)
    p = _lanzar(["--papel", "convertidor", "--entrada",
                 os.path.join(base, "tipico.png"), "--salida", salida,
                 "--dir", base, "--listo", listo],
                {"FILEX_CERROJO_DESTINO": "maquina"})
    out, _ = p.communicate(timeout=TOPE)
    fila = json.loads(out.strip().splitlines()[-1])
    print(f"  [CONTROL ] sin tercero delante: {fila}  "
          f"bytes={os.path.getsize(salida) if os.path.exists(salida) else None}")
    res["B_control_sin_tercero"] = {
        "filex": fila,
        "bytes": os.path.getsize(salida) if os.path.exists(salida) else None}


def main() -> int:
    if "--papel" in sys.argv:
        i = sys.argv.index("--papel")
        papel = sys.argv[i + 1]
        arg = dict(zip(sys.argv[i + 2::2], sys.argv[i + 3::2]))
        if papel == "convertidor":
            return papel_convertidor(arg["--entrada"], arg["--salida"],
                                     arg["--dir"], arg["--listo"])
        if papel == "tercero":
            return papel_tercero(arg["--ruta"])
        return 2

    base = os.path.join(AQUI, "desechable", "huerfano")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    for n in ("tipico.png", "patologico_16bit.tif"):
        shutil.copy2(os.path.join(RAIZ, "corpus", "imagen", n),
                     os.path.join(base, n))

    res: dict = {}
    escena_huerfano(base, res)
    escena_tercero(base, res)
    with open(os.path.join(AQUI, "huerfano_y_deteccion.json"), "w",
              encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
