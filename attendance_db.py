import sqlite3
import os
from datetime import date as _date_type


BASE_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(BASE_DIR, "badminton.db")


def _connect():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                player_name TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (player_name, date)
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(attendance)").fetchall()
        }
        if "amount" not in columns:
            conn.execute(
                "ALTER TABLE attendance ADD COLUMN amount REAL NOT NULL DEFAULT 0"
            )


def _to_date_str(date) -> str:
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    date = str(date).strip()
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise ValueError(f"Invalid date format '{date}'. Use YYYY-MM-DD.")
    return date


def mark_present(player_name: str, date=None, amount=0.0) -> None:
    _mark(player_name, date, "present", amount)


def mark_absent(player_name: str, date=None) -> None:
    _mark(player_name, date, "absent", 0.0)


def _mark(player_name: str, date, status: str, amount=0.0) -> None:
    _init_db()
    date_str = _to_date_str(date)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO attendance (player_name, date, status, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_name, date)
            DO UPDATE SET
                status = excluded.status,
                amount = excluded.amount
            """,
            (player_name.strip(), date_str, status, float(amount)),
        )


def get_attendance_by_date(date=None) -> list[dict]:
    _init_db()
    date_str = _to_date_str(date)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT player_name, date, status, amount
            FROM attendance
            WHERE date = ?
            ORDER BY player_name ASC
            """,
            (date_str,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_attendance() -> list[dict]:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT player_name, date, status, amount
            FROM attendance
            ORDER BY date DESC, player_name ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_attendance_by_player(player_name: str) -> list[dict]:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT player_name, date, status, amount
            FROM attendance
            WHERE player_name = ?
            ORDER BY date DESC
            """,
            (player_name.strip(),),
        ).fetchall()
    return [dict(row) for row in rows]
