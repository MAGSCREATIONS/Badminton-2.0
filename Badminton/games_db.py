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
            CREATE TABLE IF NOT EXISTS games (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                date     TEXT    NOT NULL,
                court    INTEGER NOT NULL,
                team1_p1 TEXT   NOT NULL,
                team1_p2 TEXT   NOT NULL,
                team2_p1 TEXT   NOT NULL,
                team2_p2 TEXT   NOT NULL,
                winner   INTEGER NOT NULL CHECK (winner IN (1, 2))
            )
            """
        )


def _to_date_str(date) -> str:
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    return str(date).strip()


def record_game(date, court: int, team1: list[str], team2: list[str], winner: int) -> dict:
    """
    Saves one doubles result. team1/team2 each hold exactly two player names,
    winner is 1 (team1 won) or 2 (team2 won).
    """
    _init_db()
    date_str = _to_date_str(date)
    team1 = [n.strip() for n in team1]
    team2 = [n.strip() for n in team2]

    if len(team1) != 2 or len(team2) != 2:
        raise ValueError("Each team must have exactly 2 players.")
    if any(not n for n in team1 + team2):
        raise ValueError("Player names cannot be empty.")
    if len(set(team1 + team2)) != 4:
        raise ValueError("The same player cannot appear twice in one game.")
    if winner not in (1, 2):
        raise ValueError("Winner must be 1 (Team A) or 2 (Team B).")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (date, court, team1_p1, team1_p2, team2_p1, team2_p2, winner)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date_str, int(court), team1[0], team1[1], team2[0], team2[1], int(winner)),
        )
        game_id = cursor.lastrowid

    return {
        "id": game_id,
        "date": date_str,
        "court": int(court),
        "team1": team1,
        "team2": team2,
        "winner": int(winner),
    }


def get_all_games() -> list[dict]:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, date, court, team1_p1, team1_p2, team2_p1, team2_p2, winner
            FROM games
            ORDER BY date DESC, id DESC
            """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "court": row["court"],
            "team1": [row["team1_p1"], row["team1_p2"]],
            "team2": [row["team2_p1"], row["team2_p2"]],
            "winner": row["winner"],
        }
        for row in rows
    ]


def delete_game(game_id: int) -> dict:
    _init_db()
    with _connect() as conn:
        deleted = conn.execute("DELETE FROM games WHERE id = ?", (int(game_id),)).rowcount
    if not deleted:
        raise ValueError(f"No game found with id {game_id}")
    return {"success": True, "id": int(game_id)}


def _tally(stats: dict, name: str, won: bool) -> None:
    entry = stats.setdefault(name, {"wins": 0, "losses": 0})
    entry["wins" if won else "losses"] += 1


def _with_pct(wins: int, losses: int) -> dict:
    played = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "played": played,
        "win_pct": round(wins / played * 100, 1) if played else 0.0,
    }


def get_rankings() -> list[dict]:
    """
    Ranks every player who has played by total wins (then win %, then name).
    Each player also gets a 'partners' list with wins/losses for every
    teammate they have played alongside, so the pairing history can be
    analysed directly.
    """
    games = get_all_games()
    totals: dict[str, dict] = {}
    partners: dict[str, dict[str, dict]] = {}

    for game in games:
        for team, won in ((game["team1"], game["winner"] == 1), (game["team2"], game["winner"] == 2)):
            for name in team:
                _tally(totals, name, won)
                teammate = team[1] if name == team[0] else team[0]
                _tally(partners.setdefault(name, {}), teammate, won)

    ranking = []
    for name, record in totals.items():
        partner_rows = [
            {"name": mate, **_with_pct(p["wins"], p["losses"])}
            for mate, p in partners.get(name, {}).items()
        ]
        partner_rows.sort(key=lambda r: (-r["wins"], -r["win_pct"], r["name"]))
        ranking.append({
            "name": name,
            **_with_pct(record["wins"], record["losses"]),
            "partners": partner_rows,
        })

    ranking.sort(key=lambda r: (-r["wins"], -r["win_pct"], r["name"]))
    return ranking
