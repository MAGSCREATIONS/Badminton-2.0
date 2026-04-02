"""
session_db.py
-------------
Firebase Firestore-backed session tracking.

Per-player fields stored:
    name, hours_played, amount_due, amount_paid
    → balance = amount_paid - amount_due
      positive = advance (overpaid), negative = balance owed
"""

import os
import json
from datetime import date as _date_type

import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")
    if firebase_creds:
        cred = credentials.Certificate(json.loads(firebase_creds))
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

_db = firestore.client()
_COLLECTION   = "sessions"
RATE_PER_COURT_PER_HOUR = 350


def _to_date_str(date) -> str:
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    return str(date).strip()


def create_session(date, courts: int, session_hours: float, player_hours: dict) -> dict:
    """
    Creates/overwrites a session. Calculates each player's share
    proportionally based on hours played.
    Preserves any existing payments if session already exists.
    """
    date_str   = _to_date_str(date)
    total_cost = courts * session_hours * RATE_PER_COURT_PER_HOUR
    total_hrs  = sum(h for h in player_hours.values() if h > 0)

    # Load existing payments if session already exists
    existing_payments = {}
    existing_doc = _db.collection(_COLLECTION).document(date_str).get()
    if existing_doc.exists:
        for p in existing_doc.to_dict().get("players", []):
            existing_payments[p["name"]] = p.get("amount_paid", 0)

    players = []
    for name, hrs in player_hours.items():
        share = round((hrs / total_hrs) * total_cost, 2) if total_hrs > 0 and hrs > 0 else 0
        paid  = existing_payments.get(name, 0)
        players.append({
            "name":         name,
            "hours_played": hrs,
            "amount_due":   share,
            "amount_paid":  paid,
            "balance":      round(paid - share, 2),  # + = advance, - = owes
        })

    session = {
        "date":       date_str,
        "courts":     courts,
        "hours":      session_hours,
        "total_cost": total_cost,
        "players":    players,
    }
    _db.collection(_COLLECTION).document(date_str).set(session)
    return session


def get_session(date=None) -> dict | None:
    date_str = _to_date_str(date)
    doc = _db.collection(_COLLECTION).document(date_str).get()
    return doc.to_dict() if doc.exists else None


def get_all_sessions() -> list[dict]:
    docs = _db.collection(_COLLECTION).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda s: s["date"], reverse=True)


def record_payment(date, player_name: str, amount: float) -> dict:
    """
    Adds a payment for a player and recomputes their balance.
    Returns the updated player record.
    """
    date_str = _to_date_str(date)
    doc_ref  = _db.collection(_COLLECTION).document(date_str)
    doc      = doc_ref.get()
    if not doc.exists:
        raise ValueError(f"No session found for {date_str}")

    session = doc.to_dict()
    updated_player = None

    for player in session["players"]:
        if player["name"] == player_name:
            player["amount_paid"] = round(player["amount_paid"] + amount, 2)
            player["balance"]     = round(player["amount_paid"] - player["amount_due"], 2)
            updated_player = player
            break

    if not updated_player:
        raise ValueError(f"Player {player_name} not found in session")

    doc_ref.set(session)
    return updated_player


def get_player_summary() -> list[dict]:
    """
    Returns accumulated stats per player across ALL sessions.
    Each entry: { name, total_hours, total_due, total_paid, balance }
    balance > 0 = advance, balance < 0 = owes, balance == 0 = settled
    """
    docs     = _db.collection(_COLLECTION).stream()
    sessions = [doc.to_dict() for doc in docs]

    totals = {}
    for session in sessions:
        for p in session.get("players", []):
            if p["hours_played"] == 0:
                continue
            name = p["name"]
            if name not in totals:
                totals[name] = {"name": name, "total_hours": 0, "total_due": 0, "total_paid": 0}
            totals[name]["total_hours"] += p["hours_played"]
            totals[name]["total_due"]   += p["amount_due"]
            totals[name]["total_paid"]  += p["amount_paid"]

    result = []
    for name, data in totals.items():
        data["balance"] = round(data["total_paid"] - data["total_due"], 2)
        data["total_due"]   = round(data["total_due"],  2)
        data["total_paid"]  = round(data["total_paid"], 2)
        data["total_hours"] = round(data["total_hours"], 1)
        result.append(data)

    return sorted(result, key=lambda x: x["name"])


# ── NEW: Clear all sessions ─────────────────────────────────────────────

def clear_all_payments() -> dict:
    """
    Resets payment-related session data across all sessions.
    Keeps the session documents, but clears paid amounts, due amounts,
    recorded hours, and balances.
    """
    docs = _db.collection(_COLLECTION).stream()
    sessions_updated = 0
    players_reset = 0

    for doc in docs:
        session = doc.to_dict()
        players = session.get("players", [])

        for player in players:
            if (
                player.get("amount_paid", 0) != 0
                or player.get("amount_due", 0) != 0
                or player.get("hours_played", 0) != 0
                or player.get("balance", 0) != 0
            ):
                players_reset += 1
            player["amount_paid"] = 0
            player["amount_due"] = 0
            player["hours_played"] = 0
            player["balance"] = 0

        if players:
            session["total_cost"] = 0
            doc.reference.set(session)
            sessions_updated += 1

    return {
        "success": True,
        "sessions_updated": sessions_updated,
        "players_reset": players_reset,
    }
