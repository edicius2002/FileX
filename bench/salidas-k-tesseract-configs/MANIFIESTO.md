# MANIFIESTO — `bench/salidas-k-tesseract-configs/`

Los **58 rásteres PNG** de `img/` (≈32 MB) **no se versionan**: son regenerables.
Dos son de un control de colorspace (`ctrl_*`), el resto de la rejilla 2×2.

- `vphys####__<doc>.png` (28): corpus VIEJO (`escaneado_d3`, `escaneado_d4`,
  `escaneado_d4c`, `patologico_escaneado`), pHYs **DECLARADO**
  (`-units PixelsPerInch -density N -colorspace Gray`) — la celda que faltaba
  del 2×2. Misma receta Gray que ya usaba `preparar_km.py` (sin pHYs), con
  **solo** `-units PixelsPerInch` añadido, para aislar el efecto de pHYs sin
  cambiar el colorspace.
- `d5nophys####__<doc>.png` (28): corpus D5 (`escaneado_d5`, `escaneado_d5a`,
  `escaneado_d5b`, `escaneado_d5c`), pHYs **SIN declarar**
  (`-colorspace sRGB`, sin `-units`) — la otra celda que faltaba. Misma receta
  sRGB que ya usaba `b23_k_d5.py:raster_declarado`, con **solo** el
  `-units PixelsPerInch` quitado.
- `ctrl_gray_units__escaneado_d5a.png`, `ctrl_srgb_nounits__escaneado_d4c.png`
  (2): control de colorspace — confirman que Gray vs sRGB no mueve el CER de
  Tesseract (ver informe §2.2).

**Orden que los reproduce** (desde el worktree, con el intérprete de
`.venv-mcp-filex`, que basta: no hay imports de GPU):

```
python bench/salidas-k-tesseract-configs/b25_phys_corpus.py viejo-phys --reps 3
python bench/salidas-k-tesseract-configs/b25_phys_corpus.py d5-nophys --reps 3
```

**Los `.txt` de `texto/`** (112 ficheros, texto plano, unos KB cada uno) **sí**
se versionan: son baratos y son la trazabilidad de cada celda.

**`ocr_eval_d4.py` y `d4_texto.py` son copias byte a byte** de
`bench/salidas-k-motor/` (verificado con `sha256` antes de usarlos) — el mismo
evaluador que produjo las cifras de `d4`/`d4c`/`d3`/`patológico` ya publicadas,
para que la celda «viejo, con pHYs» sea comparable con la celda ya medida
«viejo, sin pHYs» sin reimplementar la métrica.

