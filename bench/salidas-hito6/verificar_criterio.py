# -*- coding: utf-8 -*-
"""S6 / hito 6 — el sidecar contra el criterio nuevo, con la tarjeta delante.

Cinco comprobaciones, cada una atada a una clausula del criterio:

  V1  el TTL **devuelve la VRAM**. «Los modelos se descargan por inactividad» es
      la unica clausula del criterio original que sobrevive, y hay que
      demostrarla midiendo la tarjeta antes y despues, no viendo un diccionario
      vacio. El asignador no devuelve la memoria esperando; el proceso al morir,
      si — y esa es toda la diferencia.
  V2  el **orden descendente** de un lote. G5 lo midio con EasyOCR (x2,25);
      aqui se comprueba sobre el motor de PRODUCCION, que tiene tope propio y
      por tanto deberia dar x1,00. Un resultado nulo con su mecanismo dicho.
  V3  el **rechazo** de una pagina que no cabe: con la VRAM inyectada baja, el
      sidecar tiene que decir que no ANTES de cargar el modelo.
  V4  el **reciclado** de verdad: matar y relanzar, con la VRAM medida a los dos
      lados. Cuanto cuesta, y cuanto devuelve.
  V5  el **presupuesto declarado**: el perfil entero con el mayor documento
      admitido, medido de punta a punta.

uso: verificar_criterio.py [salida.json]
"""
import json
import os
import subprocess
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(D))
sys.path.insert(0, RAIZ)
sys.path.insert(0, D)

from filex import gpu, sidecar                              # noqa: E402
from testigos import testigo_deriva, testigo_nivel, veredicto  # noqa: E402

PY_OCR = os.environ.get("H6_PY", "D:/Work/research/FileX/.venv-ai/Scripts/python.exe")
IMG = os.path.join(D, "img")
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "json", "verificacion.json")

FOLIOS = [("escaneado_d4_r100.png", 0.555), ("escaneado_d4_r150.png", 1.248),
          ("escaneado_d4_r200.png", 2.221), ("escaneado_d4_r280.png", 4.352),
          ("escaneado_d4_r400.png", 8.882)]


def usada():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=20)
    return int(r.stdout.decode().strip().splitlines()[0])


def pico_durante(fn, cada=0.25):
    """Ejecuta `fn` muestreando la VRAM. Devuelve `(resultado, pico, base)`."""
    import threading
    estado = {"pico": usada(), "parar": False}
    base = estado["pico"]

    def bucle():
        while not estado["parar"]:
            v = usada()
            if v > estado["pico"]:
                estado["pico"] = v
            time.sleep(cada)

    h = threading.Thread(target=bucle, daemon=True)
    h.start()
    try:
        r = fn()
    finally:
        estado["parar"] = True
        h.join(timeout=5)
    return r, estado["pico"], base


res = {"maquina": {"vram_libre_inicial_MiB": gpu.vram_libre_mib(),
                   "python_ocr": PY_OCR},
       "constantes": {"MARGEN_MIB": sidecar.MARGEN_MIB, "TTL_S": sidecar.TTL_S},
       "pruebas": []}

d_ini = testigo_deriva()
n_ini, ag1 = testigo_nivel()


def anotar(**kw):
    res["pruebas"].append(kw)
    print(json.dumps(kw, ensure_ascii=False), flush=True)


