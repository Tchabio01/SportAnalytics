"""Serveur Flask : dashboard + API REST pour SportAnalytics."""
import os
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# ---------- Dashboard ----------

@app.route("/")
def index():
    """Page principale du dashboard."""
    from data.history import stats, recent, pending_count
    from datetime import datetime

    s = stats()
    recents = recent(20)
    return render_template(
        "dashboard.html",
        stats=s,
        recents=recents,
        pending=pending_count(),
        now=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


# ---------- API REST ----------

@app.route("/api/health")
def health():
    """Vérifie que le service répond."""
    return jsonify({"status": "ok", "service": "sportanalytics"})


@app.route("/api/stats")
def api_stats():
    """Statistiques globales du modèle."""
    from data.history import stats, pending_count
    s = stats()
    s["pending"] = pending_count()
    return jsonify(s)


@app.route("/api/predictions")
def api_predictions():
    """Dernières prédictions (paramètre n, max 100)."""
    from data.history import recent
    n = min(int(request.args.get("n", 10)), 100)
    return jsonify({"predictions": recent(n)})


@app.route("/api/predict")
def api_predict():
    """
    Analyse d'un match.
    Usage : /api/predict?home=Arsenal&away=Leeds
    """
    home = request.args.get("home", "").strip()
    away = request.args.get("away", "").strip()
    if not home or not away:
        return jsonify({"error": "Paramètres 'home' et 'away' requis"}), 400

    from sources.football_data import search_team, _compute_form
    from analysis.analyzer import analyse

    try:
        t1 = search_team(home)
        t2 = search_team(away)
        if not t1 or not t2:
            return jsonify({"error": "Équipe(s) introuvable(s)"}), 404

        t1 = t1[0]
        t2 = t2[0]
        h_s, h_c, h_n = _compute_form(t1["id"], "home")
        a_s, a_c, a_n = _compute_form(t2["id"], "away")

        result = analyse(
            t1["name"], t2["name"],
            h_s, h_c, a_s, a_c,
            home_games=h_n, away_games=a_n,
        )
        result["home"] = t1["name"]
        result["away"] = t2["name"]
        result["disclaimer"] = (
            "Analyse statistique uniquement. "
            "Ne constitue pas un conseil de pari."
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/h2h")
def api_h2h():
    """Confrontations directes entre 2 équipes."""
    home = request.args.get("home", "").strip()
    away = request.args.get("away", "").strip()
    if not home or not away:
        return jsonify({"error": "Paramètres 'home' et 'away' requis"}), 400

    from sources.football_data import search_team, get_team_matches

    try:
        t1 = search_team(home)
        t2 = search_team(away)
        if not t1 or not t2:
            return jsonify({"error": "Équipe(s) introuvable(s)"}), 404
        t1 = t1[0]
        t2 = t2[0]
        data = get_team_matches(t1["id"], limit=100)

        h2h = []
        for m in data.get("matches", []):
            h_id = m["homeTeam"]["id"]
            a_id = m["awayTeam"]["id"]
            if ((h_id == t1["id"] and a_id == t2["id"]) or
                    (h_id == t2["id"] and a_id == t1["id"])):
                ft = m.get("score", {}).get("fullTime", {})
                h2h.append({
                    "date": m["utcDate"][:10],
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "score": f"{ft.get('home')}-{ft.get('away')}",
                })
        return jsonify({
            "team1": t1["name"],
            "team2": t2["name"],
            "matches": h2h[:10],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Doc API ----------

@app.route("/api")
@app.route("/docs")
def api_docs():
    """Documentation de l'API."""
    return render_template("docs.html")


# ---------- Démarrage ----------

def run():
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    run()
