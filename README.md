# ⚽ SportAnalytics Pro

Moteur d'analyse statistique de matchs de football : modèle Poisson, historique SQLite, bot Telegram.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Fonctionnalités

- Récupération de vrais matchs (Football-Data.org)
- Probabilités 1X2, Plus de 2,5 buts, BTTS
- Scores exacts probables (top 3)
- xG attendus par équipe
- Confiance dynamique
- Cache intelligent (fixtures 6h, équipes 12h)
- Historique SQLite des prédictions
- Suivi de performance (précision 1X2 / O2.5 / BTTS)
- Export CSV
- Value betting (comparaison avec cotes bookmaker)
- Bot Telegram avec 7 commandes
- Menu interactif

## Installation

```bash
pkg update
pkg install python git
git clone https://github.com/Tchabio01/SportAnalytics.git
cd SportAnalytics
python -m pip install -r requirements.txt
cp .env.example .env
