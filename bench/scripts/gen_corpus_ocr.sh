#!/usr/bin/env bash
# FASE 2-D: genera variantes progresivamente peores del mismo PDF escaneado.
# El texto de referencia es IDENTICO al de corpus/pdf/patologico_escaneado.pdf,
# para poder medir distancia de edicion contra la misma cadena conocida.
set -u
MAGICK="/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick"
OUT="D:/Work/research/FileX/corpus/pdf"
TMP="D:/Work/research/FileX/bench/salidas-fase2/tmp_corpus"
mkdir -p "$TMP" "$OUT"

L1="DOCUMENTO ESCANEADO"
L2="Texto que solo existe como pixeles."
L3="Debe recuperarse con OCR."

# Pagina maestra a 300 ppp (6,47 x 8,96 pulgadas, misma proporcion que el PDF original)
MW=1941; MH=2688
render_master(){  # $1 = destino
  "$MAGICK" -size ${MW}x${MH} xc:white \
    -fill black -font Arial-Bold -pointsize 96 -gravity North -annotate +0+380 "$L1" \
    -fill black -font Arial      -pointsize 62 -gravity North -annotate +0+700 "$L2" \
    -fill black -font Arial      -pointsize 62 -gravity North -annotate +0+840 "$L3" \
    "$1"
}

# variante: nombre ppp angulo ruido nivel_contraste blur jpegq
variante(){
  local nom="$1" ppp="$2" ang="$3" ruido="$4" nivel="$5" blur="$6" jq="$7"
  local w=$(( MW * ppp / 300 ))
  local png="$TMP/${nom}.png" jpg="$TMP/${nom}.jpg" pdf="$OUT/${nom}.pdf"
  local extra=""
  [ "$blur" != "0" ] && extra="-blur 0x${blur}"
  # Orden: girar -> reducir a los ppp objetivo -> desenfocar -> BAJAR contraste
  # (+level comprime el rango: negro->gris oscuro, blanco->gris claro) -> ruido -> JPEG.
  # El ruido va DESPUES del +level para que no lo recorte la compresion de rango.
  "$MAGICK" "$TMP/master.png" \
      -background white -rotate "$ang" \
      -resize ${w}x \
      $extra \
      -colorspace Gray \
      +level "$nivel" \
      -attenuate "$ruido" +noise Gaussian \
      -quality "$jq" "$jpg"
  "$MAGICK" "$jpg" -units PixelsPerInch -density "$ppp" "$pdf"
  local bytes=$(stat -c%s "$pdf")
  local dim=$("$MAGICK" identify -format "%wx%h" "$jpg")
  echo "$nom  ppp=$ppp  angulo=$ang  ruido=$ruido  nivel=$nivel  blur=$blur  jpegq=$jq  px=$dim  bytes=$bytes"
}

render_master "$TMP/master.png"
echo "maestro: $("$MAGICK" identify -format '%wx%h' "$TMP/master.png")"

# d1: 150 ppp, 3 grados, ruido moderado, contraste algo reducido, JPEG 60
variante escaneado_d1 150 3   0.30 "8%,92%"  0   60
# d2: 100 ppp, -5 grados, ruido fuerte, contraste bajo, ligero desenfoque, JPEG 40
variante escaneado_d2 100 -5  0.55 "22%,80%" 0.6 40
# d3: 100 ppp, 5 grados, ruido muy fuerte, contraste muy bajo, desenfoque, JPEG 25
variante escaneado_d3 100 5   0.90 "38%,72%" 1.1 25
