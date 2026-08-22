# MANIFIESTO — `bench/salidas-sondeo-ff/`

Sondeo de las **70 aristas `sin_sondear` de ffmpeg**. Informe: `bench/sondeo-ffmpeg.md`.

**Build medido:** `ffmpeg N-121159-g0bd5a7d371-20250921`. Una medida de otro build **no se aplica** (`filex/sondeo.py`).

**Los contenedores de ffmpeg no son reproducibles byte a byte** —MP4/MOV estampan `mvhd.creation_time`, Matroska un `DateUTC`—, así que el `sha256` identifica el fichero que se midió, no un objetivo a reproducir. Lo reproducible es **la orden**.

Todas las salidas binarias de esta tanda **se han borrado**: eran 70 ficheros y ~85 MB.


## 1. Fuentes derivadas (el corpus no trae `.webm`, `.mov`, `.avi`, `.m4a`, `.opus`, `.ogg`)

Se generan con `python bench/salidas-sondeo-ff/preparar_fuentes.py <dir>`. Todas las de vídeo salen de `corpus/video/patologico_2pistas.mkv`, que lleva **dos pistas de audio**: así cada arista de vídeo vigila de paso `-map 0`.

| fichero | bytes | sha256 | orden |
|---|---:|---|---|
| `f.avi` | 8091090 | `03a06afad275f709ea9c4705042d1f3ed735cf3593bb1d8e31d2dd3477e3046e` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/video/patologico_2pistas.mkv -map 0 -c:v mpeg4 -q:v 5 -c:a libmp3lame -b:a 128k -f avi <dir>/fuentes/f.avi` |
| `f.flac` | 104318 | `b4950a7155d749deb68c894e96143194e1b6767895549ad33a9c3ec05717e684` | *(del corpus: `corpus/audio/tipico.flac`)* |
| `f.m4a` | 131397 | `965d6ebd2d6710a8cc9ded38e354ed1b9ec789cf6ca140fd94de4c8bde96ec18` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/audio/trivial.wav -vn -c:a aac -b:a 192k -f ipod <dir>/fuentes/f.m4a` |
| `f.mkv` | 4079196 | `e333ad7f6d175d8a3b9e41d3a749165394a3469e12665b126bba7c7f4f3407bd` | *(del corpus: `corpus/video/patologico_2pistas.mkv`)* |
| `f.mov` | 4085382 | `502b323020d981aa3312389c345d519fdfd762b94af14cae939ef1780d9d841b` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/video/patologico_2pistas.mkv -map 0 -c copy -f mov <dir>/fuentes/f.mov` |
| `f.mp3` | 64591 | `04b12a569ebe74fbda11b5e8b72e8e848fd6ae0eaec8ad4633d0bb902d087549` | *(del corpus: `corpus/audio/tipico.mp3`)* |
| `f.mp4` | 4085275 | `126b8cfa3342d98be3126aa8f754f05a87a631528dabd0783fd77d814df05ab4` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/video/patologico_2pistas.mkv -map 0 -c copy -f mp4 <dir>/fuentes/f.mp4` |
| `f.ogg` | 67870 | `7fc5ade4d5dba11cde308fe9620c7eb034905c77b8ea1de214a5c123d267b32d` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/audio/trivial.wav -vn -c:a libvorbis -b:a 192k <dir>/fuentes/f.ogg` |
| `f.opus` | 209834 | `674dec468c968c2631fcdfd675435d21878aff02e7c4d8de1f63219083353714` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/audio/trivial.wav -vn -c:a libopus -b:a 192k <dir>/fuentes/f.opus` |
| `f.wav` | 705678 | `b5fb614afefa1581dd00e2e417ba2578081ca7b512ed375d478890fbd86d2123` | *(del corpus: `corpus/audio/trivial.wav`)* |
| `f.webm` | 3627924 | `71ea00c0c6221f852efe541a1874763bb70a331db4a3d49e8a2da8c18f138b48` | `ffmpeg -hide_banner -nostdin -y -threads 4 -i corpus/video/patologico_2pistas.mkv -map 0 -c:v libvpx-vp9 -crf 40 -b:v 0 -row-mt 1 -deadline realtime -cpu-used 8 -c:a libopus -b:a 96k -f webm <dir>/fuentes/f.webm` |

## 2. Las 70 salidas del sondeo

