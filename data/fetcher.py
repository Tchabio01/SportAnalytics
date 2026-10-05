"""Récupération des matchs via API-Football avec cache local."""
import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

CACHE_TTL = 6 * 3600  # 6h


def _cache_path(date: str) -> Path:
    return CACHE_DIR / f"fixtures_{date}.json"


def _load_cache(date: str):
    p = _cache_path(date)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    with open(p) as f:
        return json.load(f)


def _save_cache(date: str, data):
    with open(_cache_path(date), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_fixtures(date: str, timezone: str = "Europe/Paris", use_cache: bool = True):
    """Retourne la liste brute des matchs pour une date (AAAA-MM-JJ)."""
    if use_cache:
        cached = _load_cache(date)
        if cached is not None:
            return cached

    if not API_KEY:
        raise RuntimeError("API_FOOTBALL_KEY manquante dans .env")

    headers = {"x-apisports-key": API_KEY}
    params = {"date": date, "timezone": timezone}

    r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    errors = data.get("errors")
    if errors:
        raise RuntimeError(f"Erreur API : {errors}")

    _save_cache(date, data)
    return data


def list_matches(date: str, limit: int = 20):
    """Retourne une liste simplifiée de matchs."""
    data = get_fixtures(date)
    out = []
    for f in data.get("response", [])[:limit]:
        out.append({
            "id": f["fixture"]["id"],
            "home": f["teams"]["home"]["name"],
            "away": f["teams"]["away"]["name"],
            "league": f["league"]["name"],
            "country": f["league"]["country"],
            "kickoff": f["fixture"]["date"],
        })
    return out
