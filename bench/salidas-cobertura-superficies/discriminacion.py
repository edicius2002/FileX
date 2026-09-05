"""Control de discriminacion: rompe UNA linea del modulo objetivo y comprueba
que la prueba que dice cubrirla se pone ROJA.

    python bench/salidas-cobertura-superficies/discriminacion.py [--solo N]

Por que existe: **la cobertura es la unica metrica de este proyecto que se
puede subir sin medir nada**. Un `try: main([...]) except SystemExit: pass`
sube el porcentaje de un `main()` entero y no afirma nada. Una prueba que pasa
con el arreglo y sin el es indistinguible de una que no existe (trampa 116).

Como restaura: `git checkout -- filex/<modulo>.py`. **Nunca `git stash push`**
-- sobre un fichero ya commiteado no hace nada, devuelve 0 y no avisa, y el
arnes acaba comparando el codigo nuevo contra si mismo (trampa 119). Ademas,
antes de correr las pruebas se comprueba que la mutacion ESTA en el disco, y
despues que el arbol vuelve a estar limpio: registrar que la condicion que
dices reproducir se dio (trampa 38).

Salida: `discriminacion.json` con una fila por mutacion.
"""
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDA = os.path.join(RAIZ, "bench", "salidas-cobertura-superficies",
                      "discriminacion.json")
PY = sys.executable
MOD = "pruebas.test_cob_superficies"

