# -*- coding: utf-8 -*-
"""C50 / worker10 - ESCRIBIR los 73 tokens que `ffmpeg -muxers` declara escribibles.

Cierra la mitad que la trampa 122 dejo abierta: las 445 entradas `no_materializable`
comparten UN solo string de motivo, y para 73 es falso. De esos 73, **54 nunca se
intentaron**, porque `materializa()` de `_semi_in.py` solo prueba con ffmpeg si el
token esta en `viva_ff_out`, que sale del censo de SALIDA (202 destinos de ConvertX).

Aqui se les da su `rc` por primera vez.

DISENO, con la trampa que lo obliga:
  - t.74: la sonda NO se escribe con la entrada minima. Semilla de video CIF 352x288
    (no 64x48) y audio 48 kHz estereo. El tope va en la DURACION, nunca en el tamano.
  - t.52: tope DENTRO de la orden (`-t`), ademas del timeout del cliente.
  - t.21: un directorio desechable POR CELDA, con `cwd` dentro, listado antes y
    despues: hay motores que escriben fuera del destino.
  - t.75: una celda es buena con `rc == 0` **Y** `bytes > 0`. Solo con el `rc`, la
    version rota pasa.
  - t.72: se registra el `rc` de cada celda y se clasifica por el `stderr` COMPLETO
    (no truncado a 400: es el defecto que C28 tuvo que volver a correr).
  - t.122: un estado negativo registra QUE se intento. Cada celda lleva su `argv`.

Escalera por token, con parada al primer exito:
  N1 `nominal`  - `ffmpeg -i SEM m.<tok>`            (lo que el censo habria hecho)
  N2 `muxer`    - `ffmpeg -i SEM -f <tok> m.<tok>`   (fuerza el muxer: CLAUDE.md sec.5)
La pasada 3 (remedios dirigidos por el `rc`) va en `remedios_ff.py`, despues de ver
los fallos: dos intentos por problema, no un bucle de reintento.

SOLO LEE de bench/salidas-aristas/ y bench/salidas-aristas-reclasificacion/.
ESCRIBE unicamente en este directorio.
"""
import os, sys, json, time, shutil, subprocess, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(AQUI, ".."))
RAIZ = os.path.abspath(os.path.join(BENCH, ".."))
SAL9 = os.path.join(BENCH, "salidas-aristas")
REC9 = os.path.join(BENCH, "salidas-aristas-reclasificacion")
CORPUS = os.path.join(RAIZ, "corpus")
SEMI = os.path.join(AQUI, "semillas")
TRABAJO = os.path.join(AQUI, "trabajo")
DEVNULL = subprocess.DEVNULL
TIMEOUT = 25


def corre(args, cwd, timeout=TIMEOUT):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace", cwd=cwd)
        return p.returncode, (p.stderr or ""), (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:300], (time.perf_counter() - t0) * 1000


def semillas():
    """t.74: la geometria manda. CIF 352x288, no 64x48."""
    os.makedirs(SEMI, exist_ok=True)
    s = {}
    cif = os.path.join(SEMI, "s_cif.mp4")
    if not os.path.exists(cif):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "testsrc=size=352x288:rate=25:duration=1", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=1:sample_rate=48000", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", cif], SEMI, 90)
    s["video_cif"] = cif
    a48 = os.path.join(SEMI, "s48.wav")
    if not os.path.exists(a48):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=1:sample_rate=48000", "-ac", "2", a48], SEMI, 60)
    s["audio48"] = a48
    srt = os.path.join(SEMI, "s.srt")
    if not os.path.exists(srt):
        open(srt, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:02,000\nFILEXSENTINELA C50\n\n"
            "2\n00:00:02,000 --> 00:00:04,000\nsegunda linea de subtitulo\n\n")
    s["subtitulo"] = srt
    s["jpeg_exif"] = os.path.join(CORPUS, "imagen", "tipico.jpg")
    for k, v in s.items():
        assert os.path.exists(v) and os.path.getsize(v) > 0, "semilla %s vacia" % k
    return s


# ------------------------------------------------------------------ universo
def universo():
    """Los 73 `ff_declarado_muxer`, con el subgrupo que explica por que fallaron."""
    cl = json.load(open(os.path.join(REC9, "clasificacion.json"), encoding="utf-8"))
    s1 = json.load(open(os.path.join(SAL9, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(SAL9, "semi_salida2.json"), encoding="utf-8"))
    vivas = {k: (v["vivo"] or s2.get(k, {}).get("vivo", False)) for k, v in s1.items()}
    todos_out = {k.split("|")[1] for k in s1 if k.startswith("ffmpeg|")}
    viva_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("ffmpeg|")}
    toks = sorted(k.split("|", 1)[1] for k, v in cl.items()
                  if v["clase"] == "ff_declarado_muxer")
    grupo = {}
    for t in toks:
        if t in viva_out:
            grupo[t] = "intentado_y_fallo"
        elif t in todos_out:
            grupo[t] = "probado_como_destino_muerto"
        else:
            grupo[t] = "nunca_probado"
    return toks, grupo


def signo(rc):
    """Windows devuelve el `rc` de ffmpeg SIN SIGNO: 4294967274 es -22 (EINVAL).
    Sin esta conversion el clasificador del `rc` no reconoce ni un solo AVERROR."""
    return rc - 2 ** 32 if rc is not None and rc >= 2 ** 31 else rc


