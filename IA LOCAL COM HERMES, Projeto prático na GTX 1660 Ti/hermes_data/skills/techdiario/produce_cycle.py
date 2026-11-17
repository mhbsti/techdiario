#!/usr/bin/env python3
"""
Orquestrador Completo do Ciclo TECH DIÁRIO (v2.0 Estável)
Executa em esteira determinística com importação direta dos módulos:
1. Multi-Tech News Hunter (6 Portais + Qdrant + qwen2.5:1.5b)
2. Gerador de Pautas e Roteiros (qwen2.5:3b)
3. Renderizador de Capas Exclusivas (make_thumb.py + Qwen-Image + Pillow)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

SKILLS_DIR = Path("/opt/data/skills/techdiario")
sys.path.append(str(SKILLS_DIR / "multi-tech-news-hunter" / "scripts"))
sys.path.append(str(SKILLS_DIR / "techdiario-pauta-generator" / "scripts"))
sys.path.append(str(SKILLS_DIR / "techdiario-thumbnail-maker" / "scripts"))

try:
    from multi_news_hunter import run_pipeline
    from generate_pauta import produce_pauta_for_article, WRITER_MODEL
    from make_thumb import unload_and_wait_vram, API_BASE
except Exception as e:
    print(f"Erro ao importar módulos: {e}", file=sys.stderr)


def run_full_cycle(
    top_count: Optional[int] = None,
    all_day: bool = False,
    overlay_avatar: bool = False,
    max_per_source: Optional[int] = None,
    skip_thumbs: bool = False,
):
    t_start = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    is_all = all_day or (top_count is None or top_count <= 0)
    top_label = "TODAS AS PAUTAS DO DIA" if is_all else f"TOP {top_count} PAUTA(S)"

    print("=" * 75, flush=True)
    print(f"🎬 INICIANDO PIPELINE EM ESTEIRA TECH DIÁRIO ({today_str})", flush=True)
    print(f"📌 MODO: {top_label} | ARQUITETURA: BATCH EM 4 FASES (SEM MODEL THRASHING)", flush=True)
    print("=" * 75, flush=True)

    # =========================================================================
    # FASE 1: Coleta Multi-Portal & Agrupamento Semântico no Qdrant
    # Modelos: nomic-embed-text (335MB) + qwen2.5:1.5b (1.2GB)
    # =========================================================================
    t_fase1 = time.time()
    print(f"\n🌐 [Fase 1/4] Varrendo os 6 portais e agrupando matérias de hoje...", flush=True)
    hunter_top_k = None if is_all else top_count
    hunter_res = run_pipeline(
        top_k=hunter_top_k,
        only_today=True,
        use_llm_filter=True,
        max_per_source=max_per_source,
    )
    articles = hunter_res.get("articles", [])
    fase1_elapsed = round(time.time() - t_fase1, 1)

    if not articles:
        print("⚠️ Nenhuma matéria aprovada encontrada pelos filtros de relevância do dia.", flush=True)
        return

    print(f"✅ [Fase 1/4 Concluída em {fase1_elapsed}s] {len(articles)} pauta(s) selecionada(s)!", flush=True)

    # =========================================================================
    # FASE 2: Geração de Todas as Pautas em Sequência Contínua (Ollama Aquecido)
    # Modelo: WRITER_MODEL mantido 100% residente em VRAM
    # =========================================================================
    t_fase2 = time.time()
    print(f"\n✍️ [Fase 2/4] Gerando TODOS os {len(articles)} roteiros em lote contínuo ({WRITER_MODEL})...", flush=True)
    pautas_queue = []

    for idx, art in enumerate(articles, start=1):
        t_p0 = time.time()
        print(f"  [{idx}/{len(articles)}] Redigindo: {art.get('title')[:60]}...", flush=True)
        pauta_meta = produce_pauta_for_article(art)
        p_elapsed = round(time.time() - t_p0, 1)

        print(f"      ↳ Salvo em {p_elapsed}s: output/{pauta_meta['subfolder']}/pauta_roteiro.md", flush=True)

        pautas_queue.append({
            "idx": idx,
            "title": art.get("title"),
            "primary_source": art.get("primary_source"),
            "url": art.get("primary_url"),
            "image_url": pauta_meta.get("image_url") or art.get("primary_image_url") or art.get("image_url"),
            "relevance": art.get("nota_relevancia_br", 75),
            "subfolder": pauta_meta["subfolder"],
            "pauta_path": pauta_meta["pauta_path"],
            "headline": pauta_meta["headline_capa"],
            "badge": pauta_meta["badge_capa"],
            "theme_style": pauta_meta["theme_style"],
            "prompt_capa": pauta_meta["prompt_arte_capa"],
            "has_thumb": False,
        })

    fase2_elapsed = round(time.time() - t_fase2, 1)
    avg_pauta = round(fase2_elapsed / max(1, len(articles)), 1)
    print(f"✅ [Fase 2/4 Concluída em {fase2_elapsed}s] {len(pautas_queue)} roteiros gerados (média {avg_pauta}s/pauta)!", flush=True)

    # =========================================================================
    # FASE 3: Transição de Recursos de Hardware (Liberação ÚNICA de VRAM)
    # Evita o swap contínuo de modelos na GPU
    # =========================================================================
    t_fase3 = time.time()
    print(f"\n🔄 [Fase 3/4] Hardware Gate: Descarregando modelos do Ollama da VRAM (1 única vez)...", flush=True)
    unload_and_wait_vram(max_wait_seconds=20)
    fase3_elapsed = round(time.time() - t_fase3, 1)
    print(f"✅ [Fase 3/4 Concluída em {fase3_elapsed}s] Memória da GPU 100% liberada para renderização!", flush=True)

    # =========================================================================
    # FASE 4: Renderização de Todas as Capas em Lote (Qwen-Image / Pillow)
    # =========================================================================
    t_fase4 = time.time()
    thumb_script = SKILLS_DIR / "techdiario-thumbnail-maker" / "scripts" / "make_thumb.py"

    if not skip_thumbs:
        print(f"\n🎨 [Fase 4/4] Renderizando {len(pautas_queue)} thumbnails em lote contínuo...", flush=True)
        for idx, item in enumerate(pautas_queue, start=1):
            t_t0 = time.time()
            print(f"  [{idx}/{len(pautas_queue)}] Capa '{item['theme_style']}': {item['headline']} ({item['badge']})...", flush=True)

            thumb_cmd = [
                sys.executable,
                str(thumb_script),
                "--prompt", item["prompt_capa"],
                "--headline", item["headline"],
                "--badge", item["badge"],
                "--theme-style", item["theme_style"],
                "--subfolder", item["subfolder"],
                "--skip-vram-unload",
            ]
            if item.get("image_url"):
                thumb_cmd.extend(["--image-url", item["image_url"]])
            if overlay_avatar:
                thumb_cmd.append("--overlay-avatar")

            try:
                proc = subprocess.run(thumb_cmd, capture_output=True, text=True, timeout=1200)
                if proc.returncode == 0:
                    t_item_elapsed = round(time.time() - t_t0, 1)
                    item["has_thumb"] = True
                    print(f"      ↳ Capa concluída em {t_item_elapsed}s: output/{item['subfolder']}/capa_youtube_1280x720.png", flush=True)
                else:
                    print(f"      ⚠️ Falha ao renderizar capa: {proc.stderr[-300:].strip()}", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print(f"      ⚠️ Timeout de geração da capa '{item['subfolder']}'.", file=sys.stderr)
            except Exception as e:
                print(f"      ⚠️ Erro inesperado: {e}", file=sys.stderr)
        fase4_elapsed = round(time.time() - t_fase4, 1)
        print(f"✅ [Fase 4/4 Concluída em {fase4_elapsed}s] Lote de thumbnails finalizado!", flush=True)
    else:
        fase4_elapsed = 0.0
        print("\n🎨 [Fase 4/4] Renderização de capas pulada via --skip-thumbs.", flush=True)

    # =========================================================================
    # FASE 5: Compilação do Relatório e Índice Diário (PAUTAS_DO_DIA.md)
    # =========================================================================
    output_root = Path(os.getenv("OUTPUT_DIR", "/opt/output"))
    index_md_path = output_root / f"{today_str}_PAUTAS_DO_DIA.md"
    try:
        lines = [
            f"# 📺 TECH DIÁRIO — Pautas do Dia ({today_str})\n",
            f"**Total de Matérias Analisadas:** {hunter_res.get('total_collected', 0)} matérias coletadas nos 6 portais.\n",
            f"**Pautas Únicas Aprovadas:** {len(pautas_queue)}\n",
            f"**Tempo de Execução:** Fase 1 ({fase1_elapsed}s) | Fase 2 ({fase2_elapsed}s) | Fase 3 ({fase3_elapsed}s) | Fase 4 ({fase4_elapsed}s)\n\n",
            "| # | Chamada Capa | Badge | Tema / Título Original | Fonte | Relevância | Pasta de Saída |",
            "| :-: | :--- | :--- | :--- | :--- | :-: | :--- |",
        ]
        for r in pautas_queue:
            thumb_badge = "🖼️ Capa OK" if r["has_thumb"] else "📝 Roteiro"
            lines.append(
                f"| {r['idx']} | **{r['headline']}** | `{r['badge']}` | [{r['title']}]({r['url']}) | {r['primary_source']} | {r['relevance']}/100 | [`{r['subfolder']}`]({r['subfolder']}/) ({thumb_badge}) |"
            )
        lines.append("\n---\n*Gerado automaticamente pelo Hermes Agent TECH DIÁRIO v2.0 (Pipeline em Lote).*")
        with open(index_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n📋 Índice diário consolidado salvo em: {index_md_path}", flush=True)
    except Exception as exc:
        print(f"Aviso ao salvar índice diário: {exc}", file=sys.stderr)

    total_elapsed = round(time.time() - t_start, 1)
    print("\n" + "=" * 75, flush=True)
    print(f"🎉 CICLO FINALIZADO COM SUCESSO EM {total_elapsed}s ({len(pautas_queue)} PAUTAS)", flush=True)
    print(f"⏱️ Métricas: Hunter={fase1_elapsed}s | Roteiros={fase2_elapsed}s | VRAM Flush={fase3_elapsed}s | Capas={fase4_elapsed}s", flush=True)
    print("=" * 75, flush=True)
    for r in pautas_queue:
        thumb_icon = "🖼️" if r["has_thumb"] else "📝"
        print(f"  {thumb_icon} output/{r['subfolder']}/ -> {r['headline']} ({r['badge']}) [{r['primary_source']}]")


def main():
    parser = argparse.ArgumentParser(description="Orquestrador Estável do Ciclo TECH DIÁRIO")
    parser.add_argument("-t", "--top", type=str, default="1", help="Quantidade de pautas ('all' ou número)")
    parser.add_argument("-a", "--all", action="store_true", help="Gera pautas e capas para TODAS as notícias do dia")
    parser.add_argument("-o", "--overlay-avatar", action="store_true", help="Força foto do apresentador na capa")
    parser.add_argument("-m", "--max-per-source", type=int, default=None, help="Limite por portal (padrão: sem limite)")
    parser.add_argument("--writer-model", type=str, default=None, help="Modelo redator no Ollama (padrão: qwen3.5:9b)")
    parser.add_argument("--skip-thumbs", action="store_true", help="Gera apenas os roteiros sem renderizar as capas")
    args = parser.parse_args()

    if args.writer_model:
        os.environ["WRITER_MODEL"] = args.writer_model

    top_count = None
    if not args.all:
        if args.top.lower() in ("all", "0", "tudo"):
            top_count = None
        else:
            try:
                top_count = int(args.top)
            except ValueError:
                top_count = 1

    run_full_cycle(
        top_count=top_count,
        all_day=args.all or (top_count is None),
        overlay_avatar=args.overlay_avatar,
        max_per_source=args.max_per_source,
        skip_thumbs=args.skip_thumbs,
    )


if __name__ == "__main__":
    main()