#: (modulo, texto_viejo, texto_nuevo, prueba, que_rompe)
MUTACIONES = [
    # ---------------------------------------------------------------- cli.py
    ("cli.py", 'return f"{ms:.0f} ms" if ms >= 1', 'return f"{ms:.2f} ms" if ms >= 1',
     "CliConvertirImpresion.test_fmt_ms_cambia_de_precision_por_debajo_del_milisegundo",
     "_fmt_ms deja de redondear a milisegundo entero"),
    ("cli.py", '+ (m.motivo_ausencia or f"falta el ejecutable \'{m.binario}\'"))',
     '+ "")',
     "CliInventario.test_el_inventario_nombra_la_capacidad_que_falta_no_el_comando",
     "el motor ausente deja de nombrar la capacidad que falta"),
    ("cli.py", 'n = len([a for a in m.aristas if a.estado == "real"])',
     'n = len(m.aristas)',
     "CliInventario.test_el_inventario_nombra_la_capacidad_que_falta_no_el_comando",
     "se cuentan como medidas las aristas sin sondear"),
    ("cli.py", 'print(f"formato desconocido: \'{ext}\'", file=sys.stderr)\n        return 2',
     'print(f"formato desconocido: \'{ext}\'", file=sys.stderr)\n        return 0',
     "CliInventario.test_destinos_desconocido_es_error_de_uso",
     "un formato desconocido deja de ser error de uso"),
    ("cli.py", 'print(f"desde \'{ext}\' no se llega a ningún destino con los motores disponibles")\n        return 1',
     'print(f"desde \'{ext}\' no se llega a ningún destino con los motores disponibles")\n        return 0',
     "CliInventario.test_destinos_conocido_sin_salida_es_fallo_de_negocio",
     "un formato sin destinos deja de ser fallo de negocio"),
    ("cli.py", 'print(f"NO HAY CAMINO — {dec.motivo}")\n        return 1',
     'print(f"NO HAY CAMINO — {dec.motivo}")\n        return 0',
     "CliPlan.test_sin_camino_lo_dice_y_devuelve_1",
     "«no hay camino» deja de devolver 1"),
    ("cli.py", 'mostrar = (interesantes or dec.rechazados)[:4]', 'mostrar = []',
     "CliPlan.test_con_camino_enseña_los_saltos_y_cuenta_los_descartes",
     "el plan deja de enseñar los descartes"),
    ("cli.py", 'if dec.aviso:\n        print(f"\\nAVISO  {dec.aviso}")',
     'if False:\n        print(f"\\nAVISO  {dec.aviso}")',
     "CliPlan.test_el_aviso_de_rasterizacion_se_imprime",
     "el aviso de rasterización se calla"),
    ("cli.py", 'if pedido is not None and not isinstance(pedido, dict):',
     'if False:',
     "CliConvertirParams.test_params_json_valido_pero_no_objeto_tambien_es_2",
     "--params 42 vuelve a llegar al núcleo como int"),
    ("cli.py", 'print(f"--params no es JSON válido: {e}", file=sys.stderr)\n            return 2',
     'print(f"--params no es JSON válido: {e}", file=sys.stderr)\n            return 0',
     "CliConvertirParams.test_params_que_no_es_json_es_error_de_uso",
     "--params roto deja de ser error de uso"),
    ("cli.py", 'if conv.camino and conv.camino.formatos:',
     'if conv.camino:',
     "CliConvertirImpresion.test_un_fallo_sin_formatos_no_imprime_un_camino_vacio",
     "vuelve el «camino intentado: » con nada detrás"),
    ("cli.py", 'if s.err and args.verboso:', 'if s.err:',
     "CliConvertirImpresion.test_un_fallo_enseña_el_camino_intentado_y_el_stderr_solo_con_verboso",
     "el stderr del motor sale sin pedirlo"),
    ("cli.py", 'if s.sobrantes:', 'if False:',
     "CliConvertirImpresion.test_un_exito_enseña_contrato_hallazgos_aviso_y_el_punto_5",
     "el punto 5 deja de nombrar los ficheros no declarados"),
    ("cli.py", 'cubiertos = sum(1 for k, v in cob.items() if k[0].isdigit() and v)',
     'cubiertos = sum(1 for k, v in cob.items() if v)',
     "CliConvertirImpresion.test_un_exito_enseña_contrato_hallazgos_aviso_y_el_punto_5",
     "la cuenta del contrato incluye claves que no son puntos"),
    ("cli.py", 'if args.verboso or "rasteriza" in motivo or "pierde" in motivo:',
     'if args.verboso:',
     "CliConvertirImpresion.test_un_exito_enseña_contrato_hallazgos_aviso_y_el_punto_5",
     "los descartes que enseñan algo dejan de enseñarse"),
    ("cli.py", 'argv = ["convertir", *argv]', 'pass',
     "CliExtremoAExtremo.test_la_forma_corta_sin_subcomando_convierte_y_avisa_de_la_lista_blanca",
     "la forma corta vuelve a estar muerta"),
    ("cli.py", 'if args.raiz is None and args.orden == "convertir":', 'if False:',
     "CliExtremoAExtremo.test_la_forma_corta_sin_subcomando_convierte_y_avisa_de_la_lista_blanca",
     "no se avisa de que no hay lista blanca"),
    ("cli.py", 'print(f"no se puede arrancar: {e}", file=sys.stderr)\n        return 2',
     'print(f"no se puede arrancar: {e}", file=sys.stderr)\n        return 1',
     "CliExtremoAExtremo.test_una_raiz_que_no_confina_impide_arrancar_con_rc_2",
     "no poder arrancar deja de ser error de uso"),
    ("cli.py", 'if args.orden is None:\n        p.print_help()\n        return 0',
     'if args.orden is None:\n        return 0',
     "CliExtremoAExtremo.test_sin_subcomando_y_sin_dos_posicionales_sale_la_ayuda_con_rc_0",
     "sin subcomando no sale la ayuda"),
    # ----------------------------------------------------------- __main__.py
    ("__main__.py", "raise SystemExit(main())", "raise SystemExit(0)",
     "PuntosDeEntrada.test_python_m_filex_sin_argumentos_imprime_la_ayuda_y_sale_con_0",
     "`python -m filex` deja de llamar a la CLI"),
    # ---------------------------------------------------------------- api.py
    ("api.py", "ipaddress.ip_address(h)\n        return True",
     "ipaddress.ip_address(h)\n        return False",
     "ApiTransporteDefensivo.test_es_ip_literal_separa_una_ip_de_un_nombre",
     "una IP literal deja de reconocerse"),
    ("api.py", "except (BrokenPipeError, ConnectionResetError):\n            pass",
     "except (KeyError,):\n            pass",
     "ApiTransporteDefensivo.test_si_el_cliente_cuelga_la_respuesta_no_revienta_la_superficie",
     "un cliente que cuelga propaga la excepción"),
    ("api.py", 'if self.close_connection:\n            self.send_header("Connection", "close")',
     'if False:\n            self.send_header("Connection", "close")',
     "ApiTransporteDefensivo.test_la_respuesta_anuncia_close_cuando_va_a_cerrar",
     "la respuesta no anuncia que va a cerrar"),
    ("api.py", 'n = int(self.headers.get("Content-Length") or 0)\n        except ValueError:\n            n = 0',
     'n = int(self.headers.get("Content-Length") or 0)\n        except KeyError:\n            n = 0',
     "ApiTransporteDefensivo.test_un_rechazo_con_content_length_ilegible_no_intenta_leer_nada",
     "un Content-Length ilegible revienta el rechazo"),
    ("api.py", "except OSError:\n                pass\n        self.close_connection = True",
     "except KeyError:\n                pass\n        self.close_connection = True",
     "ApiTransporteDefensivo.test_un_rechazo_descarta_el_cuerpo_y_aguanta_que_el_socket_muera",
     "un socket muerto revienta el rechazo"),
    ("api.py", "if 0 < n <= MAX_CUERPO:\n            try:\n                self.rfile.read(n)",
     "if False:\n            try:\n                self.rfile.read(n)",
     "ApiCuerpoLeidoDosVeces.test_el_cuerpo_se_lee_dos_veces_y_el_segundo_read_no_tiene_nada",
     "el rechazo deja de descartar el cuerpo (y el defecto desaparece)"),
    ("api.py", 'self._rechazo(400, "longitud no válida")',
     'self._rechazo(200, "longitud no válida")',
     "ApiTransporteDefensivo.test_un_cuerpo_con_content_length_ilegible_es_400_y_no_None_silencioso",
     "un Content-Length ilegible deja de ser 400"),
    ("api.py", "if h == declarado.lower():\n            return True",
     "if h == declarado.lower():\n            return False",
     "ApiHostDeclarado.test_la_direccion_declarada_admite_a_su_cliente_legitimo",
     "el cliente legítimo de un despliegue en red se rechaza"),
    ("api.py", 'return declarado in ("0.0.0.0", "::") and _es_ip_literal(h)',
     "return False",
     "ApiHostDeclarado.test_en_0_0_0_0_se_admite_una_ip_literal_y_se_rechaza_todo_nombre",
     "en 0.0.0.0 no pasa ni una IP literal"),
    ("api.py", "if not declarado or es_loopback(declarado):\n            return False",
     "if not declarado or es_loopback(declarado):\n            return True",
     "ApiHostDeclarado.test_sin_direccion_declarada_solo_pasa_loopback",
     "sin dirección declarada pasa cualquier Host"),
    ("api.py", "if not isinstance(d, dict):", "if False:",
     "ApiCuerpoLeidoDosVeces.test_el_cuerpo_se_lee_dos_veces_y_el_segundo_read_no_tiene_nada",
     "un cuerpo que no es un objeto JSON pasa al servicio"),
    ("api.py", 'return self._rechazo(400, "falta el parámetro \'formato\'")',
     'return self._rechazo(404, "falta el parámetro \'formato\'")',
     "ApiEncaminado.test_destinos_sin_formato_es_400_y_con_formato_responde_la_lista",
     "/destinos sin formato deja de ser 400"),
    ("api.py", 'return self._rechazo(400, "falta el parámetro \'ruta\'")',
     'return self._rechazo(404, "falta el parámetro \'ruta\'")',
     "ApiEncaminado.test_inspeccionar_sin_ruta_es_400_y_una_ruta_ajena_es_404_opaco",
     "/inspeccionar sin ruta deja de ser 400"),
    ("api.py", 'd = self.servicio.despachar("batch", cuerpo)', "d = {}",
     "ApiEncaminado.test_un_lote_sin_entradas_lo_rechaza_el_servicio_no_el_transporte",
     "/lote deja de llamar al servicio"),
    ("api.py", 'd = self.servicio.despachar("job", {"job_id": jid, "accion": "cancelar"})',
     "d = {}",
     "ApiEncaminado.test_cancelar_un_trabajo_que_no_existe_es_404",
     "cancelar deja de llamar al servicio"),
    ("api.py", 'if getattr(self.server, "verboso", False):       # type: ignore[attr-defined]',
     "if False:       # type: ignore[attr-defined]",
     "ApiEncaminado.test_la_bitacora_calla_por_defecto_y_habla_con_verboso",
     "--verboso deja de registrar nada"),
    ("api.py", "self.address_family = socket.AF_INET6", "pass",
     "ApiServidorIPv6.test_una_direccion_con_dos_puntos_cambia_la_familia_de_socket",
     "una dirección IPv6 se intenta abrir como IPv4"),
    ("api.py", 'print(f"filex-api en http://{args.host}:{args.puerto}  "',
     'print(f"filex-api ARRANCADO  "',
     "ApiArranque.test_arranca_sirve_y_se_para_devolviendo_0",
     "el arranque deja de decir dónde escucha"),
    ("api.py", "except KeyboardInterrupt:\n        srv.shutdown()",
     "except SystemExit:\n        srv.shutdown()",
     "ApiArranque.test_un_control_c_para_el_servidor_y_tambien_devuelve_0",
     "Ctrl-C deja de parar el servidor"),
    ("api.py", 'print(f"AVISO: escuchando en {args.host} — cualquiera que llegue a este "',
     'print(f"nota: escuchando en {args.host} — cualquiera que llegue a este "',
     "ApiArranque.test_con_permitir_red_avisa_por_stderr_antes_de_abrir_el_puerto",
     "escuchar en la LAN deja de avisar"),
    ("api.py", 'if args.raiz is None:\n        print("aviso: sin --raiz no hay lista blanca',
     'if False:\n        print("aviso: sin --raiz no hay lista blanca',
     "ApiArranque.test_arranca_sirve_y_se_para_devolviendo_0",
     "la API no avisa de que no hay lista blanca"),
    # ------------------------------------------------------------ watcher.py
    ("watcher.py", "except (OSError, ValueError):\n                self._claves = set()",
     "except KeyError:\n                self._claves = set()",
     "WatcherMemoria.test_una_memoria_corrupta_arranca_vacia_en_vez_de_reventar",
     "una memoria corrupta impide arrancar"),
    ("watcher.py", "def __len__(self) -> int:\n        return len(self._claves)",
     "def __len__(self) -> int:\n        return 0",
     "WatcherMemoria.test_la_memoria_cuenta_lo_que_recuerda_y_persiste",
     "la memoria dice que no recuerda nada"),
    ("watcher.py", "except OSError:\n            pass                                        # el disco no manda aquí",
     "except KeyError:\n            pass                                        # el disco no manda aquí",
     "WatcherMemoria.test_si_el_disco_no_deja_escribir_la_memoria_sigue_en_RAM",
     "un disco que no deja escribir tumba el watcher"),
    ("watcher.py", "if (s.st_dev, s.st_ino) == ident:", "if False:",
     "WatcherTenedoresPosix.test_encuentra_al_que_tiene_el_inodo_y_solo_a_ese",
     "el cerrojo POSIX no reconoce el inodo"),
    ("watcher.py", "if pid == yo:\n            continue", "if False:\n            continue",
     "WatcherTenedoresPosix.test_encuentra_al_que_tiene_el_inodo_y_solo_a_ese",
     "el watcher se cuenta a sí mismo como tenedor"),
    ("watcher.py", "except OSError:\n            return None                    # no es Linux: no hay defensa que dar",
     "except KeyError:\n            return None                    # no es Linux: no hay defensa que dar",
     "WatcherTenedoresPosix.test_sin_proc_no_hay_defensa_que_dar_y_se_dice_None",
     "sin /proc el sondeo revienta en vez de decir «no se pudo»"),
    ("watcher.py", "if not st.st_ino:\n        return None                    # sistema de ficheros sin identidad",
     "if False:\n        return None                    # sistema de ficheros sin identidad",
     "WatcherTenedoresPosix.test_un_sistema_de_ficheros_sin_identidad_no_se_puede_sondear",
     "sin identidad de inodo se responde igualmente"),
    ("watcher.py", "except OSError:\n            # Otro usuario, o el proceso murió entre el `listdir` y esto.",
     "except KeyError:\n            # Otro usuario, o el proceso murió entre el `listdir` y esto.",
     "WatcherTenedoresPosix.test_un_proceso_ajeno_ilegible_no_finge_una_respuesta",
     "un proceso de otro usuario tumba el barrido"),
    ("watcher.py", "return not tenedores", "return True",
     "WatcherTenedoresPosix.test_en_posix_el_cerrojo_pregunta_a_proc_y_no_a_os_replace",
     "en POSIX el cerrojo aprueba un fichero que alguien tiene abierto"),
    ("watcher.py", 'if len(cab) < 12:\n        return "incompleto"',
     'if False:\n        return "incompleto"',
     "WatcherCoherencia.test_un_fichero_mas_corto_que_una_cabecera_esta_incompleto",
     "un fichero sin cabecera pasa por bueno"),
    ("watcher.py", 'except OSError:\n            return "sin_declaracion"\n        return "completo" if cola[4:8] == b"IEND"',
     'except KeyError:\n            return "sin_declaracion"\n        return "completo" if cola[4:8] == b"IEND"',
     "WatcherCoherencia.test_un_png_que_desaparece_entre_la_cabecera_y_la_cola_no_revienta",
     "un PNG que desaparece a mitad revienta la defensa"),
    ("watcher.py", 'except OSError:\n        return "sin_declaracion"           # ya desapareció',
     'except KeyError:\n        return "sin_declaracion"           # ya desapareció',
     "WatcherCoherencia.test_un_fichero_que_ya_no_esta_no_es_asunto_de_esta_defensa",
     "un fichero que ya no está revienta la defensa"),
    ("watcher.py", "if c is None:\n            return", "if False:\n            return",
     "WatcherSondeo.test_sin_confinamiento_no_hay_raices_que_comprobar",
     "sin lista blanca se intenta validar contra nada"),
    ("watcher.py", "c.resolver(self.salida, escritura=True)", "pass",
     "WatcherSondeo.test_con_lista_blanca_se_valida_tambien_el_DIRECTORIO_DE_SALIDA",
     "el directorio de salida deja de validarse"),
    ("watcher.py", "if not self.fx.grafo.camino(ext, self.destino).hay:\n                        continue",
     "if False:\n                        continue",
     "WatcherSondeo.test_el_filtro_de_extension_pregunta_al_grafo_y_salta_lo_que_no_lleva_a_nada",
     "el filtro deja de preguntar al grafo"),
    ("watcher.py", "except OSError:\n                        continue                    # desapareció entre medias",
     "except KeyError:\n                        continue                    # desapareció entre medias",
     "WatcherSondeo.test_un_fichero_que_desaparece_entre_el_listado_y_el_stat_se_salta",
     "un fichero que desaparece tumba el sondeo entero"),
    ("watcher.py", "if self.cerrojo and not _estable_en_disco(h.ruta):", "if False:",
     "WatcherSondeo.test_un_fichero_abierto_por_otro_se_aplaza_y_no_se_descarta",
     "un fichero que otro tiene abierto se convierte igual"),
    ("watcher.py", "for r in self.paso():", "for r in []:",
     "WatcherSondeo.test_el_bucle_para_por_ciclos_y_por_tiempo_y_no_de_otra_forma",
     "el bucle gira sin sondear"),
    ("watcher.py", "except Denegado:\n            # No debería llegar",
     "except KeyError:\n            # No debería llegar",
     "WatcherAtender.test_una_denegacion_del_nucleo_no_sale_por_la_superficie_como_traza",
     "una denegación sale por la superficie como traza"),
    ("watcher.py", 'p5 = "sí" if r.cobertura.get("5_escritura") else "NO"', 'p5 = "NO"',
     "WatcherAtender.test_la_linea_humana_dice_el_punto_5_y_los_ficheros_no_declarados",
     "la línea humana miente sobre el punto 5"),
    ("watcher.py", 'return f"[{r.estado}] {r.entrada} — {r.motivo}"',
     'return f"[{r.estado}] {r.salida} — {r.motivo}"',
     "WatcherAtender.test_la_linea_de_lo_que_no_se_convirtio_nombra_la_ENTRADA",
     "un fallo nombra una salida que no existe"),
    ("watcher.py", "os.makedirs(v.salida, exist_ok=True)", "pass",
     "WatcherArranque.test_un_ciclo_convierte_crea_el_directorio_de_salida_y_lo_cuenta",
     "el watcher no crea su directorio de salida"),
    ("watcher.py", "if args.json:\n            print(json.dumps({", "if False:\n            print(json.dumps({",
     "WatcherArranque.test_con_json_cada_fichero_es_una_linea_de_json_con_su_asa",
     "--json deja de emitir JSON"),
    ("watcher.py", "except Denegado as e:", "except KeyError as e:",
     "WatcherArranque.test_vigilar_fuera_de_la_lista_blanca_es_rc_2_con_el_mensaje_opaco",
     "vigilar fuera de la lista blanca revienta con una traza"),
    ("watcher.py", "except KeyboardInterrupt:\n        pass\n    return 0",
     "except SystemExit:\n        pass\n    return 0",
     "WatcherArranque.test_un_control_c_en_el_bucle_sale_limpio_con_0",
     "Ctrl-C deja de salir limpio"),
    ("watcher.py", "except json.JSONDecodeError as e:", "except KeyError as e:",
     "PuntosDeEntrada.test_python_m_filex_watcher_rechaza_un_params_que_no_es_json",
     "--params roto revienta en vez de devolver 2"),
    ("watcher.py", 'if args.raiz is None:\n        print("aviso: sin --raiz no hay lista blanca',
     'if False:\n        print("aviso: sin --raiz no hay lista blanca',
     "WatcherArranque.test_sin_raiz_avisa_de_que_no_hay_lista_blanca",
     "el watcher no avisa de que no hay lista blanca"),
    ("watcher.py", 'print(f"no se puede arrancar: {e}", file=sys.stderr)\n        return 2',
     'print(f"no se puede arrancar: {e}", file=sys.stderr)\n        return 0',
     "WatcherArranque.test_una_raiz_que_no_confina_impide_arrancar_con_rc_2",
     "no poder arrancar deja de ser rc=2"),
]


