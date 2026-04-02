"""
logic.py  (updated)
--------------------
Core application logic for the Badminton Manager.

Changes vs. original:
  - Added mark_attendance() — marks a list of present player names for a date
    and automatically marks everyone else in the roster as absent.
  - Re-exports attendance query helpers so other modules only need to import
    from logic, not from attendance_db directly.

All attendance persistence is handled by attendance_db; this module stays
focused on business rules (who is in the roster, group generation, etc.).
"""

import json
import os
from player import Player, SkillLevel
from badminton_group_randomizer import BadmintonGroupRandomizer
from attendance_db import (          # ← new import
    mark_present,
    mark_absent,
    get_attendance_by_date,
    get_all_attendance,
    get_attendance_by_player,
)

PLAYER_FILE = "players_data.json"

# ── Roster helpers (unchanged) ────────────────────────────────────────────────

def init_files():
    if not os.path.exists(PLAYER_FILE):
        with open(PLAYER_FILE, "w") as f:
            json.dump([], f, indent=4)


def load_players():
    init_files()
    with open(PLAYER_FILE, "r") as f:
        data = json.load(f)
    return [Player(p["name"], SkillLevel(p["skill"])) for p in data]


def save_players(players):
    data = [{"name": p.get_name(), "skill": p.get_skill_level().value} for p in players]
    with open(PLAYER_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_player(name, skill_str):
    players = load_players()
    skill_map = {
        "beginner":     SkillLevel.BEGINNER,
        "intermediate": SkillLevel.INTERMEDIATE,
        "advanced":     SkillLevel.ADVANCED,
    }
    skill = skill_map.get(skill_str.lower(), SkillLevel.BEGINNER)
    players.append(Player(name, skill))
    save_players(players)


def remove_player(name):
    players = load_players()
    players = [p for p in players if p.get_name().lower() != name.lower()]
    save_players(players)


def generate_balanced_groups(present_names):
    all_players = load_players()
    present_players = [p for p in all_players if p.get_name() in present_names]
    if len(present_players) < 4:
        raise ValueError("Need at least 4 present players.")
    return BadmintonGroupRandomizer.randomize_players(present_players)


# ── Attendance helpers (new) ──────────────────────────────────────────────────

def mark_attendance(present_names: list[str], contributions: dict | None = None, date=None) -> dict:
    """
    Mark today's (or a given date's) attendance for the full roster.

    Players whose names appear in *present_names* are marked 'present';
    everyone else in the roster is marked 'absent'.

    Contributions may be provided as a mapping from player name to amount paid.

    Args:
        present_names: List of player name strings who are present.
        contributions: Mapping of player names to amounts contributed.
        date:          'YYYY-MM-DD' string, datetime.date, or None for today.

    Returns:
        A summary dict with present/absent details and the total pool amount.
    """
    all_players  = load_players()
    present_set  = {n.strip() for n in present_names}
    contributions = contributions or {}

    marked_present = []
    marked_absent  = []
    total_amount   = 0.0

    for player in all_players:
        name = player.get_name()
        if name in present_set:
            amount = float(contributions.get(name, 0) or 0)
            mark_present(name, date, amount)
            marked_present.append(name)
            total_amount += amount
        else:
            mark_absent(name, date)
            marked_absent.append(name)

    from attendance_db import _to_date_str
    return {
        "date":         _to_date_str(date),
        "present":      marked_present,
        "absent":       marked_absent,
        "total_amount": total_amount,
    }


# Re-export so callers can do `from logic import get_attendance_by_date` etc.
__all__ = [
    "init_files", "load_players", "save_players",
    "add_player", "remove_player", "generate_balanced_groups",
    "mark_attendance",
    "mark_present", "mark_absent",
    "get_attendance_by_date", "get_all_attendance", "get_attendance_by_player",
]
