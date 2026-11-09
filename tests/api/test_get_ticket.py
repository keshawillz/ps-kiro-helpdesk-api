from api import get_ticket
from tests.conftest import body_of, event


def test_returns_existing_ticket(open_ticket):
    resp = get_ticket.handler(event(path={"ticketId": "T-0001"}), None)
    assert resp["statusCode"] == 200
    assert body_of(resp) == open_ticket


def test_returns_404_for_unknown_ticket():
    resp = get_ticket.handler(event(path={"ticketId": "T-NOPE"}), None)
    assert resp["statusCode"] == 404


def test_returns_400_without_ticket_id():
    resp = get_ticket.handler(event(path=None), None)
    assert resp["statusCode"] == 400


def test_response_is_json(open_ticket):
    resp = get_ticket.handler(event(path={"ticketId": "T-0001"}), None)
    assert resp["headers"]["Content-Type"] == "application/json"
