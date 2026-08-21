# -*- coding: utf-8 -*-
"""Genera las entradas que el corpus no tiene (docx, epub, xlsx, html, md, rtf, odt).
Todas llevan el mismo texto centinela para poder medir supervivencia de la capa de texto.
Sin dependencias externas: los formatos OOXML/EPUB/ODF son ZIP con XML.
"""
import os, zipfile, textwrap

DIR = r"D:\Work\research\FileX\bench\salidas-fidelidad\entradas"
os.makedirs(DIR, exist_ok=True)

CENTINELA = "FILEXSENTINELA7743"
PARRAFO = ("Informe de fidelidad de caminos multisalto. " + CENTINELA +
           " es la marca que debe sobrevivir a la conversion. "
           "El texto seleccionable de un documento es una capa estructurada, no una imagen: "
           "si un salto intermedio rasteriza la pagina, esta frase deja de poder copiarse, "
           "buscarse o leerse con un lector de pantalla, y el fichero resultante ya no sirve "
           "para lo que sirve un documento.")
FILAS = [("codigo", "cantidad", "unidad"),
         ("AX-1", "128", "kg"),
         ("BX-2", "256", "kg"),
         ("CX-3", "512", "kg")]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---------------------------------------------------------------- md / html / rtf / csv / txt
open(os.path.join(DIR, "entrada.md"), "w", encoding="utf-8").write(
    "# Informe FileX\n\n" + PARRAFO + "\n\n" +
    "| " + " | ".join(FILAS[0]) + " |\n|---|---|---|\n" +
    "".join("| " + " | ".join(f) + " |\n" for f in FILAS[1:]) + "\n")

open(os.path.join(DIR, "entrada.html"), "w", encoding="utf-8").write(
    "<!doctype html><html><head><meta charset='utf-8'><title>Informe FileX</title></head><body>"
    "<h1>Informe FileX</h1><p>" + esc(PARRAFO) + "</p><table border='1'>" +
    "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in f) + "</tr>" for f in FILAS) +
    "</table></body></html>")

open(os.path.join(DIR, "entrada.rtf"), "w", encoding="ascii", errors="replace").write(
    r"{\rtf1\ansi\deff0{\fonttbl{\f0 Times New Roman;}}\fs24 " +
    PARRAFO.replace("\\", "").encode("ascii", "replace").decode() +
    r"\par\par " + " | ".join(FILAS[0]) + r"\par " +
    r"\par ".join(" | ".join(f) for f in FILAS[1:]) + "}")

open(os.path.join(DIR, "entrada.csv"), "w", encoding="utf-8", newline="").write(
    ",".join(FILAS[0]) + "\n" + "\n".join(",".join(f) for f in FILAS[1:]) + "\n" +
    "nota,\"" + PARRAFO[:120] + "\",-\n")

open(os.path.join(DIR, "entrada.txt"), "w", encoding="utf-8").write(PARRAFO + "\n")

# ---------------------------------------------------------------- docx
def docx(path):
    cuerpo = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{esc(t)}</w:t></w:r></w:p>'
        for t in ["Informe FileX", PARRAFO])
    filas = "".join(
        "<w:tr>" + "".join(
            '<w:tc><w:tcPr><w:tcW w:w="2000" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:r><w:t>{esc(c)}</w:t></w:r></w:p></w:tc>' for c in f) + "</w:tr>"
        for f in FILAS)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body>' + cuerpo +
           '<w:tbl><w:tblPr><w:tblBorders>'
           '<w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/>'
           '<w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/>'
           '<w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/>'
           '</w:tblBorders></w:tblPr>' + filas + '</w:tbl>'
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
docx(os.path.join(DIR, "entrada.docx"))

# ---------------------------------------------------------------- xlsx
def xlsx(path):
    def celda(col, fila, val):
        return f'<c r="{col}{fila}" t="inlineStr"><is><t>{esc(val)}</t></is></c>'
    filas = ""
    for i, f in enumerate(FILAS, start=1):
        filas += f'<row r="{i}">' + "".join(celda(c, i, v) for c, v in zip("ABC", f)) + "</row>"
    filas += f'<row r="5">{celda("A",5,CENTINELA)}{celda("B",5,PARRAFO[:80])}</row>'
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData>' + filas + '</sheetData></worksheet>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Hoja1" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
xlsx(os.path.join(DIR, "entrada.xlsx"))

# ---------------------------------------------------------------- epub
def epub(path):
    xhtml = ('<?xml version="1.0" encoding="utf-8"?>'
             '<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><head>'
             '<title>Informe FileX</title></head><body><h1>Informe FileX</h1><p>'
             + esc(PARRAFO) + '</p><table border="1">' +
             "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in f) + "</tr>" for f in FILAS) +
             '</table></body></html>')
    opf = ('<?xml version="1.0" encoding="utf-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           '<dc:identifier id="bid">filex-fidelidad-1</dc:identifier>'
           '<dc:title>Informe FileX</dc:title><dc:language>es</dc:language>'
           '<meta property="dcterms:modified">2026-08-20T00:00:00Z</meta></metadata>'
           '<manifest><item id="c1" href="cap1.xhtml" media-type="application/xhtml+xml"/>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '</manifest><spine><itemref idref="c1"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
           'xmlns:epub="http://www.idpf.org/2007/ops"><head><title>nav</title></head><body>'
           '<nav epub:type="toc"><ol><li><a href="cap1.xhtml">Informe FileX</a></li></ol></nav>'
           '</body></html>')
    container = ('<?xml version="1.0"?>'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/cap1.xhtml", xhtml)
        z.writestr("OEBPS/nav.xhtml", nav)
epub(os.path.join(DIR, "entrada.epub"))

# ---------------------------------------------------------------- odt
def odt(path):
    filas = "".join(
        "<table:table-row>" + "".join(
            f'<table:table-cell office:value-type="string"><text:p>{esc(c)}</text:p></table:table-cell>'
            for c in f) + "</table:table-row>" for f in FILAS)
    content = ('<?xml version="1.0" encoding="UTF-8"?>'
      '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" office:version="1.2">'
      '<office:body><office:text><text:h text:outline-level="1">Informe FileX</text:h>'
      f'<text:p>{esc(PARRAFO)}</text:p>'
      '<table:table table:name="T1"><table:table-column table:number-columns-repeated="3"/>'
      + filas + '</table:table></office:text></office:body></office:document-content>')
    manifest = ('<?xml version="1.0" encoding="UTF-8"?>'
      '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
      'manifest:version="1.2">'
      '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>'
      '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
      '</manifest:manifest>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED)
        z.writestr("META-INF/manifest.xml", manifest)
        z.writestr("content.xml", content)
odt(os.path.join(DIR, "entrada.odt"))

for f in sorted(os.listdir(DIR)):
    print(f, os.path.getsize(os.path.join(DIR, f)))
