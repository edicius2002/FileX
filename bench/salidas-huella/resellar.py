"""Resella el campo `huella` de `filex/sondeo/*.json` tras cambiar el ALGORITMO
de la huella. Por script y dejando el `sha256` de antes y despues; nunca a mano.

POR QUE ES LEGITIMO, Y LA PRUEBA QUE LO SOSTIENE
------------------------------------------------
Cambiar como se calcula una huella cambia su valor aunque el codigo medido no
haya cambiado ni una letra. Resellar seria indulgencia si el codigo hubiera
cambiado; aqui no lo ha hecho, y se DEMUESTRA antes de tocar nada: con el
algoritmo de HEAD, las cinco huellas almacenadas coinciden exactamente con las
del `verificador.py`, `motores.py` y `motor_contenedor.py` del arbol de trabajo
(`diferencias()` vacia en los cinco). Es el mismo argumento de
`deuda-sondeo.md` sec.3.3: las medidas se tomaron con ESTE codigo, asi que se
SELLAN, no se tiran.

Si esa comprobacion previa fallara en algun fichero, ese fichero NO se resella:
ya estaba caducado por codigo y hay que RESONDEARLO.

Uso:  python resellar.py --comprobar    (no escribe: solo dice que haria)
      python resellar.py --escribir

Salida: bench/salidas-huella/resellado.json
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(RAIZ, "filex", "sondeo")
sys.path.insert(0, RAIZ)

from filex import huella as NUEVA  # noqa: E402


def _sha(p: str) -> str:
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _vieja():
    src = subprocess.run(["git", "-C", RAIZ, "show", "HEAD:filex/huella.py"],
                         capture_output=True, text=True, encoding="utf-8",
                         timeout=60).stdout
    p = os.path.join(SAL, "_huella_head.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("_huella_head_res", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Cargado suelto, `_PAQUETE` apuntaria a bench/: se le devuelve el suyo, y
    # `de_motor_por_nombre` se replica aqui porque su import es relativo.
    mod._PAQUETE = os.path.join(RAIZ, "filex")
    return mod


def _clases_por_nombre() -> dict:
    from filex import motores
    fuera = {}
    for cls in list(motores.MOTORES) + motores._descubrir():
        try:
            fuera[cls().nombre] = cls
        except Exception:
            continue
    return fuera


def _de_motor(mod, nombre: str, clases: dict) -> dict:
    cls = clases.get(nombre)
    h = {"invocacion": mod.de_fichero(os.path.join(mod._PAQUETE,
                                                   "invocacion.py")),
         "contrato": mod.de_contrato()}
    if cls is not None:
        h["motor"] = mod.de_clase(cls)
    return h


def main() -> None:
    escribir = "--escribir" in sys.argv
    VIEJA = _vieja()
    clases = _clases_por_nombre()
    filas = []
    for f in sorted(os.listdir(DIR)):
        if not f.endswith(".json"):
            continue
        p = os.path.join(DIR, f)
        with open(p, encoding="utf-8") as fh:
            cuerpo = json.load(fh)
        motor = cuerpo.get("motor") or f[:-5]
        guardada = cuerpo.get("huella") or {}
        # 1. la comprobacion que autoriza el resellado
        VIEJA.olvidar()
        con_algoritmo_viejo = _de_motor(VIEJA, motor, clases)
        coincide = not VIEJA.diferencias(guardada, con_algoritmo_viejo)
        NUEVA.olvidar()
        nueva = _de_motor(NUEVA, motor, clases)
        fila = {
            "fichero": f, "motor": motor,
            "sha256_antes": _sha(p),
            "huella_antes": guardada,
            "coincide_con_algoritmo_viejo": coincide,
            "huella_nueva": nueva,
            "resellado": False,
        }
        if coincide and escribir:
            # Sustitucion TEXTUAL de cada valor: reescribir el JSON entero
            # reformatearia 210 aristas y el diff no diria nada. Solo se
            # tocan los componentes que el fichero YA declaraba (regla de
            # `diferencias()`: lo que no declara, no se compara).
            with open(p, encoding="utf-8", newline="") as fh:
                texto = fh.read()
            for k, v in guardada.items():
                if k not in nueva or nueva[k] == v:
                    continue
                antes, texto = texto, texto.replace(f'"{k}": "{v}"',
                                                    f'"{k}": "{nueva[k]}"', 1)
                assert texto != antes, f"{f}: no se encontro {k}={v}"
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(texto)
            json.load(open(p, encoding="utf-8"))     # sigue siendo JSON
            fila["resellado"] = True
            fila["sha256_despues"] = _sha(p)
        elif not coincide:
            fila["accion"] = "NO se resella: ya estaba caducado, hay que RESONDEAR"
        filas.append(fila)

    res = {"escrito": escribir, "ficheros": filas}
    with open(os.path.join(SAL, "resellado.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    for x in filas:
        print(f"{x['fichero']:22s} coincide_viejo={x['coincide_con_algoritmo_viejo']!s:5s}"
              f" resellado={x['resellado']!s:5s}")
        print(f"   sha256 antes   {x['sha256_antes']}")
        if "sha256_despues" in x:
            print(f"   sha256 despues {x['sha256_despues']}")
        print(f"   huella antes {x['huella_antes']}")
        print(f"   huella nueva {x['huella_nueva']}")


if __name__ == "__main__":
    main()
