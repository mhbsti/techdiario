# Script de Execução Automatizada do Benchmark
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " EXECUTANDO BENCHMARK: QWEN 3.5 9B NA GTX 1660 Ti (6GB VRAM 100%)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$pythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    Write-Host "[ERRO] Python não foi encontrado no PATH do sistema!" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $PSScriptRoot "benchmark.py"
& $pythonExe -u $scriptPath