def clase_rc(rc, err):
    """t.72: el `rc` no es una pista, es la respuesta. Sobre el stderr COMPLETO."""
    e = err or ""
    rc = signo(rc)
    if rc == 0:
        return "rc0"
    if rc == -9:
        return "timeout"
    if "Encoder not found" in e or "Unknown encoder" in e or "encoder not found" in e:
        return "ENCODER_NOT_FOUND"
    if "experimental" in e and "-strict" in e:
        return "EXPERIMENTAL"
    if "Requested output format" in e and "is not" in e:
        return "MUXER_NO_RECONOCIDO"
    if "Invalid data found" in e:
        return "INVALIDDATA"
    if "Unable to find a suitable output format" in e:
        return "SIN_FORMATO_DEDUCIBLE"
    if rc == -22 or "Invalid argument" in e:
        return "EINVAL"
    return "otro_rc_%s" % rc


def censa(d):
    out = {}
    for r, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(r, f)
            try:
                out[os.path.relpath(p, d)] = os.path.getsize(p)
            except OSError:
                out[os.path.relpath(p, d)] = -1
    return out


def celda(n, tok, sem_nom, sem_ruta, nivel, extra):
    """Una invocacion, en su propio desechable, con censo antes y despues (t.21)."""
    d = os.path.join(TRABAJO, "c%04d" % n)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    antes = censa(d)
    nom = "m." + tok
    dest = os.path.join(d, nom)
    argv = ["ffmpeg", "-nostdin", "-y", "-i", sem_ruta] + extra + [dest]
    rc, err, ms = corre(argv, d)
    rc = signo(rc)
    desp = censa(d)
    b_nom = desp.get(nom, -1)
    b_dir = sum(v for v in desp.values() if v > 0)
    extras = sorted(k for k in desp if k not in antes and k != nom)
    ok = (rc == 0 and b_nom > 0)
    reg = {"n": n, "token": tok, "semilla": sem_nom, "nivel": nivel,
           "argv": argv, "rc": rc, "clase_rc": clase_rc(rc, err),
           "bytes": b_nom, "bytes_dir": b_dir, "ficheros_extra": extras,
           "ms": round(ms, 1), "ok": ok,
           "escribe_directorio": bool(rc == 0 and b_nom <= 0 and b_dir > 0),
           "stderr": err.replace("\r", "").replace("\n", " | ")[-1200:] if not ok else ""}
    if ok:
        guarda = os.path.join(AQUI, "muestras")
        os.makedirs(guarda, exist_ok=True)
        try:
            shutil.copy(dest, os.path.join(guarda, nom))
        except OSError:
            pass
    shutil.rmtree(d, ignore_errors=True)
    return reg


if __name__ == "__main__":
    sem = semillas()
    print("semillas: %s" % {k: os.path.getsize(v) for k, v in sem.items()}, flush=True)
    toks, grupo = universo()
    print("universo: %d tokens  %s" % (len(toks), collections.Counter(grupo.values())), flush=True)

    if os.path.isdir(TRABAJO):
        shutil.rmtree(TRABAJO, ignore_errors=True)
    os.makedirs(TRABAJO)
    raiz_antes = censa(os.path.join(AQUI))

    orden = ["video_cif", "audio48", "subtitulo", "jpeg_exif"]
    res, n, t0 = {}, 0, time.time()
    for i, tok in enumerate(toks):
        celdas, ok = [], False
        for nivel, extra in (("muxer", ["-f", tok]), ("nominal", [])):
            for mod in orden:
                n += 1
                c = celda(n, tok, mod, sem[mod], nivel, list(extra))
                celdas.append(c)
                if c["ok"]:
                    ok = True
                    break
            if ok:
                break
        res[tok] = {"grupo": grupo[tok], "materializado": ok,
                    "por": (celdas[-1]["nivel"] + "<-" + celdas[-1]["semilla"]) if ok else None,
                    "bytes": celdas[-1]["bytes"] if ok else -1,
                    "celdas": celdas}
        print("  %-12s %-28s %s" % (tok, grupo[tok],
              ("ESCRITO %d B por %s" % (celdas[-1]["bytes"], res[tok]["por"])) if ok
              else "no (%s)" % ", ".join(sorted({c["clase_rc"] for c in celdas}))), flush=True)

    raiz_desp = censa(os.path.join(AQUI))
    fugas = sorted(k for k in raiz_desp if k not in raiz_antes
                   and not k.startswith(("muestras", "trabajo", "semillas")))
    print("\nficheros fuera del desechable: %d %s" % (len(fugas), fugas[:10]))

    esc = sum(1 for v in res.values() if v["materializado"])
    print("\nESCRITOS %d de %d  (%.0fs, %d celdas)" % (esc, len(toks), time.time() - t0, n))
    for g in ("nunca_probado", "probado_como_destino_muerto", "intentado_y_fallo"):
        sub = {k: v for k, v in res.items() if v["grupo"] == g}
        e = sum(1 for v in sub.values() if v["materializado"])
        print("  %-30s %2d de %2d escritos" % (g, e, len(sub)))
    json.dump({"celdas_totales": n, "fugas_fuera_del_desechable": fugas, "res": res},
              open(os.path.join(AQUI, "escritura_ff.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
