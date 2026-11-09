from api import update_ticket
from tests.conftest import body_of, event


def test_updates_priority(open_ticket):
    resp = update_ticket.handler(event({"priority": "P1"}, {"ticketId": "T-0001"}), None)
    assert resp["statusCode"] == 200
    assert body_of(resp)["priority"] == "P1"


def test_updates_assignee(open_ticket):
    resp = update_ticket.handler(event({"assignee": "ops-team"}, {"ticketId": "T-0001"}), None)
    assert body_of(resp)["assignee"] == "ops-team"


def test_rejects_closing_through_update(open_ticket):
    resp = update_ticket.handler(event({"status": "CLOSED"}, {"ticketId": "T-0001"}), None)
    assert resp["statusCode"] == 400
    assert "close endpoint" in body_of(resp)["error"]


def test_returns_404_for_unknown_ticket():
    resp = update_ticket.handler(event({"priority": "P1"}, {"ticketId": "T-NOPE"}), None)
    assert resp["statusCode"] == 404


def test_rejects_body_with_no_allowed_fields(open_ticket):
    resp = update_ticket.handler(event({"color": "blue"}, {"ticketId": "T-0001"}), None)
    assert resp["statusCode"] == 400


def test_refuses_to_update_closed_ticket(closed_ticket):
    resp = update_ticket.handler(event({"priority": "P4"}, {"ticketId": "T-0002"}), None)
    assert resp["statusCode"] == 409
