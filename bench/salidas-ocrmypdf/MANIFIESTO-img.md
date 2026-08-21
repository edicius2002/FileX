# Manifiesto — rasterizaciones intermedias de `salidas-ocrmypdf`

**Generado:** 2026-08-20  
**Ficheros:** 134  ·  **Peso original:** 229.5 MB

Estos PNG son **andamiaje regenerable**, no evidencia. Se retiraron del repositorio para no
versionar 230 MB de intermedios: el hallazgo que sostienen (el arnés de la fase 2 rasterizaba a
200 ppp un PDF cuya imagen incrustada es de 100 ppp) está respaldado por las salidas de texto en
`texto/` (317 ficheros) y los `.json` de CER, que sí se conservan.

## Cómo regenerarlos

```bash
# desde la raiz del proyecto, dentro de WSL
bash bench/salidas-ocrmypdf/20_rasterizar.sh        # img/
bash bench/salidas-ocrmypdf/40_matriz_ppp_deskew.sh # img2/ (matriz de ppp)
# variante Windows:
bash bench/salidas-ocrmypdf/21_rasterizar_win.sh
```

## Inventario

| Fichero | Bytes | sha256 |
|---|---:|---|
| `img/base__escaneado_d1.png` | 750351 | `ea1dc1d090438cc2c026c6caf4a45238cc52a946d7ee4aac5feb443ffe523724` |
| `img/base__escaneado_d2.png` | 434296 | `abdb6c3e938de98b675fd8d368d9e0c9c8a40d5b916229b38aae113bc008f86f` |
| `img/base__escaneado_d3.png` | 489021 | `5296fb0923b304f1fcd8fd0f568151d797c49e30bdf2d122f71b28fa536ea35c` |
| `img/base__patologico_escaneado.png` | 214040 | `df96f164b90e08dee6f74d0d682767d40657f2228b90b447b4b407cac81f6d70` |
| `img/clean__escaneado_d1.png` | 775102 | `69357e6183fbd3ed08ff4f5b5058a2f1d4ee947ed1932a95aa82816a5df2bb14` |
| `img/clean__escaneado_d2.png` | 434294 | `31c95e02235df4d77ee775a34afa4feaa60427ed7ca791d59c7c9e2c8e8ad487` |
| `img/clean__escaneado_d3.png` | 489018 | `9ee42ad024fb67ab5fbbca0c86115bfb28db6fa943751de0d0467fb67c245eb1` |
| `img/clean__patologico_escaneado.png` | 168969 | `9a255b6efa56766a33482b255347b24b219950e090642063484d35758843c07a` |
| `img/clean_os300__escaneado_d1.png` | 923282 | `c55c5afdccf6514ec19fb576513da5cd15bc552afeaf83d26bfc48368556c4c6` |
| `img/clean_os300__escaneado_d2.png` | 914925 | `a2b66d1054a9034c28eb83ebd999530e6ec3a2d1e8131bf36d79924a40d8b125` |
| `img/clean_os300__escaneado_d3.png` | 1057761 | `545779cab5d4eb60e39cbb9d9d25b6adeca76490065a61c384a685c2c6504610` |
| `img/clean_os300__patologico_escaneado.png` | 495799 | `6648b0081cd36593cfe5e767b7cd471c34c3e5fdd50079cbc588ca768d0379c8` |
| `img/ctrlmagickdeskew__escaneado_d1.png` | 4339997 | `54d31483a9d6b6a589848e66bef2b729cb17afc4bc78ce9ccacb91026f3da1a9` |
| `img/ctrlmagickdeskew__escaneado_d2.png` | 4408043 | `0a359a06748b716d0f800fff00b8d3d2697e9f961a863f573a690befc16f6275` |
| `img/ctrlmagickdeskew__escaneado_d3.png` | 4548005 | `e14a3f190ea55c20ad07c3e43713c0a0c6789f8f9973d6c98a45db76ed4d0720` |
| `img/ctrlmagickdeskew__patologico_escaneado.png` | 4698616 | `d08dfc91e5fa2c0f1c0891b077f5e214d35d40cbf652572c6074355fa3dfe363` |
| `img/ctrlppp100__escaneado_d1.png` | 295504 | `e4e0be16927d78a36a6facd25d96f8c00dd19cc20489078cbeb153e2980732c5` |
| `img/ctrlppp100__escaneado_d2.png` | 318982 | `d2e8343959b8d8bf8b289613787cd858a44163e5252946d9ff16364af72f3681` |
| `img/ctrlppp100__escaneado_d3.png` | 364119 | `b9a78a23f485ee991f65698cc00e09029f5f39894ffc30b7a86ef9f41f3ca7d2` |
| `img/ctrlppp100__patologico_escaneado.png` | 1031747 | `122ecf4ef327c7608b7e4a5f8bfa45b2aa9087586fe4b733835be572ba19048c` |
| `img/ctrlppp150__escaneado_d1.png` | 592871 | `983ca635ca57881be9385f54c5e304d338421428655e1becdcaf6e59006fb8df` |
| `img/ctrlppp150__escaneado_d2.png` | 396259 | `701399f438745eafe05d5c6566f9557af73291f802cc91480ce645ff374d08cf` |
| `img/ctrlppp150__escaneado_d3.png` | 447327 | `6455e0fb0011e41073a2ac192c0d934ea04c4bd5b16ca0832ad22c1574edb8a8` |
| `img/ctrlppp150__patologico_escaneado.png` | 2265789 | `9da5a4c12577a976770bb9529ebb0af6849aa590db8af4958511c20f0bebb74e` |
| `img/ctrlppp200__escaneado_d1.png` | 711027 | `42d31587104065ea6ff115a7cfcd7249b717c793513a9ab105705a59fe20f876` |
| `img/ctrlppp200__escaneado_d2.png` | 431141 | `53e6fb2ff7a1ee8c299d95a3276c58ea68d27927d20016bfb4e8b8692f832749` |
| `img/ctrlppp200__escaneado_d3.png` | 486554 | `8f073993e717fca417320a90314053badf285375257991f7f843a14c71bea781` |
| `img/ctrlppp200__patologico_escaneado.png` | 4016393 | `6bcc3d2aba0ca7e111cd1d183b4f37ef41bca4b1d6be99c120614c29471bef7f` |
| `img/ctrlppp300__escaneado_d1.png` | 800995 | `8530b504350f7b75087f7fa91ff780ee3e60458633f0bafeddb1ee03ea85151a` |
| `img/ctrlppp300__escaneado_d2.png` | 485341 | `788260177a1ca5a80cd6b2dec522b2ac768f8bce5371e8f035a15a2b7f42b0fc` |
| `img/ctrlppp300__escaneado_d3.png` | 547755 | `d3f284df6f896a60d85eb0a3a604b45c9d9c986db72e129ed5b95dd2a21fdcbd` |
| `img/ctrlppp300__patologico_escaneado.png` | 5648022 | `7cbbe961c318ba3ece2516ea668ced276001043e2d37282a30c1aa22d2a58743` |
| `img/ctrlppp400__escaneado_d1.png` | 961556 | `375e6f769c9a537475e56ba52bf3e115fc85a05bbbc52f0256312313103931c7` |
| `img/ctrlppp400__escaneado_d2.png` | 543921 | `6ddde23c1fbadf8706670c474cfe9d8759da16210b5e280f73dfc94a13760317` |
| `img/ctrlppp400__escaneado_d3.png` | 615353 | `1d4cea8def5c88e7eeef6ac4c8101e27f301544c2a92bd543bbdd0ceb2594216` |
| `img/ctrlppp400__patologico_escaneado.png` | 5611886 | `979793bacbd12687515ad813b06bc4919897918afc0763953092a4f8fb966371` |
| `img/ctrlppp600__escaneado_d1.png` | 1005179 | `716194c06366bcc1bd3bc11af04101d6822dd201be90c0abfe756d8bb58a2f97` |
| `img/ctrlppp600__escaneado_d2.png` | 613051 | `f5306723177bdefd9c7267787d79abeb4b8d50a6fd8aa879dd5d6c8e811099f5` |
| `img/ctrlppp600__escaneado_d3.png` | 691608 | `8ad18f246f310f11cbecb4c973b750f6b2e6de40995a3006d85013b5c2c3fc61` |
| `img/ctrlppp600__patologico_escaneado.png` | 6151236 | `4805d0e36b7baf6eeb02796318c73bedc158945bf09cec55800b3e3e2e191ad7` |
| `img/deskew__escaneado_d1.png` | 750344 | `2ebdb8fa78b189d758617af3d62e68734e12019af83399c98c55a967565e4ce2` |
| `img/deskew__escaneado_d2.png` | 434291 | `fa34a5aca81e52a4705f4ae467aeccb7ee951ae581599837888fc9ad0587e37f` |
| `img/deskew__escaneado_d3.png` | 489018 | `2e30020f98cfaf17d7f0c58888830bc23c2a02f04bf8863007588fd9342d7cb5` |
| `img/deskew__patologico_escaneado.png` | 214041 | `74a93a961c36b3919c88ea0de632bcd30a121cb3c2b27fc7b1b48ac9f28a75c1` |
| `img/deskew_os300__escaneado_d1.png` | 874757 | `3001e362fdbcf0e76dc857425a9a7d066a260939fc8b8118493ebf2307022e45` |
| `img/deskew_os300__escaneado_d2.png` | 914930 | `a8a35ff0d0570c664c3bc139ebf78247a54753f7744d986dd4b35bd5afb7397f` |
| `img/deskew_os300__escaneado_d3.png` | 1057762 | `e0cd082fff63de760edcac2bab96916488c16f229395f34e034da3a4a269fe2d` |
| `img/deskew_os300__patologico_escaneado.png` | 692896 | `e259ca8a8273267aebb243893f7224b6b0a6a9c2eb0b577ab510c3fb1e5fbea3` |
| `img/os300__escaneado_d1.png` | 874754 | `1034ff327fa5003e146549064cfdaae2fc87775f50d4126e213e8bbaf7802373` |
| `img/os300__escaneado_d2.png` | 914928 | `23bbc4024ccbf7b537eb884f4fcbf9284139db8c7e182a0a256eee1015aa3588` |
| `img/os300__escaneado_d3.png` | 1057758 | `470125a7531f740cf76a693410891b4732e1ec76d4d182f98239cb8c7739fc55` |
| `img/os300__patologico_escaneado.png` | 692897 | `5ff53e40a657d1b8b9e67565b1f00c862768fec4a8e77d9f02554a6d8ea187ea` |
| `img/os400__escaneado_d1.png` | 923193 | `c9f69b48d79ecc7b6d57edbb9bd8e27b3cb5f13063e406e6dc1df402af0333f4` |
| `img/os400__escaneado_d2.png` | 933152 | `6a0601cd476acc7fa89f5c6edc85029830f47ff153a6b11f9a819e5ce50f56db` |
| `img/os400__escaneado_d3.png` | 1068346 | `ad698914d0d7d0225604085d30f393bf9536e7d134b02c747a3c4e4e77ebfbe0` |
| `img/os400__patologico_escaneado.png` | 1113060 | `b2fac12c37c2e77f1729f64453dca4cd4f042ceb77a750db34855af986a058ec` |
| `img/rotate__escaneado_d1.png` | 750343 | `b726d239935dfd85b1366876d1980b063eee001b8437f703917f4d7de5cb5d4f` |
| `img/rotate__escaneado_d2.png` | 434291 | `814c1f4514877f9c3e8667f8ddef1f00f58c573f5edc4f12a425cd190260495d` |
| `img/rotate__escaneado_d3.png` | 489018 | `a6f0a53327b580bbfd0bf7944537ab84014d08ba24f6fe5bd0ad71efd155d696` |
| `img/rotate__patologico_escaneado.png` | 214040 | `95e48f242744fc12cfcf268c743493a791621f281a361afe3bb23119296e8bc6` |
| `img/smoke_d3.png` | 489020 | `9dccdd004b287ed08a24b7530b8c39d5f771638d76090e395008ec8bc60bf9d4` |
| `img/todo__escaneado_d1.png` | 775094 | `b1f61e94dfd37f044f92e34fe86806e00290e5dc1a38a4e8996e1d8c079b1dd6` |
| `img/todo__escaneado_d2.png` | 434290 | `4349d2d14d5719fedefef276cf9e9d193db7330413ddab76271bd4fc87b7e8c1` |
| `img/todo__escaneado_d3.png` | 489017 | `eaf6cde553a489964e1dcca881976d42eb0adc102328325768ac35f3cc0b7c26` |
| `img/todo__patologico_escaneado.png` | 168967 | `44d49012ff86898a6f2d5cc961fbbd7cb3991cbc0b00fb1aae30eb7d5eee88a4` |
| `img2/m_ppp100__escaneado_d1.png` | 295504 | `41b8378d638c8c7a6fc2f6bdef6a168fdf5ec76aac1154c9f8f05f36ad1715ff` |
| `img2/m_ppp100__escaneado_d2.png` | 318982 | `2147df575dac96b4b29fb639b14d834417ea5754f89e3b80040710c8d7d3d75d` |
| `img2/m_ppp100__escaneado_d3.png` | 364119 | `33ea2095c0d0cac1639ab181e9eb1c43e54693898d5aef4a05f1e635fb18cf64` |
| `img2/m_ppp100__patologico_escaneado.png` | 1031747 | `845c88ed459ac7dcc751090a9a14d579dab653a672af60a106464635ca82dc36` |
| `img2/m_ppp100_ds__escaneado_d1.png` | 1164807 | `72dedd403cdec8d9e0f8d52bba187eb7dbe6929a86403b61aa8995f6b4cf404f` |
| `img2/m_ppp100_ds__escaneado_d2.png` | 1189692 | `e190d9de3bc75b205e1b04c244685a993231b91051d4f3c902acc2dbc14f22f1` |
| `img2/m_ppp100_ds__escaneado_d3.png` | 1230092 | `327672a7020a386b280260822aacce2c00bd2502210e40f1a45740ed9d8beadf` |
| `img2/m_ppp100_ds__patologico_escaneado.png` | 1194399 | `34ffc6a941b0aad8e5c5b90aa89ab761c841d9ba016b780b1a7438d498d400a7` |
| `img2/m_ppp125__escaneado_d1.png` | 434418 | `58c645451cd1769ed0c5bf21406d0869ba4a6466123358a1cd0262dfeb5809c9` |
| `img2/m_ppp125__escaneado_d2.png` | 366097 | `40efe6e7e4505a8bf2272521a88de8401997c4e2bd853abce2e4673fa2332bfe` |
| `img2/m_ppp125__escaneado_d3.png` | 414307 | `a786190f8a519309fcd62b80ea1bc30121d49f4c3e15b7b56df79e8cd8cdf315` |
| `img2/m_ppp125__patologico_escaneado.png` | 1582158 | `891222dd0e4fc8829a5aa987650437f3f4e87f9cf00263352d427ed33c7ddef4` |
| `img2/m_ppp125_ds__escaneado_d1.png` | 1795009 | `dc109ae64b01381ad608e6ad5b36a182bf837566fcdcb7419bf5314db287a4e9` |
| `img2/m_ppp125_ds__escaneado_d2.png` | 1808032 | `f6c0b1da93db547b04e1bdad60f45bdc9e21184e4c13abbb00d845dfcc1a6b45` |
| `img2/m_ppp125_ds__escaneado_d3.png` | 1873317 | `722c02d31ba19fbf7c1ac6c2f85241f866703ccff8c81cf066ea5d0b84e1c7da` |
| `img2/m_ppp125_ds__patologico_escaneado.png` | 1852326 | `b83554c312db63a92e5b8f3fe89b3d60396451a09ab455bf6f33cc5dda8b5d1f` |
| `img2/m_ppp150__escaneado_d1.png` | 592871 | `2749588334a61a189f2b176cef6744537035b6fba8df14fde708a70733b49b8c` |
| `img2/m_ppp150__escaneado_d2.png` | 396259 | `05f616de188cabb0e1adf1d333c541b96815e23cfe08953552d4cf247ad930dd` |
| `img2/m_ppp150__escaneado_d3.png` | 447327 | `b8cf4830b59426a06c913348407d07ccece241cbf44d0c3f68f55c7027541fef` |
| `img2/m_ppp150__patologico_escaneado.png` | 2265789 | `d22c77c0d5bf37ee96cc6d01a222f2a7d2ad53ac2f663389e880846831938e08` |
| `img2/m_ppp150_ds__escaneado_d1.png` | 2560584 | `1478178cfc826e9de9eaffe7068cad51566e1299693bfad93d53305e978f8800` |
| `img2/m_ppp150_ds__escaneado_d2.png` | 2549082 | `a13e3d81050f1fd7b33c8e60c0c7eadc283f125bef515438ca1ed882b6f13e43` |
| `img2/m_ppp150_ds__escaneado_d3.png` | 2636856 | `fd4fa2bb413a545b178ef9303476db75bf482a5297a87b4a2d7e949e506160f5` |
| `img2/m_ppp150_ds__patologico_escaneado.png` | 2656085 | `47d123771d679cf1d14c9ed458b77d5ce0d751cd17b158e2e9b5cd11b7887913` |
| `img2/m_ppp175__escaneado_d1.png` | 665214 | `b8496cb251aa1bc074da96adb0a55181153989fab90089b55838d875ff6ee99a` |
| `img2/m_ppp175__escaneado_d2.png` | 429003 | `fa84f8a61e0b95e9ddf5d434ea2d2ecbb2c75e4967302a3e330c5a2b47cccb15` |
| `img2/m_ppp175__escaneado_d3.png` | 478777 | `14dc75c3a9b320bb99d7808b85aac24089c911eb5d4600bd03b77867a9732c96` |
| `img2/m_ppp175__patologico_escaneado.png` | 3090321 | `5554da4e0b7ea6f6dca87a0d21615186509c2a06ff3fb0fe726d6eba6699a663` |
| `img2/m_ppp175_ds__escaneado_d1.png` | 3398324 | `f83be5d4b26957f167b1ebfee3e22cd648ce2a6190c162f6d348c6ad90f5a412` |
| `img2/m_ppp175_ds__escaneado_d2.png` | 3412992 | `6216217611eb5bd92716d521eb2c845cb3b50d1d500eabdb3aea9b78ee079ec2` |
| `img2/m_ppp175_ds__escaneado_d3.png` | 3526456 | `a2f4955e3f26e23ce1a77797685d0368113c0d384c4528f5adc0baae7ebf1218` |
| `img2/m_ppp175_ds__patologico_escaneado.png` | 3608500 | `c3d8d6eb21a4934bd7a2b77c3f89ac286471997ed41a24d6a2b90a6ccc82a5ff` |
| `img2/m_ppp200__escaneado_d1.png` | 711027 | `976901dcee2e26ccb37a67a7dc3a38a48f23e5d0a5f3586557591e91920018ca` |
| `img2/m_ppp200__escaneado_d2.png` | 431141 | `f4f5d545c6c2ec800be785a87616647ad0568ed66d010b8bd452c34f9825e850` |
| `img2/m_ppp200__escaneado_d3.png` | 486554 | `cd0f75626df3717916ddaec89acc002dfb2331ed953b9e20f8ae7fcec0cbc88c` |
| `img2/m_ppp200__patologico_escaneado.png` | 4016393 | `f08a1e16bc2e0702b58e5a21e6f367d0b3cc43e7af8320df09b3d96ae868c60e` |
| `img2/m_ppp200_ds__escaneado_d1.png` | 4339997 | `4590fdcc71bbfb5d4bd404f3785bf4af2b5fda639795008cf4234a4099282922` |
| `img2/m_ppp200_ds__escaneado_d2.png` | 4408043 | `d9c8df532a745ddc458760789dad979d35b4bd73ba0760eb5dd21057c936b51b` |
| `img2/m_ppp200_ds__escaneado_d3.png` | 4548005 | `ab75c6aed8b9ec9b966cc67efd3cf1322e28fa13e84a18c1f65526de1bf3e3b0` |
| `img2/m_ppp200_ds__patologico_escaneado.png` | 4698616 | `2196f06b8dbd4c33da665148cf7534100e890e58ffa22bd3dcb0e84046cdfe51` |
| `img2/m_ppp250__escaneado_d1.png` | 794793 | `ee6f65360fc00a2114a68e0cf8489d9b3246dec32fcf063bf626c73492f5500f` |
| `img2/m_ppp250__escaneado_d2.png` | 492692 | `caa8a292f8c690409be5b42d62e81abb8a388339c330ec3484b9f5f138e8d61c` |
| `img2/m_ppp250__escaneado_d3.png` | 552480 | `711aa1b95bfbc49beebea02801e60e4f7523c14ac87094ade5403de558804451` |
| `img2/m_ppp250__patologico_escaneado.png` | 5296386 | `1d865eca39ab566f314ffa1ab05dc884a3b27f6e55976ac40e20628a562492b5` |
| `img2/m_ppp250_ds__escaneado_d1.png` | 6582218 | `5bfeb5d5e3fb7476d641c7df565b96f8b254432fb74286f031662add09a90452` |
| `img2/m_ppp250_ds__escaneado_d2.png` | 6608088 | `dd8e7fa2a2b68be04e3b75d91251929fcc31244656ab6bfd07f07ccca820ab3f` |
| `img2/m_ppp250_ds__escaneado_d3.png` | 6859508 | `9ea114eddb0ab39304cbb0ee581f66b2a6d0737073448df582910ece029e8a02` |
| `img2/m_ppp250_ds__patologico_escaneado.png` | 7149251 | `fc92acd5fbb6de65d9d12e0635039b1aae4e852e84b23b0e36a012c703b4e2a0` |
| `img2/m_ppp300__escaneado_d1.png` | 800995 | `0a375449d671ada14689b9298cd35fca92e4fb1b44fb35599ac9e0c3bff2f144` |
| `img2/m_ppp300__escaneado_d2.png` | 485341 | `2cbe130ab1c218367c3070ca3b466e365677ae97941c4565cac834af297deda1` |
| `img2/m_ppp300__escaneado_d3.png` | 547755 | `19f85cb9c4c65887f47bb4368ede3bb7866fa39086e7d4ee6ab53082ec65e655` |
| `img2/m_ppp300__patologico_escaneado.png` | 5648022 | `8b44deff06125d9c666d4d4b3feb80f91f09905094476a0a065b50c6b3ed86ab` |
| `img2/m_ppp300_ds__escaneado_d1.png` | 9282306 | `817b40126df9dd721e93ed9344292e3e8dcd23a826f286c2ed2c168bcb704f2c` |
| `img2/m_ppp300_ds__escaneado_d2.png` | 9259206 | `fae93a6165441050018ef0b165a1a2b004a97fc7ae710e09e95c06ae946e732d` |
| `img2/m_ppp300_ds__escaneado_d3.png` | 9638505 | `86cd5ed19fead4730b069d51671bd6feeb402faee864e764389018e2cb4b3ef8` |
| `img2/m_ppp300_ds__patologico_escaneado.png` | 10064421 | `b423190efda2933c2f73551fc45bec3e7150e91faa46f512acf893f089837346` |
| `img2/m_ppp75__escaneado_d1.png` | 177714 | `7048e79a9befdf5737954db48d2fa589dd5956df442fd8f7308ca9360d79b776` |
| `img2/m_ppp75__escaneado_d2.png` | 191485 | `9a7c3c6cc3c844bb603ca9e24e88456afc8833eadd5d81d7f8d367c161d29007` |
| `img2/m_ppp75__escaneado_d3.png` | 217118 | `c120cf1ae9486bd349ec07315f039b74c1eff8c0d1bede398f70ef376d5a9b1a` |
| `img2/m_ppp75__patologico_escaneado.png` | 584837 | `faab29e4dcd4ff240447eaea8bcef412978664bbb3c1052ba5559036bf9a57c4` |
| `img2/m_ppp75_ds__escaneado_d1.png` | 661054 | `6d181f4950f331a1c405dd1f9d54c41b0bf5b6086f63e5d0472208e6566788de` |
| `img2/m_ppp75_ds__escaneado_d2.png` | 678036 | `ced1f02b489353ba4667d2478286383ad850fea79176af94b3719a29388d1b12` |
| `img2/m_ppp75_ds__escaneado_d3.png` | 700891 | `ac7e47129ff7494a4950089ec5f2682f2566afd9d4cad6263ac63bc2a8270961` |
| `img2/m_ppp75_ds__patologico_escaneado.png` | 675986 | `0b316afedf5278a8ec7599c4be3e3e8f8b36c1fde507e30041a22319cf49a5b5` |
| `img2/nat__escaneado_d1.png` | 592582 | `e22bfe46910ecd891b704fa35f696b7bf1f7ff7d9fe75a7f150205acd4469b20` |
| `img2/nat__escaneado_d2.png` | 319625 | `af608352a3a93c6d492be271de7131959dcd8b41be97c51c187d89c00d933acb` |
| `img2/nat__escaneado_d3.png` | 365078 | `1c96e24f25073a8252fe65512d4d4d45116aea974461777dc9c1d2b5b3a3bdfc` |
| `img2/nat__patologico_escaneado-001.png` | 1180134 | `21559cfc1c797c0cb395f186cf6f34810eeb9818118c9531819a1568f975d33f` |
| `img2/nat__patologico_escaneado.png` | 3536149 | `3852e7e10105aac6c8be24b8d74ab9db3566af07ef5ecd49b29ff53484d2a87f` |
