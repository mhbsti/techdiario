#!/usr/bin/env python3
"""
Gerador de Pautas e Roteiros de Alto CTR para o Canal TECH DIÁRIO.
Utiliza o modelo qwen2.5:3b via Ollama API para redigir roteiros completos,
títulos magnéticos, ganchos e metadados de SEO para YouTube.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
WRITER_MODEL = os.getenv("WRITER_MODEL", "qwen3.5:9b")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/opt/output"))


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")[:45]


def generate_pauta_content(article: dict) -> dict:
    title = article.get("title", "")
    source = article.get("primary_source", article.get("source", "Portal Tech"))
    url = article.get("primary_url", article.get("url", ""))
    summary = article.get("summary", "")
    original_text = article.get("original_text", summary)
    categoria = article.get("categoria", "hardware")
    entidades = article.get("entidades", [])
    motivo = article.get("motivo_editorial", "")
    lang = article.get("lang", "en")
    is_english = (lang.lower().startswith("en") or source in ["TechPowerUp", "TechSpot", "PC Gamer", "Tom's Hardware", "VideoCardz"])

    translation_block = ""
    if is_english:
        translation_block = """5. '## 🌐 Tradução da Notícia Completa para o Português (pt-BR)'
   - Traduza todo o conteúdo da notícia original para o português com precisão jornalística e tom profissional.
   - ⚠️ REGRA MANDATÓRIA DE MOEDA: Se existirem valores em dólar (ex: $450, $2,549.99, US$ 1,200, USD 599), MANTENHA OBRIGATORIAMENTE OS VALORES EM DÓLAR exatamente como no original. NÃO converta para Real nem altere o símbolo de dólar ($)."""
    else:
        translation_block = """5. '## 📄 Síntese Detalhada da Notícia (pt-BR)'
   - Apresente os fatos completos da notícia original com clareza e profundidade técnica.
   - ⚠️ REGRA MANDATÓRIA DE MOEDA: Se existirem valores em dólar (ex: $450, $2,549.99), mantenha os valores em dólar."""

    prompt = f"""Você é o Editor-Chefe e Roteirista sênior do canal brasileiro TECH DIÁRIO (YouTube: @techdiario).
O foco do canal é hardware custo-benefício, placas de vídeo, IA local (llama.cpp, VRAM, GGUF), mercado brasileiro de informática e compras no Paraguai.

🚨 REGRA SUPREMA DE MOEDA:
Se a matéria original contiver valores em DÓLAR (ex: $450, $2,549.99, US$ 1,200, $599), MANTENHA OBRIGATORIAMENTE OS VALORES EM DÓLAR COM O SÍMBOLO $ em TODAS as seções (Títulos, Roteiro, Descrição e Tradução).
É ESTRITAMENTE PROIBIDO converter valores de dólar para Real (R$) ou trocar o símbolo '$' por 'R$'.
Se um PC custa $2,549.99 na Newegg ou tem desconto de $450, escreva SEMPRE '$2,549.99' e '$450'. NUNCA escreva 'R$ 2.549' ou 'R$ 450'.

Escreva um arquivo completo de pauta, roteiro e tradução para o YouTube baseado na seguinte notícia:
Fonte: [{source}]({url})
Título Original: {title}
Conteúdo da Notícia: {original_text}
Entidades citadas: {', '.join(entidades) if isinstance(entidades, list) else entidades}
Ângulo Editorial: {motivo}

Estruture sua resposta EXATAMENTE com as seções abaixo em Markdown:
1. '## 🎯 3 Opções de Título (Alto CTR)' - Menos de 65 caracteres, voltados para cliques sem mentir (mantendo valores originais em dólar como $450 ou $2,549.99 se citados).
2. '## 🎙️ Roteiro Estruturado de Gravação':
   - '### 1. Gancho de Abertura (0:00 – 0:45)' - Chame a atenção do público de hardware/IA local imediatamente.
   - '### 2. Bloco do Patrocinador Oficial (0:45 – 1:15)' - Inclua a menção: 'E antes de continuar: se você quer economizar de verdade, passe na GATO MERCOSUL! Use o cupom TD5 e ganhe 5% de desconto em qualquer produto no site www.gatomercosul.com.br!'.
   - '### 3. Desenvolvimento Técnico & Pilares TECH DIÁRIO (1:15 – 5:00)' - Explicação técnica acessível, VRAM necessária, impacto prático em jogos e IA local, e estimativa de preço no Brasil vs Paraguai (mantendo rigorosamente preços originais em dólar como $450 ou $2,549.99 se citados na fonte).
   - '### 4. Veredito & Chamada para Comentários (5:00 – 6:00)' - Pergunta engajadora para os inscritos comentarem.
3. '## 📝 Descrição Completa para YouTube & SEO' - Com capítulos de minutagem e 15 tags de SEO.
{translation_block}

