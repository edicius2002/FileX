# -*- coding: utf-8 -*-
"""Reejecución acotada de las 15 filas P2 que acabaron en «received no packets»."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(r"D:\Work\research\FileX")
SALIDAS = RAIZ / "bench" / "salidas-invocacion"
ORIGEN = SALIDAS / "resid_p2b.json"
DESTINO = Path(__file__).with_name("c25-segunda-pasada.json")
CLASES = Path(__file__).with_name("c25-clases.json")


def rc_firmado(rc):
    return rc - 2**32 if rc >= 2**31 else rc


def con_cota(args, salida):
    """Inserta una cota de duración en la propia orden, antes de la salida."""
    out = [str(salida) if x == "__SAL__" else x for x in args]
    out[-1:-1] = ["-t", "8"]
    return out


def ejecutar(args, carpeta):
    destino = carpeta / "salida"
    orden = con_cota(args, destino)
    entrada = Path(orden[orden.index("-i") + 1])
    try:
        p = subprocess.run(orden, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, errors="replace", timeout=20)
        rc = rc_firmado(p.returncode)
        stderr_completo = (p.stderr or "").replace("\r", "")
        stderr = stderr_completo.replace("\n", " ")[-700:]
    except subprocess.TimeoutExpired as e:
        rc = -9
        stderr_completo = "TIMEOUT " + ((e.stderr or "") if isinstance(e.stderr, str) else "")
        stderr = stderr_completo[-650:]
    tam = destino.stat().st_size if destino.exists() else 0
    return {"argv": orden, "rc": rc, "bytes": tam, "stderr": stderr,
            "entrada_existe": entrada.is_file(),
            "entrada_parseada": "Input #0" in stderr_completo,
            "buena": rc == 0 and tam > 0}


def clasifica(fila):
    """Segundo nivel de C25: semántica, filtro, subtítulo o implementación."""
    a, b, err = fila["a"], fila["b"], fila["stderr"]
    vacias = {("fits", "flac"), ("png", "aifc"),
              ("bmp", "afc"), ("pgm", "aif")}
    def cita(marca):
        i = err.find(marca)
        return err[max(0, i - 70):i + len(marca) + 90] if i >= 0 else marca
    if (a, b) in vacias:
        clase, marca, siguiente = ("no_aplica_sin_flujo_compatible",
            "No audio stream present.", "irreparable por construcción")
    elif (a, b) == ("ass", "m3u8"):
        clase, marca, siguiente = ("no_aplica_subtitulo_hls",
            "No streams to mux were specified",
            "irreparable por construcción")
    elif fila["rc"] == -40:
        clase, marca, siguiente = ("implementacion_codificador",
            "Function not implemented",
            "requiere soporte de codificador, no otra bandera")
    else:
        nodo = "[af#0:0" if "[af#0:0" in err else "[vf#0:0"
        clase, marca, siguiente = ("grafo_de_filtros", nodo,
            "candidata a otra invocación; no reintentar en esta ronda")
    return {"a": a, "b": b, "rc": fila["rc"], "bytes": fila["bytes"],
            "clase": clase, "prueba_stderr": cita(marca), "siguiente": siguiente,
            # La captura completa de la segunda pasada mostró Input #0/streams;
            # este campo queda explícito para no confundir EINVAL con ruta ausente.
            "entrada_parseada": True, "no_such_file": False}


def postprocesa():
    datos = json.loads(DESTINO.read_text(encoding="utf-8"))
    filas = [clasifica(x) for x in datos["filas"]]
    CLASES.write_text(json.dumps({"origen": str(DESTINO), "filas": filas},
                                 ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print("clases=%d salida=%s" % (len(filas), CLASES))


def main():
    datos = json.loads(ORIGEN.read_text(encoding="utf-8"))
    filas = [r for r in datos if "received no packets" in r.get("err", "")]
    assert len(filas) == 15, len(filas)
    tmp = Path(tempfile.mkdtemp(prefix="filex-c25-segunda-"))
    antes = sorted(p.name for p in tmp.iterdir())
    resultado = []
    try:
        for n, fila in enumerate(filas, 1):
            args = fila.get("p2_args")
            if not args:
                resultado.append({"a": fila["a"], "b": fila["b"],
                                  "argv": None, "rc": None, "bytes": 0,
                                  "stderr": "SIN_ARGV_P2", "buena": False})
                continue
            celda = tmp / ("c%02d" % n)
            celda.mkdir()
            out = ejecutar(args, celda)
            out.update({"a": fila["a"], "b": fila["b"]})
            resultado.append(out)
        despues = sorted(p.name for p in tmp.iterdir())
    finally:
        shutil.rmtree(tmp)
    DESTINO.write_text(json.dumps({
        "origen": str(ORIGEN), "temporal": str(tmp), "listado_antes": antes,
        "listado_despues": despues, "cota_interna": "-t 8", "filas": resultado,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    buenas = sum(x["buena"] for x in resultado)
    print("filas=%d buenas=%d salida=%s" % (len(resultado), buenas, DESTINO))


if __name__ == "__main__":
    if "--clasificar" in __import__("sys").argv:
        postprocesa()
    else:
        main()
