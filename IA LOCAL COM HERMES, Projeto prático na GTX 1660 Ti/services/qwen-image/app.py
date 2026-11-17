import hashlib
import io
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel, Field

from overlay_utils import THEME_PRESETS, add_techdiario_finishing, pick_theme_style

app = FastAPI(
    title="TECH DIARIO - Studio Thumbnail Engine",
    description="Servico local acelerado em Docker para geracao e composicao de capas profissionais YouTube do TECH DIARIO",
    version="2.0.0",
)

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/models"))
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/opt/assets"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/opt/output"))

DIFFUSION_MODEL = os.getenv("DIFFUSION_MODEL", "qwen-image-2.1-Q3_K_XL.gguf")
VAE_MODEL = os.getenv("VAE_MODEL", "qwen_image_2.1_vae_bf16.safetensors")
TEXT_ENCODER = os.getenv("TEXT_ENCODER", "Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf")
MMPROJ_MODEL = os.getenv("MMPROJ_MODEL", "mmproj-F16.gguf")


class ComposeRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="URL direta da imagem oficial em alta resolucao coletada da web")
    local_image_path: Optional[str] = Field(default=None, description="Caminho para imagem ja existente em disco")
    headline_text: str = Field(default="", description="Texto curto (2 a 4 palavras) para renderizar em 3D")
    badge_text: Optional[str] = Field(default=None, description="Badge tecnico (ex: '16GB VRAM', '$450')")
    theme_style: str = Field(
        default="auto",
        description="Estilo tematico: 'auto', 'nvidia_rtx', 'amd_radeon', 'intel_core', 'versus', 'alert', 'oferta_dollar'",
    )
    output_subfolder: str = Field(default="avulsas", description="Subpasta dentro de /opt/output")
    output_filename: str = Field(default="capa_youtube_1280x720.png", description="Nome do arquivo de saida")
    overlay_avatar: bool = Field(default=True, description="Insere recorte oficial do apresentador com rim-light")
    logo_position: str = Field(default="auto", description="Posicao do logotipo TECH DIARIO")


class ThumbnailRequest(BaseModel):
    prompt: str = Field(..., description="Prompt detalhado exclusivo do tema para o gerador de imagem")
    headline_text: str = Field(default="", description="Texto curto (2 a 4 palavras) para renderizar em 3D")
    badge_text: Optional[str] = Field(default=None, description="Badge tecnico opcional (ex: '16GB GDDR7')")
    theme_style: str = Field(
        default="auto",
        description="Estilo visual: auto, nvidia_rtx, amd_radeon, intel_core, versus, alert, oferta_dollar",
    )
    output_subfolder: str = Field(default="avulsas", description="Subpasta dentro de /opt/output")
    output_filename: str = Field(default="capa_youtube_1280x720.png", description="Nome do arquivo PNG de saida")
    reference_mode: str = Field(default="none", description="Referencia de ativo: eu_foto, eu_ilustrado ou none")
    overlay_avatar: bool = Field(default=True, description="Se True, aplica o apresentador oficial")
    logo_position: str = Field(default="auto", description="Posicao do LOGO SIMPLES.png")
    image_url: Optional[str] = Field(default=None, description="URL opcional de imagem web de alta fidelidade")
    steps: int = Field(default=4, ge=1, le=40)
    cfg_scale: float = Field(default=1.0, ge=1.0, le=10.0)
    seed: int = Field(default=-1, description="Seed (-1 gera seed automatica)")
    width: int = Field(default=1280)
    height: int = Field(default=720)


