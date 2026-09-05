"""Control de discriminacion del carril `cob/png`.

La cobertura es la unica metrica del proyecto que se puede subir sin medir
nada: `try: f(x) except: pass` sube el porcentaje y no afirma nada. Este arnes
comprueba lo contrario para cada funcion objetivo: **rompe una linea de
`filex/verificador.py` y exige que el modulo se ponga ROJO**. Una mutacion que
deja la suite verde es una funcion ejecutada pero no juzgada, y se publica como
tal.

Metodo, con las trampas del proyecto delante:

* **Trampa 119** — no se usa `git stash push <fichero>`: sobre un fichero ya
  commiteado no hace nada y devuelve 0. Aqui se guardan los BYTES originales al
  empezar y se reescriben al terminar cada celda.
* **Trampa 38 / 91** — se registra que la condicion se dio: cada celda
  comprueba que el fichero cambio de verdad (`sha256` distinto) ANTES de
  ejecutar, y que volvio al original despues. Una celda cuyo parche no se
  aplico se marca `no_aplicada` y NO cuenta como discriminante.
* **Trampa 60** — se comprueba que la fuente mutada COMPILA. Un fallo de
  sintaxis pondria rojo el modulo entero por el motivo equivocado y regalaria
  una discriminacion falsa.
* **Trampa 84** — mientras corre esto no se toca ni el codigo que mide ni el
  que se mide.

Al terminar, `filex/verificador.py` queda byte a byte como estaba (se verifica
con su `sha256`).
"""

import hashlib
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FUENTE = os.path.join(RAIZ, "filex", "verificador.py")
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "discriminacion.json")
PY = sys.executable