Se generan con `python bench/salidas-sondeo-ff/sondear_ff.py <dir> 3`, que para cada arista sustituye el grafo por uno de **una sola arista** y llama a `FileX.convertir()` — con el desechable, el censo del punto 5 y el contrato dentro. La orden literal que `motores.FFmpeg.orden()` construye está en el campo `diagnostico.argv` de `resultados.json` para cada `nominal`.

| arista | estado | bytes | sha256 | ms (mediana n=3) |
|---|---|---:|---|---:|
| `avi>flac` | real | 507206 | `d75fe41d82715299c6af9ed892b9bb5e0d208b8c45b69010b90b123253631cd6` | 57.0 |
| `avi>gif` | nominal | — | `—` | 43.5 |
| `avi>m4a` | real | 160970 | `aba25b88976b69df63a0249257910f0dfa965b9c005c45a9df278b662298c4b1` | 852.2 |
| `avi>mkv` | real | 4023657 | `9388f1cf5032e26934d16210623ea69f59ce0f2e6d407269a1657b444baed144` | 3143.8 |
| `avi>mov` | nominal | 4027763 | `345168a802a3b2a687a3ce2234e417742168357be878c98e7e1da8c60b11f0f3` | 2239.9 |
| `avi>mp3` | real | 242701 | `001ea59ab20dd0fbd49ac3ec9e6b681971d09a611950cc3e4ce4e1d7906f11f0` | 126.2 |
| `avi>mp4` | real | 4027656 | `6a96ef7aba7c1a587037be588913ad65692e80ea5af72d76c7d1798477287c1a` | 3318.7 |
| `avi>ogg` | real | 89150 | `bdfcfc3206f73c9ee620023514b429ce5a7c61c9fafe4beb94b3ac0007bbdded` | 177.7 |
| `avi>opus` | real | 263684 | `08a8eac7328b982dc209d613ca90c6831aa421095e9e2e21922992b5e59ce3e3` | 138.7 |
| `avi>wav` | real | 887118 | `f4de68c66c5836f23e61112885729ad9329398e0b149f3ad814b789299e2674d` | 59.2 |
| `avi>webm` | real | 4254211 | `48a9ed721d63984611dbe9a46682c6cbc3b0dc19a0cf7e9da44bd0e226975c4d` | 11270.5 |
| `flac>m4a` | real | 131397 | `965d6ebd2d6710a8cc9ded38e354ed1b9ec789cf6ca140fd94de4c8bde96ec18` | 642.1 |
| `flac>ogg` | nominal | 67870 | `d698c4c4d75e2a4af675150e5eeb4e502b437bf9b521e1e616912603d1a10a5a` | 118.9 |
| `m4a>flac` | real | 425009 | `47529ec6d90c8abf61c1cdf8fe5644afef4a96d0ffdb81a4af4ae19a1a8775b2` | 59.6 |
| `m4a>mp3` | real | 193866 | `fb21f5f689ae2e78daf4f3e03c22239a9f07112ab3c57f4decf13e13a9c579e8` | 111.9 |
| `m4a>ogg` | nominal | 68659 | `39f60cae48176b916c7d45d42e23e7a204cd333d1f78bc0c81dcf10ac28580be` | 125.9 |
| `m4a>opus` | real | 210828 | `6e6490436a676f093e29dd293def5828ad66918c6dcac19db946e191a2812c38` | 108.6 |
| `m4a>wav` | real | 706638 | `ff7bff551f1cb1f3b80873874709ccaf600569d31121defdb65a9026a9c98d93` | 63.6 |
| `mkv>avi` | real | 3996458 | `f480d18426e413953d14b52612e76600d5d323fbba7e1ac82c64afd6d604d6a2` | 2153.7 |
| `mkv>flac` | real | 505842 | `1ecadcbb958fc671f06cb80e64791085be1f52b633f8d263ea61d1160acd0fef` | 79.9 |
| `mkv>gif` | nominal | — | `—` | 56.4 |
| `mkv>m4a` | nominal | 126057 | `03734e26a80e8fa128448b1db1d97570ecd77f9e40f7181e69abe0d94f8cade6` | 818.8 |
| `mkv>mov` | nominal | 3966949 | `d3322af36625f4d9ec1efe61f3434c6f8c249072a141e81b8af8cb2057d54191` | 2140.4 |
| `mkv>mp3` | real | 242041 | `14ebcd013572dfa3ddc67e5e903a69dcb3791d8d65489074b19e8cb56b7b0c5a` | 143.3 |
| `mkv>ogg` | nominal | 88086 | `cef4c0b5f92512bbd57cd1725965264b5667b8a7fc5daa89b5b392cd557741fc` | 174.8 |
| `mkv>opus` | real | 263363 | `f771a616e37d21331624d3688a7c21d5a0dfc2135802492ce86ce5cb70c4085b` | 173.6 |
| `mkv>wav` | real | 884814 | `0035c5248e308f80e2fa57510ef3cc261fd9bb8c95312f1f14c5f1bd9ac98e80` | 85.9 |
| `mkv>webm` | real | 4306234 | `8b9f30bd3d2b3b6228e28d941077abc6ca0dbb98c6a7df6cd9d80f5f7eb49134` | 8917.6 |
| `mov>avi` | real | 3996458 | `f480d18426e413953d14b52612e76600d5d323fbba7e1ac82c64afd6d604d6a2` | 2233.4 |
| `mov>flac` | real | 505909 | `e60d3615bc1803f5313ac9381ad80e65f041ae4899bb330d7c242256a9369d7d` | 113.1 |
| `mov>gif` | nominal | — | `—` | 66.7 |
| `mov>m4a` | real | 126057 | `03734e26a80e8fa128448b1db1d97570ecd77f9e40f7181e69abe0d94f8cade6` | 1923.6 |
| `mov>mkv` | real | 3962995 | `5ca705cd93572bef4d5360c5d9dbafd3221c7546e4eb7d75b6b2215bb5cee949` | 2342.8 |
| `mov>mp3` | real | 242132 | `3395856a077aedfcb9138154404d0af951fe2f82f1fe70bafc99340b798b2113` | 150.5 |
| `mov>mp4` | real | 3966842 | `7105da74af1d5d4a04873604f9d4919db4c39189c4ba4b77242f740918c0f85d` | 2134.1 |
| `mov>ogg` | nominal | 88177 | `53c8920e801251c8dd6227e2b9a48d6538e3fa3444ecf05606fa1b2ec1f656f3` | 669.8 |
| `mov>opus` | real | 263454 | `517adda72355e01ec06c9d81aa717bdfdcbc1b1b6600fe47a6a43274dad3fb5c` | 169.4 |
| `mov>wav` | real | 884814 | `0035c5248e308f80e2fa57510ef3cc261fd9bb8c95312f1f14c5f1bd9ac98e80` | 92.3 |
| `mov>webm` | real | 4306494 | `b6aa1d707f8a5561e84692653148f440b7641aae2995b27b7185ee339babeee1` | 9556.9 |
| `mp3>m4a` | real | 142738 | `f583056ff590ac2310e5c91bd53fde7b74ca6add465d6cad4d91398b56ee46ba` | 588.2 |
| `mp3>ogg` | nominal | 68372 | `4bcdaba1e43490fe54ee3ada27e8930c3d9673463f9ff8d37d0276c35b3d2fd1` | 120.1 |
| `mp3>opus` | real | 209875 | `cb5e0b96796d73b593d8f3c9240eb12d8a3a522c4b53bf31c12fa9f25255d59f` | 109.4 |
| `mp4>avi` | real | 3996458 | `f480d18426e413953d14b52612e76600d5d323fbba7e1ac82c64afd6d604d6a2` | 2231.6 |
| `mp4>flac` | real | 505921 | `51026bee72a20fcdbf764933c6c703cc22008a2204c4ee304636b46d6a069176` | 75.4 |
| `mp4>mov` | nominal | 3966949 | `d3322af36625f4d9ec1efe61f3434c6f8c249072a141e81b8af8cb2057d54191` | 5435.1 |
| `mp4>ogg` | nominal | 88205 | `9d0466cb550d3bd9c739ebc3e183fbb05908f1339a74cc24870f271028f9acf3` | 159.6 |
| `mp4>opus` | real | 263482 | `00e04540b8049d88ccb0d94a6eb002f1a0bf8a79b74bc799c751388548104f9e` | 140.4 |
| `mp4>wav` | real | 884814 | `0035c5248e308f80e2fa57510ef3cc261fd9bb8c95312f1f14c5f1bd9ac98e80` | 71.0 |
| `ogg>flac` | nominal | 396554 | `9d941100dc7e777a8d7157981e3f875c5d5c6a429f80ee923887f1aebbb1c03b` | 57.2 |
| `ogg>m4a` | nominal | 135243 | `95df7096525f9ebbc78dbaf085869acac7a562a1d694840700c2359a70883e39` | 565.1 |
| `ogg>mp3` | nominal | 193767 | `d2e80f7ebd34b4e44e2800038d1bf0b08975561bc83022d0652feab842747d2f` | 100.3 |
| `ogg>opus` | nominal | 214701 | `ed3842fb2c91f49f4fdad698b561e55c6dc9f59987ee05367a7af2f790babe16` | 110.5 |
| `ogg>wav` | nominal | 705678 | `cc4579dc3221e7b2b39ca29b1268e054cacc96b3f0f5aaaf8d6314849b9003ad` | 66.8 |
| `opus>flac` | real | 464456 | `9daf25b46a85cb7a1c40b4a68669d0eaffd364e80312e358cdb82575248dddd5` | 91.4 |
| `opus>m4a` | real | 140767 | `22a31e19cba166068a169069d740c07bea891f2bbe278e70cb3973964fed4d58` | 688.1 |
| `opus>mp3` | real | 193580 | `785fd18b0f4f049addce12ba4a44240353c57f87375ca3551916c2c10e95d921` | 113.7 |
| `opus>ogg` | real | 78304 | `1953f7cd30ef3b0e1508cb8353cd3e641abac5b76921de330e58aa92b4221815` | 146.9 |
| `opus>wav` | real | 768078 | `4a62d9d6e589e0d54e6c626116067c1cc1125ebaabca2b973bec2c13ce1a9838` | 70.1 |
| `wav>ogg` | nominal | 67870 | `509d8a7cd15bede464b2d6874060597a37073dadb3319824df7be874aebbd40e` | 152.5 |
| `webm>avi` | real | 4179602 | `c9630188d39877a66034ceb2cf23f38b92fddf6bbd6b9f263a3495ae9b2077bb` | 2075.1 |
| `webm>flac` | real | 538445 | `19aca91dafa949c0a58f851b3bc6074c78a1d630b06e4d8716d261b9a9579ba0` | 86.3 |
| `webm>gif` | nominal | — | `—` | 56.8 |
| `webm>m4a` | real | 169454 | `47a90c8e515e4209623bf116f9a267ecedd2a0600fe8b752f8cbf4c8f21d4198` | 1097.4 |
| `webm>mkv` | real | 4144568 | `02dd091abb08df6b6051a72203876ec7acacd930e270ef48b5c0b4ff23925766` | 2288.2 |
| `webm>mov` | nominal | 4148982 | `46f313c40eb034e35a4fb407fe29d7d9aa90e7d91787d98c0f665d218aa43754` | 1978.3 |
| `webm>mp3` | real | 241964 | `e5a01df9ce4170f84bd350c483b486f0de73bf80b81512824f902e6e33d62bd5` | 177.8 |
| `webm>mp4` | real | 4148875 | `29126071d983c07c6905d12c66460268c6fde9608eb178f55421a8b5b8547da4` | 2490.0 |
| `webm>ogg` | real | 89219 | `44824f039bf6a8d85dee14418126aceeefaa2db49240563dc4bb4f225ac6e5e6` | 295.8 |
| `webm>opus` | real | 262464 | `a36a990f95dfaa3956aa89206604a7ecdb94b7b6924bb3e327d95abf96e50384` | 153.0 |
| `webm>wav` | real | 963056 | `3b36038814b292a3edeac1ee38fbe51e7b35197de9e9a81508d9dfd059519f8e` | 90.5 |

## 3. Lo que SÍ queda versionado

| fichero | qué es |
|---|---|
| `preparar_fuentes.py` | genera las 7 fuentes derivadas |
| `sondear_ff.py` | el arnés del sondeo |
| `reparacion_verificador.py` | re-sondeo con los dos parches de la sonda en memoria |
| `escribir_json.py` | vuelca `filex/sondeo/ffmpeg.json` |
| `escribir_manifiesto.py` | este fichero |
| `resultados.json` | el crudo: rc, veredicto, hallazgos, censo, testigos, diagnóstico |
| `reparacion.json` | qué aristas recupera arreglar la sonda |
| `reparacion_gif.py` / `gif.json` | la escalera `-map 0` → `-map 0:v:0` → escala declarada |
