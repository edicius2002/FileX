# -*- coding: utf-8 -*-
"""Sondeo de las 70 aristas `sin_sondear` de ffmpeg.

**Cada arista se EJECUTA de verdad, por `FileX.convertir()`**, para que entren
solos el directorio desechable (R18), el censo del punto 5 —que no se puede
tomar a posteriori— y el contrato de cinco puntos.

Tres decisiones que hay que declarar porque cambian lo que se mide:

1. **Un grafo de UNA arista.** `convertir()` planifica, y el planificador no
   elige siempre la arista directa: una `sin_sondear` cuesta 1,0 + 2,0 = 3,0 y
   dos `real` encadenadas cuestan 1,0 + 1,0 = 2,0, así que pedirle `mp3→opus`
   al grafo entero le hace tomar `mp3→wav→opus` y **la arista que se quería
   sondear no se ejecuta**. Para cada arista se sustituye el grafo por uno que
   contiene solo esa arista. Todo lo demás es el núcleo sin tocar.

2. **El `pedido` declara lo que se está pidiendo.** Cuando el destino es de
   categoría audio, `motores.FFmpeg.orden()` añade `-vn` por su cuenta, pero
   **el núcleo no se lo dice al contrato**, y el contrato entonces exige que la
   salida conserve la pista de vídeo de la entrada (`V7 fallo`). El sondeo pasa
   `solo_audio` —que es la verdad de lo que se pide— y **mide también qué pasa
   sin declararlo**, porque esa diferencia es un hueco del núcleo, no del motor.

3. **Diagnóstico aparte para las que fallan.** Cuando el contrato dicta `fallo`
   el núcleo borra el desechable y la salida se pierde, así que no se puede
   mirar. Para cada `nominal` se repite la orden EXACTA del motor en un
   directorio de diagnóstico y se sondea el resultado con `ffprobe`. Eso es lo
   que separa «el motor no produjo nada» de «el motor produjo un fichero bueno
   que el verificador no sabe leer».

Uso:  python bench/salidas-sondeo-ff/sondear_ff.py <dir_trabajo> [n]
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import formatos, invocacion                # noqa: E402
from filex.grafo import Grafo                         # noqa: E402
from filex.nucleo import FileX                        # noqa: E402

TIMEOUT = 300.0
TOPE_TESTIGO = 20.0


# ------------------------------------------------------------------ testigos
def testigo_proceso():
    """Nivel de carga de la máquina. **Con tope**: un testigo que puede tumbar
    la medición no es un testigo (CLAUDE.md §3)."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-hide_banner", "-version"],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=TOPE_TESTIGO)
    except Exception:
        return TOPE_TESTIGO * 1000.0, True
    return (time.perf_counter() - t0) * 1000.0, False


def testigo_deriva():
    """Deriva monohilo dentro de la tanda."""
    t0 = time.perf_counter()
    x = 0
    for i in range(400000):
        x += i * i
    return (time.perf_counter() - t0) * 1000.0


def sonda_ffprobe(ruta):
    if not os.path.isfile(ruta) or os.path.getsize(ruta) == 0:
        return {"existe": False}
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=index,codec_type,codec_name,sample_rate,channels,width,height",
             "-show_entries", "format=format_name,duration", "-of", "json", ruta],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, errors="replace", timeout=60)
        d = json.loads(r.stdout or "{}")
    except Exception as e:
        return {"existe": True, "error": type(e).__name__}
    st = d.get("streams") or []
    return {
        "existe": True,
        "bytes": os.path.getsize(ruta),
        "n_video": sum(1 for s in st if s.get("codec_type") == "video"),
        "n_audio": sum(1 for s in st if s.get("codec_type") == "audio"),
        "codecs": [s.get("codec_name") for s in st],
        "formato": (d.get("format") or {}).get("format_name"),
        "duracion": (d.get("format") or {}).get("duration"),
    }


def pedido_de(destino):
    """Lo que el que llama está pidiendo de verdad.

    `motores.FFmpeg.orden()` decide `-vn` con este mismo criterio. Declararlo
    en el pedido es decirle al contrato lo que el motor ya sabe.
    """
    fo = formatos.formato(destino)
    if fo is not None and fo.categoria == "audio":
        # `params` además del nivel superior: punto 2 mira los dos, punto 4
        # solo mira `pedido['params']`.
        return {"solo_audio": True, "params": {"solo_audio": True}}
    return {}


