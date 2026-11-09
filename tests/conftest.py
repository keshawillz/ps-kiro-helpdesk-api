"""Shared fixtures. Tests never touch AWS; they use an in-memory store."""
import json

import pytest

from api import common
from api.ticket_store import TicketStore


class FakeTable:
    """Just enough of the boto3 Table interface for the handlers."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, Key):
        item = self.items.get(Key["ticketId"])
        return {"Item": dict(item)} if item else {}

    def put_item(self, Item):
        self.items[Item["ticketId"]] = dict(Item)

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames,
                    ExpressionAttributeValues, ReturnValues):
        item = self.items[Key["ticketId"]]
        for placeholder, name in ExpressionAttributeNames.items():
            item[name] = ExpressionAttributeValues[":" + placeholder[1:]]
        return {"Attributes": dict(item)}


@pytest.fixture
def table():
    return FakeTable()


@pytest.fixture(autouse=True)
def store(table):
    s = TicketStore(table)
    common.set_store(s)
    yield s
    common.set_store(None)


@pytest.fixture
def open_ticket(table):
    ticket = {
        "ticketId": "T-0001",
        "status": "OPEN",
        "requester": "Ada Lovelace",
        "subject": "VPN drops every hour",
        "priority": "P2",
        "createdAt": "2026-11-01T09:00:00Z",
    }
    table.put_item(Item=ticket)
    return ticket


@pytest.fixture
def closed_ticket(table):
    ticket = {
        "ticketId": "T-0002",
        "status": "CLOSED",
        "requester": "Grace Hopper",
        "subject": "Badge reader offline",
        "priority": "P1",
        "createdAt": "2026-11-01T10:00:00Z",
        "closedAt": "2026-11-02T15:30:00Z",
    }
    table.put_item(Item=ticket)
    return ticket


def event(body=None, path=None):
    """Build a minimal API Gateway proxy event."""
    return {
        "body": json.dumps(body) if isinstance(body, dict) else body,
        "pathParameters": path,
    }


def body_of(resp):
    return json.loads(resp["body"])
