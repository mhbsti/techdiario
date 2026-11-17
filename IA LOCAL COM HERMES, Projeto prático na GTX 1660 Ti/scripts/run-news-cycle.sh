#!/usr/bin/env bash
# =============================================================================
# Dispara um Ciclo Completo do Agente Hermes v2.0 (Multi-Portal -> Pauta -> Capa)
# =============================================================================
set -euo pipefail

# Evita conversao automatica de caminhos POSIX pelo Git Bash no Windows (MSYS2)
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

TOP_COUNT=1
ALL_DAY=false
REF_MODE="none"
OVERLAY_AVATAR=false
SKIP_THUMBS=false

usage() {
    cat <<EOF
Uso: $0 [OPCOES]

Opcoes:
  -a, --all                 Extrai e produz TODAS as noticias de hoje de cada portal
  -t, --top-count <n|all>   Numero de pautas a produzir (padrao: 1, ou 'all' para todas do dia)
  -m, --model <nome>        Modelo redator (padrao: qwen3.5:9b, ou qwen2.5:3b)
  -s, --skip-thumbs         Gera apenas as pautas/roteiros sem renderizar thumbnails
  -o, --overlay-avatar      Ativa a composicao com foto do apresentador
  -h, --help                Exibe esta ajuda

Exemplos:
  $0 --all                  # Processa todas as materias de hoje dos 6 portais
  $0 -t 5                   # Processa as 5 mais relevantes do dia
  $0 --all --skip-thumbs    # Roteiriza todas do dia rapidamente
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--all)
            ALL_DAY=true
            shift
            ;;
        -t|--top-count)
            TOP_COUNT="$2"
            if [ "$TOP_COUNT" = "all" ] || [ "$TOP_COUNT" = "0" ] || [ "$TOP_COUNT" = "tudo" ]; then
                ALL_DAY=true
            fi
            shift 2
            ;;
        -m|--model)
            CUSTOM_MODEL="$2"
            shift 2
            ;;
        -s|--skip-thumbs)
            SKIP_THUMBS=true
            shift
            ;;
        -r|--ref-mode)
            REF_MODE="$2"
            shift 2
            ;;
        -o|--overlay-avatar)
            OVERLAY_AVATAR=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Opcao desconhecida: $1" >&2
            usage
            ;;
    esac
done

EXTRA_FLAGS=""
if [ "$ALL_DAY" = true ]; then
    EXTRA_FLAGS="${EXTRA_FLAGS} --all"
else
    EXTRA_FLAGS="${EXTRA_FLAGS} --top ${TOP_COUNT}"
fi

if [ "$OVERLAY_AVATAR" = true ]; then
    EXTRA_FLAGS="${EXTRA_FLAGS} --overlay-avatar"
fi

if [ "$SKIP_THUMBS" = true ]; then
    EXTRA_FLAGS="${EXTRA_FLAGS} --skip-thumbs"
fi

if [ -n "${CUSTOM_MODEL:-}" ]; then
    EXTRA_FLAGS="${EXTRA_FLAGS} --writer-model ${CUSTOM_MODEL}"
fi

CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Disparando Ciclo TECH DIÁRIO no container 'techdiario-hermes-agent'...${NC}"

# Detecta se há um TTY alocado para usar -it ou apenas -i
DOCKER_INTERACTIVE_FLAGS="-i"
if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_INTERACTIVE_FLAGS="-it"
fi

docker exec ${DOCKER_INTERACTIVE_FLAGS} -u hermes techdiario-hermes-agent python3 /opt/data/skills/techdiario/produce_cycle.py ${EXTRA_FLAGS}

