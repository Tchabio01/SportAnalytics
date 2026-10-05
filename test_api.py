import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")

if not API_KEY:
    print("❌ API_KEY non trouvée. Vérifie le fichier .env")
    print("   pwd =", os.getcwd())
    print("   .env présent ?", os.path.exists(".env"))
    raise SystemExit(1)

print(f"✅ Clé chargée (longueur {len(API_KEY)}, début {API_KEY[:4]}…)")

BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}
params = {"date": "2026-10-05", "timezone": "Europe/Paris"}

r = requests.get(f"{BASE_URL}/fixtures", headers=headers, params=params)
data = r.json()

print("Erreurs :", data.get("errors"))
print("Résultats :", data.get("results"))

for f in data.get("response", [])[:10]:
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    league = f["league"]["name"]
    print(f"[{league}] {home} vs {away}")