# (id, funcion tocada, fragmento que se busca, con que se sustituye)
# El fragmento tiene que ser UNICO en el fichero: si no, la celda se marca
# `no_aplicada` en vez de tocar algo que no era.
MUTACIONES = [
    ("M01", "_paeth", "    return b if pb <= pc else c",
     "    return c if pb <= pc else b"),
    ("M02", "_rep", "        _FFS[clave] = bytes([valor]) * n",
     "        _FFS[clave] = bytes([(valor + 1) & 255]) * n"),
    ("M03", "_desfiltrar_carril (filtro 3, Average)",
     "            a = (filt[j] + ((a + previo[j]) >> 1)) & 255",
     "            a = (filt[j] + ((a + previo[j] + 1) >> 1)) & 255"),
    ("M04", "_desfiltrar_carril (filtro 4: orden de a y b) [EQUIVALENTE]",
     "            a = (filt[j] + _paeth(a, b, c)) & 255",
     "            a = (filt[j] + _paeth(b, a, c)) & 255"),
    ("M04b", "_desfiltrar_carril (filtro 4: el vecino de arriba-izquierda)",
     "            out[j] = a\n            c = b",
     "            out[j] = a\n            c = 0"),
    ("M05", "_pixel_en_byte", "            return k", "            return 0"),
    ("M06", "_alfa_min_png (salida por cabecera)",
     '        if m["trns"] is None and ct not in (4, 6):\n            return r',
     '        if m["trns"] is None and ct not in (4, 6):\n'
     '            return dict(r, filas_leidas=1)'),
    ("M07", "_alfa_min_png (tabla de la paleta empaquetada)",
     "                tabla = bytes(min(alfa[(v >> (8 - bd * (k + 1))) & masc]\n"
     "                                  for k in range(por_byte)) for v in range(256))",
     "                tabla = bytes(max(alfa[(v >> (8 - bd * (k + 1))) & masc]\n"
     "                                  for k in range(por_byte)) for v in range(256))"),
    ("M08", "_alfa_min_png (bits de relleno de la ultima celda)",
     "                if sobra and bd < 8 and len(car):\n"
     "                    # los bits de relleno de la ultima celda no son pixeles",
     "                if False and bd < 8 and len(car):\n"
     "                    # los bits de relleno de la ultima celda no son pixeles"),
    ("M09", "_alfa_min_png (carril del alfa)",
     "\n        desp = (canales - 1) * bps",
     "\n        desp = max(0, (canales - 2)) * bps"),
    ("M10", "_alfa_min_png (fila previa al salir del atajo)",
     "                previos = [bytearray(_rep(0 if y == 0 else maxv, an))",
     "                previos = [bytearray(_rep(maxv if y == 0 else 0, an))"),
    # M11 y M11b son el MISMO atajo por los dos lados. Un patron mas ESTRICTO
    # (M11) no puede dar un veredicto falso: la fila se reconstruye igual, solo
    # que sin atajo. Uno mas LAXO (M11b) se traga transparencia real, y eso si
    # tiene que verse. Publicar solo M11 diria que la prueba no juzga el atajo;
    # lo que dice el par es que juzga la mitad que importa.
    ("M11", "_PATRON_OPACO (filtro 3, fila no inicial) [mas ESTRICTO]",
     "    False: {0: (255, 255), 1: (255, 0), 2: (0, 0), 3: (128, 0), 4: (0, 0)},",
     "    False: {0: (255, 255), 1: (255, 0), 2: (0, 0), 3: (129, 0), 4: (0, 0)},"),
    ("M11b", "_alfa_min_png (el atajo mira solo el primer byte) [mas LAXO]",
     "                if all(c[:1] == bytes([b0]) and c[1:] == _rep(resto, len(c) - 1)\n"
     "                       for c in carriles):",
     "                if all(c[:1] == bytes([b0]) for c in carriles):"),
    ("M12", "_ADAM7 (geometria de la pasada 5)",
     "_ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),\n"
     "          (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))",
     "_ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),\n"
     "          (0, 2, 4, 4), (1, 0, 2, 2), (0, 1, 1, 2))"),
    ("M13", "_alfa_min_png_adam7 (mapeo a coordenadas reales)",
     '                    r["primer_transparente"] = (min(xini + idx * xpaso, an - 1),\n'
     "                                                yini + y * ypaso)",
     '                    r["primer_transparente"] = (min(xini + idx * ypaso, an - 1),\n'
     "                                                yini + y * ypaso)"),
    ("M14", "_alfa_min_png_adam7.rellenar (tope del bucle)",
     "        while len(buf) < n:", "        while len(buf) < n - 1:"),
    ("M14b", "_alfa_min_png_adam7.rellenar (se acabaron los IDAT)",
     "                return len(buf) >= n", "                return True"),
    ("M14c", "_alfa_min_png_adam7.rellenar (lo que aporta cada bloque)",
     "            buf.extend(do.decompress(bloque))",
     "            buf.extend(do.decompress(bloque)[:-1])"),
    ("M15", "_alfa_min_png_adam7 (pareja hi/lo de 16 bits)",
     "                        v = 65280 + (min(lo) if lo else 255)",
     "                        v = 65280 + (max(lo) if lo else 255)"),
    ("M16", "_leer_plte (troceado de la paleta)",
     "            return [(d[i], d[i + 1], d[i + 2]) for i in range(0, ln - 2, 3)]",
     "            return [(d[i], d[i + 1], d[i + 2]) for i in range(1, ln - 2, 3)]"),
    ("M17", "_predice (modo 3, arriba-derecha)",
     "    if modo == 3:\n        return TR", "    if modo == 3:\n        return TL"),
    ("M18", "_predice (modo 10)",
     "        return _med2(_med2(L, TL), _med2(T, TR))",
     "        return _med2(_med2(L, TR), _med2(T, TL))"),
    ("M19", "_selecciona", "    return a if d <= 0 else b",
     "    return b if d <= 0 else a"),
    ("M20", "_clamp_full (saturacion)",
     "        v |= (0 if x < 0 else (255 if x > 255 else x)) << desp\n    return v\n\n\n"
     "def _clamp_half",
     "        v |= (0 if x < 0 else (254 if x > 255 else x)) << desp\n    return v\n\n\n"
     "def _clamp_half"),
    ("M21", "_clamp_half (la mitad)",
     "        x = av + (av - ((c >> desp) & 0xFF)) // 2",
     "        x = av + (av - ((c >> desp) & 0xFF)) // 3"),
    ("M22", "_distancia_plano (codigos > 120)",
     "        return cod - 120", "        return cod - 121"),
    ("M23", "_codigo_a_plano (orden de la tabla)",
     "    pares.sort(key=lambda p: (p[0] * p[0] + p[1] * p[1], -p[1], p[0] < 0))",
     "    pares.sort(key=lambda p: (p[0] * p[0] + p[1] * p[1], p[1], p[0] < 0))"),
    ("M24", "_med2", "    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a & b)",
     "    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a | b)"),
    ("M25", "_alfa_min_png (normalizacion final de 16 bits)",
     '        r["alfa_min"] = mn_pareja / float(tope)',
     '        r["alfa_min"] = mn_pareja / float(tope) if mn_pareja else 0.5'),
]


