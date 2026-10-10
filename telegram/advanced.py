"""Commandes avancées : /h2h, /subscribe, notifications auto."""
import os
import time
import threading
from datetime import date as _date, datetime, timedelta
from dotenv import load_dotenv

from analysis.analyzer import analyse
from reports.formatter import format_match
from telegram.nlp import parse_match_query

load_dotenv()

NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "8"))


def register(bot):
    """Enregistre les commandes avancées sur le bot."""

    @bot.message_handler(commands=["h2h"])
    def cmd_h2h(message):
        from sources.football_data import search_team, get_team_matches
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Usage : /h2h Arsenal vs Chelsea")
            return
        query = parse_match_query(parts[1])
        if not query:
            bot.reply_to(message, "Format : /h2h Équipe1 vs Équipe2")
            return
        try:
            t1_list = search_team(query["home"])
            t2_list = search_team(query["away"])
            if not t1_list or not t2_list:
                bot.send_message(message.chat.id, "Équipe(s) introuvable(s).")
                return
            t1 = t1_list[0]
            t2 = t2_list[0]
            bot.send_message(
                message.chat.id,
                f"🔎 Recherche {t1['name']} vs {t2['name']}…"
            )
            data = get_team_matches(t1["id"], limit=100)
            h2h = []
            for m in data.get("matches", []):
                h_id = m["homeTeam"]["id"]
                a_id = m["awayTeam"]["id"]
                if ((h_id == t1["id"] and a_id == t2["id"]) or
                        (h_id == t2["id"] and a_id == t1["id"])):
                    h2h.append(m)
            if not h2h:
                bot.send_message(
                    message.chat.id,
                    "Aucune confrontation trouvée dans l'historique récent."
                )
                return
            h2h = h2h[:5]
            lines = [
                f"⚔️ H2H : {t1['name']} vs {t2['name']}",
                f"({len(h2h)} dernières confrontations)", ""
            ]
            v1 = v2 = n = 0
            for m in h2h:
                ft = m.get("score", {}).get("fullTime", {})
                gh, ga = ft.get("home"), ft.get("away")
                if gh is None:
                    continue
                home_name = m["homeTeam"]["name"]
                away_name = m["awayTeam"]["name"]
                if m["homeTeam"]["id"] == t1["id"]:
                    if gh > ga:
                        v1 += 1
                    elif gh < ga:
                        v2 += 1
                    else:
                        n += 1
                else:
                    if ga > gh:
                        v1 += 1
                    elif ga < gh:
                        v2 += 1
                    else:
                        n += 1
                lines.append(
                    f"  {m['utcDate'][:10]} | {home_name} {gh}-{ga} {away_name}"
                )
            lines.append("")
            lines.append(f"📊 Bilan : {v1}V {n}N {v2}D (pour {t1['name']})")
            bot.send_message(message.chat.id, "\n".join(lines))
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Erreur : {e}")

    @bot.message_handler(commands=["subscribe"])
    def cmd_subscribe(message):
        from data.history import subscribe, is_subscribed
        if is_subscribed(message.chat.id):
            bot.send_message(message.chat.id, "ℹ️ Vous êtes déjà abonné.")
            return
        ok = subscribe(message.chat.id)
        if ok:
            bot.send_message(
                message.chat.id,
                f"🔔 Abonné ! Vous recevrez les analyses du jour "
                f"chaque matin à {NOTIFY_HOUR}h (heure serveur)."
            )
        else:
            bot.send_message(message.chat.id, "❌ Erreur lors de l'abonnement.")

    @bot.message_handler(commands=["unsubscribe"])
    def cmd_unsubscribe(message):
        from data.history import unsubscribe
        ok = unsubscribe(message.chat.id)
        bot.send_message(
            message.chat.id,
            "🔕 Désabonné." if ok else "Vous n'étiez pas abonné."
        )


def start_notifier(bot):
    """Lance le thread qui envoie les analyses chaque jour à NOTIFY_HOUR."""
    from data.history import subscribers_list
    from sources.football_data import real_matches

    def _loop():
        while True:
            now = datetime.now()
            target = now.replace(hour=NOTIFY_HOUR, minute=0,
                                 second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            wait = (target - now).total_seconds()
            time.sleep(wait)

            try:
                subs = subscribers_list()
                if not subs:
                    continue
                today = _date.today().isoformat()
                matches = real_matches(today, limit=5)
                if not matches:
                    continue
                for chat_id in subs:
                    try:
                        bot.send_message(
                            chat_id,
                            f"🌅 Bonjour ! Analyses du {today} :"
                        )
                        for m in matches[:3]:
                            a = analyse(
                                m["home"], m["away"],
                                m["home_scored"], m["home_conceded"],
                                m["away_scored"], m["away_conceded"],
                                home_games=m.get("home_games_used", 0),
                                away_games=m.get("away_games_used", 0)
                            )
                            bot.send_message(chat_id, format_match(m, a))
                    except Exception as e:
                        print(f"Notif échouée pour {chat_id}: {e}")
            except Exception as e:
                print(f"Erreur daily notifier : {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print(f"🔔 Notificateur démarré (notifs à {NOTIFY_HOUR}h).")
