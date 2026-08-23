"""Hito 7 — el watcher de carpetas. La TERCERA de las cuatro superficies.

**Este fichero no valida ni una ruta.** R10 (`RESULTADOS-MCP.md` §10): *la
validación vive en el núcleo, no en la superficie*. La CLI de `kordoc` lee
ficheros fuera de `KORDOC_ROOT` con `exit=0` precisamente porque `safePath`
vivía en su capa MCP. Aquí el único predicado sobre rutas que se ejecuta es
`filex.confinamiento.Confinamiento.resolver`, y lo llama **el núcleo** desde
`FileX._resolver`. Lo mismo con el nombre de salida: `nombre_seguro` no se
invoca aquí, se invoca allí — y esa es justamente la trampa que ya mordió una
vez (`nombre_seguro` escrito, probado y **sin un solo llamante** fuera de su
prueba, con 94 B escritos en el flujo alternativo de un fichero ajeno y
`veredicto: ok`).

Lo que sí decide este fichero, y son las cuatro preguntas que ni la CLI ni MCP
tienen que responder:

1. **¿Cuándo está completo un fichero?** No se supone: se sondea. El watcher ve
   el fichero mientras se escribe, y convertir un PNG a medias produce basura
   con `rc != 0` o, peor, con `rc == 0`. La respuesta implementada es
   **estabilidad de `(tamaño, mtime_ns)` durante `N` sondeos consecutivos**,
   con un segundo cerrojo opcional en Windows —`os.replace(p, p)` sobre el
   propio fichero— cuya utilidad está MEDIDA en `bench/hito7-superficies.md` §3.
2. **¿Qué es «el mismo fichero»?** La identidad es
   `(ruta normalizada, tamaño, mtime_ns)`. Un renombrado es un fichero nuevo
   —tiene otro nombre y por tanto otra salida—, una reescritura en sitio
   también, y dos sondeos del mismo fichero quieto no lo son. Medido en §4.
3. **¿Y si el destino ya existe?** No se sobrescribe en silencio (R9). Se salta
   con motivo, salvo `--sobrescribir`.
4. **¿Quién ve el trabajo?** El mismo registro `Trabajos` de la capa MCP, que
   ya está persistido en disco precisamente para esto: *«un JSON por trabajo
   sirve además a la CLI, al watcher y a la API: los cuatro frentes ven el
   mismo trabajo»* (`PLAN-ORQUESTADOR.md` §5.3). El watcher no inventa un
   registro propio.

**Y lo que NO hace, que es lo importante:** no convierte y verifica después. No
puede: el punto 5 del contrato —«¿escribió el motor fuera de lo declarado?»— es
el único que **no se puede verificar a posteriori**, y sin censo **49 de las 53
salidas del patrón oro bajan de `ok` a `ok_parcial`**. El watcher llama a
`FileX.convertir`, que toma el censo dentro del mismo `with` que lanza el motor.
Aquí no hay una segunda llamada al contrato, y no puede haberla.

Arranque:

    python -m filex.watcher --vigilar D:/entrada --salida D:/salida --destino webp \\
                            --raiz D:/entrada --raiz D:/salida
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field

from . import formatos
from .confinamiento import Denegado
from .mcp import COMPLETADO, FALLIDO, Trabajos
from .nucleo import FileX

# **`subprocess` no se importa aquí, igual que en `filex/mcp.py`, y tampoco es
# un descuido: es la comprobación.** Todo motor externo se lanza por
# `filex.invocacion.ejecutar()`, que construye el proceso con `stdin=DEVNULL`
# ANTES de las banderas. No hay puntos de invocación: hay uno.

#: Cada cuánto se sondea el directorio, en segundos. Un `ReadDirectoryChangesW`
#: o un `inotify` avisarían antes, pero **avisan del PRIMER byte**, no del
#: último: el problema de «¿está completo?» no lo resuelve la notificación, lo
#: resuelve el sondeo posterior. Sondear es además portable y sin dependencias.
INTERVALO_POR_DEFECTO = 1.0

#: Cuántos sondeos consecutivos tienen que dar el MISMO `(tamaño, mtime_ns)`
#: para considerar el fichero terminado. Con 2 el coste mínimo de latencia es
#: `estables × intervalo`. El número está MEDIDO en `bench/hito7-superficies.md`
#: §3: con 1 sondeo el watcher convierte ficheros a medio escribir.
ESTABLES_POR_DEFECTO = 2

#: Tope de una conversión lanzada por el watcher. Más alto que el de la CLI
#: (120 s) porque aquí nadie espera delante, y más bajo que el de MCP (300 s)
#: porque una cola de ficheros no puede quedarse parada en uno.
TIMEOUT_WATCHER = 240.0


@dataclass(frozen=True)
class Huella:
    """La identidad de un fichero *para el watcher*. No es un hash del contenido.

    Que sea `(ruta, tamaño, mtime_ns)` y no `sha256` es una decisión con precio
    medido (`bench/hito7-superficies.md` §4.3): el `stat` cuesta microsegundos y
    el hash, milisegundos por MB. El precio de la decisión es que **un `touch`
    sin cambio de contenido cuenta como fichero nuevo**; el precio del hash
    sería recorrer cada fichero entero antes de decidir si merece la pena
    convertirlo.
    """

    ruta: str
    tamano: int
    mtime_ns: int

    def clave(self) -> str:
        """La clave de identidad, con `normcase` (R3).

        La `ruta` se guarda **tal cual la da el sistema de ficheros** para que la
        bitácora y el núcleo la vean con su caja real; la comparación se hace
        aquí. Guardar la normalizada era más corto y hacía que el watcher
        imprimiera rutas en minúsculas y se las pasara así al motor.
        """
        return f"{os.path.normcase(self.ruta)}|{self.tamano}|{self.mtime_ns}"


@dataclass
class Visto:
    """Lo que el watcher sabe de un fichero entre dos sondeos."""

    huella: Huella
    repeticiones: int = 1


@dataclass
class Atendido:
    """El resultado de atender UN fichero. Sin `stderr`, nunca.

    `invocacion.Resultado` separa `err` (crudo, para el log) de `motivo`
    (opaco). Aquí solo vive el segundo: el watcher escribe su bitácora en JSON
    y esa bitácora la puede leer cualquiera, incluido un agente.
    """

    entrada: str
    salida: str = ""
    estado: str = ""
    veredicto: str = ""
    motivo: str = ""
    ms: float = 0.0
    job_id: str = ""
    #: Cobertura del contrato tal y como la devolvió el núcleo. El `5_escritura`
    #: solo puede valer `True` porque el censo se tomó DENTRO de la conversión.
    cobertura: dict = field(default_factory=dict)
    sobrantes: dict = field(default_factory=dict)


class Memoria:
    """Qué se ha atendido ya. En memoria, y opcionalmente en disco.

    Sin persistencia, reiniciar el watcher vuelve a convertir la carpeta entera.
    Con ella, no. Es un JSON plano porque el orden de magnitud es «los ficheros
    que caben en una carpeta de entrada», no un índice.
    """

    def __init__(self, fichero: str | None = None) -> None:
        self.fichero = fichero
        self._claves: set[str] = set()
        if fichero and os.path.isfile(fichero):
            try:
                with open(fichero, encoding="utf-8") as fh:
                    self._claves = set(json.load(fh).get("atendidas") or [])
            except (OSError, ValueError):
                self._claves = set()

    def __contains__(self, h: Huella) -> bool:
        return h.clave() in self._claves

    def __len__(self) -> int:
        return len(self._claves)

    def marcar(self, h: Huella) -> None:
        self._claves.add(h.clave())
        if not self.fichero:
            return
        tmp = self.fichero + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"atendidas": sorted(self._claves)}, fh, ensure_ascii=False)
            os.replace(tmp, self.fichero)
        except OSError:
            pass                                        # el disco no manda aquí


def _estable_en_disco(ruta: str) -> bool:
    """Segundo cerrojo: ¿puede este proceso renombrar el fichero sobre sí mismo?

    En Windows, un fichero abierto por otro proceso sin `FILE_SHARE_DELETE`
    hace fallar el `MoveFileEx`, y `open(ruta, 'rb')` **no** falla: leer un
    fichero a medio escribir es perfectamente legal. Por eso el cerrojo es un
    renombrado y no una apertura.

    En POSIX esto **siempre** da `True` —un `rename` sobre un fichero abierto es
    legal—, así que ahí el único cerrojo real es la estabilidad de `stat`. Se
    devuelve `True` para no inventar una defensa que no existe.

    Su eficacia está MEDIDA, no supuesta: `bench/hito7-superficies.md` §3.2.
    """
    if os.name != "nt":
        return True
    try:
        os.replace(ruta, ruta)
        return True
    except OSError:
        return False


class Vigilante:
    """Vigila directorios y convierte lo que aparece. Una superficie, cero validación.

    El filtro por extensión que hay aquí **no es un predicado de seguridad**: es
    la pregunta «¿sé convertir esto?», y se la hace al grafo, no a una lista
    escrita a mano. La pregunta «¿puedo tocar esto?» no se hace aquí en absoluto.
    """

    def __init__(self, fx: FileX, vigilados, salida: str, destino: str, *,
                 intervalo: float = INTERVALO_POR_DEFECTO,
                 estables: int = ESTABLES_POR_DEFECTO,
                 cerrojo: bool = True,
                 parametros: dict | None = None,
                 timeout: float = TIMEOUT_WATCHER,
                 sobrescribir: bool = False,
                 trabajos: Trabajos | None = None,
                 memoria: Memoria | None = None,
                 recursivo: bool = False,
                 conservar_extension: bool = False) -> None:
        self.fx = fx
        self.vigilados = [os.path.abspath(v) for v in vigilados]
        self.salida = os.path.abspath(salida)
        self.destino = formatos.normaliza(destino)
        self.intervalo = intervalo
        self.estables = max(1, int(estables))
        self.cerrojo = cerrojo
        self.parametros = dict(parametros or {})
        self.timeout = timeout
        self.sobrescribir = sobrescribir
        self.trabajos = trabajos or Trabajos()
        self.memoria = memoria if memoria is not None else Memoria()
        self.recursivo = recursivo
        self.conservar_extension = conservar_extension
        self._pendientes: dict[str, Visto] = {}
        #: Contadores para la bitácora y para las pruebas. No son estadística:
        #: son la única forma de saber si el watcher está haciendo algo.
        self.contadores = {"vistos": 0, "maduros": 0, "atendidos": 0,
                           "saltados": 0, "fallidos": 0}

    # ------------------------------------------------------------- arranque

    def comprobar_raices(self) -> None:
        """Pide al NÚCLEO que valide los directorios vigilados y el de salida.

        Esto no es una copia de la validación: es una llamada a la que hay.
        Sirve para que un watcher apuntado a un sitio prohibido **se niegue a
        arrancar** en vez de girar en vacío denegando fichero a fichero, y
        falla con el mismo `Denegado` opaco de siempre (R4): ni el directorio,
        ni la lista blanca, ni si existe.
        """
        c = self.fx.confinamiento
        if c is None:
            return
        for v in self.vigilados:
            c.resolver(v)
        c.resolver(self.salida, escritura=True)

    # -------------------------------------------------------------- sondeo

    def _candidatos(self) -> list[Huella]:
        """Un `scandir` por directorio vigilado. Sin recursión salvo que se pida.

        Se filtra por extensión **preguntando al grafo**: si desde este origen
        no se llega al destino con los motores presentes, el fichero no es un
        candidato. Es la misma respuesta que da `list_targets`, y por el mismo
        motivo: *«lo que no está aquí no se puede hacer»*.
        """
        out: list[Huella] = []
        for base in self.vigilados:
            for raiz, _dirs, ficheros in os.walk(base):
                for nombre in ficheros:
                    ruta = os.path.join(raiz, nombre)
                    ext = formatos.normaliza(os.path.splitext(nombre)[1])
                    if not ext or ext == self.destino:
                        continue
                    if not self.fx.grafo.camino(ext, self.destino).hay:
                        continue
                    try:
                        st = os.stat(ruta)
                    except OSError:
                        continue                    # desapareció entre medias
                    out.append(Huella(os.path.abspath(ruta),
                                      st.st_size, st.st_mtime_ns))
                if not self.recursivo:
                    break
        return out

    def maduros(self) -> list[Huella]:
        """Un sondeo. Devuelve los ficheros que ya no cambian y no se atendieron.

        Llamarla `estables × intervalo` veces seguidas es lo que separa «lo he
        visto» de «está completo». Un solo sondeo **no** puede saberlo, y esa es
        la parte del watcher que no se puede tomar prestada del núcleo.
        """
        actuales = self._candidatos()
        self.contadores["vistos"] += len(actuales)
        vivos = set()
        listos: list[Huella] = []
        for h in actuales:
            clave = os.path.normcase(h.ruta)
            vivos.add(clave)
            if h in self.memoria:
                continue
            prev = self._pendientes.get(clave)
            if prev is not None and prev.huella == h:
                prev.repeticiones += 1
            else:
                # Primera vez, o el fichero ha cambiado: la cuenta vuelve a 1.
                prev = Visto(huella=h)
                self._pendientes[clave] = prev
            if prev.repeticiones < self.estables:
                continue
            if self.cerrojo and not _estable_en_disco(h.ruta):
                # El `stat` ya no se mueve pero el escritor sigue teniendo el
                # fichero abierto. Se espera otro sondeo: no se descarta.
                continue
            listos.append(h)
        for muerto in [r for r in self._pendientes if r not in vivos]:
            del self._pendientes[muerto]
        self.contadores["maduros"] += len(listos)
        return listos

    # ---------------------------------------------------------- conversión

    def ruta_de_salida(self, entrada: str) -> str:
        """El nombre de salida se DERIVA, y el núcleo lo juzga.

        Aquí no se llama a `nombre_seguro`: se llama en `FileX._resolver`, antes
        que nada y antes incluso de mirar si hay lista blanca. Si esta línea
        produjera `CON.webp` o `algo:oculto.webp`, la conversión se deniega con
        el mensaje opaco — y hay una prueba que lo demuestra para esta
        superficie, porque «escrito y sin llamantes» ya costó una escritura en
        el ADS de un fichero ajeno.

        **Y el tallo COLISIONA, MEDIDO en la primera prueba de humo:** una
        carpeta con `tipico.png` y `tipico.jpg` produce dos veces `tipico.webp`.
        No se pierde nada —R9 salta el segundo con motivo— pero el usuario
        pidió dos conversiones y obtiene una. Con `conservar_extension` la
        salida es `tipico.png.webp` y `tipico.jpg.webp`, que es feo y no
        colisiona; el defecto sigue siendo el nombre limpio porque la mayoría de
        las carpetas vigiladas no mezclan formatos, y porque un fallo ruidoso es
        mejor que un nombre que nadie reconoce.
        """
        nombre = os.path.basename(entrada)
        base = nombre if self.conservar_extension else os.path.splitext(nombre)[0]
        return os.path.join(self.salida, f"{base}.{self.destino}")

    def atender(self, huella: Huella) -> Atendido:
        """Convierte UN fichero. La verificación va dentro, no después.

        No hay aquí ninguna llamada a `contrato.verificar`, y no puede haberla:
        el punto 5 se toma dentro del `with` del directorio desechable, en
        `FileX._un_salto`. Un watcher que convirtiera y verificase luego
        aprobaría el punto 5 sin haber mirado, que es exactamente el fallo que
        el contrato existe para no cometer.
        """
        sal = self.ruta_de_salida(huella.ruta)
        r = Atendido(entrada=huella.ruta, salida=sal)
        t = self.trabajos.nuevo("watch")
        r.job_id = t.id
        t0 = time.perf_counter()

        if os.path.exists(sal) and not self.sobrescribir:
            # R9: no sobrescribir en silencio. El fichero de entrada se marca
            # como atendido igualmente: si no, el watcher lo reintentaría en
            # cada sondeo para siempre.
            r.estado, r.motivo = "saltado", "el destino ya existe"
            self.contadores["saltados"] += 1
            self.trabajos.terminar(t, FALLIDO, {"ok": False, "motivo": r.motivo})
            self.memoria.marcar(huella)
            return r

        try:
            conv = self.fx.convertir(huella.ruta, sal, self.parametros,
                                     timeout=self.timeout)
        except Denegado:
            # No debería llegar: `convertir` ya devuelve el motivo opaco en vez
            # de lanzar. Se captura igual, porque una superficie que revienta
            # con una traza es una superficie que filtra.
            conv = None
        r.ms = (time.perf_counter() - t0) * 1000

        if conv is None:
            r.estado, r.motivo = "denegado", "ruta no accesible"
            self.contadores["fallidos"] += 1
            self.trabajos.terminar(t, FALLIDO, {"ok": False, "motivo": r.motivo})
            self.memoria.marcar(huella)
            return r

        ultimo = conv.saltos[-1] if conv.saltos else None
        r.veredicto = conv.veredicto
        r.cobertura = dict(ultimo.cobertura) if ultimo else {}
        r.sobrantes = {n: b for s in conv.saltos for n, b in (s.sobrantes or {}).items()}
        if conv.ok:
            r.estado = "convertido"
            self.contadores["atendidos"] += 1
            self.trabajos.terminar(t, COMPLETADO, {
                "ok": True, "veredicto": conv.veredicto,
                "ruta_salida": sal, "ms_motor": round(sum(s.ms for s in conv.saltos), 1),
                "camino": conv.camino.formatos if conv.camino else [],
            })
        else:
            r.estado, r.motivo = "fallido", conv.motivo
            self.contadores["fallidos"] += 1
            self.trabajos.terminar(t, FALLIDO, {"ok": False, "motivo": conv.motivo})
        self.memoria.marcar(huella)
        return r

    # ----------------------------------------------------------- el bucle

    def paso(self) -> list[Atendido]:
        """Un ciclo completo: sondear y atender lo maduro. Sin dormir.

        Separada de `correr` a propósito: un bucle con `sleep` dentro no se
        puede probar, y una superficie que no se puede probar no demuestra R10.
        """
        return [self.atender(h) for h in self.maduros()]

    def correr(self, *, ciclos: int | None = None, hasta: float | None = None,
               al_atender=None) -> None:
        """El bucle. Con dos topes explícitos, porque «hasta que lo maten» no
        es un tope y este proyecto tiene una regla sobre eso."""
        n = 0
        fin = (time.time() + hasta) if hasta else None
        while True:
            for r in self.paso():
                if al_atender is not None:
                    al_atender(r)
            n += 1
            if ciclos is not None and n >= ciclos:
                return
            if fin is not None and time.time() >= fin:
                return
            time.sleep(self.intervalo)


# ------------------------------------------------------------------- CLI


def _linea(r: Atendido) -> str:
    if r.estado == "convertido":
        p5 = "sí" if r.cobertura.get("5_escritura") else "NO"
        extra = f"  punto5={p5}"
        if r.sobrantes:
            extra += f"  no declarados: {', '.join(sorted(r.sobrantes))}"
        return f"[{r.estado}] {r.salida}  [{r.veredicto}]  {r.ms:.0f} ms{extra}"
    return f"[{r.estado}] {r.entrada} — {r.motivo}"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="filex-watch",
        description="Vigila carpetas y convierte lo que aparece, verificando "
                    "la salida DENTRO de la conversión.")
    p.add_argument("--vigilar", action="append", required=True,
                   help="directorio a vigilar. Repetible.")
    p.add_argument("--salida", required=True, help="directorio de destino")
    p.add_argument("--destino", required=True, help="formato de salida (webp, pdf...)")
    p.add_argument("--raiz", action="append", default=None,
                   help="raíz permitida (lista blanca). Repetible. Sin ninguna "
                        "no hay confinamiento y se avisa.")
    p.add_argument("--intervalo", type=float, default=INTERVALO_POR_DEFECTO)
    p.add_argument("--estables", type=int, default=ESTABLES_POR_DEFECTO,
                   help="sondeos consecutivos con el mismo (tamaño, mtime) "
                        "antes de dar el fichero por completo")
    p.add_argument("--sin-cerrojo", action="store_true",
                   help="no intentar el renombrado sobre sí mismo (Windows)")
    p.add_argument("--recursivo", action="store_true")
    p.add_argument("--sobrescribir", action="store_true")
    p.add_argument("--conservar-extension", action="store_true",
                   help="nombrar la salida 'x.png.webp' en vez de 'x.webp': "
                        "feo, pero no colisiona cuando la carpeta mezcla "
                        "formatos con el mismo tallo")
    p.add_argument("--memoria", default=None,
                   help="JSON donde recordar lo ya atendido entre reinicios")
    p.add_argument("--params", default=None, help="JSON con el pedido")
    p.add_argument("--timeout", type=float, default=TIMEOUT_WATCHER)
    p.add_argument("--ciclos", type=int, default=None, help="tope de sondeos")
    p.add_argument("--hasta", type=float, default=None, help="tope en segundos")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        parametros = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError as e:
        print(f"--params no es JSON válido: {e}", file=sys.stderr)
        return 2

    try:
        fx = FileX(raices_lectura=args.raiz)
    except ValueError as e:
        print(f"no se puede arrancar: {e}", file=sys.stderr)
        return 2
    if args.raiz is None:
        print("aviso: sin --raiz no hay lista blanca (denegar por defecto está "
              "desactivado)", file=sys.stderr)

    v = Vigilante(fx, args.vigilar, args.salida, args.destino,
                  intervalo=args.intervalo, estables=args.estables,
                  cerrojo=not args.sin_cerrojo, parametros=parametros,
                  timeout=args.timeout, sobrescribir=args.sobrescribir,
                  memoria=Memoria(args.memoria), recursivo=args.recursivo,
                  conservar_extension=args.conservar_extension)
    try:
        v.comprobar_raices()
    except Denegado as e:
        # R4: el mismo mensaje opaco que para «no existe». Un watcher que
        # dijera «esa carpeta no existe» sería un mapa del disco ajeno.
        print(str(e), file=sys.stderr)
        return 2

    os.makedirs(v.salida, exist_ok=True)

    def informar(r: Atendido) -> None:
        if args.json:
            print(json.dumps({
                "entrada": r.entrada, "salida": r.salida, "estado": r.estado,
                "veredicto": r.veredicto, "motivo": r.motivo,
                "ms": round(r.ms, 1), "job_id": r.job_id,
                "cobertura": r.cobertura, "sobrantes": r.sobrantes,
            }, ensure_ascii=False), flush=True)
        else:
            print(_linea(r), flush=True)

    try:
        v.correr(ciclos=args.ciclos, hasta=args.hasta, al_atender=informar)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
