#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verificador.py — ENVOLTORIO. El codigo vive ahora en `filex/verificador.py`.

HITO 3, la mudanza. Hasta el 22/08/2026 este fichero eran las 5.197 lineas del
contrato de cinco puntos. Ahora esas 5.197 lineas, **byte a byte identicas**
(sha256 b531b4adac9b6b76b890758040eb56e8acae846bbf1a2a020caafc536a88496c), estan
en `filex/verificador.py`, que es donde tienen que estar: la verificacion es
producto, no arnes de medicion.

POR QUE QUEDA UN ENVOLTORIO Y NO UN BORRADO
-------------------------------------------
Diecinueve arneses de `bench/salidas-*/` hacen exactamente esto:

    sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
    import verificador as V

y despues tocan 33 nombres del modulo: `V.verificar`, `V.firma_real`, `V.censar`
... y tambien `V._ffmpeg_framemd5`, `V._png_meta`, `V._gs_texto`,
`V._pixel_magick`, `V._paleta_gif`, `V._magick_metrica` — DOCE de los 33 son
privados. Ademas
`bench/verificador-fidelidad.md` y `bench/firmas-contrato.md` publican ordenes
literales `python bench/scripts/verificador.py --salida ...` como el modo de
reproducir sus tablas. Romper cualquiera de las dos cosas es romper la
trazabilidad del repositorio, que es lo que lo hace util.

POR QUE `sys.modules[__name__] = _v` Y NO UN `from ... import *`
----------------------------------------------------------------
Tres motivos, y el tercero es el que decide:

  1. `import *` NO trae los nombres que empiezan por `_`, y los arneses usan
     seis. Habria que enumerarlos a mano y la lista se quedaria vieja.
  2. Reexportar copia REFERENCIAS: `V.FIRMAS` seria el mismo objeto, pero
     rebindear un nombre de modulo (lo que hace `V.v2(False)`, que escribe una
     bandera global) dejaria de verse desde el otro nombre.
  3. `V.v2()` existe justo para eso: apagar la regla V2 desde fuera. Con dos
     objetos-modulo habria DOS banderas y una de las dos mentiria. Aliasando en
     `sys.modules` hay UN solo objeto-modulo y UN solo estado global, se importe
     por donde se importe. Es el patron de `six.moves`, y CPython lo soporta a
     proposito: `importlib._bootstrap._load` relee `sys.modules[spec.name]`
     despues de ejecutar el modulo.

El coste es cero y el comportamiento, identico: `bench/salidas-hito3/` tiene la
comparacion de las 53 salidas del patron oro antes y despues, con los dos
motores de sondeo, los 9 fallos fabricados, el punto 5 con censo y el grupo de
fidelidad. Ver `bench/hito3-mudanza.md`.
"""

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from filex import verificador as _v  # noqa: E402

if __name__ == "__main__":
    # La CLI de los informes sigue valiendo palabra por palabra:
    #   python bench/scripts/verificador.py --salida F --entrada G --destino webp
    sys.exit(_v.main())
else:
    # UN solo objeto-modulo. `import verificador as V` y
    # `from filex import verificador` devuelven el MISMO, con los mismos
    # privados y la misma bandera de V2.
    sys.modules[__name__] = _v
