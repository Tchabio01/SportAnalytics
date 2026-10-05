import math
from statistics import mean


def poisson_pmf(lam, k):
    if lam < 0:
        return 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def analyse(home, away, home_scored=None, home_conceded=None,
            away_scored=None, away_conceded=None,
            home_games=0, away_games=0):
    values = [home_scored, home_conceded, away_scored, away_conceded]
    available = [x for x in values
                 if isinstance(x, (int, float)) and x >= 0]

    if len(available) < 2:
        return {
            "status": "DONNÉES INSUFFISANTES",
            "confidence": 0,
            "probabilities": {},
            "expected_goals": {},
            "message": "Impossible de produire une analyse robuste "
                       "sans statistiques suffisantes."
        }

    hs = home_scored if home_scored is not None else mean(available)
    hc = home_conceded if home_conceded is not None else mean(available)
    aw = away_scored if away_scored is not None else mean(available)
    ac = away_conceded if away_conceded is not None else mean(available)

    home_lambda = max(0.05, (hs + ac) / 2)
    away_lambda = max(0.05, (aw + hc) / 2)

    home_win = draw = away_win = over25 = btts = 0.0
    for h in range(9):
        for a in range(9):
            p = poisson_pmf(home_lambda, h) * poisson_pmf(away_lambda, a)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
            if h + a >= 3:
                over25 += p
            if h >= 1 and a >= 1:
                btts += p

    n_min = min(home_games or 0, away_games or 0)
    if n_min >= 8:
        confidence = 85
    elif n_min >= 6:
        confidence = 75
    elif n_min >= 4:
        confidence = 65
    elif n_min >= 2:
        confidence = 55
    elif n_min >= 1:
        confidence = 45
    else:
        confidence = 40

    return {
        "status": "DONNÉES SUFFISANTES",
        "confidence": confidence,
        "probabilities": {
            "home_win": round(home_win * 100, 1),
            "draw": round(draw * 100, 1),
            "away_win": round(away_win * 100, 1),
            "over_2_5": round(over25 * 100, 1),
            "btts_yes": round(btts * 100, 1),
        },
        "expected_goals": {
            "home": round(home_lambda, 2),
            "away": round(away_lambda, 2),
        },
        "message": "Tendance statistique calculée avec un modèle de "
                   "Poisson simplifié."
    }
