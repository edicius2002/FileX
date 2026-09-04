#!/usr/bin/env python3
"""Sonda de CAUSA para los fallos de `windows-latest`: sondea el mecanismo,
no lo deduce.

    python bench/salidas-ci-windows-trazas/sonda_causa_windows.py [--json f]

Las trazas de la ejecución 33826410849 apuntan a dos mecanismos, y **una traza
sigue siendo una pista, no un mecanismo** (trampa 36: una explicación plausible
no es un mecanismo; trampa 58: el hecho no implica la causa). Esta sonda los
somete a control positivo y negativo **dentro del propio runner** (trampa 104:
la aptitud de un entorno se mide EN ese entorno):

* **C1 — el nombre corto 8.3.** En `windows-latest`, `tempfile.gettempdir()`
  devuelve `C:\\Users\\RUNNER~1\\...` (lo imprime el propio fallo de
  `test_watcher_n`). `Confinamiento._preparar` normaliza la raíz con
  `normcase(normpath(abspath(r)))` —**sin `realpath`**— mientras `resolver()`
  valida la ruta **RESUELTA** (R7), que sí expande el 8.3. Si el mecanismo es
  ése, la MISMA raíz pasada larga tiene que funcionar: eso es el control
  negativo, y sin él «no entra» no significa nada.
* **C2 — el puntero de Git LFS.** El *checkout* del job va con `lfs: false`, así
  que `corpus/` son punteros de ~130 B que **existen** (trampa 107: un
  `skipUnless(os.path.exists(...))` no protege de esto; hay que mirar el TAMAÑO
  o la cabecera).
* **C3 — Docker.** `ci/windows-hosted-apto.json` da por CONFIRMADO que
  `test_hito7` falla por ausencia de imágenes. Se comprueba aquí, y se contrasta
  con si el módulo menciona siquiera a Docker en su salida.

Todo lo que imprime es MEDIDO en el runner donde corre. No sirve ejecutarla en
la máquina del proyecto salvo como control de que la sonda funciona.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from filex.confinamiento import Confinamiento, _norm  # noqa: E402


def c0_entorno() -> dict:
    t = tempfile.gettempdir()
    return {
        "interprete": sys.version.split()[0],
        "plataforma": sys.platform,
        "cwd": os.getcwd(),
        "raiz_del_repo": str(RAIZ),
        "tempdir": t,
        "tempdir_realpath": os.path.realpath(t),
        "tempdir_es_nombre_corto": _norm(os.path.abspath(t)) != _norm(os.path.realpath(t)),
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
        "USERNAME": os.environ.get("USERNAME", ""),
        "USERPROFILE": os.environ.get("USERPROFILE", ""),
    }


def c1_nombre_corto() -> dict:
    """¿Es el 8.3 lo que cierra la lista blanca? Positivo y negativo."""
    base = tempfile.mkdtemp(prefix="sonda-c1-")
    try:
        dentro = os.path.join(base, "x.txt")
        open(dentro, "w").close()

        corta = Confinamiento([base])
        larga = Confinamiento([os.path.realpath(base)])

        # Control POSITIVO independiente del temporal: una raíz que NO es 8.3,
        # dentro del propio árbol del repositorio. Si ésta tampoco entrase, el
        # roto sería `Confinamiento` y no el nombre corto.
        prop = RAIZ / "bench" / "salidas-ci-windows-trazas"
        prop_f = prop / "sonda_causa_windows.py"
        control = Confinamiento([str(prop)])

        return {
            "raiz_tal_cual": base,
            "raiz_resuelta": os.path.realpath(base),
            "difieren": _norm(os.path.abspath(base)) != _norm(os.path.realpath(base)),
            "puede_leer_con_raiz_TAL_CUAL": corta.puede_leer(dentro),
            # La raíz resuelta con la ruta SIN resolver: no basta, porque el
            # predicado léxico de R1 corre ANTES del `realpath` y compara la
            # ruta tal cual.
            "puede_leer_raiz_RESUELTA_ruta_SIN_resolver": larga.puede_leer(dentro),
            # Las dos resueltas: la tercera celda, que es la que dice si el
            # confinamiento funciona cuando todo llega ya canónico.
            "puede_leer_TODO_RESUELTO": larga.puede_leer(
                os.path.join(os.path.realpath(base), "x.txt")),
            "control_positivo_raiz_larga_del_repo": control.puede_leer(str(prop_f)),
            "veredicto": (
                "el nombre corto 8.3 de la raíz cierra la lista blanca"
                if (_norm(os.path.abspath(base)) != _norm(os.path.realpath(base))
                    and not corta.puede_leer(dentro)
                    and larga.puede_leer(os.path.join(os.path.realpath(base),
                                                      "x.txt")))
                else "el 8.3 NO explica el fallo: mirar otra cosa"),
        }
    finally:
        shutil.rmtree(base, ignore_errors=True)


def c2_lfs() -> dict:
    """¿Son punteros? Por TAMAÑO y CABECERA, no por `exists` (trampa 107)."""
    fuera = {}
    for rel in ("corpus/imagen/tipico.png", "corpus/imagen/tipico.jpg",
                "corpus/audio/trivial.wav", "corpus/audio/habla_jfk.flac",
                "corpus/datos/patologico_bom.csv"):
        p = RAIZ / rel
        f = {"existe": p.exists()}
        if p.exists():
            b = p.read_bytes()[:64]
            f["bytes"] = p.stat().st_size
            f["cabecera"] = b[:40].decode("latin-1")
            f["es_puntero_lfs"] = b.startswith(b"version https://git-lfs")
        fuera[rel] = f
    return fuera


def c3_docker() -> dict:
    exe = shutil.which("docker")
    f = {"docker_en_PATH": exe or "AUSENTE"}
    if exe:
        try:
            r = subprocess.run([exe, "images", "--format", "{{.Repository}}:{{.Tag}}"],
                               capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL)
            f["rc"] = r.returncode
            f["imagenes"] = [x for x in r.stdout.splitlines() if x.strip()]
            f["stderr"] = r.stderr.strip()[:300]
        except Exception as e:                       # noqa: BLE001
            f["error"] = "%s: %s" % (type(e).__name__, e)
    return f


def c4_motores() -> dict:
    from filex.nucleo import FileX
    fx = FileX()
    return {
        "which": {n: (shutil.which(n) or "AUSENTE")
                  for n in ("magick", "gswin64c", "ffmpeg", "ffprobe", "tesseract")},
        "disponibles": [m.nombre for m in fx.disponibles],
        "ausentes": [str(m) for m in fx.ausentes],
    }


def c5_segunda_capa() -> dict:
    """Esquivando C1 —raíz ya resuelta—, ¿convierte de verdad?

    Separa las DOS capas: si aquí sale `ok`, el único obstáculo de
    `test_cerrojo` es el nombre corto; si sale `fallo`, hay una segunda capa
    detrás (el corpus en punteros) y arreglar la primera no pondría el módulo
    en verde. Deducirlo de C1 y C2 juntos sería justo lo que el proyecto
    prohíbe: sondear en ejecución, no deducir.
    """
    from filex.nucleo import FileX
    base = os.path.realpath(tempfile.mkdtemp(prefix="sonda-c5-"))
    try:
        ent = os.path.join(base, "a.png")
        shutil.copyfile(str(RAIZ / "corpus" / "imagen" / "tipico.png"), ent)
        sal = os.path.join(base, "s.webp")
        c = FileX(raices_lectura=[base]).convertir(ent, sal, {})
        return {
            "raiz_resuelta": base,
            "bytes_de_la_entrada": os.path.getsize(ent),
            "ok": bool(getattr(c, "ok", False)),
            "motivo": getattr(c, "motivo", ""),
            "veredicto": getattr(c, "veredicto", ""),
            "salida_existe": os.path.isfile(sal),
        }
    except Exception as e:                            # noqa: BLE001
        return {"error": "%s: %s" % (type(e).__name__, e)}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=pathlib.Path,
                    default=pathlib.Path("sonda-causa-windows.json"))
    args = ap.parse_args()

    datos = {
        "_": ("MEDIDO dentro del runner donde corre. C1 lleva control negativo "
              "(la misma raíz resuelta) y control positivo (una raíz larga del "
              "repositorio): sin ellos, «no entra» no distingue el nombre corto "
              "de un Confinamiento roto."),
        "c0_entorno": c0_entorno(),
        "c1_nombre_corto": c1_nombre_corto(),
        "c2_lfs": c2_lfs(),
        "c3_docker": c3_docker(),
        "c4_motores": c4_motores(),
        "c5_segunda_capa": c5_segunda_capa(),
    }
    print(json.dumps(datos, indent=2, ensure_ascii=False))
    args.json.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print("\nescrito %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