No final do texto, inclua este bloco JSON delimitado por ```json ... ``` com os dados para a Thumbnail:
```json
{{
  "headline_capa": "TEXTO EM MAIÚSCULAS DE 2 A 4 PALAVRAS",
  "badge_capa": "DETALHE TÉCNICO CURTO (ex: 16GB GDDR7 ou $450)",
  "slug_sugerido": "termo-curto-hifenizado"
}}
```
"""

    url_api = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": WRITER_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.35,
            "num_predict": 2800,
            "num_ctx": 4096,
        },
    }

    req = urllib.request.Request(
        url_api,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=240) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        full_text = res_data.get("response", "")

    # Extrai o bloco JSON com dados da capa
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", full_text, re.DOTALL)
    thumb_info = {}
    if json_match:
        try:
            thumb_info = json.loads(json_match.group(1))
        except Exception:
            pass

    # Remove qualquer bloco preliminar de raciocinio (Thinking Process, Chain-of-Thought, outlines)
    if "## 🎯" in full_text:
        clean_body = re.sub(r"^.*?(?=## 🎯)", "", full_text, flags=re.DOTALL).strip()
    elif "## 1." in full_text:
        clean_body = re.sub(r"^.*?(?=## 1\.)", "", full_text, flags=re.DOTALL).strip()
    else:
        clean_body = full_text

    # Remove o bloco de dados técnicos JSON do corpo editorial final e cercas markdown
    clean_body = re.sub(r"```json\s*\{.*?\}\s*```", "", clean_body, flags=re.DOTALL).strip()
    clean_body = re.sub(r"^```(?:markdown)?\s*", "", clean_body, flags=re.IGNORECASE).strip()
    clean_body = re.sub(r"\s*```$", "", clean_body).strip()
    clean_body = re.sub(r"\[FIM DA PAUTA\].*", "", clean_body, flags=re.DOTALL).strip()

    headline = thumb_info.get("headline_capa") or f"{title[:25].upper()}!"
    badge = thumb_info.get("badge_capa") or "HARDWARE 2026"
    raw_slug = thumb_info.get("slug_sugerido") or title
    slug = slugify(raw_slug)

    return {
        "markdown": clean_body,
        "headline_capa": headline,
        "badge_capa": badge,
        "slug": slug,
        "is_english": is_english,
        "original_text": original_text,
    }


def produce_pauta_for_article(article: dict) -> dict:
    today_str = datetime.now().strftime("%Y-%m-%d")
    gen_result = generate_pauta_content(article)

    base_folder_name = f"{today_str}_{gen_result['slug']}"
    folder_name = base_folder_name
    counter = 1
    # Evita sobreescrita quando múltiplos artigos do dia gerarem slugs parecidos
    while (OUTPUT_DIR / folder_name / "pauta_roteiro.md").exists():
        counter += 1
        folder_name = f"{base_folder_name}-{counter}"

    target_folder = OUTPUT_DIR / folder_name
    target_folder.mkdir(parents=True, exist_ok=True)

    # Monta cabeçalho padronizado determinístico
    title = article.get("title", "")
    source = article.get("primary_source", article.get("source", "Portal Tech"))
    url = article.get("primary_url", article.get("url", ""))
    is_eng = gen_result.get("is_english", False)
    orig_text = gen_result.get("original_text", "")
    categoria = str(article.get("categoria", "hardware")).upper()
    entidades = article.get("entidades", [])
    entidades_str = ", ".join(entidades) if isinstance(entidades, list) else str(entidades)

    header_lines = [
        f"# PAUTA: {title}",
        "",
        f"- **Fonte Original:** [{source}]({url})",
        f"- **Link da Notícia:** [{url}]({url})",
        f"- **Score de Relevância:** {article.get('nota_relevancia_br', 80)}/100",
        f"- **Categoria:** {categoria}",
        f"- **Entidades Citadas:** {entidades_str}",
        "",
        "---",
        "",
    ]

    footer_lines = [
        "",
        "---",
        "",
        "## 📄 Matéria Original (Texto Fonte)",
        f"- **Título Original:** {title}",
        f"- **Fonte:** [{source}]({url})",
        f"- **Link da Notícia Original:** [{url}]({url})",
        f"- **Idioma Original:** {'Inglês (English)' if is_eng else 'Português (pt-BR)'}",
        "",
        "### Texto Original na Íntegra:",
    ]
    if orig_text:
        for p in orig_text.split("\n"):
            p_str = p.strip()
            if p_str:
                footer_lines.append(f"> {p_str}")
            else:
                footer_lines.append(">")
    else:
        footer_lines.append("> [Texto completo não fornecido no feed - consulte o link da fonte acima]")

    full_pauta_markdown = (
        "\n".join(header_lines)
        + gen_result["markdown"].strip()
        + "\n"
        + "\n".join(footer_lines)
        + "\n"
    )

    pauta_path = target_folder / "pauta_roteiro.md"
    with open(pauta_path, "w", encoding="utf-8") as f:
        f.write(full_pauta_markdown)

    print(f"[Pauta Generator] Pauta salva com sucesso em: {pauta_path}", flush=True)

    return {
        "subfolder": folder_name,
        "pauta_path": str(pauta_path),
        "headline_capa": gen_result["headline_capa"],
        "badge_capa": gen_result["badge_capa"],
        "theme_style": article.get("theme_style_sugerido", "nvidia_rtx"),
        "image_url": article.get("primary_image_url") or article.get("image_url"),
        "prompt_arte_capa": article.get("prompt_arte_capa", f"Cinematic hardware photo of {article.get('title', '')[:40]}, 8k"),
    }


def main():
    parser = argparse.ArgumentParser(description="Gerador de pautas do TECH DIÁRIO via Ollama qwen2.5:3b")
    parser.add_argument("--json", type=str, help="JSON com os dados do artigo")
    parser.add_argument("--file", type=str, help="Arquivo contendo o JSON do artigo")
    args = parser.parse_args()

    article = {}
    if args.json:
        article = json.loads(args.json)
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            article = json.load(f)
    else:
        article = json.load(sys.stdin)

    result = produce_pauta_for_article(article)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

