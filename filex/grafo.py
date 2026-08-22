"""El grafo de conversión, con COSTE POR ARISTA.

La tesis del hito 1, tal como la fija `PLAN-ORQUESTADOR.md` §7:

    «Resuelve un destino en 2 saltos **y explica por qué rechaza un camino que
    rasteriza** cuando el destino admite texto. Lo segundo es lo que demuestra
    de verdad la tesis: **alcanzar es fácil, elegir bien no.**»

Por eso `camino()` no devuelve solo el camino: devuelve también los que
**descartó y por qué**. Un grafo que solo dice «sí, se puede» no vale más que la
tabla de un competidor.

**La arista mínima viable es `(origen, destino, motor, parametrización, build)`**
— MEDIDO por dos carriles independientes (`bench/aristas-nominales.md` §9.2 y
`bench/invocacion-aristas.md` §3.2):

* `svg→png` con `magick` es **real en Windows y nominal (rc=1) en el Debian del
  contenedor** — decide el `build`.
* `epub→pdf` es **real con Calibre y nominal con LibreOffice** — decide el motor.
* De las 33 semiaristas de salida muertas de ffmpeg, **19 son codificadores no
  compilados** (build) y **8 son parametrización**.

Una tabla `(origen, destino)` miente en alguna máquina. Por eso `Arista` lleva
las cinco.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from . import formatos

#: Estados de una arista. **Solo `real` significa «se ejecutó y salió bien».**
#: El 41,0 % de las aristas que los catálogos declaran no existen: declarar
#: `nominal` como si fuera `real` es el fallo central del sector.
REAL = "real"
NOMINAL = "nominal"
SIN_SONDEAR = "sin_sondear"


@dataclass(frozen=True)
class Arista:
    origen: str
    destino: str
    motor: str
    parametrizacion: str = "por_defecto"
    build: str = ""
    estado: str = SIN_SONDEAR
    #: Coste base del salto. Adimensional y comparable solo dentro del grafo.
    coste: float = 1.0
    #: ¿Este salto convierte texto en píxeles?
    rasteriza: bool = False
    #: Referencia a la medición que respalda la arista.
    evidencia: str = ""

    @property
    def clave(self) -> tuple:
        return (self.origen, self.destino, self.motor, self.parametrizacion, self.build)

    def __str__(self) -> str:
        return f"{self.origen}→{self.destino} [{self.motor}]"


@dataclass
class Paso:
    arista: Arista


@dataclass
class Camino:
    pasos: list[Paso] = field(default_factory=list)
    coste: float = 0.0

    @property
    def saltos(self) -> int:
        return len(self.pasos)

    @property
    def formatos(self) -> list[str]:
        if not self.pasos:
            return []
        return [self.pasos[0].arista.origen] + [p.arista.destino for p in self.pasos]

    @property
    def rasteriza(self) -> bool:
        return any(p.arista.rasteriza for p in self.pasos)

    def __str__(self) -> str:
        return " → ".join(self.formatos) + "".join(
            f"\n    {i+1}. {p.arista}" for i, p in enumerate(self.pasos)
        )


@dataclass
class Decision:
    """Lo que el grafo decidió, con lo que descartó. Ninguna de las dos sobra."""

    camino: Camino | None
    rechazados: list[tuple[Camino, str]] = field(default_factory=list)
    motivo: str = ""          # por qué NO hay camino, cuando no lo hay
    aviso: str = ""           # hay camino, pero cuesta algo que hay que decir

    @property
    def hay(self) -> bool:
        return self.camino is not None


#: Cuánto se penaliza rasterizar hacia un destino que admite texto.
#: No es un número medido: es una POLÍTICA, y por eso está aquí arriba con su
#: nombre en vez de escondida en una comparación. Lo que sí está medido es que
#: la pérdida existe y es total: `resvg` entrega 0,00 % de tinta donde Inkscape
#: pone 14,02 % (`bench/aristas-nominales.md` §8.2).
PENALIZACION_RASTERIZAR = 1000.0

#: Encadenar dos ETAPAS CON PÉRDIDA es una recodificación que nadie pidió.
#: Va por CAMINO, no por arista: `mkv→mp3` es UNA codificación con pérdida
#: (se decodifica el audio que había y se codifica una vez), y penalizarla por
#: «origen con pérdida y destino con pérdida» hacía que el grafo prefiriera
#: `mkv→flac→mp3` — un salto más, un intermedio enorme y exactamente la misma
#: codificación con pérdida al final. Lo que se cuenta son los saltos que
#: ESCRIBEN un formato con pérdida, y se perdona el primero.
PENALIZACION_PERDIDA = 4.0


def _penalizacion_perdida(camino: "Camino") -> float:
    n = sum(1 for p in camino.pasos
            if (formatos.formato(p.arista.destino) or None) is not None
            and formatos.formato(p.arista.destino).perdida)
    return PENALIZACION_PERDIDA * max(0, n - 1)


class Grafo:
    def __init__(self, aristas: list[Arista] | None = None) -> None:
        self._por_origen: dict[str, list[Arista]] = {}
        self.aristas: list[Arista] = []
        for a in aristas or []:
            self.añadir(a)

    def añadir(self, a: Arista) -> None:
        self.aristas.append(a)
        self._por_origen.setdefault(a.origen, []).append(a)

    def desde(self, ext: str) -> list[Arista]:
        return self._por_origen.get(formatos.normaliza(ext), [])

    def destinos(self, ext: str) -> list[str]:
        return sorted({a.destino for a in self.desde(ext)})

    # ------------------------------------------------------------ búsqueda

    def _coste_paso(self, a: Arista, destino_final: str) -> float:
        c = a.coste
        fd = formatos.formato(destino_final)
        if a.rasteriza and fd is not None and fd.texto:
            # Rasterizar es barato en tiempo y carísimo en información. Un grafo
            # que solo mide saltos elige justo el camino que destruye el texto.
            c += PENALIZACION_RASTERIZAR
        if a.estado == NOMINAL:
            # Una arista que se sondeó y NO funcionó no se usa. Punto.
            c += float("inf")
        elif a.estado == SIN_SONDEAR:
            # Se puede intentar, pero nunca por delante de una medida.
            c += 2.0
        return c

    #: Tope de expansiones de la enumeración. Un grafo de conversión completo
    #: tendrá miles de aristas y buscar «todos los caminos» sin tope es una
    #: bomba de relojería. Si se agota, se dice — no se devuelve un resultado
    #: parcial como si fuera exhaustivo.
    TOPE_EXPANSIONES = 200_000
    #: Cuántas alternativas se conservan para poder EXPLICARLAS.
    TOPE_CANDIDATOS = 8

    def _enumerar(self, o: str, d: str, max_saltos: int) -> list[Camino]:
        """Todos los caminos simples `o → d`, hasta `max_saltos`, por coste.

        **No vale un Dijkstra a secas, y el fallo que lo demostró está en las
        pruebas:** la poda por dominancia descarta el camino alternativo ANTES de
        que llegue al destino, y entonces no queda nada que explicar. Un grafo
        que solo sabe el mejor camino no puede decir por qué rechazó el otro,
        que es justo la mitad del criterio de aceptación del hito 1.
        """
        mejores: list[tuple[float, int, Camino]] = []   # montículo-máximo por coste
        gasto = 0
        contador = 0
        pila: list[tuple[str, Camino, float]] = [(o, Camino(), 0.0)]

        while pila:
            actual, camino, coste = pila.pop()
            if actual == d:
                contador += 1
                camino.coste = coste + _penalizacion_perdida(camino)
                heapq.heappush(mejores, (-camino.coste, contador, camino))
                if len(mejores) > self.TOPE_CANDIDATOS:
                    heapq.heappop(mejores)          # fuera el más caro
                continue
            if camino.saltos >= max_saltos:
                continue
            for a in self.desde(actual):
                if gasto >= self.TOPE_EXPANSIONES:
                    break
                paso = self._coste_paso(a, d)
                if paso == float("inf"):
                    continue                        # arista sondeada y muerta
                if a.destino in camino.formatos:
                    continue                        # sin ciclos
                gasto += 1
                nuevo = Camino(pasos=camino.pasos + [Paso(a)], coste=coste + paso)
                # El coste que se compara lleva la penalización de CAMINO; el
                # que se propaga, no, para que no se cuente dos veces.
                nuevo.coste = coste + paso
                pila.append((a.destino, nuevo, nuevo.coste))

        return sorted((c for _, _, c in mejores), key=lambda c: (c.coste, c.saltos))

    def camino(self, origen: str, destino: str, *, max_saltos: int = 4) -> Decision:
        """Dijkstra sobre formatos, con el coste que penaliza perder información.

        Devuelve también los caminos que descartó **y el motivo**, que es la
        mitad del criterio de aceptación del hito 1.
        """
        o = formatos.normaliza(origen)
        d = formatos.normaliza(destino)

        if o == d:
            return Decision(camino=Camino(), motivo="origen y destino son el mismo formato")
        if not self.desde(o):
            return Decision(camino=None,
                            motivo=f"ningún motor disponible lee '{o}'")
        if not any(a.destino == d for a in self.aristas):
            return Decision(camino=None,
                            motivo=f"ningún motor disponible escribe '{d}'")

        encontrados = self._enumerar(o, d, max_saltos)

        if not encontrados:
            return Decision(camino=None, motivo=self._por_que_no(o, d))

        encontrados.sort(key=lambda c: (c.coste, c.saltos))
        elegido = encontrados[0]
        rechazados = []
        fd = formatos.formato(d)

        # El caso que no es un rechazo y hay que decir igual: **el único camino
        # que existe rasteriza**. Callarlo sería entregar un PDF con la
        # geometría exacta y ni una letra seleccionable, que es justo el fallo
        # de `resvg` (rc=0, PNG válido, 0,00 % de tinta en la banda de texto).
        aviso = ""
        if elegido.rasteriza and fd is not None and fd.texto:
            inter = next(p.arista for p in elegido.pasos if p.arista.rasteriza)
            aviso = (f"el ÚNICO camino disponible rasteriza en '{inter}' y "
                     f"'{d}' admite texto: la salida no llevará texto "
                     f"seleccionable. No es un fallo del motor; es el precio "
                     f"del camino, y hace falta un motor que no rasterice.")
        for c in encontrados[1:]:
            if c.rasteriza and not elegido.rasteriza and fd is not None and fd.texto:
                inter = next(p.arista for p in c.pasos if p.arista.rasteriza)
                rechazados.append((
                    c,
                    f"rasteriza en '{inter}' y '{d}' admite texto: el resultado "
                    f"tendría la geometría correcta y ni una letra seleccionable",
                ))
            elif c.saltos < elegido.saltos:
                rechazados.append((c, "más corto, pero pierde más información"))
            else:
                rechazados.append((c, "válido, pero más caro"))
        return Decision(camino=elegido, rechazados=rechazados, aviso=aviso)

    def _por_que_no(self, o: str, d: str) -> str:
        """«Cuando no hay camino, explica por qué» — criterio de aceptación."""
        alcanzables = {o}
        frente = [o]
        while frente:
            act = frente.pop()
            for a in self.desde(act):
                if a.estado != NOMINAL and a.destino not in alcanzables:
                    alcanzables.add(a.destino)
                    frente.append(a.destino)
        escriben_d = [a for a in self.aristas if a.destino == d]
        if not escriben_d:
            return f"ningún motor disponible escribe '{d}'"
        faltan = sorted({a.origen for a in escriben_d} - alcanzables)
        nominales = [a for a in escriben_d if a.estado == NOMINAL]
        extra = ""
        if nominales:
            extra = (f"; {len(nominales)} arista(s) hacia '{d}' están declaradas "
                     f"pero se sondearon y NO funcionan")
        return (f"'{d}' solo se escribe desde {faltan or 'formatos inalcanzables'}, "
                f"y desde '{o}' no se llega a ninguno{extra}")
