#!/usr/bin/env bash
# Control limpio: ¿el --deskew de ocrmypdf detecta un angulo cuando la imagen es
# perfecta? Se usa una pagina sintetica nitida inclinada 5 grados a 300 ppp.
set -u
D="$HOME/ocrx/diag2"; mkdir -p "$D"
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
W,H = 2000,1200
im = Image.new("L",(W,H),255); d=ImageDraw.Draw(im)
f  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",80)
f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",52)
d.text((150,200),"DOCUMENTO ESCANEADO",font=f,fill=0)
d.text((150,450),"Texto que solo existe como pixeles.",font=f2,fill=0)
d.text((150,570),"Debe recuperarse con OCR.",font=f2,fill=0)
im.save("/tmp/skew0.png", dpi=(300,300))
im.rotate(-5,expand=True,fillcolor=255).save("/tmp/skew5.png", dpi=(300,300))
for n in ("skew0","skew5"):
    Image.open(f"/tmp/{n}.png").convert("RGB").save(f"/tmp/{n}.pdf",resolution=300)
print("ok")
PY
echo "--- tesseract directo sobre el PNG inclinado (control de cordura) ---"
tesseract /tmp/skew5.png stdout -l spa 2>/dev/null | tr '\n' ' '; echo
echo "--- tesseract --psm 0 (deteccion de orientacion/skew) ---"
tesseract /tmp/skew5.png stdout --psm 0 2>&1 | head -8
for n in skew0 skew5; do
  echo "===== ocrmypdf --deskew sobre $n ====="
  ocrmypdf -l spa --force-ocr --deskew -v 1 --sidecar "$D/$n.txt" \
     "/tmp/$n.pdf" "$D/${n}_ds.pdf" 2>&1 | egrep -i 'deskew|input dpi|Rotating'
  echo "  texto: $(tr '\n' ' ' < "$D/$n.txt")"
done
