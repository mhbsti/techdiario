#!/usr/bin/env python3
"""
Pipeline Multi-Portal de Notícias + Vetorização (Qdrant) + Classificação Rápida (Ollama)
para o CANAL TECH DIARIO.

Portais Monitorados:
1. TechPowerUp: https://www.techpowerup.com/rss/news
2. TechSpot: https://www.techspot.com/backend.xml
3. Adrenaline (PT-BR): https://www.adrenaline.com.br/feed/
4. PC Gamer: https://www.pcgamer.com/rss/
5. Tom's Hardware: https://www.tomshardware.com/feeds/all
6. VideoCardz: https://videocardz.com/feed
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "qwen2.5:1.5b")

COLLECTION_NEWS = "news_articles"
COLLECTION_HISTORY = "techdiario_history"
COLLECTION_RULES = "editorial_rules"

# Fuso horário padrão do TECH DIÁRIO (América/São Paulo - UTC-3)
SP_TZ = timezone(timedelta(hours=-3))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

SOURCES = {
    "TechPowerUp": {
        "url": "https://www.techpowerup.com/rss/news",
        "lang": "en",
        "category_default": "HARDWARE",
    },
    "TechSpot": {
        "url": "https://www.techspot.com/backend.xml",
        "lang": "en",
        "category_default": "HARDWARE",
    },
    "Adrenaline": {
        "url": "https://www.adrenaline.com.br/feed/",
        "lang": "pt-BR",
        "category_default": "HARDWARE_GAMES",
    },
    "PC Gamer": {
        "url": "https://www.pcgamer.com/rss/",
        "lang": "en",
        "category_default": "PC_GAMING",
    },
    "Tom's Hardware": {
        "url": "https://www.tomshardware.com/feeds/all",
        "lang": "en",
        "category_default": "HARDWARE",
    },
    "VideoCardz": {
        # Feed indexado em tempo real com bypass total de Cloudflare 403 e pubDate precisa
        "url": "https://news.google.com/rss/search?q=site:videocardz.com+when:3d&hl=en-US&gl=US&ceid=US:en",
        "lang": "en",
        "category_default": "GPU",
    },
}

KEYWORDS_WEIGHTS = {
    "rtx 5090": 30,
    "rtx 5080": 26,
    "rtx 5070": 26,
    "rtx 5060": 30,
    "rtx 5050": 24,
    "rx 9070": 26,
    "rx 9060": 24,
    "arc b580": 22,
    "arc b570": 20,
    "battlemage": 20,
    "vram": 22,
    "8gb": 22,
    "12gb": 18,
    "16gb": 22,
    "24gb": 20,
    "gddr7": 20,
    "price": 20,
    "preço": 22,
    "msrp": 20,
    "leak": 16,
    "vazamento": 18,
    "dlss": 18,
    "fsr": 18,
    "x3d": 24,
    "9800x3d": 28,
    "ryzen": 18,
    "core ultra": 18,
    "intel": 14,
    "nvidia": 16,
    "amd": 16,
    "geforce": 16,
    "radeon": 16,
    "paraguai": 30,
    "brasil": 25,
    "roubo": 25,
    "alerta": 20,
    "driver": 15,
}


def http_get(url: str, timeout: int = 15) -> str:
    # 1. Tentativa via curl_cffi (impersonate chrome) se disponível
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout)
        if resp.status_code == 200 and len(resp.text) > 100:
            return resp.text
    except Exception:
        pass

    # 2. Tentativa direta com cabeçalhos padrão
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            if "Access blocked" in content or "Sorry, you have been blocked" in content:
                raise urllib.error.HTTPError(url, 403, "Cloudflare Access Blocked", {}, None)
            return content
    except Exception as exc:
        # 3. Fallback inteligente: se for Cloudflare/403/Forbidden, usa o proxy limpo do Jina Reader
        target_for_jina = url.replace("/feed", "/newz") if "videocardz.com" in url else url
        try:
            jina_url = f"https://r.jina.ai/{target_for_jina}"
            j_req = urllib.request.Request(
                jina_url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/plain, text/markdown, */*"},
            )
            with urllib.request.urlopen(j_req, timeout=timeout) as j_resp:
                res_jina = j_resp.read().decode("utf-8", errors="replace")
                if "Sorry, you have been blocked" not in res_jina:
                    return res_jina
        except Exception:
            pass
        raise exc


def strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<script.*?>.*?</script>", " ", raw_html, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def calculate_heuristic_score(title: str, summary: str) -> Tuple[int, List[str]]:
    blob = f"{title} {summary}".lower()
    score = 10
    triggers = []
    for kw, pts in KEYWORDS_WEIGHTS.items():
        if kw in blob:
            score += pts
            triggers.append(kw.upper())
    if re.search(r"(\$|r\$)\s?\d{2,5}", blob, re.I):
        score += 15
        triggers.append("PREÇO")
    return score, list(set(triggers))


def parse_article_datetime(pub_date_str: str) -> Optional[datetime]:
    if not pub_date_str:
        return None
    try:
        return parsedate_to_datetime(pub_date_str)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            return datetime.strptime(pub_date_str.strip(), fmt)
        except Exception:
            pass
    return None


def is_published_today(pub_date_str: str, max_age_hours: float = 24.0, target_date: Optional[str] = None) -> bool:
    """Verifica se o artigo foi publicado no dia de hoje (fuso SP/Brasília) ou nas últimas 24h."""
    dt = parse_article_datetime(pub_date_str)
    if not dt:
        # Quando a data não está explícita no feed, considera notícia recente do dia
        return True

    local_dt = dt.astimezone(SP_TZ) if dt.tzinfo else dt.replace(tzinfo=SP_TZ)
    now_local = datetime.now(SP_TZ)

    if target_date:
        return local_dt.strftime("%Y-%m-%d") == target_date

    # 1. Mesmo dia de calendário (ex: 2026-10-23)
    if local_dt.date() == now_local.date():
        return True

    # 2. Publicado nas últimas 24 horas (cobre madrugadas e fusos internacionais)
    age_seconds = (now_local - local_dt).total_seconds()
    if 0 <= age_seconds <= (max_age_hours * 3600):
        return True

    return False


def fetch_source_feed(name: str, meta: dict, only_today: bool = True, max_per_source: Optional[int] = None) -> List[dict]:
    items = []
    try:
        xml_text = http_get(meta["url"], timeout=12)
        if not ("<rss" in xml_text or "<feed" in xml_text or "<?xml" in xml_text):
            # Se a resposta veio em Markdown via Jina Reader, parseia os links diretamente
            pattern = re.compile(r"\[([^\[\]\n]{18,180})\]\((https://videocardz\.com/(?:newz|press-release|pixel|review)/[a-z0-9\-_]+)\)", re.I)
            seen_links = set()
            for m in pattern.finditer(xml_text):
                raw_t = re.sub(r"!\[.*?\]\(.*?\)", "", m.group(1)).strip()
                raw_l = m.group(2).strip()
                if raw_l in seen_links:
                    continue
                if len(raw_t) >= 18 and not any(k in raw_t.lower() for k in ["read more", "browse", "terms", "cookies", "privacy"]):
                    seen_links.add(raw_l)
                    h_score, triggers = calculate_heuristic_score(raw_t, raw_t)
                    items.append({
                        "source": name,
                        "title": raw_t,
                        "url": raw_l,
                        "summary": raw_t,
                        "published_at": datetime.now(SP_TZ).isoformat(),
                        "lang": meta["lang"],
                        "heuristic_score": h_score,
                        "triggers": triggers,
                    })
                    if max_per_source and len(items) >= max_per_source:
                        break
            if items:
                print(f"[{name}] Recuperadas {len(items)} matérias de notícias via Jina Markdown!", file=sys.stderr)
            return items

        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # Trata RSS 2.0 padrão
        for item in root.findall(".//item"):
            title = strip_html(item.findtext("title") or "")
            title = re.sub(r"\s*-\s*VideoCardz\.com$", "", title, flags=re.I).strip()
            link = (item.findtext("link") or "").strip()
            raw_body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or item.findtext("description") or ""
            full_text = strip_html(raw_body)
            pub_date = (item.findtext("pubDate") or "").strip()
            if not title or not link or len(title) < 12:
                continue

            if only_today and not is_published_today(pub_date):
                continue

            # Web Image Harvester: Extrai imagem oficial de alta fidelidade
            img_url = None
            enc = item.find("enclosure")
            if enc is not None and enc.attrib.get("url"):
                img_url = enc.attrib.get("url").strip()

            if not img_url:
                media = item.find("{http://search.yahoo.com/mrss/}content")
                if media is not None and media.attrib.get("url"):
                    img_url = media.attrib.get("url").strip()

            if not img_url:
                thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
                if thumb is not None and thumb.attrib.get("url"):
                    img_url = thumb.attrib.get("url").strip()

            if not img_url and raw_body:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_body, re.I)
                if img_match:
                    img_url = img_match.group(1).strip()

            # Otimiza thumbnail do Google News para alta resolução
            if img_url and "googleusercontent.com" in img_url and "=s" in img_url:
                img_url = re.sub(r"=s\d+.*", "=s0-w1280-rw", img_url)

            h_score, triggers = calculate_heuristic_score(title, full_text[:600])
            items.append({
                "source": name,
                "title": title,
                "url": link,
                "image_url": img_url,
                "summary": full_text[:800],
                "original_text": full_text[:4000],
                "published_at": pub_date,
                "lang": meta["lang"],
                "heuristic_score": h_score,
                "triggers": triggers,
            })
            if max_per_source and len(items) >= max_per_source:
                break

        # Trata Atom feed
        if not items:
            for entry in root.findall(".//atom:entry", ns) or root.findall(".//entry"):
                title = strip_html(entry.findtext("title") or "")
                link_el = entry.find("link")
                link = link_el.attrib.get("href", "") if link_el is not None else ""
                raw_body = entry.findtext("content") or entry.findtext("summary") or ""
                full_text = strip_html(raw_body)
                pub_date = (entry.findtext("updated") or entry.findtext("published") or "").strip()
                if title and link:
                    if only_today and not is_published_today(pub_date):
                        continue
                    h_score, triggers = calculate_heuristic_score(title, full_text[:600])
                    atom_img = None
                    if raw_body:
                        img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_body, re.I)
                        if img_m:
                            atom_img = img_m.group(1).strip()

                    items.append({
                        "source": name,
                        "title": title,
                        "url": link,
                        "image_url": atom_img,
                        "summary": full_text[:800],
                        "original_text": full_text[:4000],
                        "published_at": pub_date or datetime.now(SP_TZ).isoformat(),
                        "lang": meta["lang"],
                        "heuristic_score": h_score,
                        "triggers": triggers,
                    })
                    if max_per_source and len(items) >= max_per_source:
                        break
    except Exception as exc:
        # Fallback para parsing em markdown quando a fonte for bloqueada no XML puro (ex: VideoCardz)
        try:
            fallback_target = meta["url"].replace("/feed", "").replace("/rss", "")
            jina_md = http_get(f"https://r.jina.ai/{fallback_target}", timeout=15)
            pattern = re.compile(r"\[([^\[\]\n]{18,180})\]\((https?://[a-zA-Z0-9\.\-_/]+/(?:newz|article|news|review|post)/[a-zA-Z0-9\-_]+)\)", re.I)
            if not pattern.search(jina_md):
                pattern = re.compile(r"\[([^\[\]\n]{18,180})\]\((https://videocardz\.com/[a-z0-9\-_]+/[a-z0-9\-_]+)\)", re.I)

            seen_links = set()
            for m in pattern.finditer(jina_md):
                raw_t = re.sub(r"!\[.*?\]\(.*?\)", "", m.group(1)).strip()
                raw_l = m.group(2).strip()
                if raw_l in seen_links:
                    continue
                if len(raw_t) >= 18 and not any(k in raw_t.lower() for k in ["read more", "browse", "terms", "cookies", "privacy"]):
                    seen_links.add(raw_l)
                    h_score, triggers = calculate_heuristic_score(raw_t, raw_t)
                    items.append({
                        "source": name,
                        "title": raw_t,
                        "url": raw_l,
                        "summary": raw_t,
                        "published_at": datetime.now(SP_TZ).isoformat(),
                        "lang": meta["lang"],
                        "heuristic_score": h_score,
                        "triggers": triggers,
                    })
                    if max_per_source and len(items) >= max_per_source:
                        break
            if items:
                print(f"[{name}] Fallback Jina recuperou {len(items)} matérias com sucesso!", file=sys.stderr)
        except Exception as j_exc:
            print(f"[{name}] Erro ao coletar feed: {exc} (fallback: {j_exc})", file=sys.stderr)
    return items


# =============================================================================
# QDRANT & OLLAMA HELPERS
# =============================================================================

def init_qdrant_collections():
    """Garante que as coleções existem no Qdrant com dimensões do nomic-embed-text (768)."""
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections")
        with urllib.request.urlopen(req, timeout=5) as r:
            existing = [c["name"] for c in json.loads(r.read().decode())["result"]["collections"]]

        for col in [COLLECTION_NEWS, COLLECTION_HISTORY, COLLECTION_RULES]:
            if col not in existing:
                payload = {
                    "vectors": {"size": 768, "distance": "Cosine"}
                }
                put_req = urllib.request.Request(
                    f"{QDRANT_URL}/collections/{col}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(put_req, timeout=5) as resp:
                    print(f"[Qdrant] Coleção '{col}' criada com sucesso!")
    except Exception as exc:
        print(f"[Qdrant] Aviso: Não foi possível checar/criar coleções ({exc})", file=sys.stderr)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(x * y for x, y in zip(vec1, vec2))
    norm1 = sum(x * x for x in vec1) ** 0.5
    norm2 = sum(y * y for y in vec2) ** 0.5
    return dot / (norm1 * norm2) if (norm1 and norm2) else 0.0


def get_embedding(text: str) -> Optional[List[float]]:
    url = f"{OLLAMA_URL}/api/embeddings"
    payload = {"model": EMBED_MODEL, "prompt": text[:1500]}
    data_bytes = json.dumps(payload).encode("utf-8")
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("embedding")
        except Exception as exc:
            if attempt == 0:
                time.sleep(2.0)
                continue
            print(f"[Embedding Error] {exc}", file=sys.stderr, flush=True)
            return None
    return None


def search_similar_news(vector: List[float], collection: str = COLLECTION_NEWS, limit: int = 3) -> List[dict]:
    try:
        url = f"{QDRANT_URL}/collections/{collection}/points/search"
        payload = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("result", [])
    except Exception as exc:
        return []


def upsert_qdrant_point(point_id: str, vector: List[float], payload: dict, collection: str = COLLECTION_NEWS):
    try:
        m = hashlib.md5(point_id.encode("utf-8")).hexdigest()
        uuid_str = f"{m[0:8]}-{m[8:12]}-{m[12:16]}-{m[16:20]}-{m[20:32]}"
        
        url = f"{QDRANT_URL}/collections/{collection}/points?wait=true"
        data = {
            "points": [
                {
                    "id": uuid_str,
                    "vector": vector,
                    "payload": payload,
                }
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            pass
    except Exception as exc:
        print(f"[Qdrant] Falha ao upsert {point_id}: {exc}", file=sys.stderr)


def classify_article_with_llm(title: str, summary: str, source: str) -> dict:
    """Classifica a notícia com qwen2.5:1.5b (<1s) retornando JSON estruturado."""
    system_prompt = (
        "Você é o editor e roteador de pautas do canal brasileiro TECH DIÁRIO (YouTube: hardware, GPUs, CPUs, IA local, mercado Brasil/Paraguai).\n"
        "Analise a matéria e responda EXCLUSIVAMENTE em formato JSON com esta estrutura:\n"
        "{\n"
        '  "aprovada": true/false,\n'
        '  "categoria": "gpu" | "cpu" | "driver_ai" | "mercado_alerta" | "pc_gaming",\n'
        '  "entidades": ["RTX 5070", "AMD", "GDDR7"],\n'
        '  "nota_relevancia_br": 0-100,\n'
        '  "theme_style_sugerido": "nvidia_rtx" | "amd_radeon" | "intel_core" | "versus" | "alert" | "oferta_dollar",\n'
        '  "motivo_curto": "1 frase explicando o impacto para o público do canal",\n'
        '  "prompt_arte_capa": "Cinematic 8k photography prompt in English detailing the specific hardware component, studio lighting and background scene (ex: macro close-up of RTX 5070 PCB with neon reflections)"\n'
        "}"
    )

    user_text = f"Fonte: {source}\nTítulo: {title}\nResumo: {summary[:350]}"

    try:
        url = f"{OLLAMA_URL}/api/generate"
        payload = {
            "model": CLASSIFIER_MODEL,
            "prompt": f"{system_prompt}\n\n{user_text}\n\nResposta JSON:",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 220,
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_response = data.get("response", "{}")
            return json.loads(raw_response)
    except Exception as exc:
        print(f"[Classifier LLM Error] {exc}", file=sys.stderr, flush=True)
        # Fallback heurístico caso o Ollama ainda não tenha subido o modelo
        t_low = title.lower()
        if any(k in t_low for k in ["$", "dolar", "dólar", "preço", "preco", "save", "desconto", "barato", "oferta", "msrp", "custo", "paraguai"]):
            style = "oferta_dollar"
        elif any(k in t_low for k in ["sumiu", "roub", "alerta", "cuidado", "cilada", "caro", "golpe", "bug", "queim", "crise", "perigo"]):
            style = "alert"
        elif any(k in t_low for k in ["vs", "contra", "versus", "comparat", "duelo"]):
            style = "versus"
        elif any(k in t_low for k in ["amd", "radeon", "ryzen", "rx 90", "rx 70", "9800x3d", "fsr", "rdna", "zen 5"]):
            style = "amd_radeon"
        elif any(k in t_low for k in ["intel", "core ultra", "arc b5", "battlemage", "arrow lake"]):
            style = "intel_core"
        else:
            style = "nvidia_rtx"

        return {
            "aprovada": True,
            "categoria": "gpu",
            "entidades": ["GPU", "HARDWARE"],
            "nota_relevancia_br": 75,
            "theme_style_sugerido": style,
            "motivo_curto": "Classificado via fallback heurístico",
        }


# =============================================================================
# FLUXO PRINCIPAL
# =============================================================================

def collect_multi_portal(only_today: bool = True, max_per_source: Optional[int] = None) -> List[dict]:
    all_articles = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_source_feed, name, meta, only_today, max_per_source): name
            for name, meta in SOURCES.items()
        }
        for future in as_completed(futures):
            src_name = futures[future]
            try:
                res = future.result()
                all_articles.extend(res)
                print(f"[{src_name}] {len(res)} matérias de hoje coletadas com sucesso!", file=sys.stderr)
            except Exception as e:
                print(f"[{src_name}] Erro: {e}", file=sys.stderr)
    return all_articles


def run_pipeline(
    top_k: Optional[int] = 5,
    only_today: bool = True,
    use_llm_filter: bool = True,
    max_per_source: Optional[int] = None,
    min_relevance_score: int = 50,
) -> dict:
    t0 = time.time()
    init_qdrant_collections()

    raw_items = collect_multi_portal(only_today=only_today, max_per_source=max_per_source)
    print(f"\n[Hunter] Coletados {len(raw_items)} artigos ({'de HOJE' if only_today else 'totais'}) nos 6 portais...", file=sys.stderr, flush=True)

    if not raw_items:
        return {
            "status": "empty",
            "fetched_sources": list(SOURCES.keys()),
            "total_collected": 0,
            "total_analyzed": 0,
            "selected_top_k": 0,
            "elapsed_seconds": round(time.time() - t0, 2),
            "articles": [],
        }

    # Ordena preliminarmente por score heurístico
    raw_items.sort(key=lambda x: x["heuristic_score"], reverse=True)

    # -------------------------------------------------------------------------
    # FASE 1: Embeddings e Deduplicação Semântica no Qdrant (nomic-embed-text)
    # -------------------------------------------------------------------------
    is_all_mode = (top_k is None or top_k <= 0)
    candidates_limit = len(raw_items) if is_all_mode else min(len(raw_items), max(15, top_k * 3))
    candidates_unique = []
    seen_urls = set()

    print(f"[Hunter] Processando embeddings e agrupamento semântico de {candidates_limit} matérias...", file=sys.stderr, flush=True)
    for idx, item in enumerate(raw_items[:candidates_limit], start=1):
        url = item["url"]
        if url in seen_urls:
            continue

        text_to_embed = f"{item['title']} - {item['summary']}"
        vector = get_embedding(text_to_embed)

        is_duplicate = False
        if vector:
            # 1. Verifica contra o histórico de vídeos já gravados do canal
            hist_matches = search_similar_news(vector, COLLECTION_HISTORY, limit=1)
            if hist_matches and hist_matches[0].get("score", 0) > 0.88:
                continue

            # 2. Agrupamento semântico intra-lote (conecta o mesmo tema entre os 6 portais de hoje)
            for c_cand in candidates_unique:
                if c_cand.get("vector") and cosine_similarity(vector, c_cand["vector"]) > 0.84:
                    c_cand.setdefault("related_sources", []).append({
                        "source": item["source"],
                        "url": item["url"],
                        "title": item["title"],
                    })
                    is_duplicate = True
                    break

        if is_duplicate:
            continue

        seen_urls.add(url)
        item["vector"] = vector
        candidates_unique.append(item)

        if not is_all_mode and len(candidates_unique) >= max(6, top_k * 2):
            break

    # -------------------------------------------------------------------------
    # FASE 2: Triagem e Classificação com LLM (qwen2.5:1.5b)
    # -------------------------------------------------------------------------
    print(f"[Hunter] Triando {len(candidates_unique)} pautas únicas com qwen2.5:1.5b...", file=sys.stderr, flush=True)
    clusters = []
    for idx, item in enumerate(candidates_unique, start=1):
        print(f"[{idx}/{len(candidates_unique)}] Analisando ({item['source']}): {item['title'][:50]}...", file=sys.stderr, flush=True)

        cls_info = {}
        if use_llm_filter:
            cls_info = classify_article_with_llm(item["title"], item["summary"], item["source"])
            if not cls_info.get("aprovada", True) or cls_info.get("nota_relevancia_br", 0) < min_relevance_score:
                continue

        final_score = item["heuristic_score"] + (cls_info.get("nota_relevancia_br", 70) * 0.5)

        cluster_item = {
            "title": item["title"],
            "primary_source": item["source"],
            "primary_url": item["url"],
            "primary_image_url": item.get("image_url"),
            "image_url": item.get("image_url"),
            "summary": item["summary"],
            "original_text": item.get("original_text", item["summary"]),
            "lang": item["lang"],
            "published_at": item.get("published_at"),
            "combined_score": round(final_score, 1),
            "nota_relevancia_br": cls_info.get("nota_relevancia_br", 75),
            "categoria": cls_info.get("categoria", "gpu"),
            "entidades": cls_info.get("entidades", item.get("triggers", [])),
            "theme_style_sugerido": cls_info.get("theme_style_sugerido", "nvidia_rtx"),
            "prompt_arte_capa": cls_info.get("prompt_arte_capa", f"Cinematic detailed hardware photography of {item['title'][:40]}, dramatic studio lighting, 8k"),
            "motivo_editorial": cls_info.get("motivo_curto", "Relevante para o canal"),
            "related_sources": [],
        }

        # Salva no Qdrant com persistência vetorial
        if item.get("vector"):
            upsert_qdrant_point(item["url"], item["vector"], cluster_item, COLLECTION_NEWS)

        clusters.append(cluster_item)

    clusters.sort(key=lambda x: x["combined_score"], reverse=True)
    selected = clusters if is_all_mode else clusters[:top_k]

    return {
        "status": "success",
        "fetched_sources": list(SOURCES.keys()),
        "total_collected": len(raw_items),
        "total_analyzed": len(clusters),
        "selected_top_k": len(selected),
        "elapsed_seconds": round(time.time() - t0, 2),
        "articles": selected,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-Portal News Hunter + Qdrant + Ollama Pipeline")
    parser.add_argument("-t", "--limit", type=str, default="5", help="Quantidade de matérias (número ou 'all' para todas do dia)")
    parser.add_argument("-a", "--all", action="store_true", help="Extrai todas as matérias do dia sem corte")
    parser.add_argument("--max-per-source", type=int, default=None, help="Limite por portal (padrão: sem limite)")
    parser.add_argument("--no-today", action="store_true", help="Desativa filtro de data de hoje (pega tudo do feed)")
    parser.add_argument("--no-llm", action="store_true", help="Desativa filtro qwen2.5:1.5b (usa só heurística)")
    args = parser.parse_args()

    top_k = None
    if not args.all:
        if args.limit.lower() in ("all", "0", "tudo"):
            top_k = None
        else:
            try:
                top_k = int(args.limit)
            except ValueError:
                top_k = 5

    result = run_pipeline(
        top_k=top_k,
        only_today=not args.no_today,
        use_llm_filter=not args.no_llm,
        max_per_source=args.max_per_source,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
