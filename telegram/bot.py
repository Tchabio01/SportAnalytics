"""Bot Telegram SportAnalytics : moteur d'analyse statistique neutre."""
import os
import time
import telebot
from datetime import date as _date, timedelta
from dotenv import load_dotenv

from analysis.analyzer import analyse
from reports.formatter import format_match

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans .env")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    bot.reply_to(
        message,
        "⚽ SportAnalytics — Moteur d'analyse statistique\n\n"
        "💬 Écrivez simplement :\n"
        "« Arsenal vs Leeds demain »\n"
        "« PSG - Marseille »\n\n"
        "📊 /today · /date · /top · /team\n"
        "⭐ /watch · /unwatch · /watchlist\n"
        "📈 /stats · /update · /export"
    )


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
            bot.send_message(chat_id, "Aucun match avec données suffisantes.")
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


@bot.message_handler(commands=["top"])
def cmd_top(message):
    from sources.football_data import real_matches
    try:
        matches = real_matches(_date.today().isoformat(), limit=10)
        if not matches:
            bot.send_message(message.chat.id, "Aucun match aujourd'hui.")
            return
        results = []
        for m in matches:
            a = analyse(m["home"], m["away"],
                        m["home_scored"], m["home_conceded"],
                        m["away_scored"], m["away_conceded"],
                        home_games=m.get("home_games_used", 0),
                        away_games=m.get("away_games_used", 0))
            results.append((a.get("confidence") or 0, m, a))
        results.sort(key=lambda x: x[0], reverse=True)
        lines = [f"🏆 TOP 5 ({len(matches)} matchs analysés)", ""]
        for i, (conf, m, a) in enumerate(results[:5], 1):
            p = a.get("probabilities", {})
            lines.append(f"{i}. {m['home']} — {m['away']}")
            lines.append(f"   1X2 : {p.get('home_win',0):.0f}/{p.get('draw',0):.0f}/{p.get('away_win',0):.0f}")
            lines.append(f"   O2.5 : {p.get('over_2_5',0):.0f}%  BTTS : {p.get('btts_yes',0):.0f}%  🧠 {conf}/100")
            lines.append("")
        bot.send_message(message.chat.id, "\n".join(lines))
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["team"])
def cmd_team(message):
    from sources.football_data import search_team, team_form_summary
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage : /team Arsenal")
        return
    try:
        teams = search_team(parts[1].strip())
        if not teams:
            bot.send_message(message.chat.id, "Équipe introuvable.")
            return
        t = teams[0]
        form = team_form_summary(t["id"], 5)
        if not form:
            bot.send_message(message.chat.id, f"Pas de matchs récents pour {t['name']}.")
            return
        wins = sum(1 for f in form if f["result"] == "V")
        draws = sum(1 for f in form if f["result"] == "N")
        losses = sum(1 for f in form if f["result"] == "D")
        gf = sum(f["gf"] for f in form)
        ga = sum(f["ga"] for f in form)
        lines = [f"⭐ {t['name']}", f"Forme : {wins}V {draws}N {losses}D",
                 f"Buts : {gf} marqués / {ga} encaissés", "", "📋 Détail :"]
        for f in form:
            emoji = {"V": "🟢", "N": "🟡", "D": "🔴"}[f["result"]]
            lieu = "🏠" if f["home"] else "✈️"
            lines.append(f"{emoji} {lieu} {f['date']} {f['gf']}-{f['ga']} vs {f['opponent']}")
        bot.send_message(message.chat.id, "\n".join(lines))
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["watch"])
def cmd_watch(message):
    from sources.football_data import search_team
    from data.history import watchlist_add
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage : /watch Arsenal")
        return
    try:
        teams = search_team(parts[1].strip())
        if not teams:
            bot.send_message(message.chat.id, "Équipe introuvable.")
            return
        t = teams[0]
        ok = watchlist_add(t["id"], t["name"])
        bot.send_message(message.chat.id,
                         f"⭐ {t['name']} ajoutée." if ok else "ℹ️ Déjà suivie.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["unwatch"])
def cmd_unwatch(message):
    from data.history import watchlist_remove
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage : /unwatch Arsenal")
        return
    ok = watchlist_remove(parts[1].strip())
    bot.send_message(message.chat.id, "🗑️ Retirée." if ok else "Pas dans la watchlist.")


@bot.message_handler(commands=["watchlist"])
def cmd_watchlist(message):
    from data.history import watchlist_list
    wl = watchlist_list()
    if not wl:
        bot.send_message(message.chat.id, "Watchlist vide. /watch Arsenal pour ajouter.")
        return
    lines = [f"⭐ WATCHLIST ({len(wl)})", ""]
    for w in wl:
        lines.append(f"  • {w['team_name']}")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    from data.history import stats, pending_count
    try:
        s = stats()
        txt = (f"📊 STATISTIQUES\n\n"
               f"Prédictions : {s['total']}\n"
               f"Avec résultat : {s['with_result']}\n"
               f"En attente : {pending_count()}\n")
        if s["with_result"]:
            txt += (f"\nPrécision 1X2 : {s['accuracy']} %\n"
                    f"Précision O2.5 : {s['over_accuracy']} %\n"
                    f"Précision BTTS : {s['btts_accuracy']} %")
        bot.send_message(message.chat.id, txt)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["update"])
