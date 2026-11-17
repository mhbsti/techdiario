@echo off
chcp 65001 > nul
title Benchmark Qwen 3.5 9B (Q4_K_S) - GTX 1660 Ti
echo =================================================================
echo  INICIANDO BENCHMARK: QWEN 3.5 9B (Q4_K_S) - LLAMA.CPP NA GTX 1660 Ti
echo =================================================================
python -u "%~dp0benchmark_q4.py"
pause

