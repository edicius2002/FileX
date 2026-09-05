# -*- coding: utf-8 -*-
"""Control de DISCRIMINACION de `pruebas/test_cob_contrato.py`.

«La cobertura es la unica metrica de este proyecto que se puede subir sin medir
nada»: un `try: f(x) except: pass` sube el porcentaje y no afirma nada. Este
arnes rompe UNA linea de la funcion objetivo y comprueba que las pruebas que
dicen cubrirla se ponen ROJAS. Una prueba que sigue verde con la linea rota no
cuenta.

Tres precauciones, las tres pagadas ya por el proyecto:

  * **Trampa 119** -- para revertir se usa `git checkout -- <fichero>`, NUNCA
    `git stash push <fichero>`: sobre un fichero ya commiteado el stash no hace
    nada, devuelve 0 y deja correr las pruebas contra el codigo NUEVO, con la
    pinta exacta de «mis pruebas pasan con el arreglo y sin el».
  * **Control de IDENTIDAD** -- antes de ejecutar se comprueba que el fichero
    mutado difiere de verdad del original (sha256), y despues, que ha vuelto a
    ser el original. Sin eso, un patron que no casa produce una celda «no
    discrimina» que en realidad es «no mute nada».
  * **Trampa 60** -- se comprueba que la fuente mutada COMPILA. Una mutacion que
    rompe la sintaxis pone rojo el modulo entero y la celda no dice nada sobre
    la linea.

Uso:
    python bench/salidas-cobertura-contrato/mutaciones.py [salida.json]
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OBJETIVO = os.path.join(RAIZ, "filex", "verificador.py")
REL = "filex/verificador.py"
MODULO = "pruebas.test_cob_contrato"

# (etiqueta, funcion, texto exacto a sustituir, sustituto, pruebas que DEBEN
#  ponerse rojas). El texto se busca una sola vez en todo el fichero: si aparece
#  mas de una vez o ninguna, la celda se marca AMBIGUA y no cuenta.
MUTACIONES = [
    # El patron lleva la linea anterior porque `d["n_subtitulo"] += 1` sale
    # TRES veces en el fichero (las otras dos en las sondas en proceso) y una
    # celda ambigua no mide nada.
    ("M01 subtitulos", "sondear_subproceso",
     'elif t == "subtitle":\n                d["n_subtitulo"] += 1',
     'elif t == "subtitle":\n                pass',
     ["test_av_cuenta_la_pista_de_subtitulos"]),
    ("M02 bitrate de pista", "sondear_subproceso",
     'p["bitrate_bps"] = int(s["bit_rate"]) if s.get("bit_rate") else None',
     'p["bitrate_bps"] = None',
     ["test_av_publica_pistas_y_un_solo_proceso",
      "test_con_sonda_REAL_por_subproceso_la_rama_se_alcanza"]),
    ("M03 error de identify", "sondear_subproceso",
     'if rc != 0 or not out.strip():', 'if False:',
     ["test_imagen_rota_devuelve_error_de_identify"]),
    ("M04 ppp en centimetros", "sondear_subproceso",
     'round(res * 2.54) if unidad.startswith("PixelsPerCentimeter")',
     'round(res) if unidad.startswith("PixelsPerCentimeter")',
     ["test_pixels_per_centimeter_se_convierte_a_pulgadas"]),
    ("M05 ppp indefinido", "sondear_subproceso",
     '(round(res) if unidad.startswith("PixelsPerInch") else None)',
     '(round(res) if unidad.startswith("PixelsPerInch") else 72)',
     ["test_unidad_indefinida_no_inventa_un_ppp"]),
    ("M06 paginas de un pdf roto", "sondear_subproceso",
     'd["n_paginas"] = None\n            d["error"]',
     'd["n_paginas"] = 1\n            d["error"]',
     ["test_pdf_roto_no_inventa_un_numero_de_paginas"]),
    ("M07 salida de 0 bytes", "sondear_subproceso",
     'd.update({"categoria": "vacio", "error": "fichero de 0 bytes"})',
     'd.update({"categoria": "vacio"})',
     ["test_fichero_vacio_sale_antes_de_lanzar_un_solo_proceso"]),

    # M08 se parte en dos: cambiar el MENSAJE solo puede delatarlo la prueba
    # que afirma sobre el mensaje; apagar la RAMA tiene que delatarlas a las
    # tres. Meterlas juntas daba un falso «no discrimina» del arnes, no del
    # fichero de pruebas.
    ("M08a redimensionado: mensaje", "punto4_pedido",
     '"REDIMENSIONADO NO SOLICITADO: no se pidio cambiar el tamano"',
     '"redimensionado"',
     ["test_redimensionado_no_solicitado"]),
    ("M08b redimensionado: rama", "punto4_pedido",
     'if (an, al) != (ane, ale):', 'if False:',
     ["test_redimensionado_no_solicitado",
      "test_la_geometria_de_una_pista_de_video_tambien_cuenta",
      "test_el_redimensionado_llega_al_veredicto_por_verificar"]),
    ("M09 dimensiones pedidas", "punto4_pedido",
     'if an != p["ancho"] or (p.get("alto") and al != p["alto"]):',
     'if an != p["ancho"]:',
     ["test_alto_distinto_del_pedido_con_ancho_correcto"]),
    ("M10 aspecto", "punto4_pedido",
     'if abs(ra - rae) > 0.02 and not p.get("recortar") and not pedido_geom:',
     'if False:',
     ["test_la_relacion_de_aspecto_delata_las_barras_anadidas"]),
    ("M11 ppp pedido", "punto4_pedido",
     'if sonda.get("ppp") and abs(sonda["ppp"] - p["dpi"]) > 1:',
     'if sonda.get("ppp") and abs(sonda["ppp"] - p["dpi"]) > 100:',
     ["test_ppp_distinto_del_pedido"]),
    ("M12 pdf a imagen", "punto4_pedido",
     'esperado = round(sonda_ent["ancho_pt"] * p["dpi"] / 72.0)',
     'esperado = round(sonda_ent["ancho_pt"] * p["dpi"] / 144.0)',
     ["test_pdf_a_imagen_la_resolucion_debe_seguir_al_ppp_pedido",
      "test_pdf_a_imagen_con_la_resolucion_correcta_no_avisa"]),
    ("M13 techo de profundidad", "punto4_pedido",
     'elif techo is not None and pr <= techo:', 'elif False:',
     ["test_la_misma_bajada_hacia_jpeg_es_perdida_INEVITABLE"]),
    ("M14 profundidad pedida", "punto4_pedido",
     'if p.get("profundidad_bits") == pr:',
     'if False:',
     ["test_una_profundidad_pedida_explicitamente_no_produce_hallazgo"]),
    ("M15 profundidad inflada", "punto4_pedido",
     'if cods & CODEC_SIN_PERDIDA:', 'if False:',
     ["test_profundidad_INFLADA_en_audio_sin_perdida"]),
    ("M16 alfa no trivial", "punto4_pedido",
     'if alfa_e and alfa_no_trivial and not sonda.get("tiene_alfa"):',
     'if alfa_e and not sonda.get("tiene_alfa"):',
     ["test_un_alfa_TRIVIAL_perdido_no_es_hallazgo"]),
    ("M17 destino sin alfa", "punto4_pedido",
     'if dest in SIN_ALFA:', 'if False:',
     ["test_hacia_jpeg_la_misma_perdida_es_inevitable"]),
    ("M18 solo_audio pista a pista", "punto4_pedido",
     'if clave == "e":\n                        due = x["duracion_s"]',
     'if False:\n                        due = x["duracion_s"]',
     ["test_solo_audio_compara_PISTA_contra_PISTA"]),
    ("M19 tolerancia de duracion", "punto4_pedido",
     'if abs(du - due) > tol:', 'if abs(du - due) > tol * 1000:',
     ["test_la_duracion_cambia_mas_de_la_tolerancia",
      "test_la_tolerancia_de_un_MP3_es_la_de_su_trama_no_10_ms",
      "test_solo_audio_compara_PISTA_contra_PISTA"]),
    ("M20 excepcion de Opus", "punto4_pedido",
     'if "opus" in (cod_o or "").lower() and s_o == 48000:', 'if False:',
     ["test_opus_fuerza_48_kHz_y_eso_es_informativo"]),
    ("M21 canales alterados", "punto4_pedido",
     'if c_o and c_e and c_o != c_e and not p.get("canales"):',
     'if c_o and c_e and c_o != c_e:',
     ["test_los_canales_pedidos_no_son_un_hallazgo"]),
    ("M22 bitrate fallo/aviso", "punto4_pedido",
     'if desv > 0.50:', 'if desv > 5.0:',
     ["test_bitrate_muy_lejos_del_pedido_es_fallo",
      "test_con_sonda_REAL_por_subproceso_la_rama_se_alcanza"]),
    ("M23 bitrate umbral de aviso", "punto4_pedido",
     'elif desv > 0.15:', 'elif desv > 1.5:',
     ["test_bitrate_lejos_del_pedido_es_aviso"]),
    ("M24 caja de pagina", "punto4_pedido",
     'dens = p.get("dpi") or p.get("densidad")', 'dens = p.get("dpi")',
     ["test_la_densidad_tambien_se_lee_de_params_densidad"]),
    ("M25 pagina absurda", "punto4_pedido",
     'elif abs(pt - ane) < 1.0 and ane > 1000:', 'elif False:',
     ["test_un_pixel_un_punto_es_una_pagina_absurda"]),
    ("M26 numero de paginas", "punto4_pedido",
     'if sonda["n_paginas"] != sonda_ent["n_paginas"]:', 'if False:',
     ["test_cambia_el_numero_de_paginas"]),
    ("M27 cero filas", "punto4_pedido",
     'if fo is not None and fe is not None and fo != fe:',
     'if fo and fe and fo != fe:',
     ["test_cero_filas_no_se_confunde_con_ausencia_de_dato"]),
    ("M28 cabecera ordenada", "punto4_pedido",
     'if co and ce and sorted(co) != sorted(ce):', 'if co and ce and co != ce:',
     ["test_una_cabecera_REORDENADA_no_es_una_cabecera_perdida"]),
    ("M29 BOM pedido", "punto4_pedido",
     'if sonda.get("bom_utf8") and not pedido.get("params", {}).get("bom"):',
     'if sonda.get("bom_utf8"):',
     ["test_un_BOM_PEDIDO_no_es_un_aviso"]),
    ("M30 guarda de sonda con error", "punto4_pedido",
     'if sonda.get("error") or sonda_ent.get("error"):',
     'if False:',
     ["test_una_sonda_con_error_no_produce_ni_un_hallazgo"]),

    # --- ramas PARCIALES: las que la suite completa tampoco recorria ---------
    ("M43 tipo de pista no casado", "sondear_subproceso",
     'elif t == "subtitle":\n                d["n_subtitulo"] += 1',
     'else:\n                d["n_subtitulo"] += 1',
     ["test_una_pista_que_no_es_ni_video_ni_audio_ni_subtitulo_se_cuenta_igual"]),
    ("M44 guarda del bitrate de pista", "punto4_pedido",
     'if x["tipo"] == "audio" and x.get("bitrate_bps"):',
     'if x["tipo"] == "audio":',
     ["test_sin_bitrate_en_ninguna_pista_la_regla_se_CALLA"]),
    ("M45 caja de pagina correcta", "punto4_pedido",
     'if abs(pt - esp) > 1.5:', 'if True:',
     ["test_una_caja_de_pagina_CORRECTA_no_produce_hallazgo"]),
    ("M46 paginas ausentes", "punto4_pedido",
     'if sonda.get("n_paginas") and sonda_ent.get("n_paginas"):', 'if True:',
     ["test_sin_numero_de_paginas_en_una_de_las_dos_la_regla_P1_se_calla"]),
    ("M47 pista de audio sin duracion", "punto4_pedido",
     'if x.get("tipo") == "audio" and x.get("duracion_s"):',
     'if x.get("tipo") == "audio":',
     ["test_solo_audio_sin_una_sola_pista_de_audio_con_duracion"]),
    ("M48 el bucle de bitrate no se rompe antes", "punto4_pedido",
     'desv = abs(x["bitrate_bps"] - p["bitrate_bps"]) / p["bitrate_bps"]',
     'desv = 0.0',
     ["test_bitrate_muy_lejos_del_pedido_es_fallo",
      "test_bitrate_lejos_del_pedido_es_aviso",
      "test_una_pista_de_VIDEO_no_secuestra_la_regla_de_bitrate"]),

    ("M31 censar", "main",
     'print(json.dumps(censar(a.censar), ensure_ascii=False, indent=1))',
     'print("{}")',
     ["test_censar_vuelca_el_censo_de_un_directorio",
      "test_censar_admite_varios_directorios"]),
    ("M32 exacto de alfa-min", "main",
     'print(json.dumps(alfa_minimo(a.alfa_min, exacto=a.exacto),',
     'print(json.dumps(alfa_minimo(a.alfa_min, exacto=False),',
     ["test_alfa_min_exacto_recorre_la_imagen_entera"]),
    ("M33 motor de --sondear", "main",
     'print(json.dumps(sondear(a.sondear, a.motor, alfa=a.alfa),',
     'print(json.dumps(sondear(a.sondear, "proceso", alfa=a.alfa),',
     ["test_sondear_con_motor_subproceso"]),
    ("M34 rc del lote", "main",
     'return 0 if all(r["veredicto"] != "fallo" for r in res) else 1',
     'return 0',
     ["test_lote_devuelve_una_lista_y_el_rc_del_peor"]),
    ("M35 fidelidad en lote", "main",
     'if a.fidelidad or a.solo_fidelidad:', 'if False:',
     ["test_lote_con_fidelidad"]),
    ("M36 destino por defecto", "main",
     'pedido = {"destino": a.destino or os.path.splitext(a.salida)[1].lstrip("."),',
     'pedido = {"destino": os.path.splitext(a.salida)[1].lstrip("."),',
     ["test_el_destino_por_defecto_sale_de_la_extension_de_la_salida"]),
    ("M37 params", "main",
     '"params": json.loads(a.params)}', '"params": {}}',
     ["test_params_json_llega_al_punto_4"]),
    ("M38 censo", "main",
     'censo = json.load(open(a.censo, encoding="utf-8")) if a.censo else None',
     'censo = None',
     ["test_el_censo_habilita_el_punto_5"]),
    ("M39 interruptor V2", "main",
     'v2(not a.sin_v2)', 'v2(True)',
     ["test_sin_v2_declara_la_regla_NO_CUBIERTA_en_vez_de_darla_por_buena"]),
    ("M40 rc del contrato", "main",
     'return 0 if "fallo" not in (r["veredicto"], fid.get("veredicto")) else 1',
     'return 0',
     ["test_un_fallo_del_contrato_devuelve_1",
      "test_params_json_llega_al_punto_4",
      "test_el_destino_por_defecto_sale_de_la_extension_de_la_salida"]),
    ("M41 segundo bloque de fidelidad", "main",
     'if r.get("fidelidad"):', 'if False:',
     ["test_fidelidad_imprime_DOS_bloques_con_DOS_veredictos"]),
    ("M42 titulo de solo-fidelidad", "main",
     '"FIDELIDAD (grupo C)" if a.solo_fidelidad else "CONTRATO (grupo A)")',
     '"CONTRATO (grupo A)")',
     ["test_solo_fidelidad_omite_el_contrato"]),
]


def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def restaura():
    subprocess.run(["git", "checkout", "--", REL], cwd=RAIZ, check=True,
                   capture_output=True, timeout=120)


def rojas(salida):
    """Nombres de las pruebas que fallaron o dieron error."""
    return set(re.findall(r"^(?:FAIL|ERROR): (\w+) ", salida, re.M))


def main():
    original = open(OBJETIVO, encoding="utf-8").read()
    sha_orig = sha(original)
    filas = []
    for etiqueta, funcion, viejo, nuevo, esperadas in MUTACIONES:
        fila = {"mutacion": etiqueta, "funcion": funcion,
                "pruebas_esperadas": esperadas}
        if original.count(viejo) != 1:
            fila["veredicto"] = "AMBIGUA"
            fila["nota"] = ("el patron aparece %d veces" % original.count(viejo))
            filas.append(fila)
            print("%-30s AMBIGUA (%d apariciones)" % (etiqueta,
                                                      original.count(viejo)))
            continue
        mutado = original.replace(viejo, nuevo, 1)
        # control de IDENTIDAD: la mutacion tiene que haber cambiado algo
        assert sha(mutado) != sha_orig, etiqueta
        try:
            ast.parse(mutado)          # trampa 60: tiene que COMPILAR
        except SyntaxError as e:
            fila["veredicto"] = "NO COMPILA"
            fila["nota"] = str(e)
            filas.append(fila)
            print("%-30s NO COMPILA" % etiqueta)
            continue
        with open(OBJETIVO, "w", encoding="utf-8", newline="") as fh:
            fh.write(mutado)
        try:
            assert sha(open(OBJETIVO, encoding="utf-8").read()) != sha_orig
            r = subprocess.run([sys.executable, "-m", "unittest", MODULO],
                               cwd=RAIZ, capture_output=True, timeout=900,
                               stdin=subprocess.DEVNULL)
            salida = (r.stdout + r.stderr).decode("utf-8", "replace")
        finally:
            restaura()
            assert sha(open(OBJETIVO, encoding="utf-8").read()) == sha_orig, \
                "NO SE RESTAURO el fichero tras %s" % etiqueta
        caidas = rojas(salida)
        fila["pruebas_rojas"] = sorted(caidas)
        fila["rc"] = r.returncode
        faltan = [x for x in esperadas if x not in caidas]
        fila["esperadas_que_siguen_verdes"] = faltan
        fila["veredicto"] = "DISCRIMINA" if not faltan else "NO DISCRIMINA"
        filas.append(fila)
        print("%-30s %-14s rojas=%d %s"
              % (etiqueta, fila["veredicto"], len(caidas),
                 ("SIGUEN VERDES: %s" % faltan) if faltan else ""))

    # comprobacion final: el arbol tiene que quedar limpio
    est = subprocess.run(["git", "status", "--short", "--", REL], cwd=RAIZ,
                         capture_output=True, timeout=120)
    limpio = not est.stdout.decode("utf-8", "replace").strip()
    print("\nfilex/verificador.py limpio al terminar: %s" % limpio)
    res = {"objetivo": REL, "modulo": MODULO,
           "sha256_12_del_original": sha_orig,
           "arbol_limpio_al_terminar": limpio,
           "n_mutaciones": len(filas),
           "n_discriminan": sum(1 for f in filas
                                if f["veredicto"] == "DISCRIMINA"),
           "filas": filas}
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "discriminacion.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("escrito %s: %d/%d discriminan"
          % (destino, res["n_discriminan"], res["n_mutaciones"]))
    return 0 if res["n_discriminan"] == res["n_mutaciones"] and limpio else 1


if __name__ == "__main__":
    sys.exit(main())
