from datetime import datetime, timezone

def demo_matches():
    # Jeu local uniquement pour tester l'interface.
    # Il est explicitement marqué DEMO et ne doit jamais être présenté comme une donnée réelle.
    return [{
        "id": "DEMO-001",
        "competition": "DEMO — données locales",
        "kickoff": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "home": "Équipe A",
        "away": "Équipe B",
        "source": "LOCAL_DEMO",
        "home_scored": 1.8,
        "home_conceded": 0.9,
        "away_scored": 1.3,
        "away_conceded": 1.2,
    }]
