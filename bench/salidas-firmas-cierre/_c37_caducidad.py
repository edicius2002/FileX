"""C37 / paso 3 - QUE CADUCA EL ARREGLO, y cuanto de eso PODIA moverse.

Tocar `firma_real` caduca el componente `contrato` de la huella de TODOS los
motores sellados: la suite lo dice sola y por diseno (trampa 32). La pregunta
que la suite no responde es cuantas de esas aristas puede mover de verdad el
cambio. Este script la contesta contando la interseccion entre las aristas
selladas y los cuatro destinos que el cambio toca.

Uso:  python bench/salidas-firmas-cierre/_c37_caducidad.py
"""
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

DIR = os.path.join(RAIZ, "filex", "sondeo")
TOCADOS = set(
    # C37: los marcadores mas alla del 512 y los dos accionables por dato
    "pict pct pcd pcds 3ds rb "
    # C28: las filas de vocabulario que cierran los 17 del «banner del escritor»
    "gpl stl xfig fig chunkedhtml assjson cip hpgl fbxa "
    "revealjs s5 slidy slideous dzslides obj objnomtl pbrt pov ftxt "
    # C30: los cuatro falsos positivos del contenedor
    "vips mpc pcx mat dts dnxhd dnxhr".split())


def huellas_ahora():
    from filex import huella, motores
    out = {}
    for cls in list(motores.MOTORES) + motores._descubrir():
        m = cls()
        out[m.nombre] = huella.de_motor(m)
    return out


def huella_de_head():
    """El verificador de HEAD, para separar 'cambio mio' de 'ya estaba'."""
    tmp = os.path.join(tempfile.gettempdir(), "f2_verificador_head.py")
    r = subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                       capture_output=True, cwd=RAIZ, timeout=60,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        return None
    with open(tmp, "wb") as fh:
        fh.write(r.stdout)
    return tmp


def main():
    from filex import huella
    res = {"motores": {}, "aristas_tocables": [], "n_aristas": 0}
    ahora = huellas_ahora()
    for n in sorted(os.listdir(DIR)):
        if not n.endswith(".json"):
            continue
        motor = n[:-5]
        d = json.load(open(os.path.join(DIR, n), encoding="utf-8"))
        aristas = d.get("aristas") or {}
        guardada = d.get("huella") or {}
        malos = huella.diferencias(guardada, ahora.get(motor, {})) if guardada else []
        tocables = [k for k in aristas
                    if k.split(">")[-1].lower() in TOCADOS
                    or k.split(">")[0].lower() in TOCADOS]
        res["motores"][motor] = {
            "n_aristas": len(aristas),
            "componentes_caducados": malos,
            "aristas_que_el_cambio_puede_mover": tocables,
        }
        res["n_aristas"] += len(aristas)
        res["aristas_tocables"] += [motor + ":" + k for k in tocables]
    res["resumen"] = (
        "%d aristas selladas caducan por el componente `contrato`; de ellas, "
        "%d tienen como origen o destino uno de los cuatro formatos que el "
        "cambio toca (%s)."
        % (res["n_aristas"], len(res["aristas_tocables"]), ", ".join(sorted(TOCADOS))))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