def cmd_update(message):
    from sources.results_updater import update_all
    bot.send_message(message.chat.id, "🔄 Mise à jour…")
    try:
        u, f = update_all()
        bot.send_message(message.chat.id, f"✅ {u} mis à jour · {f} en attente")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(commands=["export"])
def cmd_export(message):
    from reports.exporter import export_csv
    try:
        export_csv()
        bot.send_message(message.chat.id, "✅ Export CSV généré.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_free_text(message):
    from telegram.nlp import parse_match_query, match_team
    from sources.football_data import get_matches, _compute_form

    text = message.text.strip()
    if text.startswith("/"):
        bot.reply_to(message, "Tape /help pour les commandes.")
        return

    query = parse_match_query(text)
    if not query:
        bot.reply_to(
            message,
            "💬 Je n'ai pas compris. Essayez :\n"
            "« Arsenal vs Leeds demain »\n"
            "« PSG - Marseille »\n"
            "Ou /help."
        )
        return

    base_date = query["date"]
    bot.send_message(message.chat.id,
                     f"🔎 Recherche : {query['home']} vs {query['away']}")

    try:
        fixture = None
        for delta in [0, 1, -1, 2, -2, 3, 4, 5, 6, 7]:
            d = (base_date + timedelta(days=delta)).isoformat()
            try:
                data = get_matches(d)
            except Exception:
                continue
            for m in data.get("matches", []):
                h, a = m["homeTeam"], m["awayTeam"]
                if match_team(query["home"], h["name"]) and match_team(query["away"], a["name"]):
                    fixture = m
                    break
            if fixture:
                break

        if not fixture:
            bot.send_message(message.chat.id,
                             "❌ Match introuvable dans les 7 jours autour.")
            return

        home = fixture["homeTeam"]
        away = fixture["awayTeam"]
        h_s, h_c, h_n = _compute_form(home["id"], "home")
        a_s, a_c, a_n = _compute_form(away["id"], "away")
        m = {
            "home": home["name"], "away": away["name"],
            "home_scored": h_s, "home_conceded": h_c,
            "away_scored": a_s, "away_conceded": a_c,
            "kickoff": fixture["utcDate"],
            "competition": fixture["competition"]["name"],
            "league": fixture["competition"]["name"],
            "country": (fixture["competition"].get("area") or {}).get("name", ""),
            "home_games_used": h_n, "away_games_used": a_n,
        }
        a = analyse(m["home"], m["away"], h_s, h_c, a_s, a_c,
                    home_games=h_n, away_games=a_n)
        bot.send_message(message.chat.id, format_match(m, a))
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erreur : {e}")


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
