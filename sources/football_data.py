"""Connecteur football-data.org : matchs réels + forme récente.
Plan gratuit : 10 req/min, grands championnats européens uniquement.
"""
import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_KEY")
BASE_URL = "https://api.football-data.org/v4"
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 6 * 3600


def _headers():
    return {"X-Auth-Token": API_KEY}


def _cached(key, ttl, fetcher):
    p = CACHE_DIR / f"fd_{key}.json"
    if p.exists() and time.time() - p.stat().st_mtime < ttl:
        return json.loads(p.read_text())
    data = fetcher()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def get_matches(date_str):
    """Matchs d'une date (AAAA-MM-JJ)."""
    def fetch():
        r = requests.get(f"{BASE_URL}/matches", headers=_headers(),
                         params={"date": date_str}, timeout=15)
        r.raise_for_status()
        return r.json()
    return _cached(f"matches_{date_str}", CACHE_TTL, fetch)


def get_team_matches(team_id, limit=10):
    """N derniers matchs terminés d'une équipe."""
    def fetch():
        r = requests.get(f"{BASE_URL}/teams/{team_id}/matches", headers=_headers(),
                         params={"status": "FINISHED", "limit": limit}, timeout=15)
        r.raise_for_status()
        return r.json()
    return _cached(f"team_{team_id}_last{limit}", 12 * 3600, fetch)


def _compute_form(team_id, side, limit=10):
    """
    Retourne (moy_buts_pour, moy_buts_contre, nb_matchs) sur les N derniers
    matchs à domicile (side='home') ou extérieur (side='away').
    """
    data = get_team_matches(team_id, limit=limit * 2)
    scored, conceded = [], []

    for m in data.get("matches", []):
        if m.get("status") != "FINISHED":
            continue
        ft = m.get("score", {}).get("fullTime", {})
        h, a = ft.get("home"), ft.get("away")
        if h is None or a is None:
            continue

        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]

        if side == "home" and home_id != team_id:
            continue
        if side == "away" and away_id != team_id:
            continue

        if home_id == team_id:
            scored.append(h); conceded.append(a)
        else:
            scored.append(a); conceded.append(h)

    if not scored:
        return 0.0, 0.0, 0
    return (round(sum(scored) / len(scored), 2),
            round(sum(conceded) / len(conceded), 2),
            len(scored))


def real_matches(date_str, limit=5, min_matches=2):
    """
    Retourne des matchs au format compatible avec analyze() / format_match().
    Fournit à la fois 'league' et 'competition' pour compatibilité.
    """
    data = get_matches(date_str)
    out, skipped = [], []

    for m in data.get("matches", []):
        if len(out) >= limit:
            break

        home = m["homeTeam"]
        away = m["awayTeam"]
        league = m["competition"]

        try:
            h_s, h_c, h_n = _compute_form(home["id"], "home")
            a_s, a_c, a_n = _compute_form(away["id"], "away")

            if h_n < min_matches or a_n < min_matches:
                skipped.append(f"{home['name']} vs {away['name']} (historique {h_n}/{a_n})")
                continue

            out.append({
                "home": home["name"],
                "away": away["name"],
                "home_scored": h_s,
                "home_conceded": h_c,
                "away_scored": a_s,
                "away_conceded": a_c,
                "kickoff": m["utcDate"],
                "date": m["utcDate"],
                "league": league["name"],
                "competition": league["name"],
                "country": (league.get("area") or {}).get("name", ""),
                "home_games_used": h_n,
                "away_games_used": a_n,
            })
        except Exception as e:
            skipped.append(f"{home['name']} vs {away['name']} -> {e}")

    if skipped:
        print(f"[football-data] {len(skipped)} match(s) ignoré(s) :")
        for s in skipped[:5]:
            print(f"  - {s}")
        if len(skipped) > 5:
            print(f"  ... et {len(skipped) - 5} autres")

    return out
