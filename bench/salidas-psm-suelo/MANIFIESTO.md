# MANIFIESTO — bench/salidas-psm-suelo/img/

Los **48 rásteres PNG** de este directorio (5,9 MB) **no se versionan**: son regenerables.
Son los mismos cuatro documentos y el mismo barrido de ppp que
`bench/salidas-suelo-ppp/MANIFIESTO.md` (nativo de cada documento + la rejilla fina
100–150 cada 5), para que las filas de `bench/psm-suelo-ppp.md` sean comparables celda a
celda con las 336 de `bench/suelo-ppp.md`. Se generan una sola vez y las comparten `tess3`
y `tess11` (mismo `img/`, mismo `-density`).

**Orden que los reproduce:** desde Git Bash de Windows, con `USERPROFILE`/`HOME` locales
(nunca heredados de WSL — ver `bench/psm-suelo-ppp.md` §0),

```
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-psm-suelo/b21b22_tess.py tess3 \
  --ppp 100,105,110,115,120,125,130,135,140,145,150 --reps 9
"/d/Work/research/FileX/.venv-ai/Scripts/python.exe" \
  bench/salidas-psm-suelo/b21b22_tess.py tess11 \
  --ppp 100,105,110,115,120,125,130,135,140,145,150 --reps 9
```

