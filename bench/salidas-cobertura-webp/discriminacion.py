"""Control de discriminacion: rompe UNA linea y comprueba que la suite del
carril se pone ROJA. Una prueba que no se pone roja no cuenta.

Restaura con `git checkout -- filex/verificador.py` (NUNCA `git stash push`,
trampa 119) y comprueba por IDENTIDAD que la mutacion se aplico de verdad.
"""
import hashlib
import sys, json, os, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = RAIZ
SRC = os.path.join(W, "filex", "verificador.py")
PY = sys.executable

MUTACIONES = [
    ("_webp / bandera de alfa de VP8X",
     'd["tiene_alfa"] = bool(cuerpo[0] & 0x10)',
     'd["tiene_alfa"] = bool(cuerpo[0] & 0x20)'),
    ("_webp / recuento de ANMF",
     'd["n_imagenes"] = d.get("n_imagenes", 0) + 1',
     'd["n_imagenes"] = d.get("n_imagenes", 0) + 2'),
    ("_webp / ancho de VP8L",
     'd["ancho"] = (bits & 0x3FFF) + 1',
     'd["ancho"] = (bits & 0x3FFF) + 2'),
    ("_BitsLSB.leer / mascara",
     "        v = self.acc & ((1 << k) - 1)\n        self.acc >>= k",
     "        v = self.acc & ((1 << k) - 2)\n        self.acc >>= k"),
    ("_BitsLSB.ojear / mascara",
     "        self._llenar(k)\n        return self.acc & ((1 << k) - 1)",
     "        self._llenar(k)\n        return self.acc & ((1 << k) - 2)"),
    ("_BitsLSB.saltar",
     "    def saltar(self, k):\n        self.acc >>= k\n        self.n -= k",
     "    def saltar(self, k):\n        self.acc >>= (k + 1)\n        self.n -= k"),
    ("_leer_simbolo / consumo del codigo",
     "    if e[1]:\n        br.saltar(e[1])\n    return e[0]",
     "    if e[1]:\n        br.saltar(e[1] + 1)\n    return e[0]"),
    ("_huff_tabla / codigo canonico",
     "        codigo = (codigo + cuenta[l - 1]) << 1",
     "        codigo = (codigo + cuenta[l - 1]) << 2"),
    ("_huff_tabla / inversion de bits",
     "            rev |= ((c >> (l - 1 - k)) & 1) << k",
     "            rev |= ((c >> k) & 1) << k"),
    ("_leer_codigo_huffman / ncod",
     "    ncod = br.leer(4) + 4",
     "    ncod = br.leer(4) + 5"),
    ("_leer_codigo_huffman / simbolo simple de 8 bits",
     "        primero = br.leer(8) if br.leer(1) else br.leer(1)",
     "        primero = br.leer(7) if br.leer(1) else br.leer(1)"),
    ("_leer_longitudes / desplazamiento de repeticion",
     "            rep = br.leer(_REP_EXTRA[ranura]) + _REP_DESP[ranura]",
     "            rep = br.leer(_REP_EXTRA[ranura]) + _REP_DESP[ranura] + 1"),
    ("_prefijo / bits extra",
     "    return ((2 + (sim & 1)) << extra) + br.leer(extra) + 1",
     "    return ((2 + (sim & 1)) << extra) + br.leer(extra) + 2"),
    ("_distancia_plano / tabla de planos",
     "    d = dy * xsize + dx\n    return d if d >= 1 else 1",
     "    d = dy * xsize + dx + 1\n    return d if d >= 1 else 1"),
    ("_predice / modo 7 (media de L y T)",
     "    if modo == 7:\n        return _med2(L, T)",
     "    if modo == 7:\n        return _med2(L, TL)"),
    ("_predice / modo 12 (clamp completo)",
     "    if modo == 12:\n        return _clamp_full(L, T, TL)",
     "    if modo == 12:\n        return _clamp_full(L, TL, T)"),
    ("_predice / modo 13 (clamp a la mitad)",
     "    if modo == 13:\n        return _clamp_half(L, T, TL)",
     "    if modo == 13:\n        return _clamp_half(L, TL, T)"),
    ("_selecciona (predictor 11)",
     "        d += abs(bv - cv) - abs(av - cv)",
     "        d += abs(bv - cv) + abs(av - cv)"),
    ("_med2 (Average2)",
     "    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a & b)",
     "    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a | b)"),
    ("_vp8l_flujo / orden de canales del pixel",
     "            px[pos] = (aa << 24) | (rr << 16) | (cod << 8) | bb",
     "            px[pos] = (aa << 24) | (bb << 16) | (cod << 8) | rr"),
    ("_vp8l_flujo / cache de color",
     "                cache[((0x1E35A7BD * v) & 0xFFFFFFFF) >> desp_cache] = v",
     "                cache[((0x1E35A7BC * v) & 0xFFFFFFFF) >> desp_cache] = v"),
    ("_vp8l_flujo / referencia hacia atras",
     "            for _ in range(lon):\n                px[pos] = px[pos - d]",
     "            for _ in range(lon):\n                px[pos] = px[pos - d - 1]"),
    ("_vp8l_flujo / guarda de referencia hacia atras",
     "            if d > pos or pos + lon > total:",
     "            if d > pos + 99 or pos + lon > total:"),
    ("_vp8l_flujo / transformacion 0 (predictor), primera fila",
     "                    elif yy == 0:\n                        pred = px[i - 1]",
     "                    elif yy == 0:\n                        pred = px[i - 1] ^ 1"),
    ("_vp8l_flujo / transformacion 0, seleccion de modo",
     "                        modo = (datos[(yy >> bits) * aux + (xx >> bits)] >> 8) & 0xFF",
     "                        modo = (datos[(yy >> bits) * aux + (xx >> bits)] >> 16) & 0xFF"),
    ("_vp8l_flujo / transformacion 1 (color cruzado)",
     "                    nr = (((v >> 16) & 0xFF) + ((g2r * vs) >> 5)) & 0xFF",
     "                    nr = (((v >> 16) & 0xFF) + ((g2r * vs) >> 4)) & 0xFF"),
    ("_vp8l_flujo / transformacion 2 (restar verde)",
     "                         ((((v >> 16) & 0xFF) + verde) & 0xFF) << 16 |",
     "                         ((((v >> 16) & 0xFF) - verde) & 0xFF) << 16 |"),
    ("_vp8l_flujo / transformacion 3, paleta sin empaquetar",
     "                    k = (px[i] >> 8) & 0xFF\n                    px[i] = pal[k] if k < npal else 0",
     "                    k = (px[i] >> 8) & 0xFF\n                    px[i] = pal[k - 1] if k < npal else 0"),
    ("_vp8l_flujo / transformacion 3, paleta empaquetada",
     "                        k = (emp >> ((xx & (ppb - 1)) * bpp_)) & masc",
     "                        k = (emp >> ((xx & (ppb - 1)) * bpp_)) & (masc >> 1)"),
    ("_vp8l_flujo / suma de la paleta",
     "                    pal[i] = _suma_argb(pal[i], pal[i - 1])",
     "                    pal[i] = _suma_argb(pal[i], pal[i - 1] + 1)"),
    ("_vp8l_flujo / imagen meta-Huffman",
     "        meta = [(p >> 8) & 0xFFFF for p in mimg]",
     "        meta = [(p >> 16) & 0xFFFF for p in mimg]"),
    ("_vp8l_flujo / alfabeto con cache de color",
     "            n = _ALFABETOS[j] + ((1 << bits_cache) if (j == 0 and bits_cache) else 0)",
     "            n = _ALFABETOS[j] + ((2 << bits_cache) if (j == 0 and bits_cache) else 0)"),
    ("_vp8l_decodificar / orden RGBA de salida",
     "        salida[4 * i] = (p >> 16) & 0xFF",
     "        salida[4 * i] = (p >> 8) & 0xFF"),
    ("_vp8l_decodificar / plano alfa del trozo ALPH",
     "        return bytearray((p >> 8) & 0xFF for p in px)",
     "        return bytearray((p >> 16) & 0xFF for p in px)"),
    ("_alph_desfiltrar / filtro 1 (horizontal)",
     "            if filtro == 1:\n                pred = izq if izq is not None else arr",
     "            if filtro == 1:\n                pred = arr if arr is not None else izq"),
    ("_alph_desfiltrar / filtro 3 (gradiente)",
     "                    d = izq + arr - out[i - an - 1]",
     "                    d = izq + arr + out[i - an - 1]"),
    ("_alph_desfiltrar / acumulacion",
     "            out[i] = (out[i] + pred) & 255",
     "            out[i] = (out[i] - pred) & 255"),
    ("_alfa_min_webp / atajo alpha_is_used",
     "        if not ((cab5 >> 28) & 1):",
     "        if not ((cab5 >> 27) & 1):"),
    ("_alfa_min_webp / posicion del primer transparente",
     '        r["primer_transparente"] = (k % an, k // an)',
     '        r["primer_transparente"] = (k // an, k % an)'),
    ("_alfa_min_webp / escala del minimo",
     '    mn = min(alfas) if alfas else 255\n    r["tiene_alfa"] = mn < 255',
     '    mn = min(alfas) if alfas else 255\n    mn = max(0, mn - 1)\n    r["tiene_alfa"] = mn < 255'),
]

