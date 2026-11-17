---
name: techdiario-pauta-generator
description: Gera pautas, titulos e roteiros YouTube para o TECH DIARIO.
version: 1.0.0
author: TECH DIARIO
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [youtube, techdiario, roteiro, seo, hardware, ia]
    related_skills: [videocardz-news-hunter, techdiario-thumbnail-maker]
---

# TECH DIÁRIO - Gerador de Pautas e Roteiros de Alto CTR

## When to Use
Use esta Skill após coletar notícias do **VideoCardz.com** (com `videocardz-news-hunter`) para criar sugestões de vídeo, títulos magnéticos, roteiro completo de gravação e metadados de SEO para o canal **TECH DIÁRIO** (`https://www.youtube.com/@techdiario`).

## Procedure
1. Leia o guia de estilo em `/opt/data/skills/techdiario/techdiario-pauta-generator/references/guia_estilo_techdiario.md` e as memórias em `/opt/data/memories/USER.md` e `/opt/data/memories/MEMORY.md`.
2. Para cada notícia principal selecionada, crie uma subpasta organizada por data e slug em `/opt/output/YYYY-MM-DD_slug-do-tema/`.
3. Salve o arquivo `pauta_roteiro.md` dentro dessa subpasta contendo obrigatoriamente:
   - **3 Opções de Título YouTube (Alto CTR):** Estilo direto, com valores estimados em Reais (R$) ou choque técnico (ex: VRAM, preço, comparativo com placas populares/usadas).
   - **Texto Curto para a Capa (2 a 4 palavras):** Exatamente o texto que será enviado para a Skill `techdiario-thumbnail-maker` renderizar em 3D.
   - **Gancho de Abertura (0:00 a 0:40):** Sem enrolação, mostrando por que a notícia importa para quem mexe com PC, Jogos ou IA Local no Brasil.
   - **Inserção do Patrocinador Oficial:**
     > *"E antes de continuar: se você quer economizar de verdade, passe na **GATO MERCOSUL**! Use o cupom **TD5** e ganhe **5% de desconto** em qualquer produto no site `www.gatomercosul.com.br`!"*
   - **Desenvolvimento Técnico (Pilares IA · MERCADO · CARREIRA):** Explicação clara das especificações do VideoCardz + impacto prático (ex: rodar modelos GGUF no `llama.cpp`, custo por frame, longevidade da VRAM).
   - **Veredito Sincero TECH DIÁRIO ("Vale o investimento ou é cilada?") + Pergunta de Engajamento para os Comentários.**
   - **Descrição Completa do Vídeo + 15 Tags de SEO.**
4. Em seguida, chame obrigatoriamente a Skill `techdiario-thumbnail-maker` passando o `headline_text`, `badge_text` e a pasta de saída criada.

## Pitfalls to Avoid
- Nunca esqueça de incluir o cupom **TD5** da **Gato Mercosul** na pauta e na descrição do vídeo.
- Não faça traduções literais robóticas do inglês; adapte para o vocabulário real do público brasileiro de hardware e IA local.

