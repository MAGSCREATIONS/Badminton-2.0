import json
import os
from datetime import datetime, timezone
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


_SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
_SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


def _load_service_account_info() -> dict:
    creds_json = os.environ.get("FIREBASE_CREDENTIALS")
    if creds_json:
        return json.loads(creds_json)

    with open("serviceAccountKey.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _build_session() -> AuthorizedSession:
    info = _load_service_account_info()
    creds = service_account.Credentials.from_service_account_info(info, scopes=_SHEETS_SCOPE)
    return AuthorizedSession(creds)


def _get_sheet_config() -> tuple[str, str]:
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        raise ValueError("Set GOOGLE_SHEETS_SPREADSHEET_ID to enable Google Sheets export.")

    tab_name = os.environ.get("GOOGLE_SHEETS_TAB_NAME", "Session Summary").strip() or "Session Summary"
    return spreadsheet_id, tab_name


def _fetch_sheet_titles(session: AuthorizedSession, spreadsheet_id: str) -> list[str]:
    url = f"{_SHEETS_API_BASE}/{spreadsheet_id}?fields=sheets.properties.title"
    res = session.get(url)
    if not res.ok:
        raise ValueError(f"Unable to read spreadsheet metadata: {res.text}")

    data = res.json()
    return [sheet["properties"]["title"] for sheet in data.get("sheets", [])]


def _ensure_sheet_exists(session: AuthorizedSession, spreadsheet_id: str, tab_name: str) -> None:
    titles = _fetch_sheet_titles(session, spreadsheet_id)
    if tab_name in titles:
        return

    url = f"{_SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate"
    body = {"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
    res = session.post(url, json=body)
    if not res.ok:
        raise ValueError(f"Unable to create sheet tab '{tab_name}': {res.text}")


def _clear_sheet(session: AuthorizedSession, spreadsheet_id: str, tab_name: str) -> None:
    range_name = quote(f"'{tab_name}'!A:Z", safe="")
    url = f"{_SHEETS_API_BASE}/{spreadsheet_id}/values/{range_name}:clear"
    res = session.post(url, json={})
    if not res.ok:
        raise ValueError(f"Unable to clear sheet tab '{tab_name}': {res.text}")


def _write_values(session: AuthorizedSession, spreadsheet_id: str, tab_name: str, values: list[list]) -> None:
    range_name = quote(f"'{tab_name}'!A1", safe="")
    url = f"{_SHEETS_API_BASE}/{spreadsheet_id}/values/{range_name}?valueInputOption=USER_ENTERED"
    res = session.put(url, json={"values": values})
    if not res.ok:
        raise ValueError(f"Unable to write summary to Google Sheets: {res.text}")


def export_session_summary(summary_rows: list[dict]) -> dict:
    spreadsheet_id, tab_name = _get_sheet_config()
    session = _build_session()
    _ensure_sheet_exists(session, spreadsheet_id, tab_name)
    _clear_sheet(session, spreadsheet_id, tab_name)

    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = [
        ["Session Summary Export"],
        ["Exported At", exported_at],
        [],
        ["Player Name", "Total Hours", "Total Due", "Advance Paid", "Status", "Balance Amount"],
    ]

    total_hours = 0.0
    total_due = 0.0
    total_paid = 0.0
    total_balance = 0.0

    for row in summary_rows:
        balance = round(float(row.get("balance", 0)), 2)
        status = "Advance" if balance > 0 else "Balance" if balance < 0 else "Settled"
        balance_amount = abs(balance) if balance < 0 else balance

        total_hours += float(row.get("total_hours", 0))
        total_due += float(row.get("total_due", 0))
        total_paid += float(row.get("total_paid", 0))
        total_balance += balance

        rows.append([
            row.get("name", ""),
            round(float(row.get("total_hours", 0)), 1),
            round(float(row.get("total_due", 0)), 2),
            round(float(row.get("total_paid", 0)), 2),
            status,
            round(balance_amount, 2),
        ])

    rows.append([])
    rows.append([
        "Totals",
        round(total_hours, 1),
        round(total_due, 2),
        round(total_paid, 2),
        "Net Balance",
        round(total_balance, 2),
    ])

    _write_values(session, spreadsheet_id, tab_name, rows)
    return {
        "success": True,
        "spreadsheet_id": spreadsheet_id,
        "tab_name": tab_name,
        "rows_exported": len(summary_rows),
    }
