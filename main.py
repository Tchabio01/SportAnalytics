#!/usr/bin/env python3
import argparse
from datetime import date as _date

from database.database import init_db
from sources.demo import demo_matches
from analysis.analyzer import analyse
from reports.formatter import format_match
from data.history import init as init_history, save_prediction


def main():
    init_db()
    init_history()

    parser = argparse.ArgumentParser(description="SportAnalytics Pro")
    parser.add_argument("--demo", action="store_true",
                        help="tester le moteur avec des données DEMO")
    parser.add_argument("--real", nargs="?", const="today",
                        help="analyser de vrais matchs (date AAAA-MM-JJ ou 'today')")
    parser.add_argument("--stats", action="store_true",
                        help="afficher les stats de performance")
    parser.add_argument("--update", action="store_true",
                        help="récupérer les résultats réels des matchs passés")
    parser.add_argument("--export", action="store_true",
                        help="exporter les prédictions en CSV")
    parser.add_argument("--value", nargs=3, metavar=("HOME", "DRAW", "AWAY"),
                        type=float,
                        help="cotes 1X2 pour analyse value betting (avec --real)")
    parser.add_argument("--telegram", action="store_true",
                        help="démarrer le bot Telegram")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════╗
║       ⚽ SPORTANALYTICS PRO      ║
║   REAL SPORTS INTELLIGENCE       ║
╚══════════════════════════════════╝
""")

    # --- Telegram ---
    if args.telegram:
        from telegram.bot import run
        run()
        return

    # --- UPDATE ---
    if args.update:
        from sources.results_updater import update_all
        updated, failed = update_all()
        print(f"\n✅ {updated} résultat(s) mis à jour · {failed} en attente")
        return

    # --- EXPORT ---
    if args.export:
        from reports.exporter import export_csv
        export_csv()
        return

    # --- DEMO ---
    if args.demo:
        m = demo_matches()[0]
        a = analyse(m["home"], m["away"],
                    m["home_scored"], m["home_conceded"],
                    m["away_scored"], m["away_conceded"])
        print(format_match(m, a))
        return

    # --- REAL ---
    if args.real:
        from sources.football_data import real_matches

        date_str = _date.today().isoformat() if args.real == "today" else args.real
        print(f"🔎 Matchs du {date_str} (source : Football-Data)\n")

        matches = real_matches(date_str, limit=5)
        if not matches:
            print("Aucun match exploitable.")
            return

        odds = args.value  # (home, draw, away) ou None

        for m in matches:
            a = analyse(m["home"], m["away"],
                        m["home_scored"], m["home_conceded"],
                        m["away_scored"], m["away_conceded"],
                        home_games=m.get("home_games_used", 0),
                        away_games=m.get("away_games_used", 0))
            save_prediction(m, a)
            print(format_match(m, a))

            if odds:
                from reports.value import print_value_report
                print()
                print_value_report(a.get("probabilities", {}),
                                   odds[0], odds[1], odds[2])
            print()
        return

    # --- STATS ---
    if args.stats:
        from data.history import stats, recent, pending_count
        s = stats()
        print("📊 STATS DU MODÈLE")
        print(f"Total prédictions       : {s['total']}")
        print(f"Avec résultat connu     : {s['with_result']}")
        print(f"En attente de résultat  : {pending_count()}")
        print()
        if s["with_result"]:
            print(f"Précision 1X2  : {s['accuracy']} %  ({s['hits']}/{s['with_result']})")
            print(f"Précision O2.5 : {s['over_accuracy']} %  ({s['over_hits']}/{s['with_result']})")
            print(f"Précision BTTS : {s['btts_accuracy']} %  ({s['btts_hits']}/{s['with_result']})")
        else:
            print("Pas encore assez de résultats pour calculer la précision.")
        print()
        print("Dernières prédictions :")
        for r in recent(5):
            ph = r['p_home'] or 0
            pd = r['p_draw'] or 0
            pa = r['p_away'] or 0
            res = ""
            if r.get("actual_home") is not None:
                hit = "✅" if r.get("outcome_hit") else "❌"
                res = f" | réel {r['actual_home']}-{r['actual_away']} {hit}"
            print(f"  {r['date_created']} · {r['home']} vs {r['away']}")
            print(f"     1X2 : {ph:.0f}/{pd:.0f}/{pa:.0f}  |  conf {r['confidence']}{res}")
        return

    # --- Menu par défaut ---
    print("Utilise `python menu.py` pour le menu interactif, ou :")
    print("  python main.py --real 2026-10-10")
    print("  python main.py --real today")
    print("  python main.py --stats")
    print("  python main.py --update")
    print("  python main.py --export")
    print("  python main.py --real today --value 2.10 3.40 3.60")


if __name__ == "__main__":
    main()
