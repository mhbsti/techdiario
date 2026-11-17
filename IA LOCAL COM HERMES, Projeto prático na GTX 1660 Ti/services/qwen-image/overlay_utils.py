import hashlib
import os
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def _load_bold_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# =============================================================================
# 6 PRESETS TEMÁTICOS PROFISSIONAIS DE HARDWARE TECH DIÁRIO
# =============================================================================
THEME_PRESETS = {
    # 1. NVIDIA GEFORCE RTX (Cyber Dark + Verde Neon #76B900 + Ciano Elétrico)
    "nvidia_rtx": {
        "name": "NVIDIA RTX",
        "line1_color": (255, 255, 255, 255),    # Branco Puro Alto Contraste
        "line2_color": (118, 255, 0, 255),      # Verde Neon GeForce
        "glow1": (0, 230, 120, 220),
        "glow2": (118, 255, 0, 230),
        "border_outer": (118, 185, 0),          # Verde Oficial NVIDIA
        "border_inner": (0, 245, 212),          # Ciano Cyber
        "badge_bg": (10, 28, 14, 245),
        "badge_fg": (118, 255, 50, 255),
        "badge_border": (118, 185, 0, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (15, 45, 25),
        "tint_strength": 0.18,
    },
    # 2. AMD RADEON & RYZEN (Flame Red #ED1C24 + Laranja Brasa)
    "amd_radeon": {
        "name": "AMD RADEON",
        "line1_color": (255, 255, 255, 255),    # Branco
        "line2_color": (255, 65, 50, 255),      # Vermelho Radeon Vibrante
        "glow1": (255, 40, 20, 220),
        "glow2": (255, 120, 0, 220),
        "border_outer": (237, 28, 36),          # Vermelho Oficial AMD
        "border_inner": (255, 120, 0),          # Laranja Brasa
        "badge_bg": (36, 10, 10, 245),
        "badge_fg": (255, 90, 80, 255),
        "badge_border": (237, 28, 36, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (50, 15, 10),
        "tint_strength": 0.20,
    },
    # 3. INTEL CORE ULTRA & ARC (Azul Elétrico #0071C5 + Branco Puro)
    "intel_core": {
        "name": "INTEL CORE",
        "line1_color": (255, 255, 255, 255),    # Branco
        "line2_color": (0, 210, 255, 255),      # Azul Claro Elétrico
        "glow1": (0, 130, 255, 220),
        "glow2": (0, 220, 255, 220),
        "border_outer": (0, 113, 197),          # Azul Intel
        "border_inner": (0, 215, 255),          # Ciano Semicondutor
        "badge_bg": (8, 22, 42, 245),
        "badge_fg": (0, 220, 255, 255),
        "badge_border": (0, 140, 255, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (10, 25, 55),
        "tint_strength": 0.20,
    },
    # 4. VERSUS / COMPARATIVO (Split-Screen Diagonal: Laranja/Vermelho vs Verde/Ciano)
    "versus": {
        "name": "VERSUS DUELO",
        "line1_color": (255, 130, 0, 255),      # Laranja Radeon/AMD
        "line2_color": (0, 255, 130, 255),      # Verde GeForce/NVIDIA
        "glow1": (255, 60, 0, 220),
        "glow2": (0, 230, 90, 220),
        "border_outer": (255, 80, 0),
        "border_inner": (0, 240, 110),
        "badge_bg": (24, 12, 34, 245),
        "badge_fg": (255, 235, 0, 255),
        "badge_border": (255, 200, 0, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (30, 20, 40),
        "tint_strength": 0.15,
    },
    # 5. ALERTA CRÍTICO / GOLPE / ROUBO (Amarelo Perigo #FFD000 + Vermelho Fogo)
    "alert": {
        "name": "ALERTA CRÍTICO",
        "line1_color": (255, 235, 0, 255),      # Amarelo Alerta
        "line2_color": (255, 45, 35, 255),      # Vermelho Perigo
        "glow1": (255, 40, 0, 230),
        "glow2": (255, 190, 0, 230),
        "border_outer": (255, 45, 25),
        "border_inner": (255, 215, 0),
        "badge_bg": (45, 8, 8, 245),
        "badge_fg": (255, 230, 0, 255),
        "badge_border": (255, 60, 30, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (55, 15, 10),
        "tint_strength": 0.25,
    },
    # 6. OFERTA & DÓLAR / MERCADO / CUSTO-BENEFÍCIO (Dourado Ouro #FFB800 + Verde Dólar)
    "oferta_dollar": {
        "name": "OFERTA & DÓLAR",
        "line1_color": (255, 220, 0, 255),      # Ouro Metálico
        "line2_color": (0, 255, 150, 255),      # Verde Dólar / Promoção
        "glow1": (255, 180, 0, 220),
        "glow2": (0, 255, 120, 220),
        "border_outer": (255, 184, 0),
        "border_inner": (0, 255, 136),
        "badge_bg": (12, 38, 20, 245),
        "badge_fg": (0, 255, 160, 255),
        "badge_border": (0, 255, 136, 255),
        "avatar_side": "right",
        "text_align": "left",
        "logo_pos": "top-right",
        "tint_color": (15, 45, 25),
        "tint_strength": 0.20,
    },
}

# Compatibilidade retroativa para aliases antigos
THEME_PRESETS["nvidia_ice"] = THEME_PRESETS["nvidia_rtx"]


def pick_theme_style(headline_text: str, badge_text: str = "", explicit_style: str = "auto") -> str:
    """Classifica automaticamente o estilo temático com base em palavras-chave da pauta."""
    if explicit_style in THEME_PRESETS and explicit_style not in ["auto", "none"]:
        return explicit_style

    blob = f"{headline_text} {badge_text}".lower()

    # Dólares / Preços / Promoções / Economia
    if any(k in blob for k in ["$", "dolar", "dólar", "preço", "preco", "save", "desconto", "barato", "oferta", "msrp", "custo", "paraguai"]):
        return "oferta_dollar"

    # Alertas / Roubos / Crises / Cuidado
    if any(k in blob for k in ["sumiu", "roub", "alerta", "cuidado", "cilada", "caro", "golpe", "bug", "queim", "crise", "perigo"]):
        return "alert"

    # Comparativos / Duelos
    if any(k in blob for k in ["vs", "contra", "versus", "comparat", "duelo", "batalha"]):
        return "versus"

    # AMD Radeon & Ryzen
    if any(k in blob for k in ["amd", "radeon", "ryzen", "rx 90", "rx 70", "9800x3d", "fsr", "rdna", "zen 5"]):
        return "amd_radeon"

    # Intel Core & Arc
    if any(k in blob for k in ["intel", "core ultra", "arc b5", "battlemage", "arrow lake", "lga"]):
        return "intel_core"

    # Padrão: NVIDIA RTX
    return "nvidia_rtx"


def _draw_centered_pill(
    draw: ImageDraw.ImageDraw,
    box: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    outline: tuple,
    text_fill: tuple,
    radius: int = 12,
    width: int = 3,
):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x1 + ((x2 - x1) - tw) // 2 - bbox[0]
    ty = y1 + ((y2 - y1) - th) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=text_fill)


def prepare_background_scene(base_img: Image.Image, style_key: str, badge_text: str = "") -> Image.Image:
    """
    Tratamento profissional de imagem de estúdio de hardware:
    1. Redimensiona em alta resolução para 1280x720 (LANCZOS).
    2. Aplica Color Grading temático (tint suave de ambientação).
    3. Vinheta cinematográfica (Dark Vignette) para contraste e destaque ao texto.
    4. Saturação (+18%) e Contraste (+20%) para impacto máximo no feed do YouTube.
    """
    w, h = 1280, 720
    preset = THEME_PRESETS.get(style_key, THEME_PRESETS["nvidia_rtx"])

    # Ajuste de Proporção e Enquadramento inteligente
    img_w, img_h = base_img.size
    target_aspect = w / float(h)
    src_aspect = img_w / float(img_h)

    if src_aspect > target_aspect:
        # Imagem mais larga que 16:9 -> corta as laterais preservando centro
        new_w = int(img_h * target_aspect)
        offset_x = (img_w - new_w) // 2
        cropped = base_img.crop((offset_x, 0, offset_x + new_w, img_h))
    else:
        # Imagem mais alta -> corta topo/baixo
        new_h = int(img_w / target_aspect)
        offset_y = (img_h - new_h) // 2
        cropped = base_img.crop((0, offset_y, img_w, offset_y + new_h))

    base = cropped.resize((w, h), Image.Resampling.LANCZOS).convert("RGB")

    # Aumento de vibração e contraste
    base = ImageEnhance.Contrast(base).enhance(1.22)
    base = ImageEnhance.Color(base).enhance(1.18)
    base = ImageEnhance.Sharpness(base).enhance(1.25)

    arr = np.array(base, dtype=np.float32)

    # Grid de coordenadas normalizadas (0 a 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = xx / float(w)
    ny = yy / float(h)

    # Vinheta cinematográfica: escurece a metade inferior (onde fica o texto 3D) e as bordas
    # mantendo o centro e o produto destacados
    vignette = 1.0 - 0.65 * np.exp(-((nx - 0.45) ** 2 / 0.35 + (ny - 0.45) ** 2 / 0.28))
    # Escurece extra o canto inferior esquerdo (área do texto)
    text_shade = 1.0 - 0.45 * np.exp(-((nx - 0.20) ** 2 / 0.20 + (ny - 0.75) ** 2 / 0.18))
    total_mask = np.clip(vignette * text_shade, 0.18, 1.0)[:, :, np.newaxis]

    # Tint de iluminação temática
    tr, tg, tb = preset["tint_color"]
    t_str = preset["tint_strength"]

    arr = arr * (1.0 - t_str) + np.array([tr, tg, tb], dtype=np.float32) * t_str
    arr = arr * total_mask

    # Efeito de Split-Screen para Versus
    if style_key == "versus":
        diag = (nx + 0.35 * ny) - 0.62
        mask_right = 1.0 / (1.0 + np.exp(-diag * 32.0))
        mask_left = 1.0 - mask_right

        # Esquerda avermelhada (AMD), Direita esverdeada (NVIDIA)
        arr[:, :, 0] = arr[:, :, 0] * (0.85 + 0.35 * mask_left)
        arr[:, :, 1] = arr[:, :, 1] * (0.85 + 0.35 * mask_right)

        # Raio/Linha de separação central
        bolt = np.exp(-(diag ** 2) / 0.0012)
        arr[:, :, 0] += bolt * 255.0
        arr[:, :, 1] += bolt * 230.0
        arr[:, :, 2] += bolt * 180.0

    scene = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")

    # Adornos de overlay temático (Faixa de alerta ou HUD)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    if style_key == "alert":
        # Faixa policial de perigo no topo
        tape = Image.new("RGBA", (1500, 48), (255, 205, 0, 230))
        tdraw = ImageDraw.Draw(tape)
        for sx in range(-60, 1560, 70):
            tdraw.polygon([(sx, 0), (sx + 35, 0), (sx + 10, 48), (sx - 25, 48)], fill=(20, 20, 20, 245))
        tdraw.rectangle([0, 0, 1499, 47], outline=(255, 50, 0, 255), width=2)
        tape_rot = tape.rotate(8, expand=True, resample=Image.Resampling.BICUBIC)
        overlay.paste(tape_rot, (-80, 28), tape_rot)

    elif style_key == "versus":
        # Marcador central de VS
        cx, cy = 640, 360
        odraw.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], fill=(16, 12, 28, 250), outline=(255, 230, 0, 255), width=4)
        font_vs = _load_bold_font(38)
        bbox_vs = odraw.textbbox((0, 0), "VS", font=font_vs)
        odraw.text(
            (cx - (bbox_vs[2] - bbox_vs[0]) // 2 - bbox_vs[0], cy - (bbox_vs[3] - bbox_vs[1]) // 2 - bbox_vs[1]),
            "VS",
            font=font_vs,
            fill=(255, 235, 0, 255),
        )

    return Image.alpha_composite(scene, overlay).convert("RGB")


def apply_screen_logo(
    base_img: Image.Image,
    logo_path: str,
    position: str = "top-right",
    scale_ratio: float = 0.13,
    margin: int = 28,
) -> Image.Image:
    """Posiciona o logotipo TECH DIÁRIO com drop shadow nítido."""
    if not os.path.exists(logo_path):
        return base_img

    base = base_img.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Auto-crop de bordas vazias
    logo_np = np.array(logo, dtype=np.float32)
    rgb = logo_np[:, :, :3]
    lum = np.max(rgb, axis=2)
    non_empty = np.where(lum > 18)
    if len(non_empty[0]) > 0 and len(non_empty[1]) > 0:
        y0, y1 = max(0, int(non_empty[0].min()) - 10), min(logo.height, int(non_empty[0].max()) + 10)
        x0, x1 = max(0, int(non_empty[1].min()) - 10), min(logo.width, int(non_empty[1].max()) + 10)
        logo = logo.crop((x0, y0, x1, y1))

    target_w = int(base.width * scale_ratio)
    aspect = logo.height / max(1, logo.width)
    target_h = int(target_w * aspect)
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Limpeza de canal alfa
    arr = np.array(logo, dtype=np.float32)
    r, g, b, _ = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    max_channel = np.maximum(np.maximum(r, g), b)
    alpha = np.clip((max_channel - 12.0) / 35.0, 0.0, 1.0) ** 0.85 * 255.0
    arr[:, :, 3] = alpha
    logo_clean = Image.fromarray(arr.astype(np.uint8), mode="RGBA")

    if position == "top-left":
        x = margin
        y = margin
    elif position == "top-right":
        x = base.width - target_w - margin
        y = margin
    elif position == "bottom-left":
        x = margin
        y = base.height - target_h - margin
    else:  # Evita bottom-right (YouTube Safe Zone)
        x = base.width - target_w - margin
        y = margin

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_mask = logo_clean.split()[3].point(lambda p: int(p * 0.80))
    shadow_box = Image.new("RGBA", logo_clean.size, (0, 0, 0, 255))
    shadow.paste(shadow_box, (x + 4, y + 4), shadow_mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))

    base = Image.alpha_composite(base, shadow)
    base.paste(logo_clean, (x, y), logo_clean)
    return base.convert("RGB")


def composite_creator_cutout(
    base_img: Image.Image,
    avatar_path: str,
    side: str = "right",
    height_ratio: float = 0.88,
    rim_color: Tuple[int, int, int] = (118, 185, 0),
) -> Image.Image:
    """Insere o apresentador (EU COM LOGO.png) com rim light temático e fade suave inferior."""
    if not os.path.exists(avatar_path):
        return base_img

    base = base_img.convert("RGBA")
    av = Image.open(avatar_path).convert("RGBA")

    target_h = int(base.height * height_ratio)
    aspect = av.width / max(1, av.height)
    target_w = int(target_h * aspect)
    av = av.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Máscara com gradiente de transição suave na lateral e no topo
    mask = Image.new("L", (target_w, target_h), 255)
    mask_np = np.array(mask, dtype=np.float32)

    fade_w = int(target_w * 0.22)
    for i in range(fade_w):
        factor = (i / float(max(1, fade_w))) ** 1.3
        if side == "right":
            mask_np[:, i] *= factor
        else:
            mask_np[:, target_w - 1 - i] *= factor

    # Aplica máscara de alfa
    orig_alpha = np.array(av.split()[3], dtype=np.float32)
    combined_alpha = np.clip((orig_alpha / 255.0) * (mask_np / 255.0) * 255.0, 0, 255).astype(np.uint8)
    av.putalpha(Image.fromarray(combined_alpha, mode="L"))

    x = base.width - target_w if side == "right" else 0
    y = base.height - target_h

    # Glow / Rim Light temático atrás do apresentador
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_mask = av.split()[3].point(lambda p: int(p * 0.65))
    glow_color_layer = Image.new("RGBA", av.size, (*rim_color, 255))
    glow.paste(glow_color_layer, (x, y), glow_mask)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=14))

    base = Image.alpha_composite(base, glow)
    base.paste(av, (x, y), av)
    return base.convert("RGB")


