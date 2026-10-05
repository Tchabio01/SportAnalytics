"""Export des prédictions en CSV."""
import csv
from pathlib import Path
from data.history import recent


def export_csv(path="predictions_export.csv", n=1000):
    rows = recent(n)
    if not rows:
        print("Aucune prédiction à exporter.")
        return

    p = Path(path)
    fields = [
        "id", "date_created", "kickoff", "competition",
        "home", "away",
        "p_home", "p_draw", "p_away", "over_25", "btts",
        "xg_home", "xg_away", "confidence",
        "actual_home", "actual_away",
        "outcome_hit", "over_hit", "btts_hit",
    ]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})
    print(f"✅ {len(rows)} prédictions exportées vers {p.resolve()}")
