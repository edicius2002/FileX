"""Qué cuesta en RELOJ el defecto de `_cuerpo`, medido con su control al lado.

    python bench/salidas-fix-superficies/reloj.py

La prueba de la suite mide el MECANISMO —cuántas veces se lee el cuerpo—
porque es determinista. Este arnés mide la CONSECUENCIA, que es lo que sufre
un usuario: el hilo que se queda esperando bytes que no van a llegar hasta que
salta el plazo del socket.

Dos decisiones de método, y las dos salen de trampas ya pagadas:

* **El control positivo es el SUJETO CON EL DEFECTO** (trampa 116), no una
  variante del doble: `_ManejadorVulnerable` reimplementa el `_rechazo`
  anterior —el que lee sin preguntar si queda algo— sobre el mismo
  `filex/api.py` de hoy. Sin él, «responde en 0,00 s» no se distingue de un
  arnés que no dispara.
* **Las dos configuraciones se miden en la MISMA tanda** (trampa 59): una
  cifra de este fichero contra otra de otro día mediría dos máquinas.

El plazo se acorta a `PLAZO` segundos: con los 30 s de producción la tanda
costaría más de tres minutos y mediría exactamente lo mismo, porque lo que se
compara es «agota el plazo» contra «no lo agota». Por eso lo que se publica es
el COCIENTE contra el plazo, no un tiempo absoluto (`CLAUDE.md` §3).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import api as _api                      # noqa: E402
from filex.confinamiento import Confinamiento      # noqa: E402
from filex.nucleo import FileX                     # noqa: E402
from filex.servicio import Trabajos                # noqa: E402

PLAZO = 3.0

#: Los tres caminos en que `do_POST` rechaza DESPUÉS de leer el cuerpo, y un
#: cuarto que rechaza ANTES: es el control negativo del propio arnés — si el
#: `415` también se disparase, lo que se estaría midiendo sería el socket.
CELDAS = (
    ("no es JSON", "/convertir", b"{roto", "application/json", 400),
    ("no es objeto", "/convertir", b"[1,2]", "application/json", 400),
    ("ruta desconocida", "/no-existe", b"{}", "application/json", 404),
    ("415 (rechaza ANTES)", "/convertir", b"{}", "text/plain", 415),
)


class _Base(_api.Manejador):
    timeout = PLAZO


class _Vulnerable(_Base):
    """El `_rechazo` de ANTES del arreglo, conservado a propósito.

    Es literalmente el cuerpo anterior: lee el cuerpo sin preguntarse si
    alguien ya se lo llevó. Todo lo demás —`do_POST`, `_cuerpo`, `_responder`—
    es el de producción.
    """

    def _rechazo(self, codigo: int, motivo: str) -> None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if 0 < n <= _api.MAX_CUERPO:
            try:
                self.rfile.read(n)
            except OSError:
                pass
        self.close_connection = True
        self._responder(codigo, {"error": motivo})


def _servidor(manejador, carpeta):
    fx = FileX()
    fx.confinamiento = Confinamiento([carpeta])
    srv = _api.Servidor(("127.0.0.1", 0), manejador,
                        _api.Servicio(fx, Trabajos(os.path.join(carpeta, "_t"))))
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    return srv, hilo


def _celda(puerto, ruta, crudo, tipo):
    req = urllib.request.Request(f"http://127.0.0.1:{puerto}{ruta}", data=crudo,
                                 headers={"Content-Type": tipo}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=PLAZO * 20) as r:
            codigo = r.status
            r.read()
    except urllib.error.HTTPError as e:
        codigo = e.code
        e.read()
    return codigo, time.perf_counter() - t0


def main() -> int:
    carpeta = tempfile.mkdtemp(prefix="filex-fix-reloj-")
    filas = []
    try:
        for nombre, manejador in (("vulnerable", _Vulnerable),
                                  ("arreglado", _Base)):
            srv, hilo = _servidor(manejador, carpeta)
            puerto = srv.server_address[1]
            try:
                for etiqueta, ruta, crudo, tipo, esperado in CELDAS:
                    codigo, seg = _celda(puerto, ruta, crudo, tipo)
                    filas.append({
                        "configuracion": nombre,
                        "celda": etiqueta,
                        "codigo": codigo,
                        "codigo_esperado": esperado,
                        "correcto": codigo == esperado,
                        "veces_el_plazo": round(seg / PLAZO, 3),
                        "agota_el_plazo": seg >= PLAZO * 0.9,
                    })
            finally:
                srv.shutdown()
                srv.server_close()
                hilo.join(timeout=10)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)

    agotan = {c: sum(1 for f in filas
                     if f["configuracion"] == c and f["agota_el_plazo"])
              for c in ("vulnerable", "arreglado")}
    salida = {
        "plazo_s": PLAZO,
        "timeout_socket_de_produccion_s": _api.TIMEOUT_SOCKET,
        "nota": ("se publica el cociente contra el plazo, no un tiempo "
                 "absoluto (CLAUDE.md §3); las dos configuraciones van en la "
                 "misma tanda (trampa 59)"),
        "celdas_que_agotan_el_plazo": agotan,
        "el_arnes_dispara": agotan["vulnerable"] > 0,
        "todas_responden_lo_correcto": all(f["correcto"] for f in filas),
        "filas": filas,
    }
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reloj.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=1, ensure_ascii=False)
    print(json.dumps(salida, indent=1, ensure_ascii=False))
    # Si el control positivo no dispara, la medida del arreglado no dice nada.
    return 0 if salida["el_arnes_dispara"] and salida["todas_responden_lo_correcto"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
