import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SPORT_API_KEY = os.getenv("SPORT_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

DB_PATH = BASE_DIR / "data" / "sportanalytics.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