def download_web_image(url: str, dest_path: Path, timeout: int = 10) -> bool:
    """Baixa a imagem oficial da web em alta resolucao e valida integridade via PIL."""
    try:
        # Otimiza resolucao de miniaturas do Google News para HD 1280px
        if "googleusercontent.com" in url and "=s" in url:
            url = re.sub(r"=s\d+.*", "=s0-w1280-rw", url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 2000:
                return False
            # Valida imagem com PIL
            img = Image.open(io.BytesIO(data))
            # Converte formatos como WEBP/AVIF para RGB direto em PNG/JPG
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            img.convert("RGB").save(dest_path, format="JPEG", quality=95)
            print(f"[Web Image Harvester] Sucesso: Imagem {img.size} salva em {dest_path}", flush=True)
            return True
    except Exception as e:
        print(f"[Web Image Harvester] Falha ao baixar de {url}: {e}", flush=True)
        return False


@app.get("/health")
def health_check():
    files = {
        "asset_capa": (ASSETS_DIR / "CAPA.png").exists(),
        "asset_eu_com_logo": (ASSETS_DIR / "EU COM LOGO.png").exists(),
        "asset_logo_simples": (ASSETS_DIR / "LOGO SIMPLES.png").exists(),
        "diffusion_model": (MODELS_DIR / DIFFUSION_MODEL).exists(),
    }
    return {
        "status": "ok",
        "models_dir": str(MODELS_DIR),
        "assets_dir": str(ASSETS_DIR),
        "themes_available": list(THEME_PRESETS.keys()),
        "files_ready": files,
    }


@app.post("/compose-thumbnail")
def compose_thumbnail(req: ComposeRequest):
    """
    Novo Endpoint Ultra-Rapido (<1.5s):
    Utiliza a imagem de alta fidelidade obtida da web ou disco e processa
    o layout tematico 100% acelerado no Studio sem precisar de geracao pesada de difusao.
    """
    t0 = time.time()
    target_dir = OUTPUT_DIR / req.output_subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / req.output_filename
    raw_bg_file = target_dir / "raw_web_image.jpg"

    effective_style = pick_theme_style(req.headline_text, req.badge_text or "", req.theme_style)

    has_base_image = False

    # 1. Tenta usar imagem da web se fornecida
    if req.image_url and download_web_image(req.image_url, raw_bg_file):
        has_base_image = True
    # 2. Tenta usar imagem local
    elif req.local_image_path and Path(req.local_image_path).exists():
        img = Image.open(req.local_image_path).convert("RGB")
        img.save(raw_bg_file, format="JPEG", quality=95)
        has_base_image = True
    elif raw_bg_file.exists():
        has_base_image = True

    # 3. Fallback: cria cena temática sintética de estúdio se nenhuma imagem foi encontrada
    if not has_base_image:
        print("[Studio] Nenhuma imagem de fundo encontrada; criando backdrop de estúdio...", flush=True)
        backdrop = Image.new("RGB", (1280, 720), (12, 14, 22))
        backdrop.save(raw_bg_file, format="JPEG")

    # Copia o raw para o arquivo de destino e aplica o acabamento temático profissional
    base = Image.open(raw_bg_file).convert("RGB")
    base.save(out_file, format="PNG")

    add_techdiario_finishing(
        img_path=str(out_file),
        assets_dir=str(ASSETS_DIR),
        headline_text=req.headline_text,
        badge_text=req.badge_text,
        logo_position=req.logo_position,
        overlay_avatar=req.overlay_avatar,
        theme_style=effective_style,
    )

    elapsed = round(time.time() - t0, 2)
    print(f"[Studio] Capa {req.output_filename} finalizada em {elapsed}s (Tema: {effective_style})", flush=True)

    return {
        "status": "success",
        "method": "web_harvester_composite" if has_base_image else "studio_backdrop",
        "elapsed_seconds": elapsed,
        "theme_style": effective_style,
        "output_path": str(out_file),
        "headline_rendered": req.headline_text,
        "badge_rendered": req.badge_text,
    }


@app.post("/generate-thumbnail")
def generate_thumbnail(req: ThumbnailRequest):
    """
    Endpoint com Dual-Engine Inteligente:
    Se 'image_url' for fornecido, compõe instantaneamente via /compose-thumbnail (<1s).
    Se nao houver imagem web, executa o motor generativo via sd-cli.
    """
    target_dir = OUTPUT_DIR / req.output_subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / req.output_filename

    # Se uma imagem web de alta qualidade foi informada, utiliza o compositor ultra-rápido!
    if req.image_url:
        compose_req = ComposeRequest(
            image_url=req.image_url,
            headline_text=req.headline_text,
            badge_text=req.badge_text,
            theme_style=req.theme_style,
            output_subfolder=req.output_subfolder,
            output_filename=req.output_filename,
            overlay_avatar=req.overlay_avatar,
            logo_position=req.logo_position,
        )
        return compose_thumbnail(compose_req)

    # Caso contrário, fallback para o gerador sd-cli
    diff_path = MODELS_DIR / DIFFUSION_MODEL
    vae_path = MODELS_DIR / VAE_MODEL
    llm_path = MODELS_DIR / TEXT_ENCODER
    mmproj_path = MODELS_DIR / MMPROJ_MODEL

    for p, label in [(diff_path, "Diffusion GGUF"), (vae_path, "VAE"), (llm_path, "Text Encoder GGUF")]:
        if not p.exists():
            # Se faltar algum modelo pesado, faz fallback para composição de estúdio limpa
            compose_req = ComposeRequest(
                headline_text=req.headline_text,
                badge_text=req.badge_text,
                theme_style=req.theme_style,
                output_subfolder=req.output_subfolder,
                output_filename=req.output_filename,
                overlay_avatar=req.overlay_avatar,
                logo_position=req.logo_position,
            )
            return compose_thumbnail(compose_req)

    effective_seed = req.seed
    if effective_seed <= 0 or effective_seed == 42:
        digest = hashlib.sha256(f"{req.output_subfolder}:{req.prompt}:{req.headline_text}".encode("utf-8")).hexdigest()
        effective_seed = int(digest[:8], 16) % 2147483647

    full_prompt = req.prompt.strip()
    if req.headline_text.strip():
        full_prompt += (
            f'. High-impact YouTube tech thumbnail background scene for "{req.headline_text.strip().upper()}", '
            f"dramatic cinematic studio lighting, ultra detailed hardware photography, 8k."
        )

    gen_w = min(req.width, 512)
    gen_h = min(req.height, 288)

    cmd = [
        "/usr/local/bin/sd-cli",
        "--mmap",
        "--diffusion-model", str(diff_path),
        "--vae", str(vae_path),
        "--llm", str(llm_path),
        "-p", full_prompt,
        "--steps", str(req.steps),
        "--cfg-scale", str(req.cfg_scale),
        "--sampling-method", "euler",
        "-W", str(gen_w),
        "-H", str(gen_h),
        "--seed", str(effective_seed),
        "--vae-tiling",
        "--flash-attn", "off,diffusion=on",
        "--model-args", "qwen_image_2_1_prefix_cache_type=q8_0",
        "--cache-mode", "easycache",
        "-o", str(out_file),
    ]

    if req.steps <= 4:
        cmd.extend(["--sigmas", "1.0,0.75,0.5,0.25,0.0"])
    elif req.steps <= 8:
        cmd.extend(["--sigmas", "qwen-image-2.1-turbo"])
    else:
        cmd.extend(["--flow-shift", "3"])

    ref_file = None
    if req.reference_mode == "eu_foto" and (ASSETS_DIR / "EU.jpg").exists():
        ref_file = ASSETS_DIR / "EU.jpg"
    elif req.reference_mode == "eu_ilustrado" and (ASSETS_DIR / "EU COM LOGO.png").exists():
        ref_file = ASSETS_DIR / "EU COM LOGO.png"

    if ref_file is not None and mmproj_path.exists():
        cmd.extend(["--llm_vision", str(mmproj_path), "-r", str(ref_file)])

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.time() - t0, 2)

    if proc.returncode != 0 or not out_file.exists():
        # Fallback gracioso para a composição de estúdio
        compose_req = ComposeRequest(
            headline_text=req.headline_text,
            badge_text=req.badge_text,
            theme_style=req.theme_style,
            output_subfolder=req.output_subfolder,
            output_filename=req.output_filename,
            overlay_avatar=req.overlay_avatar,
            logo_position=req.logo_position,
        )
        return compose_thumbnail(compose_req)

    add_techdiario_finishing(
        img_path=str(out_file),
        assets_dir=str(ASSETS_DIR),
        headline_text=req.headline_text,
        badge_text=req.badge_text,
        logo_position=req.logo_position,
        overlay_avatar=req.overlay_avatar,
        theme_style=req.theme_style,
    )

    return {
        "status": "success",
        "method": "sd_cli_generative",
        "elapsed_seconds": elapsed,
        "seed_used": effective_seed,
        "theme_style": req.theme_style,
        "output_path": str(out_file),
        "prompt_used": full_prompt,
    }
