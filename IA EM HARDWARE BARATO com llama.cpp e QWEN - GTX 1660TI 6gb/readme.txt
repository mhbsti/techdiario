================================================================================
INSTRUCOES DE DOWNLOAD DOS MODELOS E CONFIGURACAO DO LLAMA.CPP
================================================================================
Projeto: IA em Hardware Barato com llama.cpp e Qwen 3.5 - GTX 1660 Ti (6GB VRAM)
Canal YouTube: @techdiario

Devido ao tamanho dos arquivos binarios e modelos GGUF (~10 GB somados),
os modelos de IA e executaveis compilados nao sao armazenados no Git.
Siga as instrucoes abaixo para preparar o ambiente local e rodar os benchmarks.

--------------------------------------------------------------------------------
1. MODELOS DE IA NECESSARIOS (HUGGING FACE)
--------------------------------------------------------------------------------
Os scripts de benchmark buscam exatamente os seguintes arquivos nesta pasta:

  - Qwen3.5-9B-Q3_K_S.gguf  (~4.01 GiB - recomendado para 100% VRAM livre)
  - Qwen3.5-9B-Q4_K_S.gguf  (~5.02 GiB - quantizacao superior de 4-bits)

OPCAO A: Download via Navegador (Hugging Face)
Acesse a pagina do modelo no Hugging Face:
  Repositorio: https://huggingface.co/unsloth/Qwen3.5-9B-GGUF
  - Va na aba "Files and versions"
  - Procure por "Qwen3.5-9B-Q3_K_S.gguf" e clique em "Download"
  - Procure por "Qwen3.5-9B-Q4_K_S.gguf" e clique em "Download"
  - Mova os arquivos baixados diretamente para esta pasta:
    "techdiario\IA EM HARDWARE BARATO com llama.cpp e QWEN - GTX 1660TI 6gb\"

OPCAO B: Download via Hugging Face CLI (Recomendado)
Se tiver o Python com huggingface_hub instalado:
  pip install huggingface_hub

Execute no terminal dentro desta pasta:
  huggingface-cli download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q3_K_S.gguf --local-dir . --local-dir-use-symlinks False
  huggingface-cli download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_S.gguf --local-dir . --local-dir-use-symlinks False

OPCAO C: Download direto via PowerShell (curl.exe)
Execute em uma janela do PowerShell nesta pasta:
  curl.exe -L -o "Qwen3.5-9B-Q3_K_S.gguf" "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q3_K_S.gguf"
  curl.exe -L -o "Qwen3.5-9B-Q4_K_S.gguf" "https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_S.gguf"

--------------------------------------------------------------------------------
2. MOTOR DE INFERENCIA (LLAMA.CPP COM CUDA)
--------------------------------------------------------------------------------
Os scripts de benchmark executam o servidor local via:
  bin\llama\llama-server.exe

Para configurar o llama.cpp:
1. Acesse os releases oficiais do llama.cpp no GitHub:
   https://github.com/ggerganov/llama.cpp/releases
2. Baixe o pacote pre-compilado para Windows com suporte a CUDA 12:
   Exemplo: llama-b<versao>-bin-win-cuda-cu12.x-x64.zip
   e tambem o pacote de dependencias cudart (se aplicavel):
   cudart-llama-bin-win-cu12.x-x64.zip
3. Extraia todos os arquivos .exe e .dll dentro da pasta:
   "bin\llama\" deste diretorio.

--------------------------------------------------------------------------------
3. EXECUTANDO OS BENCHMARKS
--------------------------------------------------------------------------------
Com os arquivos posicionados, basta executar:

  - Para benchmark do modelo Q3_K_S:
    Clique duas vezes em "run_benchmark.bat" ou execute no PowerShell:
    .\run_benchmark.ps1

  - Para benchmark do modelo Q4_K_S:
    Clique duas vezes em "run_benchmark_q4.bat" ou execute no PowerShell:
    .\run_benchmark_q4.ps1

Os relatorios comparativos serao atualizados automaticamente em formato Markdown
e os logs detalhados de inferencia serao salvos em:
  - llama_server.log
  - llama_server_q4.log
================================================================================
