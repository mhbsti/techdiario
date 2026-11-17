---
name: techdiario-thumbnail-maker
description: Gera thumbnails 1280x720 via Qwen-Image-2.1-GGUF local.
version: 1.1.0
author: TECH DIARIO
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [thumbnail, qwen-image, gguf, youtube, techdiario, design]
    related_skills: [videocardz-news-hunter, techdiario-pauta-generator]
---

# TECH DIÁRIO - Gerador Local de Thumbnails Exclusivas (`Qwen-Image-2.1-GGUF`)

## When to Use
Use esta Skill sempre que precisar gerar uma **capa de vídeo exclusiva (thumbnail 1280x720)** para uma pauta do canal **TECH DIÁRIO**, utilizando o motor local `qwen-image-2.1-Q3_K_XL.gguf` e os ativos da pasta `CANAL TECH DIARIO` (`/opt/assets`).

## Regra de Ouro: Capas 100% Exclusivas por Tema
Nunca reutilize o mesmo prompt ou o mesmo estilo visual entre pautas diferentes! Cada tema deve ter:
1. **Cenário Visual Próprio (`--prompt`):** Descreva elementos específicos daquela notícia (ex: caixas de carga no aeroporto com faixa de alerta para roubo de carga; bancada branca gelo minimalista para placa triple-fan branca; colisão de energia vermelha Radeon vs verde GeForce para notícias AMD vs NVIDIA).
2. **Template de Layout & Ativo (`--theme-style`):**
   - `alert`: Para notícias urgentes, roubos, polêmicas de preço ou alertas. Usa a foto real **`EU.jpg`** em medalhão neon na **esquerda**, texto 3D em **Amarelo Alerta + Vermelho Fogo** na **direita**, e `LOGO SIMPLES.png` no **topo direito**.
   - `nvidia_ice`: Para lançamentos de GPUs, reviews e hardware. Usa o avatar **`EU COM LOGO.png`** na **direita**, texto 3D em **Branco + Ciano/Verde** na **esquerda**, e `LOGO SIMPLES.png` no **topo esquerdo**.
   - `versus`: Para comparativos, mods (ex: DLSS na AMD), disputas de mercado. Posiciona o texto 3D no **topo esquerdo** em **Laranja Radeon + Verde GeForce**, foto **`EU.jpg`** na **direita** e `LOGO SIMPLES.png` no **canto inferior esquerdo**.

## Procedure
Execute o script `make_thumb.py` especificando `--prompt`, `--headline`, `--badge`, `--subfolder` e `--theme-style`:
```bash
python3 /opt/data/skills/techdiario/techdiario-thumbnail-maker/scripts/make_thumb.py \
  --prompt "Dark airport cargo warehouse at night with wooden shipping pallets, yellow police caution tape, glowing green RTX 5090 graphics card box opened, dramatic red and yellow siren lighting, cinematic 8k" \
  --headline "SUMIU NO BRASIL!" \
  --badge "R$ 2,7 MILHÕES EM RTX 5090" \
  --theme-style "alert" \
  --subfolder "2026-10-18_rtx-5090-roubadas-brasil"
```
