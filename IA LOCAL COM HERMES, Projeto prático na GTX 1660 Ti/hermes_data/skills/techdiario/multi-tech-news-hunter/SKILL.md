---
name: multi-tech-news-hunter
description: Varre em tempo real os 6 maiores portais de tecnologia e jogos (TechPowerUp, TechSpot, Adrenaline, PC Gamer, Tom's Hardware e VideoCardz), gera embeddings semânticos com nomic-embed-text, deduplica matérias no banco vetorial Qdrant e classifica relevância para o público brasileiro com qwen2.5:1.5b.
category: techdiario
tools:
  - run_command
---

# Multi-Tech News Hunter (6 Portais + Vector DB + Classificador Rápido)

Esta skill permite ao **Hermes Agent** coletar, vetorizar e ranquear notícias de tecnologia cobrindo toda a cena global e nacional:

- **TechPowerUp** (Hardware aprofundado, BIOS, GPUs)
- **TechSpot** (Análises técnicas e benchmarks)
- **Adrenaline** (Portal de referência no Brasil, preços nacionais e mercado)
- **PC Gamer** (Tendências de jogos, drivers e mods de PC)
- **Tom's Hardware** (Lançamentos de CPUs, memórias e arquiteturas)
- **VideoCardz** (Vazamentos e datas de placas de vídeo)

## Como Usar

### 1. Extrair TODAS as notícias do dia de cada portal (sem limite):
```bash
python3 /opt/data/skills/techdiario/multi-tech-news-hunter/scripts/multi_news_hunter.py --all
```

### 2. Extrair as TOP N matérias mais relevantes do dia:
```bash
python3 /opt/data/skills/techdiario/multi-tech-news-hunter/scripts/multi_news_hunter.py --limit 5
```

### 3. Rodar ciclo completo determinístico de pautas e capas:
```bash
# Todas as pautas e capas do dia:
python3 /opt/data/skills/techdiario/produce_cycle.py --all

# Top 5 pautas e capas do dia:
python3 /opt/data/skills/techdiario/produce_cycle.py --top 5

# Roteirizar todas as pautas rapidamente sem renderizar capas:
python3 /opt/data/skills/techdiario/produce_cycle.py --all --skip-thumbs
```

O comando retornará um JSON estruturado com:
- `title`: Título da matéria
- `primary_source`: Portal de origem
- `related_sources`: Outros portais que cobriram a mesma notícia (agrupados pelo Qdrant)
- `combined_score`: Pontuação final
- `nota_relevancia_br`: Nota de 0 a 100 dada pelo classificador `qwen2.5:1.5b`
- `categoria`: Segmento (`gpu`, `cpu`, `driver_ai`, etc.)
- `theme_style_sugerido`: Estilo de thumbnail (`alert`, `nvidia_ice` ou `versus`)
- `motivo_editorial`: Justificativa do porquê o tema rende visualizações no TECH DIÁRIO

