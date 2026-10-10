"""Parsing en langage naturel : « Arsenal vs Leeds demain »."""
import re
from datetime import date as _date, timedelta


def _norm(s):
    s = s.lower().strip()
    s = re.sub(r"\b(fc|afc|cf|sc|ac|club|de|the)\b", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.strip()


WEEKDAYS = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
}

MOIS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}


def parse_date(text):
    t = text.lower()
    t_norm = t.replace("é", "e").replace("è", "e").replace("à", "a")
    today = _date.today()

    if "apres-demain" in t_norm or "apres demain" in t_norm:
        return today + timedelta(days=2)
    if "demain" in t_norm:
        return today + timedelta(days=1)
    if "aujourd'hui" in t_norm or "aujourdhui" in t_norm or "ce soir" in t_norm:
        return today

    for jour, num in WEEKDAYS.items():
        if re.search(r"\b" + jour + r"\b", t_norm):
            delta = (num - today.weekday()) % 7
            if delta == 0:
                delta = 7
            return today + timedelta(days=delta)

    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return _date(year, month, day)
        except ValueError:
            pass

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            return _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    m = re.search(r"\b(\d{1,2})\s+([a-zéû]+)", t_norm)
    if m:
        day = int(m.group(1))
        for mois_nom, num in MOIS.items():
            if m.group(2).startswith(mois_nom[:3]):
                try:
                    return _date(today.year, num, day)
                except ValueError:
                    pass

    return None


SEPARATORS = [
    r"\s+vs\.?\s+",
    r"\s+versus\s+",
    r"\s+contre\s+",
    r"\s+-\s+",
    r"\s+–\s+",
    r"\s+/\s+",
]


def _clean_team(s):
    s = s.lower()
    for mot in ["apres-demain", "apres demain", "demain", "aujourd'hui",
                "aujourdhui", "ce soir", "lundi", "mardi", "mercredi",
                "jeudi", "vendredi", "samedi", "dimanche",
                "le", "du", "de", "à", "a", "ce", "cette"]:
        s = re.sub(r"\b" + re.escape(mot) + r"\b", "", s)
    s = re.sub(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?", "", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}", "", s)
    s = re.sub(r"\d{1,2}\s+[a-zéû]+", "", s)
    s = re.sub(r"[^\w\s\-']", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_match_query(text):
    original = text.strip()
    if not original:
        return None

    sep_pattern = None
    for pat in SEPARATORS:
        if re.search(pat, original, re.IGNORECASE):
            sep_pattern = pat
            break

    if not sep_pattern:
        return None

    parts = re.split(sep_pattern, original, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None

    home_raw = parts[0].strip()
    away_raw = parts[1].strip()

    target_date = parse_date(away_raw) or parse_date(home_raw) or _date.today()

    home = _clean_team(home_raw)
    away = _clean_team(away_raw)

    if not home or not away or len(home) < 3 or len(away) < 3:
        return None

    return {
        "home": home,
        "away": away,
        "date": target_date,
        "raw": original,
    }


def match_team(query, target):
    q = _norm(query)
    t = _norm(target)
    if not q or not t:
        return False
    if q == t:
        return True
    if q in t or t in q:
        return True
    q_words = [w for w in q.split() if len(w) > 2]
    t_words = [w for w in t.split() if len(w) > 2]
    return any(qw in t_words for qw in q_words)
