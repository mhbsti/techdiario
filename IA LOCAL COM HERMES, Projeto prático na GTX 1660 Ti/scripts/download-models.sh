#!/usr/bin/env bash
# =============================================================================
# Script de Preparacao de Modelos GGUF - Qwen-Image-2.1 (CANAL TECH DIARIO)
# =============================================================================
# Nota: Os modelos LLM (qwen2.5:3b, qwen2.5:1.5b, nomic-embed-text) sao
# gerenciados automaticamente pelo container 'techdiario-ollama'.
# Esta pasta 'models' contem estritamente os 4 modelos do motor grafico Qwen-Image.
# =============================================================================
set -euo pipefail

# Evita conversao automatica de caminhos POSIX pelo Git Bash no Windows (MSYS2)
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${SCRIPT_DIR}/../models"
mkdir -p "${MODELS_DIR}"
MODELS_DIR="$(cd "${MODELS_DIR}" && pwd)"

CYAN='\033[0;36m'
GRAY='\033[0;90m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${CYAN}Pasta de modelos do Qwen-Image: ${MODELS_DIR}${NC}"

get_file_size() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo 0
        return
    fi
    if command -v stat >/dev/null 2>&1; then
        stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || wc -c < "$file"
    else
        wc -c < "$file"
    fi
}

declare -a DOWNLOADS=(
    "[1/4]|qwen-image-2.1-Q3_K_XL.gguf|Modelo de Difusao Principal (Unsloth Dynamic 2.0 Q3_K_XL)|https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF/resolve/main/qwen-image-2.1-Q3_K_XL.gguf|3500000000"
    "[2/4]|qwen_image_2.1_vae_bf16.safetensors|VAE Oficial Qwen-Image-2.1 (BF16)|https://huggingface.co/unsloth/Qwen-Image-2.1-FP8/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors|200000000"
    "[3/4]|Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf|Text Encoder Multimodal Qwen3-VL-8B (Q3_K_XL otimizado p/ 6GB VRAM)|https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf|3500000000"
    "[4/4]|mmproj-F16.gguf|Vision Projector Multimodal|https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/mmproj-F16.gguf|500000000"
)

for entry in "${DOWNLOADS[@]}"; do
    IFS="|" read -r step name desc url min_bytes <<< "$entry"
    dest="${MODELS_DIR}/${name}"
    needs_download=true

    if [ -f "$dest" ]; then
        size=$(get_file_size "$dest")
        if [ "$size" -ge "$min_bytes" ]; then
            size_gb=$(awk "BEGIN {printf \"%.2f\", $size / 1073741824}")
            echo -e "${GRAY}${step} ${name} ja baixado (${size_gb} GB).${NC}"
            needs_download=false
        fi
    fi

    if [ "$needs_download" = true ]; then
        echo -e "${CYAN}${step} Baixando ${name} - ${desc}...${NC}"
        curl -L -C - --retry 5 --retry-delay 3 -o "$dest" "$url"
    fi
done

echo -e "\n${GREEN}Todos os modelos do Qwen-Image em '${MODELS_DIR}' estao prontos!${NC}"
ls -lh "${MODELS_DIR}"

