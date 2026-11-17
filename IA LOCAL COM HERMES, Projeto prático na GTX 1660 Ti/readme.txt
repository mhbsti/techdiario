================================================================================
INSTRUCOES DE DOWNLOAD DOS MODELOS E CONFIGURACAO DO ESTUDIO HERMES
================================================================================
Projeto: IA Local com Hermes, Projeto Pratico na GTX 1660 Ti (6GB VRAM)
Canal YouTube: @techdiario

Devido ao tamanho dos modelos de IA (~18 GB somados), os pesos GGUF,
SafeTensors e volumes locais do Docker nao sao armazenados no Git.
Siga as instrucoes abaixo para preparar o ambiente e rodar o estudio.

--------------------------------------------------------------------------------
1. MODELOS GRAFICOS QWEN-IMAGE-2.1 (PASTA 'models/')
--------------------------------------------------------------------------------
O motor grafico techdiario-qwen-image necessita dos seguintes 4 modelos na pasta 'models/':

1. qwen-image-2.1-Q3_K_XL.gguf (~3.36 GiB - Difusao Principal)
   URL: https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF/resolve/main/qwen-image-2.1-Q3_K_XL.gguf

2. qwen_image_2.1_vae_bf16.safetensors (~644 MiB - VAE Oficial BF16)
   URL: https://huggingface.co/unsloth/Qwen-Image-2.1-FP8/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors

3. Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf (~4.01 GiB - Text Encoder Multimodal)
   URL: https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf

4. mmproj-F16.gguf (~1.07 GiB - Vision Projector Multimodal)
   URL: https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/mmproj-F16.gguf

(Opcional para Redacao Customizada):
5. Qwen3.5-9B-Q3_K_S.gguf (~4.01 GiB - LLM Redator via Ollama Modelfile)
   URL: https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q3_K_S.gguf

COMO BAIXAR:

Opcao A (Script Automatizado via Bash / Git Bash):
  Execute dentro da pasta do projeto:
  bash scripts/download-models.sh

Opcao B (Download via PowerShell - curl.exe):
  cd models
  curl.exe -L -C - -o "qwen-image-2.1-Q3_K_XL.gguf" "https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF/resolve/main/qwen-image-2.1-Q3_K_XL.gguf"
  curl.exe -L -C - -o "qwen_image_2.1_vae_bf16.safetensors" "https://huggingface.co/unsloth/Qwen-Image-2.1-FP8/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors"
  curl.exe -L -C - -o "Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf" "https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf"
  curl.exe -L -C - -o "mmproj-F16.gguf" "https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/mmproj-F16.gguf"
  curl.exe -L -C - -o "Qwen3.5-9B-Q3_K_S.gguf" "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q3_K_S.gguf"

Opcao C (Download via Hugging Face CLI):
  pip install huggingface_hub
  cd models
  huggingface-cli download unsloth/Qwen-Image-2.1-GGUF qwen-image-2.1-Q3_K_XL.gguf --local-dir . --local-dir-use-symlinks False
  huggingface-cli download unsloth/Qwen-Image-2.1-FP8 vae/qwen_image_2.1_vae_bf16.safetensors --local-dir . --local-dir-use-symlinks False
  huggingface-cli download unsloth/Qwen3-VL-8B-Instruct-GGUF Qwen3-VL-8B-Instruct-UD-Q3_K_XL.gguf --local-dir . --local-dir-use-symlinks False
  huggingface-cli download unsloth/Qwen3-VL-8B-Instruct-GGUF mmproj-F16.gguf --local-dir . --local-dir-use-symlinks False
  huggingface-cli download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q3_K_S.gguf --local-dir . --local-dir-use-symlinks False

--------------------------------------------------------------------------------
2. MODELOS DO OLLAMA (GERENCIADOS PELO CONTAINER)
--------------------------------------------------------------------------------
Apos iniciar o container techdiario-ollama, os modelos leves sao baixados via:
  docker exec -it techdiario-ollama ollama pull nomic-embed-text
  docker exec -it techdiario-ollama ollama pull qwen2.5:1.5b
  docker exec -it techdiario-ollama ollama pull qwen2.5:3b

Para criar o modelo Qwen 3.5 9B quantizado no Ollama usando o Modelfile:
  docker exec -it techdiario-ollama ollama create qwen3.5:9b -f /models/Modelfile-qwen3.5-9b

--------------------------------------------------------------------------------
3. CONFIGURACAO DO AMBIENTE E INICIALIZACAO
--------------------------------------------------------------------------------
1. Copie o arquivo de exemplo de ambiente:
   copy .env.example .env

2. Suba todos os servicos com o Docker Compose:
   docker compose up -d

3. Acompanhe os servicos:
   - Dashboard do Hermes Agent: http://localhost:9119 (User: techdiario / Pass: techdiario)
   - Studio Thumbnail API:       http://localhost:8090/docs
   - Base Vetorial Qdrant:       http://localhost:6333/dashboard
   - Ollama API:                 http://localhost:11434

4. Para rodar o ciclo completo de noticias e capas:
   bash scripts/run-news-cycle.sh

5. Para rodar o benchmark de telemetria da GPU e CPU:
   python scripts/benchmark_performance.py
================================================================================