Rasterizador: `magick -density N …[0] -units PixelsPerInch -density N -colorspace sRGB
-alpha remove -background white -flatten dst.png` (`bench/salidas-psm-suelo/b21b22_tess.py`,
función `raster`) — el pHYs declarado es el verdadero, mismo criterio que la trampa 8/29 de
`CLAUDE.md`.

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `ppp060__escaneado_d5b.png` | 71068 | `c1b99d3a793c6fe549326c4e38166514b85b976dbf2006eb4f273f3b03750b07` |
| `ppp072__escaneado_d5.png` | 97718 | `41ed6e69020c96337082ef7bd28a8280a38281ac8f78cdec33a910361c577ffa` |
| `ppp080__escaneado_d5c.png` | 116022 | `ea97d624b32031beaf59c55e6aaee9a2e29ab20337bc585312fed4989f83c8a9` |
| `ppp090__escaneado_d5a.png` | 124796 | `c73eba1fb984d66e3414f0873ad0c68326b51f3509cf5bdb1ab39e92482462c6` |
| `ppp100__escaneado_d5.png` | 115276 | `e27eef6373fc5d8405dfdf0c730817dbe974ca34f7e6ba85f1cd9b0297349ada` |
| `ppp100__escaneado_d5a.png` | 135472 | `12ffebf0030be45158557f26c592b7130aea4a9b2fb0cd6830b445a3978d6985` |
| `ppp100__escaneado_d5b.png` | 90839 | `85969725c4b5c394d73cc4658df23f262e5597aeca8f7d8321bae3d729a4900a` |
| `ppp100__escaneado_d5c.png` | 128239 | `62cd1774a3a9c5f7e5a942d02d641ceee76898e60b57dfc4093aec1b075e6537` |
| `ppp105__escaneado_d5.png` | 117230 | `b45b4737274587346b0b272c85c25d00a475d6a14e41a6584c5703075bef2d17` |
| `ppp105__escaneado_d5a.png` | 138658 | `ceea11790a53321d1ddf9af1b84d9da045f793a7eb7c9d04500eb68045943f5c` |
| `ppp105__escaneado_d5b.png` | 90437 | `37b83fdb053d6f7b405b9a1a12c75f1b8f9fc22320c0dbd39a5c94d7059e8aeb` |
| `ppp105__escaneado_d5c.png` | 133465 | `570751bc91a068367e042d893609f15f57f2296ca186ea42d36647dc7d0bb957` |
| `ppp110__escaneado_d5.png` | 120482 | `98592106253600ce43f4e6ad8a4ecafb1431c6e47a21e0da03906c0054956c35` |
| `ppp110__escaneado_d5a.png` | 142603 | `8f18c09760979b66008ef43c5c96a6fb699109cf862537af13bc594c8135e89b` |
| `ppp110__escaneado_d5b.png` | 93839 | `9b34db48c025c12ae2359bd0870f55fe57d5691f5dbb00dbda7239c3cec79b54` |
| `ppp110__escaneado_d5c.png` | 134045 | `6db81382323ac87a821767b7153f7f9bb774bc40cd376634fa11c8210c246c02` |
| `ppp115__escaneado_d5.png` | 123535 | `4a065cbb8d8f815f1f45c75b3c36cd271b73bd9102573bf97d3da3f6a69d84eb` |
| `ppp115__escaneado_d5a.png` | 144903 | `776161b290128e929f7759227ed20666f19c46238a64d97618a756f93f2c9413` |
| `ppp115__escaneado_d5b.png` | 94445 | `dea0027b978bb65565fe42c7355f1312655b82fd6083bc4783aca73f5c6cfc67` |
| `ppp115__escaneado_d5c.png` | 138782 | `2b09fb5117c1b3e96abb8d8e41b2b6efc2fd362ab8ee25bc1d81bcbb99dfde87` |
| `ppp120__escaneado_d5.png` | 124857 | `2d6d21675b4d426466fe4291be74942b91cf18bdeec97bfc7c16744a2e70caa8` |
| `ppp120__escaneado_d5a.png` | 146489 | `af0cebab3eac2fa68809ab67947715d1243eadca29cef750892a9bf5503f9d5c` |
| `ppp120__escaneado_d5b.png` | 93010 | `32b15232a6b6e2f54f94a413bcb123784e12afaf2671072c21f0cec4ec1c8d0a` |
| `ppp120__escaneado_d5c.png` | 138152 | `c576f3a2e9e985d8b4e1c4403d1b0349b9a1e228a09b8e981cf0d90cd3ce97b4` |
| `ppp125__escaneado_d5.png` | 128342 | `052880734828323b14f51fc78b26bb27a98d6a5284be678f9924f56f39aaf519` |
| `ppp125__escaneado_d5a.png` | 148747 | `4861d945f7f4050123e93c00f9efcee2e2ba1eca8daf48e7117edc4e33d9d46b` |
| `ppp125__escaneado_d5b.png` | 98104 | `05c6ae88fb6ccaab96b840595abae896f9a8fe15cc5783c8fb507e6d602fa454` |
| `ppp125__escaneado_d5c.png` | 143601 | `c7e4c4e8c1218215efc1bb24d4d2ae734833990239676e7fb5dc252154e7e89a` |
| `ppp130__escaneado_d5.png` | 129960 | `2181126ab467ec3aaa636459e8767a7ddde99140987bd562b0096fbff6f52b70` |
| `ppp130__escaneado_d5a.png` | 150242 | `a6c892819f888d4cfae66945120ce973277b2d268843a57c5b042d2b440a3679` |
| `ppp130__escaneado_d5b.png` | 101068 | `44b6b23d2f1526dc80b68172a6701bcdc55f20b0f168a51ef14cba3bbcccf8ce` |
| `ppp130__escaneado_d5c.png` | 143313 | `485972405b71452aec719a0f6744806cd38cdb7c1ba756bbf54b5de5c1a8bbba` |
| `ppp135__escaneado_d5.png` | 128234 | `ae1d6a7b3459e2d95b07d8b48d80e557c01aa16edbad8e2236a7ac4b9cc46a56` |
| `ppp135__escaneado_d5a.png` | 148928 | `a3efe5e1d13f5e22b76b4901c0e8e657da6356f32a51544796a0271a503c651e` |
| `ppp135__escaneado_d5b.png` | 100513 | `9204a7d575c74cd8a7d89ea197713b3183a546aa9252016001d77692b5edb733` |
| `ppp135__escaneado_d5c.png` | 148071 | `0018c46688de5695fdaee85e256a028fe9c355bc751d9fa8372a48778b6a4652` |
| `ppp140__escaneado_d5.png` | 130757 | `1e8888382d9ea595a8b1d546fb97dceb0bdec5f2329d38b7d89faaa5282060c7` |
| `ppp140__escaneado_d5a.png` | 156235 | `1baf0b11a1aa8b1e198bd148e5ab99b3f6766cdb88d5e0f4af7dbebf15ef0148` |
| `ppp140__escaneado_d5b.png` | 104169 | `96a42bf210409da275d95e1bf0a73b04a4a3074f7e72ffdd354cbee2367a9e6a` |
| `ppp140__escaneado_d5c.png` | 146913 | `ba98116f461587a0b9e1f52f30ab1f0a24b63fc4b38e7a78066cd075203f6bde` |
| `ppp145__escaneado_d5.png` | 130231 | `f13d10000141a59176d2a285d861e1d2ae06f9afe2f9a7d8a7675cfc45ad962f` |
| `ppp145__escaneado_d5a.png` | 158529 | `80f4700457abb2ef8802e5314f166dcaccaadbbf9b9b765a3da5d9d375e5195c` |
| `ppp145__escaneado_d5b.png` | 105820 | `f411a58df3ce104c3dd20f7b147f938dea2977e00b86965d10d8f5bfabc9124e` |
| `ppp145__escaneado_d5c.png` | 151610 | `bdc36d5b3adb75c84927970b9df8992b3c5f405dd227a3f75dd787455a41058a` |
| `ppp150__escaneado_d5.png` | 135557 | `504ce85698e5634e3f8d7f1651b36d55bb422a515a02d29b99dd6c04e1c5f000` |
| `ppp150__escaneado_d5a.png` | 160006 | `64db62426b22ff92a1c9b24931b9a65cb56258530c512f41a40811fb654002ec` |
| `ppp150__escaneado_d5b.png` | 104367 | `480c8264ca0bc914c8bf37b10063a63ca0445754d0e7d0ba1b4602034877ea86` |
| `ppp150__escaneado_d5c.png` | 149674 | `549f9ffe75886336e77629414f52c9d89049bbd635e441abfafd071acc98773a` |
