"""Persistencia del MVP con SQLite (estándar de Python).

En producción se puede migrar a PostgreSQL manteniendo estas mismas
funciones como contrato; el MVP no finge tener Postgres.
Las fotos NO se guardan como blobs: solo el file_id de Telegram.
"""
import sqlite3
from datetime import date

from .matching import mutually_compatible

PROFILE_FIELDS = {
    "language", "platform_username", "display_name", "age", "gender",
    "seeking", "relationship", "country", "city", "languages",
    "interests", "bio", "age_min", "age_max", "status",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    language TEXT,
    platform_username TEXT UNIQUE,
    display_name TEXT,
    age INTEGER,
    gender TEXT,
    seeking TEXT,
    relationship TEXT,
    country TEXT,
    city TEXT,
    languages TEXT,
    interests TEXT,
    bio TEXT,
    age_min INTEGER,
    age_max INTEGER,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS actions (
    liker_id INTEGER NOT NULL,
    liked_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    day TEXT NOT NULL,
    PRIMARY KEY (liker_id, liked_id)
);
CREATE TABLE IF NOT EXISTS matches (
    user_a INTEGER NOT NULL,
    user_b INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_a, user_b)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS blocks (
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    PRIMARY KEY (blocker_id, blocked_id)
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    reported_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_user(conn, telegram_id):
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
    ).fetchone()
    return dict(row) if row else None


def create_or_get_user(conn, telegram_id):
    user = get_user(conn, telegram_id)
    if user:
        return user
    conn.execute(
        "INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
    conn.commit()
    return get_user(conn, telegram_id)


def set_language(conn, telegram_id, lang):
    conn.execute("UPDATE users SET language=? WHERE telegram_id=?",
                 (lang, telegram_id))
    conn.commit()


def update_profile(conn, telegram_id, **fields):
    safe = {k: v for k, v in fields.items() if k in PROFILE_FIELDS}
    if not safe:
        return
    assignments = ", ".join(f"{k}=?" for k in safe)
    conn.execute(f"UPDATE users SET {assignments} WHERE telegram_id=?",
                 (*safe.values(), telegram_id))
    conn.commit()


def add_photo(conn, telegram_id, file_id, is_main=False):
    if is_main:
        conn.execute("UPDATE photos SET is_main=0 WHERE telegram_id=?",
                     (telegram_id,))
    conn.execute(
        "INSERT INTO photos (telegram_id, file_id, is_main) VALUES (?,?,?)",
        (telegram_id, file_id, 1 if is_main else 0))
    conn.commit()


def get_main_photo(conn, telegram_id):
    row = conn.execute(
        "SELECT file_id FROM photos WHERE telegram_id=? ORDER BY is_main DESC, id LIMIT 1",
        (telegram_id,)).fetchone()
    return row["file_id"] if row else None


def is_blocked(conn, a, b):
    row = conn.execute(
        "SELECT 1 FROM blocks WHERE (blocker_id=? AND blocked_id=?)"
        " OR (blocker_id=? AND blocked_id=?)",
        (a, b, b, a)).fetchone()
    return row is not None


def block_user(conn, blocker_id, blocked_id):
    conn.execute("INSERT OR IGNORE INTO blocks VALUES (?,?)",
                 (blocker_id, blocked_id))
    conn.commit()


def report_user(conn, reporter_id, reported_id, reason="report_from_card"):
    conn.execute(
        "INSERT INTO reports (reporter_id, reported_id, reason) VALUES (?,?,?)",
        (reporter_id, reported_id, reason))
    conn.commit()


def daily_likes(conn, telegram_id):
    row = conn.execute(
        "SELECT COUNT(*) c FROM actions WHERE liker_id=? AND action='like' AND day=?",
        (telegram_id, date.today().isoformat())).fetchone()
    return row["c"]


def discover(conn, telegram_id, limit=1):
    """Candidatos activos, compatibles en ambos sentidos, sin repetir
    acciones previas, sin bloqueos y sin matches ya existentes."""
    me = get_user(conn, telegram_id)
    if not me or me["status"] != "active":
        return []
    rows = conn.execute(
        "SELECT * FROM users WHERE status='active' AND telegram_id != ?",
        (telegram_id,)).fetchall()
    out = []
    for row in rows:
        cand = dict(row)
        if is_blocked(conn, telegram_id, cand["telegram_id"]):
            continue
        acted = conn.execute(
            "SELECT 1 FROM actions WHERE liker_id=? AND liked_id=?",
            (telegram_id, cand["telegram_id"])).fetchone()
        if acted:
            continue
        matched = conn.execute(
            "SELECT 1 FROM matches WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)",
            (telegram_id, cand["telegram_id"], cand["telegram_id"], telegram_id)).fetchone()
        if matched:
            continue
        if cand.get("age") is None or me.get("age") is None:
            continue
        if not mutually_compatible(me, cand):
            continue
        out.append(cand)
        if len(out) >= limit:
            break
    return out


def record_action(conn, liker_id, liked_id, action):
    """Devuelve True solo si un 'like' crea un match mutuo nuevo."""
    conn.execute(
        "INSERT OR REPLACE INTO actions VALUES (?,?,?,?)",
        (liker_id, liked_id, action, date.today().isoformat()))
    is_match = False
    if action == "like":
        reciprocal = conn.execute(
            "SELECT 1 FROM actions WHERE liker_id=? AND liked_id=? AND action='like'",
            (liked_id, liker_id)).fetchone()
        if reciprocal:
            a, b = sorted((liker_id, liked_id))
            conn.execute("INSERT OR IGNORE INTO matches VALUES (?,?,CURRENT_TIMESTAMP)", (a, b))
            is_match = True
    conn.commit()
    return is_match


def list_matches(conn, telegram_id):
    rows = conn.execute(
        "SELECT * FROM matches WHERE user_a=? OR user_b=? ORDER BY created_at DESC",
        (telegram_id, telegram_id)).fetchall()
    out = []
    for row in rows:
        peer = row["user_b"] if row["user_a"] == telegram_id else row["user_a"]
        out.append(get_user(conn, peer))
    return [u for u in out if u]


def can_message(conn, sender_id, receiver_id):
    matched = conn.execute(
        "SELECT 1 FROM matches WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)",
        (sender_id, receiver_id, receiver_id, sender_id)).fetchone()
    return bool(matched) and not is_blocked(conn, sender_id, receiver_id)


def send_message(conn, sender_id, receiver_id, text):
    if not can_message(conn, sender_id, receiver_id):
        raise ValueError("no_match_or_blocked")
    conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, text) VALUES (?,?,?)",
        (sender_id, receiver_id, text))
    conn.commit()


def delete_account(conn, telegram_id):
    conn.execute(
        "UPDATE users SET status='deleted', display_name=NULL, bio=NULL,"
        " interests=NULL, platform_username=NULL WHERE telegram_id=?",
        (telegram_id,))
    conn.execute("DELETE FROM photos WHERE telegram_id=?", (telegram_id,))
    conn.commit()


def admin_stats(conn):
    def count(sql, args=()):
        return conn.execute(sql, args).fetchone()[0]
    return {
        "users": count("SELECT COUNT(*) FROM users"),
        "active": count("SELECT COUNT(*) FROM users WHERE status='active'"),
        "matches": count("SELECT COUNT(*) FROM matches"),
        "reports": count("SELECT COUNT(*) FROM reports"),
        "messages": count("SELECT COUNT(*) FROM messages"),
    }
