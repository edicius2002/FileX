import sys, pypdfium2 as pdfium, os
for doc in sys.argv[1:]:
    r = os.path.join(r"D:\Work\research\FileX\corpus\pdf", doc + ".pdf")
    d = pdfium.PdfDocument(r); p = d[0]; w,h = p.get_size()
    mejor=None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m=obj.get_metadata(); px=m.width*m.height
            if mejor is None or px>mejor[0]*mejor[1]: mejor=(m.width,m.height)
        except Exception: pass
    d.close()
    ppp = round(mejor[0]/(w/72.0),1) if mejor else None
    print(f"{doc:24s} pag={w:.2f}x{h:.2f}pt  img={mejor}  ppp_nativos={ppp}  paginas=?")
