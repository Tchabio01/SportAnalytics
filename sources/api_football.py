"""Connecteur API-Football : renvoie des matchs au format attendu par analyze().

Stratégie pour le plan gratuit :
  - /teams/statistics est limité aux saisons 2022-2024 → inutilisable
  - On récupère les N derniers matchs via /fixtures?team=X&last=N (autorisé)
  - On calcule nous-mêmes les moyennes buts pour/contre à domicile / extérieur
"""
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from data.fetcher import get_fixtures, API_KEY, BASE_URL

load_dotenv()

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
TEAM_HISTORY_TTL = 12 * 3600  # 12h
N_LAST = 20  # nb de matchs récents à analyser par équipe


def _team_history_path(team_id: int):
    return CACHE_DIR / f"team_{team_id}_last{N_LAST}.json"


def get_team_history(team_id: int) -> list:
    """Récupère les N derniers matchs d'une équipe (cache 12h)."""
    p = _team_history_path(team_id)
    if p.exists() and time.time() - p.stat().st_mtime < TEAM_HISTORY_TTL:
        return json.loads(p.read_text()).get("response", [])

    if not API_KEY:
        raise RuntimeError("API_FOOTBALL_KEY manquante dans .env")

    headers = {"x-apisports-key": API_KEY}
    params = {"team": team_id, "last": N_LAST}
    r = requests.get(f"{BASE_URL}/fixtures",
                     headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    if data.get("errors"):
        raise RuntimeError(f"Fixtures team {team_id}: {data['errors']}")

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data.get("response", [])


def _compute_stats(history: list, team_id: int, side: str):
    """
    Calcule (moyenne buts pour, moyenne buts contre) pour une équipe.
    side = 'home' → uniquement ses matchs à domicile
    side = 'away' → uniquement ses matchs à l'extérieur
    """
    scored = []
    conceded = []

    for f in history:
        teams = f["teams"]
        goals = f.get("goals", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue  # match pas joué ou score inconnu

        is_home = teams["home"]["id"] == team_id
        is_away = teams["away"]["id"] == team_id

        if side == "home" and not is_home:
            continue
        if side == "away" and not is_away:
            continue

        if is_home:
            scored.append(goals["home"])
            conceded.append(goals["away"])
        elif is_away:
            scored.append(goals["away"])
            conceded.append(goals["home"])

    if not scored:
        return 0.0, 0.0

    return sum(scored) / len(scored), sum(conceded) / len(conceded)


def real_matches(date_str: str, limit: int = 5, min_matches: int = 3) -> list:
    """
    Renvoie des matchs au format compatible avec analyze() et demo_matches().
    min_matches = nb minimum de matchs récents requis par équipe pour retenir le match.
    """
    fixtures = get_fixtures(date_str)
    out = []
    skipped = []

    for f in fixtures.get("response", []):
        if len(out) >= limit:
            break

        league = f["league"]
        home = f["teams"]["home"]
        away = f["teams"]["away"]

        try:
            h_hist = get_team_history(home["id"])
            a_hist = get_team_history(away["id"])

            h_home_games = [x for x in h_hist
                            if x["teams"]["home"]["id"] == home["id"]]
            a_away_games = [x for x in a_hist
                            if x["teams"]["away"]["id"] == away["id"]]

            if len(h_home_games) < min_matches or len(a_away_games) < min_matches:
                skipped.append(
                    f"{home['name']} vs {away['name']} "
                    f"(historique insuffisant: {len(h_home_games)} dom / {len(a_away_games)} ext)"
                )
                continue

            h_scored, h_conc = _compute_stats(h_hist, home["id"], "home")
            a_scored, a_conc = _compute_stats(a_hist, away["id"], "away")

            if h_scored == 0 and a_scored == 0:
                skipped.append(f"{home['name']} vs {away['name']} (0 buts marqués)")
                continue

            out.append({
                "home": home["name"],
                "away": away["name"],
                "home_scored": round(h_scored, 2),
                "home_conceded": round(h_conc, 2),
                "away_scored": round(a_scored, 2),
                "away_conceded": round(a_conc, 2),
                "kickoff": f["fixture"]["date"],
                "league": league["name"],
                "country": league["country"],
                "home_games_used": len(h_home_games),
                "away_games_used": len(a_away_games),
            })

        except Exception as e:
            skipped.append(f"{home['name']} vs {away['name']} → {e}")
            continue

    if skipped:
        print(f"[api_football] {len(skipped)} match(s) ignoré(s) :")
        for s in skipped[:5]:
            print(f"  · {s}")
        if len(skipped) > 5:
            print(f"  … et {len(skipped) - 5} autres")

    return out
