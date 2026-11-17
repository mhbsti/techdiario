#!/usr/bin/env python3
"""
Disparador do Ciclo Completo do TECH DIÁRIO para o Cron do Hermes.
"""
import os
import sys
from pathlib import Path

SKILLS_DIR = Path("/opt/data/skills/techdiario")
sys.path.append(str(SKILLS_DIR))

from produce_cycle import run_full_cycle

if __name__ == "__main__":
    top = None if os.getenv("TECHDIARIO_PRODUCE_ALL", "0") == "1" else 3
    all_day = (top is None)

    for arg in sys.argv[1:]:
        if arg.lower() in ("--all", "-a", "all", "0", "tudo"):
            all_day = True
            top = None
        elif arg.isdigit():
            top = int(arg)
            all_day = False

    run_full_cycle(top_count=top, all_day=all_day, overlay_avatar=False)

