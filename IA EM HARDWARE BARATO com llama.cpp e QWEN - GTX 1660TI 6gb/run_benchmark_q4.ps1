<#
.SYNOPSIS
    Script de automação para benchmark com Qwen 3.5 9B Q4_K_S na GTX 1660 Ti (6GB).
.DESCRIPTION
    Executa benchmark_q4.py com saída imediata em UTF-8 no console.
#>

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " INICIANDO BENCHMARK: QWEN 3.5 9B (Q4_K_S) - LLAMA.CPP NA GTX 1660 Ti" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "benchmark_q4.py"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Arquivo benchmark_q4.py nao encontrado em $scriptPath"
    exit 1
}

python -u $scriptPath

