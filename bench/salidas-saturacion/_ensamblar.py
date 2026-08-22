# -*- coding: utf-8 -*-
"""Ensambla bench/saturacion-herramientas.md a partir de las secciones y las
tablas generadas. Sin transcripcion a mano."""
import io
import os

BASE = os.path.dirname(os.path.abspath(__file__))
INF = os.path.join(BASE, "..", "saturacion-herramientas.md")


def leer(n):
    return io.open(os.path.join(BASE, n), encoding="utf-8").read().rstrip() + "\n"


s = io.open(INF, encoding="utf-8").read()

tablas = leer("_seccion3.md") + u"""
---

## 4. Las tablas completas

<details>
<summary><b>Haiku 4.5 — 360 ejecuciones (desplegar)</b></summary>

""" + leer("tablas_haiku.md") + u"""
</details>

<details>
<summary><b>Sonnet 4.5 — 180 ejecuciones (desplegar)</b></summary>

""" + leer("tablas_sonnet.md") + u"""
</details>
"""

s = s.replace(u"<!--TABLAS-->", tablas)
s = s.replace(u"<!--VEREDICTO-->", leer("_seccion678.md"))
s = s.replace(u"<!--PRESUPUESTO-->", leer("_seccion7.md"))
s = s.replace(u"<!--LIMITACIONES-->", leer("_seccion8.md"))

io.open(INF, "w", encoding="utf-8").write(s)
print("informe ensamblado:", len(s), "caracteres")