def _limpio(modulo):
    r = subprocess.run(["git", "status", "--porcelain", "--", "filex/" + modulo],
                       cwd=RAIZ, capture_output=True, text=True, timeout=120)
    return r.stdout.strip() == ""


def _restaurar(modulo):
    subprocess.run(["git", "checkout", "--", "filex/" + modulo],
                   cwd=RAIZ, capture_output=True, text=True, timeout=120)


def una(i, modulo, viejo, nuevo, prueba, que_rompe):
    ruta = os.path.join(RAIZ, "filex", modulo)
    fuente = open(ruta, encoding="utf-8").read()
    fila = {"n": i, "modulo": modulo, "prueba": prueba, "que_rompe": que_rompe}
    if fuente.count(viejo) != 1:
        fila["veredicto"] = "MUTACION_NO_UNICA"
        fila["ocurrencias"] = fuente.count(viejo)
        return fila
    try:
        with open(ruta, "w", encoding="utf-8", newline="") as fh:
            fh.write(fuente.replace(viejo, nuevo))
        # Trampa 38: registrar que la condicion que se dice reproducir SE DIO.
        fila["mutacion_en_disco"] = (
            open(ruta, encoding="utf-8").read().count(nuevo) >= 1)
        fila["arbol_sucio_durante"] = not _limpio(modulo)
        r = subprocess.run([PY, "-m", "unittest", f"{MOD}.{prueba}"],
                           cwd=RAIZ, capture_output=True, text=True, timeout=900,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        fila["rc_con_mutacion"] = r.returncode
        cola = (r.stderr or "").strip().splitlines()
        fila["ultima_linea"] = cola[-1] if cola else ""
    finally:
        _restaurar(modulo)
    fila["arbol_limpio_despues"] = _limpio(modulo)
    fila["veredicto"] = ("DISCRIMINA" if (fila.get("rc_con_mutacion") not in (0, None)
                                          and fila["mutacion_en_disco"]
                                          and fila["arbol_sucio_durante"]
                                          and fila["arbol_limpio_despues"])
                         else "NO_DISCRIMINA")
    return fila


def main():
    solo = None
    if "--solo" in sys.argv:
        solo = int(sys.argv[sys.argv.index("--solo") + 1])
    filas = []
    for i, m in enumerate(MUTACIONES):
        if solo is not None and i != solo:
            continue
        fila = una(i, *m)
        filas.append(fila)
        print(f"[{i:>3}] {fila['veredicto']:<18} {fila['modulo']:<12} "
              f"{fila['que_rompe']}", flush=True)
    malas = [f for f in filas if f["veredicto"] != "DISCRIMINA"]
    print(f"\n{len(filas) - len(malas)}/{len(filas)} discriminan")
    if solo is None:
        with open(SALIDA, "w", encoding="utf-8") as fh:
            json.dump({"mutaciones": filas,
                       "discriminan": len(filas) - len(malas),
                       "total": len(filas)}, fh, ensure_ascii=False, indent=1)
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
