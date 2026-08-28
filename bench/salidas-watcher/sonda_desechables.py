#!/usr/bin/env python3
"""N14 — el desechable de R18 que un `taskkill /F` deja sin borrar.

N-b lo vio de pasada (`bench/cerrojo-de-maquina.md` §4.1) con una frase y un
número: *«desechables de R18 que el taskkill dejó sin borrar: 1»*. Aquí se
cuantifica y se cierra.

Cinco escenas, todas con procesos de verdad:

  A. **Cuánto se deja y dónde**: `n` conversiones matadas a mitad; se cuentan
     los directorios y los BYTES que quedan en `%TEMP%`.
  B. **El barrido bueno**: con el candado de vida, `barrer_huerfanos` los
     borra todos y no toca ninguno vivo.
  C. **El peligro, reproducido**: un barrido SIN comprobar si el dueño vive
     —el que uno escribiría por edad, o por prefijo a secas— borra el
     desechable de un `filex` que está convirtiendo. Es la trampa 26 con otro
     recurso, y sin esta escena la defensa no está probada, solo escrita.
  D. **El coste**: lo que añade el candado de vida por desechable y lo que
     tarda el barrido, medianas de n≥9 con los dos testigos de ruido.
  E. **El control negativo**: `FILEX_BARRER=0` deja los huérfanos donde
     estaban. Si esta escena no se distinguiera de la B, la B no probaría nada.

R21: se lista `%TEMP%` antes y después de todo.
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
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
HIJO = os.path.join(AQUI, "hijo_convierte.py")
sys.path.insert(0, RAIZ)


def desechables(base: str) -> list[str]:
    """Los desechables de R18, **sin el directorio de candados**.

    `cerrojo.directorio()` se llama `filex-destinos` y empieza por el mismo
    prefijo: la primera versión de esta sonda lo contaba como desechable, y la
    primera versión de `barrer_huerfanos` lo habría **borrado entero**. Está
    arreglado en el código y aquí; queda escrito porque el fallo lo encontró la
    medición, no la lectura.
    """
    from filex import cerrojo

    try:
        prohibido = os.path.normcase(os.path.abspath(cerrojo.directorio()))
    except OSError:
        prohibido = ""
    out = []
    try:
        for e in os.scandir(base):
            try:
                if not (e.is_dir(follow_symlinks=False)
                        and e.name.startswith("filex-")):
                    continue
                if os.path.normcase(os.path.abspath(e.path)) == prohibido:
                    continue
                out.append(e.path)
            except OSError:
                pass
    except OSError:
        pass
    return sorted(out)


def bytes_de(rutas) -> int:
    total = 0
    for r in rutas:
        for raiz, _d, fs in os.walk(r):
            for f in fs:
                try:
                    total += os.stat(os.path.join(raiz, f)).st_size
                except OSError:
                    pass
    return total


class Hijo:
    def __init__(self, entrada: str, salida: str, *, barrer: bool = True):
        # **Sin `FILEX_BARRER=0` la escena A no mide lo que dice**: cada hijo
        # nuevo barre al anterior en su `FileX.__init__`, y la cuenta de
        # huérfanos sale ×1 en vez de ×n. Se descubrió midiendo: 5 muertes
        # válidas dejaban 2 huérfanos.
        env = dict(os.environ)
        if not barrer:
            env["FILEX_BARRER"] = "0"
        self.p = subprocess.Popen(
            [sys.executable, HIJO, "--entrada", entrada, "--salida", salida],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
            env=env)
        self.lineas = []
        self.pid = None

    def esperar(self, marcador: str, tope: float = 180.0) -> bool:
        fin = time.monotonic() + tope
        while time.monotonic() < fin:
            linea = self.p.stdout.readline()
            if not linea:
                return False
            linea = linea.strip()
            self.lineas.append(linea)
            if linea.startswith("LISTO"):
                self.pid = int(linea.split()[1])
            if linea.startswith(marcador):
                return True
        return False

    def matar_duro(self) -> int:
        if os.name == "nt":
            r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.p.pid)],
                               stdin=subprocess.DEVNULL, capture_output=True,
                               timeout=60)
            rc = r.returncode
        else:
            self.p.kill()
            rc = -9
        try:
            self.p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        return rc

    def murio_a_mitad(self) -> bool:
        """La condición de la trampa 38: si llegó a imprimir `FIN`, terminó, y
        entonces su `finally` borró el desechable y la escena no prueba nada."""
        resto = ""
        try:
            resto = self.p.stdout.read() or ""
        except (OSError, ValueError):
            pass
        self.lineas += [x for x in resto.split("\n") if x.strip()]
        return not any(l.startswith("FIN") for l in self.lineas)


def esperar_desechable(base: str, previos: set, tope: float = 30.0,
                       con_contenido: bool = True):
    """Espera a que aparezca un desechable NUEVO, y con algo dentro.

    **Es la trampa 38 de este encargo.** «El hijo imprimió ARRANCA» no es la
    condición que hay que reproducir: entre ese `print` y el `mkdtemp` hay
    validación de rutas y planificación, y matar ahí no deja huérfano ninguno —
    saldrían ceros que parecen un éxito de la defensa y son un arnés que mide
    otra cosa. La condición es **que el directorio exista y el motor esté
    escribiendo dentro**.
    """
    fin = time.monotonic() + tope
    while time.monotonic() < fin:
        nuevos = [d for d in desechables(base) if d not in previos]
        for d in nuevos:
            try:
                dentro = os.listdir(d)
            except OSError:
                continue
            if dentro or not con_contenido:
                return d, dentro
        time.sleep(0.05)
    return None, []


# ==========================================================================
def escena_a(entrada: str, saldir: str, n: int, espera: float, log) -> dict:
    base = tempfile.gettempdir()
    antes = set(desechables(base))
    celdas = []
    for i in range(n):
        sal = os.path.join(saldir, f"a{i}.webp")
        previos = set(desechables(base))
        h = Hijo(entrada, sal, barrer=False)
        arranco = h.esperar("ARRANCA")
        d, dentro = esperar_desechable(base, previos)
        time.sleep(espera)                # dentro de la conversión, no antes
        rc = h.matar_duro()
        mitad = h.murio_a_mitad()
        celdas.append({"i": i, "arranco": arranco, "rc_taskkill": rc,
                       "murio_a_mitad": mitad,
                       "desechable_en_vuelo": d,
                       "contenido_al_matar": dentro,
                       "condicion_ok": bool(arranco and mitad and d),
                       "lineas": h.lineas[-3:]})
        log.write(f"[A{i}] arranco={arranco} rc={rc} murio_a_mitad={mitad} "
                  f"desechable={d} dentro={dentro}\n")
    despues = set(desechables(base))
    nuevos = sorted(despues - antes)
    r = {"escena": "A_cuanto_se_deja", "matados": n,
         "celdas_validas": sum(1 for c in celdas if c["condicion_ok"]),
         "huerfanos": len(nuevos), "bytes": bytes_de(nuevos),
         "rutas": nuevos, "celdas": celdas}
    log.write(json.dumps({k: v for k, v in r.items() if k != "celdas"},
                         ensure_ascii=False) + "\n")
    return r


def escena_b(huerfanos: list[str], entrada: str, saldir: str, log) -> dict:
    """Barrido bueno, **con un `filex` vivo en la misma tanda**."""
    from filex.trabajo import barrer_huerfanos

    base = tempfile.gettempdir()
    sal = os.path.join(saldir, "vivo.webp")
    previos = set(desechables(base))
    # `barrer=False` a propósito: si el vivo barriera al arrancar, los huérfanos
    # desaparecerían ANTES de la llamada que se quiere medir, y el experimento
    # mediría el arranque del hijo en vez del barrido del padre. Pasó en la
    # primera pasada: `huerfanos_borrados=6` con `parte.borrados=0`.
    vivo = Hijo(entrada, sal, barrer=False)
    arranco = vivo.esperar("ARRANCA")
    suyo, dentro = esperar_desechable(base, previos)
    antes = set(desechables(base))
    suyos = [suyo] if suyo else []
    parte = barrer_huerfanos()
    despues = set(desechables(base))
    sobrevivio_el_vivo = bool(suyos) and all(os.path.isdir(d) for d in suyos)
    borrados_huerfanos = [h for h in huerfanos if not os.path.isdir(h)]
    vivo.matar_duro()
    r = {"escena": "B_barrido_bueno",
         "condicion_ok": bool(arranco and suyos),
         "condicion": "había un filex vivo con su desechable creado y con "
                      "contenido dentro",
         "contenido_del_vivo": dentro,
         "desechables_del_vivo": suyos,
         "huerfanos_previos": len(huerfanos),
         "huerfanos_borrados": len(borrados_huerfanos),
         "el_vivo_sobrevivio": sobrevivio_el_vivo,
         "parte": parte, "quedan": len(despues)}
    log.write(json.dumps(r, ensure_ascii=False) + "\n")
    return r


def escena_c(entrada: str, saldir: str, log) -> dict:
    """El barrido INGENUO: por prefijo, sin preguntar si el dueño vive."""
    base = tempfile.gettempdir()
    sal = os.path.join(saldir, "victima.webp")
    if os.path.exists(sal):
        os.remove(sal)
    previos = set(desechables(base))
    vivo = Hijo(entrada, sal)
    arranco = vivo.esperar("ARRANCA")
    suyo, dentro = esperar_desechable(base, previos)
    censo_antes = list(dentro)
    # El barrido que uno escribiría sin haber leído la trampa 26: por PREFIJO,
    # o «por antigüedad» con la antigüedad a cero. Son el mismo barrido.
    borrado_entero = False
    censo_despues = []
    if suyo:
        shutil.rmtree(suyo, ignore_errors=True)
        borrado_entero = not os.path.isdir(suyo)
        try:
            censo_despues = os.listdir(suyo)
        except OSError:
            censo_despues = []
    salida_final = ""
    try:
        resto, _ = vivo.p.communicate(timeout=300)
        salida_final = (resto or "").strip()
    except subprocess.TimeoutExpired:
        salida_final = "(no terminó en 300 s)"
        vivo.matar_duro()
    existe_salida = os.path.exists(sal)
    r = {"escena": "C_barrido_ingenuo",
         "condicion_ok": bool(arranco and suyo and censo_antes),
         "condicion": "el vivo tenía su desechable con contenido cuando se "
                      "lanzó el barrido ingenuo",
         "desechable_de_la_victima": suyo,
         "censo_antes": censo_antes, "censo_despues": censo_despues,
         "ficheros_arrancados": len(censo_antes) - len(censo_despues),
         "directorio_borrado_entero": borrado_entero,
         "salida_del_hijo": salida_final[-300:],
         "la_conversion_produjo_fichero": existe_salida}
    log.write(json.dumps(r, ensure_ascii=False) + "\n")
    return r


def escena_e(entrada: str, saldir: str, espera: float, log) -> dict:
    """Control negativo: `FILEX_BARRER=0` y el huérfano se queda."""
    from filex.trabajo import barrer_huerfanos

    base = tempfile.gettempdir()
    antes = set(desechables(base))
    sal = os.path.join(saldir, "e0.webp")
    h = Hijo(entrada, sal, barrer=False)
    arranco = h.esperar("ARRANCA")
    d, _dentro = esperar_desechable(base, antes)
    arranco = bool(arranco and d)
    time.sleep(espera)
    h.matar_duro()
    mitad = h.murio_a_mitad()
    nuevos = sorted(set(desechables(base)) - antes)
    os.environ["FILEX_BARRER"] = "0"
    parte = barrer_huerfanos()
    os.environ.pop("FILEX_BARRER", None)
    siguen = [d for d in nuevos if os.path.isdir(d)]
    r = {"escena": "E_control_negativo",
         "condicion_ok": arranco and mitad and bool(nuevos),
         "condicion": "hubo un huérfano nuevo que barrer",
         "huerfanos": len(nuevos), "siguen_tras_barrer": len(siguen),
         "parte": parte}
    log.write(json.dumps(r, ensure_ascii=False) + "\n")
    return r


def escena_d(repes: int = 11) -> dict:
    """Coste, **aislado** (trampa 36): no se mide por diferencia de totales."""
    from filex import cerrojo
    from filex.trabajo import DirectorioDeTrabajo, _nombre_candado, barrer_huerfanos

    out = {}

    # 1) El candado de vida, SOLO. Sobre un nombre igual al de un desechable.
    d = tempfile.mkdtemp(prefix="filex-medida-")
    nombre = _nombre_candado(d)
    ms = []
    for _ in range(repes):
        c = cerrojo.Candado(nombre, metadatos=d)
        t0 = time.perf_counter()
        c.tomar()
        c.soltar()
        ms.append((time.perf_counter() - t0) * 1e6)
    shutil.rmtree(d, ignore_errors=True)
    out["candado_vida_tomar_soltar_us"] = {
        "mediana": round(statistics.median(ms), 1), "min": round(min(ms), 1),
        "max": round(max(ms), 1), "n": repes}

    # 2) `mkdtemp` + `rmtree` a secas, para tener la escala del desechable.
    ms = []
    for _ in range(repes):
        t0 = time.perf_counter()
        x = tempfile.mkdtemp(prefix="filex-medida2-")
        shutil.rmtree(x, ignore_errors=True)
        ms.append((time.perf_counter() - t0) * 1e6)
    out["mkdtemp_rmtree_us"] = {
        "mediana": round(statistics.median(ms), 1), "n": repes}

    # 3) El DirectorioDeTrabajo entero, con candado.
    ms = []
    for _ in range(repes):
        t0 = time.perf_counter()
        t = DirectorioDeTrabajo()
        t.cerrar()
        ms.append((time.perf_counter() - t0) * 1e6)
    out["directorio_de_trabajo_completo_us"] = {
        "mediana": round(statistics.median(ms), 1), "n": repes}

    # 4) El barrido. Se mide **con carga controlada**, no por diferencia: se
    #    fabrican `k` desechables jóvenes y sin candado —que el barrido mira y
    #    NO borra, por la edad— para tener el coste POR DIRECTORIO MIRADO.
    base = tempfile.gettempdir()
    entradas = len(list(os.scandir(base)))
    for k in (0, 20):
        falsos = [tempfile.mkdtemp(prefix="filex-carga-") for _ in range(k)]
        barrer_huerfanos()                                       # calentar
        ms, mirados = [], 0
        for _ in range(repes):
            t0 = time.perf_counter()
            p = barrer_huerfanos()
            ms.append((time.perf_counter() - t0) * 1000)
            mirados = p["mirados"]
        out[f"barrido_ms_con_{k}_desechables"] = {
            "mediana": round(statistics.median(ms), 3), "n": repes,
            "mirados": mirados, "entradas_en_el_temp_de_la_sonda": entradas}
        for f in falsos:
            shutil.rmtree(f, ignore_errors=True)
            try:
                os.remove(cerrojo.fichero(_nombre_candado(f)))
            except OSError:
                pass

    # 5) El `%TEMP%` REAL de la máquina, solo para dar la escala. **No se
    #    barre**: hay otro agente trabajando y sus desechables no son míos.
    real = os.environ.get("FILEX_TEMP_REAL") or ""
    if real and os.path.isdir(real):
        try:
            out["temp_real"] = {
                "ruta": real, "entradas": len(list(os.scandir(real))),
                "desechables_filex": len(desechables(real))}
        except OSError:
            pass
    return out


def testigo_deriva(n=300000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 20000.0
    return (time.perf_counter() - t0) * 1000


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", required=True)
    p.add_argument("--tmp", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--matados", type=int, default=3)
    p.add_argument("--espera", type=float, default=0.5)
    a = p.parse_args(argv)

    os.makedirs(a.tmp, exist_ok=True)
    base = tempfile.gettempdir()
    res = {"temp": base, "entrada": a.entrada,
           "bytes_entrada": os.path.getsize(a.entrada),
           "desechables_al_empezar": desechables(base)}

    d0, n0 = testigo_deriva(), testigo_nivel()
    with open(a.log, "w", encoding="utf-8") as log:
        log.write(f"# sonda_desechables — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"# TEMP={base} entradas={len(list(os.scandir(base)))}\n")
        log.write(f"# desechables al empezar: {res['desechables_al_empezar']}\n")

        res["A"] = escena_a(a.entrada, a.tmp, a.matados, a.espera, log)
        res["E"] = escena_e(a.entrada, a.tmp, a.espera, log)
        huerfanos = sorted(set(res["A"]["rutas"]) | set(desechables(base)))
        res["B"] = escena_b(huerfanos, a.entrada, a.tmp, log)
        res["C"] = escena_c(a.entrada, a.tmp, log)
        res["D"] = escena_d()
        log.write(json.dumps(res["D"], ensure_ascii=False) + "\n")

        d1, n1 = testigo_deriva(), testigo_nivel()
        res["testigos"] = {"deriva_ms": [round(d0, 2), round(d1, 2)],
                           "nivel_ms": [round(n0, 2), round(n1, 2)],
                           "deriva_ratio": round(d1 / d0, 3) if d0 else None,
                           "nivel_ratio": round(n1 / n0, 3) if n0 else None}
        res["testigos"]["etiqueta"] = (
            "limpia" if res["testigos"]["deriva_ratio"] < 1.5
            and res["testigos"]["nivel_ratio"] < 3.0 else "SUCIA")
        log.write(f"# testigos: {json.dumps(res['testigos'])}\n")
        res["desechables_al_terminar"] = desechables(base)
        log.write(f"# desechables al terminar: {res['desechables_al_terminar']}\n")

    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({
        "A_huerfanos": res["A"]["huerfanos"], "A_bytes": res["A"]["bytes"],
        "A_validas": res["A"]["celdas_validas"],
        "E_siguen": res["E"]["siguen_tras_barrer"],
        "B_borrados": res["B"]["huerfanos_borrados"],
        "B_vivo_sobrevivio": res["B"]["el_vivo_sobrevivio"],
        "C_cond": res["C"]["condicion_ok"],
        "C_arrancados": res["C"]["ficheros_arrancados"],
        "C_dir_borrado": res["C"]["directorio_borrado_entero"],
        "C_produjo_fichero": res["C"]["la_conversion_produjo_fichero"],
        "C_salida_hijo": res["C"]["salida_del_hijo"][-80:],
        "testigos": res["testigos"]["etiqueta"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
