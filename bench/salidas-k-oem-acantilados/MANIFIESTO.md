# MANIFIESTO — bench/salidas-k-oem-acantilados/img/

Los **85 rásteres PNG** de este directorio (16 MB) **no se versionan**: son
regenerables.

- `k####__escaneado_d3.png` (13): B16, receta gris SIN declarar pHYs — MISMA que
  `bench/salidas-k-motor/preparar_km.py`, a proposito, para reproducir los anclajes
  ya publicados byte a byte. RapidOCR y PaddleOCR son inmunes al pHYs (trampa 29).
- `kf####__escaneado_d5*.png` (28): B23, misma receta gris, familia d5, factor sobre
  el nativo de cada documento (60/72/80/90 ppp).
- `kd####__escaneado_d5*.png` (28): B23, receta DECLARADA (`-units PixelsPerInch`)
  para Tesseract, unico motor que consulta el pHYs.
- `ppp###__escaneado_d5*.png`, `raster_im__*.png`, `raster_gs__*.png` (16): B24,
  oem/psm al nativo y el control magick-vs-Ghostscript.

**Orden que los reproduce:** desde Git Bash de Windows (cd al worktree primero):

```
"D:/Work/research/FileX/.venv-ai/Scripts/python.exe" bench/salidas-k-oem-acantilados/b16_acantilados.py rapidocr-r6 --reps 3
"D:/Work/research/FileX/.venv-paddle/Scripts/python.exe" bench/salidas-k-oem-acantilados/b16_acantilados.py paddleocr --reps 3
"D:/Work/research/FileX/.venv-ai/Scripts/python.exe" bench/salidas-k-oem-acantilados/b23_k_d5.py <rapidocr-r6|paddleocr|easyocr|tess3|tess11> --reps 3
"D:/Work/research/FileX/.venv-ai/Scripts/python.exe" bench/salidas-k-oem-acantilados/b24_tess.py <oem|psm|raster> --reps 3
```

| Fichero | Bytes | SHA-256 |
|---|---:|---|