def draw_3d_headline(
    base_img: Image.Image,
    headline_text: str,
    preset: dict,
) -> Image.Image:
    """Renderiza a headline em 3D profissional (2 linhas, extrusão em 8 etapas e stroke preto)."""
    if not headline_text or not headline_text.strip():
        return base_img

    base = base_img.convert("RGBA")
    words = headline_text.strip().upper().split()
    if len(words) >= 3:
        mid = (len(words) + 1) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        lines = [headline_text.strip().upper()]

    font_size = 76 if max(len(l) for l in lines) <= 13 else 62
    font = _load_bold_font(font_size)

    txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(txt_layer)
    draw_glow = ImageDraw.Draw(glow_layer)

    start_y = 425 if len(lines) > 1 else 490
    line_gap = font_size + 14

    for idx, line in enumerate(lines):
        start_x = 45
        y = start_y + idx * line_gap

        # Glow temático suave
        glow_color = preset["glow1"] if idx == 0 else preset["glow2"]
        draw_glow.text((start_x, y), line, font=font, fill=glow_color, stroke_width=16, stroke_fill=glow_color)

        # Extrusão 3D profunda (Drop Shadow em múltiplos passos)
        for depth in range(10, 0, -1):
            draw_txt.text(
                (start_x + depth, y + depth),
                line,
                font=font,
                fill=(6, 6, 12, 255),
                stroke_width=8,
                stroke_fill=(6, 6, 12, 255),
            )

        # Cor frontal vibrante com stroke preto para corte perfeito
        fill_color = preset["line1_color"] if idx == 0 else preset["line2_color"]
        draw_txt.text(
            (start_x, y),
            line,
            font=font,
            fill=fill_color,
            stroke_width=6,
            stroke_fill=(10, 10, 18, 255),
        )

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=14))
    base = Image.alpha_composite(base, glow_layer)
    base = Image.alpha_composite(base, txt_layer)
    return base.convert("RGB")


