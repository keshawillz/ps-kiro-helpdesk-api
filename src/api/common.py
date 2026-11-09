"""Shared helpers for the ticket API handlers."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from api.ticket_store import TicketStore

PRIORITIES = ("P1", "P2", "P3", "P4")
OPEN_STATUSES = ("OPEN", "IN_PROGRESS")
CLOSED = "CLOSED"

_store: Optional[TicketStore] = None


def get_store() -> TicketStore:
    """Return the ticket store. Tests swap this with a fake via set_store()."""
    global _store
    if _store is None:
        import boto3  # imported here so tests never need AWS credentials

        table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
        _store = TicketStore(table)
    return _store


def set_store(store: Optional[TicketStore]) -> None:
    global _store
    _store = store


def now_iso() -> str:
    """Current UTC time as ISO 8601 with a Z suffix, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def response(status: int, body: Any) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def error(status: int, message: str) -> dict:
    return response(status, {"error": message})


def parse_body(event: dict) -> Optional[dict]:
    """Parse the JSON body. Returns None if the body is missing or not an object."""
    raw = event.get("body")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def path_param(event: dict, name: str) -> Optional[str]:
    params = event.get("pathParameters") or {}
    value = params.get(name)
    return value if value else None
