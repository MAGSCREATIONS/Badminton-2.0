import sqlite3
import os
from datetime import date as _date_type


BASE_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(BASE_DIR, "badminton.db")
RATE_PER_COURT_PER_HOUR = 350


def _connect():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                date TEXT PRIMARY KEY,
                courts INTEGER NOT NULL,
                hours REAL NOT NULL,
                total_cost REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_players (
                session_date TEXT NOT NULL,
                name TEXT NOT NULL,
                hours_played REAL NOT NULL DEFAULT 0,
                amount_due REAL NOT NULL DEFAULT 0,
                amount_paid REAL NOT NULL DEFAULT 0,
                balance REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (session_date, name),
                FOREIGN KEY (session_date) REFERENCES sessions(date) ON DELETE CASCADE
            )
            """
        )


def _to_date_str(date) -> str:
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    return str(date).strip()


def _get_session_players(conn, date_str: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT name, hours_played, amount_due, amount_paid, balance
        FROM session_players
        WHERE session_date = ?
        ORDER BY name ASC
        """,
        (date_str,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_session(date, courts: int, session_hours: float, player_hours: dict) -> dict:
    """
    Creates/overwrites a session. Calculates each player's share
    proportionally based on hours played.
    Preserves any existing payments if session already exists.
    """
    _init_db()
    date_str = _to_date_str(date)
    total_cost = courts * session_hours * RATE_PER_COURT_PER_HOUR
    total_hrs = sum(h for h in player_hours.values() if h > 0)

    with _connect() as conn:
        existing_payments = {
            row["name"]: row["amount_paid"]
            for row in conn.execute(
                """
                SELECT name, amount_paid
                FROM session_players
                WHERE session_date = ?
                """,
                (date_str,),
            ).fetchall()
        }

        conn.execute(
            """
            INSERT INTO sessions (date, courts, hours, total_cost)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                courts = excluded.courts,
                hours = excluded.hours,
                total_cost = excluded.total_cost
            """,
            (date_str, courts, float(session_hours), float(total_cost)),
        )

        conn.execute("DELETE FROM session_players WHERE session_date = ?", (date_str,))

        players = []
        for name, hrs in player_hours.items():
            share = round((hrs / total_hrs) * total_cost, 2) if total_hrs > 0 and hrs > 0 else 0
            paid = round(float(existing_payments.get(name, 0)), 2)
            balance = round(paid - share, 2)
            conn.execute(
                """
                INSERT INTO session_players (session_date, name, hours_played, amount_due, amount_paid, balance)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (date_str, name, float(hrs), share, paid, balance),
            )
            players.append({
                "name": name,
                "hours_played": float(hrs),
                "amount_due": share,
                "amount_paid": paid,
                "balance": balance,
            })

    return {
        "date": date_str,
        "courts": courts,
        "hours": float(session_hours),
        "total_cost": float(total_cost),
        "players": players,
    }


def get_session(date=None) -> dict | None:
    _init_db()
    date_str = _to_date_str(date)
    with _connect() as conn:
        session_row = conn.execute(
            """
            SELECT date, courts, hours, total_cost
            FROM sessions
            WHERE date = ?
            """,
            (date_str,),
        ).fetchone()
        if not session_row:
            return None
        players = _get_session_players(conn, date_str)
    return {
        "date": session_row["date"],
        "courts": session_row["courts"],
        "hours": session_row["hours"],
        "total_cost": session_row["total_cost"],
        "players": players,
    }


def get_all_sessions() -> list[dict]:
    _init_db()
    with _connect() as conn:
        session_rows = conn.execute(
            """
            SELECT date, courts, hours, total_cost
            FROM sessions
            ORDER BY date DESC
            """
        ).fetchall()
        result = []
        for row in session_rows:
            result.append({
                "date": row["date"],
                "courts": row["courts"],
                "hours": row["hours"],
                "total_cost": row["total_cost"],
                "players": _get_session_players(conn, row["date"]),
            })
    return result


def record_payment(date, player_name: str, amount: float) -> dict:
    """
    Adds a payment for a player and recomputes their balance.
    Returns the updated player record.
    """
    _init_db()
    date_str = _to_date_str(date)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT name, hours_played, amount_due, amount_paid, balance
            FROM session_players
            WHERE session_date = ? AND name = ?
            """,
            (date_str, player_name),
        ).fetchone()
        if not row:
            session_exists = conn.execute(
                "SELECT 1 FROM sessions WHERE date = ?",
                (date_str,),
            ).fetchone()
            if not session_exists:
                raise ValueError(f"No session found for {date_str}")
            raise ValueError(f"Player {player_name} not found in session")

        new_paid = round(float(row["amount_paid"]) + float(amount), 2)
        new_balance = round(new_paid - float(row["amount_due"]), 2)
        conn.execute(
            """
            UPDATE session_players
            SET amount_paid = ?, balance = ?
            WHERE session_date = ? AND name = ?
            """,
            (new_paid, new_balance, date_str, player_name),
        )
    return {
        "name": row["name"],
        "hours_played": row["hours_played"],
        "amount_due": row["amount_due"],
        "amount_paid": new_paid,
        "balance": new_balance,
    }


def get_player_summary() -> list[dict]:
    """
    Returns accumulated stats per player across ALL sessions.
    Each entry: { name, total_hours, total_due, total_paid, balance }
    """
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                name,
                ROUND(SUM(hours_played), 1) AS total_hours,
                ROUND(SUM(amount_due), 2) AS total_due,
                ROUND(SUM(amount_paid), 2) AS total_paid
            FROM session_players
            WHERE hours_played > 0
            GROUP BY name
            ORDER BY name ASC
            """
        ).fetchall()

    result = []
    for row in rows:
        total_due = float(row["total_due"] or 0)
        total_paid = float(row["total_paid"] or 0)
        result.append({
            "name": row["name"],
            "total_hours": float(row["total_hours"] or 0),
            "total_due": total_due,
            "total_paid": total_paid,
            "balance": round(total_paid - total_due, 2),
        })
    return result


def clear_all_payments() -> dict:
    """
    Resets payment-related session data across all sessions.
    Keeps the session documents, but clears paid amounts, due amounts,
    recorded hours, and balances.
    """
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT session_date, name, amount_paid, amount_due, hours_played, balance
            FROM session_players
            """
        ).fetchall()
        players_reset = sum(
            1
            for row in rows
            if any(float(row[key] or 0) != 0 for key in ("amount_paid", "amount_due", "hours_played", "balance"))
        )
        conn.execute(
            """
            UPDATE session_players
            SET amount_paid = 0,
                amount_due = 0,
                hours_played = 0,
                balance = 0
            """
        )
        sessions_updated = conn.execute(
            """
            UPDATE sessions
            SET total_cost = 0
            """
        ).rowcount

    return {
        "success": True,
        "sessions_updated": sessions_updated,
        "players_reset": players_reset,
    }