# Mutantes EQUIVALENTES: cambian el texto y no el comportamiento. Que salgan
# verdes NO es un hueco de la prueba, y decirlo exige la razon medida.
EQUIVALENTES = {
    "M04": "`_paeth` es SIMETRICO en sus dos primeros argumentos: comprobado "
           "exhaustivamente, 0 asimetrias en los 8 355 840 tercetos con a<b "
           "(bench/salidas-cobertura-png/_paeth_simetria.py). Intercambiarlos "
           "no puede cambiar ningun pixel.",
    "M11": "El patron de fila opaca es un ATAJO. Un valor mas estricto solo "
           "hace que la fila se reconstruya de verdad, con el mismo resultado: "
           "cuesta tiempo, no correccion. El lado peligroso -- un patron mas "
           "LAXO, que se traga transparencia real -- es M11b, y ese SI se ve.",
    "M14": "El tope del bucle decide cuando dejar de pedir bloques; el "
           "veredicto lo da el `return len(buf) >= n`, que no se toca. Los "
           "bloques llegan en bulto, asi que pedir un byte menos no cambia que "
           "bloques se consumen. Los dos lados que si deciden son M14b (el fin "
           "de los IDAT) y M14c (lo que aporta cada bloque), y los dos se ven.",
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def corre():
    r = subprocess.run([PY, "-m", "unittest", "pruebas.test_cob_png"],
                       cwd=RAIZ, capture_output=True, timeout=900)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    fallos = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)",
                                   txt, re.M)))
    m = re.search(r"Ran (\d+) tests", txt)
    return {"rc": r.returncode, "pruebas": int(m.group(1)) if m else None,
            "fallan": ["%s.%s" % (b.rsplit(".", 1)[-1], a) for a, b in fallos],
            "n_fallan": len(fallos)}


def main():
    original = open(FUENTE, "rb").read()
    sha0 = sha(original)
    filas = []
    verde = corre()
    if verde["rc"] != 0:
        print("El modulo NO esta verde antes de empezar; se aborta.")
        print(verde)
        return 1
    print("control: sin mutar -> %d pruebas, rc=0" % verde["pruebas"])

    for ident, funcion, viejo, nuevo in MUTACIONES:
        texto = original.decode("utf-8")
        n = texto.count(viejo)
        fila = {"id": ident, "funcion": funcion, "ocurrencias": n,
                "fragmento": viejo.strip().splitlines()[0][:90]}
        if n != 1:
            fila.update({"aplicada": False,
                         "motivo": "el fragmento aparece %d veces" % n})
            filas.append(fila)
            print("%s %-46s NO APLICADA (%d ocurrencias)" % (ident, funcion, n))
            continue
        mutado = texto.replace(viejo, nuevo).encode("utf-8")
        try:
            compile(mutado.decode("utf-8"), FUENTE, "exec")
        except SyntaxError as e:      # trampa 60: un falso rojo de sintaxis
            fila.update({"aplicada": False, "motivo": "no compila: %s" % e})
            filas.append(fila)
            print("%s %-46s NO APLICADA (no compila)" % (ident, funcion))
            continue
        with open(FUENTE, "wb") as fh:
            fh.write(mutado)
        assert sha(open(FUENTE, "rb").read()) != sha0, "el parche no se aplico"
        try:
            res = corre()
        finally:
            with open(FUENTE, "wb") as fh:
                fh.write(original)
            assert sha(open(FUENTE, "rb").read()) == sha0, "no se restauro"
        fila.update({"aplicada": True, "sha_mutado": sha(mutado)[:16], **res})
        fila["discrimina"] = res["rc"] != 0
        if ident in EQUIVALENTES:
            fila["equivalente"] = EQUIVALENTES[ident]
        filas.append(fila)
        print("%s %-46s %s  (%d pruebas rojas) %s"
              % (ident, funcion, "ROJO " if res["rc"] else "VERDE",
                 res["n_fallan"], res["fallan"][:2]))

    resumen = {
        "interprete": sys.version.split()[0],
        "plataforma": sys.platform,
        "modulo": "pruebas.test_cob_png",
        "pruebas_en_verde": verde["pruebas"],
        "sha256_verificador": sha0,
        "mutaciones": len(MUTACIONES),
        "aplicadas": sum(1 for f in filas if f.get("aplicada")),
        "discriminan": sum(1 for f in filas if f.get("discrimina")),
        "equivalentes": sum(1 for f in filas
                            if f.get("aplicada") and not f.get("discrimina")
                            and f.get("equivalente")),
        "sin_explicar": [f["id"] for f in filas
                         if f.get("aplicada") and not f.get("discrimina")
                         and not f.get("equivalente")],
        "celdas": filas,
    }
    json.dump(resumen, open(SALIDA, "w"), indent=1)
    print("\naplicadas %d de %d, discriminan %d, equivalentes %d"
          % (resumen["aplicadas"], resumen["mutaciones"],
             resumen["discriminan"], resumen["equivalentes"]))
    for f in filas:
        if f.get("aplicada") and not f.get("discrimina"):
            print("  VERDE %s %s -- %s" % (
                f["id"], f["funcion"],
                f.get("equivalente", "*** SIN EXPLICAR: es un hueco")))
    assert sha(open(FUENTE, "rb").read()) == sha0
    print("filex/verificador.py restaurado (sha256 %s)" % sha0[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
