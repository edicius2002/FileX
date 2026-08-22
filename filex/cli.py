"""`filex entrada.x salida.y` — la primera de las cuatro superficies.

Las otras tres (MCP, watcher, API HTTP) usan el mismo núcleo. **Ninguna lleva su
propia copia de la validación** (R10): la CLI de kordoc ignora su variable de
confinamiento justamente porque allí la validación vivía en la capa MCP.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, formatos
from .nucleo import FileX


def _fmt_ms(ms: float) -> str:
    return f"{ms:.0f} ms" if ms >= 1 else f"{ms:.2f} ms"


def _inventario(fx: FileX, args) -> int:
    print(f"FileX {__version__}\n")
    print("MOTORES")
    for m in fx.disponibles:
        n = len([a for a in m.aristas if a.estado == "real"])
        print(f"  ✓ {m.nombre:<14} {m.version or '?':<12} "
              f"{len(m.aristas):>4} aristas ({n} medidas)")
    for m in fx.ausentes:
        # «Un motor cuyo binario falta se auto-excluye y la CLI lo INFORMA».
        # Y el mensaje nombra la CAPACIDAD que falta, no el comando que la
        # instala (R14): kordoc responde con su propia CLI, docling con `pip`.
        print(f"  ✗ {m.nombre:<14} no disponible — falta el ejecutable "
              f"'{m.binario}'")
    total = len(fx.grafo.aristas)
    reales = len([a for a in fx.grafo.aristas if a.estado == "real"])
    print(f"\nGRAFO: {total} aristas, {reales} respaldadas por una medición "
          f"reproducible del patrón oro.")
    print("El resto están SIN SONDEAR y se marcan como tal: declarar 'nominal'")
    print("como si fuera 'real' es el fallo central del sector (41,0 % de las")
    print("aristas que los catálogos declaran no existen).")
    return 0


def _destinos(fx: FileX, args) -> int:
    ext = formatos.normaliza(args.formato)
    if not formatos.conocido(ext):
        print(f"formato desconocido: '{ext}'", file=sys.stderr)
        return 2
    d = fx.destinos(ext)
    if not d:
        print(f"desde '{ext}' no se llega a ningún destino con los motores disponibles")
        return 1
    print(f"desde '{ext}' ({len(d)} destinos):")
    print("  " + "  ".join(d))
    return 0


def _plan(fx: FileX, args) -> int:
    dec = fx.planificar(args.entrada, args.salida)
    if not dec.hay:
        print(f"NO HAY CAMINO — {dec.motivo}")
        return 1
    print(f"CAMINO ({dec.camino.saltos} salto(s), coste {dec.camino.coste:.1f}):")
    print("  " + str(dec.camino).replace("\n", "\n  "))
    if dec.aviso:
        print(f"\nAVISO  {dec.aviso}")
    # Solo se enseñan los descartes que ENSEÑAN algo: con 156 aristas salen
    # siete «válido pero más caro» por consulta, y eso es ruido.
    interesantes = [(c, m) for c, m in dec.rechazados
                    if "rasteriza" in m or "pierde" in m]
    mostrar = (interesantes or dec.rechazados)[:4]
    for c, motivo in mostrar:
        print(f"\nDESCARTADO  {' → '.join(c.formatos)}\n  porque {motivo}")
    resto = len(dec.rechazados) - len(mostrar)
    if resto > 0:
        print(f"\n(+{resto} camino(s) válido(s) y más caro(s))")
    return 0


def _convertir(fx: FileX, args) -> int:
    pedido = {}
    if args.params:
        try:
            pedido = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"--params no es JSON válido: {e}", file=sys.stderr)
            return 2

    conv = fx.convertir(args.entrada, args.salida, pedido, timeout=args.timeout)

    if args.json:
        print(json.dumps({
            "entrada": conv.entrada, "salida": conv.salida,
            "ok": conv.ok, "veredicto": conv.veredicto, "motivo": conv.motivo, "aviso": conv.aviso,
            "camino": conv.camino.formatos if conv.camino else [],
            "saltos": [{
                "arista": str(s.arista), "motor": s.arista.motor,
                "rc": s.rc, "ms": round(s.ms, 1), "veredicto": s.veredicto,
                "cobertura": s.cobertura, "hallazgos": s.hallazgos,
                "sobrantes": s.sobrantes,
            } for s in conv.saltos],
            "descartados": [{"camino": c.formatos, "motivo": m}
                            for c, m in conv.rechazados],
        }, ensure_ascii=False, indent=1))
        return 0 if conv.ok else 1

    if not conv.ok:
        print(f"NO CONVERTIDO — {conv.motivo}")
        if conv.camino:
            print(f"  camino intentado: {' → '.join(conv.camino.formatos)}")
        for s in conv.saltos:
            if s.err and args.verboso:
                print(f"  [{s.arista.motor}] {s.err.strip().splitlines()[-1][:200]}")
        return 1

    print(f"{conv.salida}   [{conv.veredicto}]")
    if conv.aviso:
        print(f"  aviso: {conv.aviso}")
    for s in conv.saltos:
        cob = s.cobertura or {}
        cubiertos = sum(1 for k, v in cob.items() if k[0].isdigit() and v)
        print(f"  {s.arista}  rc={s.rc}  {_fmt_ms(s.ms)}  "
              f"contrato {cubiertos}/{len([k for k in cob if k[0].isdigit()])} "
              f"→ {s.veredicto}")
        for h in s.hallazgos:
            print(f"      [{h.get('severidad')}] {h.get('regla')}: {h.get('mensaje')}")
        if s.sobrantes:
            # El punto 5 en lenguaje humano.
            print(f"      punto 5: el motor escribió {len(s.sobrantes)} fichero(s) "
                  f"no declarado(s): {', '.join(sorted(s.sobrantes))}")
    for c, motivo in conv.rechazados:
        if args.verboso or "rasteriza" in motivo or "pierde" in motivo:
            print(f"  descartado {' → '.join(c.formatos)}: {motivo}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="filex",
        description="Conversor universal con verificación obligatoria de la salida.",
        epilog="La verificación no es opcional y no es un paso posterior: el "
               "punto 5 del contrato no se puede comprobar a posteriori.",
    )
    p.add_argument("--version", action="version", version=f"filex {__version__}")
    p.add_argument("--raiz", action="append", default=None,
                   help="raíz permitida (lista blanca). Repetible. Sin ninguna, "
                        "no hay confinamiento y se avisa.")
    sub = p.add_subparsers(dest="orden")

    c = sub.add_parser("convertir", help="convertir un fichero")
    c.add_argument("entrada")
    c.add_argument("salida")
    c.add_argument("--params", help='JSON: {"ancho":800,"calidad":90,"copia":true}')
    c.add_argument("--timeout", type=float, default=120.0)
    c.add_argument("--json", action="store_true")
    c.add_argument("-v", "--verboso", action="store_true")
    c.set_defaults(func=_convertir)

    m = sub.add_parser("motores", help="qué motores hay y qué aristas aportan")
    m.set_defaults(func=_inventario)

    d = sub.add_parser("destinos", help="a qué formatos se llega desde uno dado")
    d.add_argument("formato")
    d.set_defaults(func=_destinos)

    pl = sub.add_parser("plan", help="qué camino se elegiría, y qué se descarta")
    pl.add_argument("entrada")
    pl.add_argument("salida")
    pl.set_defaults(func=_plan)
    return p


def _consola_utf8() -> None:
    """La consola de Windows es cp1252 y revienta con una flecha.

    Un conversor que no puede imprimir el nombre de un formato no es un
    conversor. `errors="replace"` para que, si el terminal no puede pintar el
    glifo, salga un interrogante y no una excepcion.
    """
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv=None) -> int:
    _consola_utf8()
    p = construir_parser()
    args = p.parse_args(argv)

    # `filex a.png b.webp` sin subcomando: la forma corta del hito 1.
    if args.orden is None:
        resto = (argv if argv is not None else sys.argv[1:])
        resto = [a for a in resto if not a.startswith("-")]
        if len(resto) == 2:
            args = p.parse_args(["convertir"] + (argv if argv is not None else sys.argv[1:]))
        else:
            p.print_help()
            return 0

    try:
        fx = FileX(raices_lectura=args.raiz)
    except ValueError as e:
        print(f"no se puede arrancar: {e}", file=sys.stderr)
        return 2
    if args.raiz is None and args.orden == "convertir":
        print("aviso: sin --raiz no hay lista blanca (denegar por defecto está "
              "desactivado)", file=sys.stderr)
    return args.func(fx, args)


if __name__ == "__main__":
    raise SystemExit(main())