with gpu.Lock("S6-verificacion") as lk:
    if lk.aviso:
        print(f"[aviso] {lk.aviso}", flush=True)

    # ---------------------------------------------------------------- V1: TTL
    reg = sidecar.Registro(ttl_s=3.0, python=PY_OCR)
    antes = usada()
    reg.obtener("rapidocr")
    r = reg.procesar("rapidocr", os.path.join(IMG, FOLIOS[-1][0]))
    con_modelo = usada()
    time.sleep(4.0)                        # mas que el TTL
    caducados = reg.caducar()
    time.sleep(2.0)                        # el proceso tarda en morir del todo
    tras_ttl = usada()
    anotar(prueba="V1_ttl_devuelve_vram", antes_MiB=antes,
           con_modelo_MiB=con_modelo, tras_ttl_MiB=tras_ttl,
           retenido_MiB=con_modelo - antes,
           devuelto_MiB=con_modelo - tras_ttl,
           caducados=[list(c) for c in caducados],
           residentes=len(reg.residentes), ocr_ok=r.get("ok"),
           ocr_chars=r.get("chars"))
    reg.cerrar()

    # ------------------------------------------------- V2: el orden del lote
    rutas = [os.path.join(IMG, n) for n, _ in FOLIOS]
    ordenes = {}
    for nombre, secuencia in (("descendente", list(reversed(rutas))),
                              ("ascendente", list(rutas))):
        reg = sidecar.Registro(ttl_s=999, python=PY_OCR)
        # `procesar_lote` reordena siempre; para el control ascendente hay que
        # saltarselo a mano, que es justo el orden que G5 refuto.
        def lote(secuencia=secuencia, reg=reg):
            return [reg.procesar("rapidocr", p) for p in secuencia]
        salidas, pico, base = pico_durante(lote)
        ordenes[nombre] = {"pico_MiB": pico, "base_MiB": base,
                           "propio_MiB": pico - base,
                           "ok": all(s.get("ok") for s in salidas),
                           "chars": [s.get("chars") for s in salidas]}
        reg.cerrar()
        time.sleep(2.0)
    anotar(prueba="V2_orden_del_lote", **ordenes,
           ratio_asc_sobre_desc=round(
               ordenes["ascendente"]["propio_MiB"]
               / max(1, ordenes["descendente"]["propio_MiB"]), 3))

    # --------------------------------------------------------- V3: el rechazo
    # VRAM inyectada baja: no hace falta llenar 12 GiB de verdad para comprobar
    # que el sidecar dice que no, y **no se puede** sin robarle la tarjeta a
    # otro. Lo que se comprueba es que no arranca ningun modelo.
    reg = sidecar.Registro(python=PY_OCR, vram_libre=lambda: 900)
    antes = usada()
    r = reg.procesar("easyocr", os.path.join(IMG, FOLIOS[-1][0]))
    anotar(prueba="V3_rechazo_antes_de_cargar", rechazada=r.get("rechazada"),
           decision=r.get("decision"), residentes=len(reg.residentes),
           vram_movida_MiB=usada() - antes)
    reg.cerrar()

    # ------------------------------------------------------- V4: el reciclado
    reg = sidecar.Registro(ttl_s=999, python=PY_OCR)
    reg.procesar("rapidocr", os.path.join(IMG, FOLIOS[-1][0]))
    t = reg.residentes[("rapidocr", "cuda")]
    con_modelo = usada()
    pid_antes = t.meta.get("pid")
    t0 = time.perf_counter()
    t.reciclar()
    coste_s = time.perf_counter() - t0
    time.sleep(1.5)
    tras = usada()
    anotar(prueba="V4_reciclado", con_modelo_MiB=con_modelo, tras_MiB=tras,
           coste_s=round(coste_s, 3), pid_antes=pid_antes,
           pid_despues=t.meta.get("pid"),
           pid_distinto=pid_antes != t.meta.get("pid"),
           mpx_max_visto_tras=t.mpx_max_visto, reciclados=t.reciclados)
    reg.cerrar()
    time.sleep(2.0)

    # ------------------------------------------- V5: el presupuesto declarado
    # El perfil entero: audio + OCR + NVENC, con el mayor documento admitido.
    # Se mide con el arnes de coresidencia, fase `dos_procesos`, que es la
    # arquitectura de este modulo.
    perfil = sidecar.Perfil("distil-large-v3 + RapidOCR/PP-OCRv6 small + NVENC",
                            escritorio_mib=3448, audio_mib=1847,
                            motor=sidecar.MOTORES["rapidocr"], mpx_max=8.882,
                            nvenc_mib=743)
    anotar(prueba="V5_presupuesto_declarado", **perfil.evaluar())

d_fin = testigo_deriva()
n_fin, ag2 = testigo_nivel()
res["ruido"] = veredicto(d_ini, d_fin, n_ini, n_fin, ag1 or ag2)
res["maquina"]["vram_libre_final_MiB"] = gpu.vram_libre_mib()
res["maquina"]["lock_libre_al_salir"] = gpu.esta_libre()

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
json.dump(res, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({"evento": "fin", "ruido": res["ruido"]["etiqueta"],
                  "salida": SALIDA}, ensure_ascii=False))
