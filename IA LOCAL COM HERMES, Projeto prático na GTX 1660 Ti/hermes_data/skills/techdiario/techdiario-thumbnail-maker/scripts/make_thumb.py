#!/usr/bin/env python3
"""
Cliente da Skill techdiario-thumbnail-maker.
Envia o prompt exclusivo do tema + estilo visual (alert, nvidia_ice, versus) para o
servico local Qwen-Image-2.1-GGUF (http://qwen-image:8090/generate-thumbnail)
e salva os metadados junto com a imagem final 1280x720.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API_BASE = os.getenv("QWEN_IMAGE_API_URL", "http://qwen-image:8090")
OLLAMA_BASE = os.getenv("OLLAMA_URL", "http://ollama:11434")
OUTPUT_ROOT = Path(os.getenv("OUTPUT_DIR", "/opt/output"))


def unload_and_wait_vram(max_wait_seconds: int = 15):
    """
    VRAM Hardware Gate: Descarrega os modelos do Ollama e aguarda a confirmacao
    de que a VRAM da GTX 1660 Ti esta 100% liberada antes de disparar o Qwen-Image.
    """
    writer_model = os.getenv("WRITER_MODEL", "qwen3.5:9b")
    print(f"[VRAM Gate] Solicitando descarregamento imediato de modelos no Ollama ({writer_model})...", flush=True)

    candidate_models = set()
    candidate_models.add(writer_model)
    candidate_models.add("qwen3.5:9b")
    candidate_models.add("qwen2.5:1.5b")
    candidate_models.add("nomic-embed-text:latest")
    candidate_models.add("nomic-embed-text")

    try:
        req = urllib.request.Request(f"{OLLAMA_BASE.rstrip('/')}/api/ps")
        with urllib.request.urlopen(req, timeout=3) as r:
            running = json.loads(r.read().decode("utf-8")).get("models", [])
        for m in running:
            m_name = m.get("name")
            if m_name:
                candidate_models.add(m_name)
    except Exception as e:
        print(f"[VRAM Gate] Aviso ao contatar Ollama: {e}", file=sys.stderr)

    for m_name in candidate_models:
        try:
            u_req = urllib.request.Request(
                f"{OLLAMA_BASE.rstrip('/')}/api/generate",
                data=json.dumps({"model": m_name, "keep_alive": 0}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(u_req, timeout=5) as _:
                label = f"{m_name} (Qwen3.5-9B-Q3_K_S)" if "qwen3.5" in m_name else m_name
                print(f"[VRAM Gate] Solicitado unload de: {label}", flush=True)
        except Exception:
            pass

    # Polling ativo até que a lista de modelos ativos no Ollama fique vazia
    t0 = time.time()
    while time.time() - t0 < max_wait_seconds:
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE.rstrip('/')}/api/ps")
            with urllib.request.urlopen(req, timeout=3) as r:
                active = json.loads(r.read().decode("utf-8")).get("models", [])
            if not active:
                print(f"[VRAM Gate] Confirmado: GPU 100% livre em {round(time.time() - t0, 2)}s!", flush=True)
                return
        except Exception:
            break
        time.sleep(1.0)
    print("[VRAM Gate] Prosseguindo com o render...", flush=True)



def main():
    parser = argparse.ArgumentParser(description="Gera thumbnail exclusiva 1280x720 para o canal TECH DIARIO")
    parser.add_argument("--prompt", required=True, help="Descricao visual exclusiva da cena da capa")
    parser.add_argument("--headline", required=True, help="Texto curto em Portugues (2 a 4 palavras) para renderizar em 3D")
    parser.add_argument("--badge", default="", help="Texto do badge tecnico (ex: '16GB VRAM')")
    parser.add_argument(
        "--theme-style",
        choices=["auto", "nvidia_rtx", "amd_radeon", "intel_core", "versus", "alert", "oferta_dollar", "nvidia_ice"],
        default="auto",
        help="Layout e paleta da capa: nvidia_rtx, amd_radeon, intel_core, versus, alert, oferta_dollar",
    )
    parser.add_argument("--image-url", default="", help="URL direta da imagem oficial em alta resolucao coletada da web")
    parser.add_argument("--subfolder", default="teste_techdiario", help="Subpasta dentro de /opt/output")
    parser.add_argument(
        "--ref-mode",
        choices=["eu_foto", "eu_ilustrado", "none"],
        default="none",
        help="Referencia opcional (-r) para o sd-cli",
    )
    parser.add_argument("--overlay-avatar", action="store_true", default=True)
    parser.add_argument("--logo-pos", default="auto", choices=["auto", "top-left", "top-right", "bottom-left", "bottom-right"])
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--skip-vram-unload", action="store_true", help="Pula descarregamento de VRAM se ja foi feito em lote")
    args = parser.parse_args()

    use_compose = bool(args.image_url and args.image_url.strip())

    if use_compose:
        payload = {
            "image_url": args.image_url.strip(),
            "headline_text": args.headline,
            "badge_text": args.badge if args.badge else None,
            "theme_style": args.theme_style,
            "output_subfolder": args.subfolder,
            "output_filename": "capa_youtube_1280x720.png",
            "overlay_avatar": args.overlay_avatar,
            "logo_position": args.logo_pos,
        }
        url = f"{API_BASE.rstrip('/')}/compose-thumbnail"
    else:
        payload = {
            "prompt": args.prompt,
            "headline_text": args.headline,
            "badge_text": args.badge if args.badge else None,
            "theme_style": args.theme_style,
            "output_subfolder": args.subfolder,
            "output_filename": "capa_youtube_1280x720.png",
            "reference_mode": args.ref_mode,
            "overlay_avatar": args.overlay_avatar,
            "logo_position": args.logo_pos,
            "steps": args.steps,
            "cfg_scale": args.cfg,
            "seed": args.seed,
            "width": 1280,
            "height": 720,
        }
        url = f"{API_BASE.rstrip('/')}/generate-thumbnail"

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # VRAM Hardware Gate: necessário apenas para render generativo pesado sd-cli
    if not use_compose:
        if not args.skip_vram_unload:
            unload_and_wait_vram()
        else:
            print("[VRAM Gate] Descarregamento previo em lote confirmado. Prosseguindo direto para render...", flush=True)
    else:
        print(f"[Studio Fast-Track] Compondo com imagem oficial web (sem necessidade de unload VRAM)...", flush=True)

    print(f"[techdiario-thumbnail-maker] Enviando requisicao ({args.theme_style}) para {url}...", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"ERRO HTTP {e.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRO de conexao com qwen-image: {e}", file=sys.stderr)
        sys.exit(1)

    target_dir = OUTPUT_ROOT / args.subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    meta_file = target_dir / "prompt_capa.json"
    meta_file.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "request": payload,
                "response": result,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