def add_techdiario_finishing(
    img_path: str,
    assets_dir: str,
    headline_text: Optional[str] = None,
    badge_text: Optional[str] = None,
    logo_position: str = "auto",
    overlay_avatar: bool = True,
    avatar_side: str = "auto",
    theme_style: str = "auto",
) -> str:
    """Aplica o acabamento completo padrão YouTube Pro do canal TECH DIÁRIO."""
    style_key = pick_theme_style(headline_text or "", badge_text or "", theme_style)
    preset = THEME_PRESETS[style_key]

    img = Image.open(img_path).convert("RGB")
    img = prepare_background_scene(img, style_key, badge_text or "")

    # Apresentador (EU COM LOGO.png)
    side = preset["avatar_side"] if avatar_side == "auto" else avatar_side
    if overlay_avatar:
        avatar_file = os.path.join(assets_dir, "EU COM LOGO.png")
        if not os.path.exists(avatar_file):
            avatar_file = os.path.join(assets_dir, "CAPA.png")
        if os.path.exists(avatar_file):
            img = composite_creator_cutout(img, avatar_file, side=side, rim_color=preset["border_outer"])

    # Headline 3D
    if headline_text:
        img = draw_3d_headline(img, headline_text, preset)

    # Logo TECH DIÁRIO (Safe Zone: Posicionado no topo direito ou esquerdo)
    lpos = preset["logo_pos"] if logo_position == "auto" else logo_position
    logo_file = os.path.join(assets_dir, "LOGO SIMPLES.png")
    if os.path.exists(logo_file):
        img = apply_screen_logo(img, logo_file, position=lpos)

    # Badge Técnico / Preço em Dólar ($)
    # Posicionado estrategicamente no Topo-Esquerdo (X=45, Y=42) para não colidir com a UI do YouTube
    if badge_text and badge_text.strip():
        draw = ImageDraw.Draw(img, "RGBA")
        text = badge_text.strip().upper()
        font = _load_bold_font(30)

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 22, 10

        bx1 = 45
        bx2 = bx1 + tw + (pad_x * 2)
        by1 = 42
        by2 = by1 + th + (pad_y * 2)

        # Sombra do badge
        draw.rounded_rectangle([bx1 + 3, by1 + 3, bx2 + 3, by2 + 3], radius=12, fill=(0, 0, 0, 180))
        # Corpo do badge
        draw.rounded_rectangle(
            [bx1, by1, bx2, by2],
            radius=12,
            fill=preset["badge_bg"],
            outline=preset["badge_border"],
            width=3,
        )
        draw.text((bx1 + pad_x, by1 + pad_y - 2), text, font=font, fill=preset["badge_fg"])

    # Moldura Neon Externa Dupla
    draw_border = ImageDraw.Draw(img)
    draw_border.rectangle([0, 0, 1279, 719], outline=preset["border_outer"], width=4)
    draw_border.rectangle([4, 4, 1275, 715], outline=preset["border_inner"], width=2)

    img.save(img_path, format="PNG", optimize=True)
    return img_path
