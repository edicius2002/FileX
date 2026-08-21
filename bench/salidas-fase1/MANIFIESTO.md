# Manifiesto — salidas-fase1

**Generado:** 2026-08-20  
**Ficheros:** 71  ·  **Peso:** 829.7 MB

Salidas de la fase de medición en GPU. Son **artefactos de medición, no evidencia**:
lo que sostiene las conclusiones es el informe `bench/gpu-fase1.md` y los logs, que sí se
conservan versionados.

## Cómo regenerarlo

```bash
# desde la raíz del proyecto
bash bench/scripts/bench_nvenc.sh
bash bench/scripts/bench_calidad.sh
bash bench/scripts/bench_nvenc_repeticion.sh
```

**Aviso:** requieren GPU y el lock de `bench/lib/harness.sh`. Los **tiempos** no se
reproducen exactamente (la sesión de escritorio remoto los etiqueta `SUCIA`); los
**ficheros** sí.

## Inventario

| Fichero | Bytes | sha256 |
|---|---:|---|
| `ia/docling_cpu_resumen.json` | 708 | `d7d79760bec035ae…` |
| `ia/docling_cuda_resumen.json` | 712 | `179d3829d667681a…` |
| `ia/tipico_audio.flac` | 1004509 | `2c3c9031c3a18f89…` |
| `ia/verificacion_ocr.json` | 1220 | `43df49fc89718f86…` |
| `ia/whisper_distil-large-v3_habla_jfk.txt` | 108 | `d5607440635b0e07…` |
| `ia/whisper_distil-large-v3_habla_largo.txt` | 3500 | `878f3637cd941929…` |
| `ia/whisper_distil-large-v3_resumen.json` | 2262 | `14917bcf9b61037f…` |
| `ia/whisper_distil-large-v3_tipico_flac.txt` | 13 | `810d7c3ca6aa6411…` |
| `ia/whisper_distil-large-v3_tipico_mp3.txt` | 7 | `37bf4052b560cb27…` |
| `ia/whisper_distil-large-v3_trivial_wav.txt` | 13 | `810d7c3ca6aa6411…` |
| `ia/whisper_distil-large-v3_video_tipico_audio.txt` | 9 | `04ccc17622b2c31f…` |
| `ia/whisper_large-v3_habla_jfk.txt` | 108 | `37d003a932256f11…` |
| `ia/whisper_large-v3_habla_largo.txt` | 3049 | `2f6438765a5c06cb…` |
| `ia/whisper_large-v3_resumen.json` | 2174 | `8546feb03ebb2240…` |
| `ia/whisper_large-v3_tipico_flac.txt` | 20 | `52109063f19c9a4f…` |
| `ia/whisper_large-v3_tipico_mp3.txt` | 20 | `52109063f19c9a4f…` |
| `ia/whisper_large-v3_trivial_wav.txt` | 20 | `52109063f19c9a4f…` |
| `ia/whisper_large-v3_video_tipico_audio.txt` | 23 | `022c6057c8515f1b…` |
| `video/1080p_deccpu.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/1080p_decgpu.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/1080p_hevcnvenc.mp4` | 8270080 | `c35cab8e0471c4ec…` |
| `video/1080p_nvenc.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/1080p_x264.mp4` | 12619413 | `a4c9247de9e8fa65…` |
| `video/1080p_x265.mp4` | 7619256 | `0c8f5408baf0b2df…` |
| `video/4k_a_1080_cpu.mp4` | 7010894 | `df35ca607e0cdecc…` |
| `video/4k_a_1080_gpu.mp4` | 7095415 | `d810e5457be99afe…` |
| `video/4k_deccpu.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/4k_decgpu.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/4k_nvenc.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/4k_x264.mp4` | 25897317 | `1b786cbf64758306…` |
| `video/act_nvenc.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/coex_nvenc.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/r_1080_deccpu.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/r_1080_decgpu.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/r_1080_hevcnvenc.mp4` | 8270080 | `c35cab8e0471c4ec…` |
| `video/r_1080_nvenc.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/r_1080_x264.mp4` | 12619413 | `a4c9247de9e8fa65…` |
| `video/r_1080_x265.mp4` | 7619256 | `0c8f5408baf0b2df…` |
| `video/r_4k1080_cpu.mp4` | 7010894 | `df35ca607e0cdecc…` |
| `video/r_4k1080_gpu.mp4` | 7095415 | `d810e5457be99afe…` |
| `video/r_4k_deccpu.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/r_4k_decgpu.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/r_4k_nvenc.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/r_4k_x264.mp4` | 25897317 | `1b786cbf64758306…` |
| `video/r_full_cpu.mp4` | 12856340 | `98fca5356bd492ce…` |
| `video/r_full_gpu.mp4` | 13788701 | `101179f542d9b202…` |
| `video/r_pat_cpu.mkv` | 3976364 | `e90eb54a2843f949…` |
| `video/r_pat_gpu.mkv` | 4465814 | `bd9447b372ef0fa4…` |
| `video/vram1.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/vram2.mp4` | 8270080 | `c35cab8e0471c4ec…` |
| `video/vram3.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/vram4.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/vram5a.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/vram5b.mp4` | 26030592 | `dfbe19206d2052a1…` |
| `video/calidad/hevcnvenc_3M.mp4` | 8270080 | `c35cab8e0471c4ec…` |
| `video/calidad/hevcnvenc_6M.mp4` | 16211872 | `f29e0a7b0aee9257…` |
| `video/calidad/hevcnvencp7_3M.mp4` | 8214686 | `d6062a827ff18184…` |
| `video/calidad/hevcnvencp7_6M.mp4` | 16367220 | `2785078c70a75699…` |
| `video/calidad/nvenc_10M.mp4` | 26962505 | `8efad648bfc56945…` |
| `video/calidad/nvenc_2M.mp4` | 5536012 | `a394b01c1c49a996…` |
| `video/calidad/nvenc_4k.mp4` | 27954975 | `2e29b1e9b82c9580…` |
| `video/calidad/nvenc_5M.mp4` | 13551798 | `96d0ae17958b9f50…` |
| `video/calidad/nvencp7_10M.mp4` | 27063833 | `9c1897633e3f8f72…` |
| `video/calidad/nvencp7_2M.mp4` | 5401579 | `d6e4a8d337c5764c…` |
| `video/calidad/nvencp7_5M.mp4` | 13242914 | `fa7ce6c952037fdb…` |
| `video/calidad/x264_10M.mp4` | 25058130 | `ad97e3d13f8880c2…` |
| `video/calidad/x264_2M.mp4` | 5065221 | `435011b708b81fc2…` |
| `video/calidad/x264_4k.mp4` | 25897317 | `1b786cbf64758306…` |
| `video/calidad/x264_5M.mp4` | 12619413 | `a4c9247de9e8fa65…` |
| `video/calidad/x265_3M.mp4` | 7619256 | `0c8f5408baf0b2df…` |
| `video/calidad/x265_6M.mp4` | 15201470 | `6d46f988b0826560…` |