| Fichero | Bytes | SHA-256 |
|---|---:|---|
| `ctrl_gray_units__escaneado_d5a.png` | 124752 | `b1e3c175f9d5cb76c5267cfd28b496731971adbc85c3f3110dd201b11947a6ab` |
| `ctrl_srgb_nounits__escaneado_d4c.png` | 1141642 | `b6d69dddaa49d3309c70459c1e77506d9470db9d7f0fe7aaf646f4f73265a0b5` |
| `d5nophys0750__escaneado_d5.png` | 62653 | `b61f23bd2414166b531abe4087ed000cccc43ec906e46a8695af2234c8fc84c7` |
| `d5nophys0750__escaneado_d5a.png` | 81520 | `8671d8c4c55a7f9e0b458422525011653d84a20496604be5066c643d6c4314cb` |
| `d5nophys0750__escaneado_d5b.png` | 43977 | `a1ad28e8df37ef5f52720d68b5962d43da262f90209b44d063c3f22ea93023b6` |
| `d5nophys0750__escaneado_d5c.png` | 74438 | `32a683f20c1a9d4fbce3c7b08778ab733b11d92c7aaa22db542093cfcb6aead9` |
| `d5nophys0875__escaneado_d5.png` | 78461 | `a20f7a89392933d5bf4825610c00710d6343b10f09246e641d3d0bce5a95e786` |
| `d5nophys0875__escaneado_d5a.png` | 103444 | `19d61789dc2975e1e1129d1b3bc5f2333a7807606b87b4eabc423eb0948e8f68` |
| `d5nophys0875__escaneado_d5b.png` | 56844 | `3de283fd556690a414ff96dd0ff47d440fd40c9e2650bfdf99832e4b1daad7c0` |
| `d5nophys0875__escaneado_d5c.png` | 91823 | `26f75d9348f1185c20917a0840f335bd07ced761a0c34d73af513b735a7036d1` |
| `d5nophys1000__escaneado_d5.png` | 97718 | `72e80db23e4d73992ff109fd6d740f856a5faa8bbab57cb5c12c17db841b03f9` |
| `d5nophys1000__escaneado_d5a.png` | 124796 | `7780392607f1885d6b4b43aa4271fd6c22a1861ab05b779535bad31caed517b3` |
| `d5nophys1000__escaneado_d5b.png` | 71068 | `c2bc2477329059e4ed50c2b8a00ffae34c4dcec105c5eb48a970a37545f2e3fc` |
| `d5nophys1000__escaneado_d5c.png` | 116022 | `ab697bd941d18dbabb26b363cef23d9e606872058174ba221d703530c4eb12c4` |
| `d5nophys1125__escaneado_d5.png` | 104396 | `de8a3b9af4e3879046f0d618e25a256cd9f94bcd48e1d2a9258f7561ded0c911` |
| `d5nophys1125__escaneado_d5a.png` | 135698 | `ab474a3aec33d6aaff59013536d59069ce04ccbf840099af6171a4c9123a734c` |
| `d5nophys1125__escaneado_d5b.png` | 76742 | `ac89a6d7ae2376f7bbf8bf451d0bcfcbb3fc24cb1459cae1e72d17ae04aa100f` |
| `d5nophys1125__escaneado_d5c.png` | 122500 | `d8e1ccbbee2af45701fd471485ce2a6d01eee432c6fd2706ae4e5a03538c238f` |
| `d5nophys1250__escaneado_d5.png` | 108902 | `d6ab04f92d2e04d1aadf8d2e5a9b00060a1c511530570e93d7cb5310e613a748` |
| `d5nophys1250__escaneado_d5a.png` | 143032 | `884693e0decf3bfb67920dcc99348e3835578601cef6d1abf8c0cfb3f298ff01` |
| `d5nophys1250__escaneado_d5b.png` | 77830 | `94aca7788c9155ffe7483c3dd15372976e9fec03c5bde66d7dce65faadf715c2` |
| `d5nophys1250__escaneado_d5c.png` | 128239 | `bf30e23059f6d231dae60f7d50d48427822aa8c9510f4be5a3ac11f4a544a7cf` |
| `d5nophys1400__escaneado_d5.png` | 115583 | `5734e4f5c0fc8e76387890a9a2f9b934adfb20e86058d2db5f890511ddbd5d2c` |
| `d5nophys1400__escaneado_d5a.png` | 149002 | `57249909a26d6986d76436170952e81867aaf3d39cc20b5c5eff46fee879f811` |
| `d5nophys1400__escaneado_d5b.png` | 84438 | `ad78e02b73a6b5ff07011f71996fb825468fa77920cd1fd606a67f84d30d89a1` |
| `d5nophys1400__escaneado_d5c.png` | 138969 | `23f5ff4f65b1935c0c50f2bba5a8a0e6ef0a3a98df4fff441a9c89715a86990b` |
| `d5nophys1600__escaneado_d5.png` | 123535 | `dc9d90394bafb5e47514df7a05a1e05393a37d458d5a3142c38caccf52b5d0b3` |
| `d5nophys1600__escaneado_d5a.png` | 158068 | `72e34f61d69d25726189021b23394cf680e969b0cc1e033c762ded3917263a0e` |
| `d5nophys1600__escaneado_d5b.png` | 89652 | `9a4c668c39c4e055938d91067cbe037caf3e842afa4e320e411690cb56ec6e04` |
| `d5nophys1600__escaneado_d5c.png` | 146624 | `3357cabc4f1cff7cfd3489376cc8d5658a46f3036917e41656428e86a9805a83` |
| `vphys0750__escaneado_d3.png` | 217118 | `8114091a5dfa3951c48f5254022ba4c617aeffc8ecef621a5a1a9be21940d209` |
| `vphys0750__escaneado_d4.png` | 755752 | `c42b5bd4a878c67ecf9d514f1255c1c872dad2e9e02e35ac6f5a19f39be8bdb7` |
| `vphys0750__escaneado_d4c.png` | 714895 | `84c691ccf0f135d0fd0a14782d59b83c63a7bbe1fa4378d0dbb48ccb1a1ff67b` |
| `vphys0750__patologico_escaneado.png` | 2265789 | `0efe750727b9f08d91ac50b5916aa6d865bcf0db8bde1e6561a18e4564266b4e` |
| `vphys0875__escaneado_d3.png` | 289788 | `2f1839fd5a4a04393e68ad737b01b5696e9eef1a259b0eb02c5e5d1eabc1851f` |
| `vphys0875__escaneado_d4.png` | 933249 | `f0d79002cde6c2df72cd817e57eeed103d4a20eb999bed6e4b6bdd7c26c7f312` |
| `vphys0875__escaneado_d4c.png` | 921522 | `d8c6487bd8796df6618212f4ed93bba46417aad4122a84ae699f5ab5f752c47d` |
| `vphys0875__patologico_escaneado.png` | 3090321 | `33bcfd16198ece7ce73accd7c264fd7144c8af72d601fa171a021af7454fca76` |
| `vphys1000__escaneado_d3.png` | 364119 | `b8299069211d490e3f9f634c647cb87aa153fe326210d83f387a8d860075801e` |
| `vphys1000__escaneado_d4.png` | 1172530 | `36595c063a0a7a751925771ac4c6b5311b5919f5995509a71329b74839c4d802` |
| `vphys1000__escaneado_d4c.png` | 1141598 | `f24245d063de14025fe39d10ef988a72b9158fdc81b92a1ae3d4b00e3187ff84` |
| `vphys1000__patologico_escaneado.png` | 4016393 | `0fed0beca74feca9f10a98a9673ebf9951f90e8327b166cf5fb90355738d5896` |
| `vphys1125__escaneado_d3.png` | 393120 | `c2319ac71972b26e0281cffdf05ca85b7578040f7f40e377c7657f7bc38b3b79` |
| `vphys1125__escaneado_d4.png` | 1262467 | `08094b7d159dac391514669314964cea84b9b0e309f0da661e5e1bdf1eb23e11` |
| `vphys1125__escaneado_d4c.png` | 1231183 | `3551ed10e52051a114c38fe84490b5eee6e2b129d679ce6e3565b34fbe6b51c7` |
| `vphys1125__patologico_escaneado.png` | 5054850 | `755f0d11b9388dcd3c9d87153eef3ead3be44c7148cc212526e6441c30fa2660` |
| `vphys1250__escaneado_d3.png` | 414307 | `c65bb5539eb45f77780537184816f449e633922deb956ffd32a34fb38fa87414` |
| `vphys1250__escaneado_d4.png` | 1338347 | `dc54661928664a2b960650ba35fc1c2b31a151702f21a72005f9fa5030752038` |
| `vphys1250__escaneado_d4c.png` | 1306838 | `17c30e0ab6d968252872e93a70b3a878de6dfe1f56e4bf34210e02ce2848e9f3` |
| `vphys1250__patologico_escaneado.png` | 5296386 | `d4dc5131c4c846e2cde443ed95671751e267960a01a77c7c651fcc3b595f8914` |
| `vphys1400__escaneado_d3.png` | 436391 | `6187828e5f5cb8c35f1e3dd78121212f64c621c107a512e804bdc369fcf952ec` |
| `vphys1400__escaneado_d4.png` | 1441993 | `3232e84261c49bccfdc90ab1b8a530ae34a91e08284e5a6fa5fbfe98dd3d9441` |
| `vphys1400__escaneado_d4c.png` | 1405447 | `da5c9ba7ae6c24cfbc018fb4deff6734e0d54b1a18709b9e8fe7b8ae5ad9481e` |
| `vphys1400__patologico_escaneado.png` | 5533080 | `68c2f1b62d81cd953496b675f7512696dbe10ef78940d2afa8f8581c399039ea` |
| `vphys1600__escaneado_d3.png` | 464948 | `501e323859bcb46f117af5b1ac7beaebf267b7cce1abf08e0441590d788a194b` |
| `vphys1600__escaneado_d4.png` | 1537339 | `ac43e049072047df251fc34a31c117135726dfc9986553c1f6faf5c593fe170e` |
| `vphys1600__escaneado_d4c.png` | 1501746 | `4330d3253f8e42d2a1a8fe0e7be470df7c5d1cdcc189e0c2cb5ea9f20b6d1dee` |
| `vphys1600__patologico_escaneado.png` | 5739663 | `2681a57c311ea03e539eee5878a225465dc144518d3a02e51cf51562fbf0e582` |
