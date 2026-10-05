"""Sauvegarde des prédictions et suivi de performance (SQLite)."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "history.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_created TEXT NOT NULL,
                kickoff TEXT,
                competition TEXT,
                home TEXT NOT NULL,
                away TEXT NOT NULL,
                p_home REAL,
                p_draw REAL,
                p_away REAL,
                over_25 REAL,
                btts REAL,
                xg_home REAL,
                xg_away REAL,
                confidence INTEGER,
                actual_home INTEGER,
                actual_away INTEGER,
                outcome_hit INTEGER,
                over_hit INTEGER,
                btts_hit INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_kickoff ON predictions(kickoff)")
        c.commit()


def save_prediction(match, analysis):
    probs = analysis.get("probabilities", {})
    xgs = analysis.get("expected_goals", {})
    kickoff = match.get("kickoff", "") or ""
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM predictions WHERE home=? AND away=? AND kickoff=?",
            (match["home"], match["away"], kickoff)
        ).fetchone()
        if existing:
            return existing["id"]

        cur = c.execute("""
            INSERT INTO predictions
            (date_created, kickoff, competition, home, away,
             p_home, p_draw, p_away, over_25, btts,
             xg_home, xg_away, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            kickoff,
            match.get("competition") or match.get("league", ""),
            match["home"],
            match["away"],
            probs.get("home_win"),
            probs.get("draw"),
            probs.get("away_win"),
            probs.get("over_2_5"),
            probs.get("btts_yes"),
            xgs.get("home"),
            xgs.get("away"),
            analysis.get("confidence"),
            datetime.now().isoformat(timespec="seconds"),
        ))
        c.commit()
        return cur.lastrowid


def pending_results():
    """Prédictions dont le coup d'envoi est passé mais sans résultat."""
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        rows = c.execute("""
            SELECT * FROM predictions
            WHERE actual_home IS NULL AND kickoff != '' AND kickoff < ?
            ORDER BY kickoff ASC
        """, (now,)).fetchall()
        return [dict(r) for r in rows]


def update_result(pred_id, actual_home, actual_away):
    """Remplit le résultat d'une prédiction et calcule les hits."""
    with _conn() as c:
        r = c.execute("SELECT * FROM predictions WHERE id=?", (pred_id,)).fetchone()
        if not r:
            return
        r = dict(r)

        # issue prédite (la plus probable)
        probs = {"home": r["p_home"] or 0, "draw": r["p_draw"] or 0, "away": r["p_away"] or 0}
        predicted = max(probs, key=probs.get)

        # issue réelle
        if actual_home > actual_away:
            real = "home"
        elif actual_home < actual_away:
            real = "away"
        else:
            real = "draw"

        outcome_hit = 1 if predicted == real else 0
        total_goals = actual_home + actual_away
        over_hit = 1 if (total_goals >= 3) == ((r["over_25"] or 0) > 50) else 0
        btts_hit = 1 if (actual_home >= 1 and actual_away >= 1) == ((r["btts"] or 0) > 50) else 0

        c.execute("""
            UPDATE predictions
            SET actual_home=?, actual_away=?, outcome_hit=?, over_hit=?, btts_hit=?
            WHERE id=?
        """, (actual_home, actual_away, outcome_hit, over_hit, btts_hit, pred_id))
        c.commit()


def stats():
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        with_result = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE actual_home IS NOT NULL"
        ).fetchone()[0]
        hits = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE outcome_hit=1"
        ).fetchone()[0]
        over_hits = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE over_hit=1"
        ).fetchone()[0]
        btts_hits = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE btts_hit=1"
        ).fetchone()[0]
        return {
            "total": total,
            "with_result": with_result,
            "hits": hits,
            "over_hits": over_hits,
            "btts_hits": btts_hits,
            "accuracy": round(hits / with_result * 100, 1) if with_result else 0.0,
            "over_accuracy": round(over_hits / with_result * 100, 1) if with_result else 0.0,
            "btts_accuracy": round(btts_hits / with_result * 100, 1) if with_result else 0.0,
        }


def recent(n=10):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]


def pending_count():
    with _conn() as c:
        return c.execute("""
            SELECT COUNT(*) FROM predictions
            WHERE actual_home IS NULL AND kickoff != ''
              AND kickoff < datetime('now')
        """).fetchone()[0]
