"""Connecteur football-data.org : matchs réels + recherche équipes locale."""
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

# Compétitions du plan gratuit où l'on va chercher les équipes
COMPETITIONS = ["PL", "PD", "SA", "BL1", "FL1", "DED", "PPL", "ELC", "CL", "BSA"]


def _headers():
    return {"X-Auth-Token": API_KEY}


def _cached(key, ttl, fetcher):
    p = CACHE_DIR / f"fd_{key}.json"
    if p.exists() and time.time() - p.stat().st_mtime < ttl:
        return json.loads(p.read_text())
    data = fetcher()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


# ---------- Matchs ----------

def get_matches(date_str):
    def fetch():
        r = requests.get(f"{BASE_URL}/matches", headers=_headers(),
                         params={"date": date_str}, timeout=15)
        r.raise_for_status()
        return r.json()
    return _cached(f"matches_{date_str}", CACHE_TTL, fetch)


def get_team_matches(team_id, limit=10):
    def fetch():
        r = requests.get(f"{BASE_URL}/teams/{team_id}/matches", headers=_headers(),
                         params={"status": "FINISHED", "limit": limit}, timeout=15)
        r.raise_for_status()
        return r.json()
    return _cached(f"team_{team_id}_last{limit}", 12 * 3600, fetch)


def _compute_form(team_id, side, limit=10):
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
            scored.append(h)
            conceded.append(a)
        else:
            scored.append(a)
            conceded.append(h)
    if not scored:
        return 0.0, 0.0, 0
    return (round(sum(scored) / len(scored), 2),
            round(sum(conceded) / len(conceded), 2),
            len(scored))


def real_matches(date_str, limit=5, min_matches=2):
    data = get_matches(date_str)
    out = []
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
                continue
            out.append({
                "home": home["name"], "away": away["name"],
                "home_scored": h_s, "home_conceded": h_c,
                "away_scored": a_s, "away_conceded": a_c,
                "kickoff": m["utcDate"], "date": m["utcDate"],
                "league": league["name"], "competition": league["name"],
                "country": (league.get("area") or {}).get("name", ""),
                "home_games_used": h_n, "away_games_used": a_n,
            })
        except Exception:
            continue
    return out


# ---------- Index des équipes (local) ----------

def _all_teams():
    """Télécharge une fois toutes les équipes des grandes ligues (cache 7 jours)."""
    def fetch():
        teams = {}
        for comp in COMPETITIONS:
            try:
                r = requests.get(
                    f"{BASE_URL}/competitions/{comp}/teams",
                    headers=_headers(), timeout=15
                )
                if r.status_code != 200:
                    continue
                for t in r.json().get("teams", []):
                    tid = t.get("id")
                    name = t.get("name") or t.get("shortName") or ""
                    if tid and name:
                        teams[str(tid)] = {
                            "id": tid,
                            "name": name,
                            "shortName": t.get("shortName", ""),
                            "tla": t.get("tla", ""),
                            "competition": comp,
                        }
                time.sleep(0.3)  # respect du rate limit
            except Exception:
                continue
        return {"teams": list(teams.values())}
    return _cached("all_teams", 7 * 24 * 3600, fetch)


def _similarity(query, name):
    """Score de similarité (0-100)."""
    q = query.lower().strip()
    n = name.lower().strip()
    if q == n:
        return 100
    if n.startswith(q):
        return 90
    if q in n:
        return 70
    # Mots en commun
    q_words = set(q.split())
    n_words = set(n.split())
    common = q_words & n_words
    if common:
        return 50 + 10 * len(common)
    # Match partiel mot à mot
    for qw in q_words:
        if len(qw) < 3:
            continue
        for nw in n_words:
            if qw == nw:
                return 60
    return 0


def search_team(name):
    """Cherche une équipe par nom dans l'index local (trié par pertinence)."""
    data = _all_teams()
    teams = data.get("teams", [])
    scored = []
    for t in teams:
        # Score basé sur le nom complet ET le nom court
        s1 = _similarity(name, t.get("name", ""))
        s2 = _similarity(name, t.get("shortName", "")) if t.get("shortName") else 0
        score = max(s1, s2)
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:10]]


def team_form_summary(team_id, n=5):
    """Résumé des N derniers matchs d'une équipe."""
    data = get_team_matches(team_id, limit=n)
    matches = [m for m in data.get("matches", [])
               if m.get("status") == "FINISHED"][:n]
    out = []
    for m in matches:
        ft = m.get("score", {}).get("fullTime", {})
        if ft.get("home") is None:
            continue
        is_home = m["homeTeam"]["id"] == team_id
        gf = ft["home"] if is_home else ft["away"]
        ga = ft["away"] if is_home else ft["home"]
        opp = m["awayTeam"]["name"] if is_home else m["homeTeam"]["name"]
        if gf > ga:
            res = "V"
        elif gf < ga:
            res = "D"
        else:
            res = "N"
        out.append({
            "date": m["utcDate"][:10],
            "result": res,
            "gf": gf, "ga": ga,
            "opponent": opp,
            "home": is_home,
            "competition": m["competition"]["name"],
        })
    return out
