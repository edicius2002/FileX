# -*- coding: utf-8 -*-
"""S3 — dos comprobaciones que deciden cómo se leen los resultados de `_sonda23.py`.

**A. El `fallo D2` no es de la arista: es del verificador.**
`sondear_en_proceso` manda todo fichero de texto sin marcador propio a `_datos`,
y `_datos` declara `formato = "csv"` a todo lo que no sea `.json`. Entonces
`csv.reader` con coma cuenta campos por línea, y cualquier prosa con un número
variable de comas dispara `D2 numero de campos no constante` → **`fallo`**.
Se prueba con tres ficheros escritos A MANO, sin motor de por medio.

**B. Las aristas `real` de K1 hacia texto están rotas HOY por lo mismo.**
`odt→txt`, `md→txt` y `docx→md` están en `_MEDIDAS` como `REAL`, y una conversión
completa por el núcleo devuelve `fallo`. No es un hallazgo de este sondeo: es un
fallo del producto que este sondeo destapa.

**C. MOBI y AZW3, verificados por IDA Y VUELTA.** `bench/hito5-documental.md` §8
deja PENDIENTE «verificar `epub→mobi` y `epub→azw3` con un lector de MOBI».
No hace falta un lector: si `mobi→epub` devuelve el centinela, el MOBI lo tenía.

    python bench/salidas-sondeo-doc/_d2.py
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import contrato  # noqa: E402
from filex.nucleo import FileX  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

from _sonda23 import (CENTINELA, SAL, busca_arista, convertir_forzando,  # noqa: E402
                      entrada_de, registro, texto_de)

#: Escritos a mano. Ningún motor los ha tocado.
A_MANO = {
    "prosa_con_comas.txt":
        "Hola, mundo, esto tiene tres comas.\nY esta linea no tiene ninguna\n",
    "prosa_sin_comas.txt":
        "Hola mundo esto no tiene comas\nY esta linea tampoco\n",
    "tabla_markdown.md":
        "# Informe\n\n| codigo | cantidad |\n|---|---|\n| AX-1 | 128 |\n",
}


def a_mano() -> list:
    out = []
    for nombre, texto in A_MANO.items():
        with DirectorioDeTrabajo(prefijo="filex-s3-d2-") as t:
            p = t.destino(nombre)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(texto)
            censo = t.censo()
            d = os.path.splitext(nombre)[1].lstrip(".")
            res = contrato.verificar(p, None, {"destino": d}, censo)
            out.append({
                "fichero": nombre, "bytes": os.path.getsize(p),
                "veredicto": res.get("veredicto"),
                "hallazgos": [f"{h.get('regla')}/{h.get('severidad')}: {h.get('mensaje')}"
                              for h in (res.get("hallazgos") or [])],
            })
    return out


#: Aristas que `motor_contenedor.py` declara **REAL** y que el contrato rechaza
#: HOY. Las tres primeras por `D2` (destino de texto plano); las dos últimas por
#: `P1 «el PDF no declara ninguna pagina»`, que es un SEGUNDO defecto y no tiene
#: nada que ver con el primero: el contador de páginas busca `/Type /Page` en
#: los bytes crudos (`verificador.py:1250-1269`) y **xelatex mete los objetos de
#: página en flujos comprimidos**, así que cuenta 0. El respaldo por `/Count`
#: cae en el mismo flujo comprimido y también da 0.
#: Son **las 8 aristas `REAL` de `motor_contenedor.py` cuyo destino es texto
#: plano o un PDF de xelatex**, o sea el censo completo de las expuestas, más
#: dos controles.
YA_REALES = (("doc_libreoffice", "odt", "txt"),
             ("doc_pandoc", "md", "txt"),
             ("doc_pandoc", "docx", "md"),
             ("doc_pandoc", "epub", "md"),
             ("doc_pandoc", "html", "md"),
             ("doc_calibre", "epub", "txt"),
             ("doc_pandoc", "md", "pdf"),
             ("doc_pandoc", "docx", "pdf"),
             # CONTROLES. Si estos dos pasan, el defecto no es «los PDF» ni «los
             # motores documentales»: es «los PDF de xelatex» y «el texto plano».
             ("doc_libreoffice", "docx", "pdf"),
             ("doc_libreoffice", "docx", "html"))


def reales_rotas(fx, out) -> list:
    res = []
    for motor, o, d in YA_REALES:
        ar = busca_arista(fx, motor, o, d)
        if ar is None:
            res.append({"motor": motor, "origen": o, "destino": d,
                        "motivo": "no está en el grafo"})
            continue
        salida = os.path.join(out, f"R_{motor[4:]}_{o}2{d}.{d}")
        espia = os.path.join(out, f"R_{motor[4:]}_{o}2{d}_desechable")
        conv = convertir_forzando(fx, ar, entrada_de(o), salida, espia=espia)
        r = registro(conv, "R", motor, o, d, salida, espia=espia)
        r["estado_declarado_en_el_codigo"] = "REAL"
        ruta = salida if os.path.isfile(salida) else os.path.join(espia, f"salida.{d}")
        if d == "pdf" and os.path.isfile(ruta):
            from filex import verificador as _v
            s = _v.sondear_en_proceso(ruta)
            r["n_paginas_sondeadas"] = s.get("n_paginas")
            r["paginas_por_flujo_comprimido"] = s.get("paginas_por_flujo_comprimido")
            r["indicio_texto"] = s.get("indicio_texto")
        res.append(r)
    return res


def ida_y_vuelta(fx, out) -> list:
    """El AZW3 de S23 y las dos semillas, verificados convirtiéndolos a EPUB."""
    res = []
    fuentes = [
        ("S23_azw3_de_mobi", os.path.join(SAL, "out", "S23_calibre_mobi2azw3.azw3")),
        ("semilla_mobi", entrada_de("mobi")),
        ("semilla_azw3", entrada_de("azw3")),
    ]
    ar = busca_arista(fx, "doc_calibre", "epub", "epub")  # se sustituye abajo
    for nombre, fuente in fuentes:
        if not os.path.isfile(fuente):
            res.append({"caso": nombre, "motivo": "falta el fichero", "ruta": fuente})
            continue
        o = os.path.splitext(fuente)[1].lstrip(".")
        ar = busca_arista(fx, "doc_calibre", o, "epub")
        if ar is None:
            res.append({"caso": nombre, "motivo": f"no hay arista {o}→epub"})
            continue
        salida = os.path.join(out, f"V_{nombre}.epub")
        espia = os.path.join(out, f"V_{nombre}_desechable")
        conv = convertir_forzando(fx, ar, fuente, salida, espia=espia)
        ruta = salida if os.path.isfile(salida) else os.path.join(espia, "salida.epub")
        txt = texto_de(ruta) if os.path.isfile(ruta) else ""
        res.append({"caso": nombre, "origen": fuente, "ok": conv.ok,
                    "contrato": conv.saltos[0].veredicto if conv.saltos else "",
                    "bytes": os.path.getsize(ruta) if os.path.isfile(ruta) else 0,
                    "caracteres": len(txt),
                    "centinela_recuperado": CENTINELA in txt,
                    "tabla_ax1": "AX-1" in txt})
    return res


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    out = os.path.join(SAL, "out-d2")
    os.makedirs(out, exist_ok=True)

    d = {"A_ficheros_a_mano": a_mano()}
    for x in d["A_ficheros_a_mano"]:
        print(f"A  {x['fichero']:<22} {x['veredicto']:<12} {x['hallazgos']}")

    fx = FileX()
    d["B_aristas_REAL_hacia_texto"] = reales_rotas(fx, out)
    for x in d["B_aristas_REAL_hacia_texto"]:
        print(f"B  {x.get('motor')} {x.get('origen')}→{x.get('destino')}  "
              f"rc={x.get('rc')} contrato={x.get('contrato')} "
              f"bytes={x.get('bytes')} cent={x.get('centinela')} "
              f"recogida={x.get('recogida')}")

    d["C_ida_y_vuelta_mobi_azw3"] = ida_y_vuelta(fx, out)
    for x in d["C_ida_y_vuelta_mobi_azw3"]:
        print(f"C  {x.get('caso'):<20} bytes={x.get('bytes')} "
              f"car={x.get('caracteres')} centinela={x.get('centinela_recuperado')}")

    with open(os.path.join(SAL, "d2.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