orig = open(SRC, encoding="utf-8").read()
sha_orig = hashlib.sha256(orig.encode()).hexdigest()
res = []
for nombre, viejo, nuevo in MUTACIONES:
    n = orig.count(viejo)
    if n != 1:
        res.append((nombre, "PATRON x%d" % n, []))
        print("%-58s PATRON APARECE %d VECES" % (nombre, n))
        continue
    mutado = orig.replace(viejo, nuevo)
    # control de IDENTIDAD: el fichero tiene que haber cambiado de verdad
    assert hashlib.sha256(mutado.encode()).hexdigest() != sha_orig
    open(SRC, "w", encoding="utf-8", newline="\n").write(mutado)
    en_disco = hashlib.sha256(open(SRC, encoding="utf-8").read().encode()).hexdigest()
    assert en_disco != sha_orig, "la mutacion no llego al disco"
    p = subprocess.run([PY, "-m", "unittest", "pruebas.test_cob_webp"],
                       cwd=W, capture_output=True, text=True, timeout=300)
    salida = p.stdout + p.stderr
    rojas = sorted(set(l.split(" ")[1] for l in salida.splitlines()
                       if l.startswith(("FAIL: ", "ERROR: "))))
    subprocess.run(["git", "checkout", "--", "filex/verificador.py"], cwd=W,
                   check=True, capture_output=True)
    vuelto = hashlib.sha256(open(SRC, encoding="utf-8").read().encode()).hexdigest()
    assert vuelto == sha_orig, "no se restauro el fichero"
    estado = "ROJA" if p.returncode != 0 else "*** VERDE ***"
    res.append((nombre, estado, rojas))
    print("%-58s %-14s %s" % (nombre, estado, ", ".join(rojas[:3]) or "-"))

json.dump([{"mutacion": n, "estado": e, "pruebas_rojas": r} for n, e, r in res],
          open(os.path.join(os.path.dirname(__file__), "discriminacion.json"), "w",
               encoding="utf-8"), ensure_ascii=False, indent=1)
verdes = [n for n, e, _ in res if e != "ROJA"]
print("\n%d mutaciones, %d ROJAS, %d sin detectar: %s"
      % (len(res), len(res) - len(verdes), len(verdes), verdes))
