"""Hito 7 — la API HTTP local. La CUARTA de las cuatro superficies.

**Este fichero no valida ni una ruta.** R10 (`RESULTADOS-MCP.md` §10): *la
validación vive en el núcleo, no en la superficie*. Aquí no aparecen
`realpath`, ni `startswith`, ni `nombre_seguro`, ni `Confinamiento`: el único
predicado sobre rutas que se ejecuta lo llama `FileX._resolver`, dentro del
núcleo. Hay una prueba que lo comprueba leyendo este fichero
(`pruebas/test_hito7.py::R10`), porque «la validación está en el núcleo» es una
afirmación fácil de escribir y fácil de incumplir sin querer.

**Y la API no es una copia de la capa MCP: es el mismo `Servicio`.** Toda la
lógica de las herramientas ya estaba escrita sin una línea de protocolo
—`filex/mcp.py` la separó a propósito para poder probarla sin levantar un
servidor— y el registro de trabajos ya estaba persistido en disco con este
motivo escrito en su docstring: *«un JSON por trabajo sirve además a la CLI, al
watcher y a la API: los cuatro frentes ven el mismo trabajo»*
(`PLAN-ORQUESTADOR.md` §5.3). Así que este módulo es **transporte**: parsear
HTTP, aplicar las defensas que son del protocolo y serializar. Nada más.

De ahí sale gratis el §5.2 —*toda operación larga devuelve un `job_id` al
empezar; no bloquea, nunca condicionado a un booleano*—: `POST /convertir`
responde `202` con el asa porque `Servicio.convert` ya lo hacía.

## Lo que sí decide este fichero: es la única superficie expuesta a la red

Las otras tres se hablan por la línea de órdenes, por una tubería o por el
sistema de ficheros. Esta abre un puerto, y eso trae defensas que **no son de
rutas sino de protocolo** — no contradicen R10, viven en otra capa:

1. **`127.0.0.1` por defecto, y salir de ahí exige decirlo.** Con `--host` no
   loopback hace falta además `--permitir-red`, y aun así se avisa por
   `stderr`. La lista blanca de raíces protege del sistema de ficheros, no de
   quién pregunta: sin autenticación, escuchar en `0.0.0.0` convierte la LAN
   entera en cliente con permiso de conversión sobre las raíces permitidas.
2. **Cabecera `Host` de loopback.** Es la defensa contra *DNS rebinding*: un
   navegador que resuelva `malo.example` a `127.0.0.1` manda `Host: malo.example`.
3. **`Origin` prohibido y `Content-Type: application/json` obligatorio en los
   `POST`.** Un formulario HTML puede mandar un `POST` a `localhost` sin
   permiso del usuario, pero **no puede fijar el `Content-Type` a
   `application/json` sin disparar un *preflight*** que aquí no se contesta
   (no hay `OPTIONS` y no hay ni una cabecera CORS). Es CSRF cerrado sin
   inventar tokens.
4. **Tope de cuerpo** (`MAX_CUERPO`) y **tope de socket**: ningún `read()` sin
   límite y ninguna conexión sin plazo. La regla de este proyecto es que no hay
   invocación sin tope; una conexión abierta tampoco.

## Y lo que la API NO hace, a propósito

- **No acepta bytes.** No hay `multipart`, no hay `base64`, no hay subida. Se
  mandan y se devuelven **rutas y metadatos**, igual que MCP. El criterio es el
  volumen de la respuesta, no el tipo del protocolo: `image-worker-mcp` devuelve
  base64 dentro de un `TextContent` y cuesta ×87,6.
- **No devuelve `stderr`.** `invocacion.Resultado` separa `err` (crudo, para el
  log) de `motivo` (opaco), y aquí solo cruza el segundo. Los tres servidores de
  referencia reenvían el `stderr` de ffmpeg: 884-1.228 tokens, casi todo banner
  de compilación, y el mensaje **nombra el comando que lo instala**.
- **No distingue «prohibido» de «no existe»** (R4). Los dos son
  `ruta no accesible`, con el mismo código HTTP.

Arranque:

    python -m filex.api --raiz D:/Work/research/FileX
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__
from .mcp import Servicio, Trabajos
from .nucleo import FileX

# **`subprocess` no se importa aquí.** Igual que en `filex/mcp.py` y en
# `filex/watcher.py`: no hay puntos de invocación, hay uno
# (`filex.invocacion.ejecutar`), y es el que pone `stdin=DEVNULL` antes de las
# banderas.

#: Puerto por defecto. Alto, para no chocar con nada del sistema.
PUERTO_POR_DEFECTO = 8756

#: Tope del cuerpo de un `POST`. Aquí solo viajan rutas y parámetros: un cuerpo
#: de 64 KiB ya es dos órdenes de magnitud más de lo que hace falta. Sin tope,
#: `rfile.read(Content-Length)` es una reserva de memoria dictada por el cliente.
MAX_CUERPO = 64 * 1024

#: Plazo de una conexión. Ninguna invocación sin tope, y una conexión abierta
#: que no manda nada es exactamente el mismo problema con otro nombre.
TIMEOUT_SOCKET = 30.0

#: Direcciones desde las que se sirve sin más preguntas.
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "[::1]"}


def es_loopback(host: str) -> bool:
    """¿Es esta dirección la máquina local? Sobre la CADENA, no sobre el disco.

    No es una validación de rutas y no tiene nada que ver con R10: decide si se
    abre el puerto a la red, no si se puede tocar un fichero.
    """
    h = (host or "").strip().lower()
    if h.startswith("[") and "]" in h:                   # [::1]:8756
        h = h[: h.index("]") + 1]
    elif h.count(":") == 1:                              # 127.0.0.1:8756
        h = h.split(":", 1)[0]
    return h in _LOOPBACK


def _es_ip_literal(host: str) -> bool:
    """¿Es esta cabecera `Host` una IP y no un nombre?

    El *DNS rebinding* necesita un nombre; con una IP literal no hay nada que
    rebindear. Es lo único que queda como defensa cuando se escucha en
    `0.0.0.0`, donde no existe «la» dirección con la que comparar.
    """
    import ipaddress

    h = (host or "").strip()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


class Manejador(BaseHTTPRequestHandler):
    """Transporte. Ni una decisión de acceso a ficheros vive aquí."""

    server_version = "FileX/" + __version__
    sys_version = ""                        # no anunciar la versión de Python
    protocol_version = "HTTP/1.1"
    timeout = TIMEOUT_SOCKET

    # ------------------------------------------------------------- utilidades

    @property
    def servicio(self) -> Servicio:
        return self.server.servicio          # type: ignore[attr-defined]

    def log_message(self, formato, *args):   # noqa: A003
        """La bitácora va a `stderr` **solo si se pide**, y sin la línea entera.

        La línea de petición lleva rutas del disco del usuario en la cadena de
        consulta. Volcarla por defecto convierte la bitácora en el oráculo que
        R4 cierra en la respuesta.
        """
        if getattr(self.server, "verboso", False):       # type: ignore[attr-defined]
            sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        if self.close_connection:
            self.send_header("Connection", "close")
        # Sin una sola cabecera CORS: una página no puede LEER esta respuesta.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(datos)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _rechazo(self, codigo: int, motivo: str) -> None:
        """Un rechazo de protocolo. Nunca dice nada del disco.

        Y **cierra la conexión**. Con `HTTP/1.1` y `keep-alive`, rechazar una
        petición cuyo cuerpo no se ha leído deja bytes sin consumir en el
        socket y la siguiente petición se lee sobre la mitad de la anterior:
        MEDIDO como `ConnectionAbortedError` (WinError 10053) en la primera
        pasada de `pruebas/test_hito7.py`. Se descarta lo que quepa y se cierra.
        """
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if 0 < n <= MAX_CUERPO:
            try:
                self.rfile.read(n)
            except OSError:
                pass
        self.close_connection = True
        self._responder(codigo, {"error": motivo})

    # ------------------------------------------------- defensas de protocolo

    def _host_admitido(self, host: str) -> bool:
        """Loopback siempre; la dirección declarada al arrancar, si se declaró.

        Sin esta segunda mitad, `--permitir-red` no serviría de nada: una
        petición legítima desde la LAN llega con `Host: 192.168.x.y` y el
        cerrojo anti-*rebinding* la rechazaría. Es un detalle que solo aparece
        al MEDIRLO (`bench/hito7-superficies.md` §6.2): las dos defensas se
        anulaban entre sí.
        """
        if es_loopback(host):
            return True
        declarado = getattr(self.server, "host_declarado", "")  # type: ignore[attr-defined]
        if not declarado or es_loopback(declarado):
            return False
        h = (host or "").strip().lower()
        if h.count(":") == 1:
            h = h.split(":", 1)[0]
        if h == declarado.lower():
            return True
        # `0.0.0.0` significa «todas las direcciones»: no hay una sola con la
        # que comparar. Pero **sigue habiendo defensa**, porque el *rebinding*
        # necesita un NOMBRE —el ataque consiste en que `malo.example` resuelva
        # a esta máquina—, así que se admite una IP literal y se rechaza todo
        # nombre. MEDIDO: sin esta línea, `--permitir-red` desactivaba el
        # cerrojo entero y `Host: malo.example` respondía 200
        # (`bench/hito7-superficies.md` §6.2).
        return declarado in ("0.0.0.0", "::") and _es_ip_literal(h)

    def _defensas(self, *, es_post: bool) -> bool:
        """Las cuatro comprobaciones de la cabecera. Ninguna mira el disco."""
        if not self._host_admitido(self.headers.get("Host", "")):
            # DNS rebinding: el navegador resuelve un nombre ajeno a 127.0.0.1
            # y manda ese nombre en `Host`.
            self._rechazo(421, "host no admitido")
            return False
        if self.headers.get("Origin"):
            # Ninguna petición legítima a esta API viene de una página web.
            self._rechazo(403, "origen no admitido")
            return False
        if es_post:
            tipo = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if tipo != "application/json":
                # Obliga al *preflight* CORS, que no se contesta: cierra el CSRF
                # de formulario sin inventar un token de sesión.
                self._rechazo(415, "se requiere application/json")
                return False
        return True

    def _cuerpo(self) -> dict | None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._rechazo(400, "longitud no válida")
            return None
        if n < 0 or n > MAX_CUERPO:
            self._rechazo(413, "cuerpo demasiado grande")
            return None
        crudo = self.rfile.read(n) if n else b"{}"
        try:
            d = json.loads(crudo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._rechazo(400, "el cuerpo no es JSON válido")
            return None
        if not isinstance(d, dict):
            self._rechazo(400, "el cuerpo tiene que ser un objeto JSON")
            return None
        return d

    # ------------------------------------------------------------- encaminado

    def do_GET(self) -> None:                              # noqa: N802
        if not self._defensas(es_post=False):
            return
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        ruta = u.path.rstrip("/") or "/"

        if ruta == "/" or ruta == "/salud":
            fx = self.servicio.fx
            return self._responder(200, {
                "filex": __version__,
                "motores": sorted(m.nombre for m in fx.disponibles),
                "ausentes": sorted(m.nombre for m in fx.ausentes),
                "aristas": len(fx.grafo.aristas),
                "confinado": fx.confinamiento is not None,
                "nota": "esta API devuelve rutas y metadatos, nunca contenido",
            })
        if ruta == "/destinos":
            if not q.get("formato"):
                return self._rechazo(400, "falta el parámetro 'formato'")
            return self._responder(200, self.servicio.despachar(
                "list_targets", {"formato_origen": q["formato"],
                                 "formato_destino": q.get("destino", "")}))
        if ruta == "/inspeccionar":
            if not q.get("ruta"):
                return self._rechazo(400, "falta el parámetro 'ruta'")
            d = self.servicio.despachar("inspect", {"ruta": q["ruta"]})
            return self._responder(404 if d.get("error") else 200, d)
        if ruta.startswith("/trabajos/"):
            jid = ruta[len("/trabajos/"):]
            d = self.servicio.despachar("job", {"job_id": jid,
                                                "accion": q.get("accion", "estado")})
            return self._responder(404 if d.get("error") else 200, d)
        return self._rechazo(404, "no hay tal recurso")

    def do_POST(self) -> None:                             # noqa: N802
        if not self._defensas(es_post=True):
            return
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        cuerpo = self._cuerpo()
        if cuerpo is None:
            return

        if ruta == "/convertir":
            d = self.servicio.despachar("convert", cuerpo)
            # 202: el asa se entrega AL EMPEZAR. `PLAN-ORQUESTADOR.md` §5.2 —
            # un `ffmpeg_convert` de un clip de 5 s superó los 900 s del timeout
            # del cliente **con la conversión ya terminada en disco**. Una
            # respuesta bloqueante hereda ese fallo tal cual.
            return self._responder(400 if d.get("error") else 202, d)
        if ruta == "/lote":
            d = self.servicio.despachar("batch", cuerpo)
            return self._responder(400 if d.get("error") else 202, d)
        if ruta.startswith("/trabajos/") and ruta.endswith("/cancelar"):
            jid = ruta[len("/trabajos/"):-len("/cancelar")]
            d = self.servicio.despachar("job", {"job_id": jid, "accion": "cancelar"})
            return self._responder(404 if d.get("error") else 200, d)
        return self._rechazo(404, "no hay tal recurso")

    def do_OPTIONS(self) -> None:                          # noqa: N802
        """Sin CORS. Se contesta `405` a propósito: contestar un *preflight*
        con permisos es lo único que abriría la API a una página web."""
        self._rechazo(405, "método no admitido")

    def do_PUT(self) -> None:                              # noqa: N802
        self._rechazo(405, "método no admitido")

    do_DELETE = do_PUT                                     # noqa: N815
    do_PATCH = do_PUT                                      # noqa: N815


class Servidor(ThreadingHTTPServer):
    """`ThreadingHTTPServer`: la primera superficie con concurrencia real.

    Lo que aguanta y lo que no está MEDIDO en `bench/hito7-superficies.md` §5,
    no supuesto. Resumen de lo que hay que saber al leer este código:

    * El `FileX` se construye **una vez** y se comparte. No es una comodidad:
      construirlo cuesta **~23,6 s en frío** (sondea los motores y el demonio de
      Docker) y **~750 ms en caliente**. Por petición sería inviable.
    * El directorio desechable de R18 es un `mkdtemp` por conversión, así que
      dos conversiones simultáneas **no se pisan**, y el censo del punto 5
      tampoco.
    * **Lo que NO está protegido es el DESTINO.** Dos peticiones con la misma
      ruta de salida se pisan en el `shutil.move` final, y eso es un hallazgo
      del hito, no una decisión — ver §5.3 del informe.
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, direccion, manejador, servicio: Servicio, *,
                 verboso: bool = False) -> None:
        self.servicio = servicio
        self.verboso = verboso
        #: La dirección con la que se arrancó. La usa el cerrojo anti-*rebinding*
        #: para no rechazar al cliente legítimo de un despliegue en red.
        self.host_declarado = direccion[0]
        # `::1` necesita AF_INET6; `127.0.0.1`, AF_INET.
        if ":" in direccion[0]:
            self.address_family = socket.AF_INET6
        super().__init__(direccion, manejador)


