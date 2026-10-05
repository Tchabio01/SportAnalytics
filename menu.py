"""Menu interactif pour SportAnalytics Pro."""
import subprocess
import sys


def _run(args):
    subprocess.run([sys.executable, "main.py"] + args)


def main():
    print("""
╔══════════════════════════════════╗
║       ⚽ SPORTANALYTICS PRO      ║
║   REAL SPORTS INTELLIGENCE       ║
╚══════════════════════════════════╝
""")
    while True:
        print("""
──── MENU ────
[1] Analyser les matchs d'aujourd'hui
[2] Analyser une date précise
[3] Mode démo (données locales)
[4] Voir les stats du modèle
[5] Mettre à jour les résultats réels
[6] Exporter en CSV
[7] Quitter
""")
        try:
            choix = input("Choix : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            return

        if choix == "1":
            _run(["--real", "today"])
        elif choix == "2":
            d = input("Date (AAAA-MM-JJ) : ").strip()
            if d:
                _run(["--real", d])
        elif choix == "3":
            _run(["--demo"])
        elif choix == "4":
            _run(["--stats"])
        elif choix == "5":
            _run(["--update"])
        elif choix == "6":
            _run(["--export"])
        elif choix == "7":
            print("Au revoir.")
            return
        else:
            print("Choix invalide.")


if __name__ == "__main__":
    main()
