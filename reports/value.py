"""Détection de value bets : compare les probas du modèle aux cotes bookmaker."""
from datetime import datetime
from data.history import recent


def _implied(odd):
    """Probabilité implicite d'une cote (avant marge bookmaker)."""
    if not odd or odd <= 1:
        return 0.0
    return 1.0 / odd


def compute_edge(model_prob_pct, odd):
    """
    Retourne l'edge (avantage) en %.
    > 0 : pari à valeur positive (théorique)
    < 0 : cote défavorable
    """
    implied = _implied(odd) * 100
    return round(model_prob_pct - implied, 2)


def evaluate_bet(model_prob_pct, odd, stake=10):
    """
    Retourne (edge %, EV €, verdict).
    EV = (p * (odd - 1) - (1 - p)) * stake
    """
    p = model_prob_pct / 100
    ev = (p * (odd - 1) - (1 - p)) * stake
    edge = compute_edge(model_prob_pct, odd)
    if edge >= 5:
        verdict = "🔥 VALUE"
    elif edge >= 2:
        verdict = "✅ Correct"
    elif edge >= -2:
        verdict = "😐 Neutre"
    else:
        verdict = "❌ Défavorable"
    return edge, round(ev, 2), verdict


def print_value_report(match_probs, odds_home=None, odds_draw=None, odds_away=None, stake=10):
    """
    Affiche un rapport de value pour un match.
    match_probs = {'home_win': 55.1, 'draw': 26.2, 'away_win': 18.7}
    """
    print("💰 ANALYSE VALUE BETTING")
    print(f"Mise de référence : {stake} €\n")

    labels = [
        ("Victoire domicile", "home_win", odds_home),
        ("Nul", "draw", odds_draw),
        ("Victoire extérieur", "away_win", odds_away),
    ]

    for label, key, odd in labels:
        if odd is None:
            continue
        prob = match_probs.get(key, 0)
        edge, ev, verdict = evaluate_bet(prob, odd, stake)
        print(f"{label:20} | modèle {prob:5.1f}%  cote {odd:.2f}  "
              f"edge {edge:+5.2f}%  EV {ev:+5.2f}€  {verdict}")
