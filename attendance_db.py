"""
attendance_db.py
----------------
SQLite-backed attendance tracking for the Badminton Player Management System.

Responsibilities:
  - Initialize the 'attendance' table (auto-called on import)
  - Mark a player present or absent for a given date
  - Upsert on conflict: no duplicate (player_name, date) rows
  - Query attendance by date or fetch the full history

Usage:
  from attendance_db import (
      mark_present, mark_absent,
      get_attendance_by_date, get_all_attendance
  )
"""

import sqlite3
import os
from datetime import date as _date_type

# ── Configuration ────────────────────────────────────────────────────────────

DB_FILE = os.path.join(os.path.dirname(__file__), "badminton.db")

# ── Internal helpers ─────────────────────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    """Opens (or creates) the SQLite database and returns a connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row        # lets us access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    return conn


def _init_db() -> None:
    """Creates the attendance table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT    NOT NULL,
                date        TEXT    NOT NULL,          -- stored as YYYY-MM-DD
                status      TEXT    NOT NULL            -- 'present' | 'absent'
                    CHECK (status IN ('present', 'absent')),
                UNIQUE (player_name, date)              -- prevents duplicates
            )
        """)


# ── Public API ───────────────────────────────────────────────────────────────

def mark_present(player_name: str, date: str | _date_type | None = None) -> None:
    """
    Records 'present' for *player_name* on *date* (default: today).

    If a record already exists for that (player, date) pair it is updated
    in-place rather than duplicated.

    Args:
        player_name: Exact name as stored in players_data.json.
        date:        ISO-format string 'YYYY-MM-DD', a datetime.date object,
                     or None to use today's date.
    """
    _mark(player_name, date, "present")


def mark_absent(player_name: str, date: str | _date_type | None = None) -> None:
    """
    Records 'absent' for *player_name* on *date* (default: today).

    Same upsert semantics as mark_present.
    """
    _mark(player_name, date, "absent")


def _mark(player_name: str, date, status: str) -> None:
    """Internal upsert helper shared by mark_present / mark_absent."""
    date_str = _to_date_str(date)
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO attendance (player_name, date, status)
            VALUES (?, ?, ?)
            ON CONFLICT (player_name, date)
                DO UPDATE SET status = excluded.status
        """, (player_name.strip(), date_str, status))


def get_attendance_by_date(date: str | _date_type | None = None) -> list[dict]:
    """
    Returns all attendance records for a specific date.

    Args:
        date: ISO string, datetime.date, or None for today.

    Returns:
        List of dicts with keys: id, player_name, date, status.
        Sorted alphabetically by player_name.
    """
    date_str = _to_date_str(date)
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT id, player_name, date, status
            FROM   attendance
            WHERE  date = ?
            ORDER  BY player_name ASC
        """, (date_str,)).fetchall()
    return [dict(row) for row in rows]


def get_all_attendance() -> list[dict]:
    """
    Returns every attendance record in the database.

    Returns:
        List of dicts with keys: id, player_name, date, status.
        Sorted by date (newest first), then player_name.
    """
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT id, player_name, date, status
            FROM   attendance
            ORDER  BY date DESC, player_name ASC
        """).fetchall()
    return [dict(row) for row in rows]


def get_attendance_by_player(player_name: str) -> list[dict]:
    """
    Returns the full attendance history for a single player.

    Args:
        player_name: Exact name string.

    Returns:
        List of dicts sorted by date (newest first).
    """
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT id, player_name, date, status
            FROM   attendance
            WHERE  player_name = ?
            ORDER  BY date DESC
        """, (player_name.strip(),)).fetchall()
    return [dict(row) for row in rows]


# ── Utility ──────────────────────────────────────────────────────────────────

def _to_date_str(date) -> str:
    """Normalises a date argument to a 'YYYY-MM-DD' string."""
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    # Assume it is already a string; validate format loosely
    date = str(date).strip()
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise ValueError(f"Invalid date format '{date}'. Use YYYY-MM-DD.")
    return date


# ── Auto-initialise on import ────────────────────────────────────────────────
_init_db()