"""R18 — un directorio de trabajo propio y DESECHABLE por conversión.

**Y no es higiene: es REQUISITO DE COSTE.** MEDIDO
(`bench/contrato-quinto-punto.md` §2.2): con R18 el quinto punto del contrato
cuesta **+11,0 %**; sin él, sobre un directorio de 1.000 ficheros, **×8,6 el
contrato entero**. R18 es lo que hace viable el punto 5.

Y el punto 5 es **el único del contrato que no se puede verificar a posteriori**:
hay que estar mirando cuando el motor escribe. Sin censo, **49 de las 53 salidas
del patrón oro bajan de `ok` a `ok_parcial`**. Por eso este módulo no es una
utilidad de limpieza: es el sitio donde la verificación entra dentro de la
conversión en vez de ser un paso posterior.

Lo que motivó la regla, MEDIDO (`bench/aristas-nominales.md` §5.2):

    ffmpeg -i trivial.mp4 DEST/t.mpd   -> t.mpd (1.234 B) en el destino
                                          y 528.447 B de segmentos DASH en el cwd
    magick trivial.png ... DEST/u.html -> u.html y u.png en el destino
                                          y u_map.shtml en el cwd

Aparecieron como **33 ficheros no pedidos en la raíz del repositorio**.
"""

from __future__ import annotations

import os
import shutil
import tempfile

_VERIFICADOR = None


def _censar_dir(directorio: str) -> dict:
    """Censo {nombre: tamaño} de un directorio, un solo `scandir`, sin recursión.

    Se delega en `bench/scripts/verificador.py` si está importable, para no tener
    dos implementaciones del mismo censo divergiendo. Si no lo está, esta copia
    es equivalente.
    """
    global _VERIFICADOR
    if _VERIFICADOR is None:
        from . import contrato

        _VERIFICADOR = contrato.verificador()
    if _VERIFICADOR is not None and hasattr(_VERIFICADOR, "censar_dir"):
        return _VERIFICADOR.censar_dir(directorio)
    d = {}
    try:
        with os.scandir(directorio) as it:
            for e in it:
                try:
                    d[e.name] = e.stat(follow_symlinks=False).st_size if e.is_file() else -1
                except OSError:
                    d[e.name] = -1
    except OSError:
        return {}
    return d


class DirectorioDeTrabajo:
    """Un directorio desechable por conversión, con censo de salida.

    Uso::

        with DirectorioDeTrabajo() as t:
            argv = motor.orden(entrada, t.destino("salida.webp"), pedido)
            res = invocacion.ejecutar(argv, cwd=t.ruta)
            censo = t.censo()          # ANTES de salir: después ya no existe
            t.recoger("salida.webp", destino_real)

    El `cwd` del motor va DENTRO. Validar la ruta de salida no basta: R8 y R16
    asumen que el motor escribe donde se le dice, y hay motores que no.
    """

    def __init__(self, prefijo: str = "filex-") -> None:
        self.ruta = tempfile.mkdtemp(prefix=prefijo)
        self._censo_final: dict | None = None
        self._recogidos: list[str] = []

    # ------------------------------------------------------------------ API

    def destino(self, nombre: str) -> str:
        """Ruta dentro del directorio de trabajo para un nombre de salida."""
        return os.path.join(self.ruta, nombre)

    def censo(self) -> dict:
        """Censo del punto 5, en el formato que espera `verificador.verificar`.

        Con R18 el directorio está **vacío antes**, así que basta el censo de
        DESPUÉS: todo lo que haya aquí lo escribió el motor. Ese es justo el
        ahorro que convierte el punto 5 de ×8,6 en +11,0 %.
        """
        if self._censo_final is None:
            self._censo_final = _censar_dir(self.ruta)
        clave = os.path.abspath(self.ruta)
        return {"antes": {clave: {}}, "despues": {clave: dict(self._censo_final)}}

    def sobrantes(self, declarados) -> dict:
        """Lo que el motor escribió y NADIE pidió. `{nombre: bytes}`.

        Es la lectura humana del punto 5. El veredicto formal lo da el contrato.
        """
        cen = self._censo_final if self._censo_final is not None else _censar_dir(self.ruta)
        dec = {os.path.basename(d) for d in declarados}
        return {n: t for n, t in cen.items() if n not in dec}

    def recoger(self, nombre: str, destino_final: str) -> str:
        """Mueve una salida real fuera del desechable, antes de borrarlo."""
        origen = self.destino(nombre)
        os.makedirs(os.path.dirname(os.path.abspath(destino_final)) or ".", exist_ok=True)
        shutil.move(origen, destino_final)
        self._recogidos.append(destino_final)
        return destino_final

    def cerrar(self) -> None:
        """Borra el directorio ENTERO. Lo que no se recogió, se pierde: es
        exactamente lo que se quiere de un desechable."""
        shutil.rmtree(self.ruta, ignore_errors=True)

    # -------------------------------------------------------------- contexto

    def __enter__(self) -> "DirectorioDeTrabajo":
        return self

    def __exit__(self, *exc) -> None:
        # El censo se toma aquí si nadie lo pidió: el punto 5 no se recupera
        # después, y salir sin haber mirado es perderlo para siempre.
        if self._censo_final is None:
            self._censo_final = _censar_dir(self.ruta)
        self.cerrar()
