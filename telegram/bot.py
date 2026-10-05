"""Bot Telegram SportAnalytics : analyses à la demande."""
import os
import time
import telebot
from datetime import date as _date
from dotenv import load_dotenv

from analysis.analyzer import analyse
from reports.formatter import format_match

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans .env")

bot = telebot.TeleBot(TOKEN)


# ---------- Aide ----------

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    bot.reply_to(
        message,
        "⚽ SportAnalytics Pro\n\n"
        "Commandes :\n"
        "/today — matchs du jour\n"
        "/date 2026-10-10 — matchs d'une date\n"
        "/demo — test avec données locales\n"
        "/stats — performance du modèle\n"
        "/update — récupérer les résultats réels\n"
        "/export — générer un CSV\n"
        "/value 1.80 3.50 4.20 — analyse value betting"
    )


# ---------- Analyses ----------

@bot.message_handler(commands=["demo"])
def cmd_demo(message):
    from sources.demo import demo_matches
    try:
        m = demo_matches()[0]
        a = analyse(m["home"], m["away"],
                    m["home_scored"], m["home_conceded"],
                    m["away_scored"], m["away_conceded"])
        bot.send_message(message.chat.id, format_match(m, a))
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


def _send_matches(chat_id, date_str, limit=3):
    from sources.football_data import real_matches
    try:
        bot.send_message(chat_id, f"🔎 Analyse du {date_str}…")
        matches = real_matches(date_str, limit=limit)
        if not matches:
            bot.send_message(chat_id, "Aucun match exploitable pour cette date.")
            return
        for m in matches:
            a = analyse(m["home"], m["away"],
                        m["home_scored"], m["home_conceded"],
                        m["away_scored"], m["away_conceded"],
                        home_games=m.get("home_games_used", 0),
                        away_games=m.get("away_games_used", 0))
            bot.send_message(chat_id, format_match(m, a))
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["today"])
def cmd_today(message):
    _send_matches(message.chat.id, _date.today().isoformat())


@bot.message_handler(commands=["date"])
def cmd_date(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage : /date 2026-10-10")
        return
    _send_matches(message.chat.id, parts[1].strip())


# ---------- Statistiques ----------

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    from data.history import stats, pending_count
    try:
        s = stats()
        txt = (
            "📊 STATS DU MODÈLE\n\n"
            f"Total prédictions : {s['total']}\n"
            f"Avec résultat     : {s['with_result']}\n"
            f"En attente        : {pending_count()}\n"
        )
        if s["with_result"]:
            txt += (
                f"\nPrécision 1X2  : {s['accuracy']} %\n"
                f"Précision O2.5 : {s['over_accuracy']} %\n"
                f"Précision BTTS : {s['btts_accuracy']} %"
            )
        else:
            txt += "\nPas encore assez de résultats."
        bot.send_message(message.chat.id, txt)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


# ---------- Mise à jour des résultats ----------

@bot.message_handler(commands=["update"])
def cmd_update(message):
    from sources.results_updater import update_all
    bot.send_message(message.chat.id, "🔄 Mise à jour des résultats en cours…")
    try:
        updated, failed = update_all()
        bot.send_message(
            message.chat.id,
            f"✅ {updated} résultat(s) mis à jour · {failed} en attente"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


# ---------- Export ----------

@bot.message_handler(commands=["export"])
def cmd_export(message):
    from reports.exporter import export_csv
    try:
        export_csv()
        bot.send_message(
            message.chat.id,
            "✅ Export généré : SportAnalytics/predictions_export.csv"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


# ---------- Value betting ----------

@bot.message_handler(commands=["value"])
def cmd_value(message):
    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(
            message,
            "Usage : /value <cote_dom> <cote_nul> <cote_ext>\n"
            "Exemple : /value 1.80 3.50 4.20"
        )
        return
    try:
        odds = [float(x) for x in parts[1:]]
    except ValueError:
        bot.reply_to(message, "Les cotes doivent être des nombres.")
        return

    try:
        from sources.football_data import real_matches
        from reports.value import evaluate_bet

        matches = real_matches(_date.today().isoformat(), limit=1)
        if not matches:
            bot.send_message(message.chat.id, "Aucun match aujourd'hui.")
            return

        m = matches[0]
        a = analyse(m["home"], m["away"],
                    m["home_scored"], m["home_conceded"],
                    m["away_scored"], m["away_conceded"],
                    home_games=m.get("home_games_used", 0),
                    away_games=m.get("away_games_used", 0))

        probs = a.get("probabilities", {})
        txt = f"💰 VALUE : {m['home']} vs {m['away']}\n\n"
        for label, key, odd in [("Dom", "home_win", odds[0]),
                                 ("Nul", "draw", odds[1]),
                                 ("Ext", "away_win", odds[2])]:
            prob = probs.get(key, 0)
            edge, ev, verdict = evaluate_bet(prob, odd, stake=10)
            txt += f"{label} : modèle {prob:.1f}% | cote {odd:.2f}\n"
            txt += f"     edge {edge:+.2f}%  EV {ev:+.2f}€  {verdict}\n\n"
        bot.send_message(message.chat.id, txt)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


# ---------- Fallback ----------

@bot.message_handler(func=lambda msg: True, content_types=["text"])
def fallback(message):
    bot.reply_to(message, "Tape /help pour voir les commandes.")


# ---------- Démarrage avec reconnexion automatique ----------

def run():
    print("🤖 Bot Telegram démarré. Ctrl+C pour arrêter.")
    while True:
        try:
            bot.polling(non_stop=True, interval=1, timeout=30,
                        long_polling_timeout=20)
        except KeyboardInterrupt:
            print("\n👋 Bot arrêté.")
            break
        except Exception as e:
            print(f"⚠️  Connexion perdue ({e}). Reconnexion dans 5 s…")
            time.sleep(5)
