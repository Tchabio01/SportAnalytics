"""Analyse et update automatiques en boucle."""
import time
import subprocess
import sys
from datetime import datetime

PY = sys.executable


def run(args):
    subprocess.run([PY, "main.py"] + args)


while True:
    now = datetime.now()
    print(f"[{now:%H:%M}] Analyse du jour…")
    run(["--real", "today"])
    print(f"[{now:%H:%M}] Update résultats…")
    run(["--update"])
    print(f"[{now:%H:%M}] Prochain cycle dans 6h.")
    time.sleep(6 * 3600)