def construir(fx: FileX, *, trabajos: Trabajos | None = None,
              host: str = "127.0.0.1", puerto: int = PUERTO_POR_DEFECTO,
              verboso: bool = False) -> Servidor:
    """Devuelve el servidor ya cableado, sin arrancarlo.

    Separado de `main` por el mismo motivo que `Servicio` está separado del
    protocolo MCP: para poder probar la superficie entera sin un `main`.
    """
    return Servidor((host, puerto), Manejador, Servicio(fx, trabajos),
                    verboso=verboso)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="filex-api",
        description="API HTTP local de FileX. Devuelve rutas y metadatos, "
                    "nunca contenido. Escucha en 127.0.0.1 salvo que se diga "
                    "lo contrario, y decirlo cuesta dos banderas.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO)
    p.add_argument("--raiz", action="append", default=None,
                   help="raíz permitida (lista blanca). Repetible.")
    p.add_argument("--permitir-red", action="store_true",
                   help="necesario para escuchar fuera de loopback. Esta API "
                        "NO tiene autenticación: la lista blanca protege el "
                        "disco, no decide quién pregunta.")
    p.add_argument("--verboso", action="store_true")
    args = p.parse_args(argv)

    if not es_loopback(args.host) and not args.permitir_red:
        print("me niego a escuchar fuera de 127.0.0.1 sin --permitir-red: esta "
              "API no autentica a nadie", file=sys.stderr)
        return 2

    try:
        fx = FileX(raices_lectura=args.raiz)
    except ValueError as e:
        print(f"no se puede arrancar: {e}", file=sys.stderr)
        return 2
    if args.raiz is None:
        print("aviso: sin --raiz no hay lista blanca (denegar por defecto está "
              "desactivado)", file=sys.stderr)
    if not es_loopback(args.host):
        print(f"AVISO: escuchando en {args.host} — cualquiera que llegue a este "
              "puerto puede convertir dentro de las raíces permitidas",
              file=sys.stderr)

    srv = construir(fx, host=args.host, puerto=args.puerto, verboso=args.verboso)
    print(f"filex-api en http://{args.host}:{args.puerto}  "
          f"({len(fx.grafo.aristas)} aristas)", file=sys.stderr)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        hilo.join()
    except KeyboardInterrupt:
        srv.shutdown()
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
