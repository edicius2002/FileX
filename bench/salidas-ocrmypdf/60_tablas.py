# -*- coding: utf-8 -*-
"""Vuelca las tablas de CER de las fases 3 y 4 en texto plano, listas para el informe."""
import json
import os

T = r"D:\Work\research\FileX\bench\salidas-ocrmypdf\texto"
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]


def carga(nom):
    p = os.path.join(T, nom)
    return json.load(open(p, encoding="utf-8"))["res"] if os.path.exists(p) else {}


r1 = {"rapidocr": carga("rapidocr_cuda__cer.json"), "paddleocr": carga("paddleocr_cuda__cer.json")}
r2 = {"rapidocr": carga("rapidocr_cuda_m__cer.json"), "paddleocr": carga("paddleocr_cuda_m__cer.json")}


def cer(res, clave):
    d = res.get(clave)
    return f"{d['cer_pct']:.1f}" if d and "cer_pct" in d else "-"


print("### FASE 3 — cadena OCRmyPDF(preproceso) -> motor.  CER %, rasterizado a 200 ppp")
recetas = ["base", "deskew", "clean", "rotate", "todo", "os300", "os400",
           "deskew_os300", "clean_os300", "ctrlppp200", "ctrlmagickdeskew"]
hdr = f"{'receta':<20}" + "".join(f"{d[:14]:>16}" for d in DOCS)
for mot in ("rapidocr", "paddleocr"):
    print(f"\n-- {mot}")
    print(hdr)
    for r in recetas:
        fila = f"{r:<20}"
        for d in DOCS:
            fila += f"{cer(r1[mot], f'{r}__{d}'):>16}"
        print(fila)

print("\n\n### FASE 4 — matriz ppp x deskew sobre el PDF ORIGINAL.  CER % en escaneado_d3")
print(f"{'ppp':<8}{'rapid sin ds':>14}{'rapid +ds':>12}{'paddle sin ds':>15}{'paddle +ds':>13}")
for ppp in (75, 100, 125, 150, 175, 200, 250, 300):
    print(f"{ppp:<8}"
          f"{cer(r2['rapidocr'], f'm_ppp{ppp}__escaneado_d3'):>14}"
          f"{cer(r2['rapidocr'], f'm_ppp{ppp}_ds__escaneado_d3'):>12}"
          f"{cer(r2['paddleocr'], f'm_ppp{ppp}__escaneado_d3'):>15}"
          f"{cer(r2['paddleocr'], f'm_ppp{ppp}_ds__escaneado_d3'):>13}")
print(f"{'nativo':<8}{cer(r2['rapidocr'], 'nat__escaneado_d3'):>14}{'-':>12}"
      f"{cer(r2['paddleocr'], 'nat__escaneado_d3'):>15}{'-':>13}")

print("\n\n### FASE 4 — misma matriz, resto de variantes (CER %, sin deskew)")
print(f"{'ppp':<8}" + "".join(f"{m+' '+d[:10]:>22}" for m in ("rap", "pad") for d in DOCS[:3]))
for ppp in (75, 100, 150, 200, 300):
    fila = f"{ppp:<8}"
    for m in ("rapidocr", "paddleocr"):
        for d in DOCS[:3]:
            fila += f"{cer(r2[m], f'm_ppp{ppp}__{d}'):>22}"
    print(fila)

print("\n\n### VRAM y carga (de los json)")
for nom in ("rapidocr_cuda__cer.json", "paddleocr_cuda__cer.json",
            "rapidocr_cuda_m__cer.json", "paddleocr_cuda_m__cer.json"):
    p = os.path.join(T, nom)
    if os.path.exists(p):
        j = json.load(open(p, encoding="utf-8"))
        print(f"{nom:<28} carga_frio={j['carga_frio_s']:>7}s  vram_base={j['vram_base_MiB']}  "
              f"vram_pico={j['vram_pico_MiB']}  coste={j['vram_pico_MiB']-j['vram_base_MiB']}")

print("\n\n### Texto recuperado en escaneado_d3 (los casos que importan)")
for f in ("paddleocr_cuda_m__m_ppp100__escaneado_d3.txt",
          "paddleocr_cuda_m__m_ppp200__escaneado_d3.txt",
          "paddleocr_cuda_m__m_ppp200_ds__escaneado_d3.txt",
          "paddleocr_cuda_m__nat__escaneado_d3.txt",
          "rapidocr_cuda_m__m_ppp75_ds__escaneado_d3.txt",
          "rapidocr_cuda_m__m_ppp200__escaneado_d3.txt"):
    p = os.path.join(T, f)
    if os.path.exists(p):
        print(f"  {f:<48} -> {open(p, encoding='utf-8').read().strip()!r}")
