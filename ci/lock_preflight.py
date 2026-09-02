#!/usr/bin/env python3
"""C44 -- la respuesta a «¿el job de CI toma el lock, o se niega a correr las
pruebas de GPU si está tomado?»: **se niega**, con una espera CORTA, no la de
producto (`FILEX_GPU_ESPERA`, 900 s por defecto -- pensada para un lote
humano, no para un runner de CI que no puede quedarse una tanda entera
esperando sin decir nada).

Decisión y por qué (MEDIDO en `bench/runner-autoalojado.md` §2):

- Tomar y soltar el lock cuesta **~0,6 ms / ~1,1 ms** (mediana, n=9, lock
  aislado). Reintentar cada 250 ms durante 30 s son ~120 intentos, y el coste
  del reintento es insignificante frente al de esperar.
- Un lote humano puede durar de minutos a **40 minutos entre configuraciones**
  (trampa 100). Un runner de CI que esperase con el `FILEX_GPU_ESPERA=900`
  de producto tendría una probabilidad alta de camparse encima de un lote
  real y quemar 15 minutos de runner sin decir nada útil.
- Recuperar un huérfano REAL (proceso matado con `taskkill /F`, no un PID
  inventado) cuesta **0,171 s** en esta máquina (Windows, vía `tasklist`) --
  rápido comparado con cualquier espera razonable, así que un job de CI que
  SÍ muere a mitad no deja el lock inservible para el siguiente: N29 lo
  arregla también aquí.

Uso, como preflight ANTES de lanzar los módulos de prueba que tocan la GPU:

    python3 ci/lock_preflight.py --etiqueta ci-windows --espera 30
    # rc=0  -> el lock está libre AHORA MISMO (se soltó de inmediato: el
    #          preflight no lo retiene, sólo comprueba que se podría tomar).
    # rc=2  -> ocupado por un dueño VIVO tras la espera: no se corre nada de
    #          GPU en este run, y el step siguiente del workflow debe
    #          saltarse, no fallar.

**Por qué "comprobar y soltar" y no "tomar y sostener durante todo el job":**
sostener el lock durante los ~3-5 minutos que tarda un módulo de prueba
completo bloquearía a un worker humano más tiempo del que hace falta -- el
preflight sólo demuestra que HABÍA hueco al empezar; cada módulo de prueba
que de verdad toca la tarjeta toma su propio lock (con su propio
`FILEX_GPU_ESPERA` corto, ver el workflow) y lo suelta enseguida, igual que
ya hace el resto del proyecto.
"""
from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="ci-preflight")
    ap.add_argument("--espera", type=float, default=30.0,
                    help="segundos que se espera antes de rendirse (defecto 30)")
    args = ap.parse_args()

    l = gpu.Lock(args.etiqueta)
    ok = l.tomar(espera=args.espera, intervalo=0.25)
    if not ok:
        print("OCUPADA: %s no consiguió el lock en %.0f s -- "
              "se omiten los módulos de GPU de este run, no se espera más."
              % (args.etiqueta, args.espera))
        return 2

    l.soltar()
    print("LIBRE: el lock estaba disponible (comprobado y soltado de inmediato; "
          "cada módulo de prueba toma el suyo por su cuenta).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