# ------------------------------------------------------------------ sondeo
def main():
    trabajo = os.path.abspath(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    salidas = os.path.join(trabajo, "salidas")
    diag = os.path.join(trabajo, "diagnostico")
    for d in (salidas, diag):
        os.makedirs(d, exist_ok=True)

    with open(os.path.join(trabajo, "fuentes", "fuentes.json"), encoding="utf-8") as fh:
        fuentes = json.load(fh)["fuentes"]

    fx = FileX()
    motor = fx.motores["ffmpeg"]
    build = motor.build
    objetivo = [a for a in fx.grafo.aristas
                if a.motor == "ffmpeg" and a.estado == "sin_sondear"]
    print("build:", build, "· aristas:", len(objetivo), flush=True)

    ref = {ext: sonda_ffprobe(p) for ext, p in fuentes.items()}
    resultados = {}
    t_ini = time.time()

    for k, a in enumerate(objetivo):
        clave = f"{a.origen}>{a.destino}"
        fuente = fuentes.get(a.origen)
        pedido = pedido_de(a.destino)
        fx.grafo = Grafo([a])

        med, ultimo = [], None
        for _ in range(n):
            dst = os.path.join(salidas, f"{a.origen}2{a.destino}.{a.destino}")
            if os.path.isfile(dst):
                os.remove(dst)
            tp0, tope0 = testigo_proceso()
            td0 = testigo_deriva()
            conv = fx.convertir(fuente, dst, dict(pedido), timeout=TIMEOUT)
            td1 = testigo_deriva()
            tp1, tope1 = testigo_proceso()
            s = conv.saltos[0] if conv.saltos else None
            if s is not None:
                med.append(s.ms)
            ultimo = (conv, s, dst, [round(tp0, 1), round(tp1, 1)],
                      [round(td0, 1), round(td1, 1)], tope0 or tope1)

        conv, s, dst, tps, tds, topado = ultimo
        rc = s.rc if s else None
        ver = s.veredicto if s else ""
        real = bool(conv.ok) and rc == 0 and ver not in ("fallo", "")
        motivo = ""
        if not real:
            if s is None:
                motivo = conv.motivo or "no se llegó a ejecutar"
            elif rc != 0:
                motivo = f"rc={rc}: {(s.motivo or 'el motor rechazó la conversión')}"
            else:
                motivo = s.motivo or "el contrato dictó fallo"

        # --- ¿cambia el veredicto si NO se declara `solo_audio`? -------------
        sin_declarar = None
        if pedido:
            dst2 = os.path.join(salidas, f"nd_{a.origen}2{a.destino}.{a.destino}")
            c2 = fx.convertir(fuente, dst2, {}, timeout=TIMEOUT)
            s2 = c2.saltos[0] if c2.saltos else None
            sin_declarar = {
                "veredicto": s2.veredicto if s2 else "",
                "rc": s2.rc if s2 else None,
                "reglas": sorted({h.get("regla") for h in (s2.hallazgos if s2 else [])
                                  if h.get("severidad") == "fallo"}),
            }
            if os.path.isfile(dst2):
                os.remove(dst2)

        # --- diagnóstico de las que fallan: ¿qué produjo el motor? -----------
        diagnostico = None
        if not real:
            dd = os.path.join(diag, clave.replace(">", "2"))
            shutil.rmtree(dd, ignore_errors=True)
            os.makedirs(dd, exist_ok=True)
            dsal = os.path.join(dd, f"salida.{a.destino}")
            try:
                argv = motor.orden(fuente, dsal, dict(pedido), timeout=TIMEOUT)
                r = invocacion.ejecutar(argv, timeout=TIMEOUT, cwd=dd)
                diagnostico = {
                    "rc": r.rc, "agotado": r.agotado,
                    "argv": [x.replace(RAIZ, "<raiz>") for x in argv],
                    "ffprobe": sonda_ffprobe(dsal),
                    "en_dir": sorted(os.listdir(dd)),
                    "err_cola": (r.err or "")[-700:],
                }
            except Exception as e:
                diagnostico = {"error": f"{type(e).__name__}: {e}"}

        # --- `-map 0`: ¿sobrevive la segunda pista de audio? -----------------
        map0 = None
        ff_sal = sonda_ffprobe(dst)
        if not ff_sal.get("existe") and diagnostico:
            ff_sal = diagnostico.get("ffprobe", {})
        if ref.get(a.origen, {}).get("n_audio", 0) >= 2 and ff_sal.get("existe"):
            es_audio = bool(pedido)
            esperadas = 1 if es_audio else (0 if a.destino == "gif"
                                            else ref[a.origen]["n_audio"])
            map0 = {"fuente": ref[a.origen]["n_audio"],
                    "salida": ff_sal.get("n_audio"),
                    "esperadas": esperadas,
                    "ok": ff_sal.get("n_audio") == esperadas}

        resultados[clave] = {
            "estado": "real" if real else "nominal",
            "ms": round(statistics.median(med), 1) if med else None,
            "n": len(med),
            "ms_todas": [round(x, 1) for x in med],
            "rc": rc,
            "veredicto": ver,
            "motivo": motivo,
            "pedido": pedido,
            "sin_declarar_solo_audio": sin_declarar,
            "fuente": os.path.basename(fuente) if fuente else None,
            "ffprobe": ff_sal,
            "map0": map0,
            "sobrantes": s.sobrantes if s else {},
            "hallazgos": [{"regla": h.get("regla"), "severidad": h.get("severidad"),
                           "mensaje": h.get("mensaje"), "esperado": h.get("esperado"),
                           "obtenido": h.get("obtenido")}
                          for h in (s.hallazgos if s else [])],
            "cobertura": s.cobertura if s else {},
            "diagnostico": diagnostico,
            "testigos": {"proceso_ms": tps, "deriva_ms": tds, "topado": topado},
        }
        print("%2d/%d %-11s %-8s rc=%-11s ver=%-10s %8sms %s" % (
            k + 1, len(objetivo), clave, resultados[clave]["estado"], rc, ver,
            resultados[clave]["ms"], motivo[:60]), flush=True)

    with open(os.path.join(trabajo, "resultados.json"), "w", encoding="utf-8") as fh:
        json.dump({"build": build, "n": n, "segundos": round(time.time() - t_ini, 1),
                   "fuentes": ref, "aristas": resultados}, fh, indent=1,
                  ensure_ascii=False)
    r = sum(1 for v in resultados.values() if v["estado"] == "real")
    print("REAL %d · NOMINAL %d · %.0f s" % (r, len(resultados) - r,
                                             time.time() - t_ini))


if __name__ == "__main__":
    main()
