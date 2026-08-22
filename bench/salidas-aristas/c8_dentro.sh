#!/bin/sh
# E1 / C8 - los 7 casos no_evaluable de referencia.json, dentro del contenedor
# filex-convertx, que trae LibreOffice, Pandoc, Calibre, vips, Inkscape y resvg.
# Sin instalar nada en el host: "lo que falte va en contenedor" (CLAUDE.md sec.2).
IN=/tmp/e1/in
OUT=/tmp/e1/out
mkdir -p "$OUT"
cd "$OUT" || exit 1
TSV=/tmp/e1/resultado.tsv
: > "$TSV"

reg() {
  # reg <id> <caso> <motor> <orden...>  -- ejecuta y anota id, rc, ms, bytes
  id=$1; caso=$2; motor=$3; shift 3
  t0=$(date +%s%N)
  timeout 180 "$@" >"/tmp/e1/log_$id.txt" 2>&1
  rc=$?
  t1=$(date +%s%N)
  ms=$(( (t1 - t0) / 1000000 ))
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$caso" "$motor" "$rc" "$ms" "$*" >> "$TSV"
}

# ---------- caso 1: ofimatica <-> PDF con LibreOffice ----------
reg L01 docx_pdf soffice soffice --headless --convert-to pdf --outdir "$OUT" "$IN/entrada.docx"
reg L02 xlsx_pdf soffice soffice --headless --convert-to pdf --outdir "$OUT/x" "$IN/entrada.xlsx"
reg L03 odt_pdf  soffice soffice --headless --convert-to pdf --outdir "$OUT/o" "$IN/entrada.odt"
reg L04 pdf_docx soffice soffice --headless --infilter=writer_pdf_import --convert-to docx --outdir "$OUT/p" "$IN/tipico_texto.pdf"
reg L05 docx_odt soffice soffice --headless --convert-to odt --outdir "$OUT/d" "$IN/entrada.docx"
reg L06 epub_pdf soffice soffice --headless --convert-to pdf --outdir "$OUT/e" "$IN/entrada.epub"

# ---------- caso 2: markup con Pandoc ----------
reg P01 md_docx   pandoc pandoc "$IN/entrada.md"   -o "$OUT/p_md.docx"
reg P02 docx_md   pandoc pandoc "$IN/entrada.docx" -o "$OUT/p_docx.md"
reg P03 html_docx pandoc pandoc "$IN/entrada.html" -o "$OUT/p_html.docx"
reg P04 md_html   pandoc pandoc "$IN/entrada.md"   -o "$OUT/p_md.html"
reg P05 docx_pdf  pandoc pandoc "$IN/entrada.docx" --pdf-engine=xelatex -o "$OUT/p_docx.pdf"
reg P06 epub_md   pandoc pandoc "$IN/entrada.epub" -o "$OUT/p_epub.md"
reg P07 md_epub   pandoc pandoc "$IN/entrada.md"   -o "$OUT/p_md.epub"
reg P08 docx_rtf  pandoc pandoc "$IN/entrada.docx" -o "$OUT/p_docx.rtf"

# ---------- caso 3: ebooks con Calibre ----------
reg C01 epub_pdf  calibre ebook-convert "$IN/entrada.epub" "$OUT/c_epub.pdf"
reg C02 epub_mobi calibre ebook-convert "$IN/entrada.epub" "$OUT/c_epub.mobi"
reg C03 epub_azw3 calibre ebook-convert "$IN/entrada.epub" "$OUT/c_epub.azw3"
reg C04 azw3_epub calibre ebook-convert "$OUT/c_epub.azw3" "$OUT/c_azw3.epub"
reg C05 mobi_epub calibre ebook-convert "$OUT/c_epub.mobi" "$OUT/c_mobi.epub"
reg C06 epub_docx calibre ebook-convert "$IN/entrada.epub" "$OUT/c_epub.docx"

# ---------- caso 4: SVG con fidelidad tipografica ----------
reg S01 svg_png_inkscape inkscape inkscape --export-type=png --export-filename="$OUT/s_ink.png" "$IN/e1.svg"
reg S02 svg_pdf_inkscape inkscape inkscape --export-type=pdf --export-filename="$OUT/s_ink.pdf" "$IN/e1.svg"
reg S03 svg_png_resvg    resvg    resvg "$IN/e1.svg" "$OUT/s_resvg.png"
reg S04 svg_png_magick   magick   magick "$IN/e1.svg" "$OUT/s_magick.png"
reg S05 svg_pdf_magick   magick   magick "$IN/e1.svg" "$OUT/s_magick.pdf"

# ---------- caso 6: qpdf ----------
reg Q01 qpdf_lineal qpdf qpdf --linearize "$IN/tipico_texto.pdf" "$OUT/q_lin.pdf"
reg Q02 qpdf_cifra  qpdf qpdf --encrypt u o 256 -- "$IN/tipico_texto.pdf" "$OUT/q_enc.pdf"

# ---------- caso 7: vips ----------
reg V01 png_jpg_vips  vips vips copy "$IN/tipico.png" "$OUT/v.jpg"
reg V02 png_webp_vips vips vips copy "$IN/tipico.png" "$OUT/v.webp"
reg V03 png_tif_vips  vips vips copy "$IN/tipico.png" "$OUT/v.tif"

# ---------- texto recuperado de cada PDF producido (comparabilidad) ----------
for f in $(find "$OUT" -name '*.pdf' 2>/dev/null); do
  gs -q -dNOPAUSE -dBATCH -sDEVICE=txtwrite -o "$f.txt" "$f" 2>/dev/null
done
for f in $(find "$OUT" -type f 2>/dev/null); do
  printf 'FICH\t%s\t%s\n' "$f" "$(stat -c %s "$f")" >> "$TSV"
done
echo FIN