| `k1250__escaneado_d3.png` | 414307 | `b5812cc4f464da6669bb1890608f331c027310eb4e0f2ba790a5638205d6b119` |
| `k1280__escaneado_d3.png` | 419502 | `be34a3774adac0be2d54384cd01ddb55c125426a9bbe560c5fe7924cad2bccdc` |
| `k1300__escaneado_d3.png` | 422330 | `ae906fa14b1e7617cafdbc0beb70549377dbb12770d39c0d1f81e2dc054b6ce9` |
| `k1320__escaneado_d3.png` | 424762 | `858a880143fd5bee0a6f875b61fbbe8a2ad6e95de7611aff264ffaa0cdc859c3` |
| `k1350__escaneado_d3.png` | 428747 | `f8e61913d326b6c18d86db8ab3e46255a0d139a9a614c18d6bcc1b8c9c9756a0` |
| `k1380__escaneado_d3.png` | 433572 | `08735e8136280c6d3ade3de90068678bb414196977d63d73e409c183e9b80e12` |
| `k1400__escaneado_d3.png` | 436391 | `0061ae48ccacf8e13a044544167fd86d302cb65fe5072e03b06e5e85e4d75927` |
| `k1440__escaneado_d3.png` | 441604 | `3d90c9ae0f13e44eac363e08b7442bdda3b91312fef3516de4659ad2b9f5def4` |
| `k1480__escaneado_d3.png` | 446229 | `3027b75c4288406855da4d31980fbc6feab8d336f6351558d691178d242bbad3` |
| `k1500__escaneado_d3.png` | 447327 | `e3e2b0ceaf998cad6d0407c29c3fcdda94979369f9d1b3c75927d2f561a3cd89` |
| `k1520__escaneado_d3.png` | 452110 | `17f3cbf8025190eb822e4cb7e29535f8145a73722ea928eca50d4641fc162d0b` |
| `k1560__escaneado_d3.png` | 459352 | `8390a58c2110b83b6bce627b7f0159ff292ecd22b09556d3b7248d5332ff07da` |
| `k1600__escaneado_d3.png` | 464948 | `7cd0086aaa1d58d60b2a18d753662aab77208d1e7fd17d69b5553ef2972a90dd` |
| `kd0750__escaneado_d5.png` | 62653 | `08322ef3c40232737c03f5e71e34a799e8024c75fc04ec00b8a892b2612c5734` |
| `kd0750__escaneado_d5a.png` | 81520 | `1577047587f61939230419c62866cebc46a18e5a7b8c68da9f9fcc94adc2b40e` |
| `kd0750__escaneado_d5b.png` | 43977 | `ea2b07b3895fce6443db69089356290b985b2cb3eefbc2181317b426df9cd4f1` |
| `kd0750__escaneado_d5c.png` | 74438 | `8ba04247f19f59acf7b42fc4c7fe619d0f45f1b1fa64e5380b279cc94e6c3fae` |
| `kd0875__escaneado_d5.png` | 78461 | `a57e12e6f328b8788cd162670cd1956f990e11ebc5bcbb2f30af00ea04559127` |
| `kd0875__escaneado_d5a.png` | 103444 | `fd5cefa86f766bbdc7a74d2b6da7024e372741d3adacd9bfca4f3f11cc602ae1` |
| `kd0875__escaneado_d5b.png` | 56844 | `11b657caf84f40ef0e7db45441127f6b225f76e99a3a4ce9a3c05dea6b206f3c` |
| `kd0875__escaneado_d5c.png` | 91823 | `f223ff5e6a940a12e9d00f06732d0532aa540b21d047738a9f23c35ff3c69f9b` |
| `kd1000__escaneado_d5.png` | 97718 | `e433a19640c1c3c4b7d836a00fb4df74120c153b0f3d9785846fe1c80b6b3117` |
| `kd1000__escaneado_d5a.png` | 124796 | `0c1d9b0b99292b2597650ad92b3887c7049fa6603d5c74cbde672cb0d5b14b53` |
| `kd1000__escaneado_d5b.png` | 71068 | `67cc5a77d35c578f4a96eb6bb01adce9c2f3d5342444bd97fa2c514f6fe94086` |
| `kd1000__escaneado_d5c.png` | 116022 | `44aa0c9bfc3ac43b23750421317a77aad95a65604689eb151b2b0c46bc812ba8` |
| `kd1125__escaneado_d5.png` | 104396 | `8e38caf52dd327bc2dba8e1d5d2dd3d65bf323000320113d0d0b4e6b29b5d494` |
| `kd1125__escaneado_d5a.png` | 135698 | `ce5a762bb663edafe2f528c5efd0081e03a8ec4e0ac67dead38932e068210fc1` |
| `kd1125__escaneado_d5b.png` | 76742 | `b98af819abe5688bf23b9e11c19d4415cd11d6ab5c1a438bba9fd57e375b16b1` |
| `kd1125__escaneado_d5c.png` | 122500 | `e2ecdb567882ae836055a0c16855fae8e160815dcd15365f157cda382bc2249a` |
| `kd1250__escaneado_d5.png` | 108902 | `1e1127d9a7caf445adf5cfac05b1fa39afeabc325ae1fa3ab97360114201a160` |
| `kd1250__escaneado_d5a.png` | 143032 | `cd9a23b3e4737c2dc2ab05672bbcac1b2e397da2b6b54fcf3e332ad9c51d8aad` |
| `kd1250__escaneado_d5b.png` | 77830 | `b51af765e97ea6d3b4303631af34243725b4ab317e9cee992136b23cec06d63e` |
| `kd1250__escaneado_d5c.png` | 128239 | `24eb7d36de1a6f7d06eaa27907405f1186077978b408af1c10ade98276f99618` |
| `kd1400__escaneado_d5.png` | 115583 | `566bc8c2a4725617ea628891cb4109a2a92a25d197b93518e674563da2a447e2` |
| `kd1400__escaneado_d5a.png` | 149002 | `bad3d5414ad4bfc1be2fb96d7457acbc60bde9f6d18e358b4f397277b5157a9c` |
| `kd1400__escaneado_d5b.png` | 84438 | `38e129bfe91062ae57b915bf24c4f127836c1cb5e4c26b474de81cc8985e28b6` |
| `kd1400__escaneado_d5c.png` | 138969 | `cccee406e9b3009f0d555ebde744a0552f52026984958bf5bd1deef8b1162e50` |
| `kd1600__escaneado_d5.png` | 123535 | `476eb28ed182276181c60b8cfebdbacda375a592effe5e3acc3103209a407c2c` |
| `kd1600__escaneado_d5a.png` | 158068 | `651828b27ccb5ff60a9645732f9bdd4afe6b080c813b85941b1b8b9768f7d513` |
| `kd1600__escaneado_d5b.png` | 89652 | `3093061e0008d7dcda807acdcb0376ffaffd9c837f79ccbb30d2256c69e35bee` |
| `kd1600__escaneado_d5c.png` | 146624 | `e727423b1775e1dbd5bd84801a6ca6ee7571a0e6d3e4057c9b52c11bb0306ad2` |
| `kf0750__escaneado_d5.png` | 62609 | `b6d5084780d77389535c9cf044aaccdae6ff02b3a7309b9df6e169d49a312892` |
| `kf0750__escaneado_d5a.png` | 81476 | `5fba62cb024083cb15db831ed76d830e4db403826a6de0bceab6591743db32f3` |
| `kf0750__escaneado_d5b.png` | 43933 | `4246975e86dc4aeaa4638dbe60acde6ab117b1fe345d06be35902fcfd94f9034` |
| `kf0750__escaneado_d5c.png` | 74394 | `3128bd30390d144866ea549ba6c7212539a344b14657b28c362ed20735fc9af2` |
| `kf0875__escaneado_d5.png` | 78417 | `cdf8be9d4fbc638f2eea2fee908c31a374c27095734b7824dcd8886559b88886` |
| `kf0875__escaneado_d5a.png` | 103400 | `2026009003e43bea0a9921916a69ddbbbacbebb98eb22314add8491b5cf4f65c` |
| `kf0875__escaneado_d5b.png` | 56800 | `1e14cb81e1219c97725c3b0689955407f32d6aeba73305f2a3f50b3d017157b0` |
| `kf0875__escaneado_d5c.png` | 91779 | `46077ce24b87f5301a15c6d06514d7fb5dc92d26625468fc35a96c88fe59d97f` |
| `kf1000__escaneado_d5.png` | 97674 | `dfb7dbfcbb6a74a12aff0f514815e0e40fe75977e410062347ff34946b2c17d8` |
| `kf1000__escaneado_d5a.png` | 124752 | `49fb896a245cf303ef1092d736316920cde396192bbf14b488a7f4680d08bd7d` |
| `kf1000__escaneado_d5b.png` | 71024 | `77b1e972feb7ad2e57e1a20ef1878ba6e8e5ceba61e6e1f068b2e1fc21b345b7` |
| `kf1000__escaneado_d5c.png` | 115978 | `6c2492f0078050cfa4e0e45ba75802f1ca9d1e798375f92714e6db63dfd7060b` |
| `kf1125__escaneado_d5.png` | 104352 | `d782332aa51bbf5b9f5021f807212ad27d4b68951ad3cd6585d27444c4a7fd58` |
| `kf1125__escaneado_d5a.png` | 135654 | `d82aa9130884b81402947d330a4dec649aaf4e89df5103efd14ed313a90abf5c` |
| `kf1125__escaneado_d5b.png` | 76698 | `abf40ff9a99c64735af9e27af111bef14cecfdfacd7a1d50856fa3753fa960f3` |
| `kf1125__escaneado_d5c.png` | 122456 | `7294cf8f41bf9c5e102c562045ab68966449cb44556cc87d77bf83bf790ba51a` |
| `kf1250__escaneado_d5.png` | 108858 | `8bcf9b0a211754422c1b32f5679efecc35e74e14158ae8981db8e6dde7af02d9` |
| `kf1250__escaneado_d5a.png` | 142988 | `9826cb8baa405264249396a88ba8d78fb49c48d7795c119a0f9316e2a0eb7055` |
| `kf1250__escaneado_d5b.png` | 77786 | `f3319e103b50b98fc4be751022e5e40ba5dd90727bf1bb1e705e3e0434b20bc3` |
| `kf1250__escaneado_d5c.png` | 128195 | `e2ca7023622c6a02a0a7ed0515047e46053943f71f4c970605206704c7345dd5` |
| `kf1400__escaneado_d5.png` | 115539 | `918d9b923e26fdf8793fbfd4613484e52c589cff39267586a6dcc56f82cc3186` |
| `kf1400__escaneado_d5a.png` | 148958 | `05afea9b8a9aa2cad3d5367ca7e16ae71869e450db47f0a9ccd006af33cb2ada` |
| `kf1400__escaneado_d5b.png` | 84394 | `41933e96d86a5399d750b879506587f02f0c8d70b55ca994aea08680338c97ce` |
| `kf1400__escaneado_d5c.png` | 138925 | `50c9d46e857f12856806235d024d72e1cec376e3aa1cc3d8cfa557a78ead9a62` |
| `kf1600__escaneado_d5.png` | 123491 | `fc09dfc3adfe0357c30f78c5bdb01573a73b4d776720b67fa060ff5fb4ddbe22` |
| `kf1600__escaneado_d5a.png` | 158024 | `694e92b1edbdfedbc53ff73782b059e17f3889354993d6469fc3fd52a60f59a2` |
| `kf1600__escaneado_d5b.png` | 89608 | `a5e51d2d3154101b63f47057655076ee6d09ff5f6938b7dc3bb3f7165989b13a` |
| `kf1600__escaneado_d5c.png` | 146580 | `1680e180dc99ab68b18c21694010d0e799ae59b6f57cd0d8e923d2e92deacff7` |
| `ppp060__escaneado_d5b.png` | 71068 | `1c8e555c36769b1bf0c7a8428c2d4a503eb02c161b48683a34ae131574fe47b9` |
| `ppp072__escaneado_d5.png` | 97718 | `ba14b5de3761f1a9eabd7cecf61c696651c3a8e34ae5256fba2a08e1fdf1884f` |
| `ppp080__escaneado_d5c.png` | 116022 | `c46310ef817705f5687149ef7565135c057a28f079717912046e1836a2cc19ae` |
| `ppp090__escaneado_d5a.png` | 124796 | `832b248414acfb1c12b7192095eb57a0c8f5407f9b109a0b26b2b6a75aff1f41` |
| `raster_gs__escaneado_d4.png` | 1933634 | `fb8fa09e9facfbd51aa0c4bc058ebc992dfeab3fbc0f795c44b44bef474521b5` |
| `raster_gs__escaneado_d5.png` | 179914 | `901dff18c92d9f95ccef86931671644c7c7eea1c4a2be46995226c4fcd3ace5a` |
| `raster_gs__escaneado_d5a.png` | 234476 | `ece9f45606dfd325a558666c285e70db97d2e4141e8ceb6143d7ac375be240ce` |
| `raster_gs__escaneado_d5b.png` | 129045 | `8f03851dd553232d3404a24ebf800c7d9f6a295a4439852d7b25993279e9074a` |
| `raster_gs__escaneado_d5c.png` | 212822 | `b0c9bbacac3073343b14b6b5c4502dacc972ac0c87961b81302b62705073386b` |
| `raster_im__escaneado_d4.png` | 1172574 | `526996b4fb3b1c8e1a7c93eb013343e95a0d50e843182bff0195aed0cc4779b1` |
| `raster_im__escaneado_d5.png` | 97718 | `b57e84dda6a6c7226bc832992fc70d276c5a4c5c3f4cf1dbe6cbffcff1e94b94` |
| `raster_im__escaneado_d5a.png` | 124796 | `a53d8c13ee260910851438c1c01e77843421c3cee091e9fb5486becde10a4eef` |
| `raster_im__escaneado_d5b.png` | 71068 | `b0ed2b8c52f33b70fdcef572859c3938f757339795d4130482f2cf5e3e44a25a` |
| `raster_im__escaneado_d5c.png` | 116022 | `774c446e8815e63a4841ae4efc7a07ace23ca18fdf41163771cd62be532369e9` |
