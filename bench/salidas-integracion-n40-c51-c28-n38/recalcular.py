"""Recalcula registro y partición C28 sobre HEAD, sin ejecutar conversiones."""
import collections
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from filex import huella, motores, sondeo


def leer(ruta):
    return json.loads((ROOT / ruta).read_text(encoding="utf-8"))


def escribir(nombre, datos):
    (OUT / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clasificar():
    original = leer("bench/salidas-firmas-cierre/c28_los56.json")
    grupos = {
        "escritura_historica_no_equivale_a_contrato": "302 amv avs2 dnxhd dnxhr dts dv flm gxf h261 h263 mlp mmf rco roq tco thd tun vbn xface",
        "sin_encoder_integrado": "ac4 avs3 bit c2 cavs cvg evc js lbc oma rcv vc1",
        "sin_escritor_integrado": "dzi nia nii pml",
        "metadatos_condicionados": "8bim 8bimtext app1 clip exif icc icm iptc iptctext mask matte thumbnail",
        "sin_bytes_en_sondeo": "8bimwtext app1jpeg iptcwtext",
        "variante_delegado_no_admitida": "jpt",
        "subtitulo_bitmap_sin_adaptador": "sup",
        "paquete_webm_sin_contrato": "chk",
        "directorio_oeb_sin_contrato": "oeb",
        "correo_sin_adaptador_no_fue_ejecutado": "eml",
    }
    filas = [{"token": t, "clase": clase, "conversion_nueva": False}
             for clase, tokens in grupos.items() for t in tokens.split()]
    assert len(filas) == len({r["token"] for r in filas}) == original["n"] == 56
    assert {r["token"] for r in filas} == {r["formato"] for r in original["filas"]}
    escribir("c28-clasificacion.json", dict(n=56, filas=filas,
        reparto=dict(collections.Counter(r["clase"] for r in filas)),
        protocolos_fuera_de_los_56=["rtsp", "sap"],
        fuentes=["bench/fate-y-aristas.md", "bench/fate-completo.md", "bench/aristas-escribibles.md"],
        inviabilidad_universal_demostrada=[],
        nota="Cierre de alcance por clasificación/rechazo, no 56 conversiones nuevas; FATE no proporciona encoders."))


def registro(nombre="registro-head.json"):
    clases = list(motores.MOTORES) + motores._descubrir()
    huellas = {}
    for cls in clases:
        m = cls()
        d = sondeo.cargar(m.nombre)
        if d:
            huellas[m.nombre] = dict(sello=d.get("huella"), actual=huella.de_motor(cls),
                diferencias=huella.diferencias(d.get("huella"), huella.de_motor(cls)),
                aristas_selladas=len(d.get("aristas", {})))
    efectivos = motores.sondear_todos()  # versiones y disponibilidad, NO conversiones
    aristas = [a for m in efectivos if m.disponible for a in m.aristas]
    fuente_auditoria = subprocess.check_output(["git", "show",
        "edicius2002/filex-auditoria-coverage-real:bench/salidas-coverage-conversion-real/coverage.json"], cwd=ROOT)
    anterior = json.loads(fuente_auditoria)
    escribir(nombre, dict(
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        auditoria_sha256=hashlib.sha256(fuente_auditoria).hexdigest(),
        auditoria_historica=anterior["registro"]["estados_auditoria"],
        conversiones_nuevas_en_este_recuento=0, huellas=huellas,
        total_aristas_disponibles=len(aristas),
        estados_runtime=dict(collections.Counter(a.estado for a in aristas)),
        motores=[dict(nombre=m.nombre, disponible=m.disponible, build=m.build,
                       n=len(m.aristas)) for m in efectivos],
        diagnostico=sondeo.diagnostico(),
        nota="Disponibilidad y tablas basales no equivalen a ejecución actual ni fidelidad. No se reselló nada."))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registro", default="registro-head.json")
    args = p.parse_args()
    clasificar()
    registro(args.registro)
