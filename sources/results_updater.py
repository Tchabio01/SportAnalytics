"""Récupère les résultats réels des matchs passés via Football-Data."""
import re
from datetime import datetime, timedelta
from data.history import pending_results, update_result
from sources.football_data import get_matches


def _norm(s):
    """Normalise un nom d'équipe pour comparaison souple."""
    s = s.lower()
    s = re.sub(r"\b(fc|afc|cf|sc|ac|club|de|the)\b", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.strip()


def _find_score(fd_matches, home_name, away_name):
    """Cherche un match correspondant dans la réponse Football-Data."""
    nh = _norm(home_name)
    na = _norm(away_name)
    for m in fd_matches:
        fh = _norm(m["homeTeam"].get("name") or m["homeTeam"].get("shortName", ""))
        fa = _norm(m["awayTeam"].get("name") or m["awayTeam"].get("shortName", ""))
        if not fh or not fa:
            continue
        if (nh in fh or fh in nh) and (na in fa or fa in na):
            ft = m.get("score", {}).get("fullTime", {})
            if ft.get("home") is not None and ft.get("away") is not None:
                return ft["home"], ft["away"]
    return None


def update_all(max_days_back=7):
    """Met à jour les résultats des prédictions en attente. Retourne (maj, echecs)."""
    pending = pending_results()
    if not pending:
        print("Aucune prédiction en attente de résultat.")
        return 0, 0

    print(f"{len(pending)} prédiction(s) à mettre à jour...")
    updated = 0
    failed = 0

    # Grouper par date de kickoff (jour)
    by_date = {}
    for p in pending:
        d = (p.get("kickoff") or "")[:10]
        if d:
            by_date.setdefault(d, []).append(p)

    for date_str, preds in by_date.items():
        try:
            data = get_matches(date_str)
            fd_matches = data.get("matches", [])
        except Exception as e:
            print(f"  ✗ {date_str} : erreur API ({e})")
            failed += len(preds)
            continue

        for p in preds:
            score = _find_score(fd_matches, p["home"], p["away"])
            if score:
                update_result(p["id"], score[0], score[1])
                print(f"  ✓ {p['home']} {score[0]}-{score[1]} {p['away']}")
                updated += 1
            else:
                print(f"  ? {p['home']} vs {p['away']} (résultat non trouvé)")
                failed += 1

    return updated, failed
