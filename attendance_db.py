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
_COLLECTION = "attendance"

def _to_date_str(date) -> str:
    if date is None:
        return str(_date_type.today())
    if isinstance(date, _date_type):
        return date.isoformat()
    date = str(date).strip()
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise ValueError(f"Invalid date format '{date}'. Use YYYY-MM-DD.")
    return date

def _doc_id(player_name: str, date_str: str) -> str:
    return f"{player_name.strip()}_{date_str}"

def mark_present(player_name: str, date=None, amount=0.0) -> None:
    _mark(player_name, date, "present", amount)

def mark_absent(player_name: str, date=None) -> None:
    _mark(player_name, date, "absent", 0.0)

def _mark(player_name: str, date, status: str, amount=0.0) -> None:
    date_str = _to_date_str(date)
    doc_ref  = _db.collection(_COLLECTION).document(_doc_id(player_name, date_str))
    doc_ref.set({
        "player_name": player_name.strip(),
        "date":        date_str,
        "status":      status,
        "amount":      float(amount),
    })

def get_attendance_by_date(date=None) -> list[dict]:
    date_str = _to_date_str(date)
    docs = _db.collection(_COLLECTION).where("date", "==", date_str).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda r: r["player_name"])

def get_all_attendance() -> list[dict]:
    docs = _db.collection(_COLLECTION).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda r: (r["date"], r["player_name"]), reverse=True)

def get_attendance_by_player(player_name: str) -> list[dict]:
    docs = _db.collection(_COLLECTION).where("player_name", "==", player_name.strip()).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda r: r["date"], reverse=True)