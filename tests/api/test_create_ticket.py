from api import create_ticket
from tests.conftest import body_of, event


def test_creates_ticket_with_open_status(table):
    resp = create_ticket.handler(event({"requester": "Ada", "subject": "VPN", "priority": "P2"}), None)
    assert resp["statusCode"] == 201
    ticket = body_of(resp)
    assert ticket["status"] == "OPEN"
    assert table.items[ticket["ticketId"]]["status"] == "OPEN"


def test_generates_prefixed_ticket_id():
    resp = create_ticket.handler(event({"requester": "Ada", "subject": "VPN"}), None)
    assert body_of(resp)["ticketId"].startswith("T-")


def test_stamps_created_at_in_iso_utc():
    resp = create_ticket.handler(event({"requester": "Ada", "subject": "VPN"}), None)
    created = body_of(resp)["createdAt"]
    assert created.endswith("Z") and len(created) == 20


def test_defaults_priority_to_p3():
    resp = create_ticket.handler(event({"requester": "Ada", "subject": "VPN"}), None)
    assert body_of(resp)["priority"] == "P3"


def test_rejects_missing_requester():
    resp = create_ticket.handler(event({"subject": "VPN"}), None)
    assert resp["statusCode"] == 400
    assert "requester" in body_of(resp)["error"]


def test_rejects_invalid_priority():
    resp = create_ticket.handler(event({"requester": "Ada", "subject": "VPN", "priority": "P9"}), None)
    assert resp["statusCode"] == 400


def test_rejects_malformed_json():
    resp = create_ticket.handler(event("{not json"), None)
    assert resp["statusCode"] == 400
