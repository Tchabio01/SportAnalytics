"""Formatage de l'affichage d'un match analysé."""
import math
from datetime import datetime


def _poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _predict_scores(h_xg, a_xg, top=3):
    """Retourne les N scores exacts les plus probables (modèle Poisson)."""
    scores = []
    for h in range(6):
        for a in range(6):
            p = _poisson(h, h_xg) * _poisson(a, a_xg)
            scores.append((p, h, a))
    scores.sort(reverse=True)
    return scores[:top]


def _fmt_date(iso_str):
    """Formate une date ISO en français court. Ex: 'Sam. 10 oct. 11:30'."""
    if not iso_str:
        return "date inconnue"
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        jours = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."]
        mois = ["jan.", "fév.", "mars", "avr.", "mai", "juin",
                "juil.", "août", "sep.", "oct.", "nov.", "déc."]
        return f"{jours[dt.weekday()]} {dt.day} {mois[dt.month - 1]} {dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return iso_str


def _confidence_from_data(match):
    """Confiance dynamique selon le nombre de matchs utilisés pour la forme."""
    h_n = match.get("home_games_used", 0) or 0
    a_n = match.get("away_games_used", 0) or 0
    n_min = min(h_n, a_n)
    if n_min >= 8:
        return 85
    if n_min >= 6:
        return 75
    if n_min >= 4:
        return 65
    if n_min >= 2:
        return 55
    return 40


def format_match(match, analysis):
    home = match.get("home", "?")
    away = match.get("away", "?")
    comp = match.get("competition") or match.get("league") or "Compétition inconnue"
    country = match.get("country") or ""
    kickoff = _fmt_date(match.get("kickoff") or match.get("date"))

    # Structure renvoyée par analyze()
    probs = analysis.get("probabilities", {})
    xgs = analysis.get("expected_goals", {})

    p_home = probs.get("home_win", 0)
    p_draw = probs.get("draw", 0)
    p_away = probs.get("away_win", 0)
    over25 = probs.get("over_2_5", 0)
    btts = probs.get("btts_yes", 0)
    xg_h = xgs.get("home", 0)
    xg_a = xgs.get("away", 0)

    # Confiance calculée à partir des données du match
    conf = _confidence_from_data(match)

    h_n = match.get("home_games_used", 0) or 0
    a_n = match.get("away_games_used", 0) or 0

    lines = []
    lines.append("⚽ ANALYSE MATCH")
    lines.append("")
    if country:
        lines.append(f"🏆 {comp} — {country}")
    else:
        lines.append(f"🏆 {comp}")
    lines.append(f"🏠 {home} — {away}")
    lines.append(f"📅 {kickoff}")
    if h_n and a_n:
        lines.append(f"📊 Basé sur : {h_n} matchs dom. / {a_n} matchs ext.")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("📊 PROBABILITÉS")
    lines.append(f"🏠 Victoire {home} : {p_home:.1f} %")
    lines.append(f"🤝 Nul : {p_draw:.1f} %")
    lines.append(f"✈️ Victoire {away} : {p_away:.1f} %")
    lines.append("")
    lines.append(f"⚽ Plus de 2,5 buts : {over25:.1f} %")
    lines.append(f"🎯 BTTS : {btts:.1f} %")

    if xg_h and xg_a:
        lines.append("")
        lines.append("🎲 SCORES PROBABLES")
        for p, h, a in _predict_scores(xg_h, xg_a, top=3):
            lines.append(f"   {h}-{a} : {p * 100:.1f} %")

    lines.append("")
    lines.append("📈 BUTS ATTENDUS")
    lines.append(f"{home} : {xg_h}")
    lines.append(f"{away} : {xg_a}")
    lines.append("")
    lines.append(f"🧠 CONFIANCE : {conf}/100")
    lines.append("")
    lines.append("⚠️ Analyse statistique uniquement.")
    lines.append("Aucun résultat n'est garanti.")

    return "\n".join(lines)
