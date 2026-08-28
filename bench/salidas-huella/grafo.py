"""El grafo tiene que seguir en 210 `real` y 5 `nominal`, con `caducados: {}`.
Si el resellado estuviera mal, aqui caerian 153 aristas a `sin_sondear`."""
import collections
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import sondeo  # noqa: E402
from filex.motores import sondear_todos  # noqa: E402

motores = sondear_todos()
ar = [x for m in motores for x in (m.aristas or [])]
c = collections.Counter(a.estado for a in ar)
res = {"por_estado": dict(c), "total": len(ar),
       "diagnostico": sondeo.diagnostico()}
print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "grafo.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False, default=str)
