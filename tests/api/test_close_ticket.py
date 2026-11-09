from api import close_ticket
from tests.conftest import body_of, event


def test_sets_status_closed(open_ticket, table):
    resp = close_ticket.handler(event(path={"ticketId": "T-0001"}), None)
    assert resp["statusCode"] == 200
    assert table.items["T-0001"]["status"] == "CLOSED"


def test_stamps_closed_at_in_iso_utc(open_ticket):
    resp = close_ticket.handler(event(path={"ticketId": "T-0001"}), None)
    closed_at = body_of(resp)["closedAt"]
    assert closed_at.endswith("Z") and len(closed_at) == 20


def test_keeps_other_fields(open_ticket):
    resp = close_ticket.handler(event(path={"ticketId": "T-0001"}), None)
    ticket = body_of(resp)
    assert ticket["requester"] == "Ada Lovelace"
    assert ticket["createdAt"] == "2026-11-01T09:00:00Z"


def test_returns_409_if_already_closed(closed_ticket):
    resp = close_ticket.handler(event(path={"ticketId": "T-0002"}), None)
    assert resp["statusCode"] == 409


def test_returns_404_for_unknown_ticket():
    resp = close_ticket.handler(event(path={"ticketId": "T-NOPE"}), None)
    assert resp["statusCode"] == 404
