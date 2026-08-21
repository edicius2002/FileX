#!/usr/bin/env bash
# (a) Ver como implementa ocrmypdf el deskew, para saber si "Deskew angle: 0.000"
#     es una deteccion real o un no-op del build de Debian.
# (b) Probar unpaper con sus filtros REALES activados via --unpaper-args, ya que
#     ocrmypdf lo llama por defecto con --no-grayfilter --no-blackfilter --no-deskew.
set -u
B="$HOME/ocrx"; D="$B/diag2"; mkdir -p "$D"

echo "=== (a) implementacion de deskew en ocrmypdf 16.13 ==="
grep -rn "deskew" /usr/lib/python3/dist-packages/ocrmypdf/_pipeline.py | head -20
echo "--- funcion preprocess_deskew ---"
sed -n '/def preprocess_deskew/,/^def /p' /usr/lib/python3/dist-packages/ocrmypdf/_pipeline.py | head -30
echo "--- de donde sale get_deskew ---"
grep -rn "get_deskew\|def deskew\|leptonica\|deskew" /usr/lib/python3/dist-packages/ocrmypdf/builtin_plugins/*.py 2>/dev/null | head -20

echo
echo "=== (b) prueba de control: imagen NITIDA e inclinada 5 grados ==="
# genera un PNG limpio, alto contraste, inclinado 5 grados -> si aqui deskew tambien
# da 0.000, el deskew de este build esta roto; si da ~5, es que d3 es demasiado malo.
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
im = Image.new("L", (1600, 900), 255)
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 46)
except Exception:
    f = f2 = ImageFont.load_default()
d.text((120, 150), "DOCUMENTO ESCANEADO", font=f, fill=0)
d.text((120, 350), "Texto que solo existe como pixeles.", font=f2, fill=0)
d.text((120, 450), "Debe recuperarse con OCR.", font=f2, fill=0)
im.rotate(-5, expand=True, fillcolor=255).save("/tmp/skew5.png")
print("generado /tmp/skew5.png")
PY
img2pdf --output "$D/skew5.pdf" /tmp/skew5.png 2>/dev/null || python3 -c "
from PIL import Image; Image.open('/tmp/skew5.png').convert('RGB').save('$D/skew5.pdf', resolution=200)"
ocrmypdf -l spa --force-ocr --deskew -v 1 --sidecar "$D/skew5_deskew.txt" \
   "$D/skew5.pdf" "$D/skew5_deskew.pdf" 2>&1 | egrep -i 'deskew angle|rotating|input dpi'
echo "texto -> $(tr '\n' ' ' < "$D/skew5_deskew.txt")"

echo
echo "=== (c) unpaper con filtros reales, sobre d3 y d2 ==="
for d in escaneado_d3 escaneado_d2; do
  for tag in agresivo deskewup; do
    case $tag in
      agresivo) UA="--layout none --no-mask-center --no-border-align";;
      deskewup) UA="--layout none --no-mask-center --no-border-align --deskew-scan-range 8 --deskew-scan-step 0.2";;
    esac
    ocrmypdf -l spa --force-ocr --clean-final --unpaper-args "$UA" \
      --sidecar "$D/unp_${tag}__$d.txt" "$B/corpus/$d.pdf" "$D/unp_${tag}__$d.pdf" >"$D/unp_${tag}__$d.log" 2>&1
    rc=$?
    printf '%-12s %-16s rc=%s chars=%s\n' "$tag" "$d" "$rc" \
      "$(tr -d '[:space:]' < "$D/unp_${tag}__$d.txt" 2>/dev/null | wc -c)"
    [ $rc -ne 0 ] && grep -iE 'error|Exception' "$D/unp_${tag}__$d.log" | tail -2
  done
done
cp "$D"/unp_*.pdf /mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/pdf/ 2>/dev/null
echo "listo"
