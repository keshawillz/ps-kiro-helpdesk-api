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

    # Maximum items returned per query page; None means one unlimited page.
    page_size: int | None = None

    def query(self, **kwargs):
        """Query an index with status = :closed AND closedAt BETWEEN :start AND :end.

        Results are sorted by (closedAt, ticketId). Items without closedAt are
        not in the index. Pages hold at most page_size items, and a page that
        is not the last carries LastEvaluatedKey (index keys plus ticketId).
        """
        if not kwargs.get("IndexName"):
            raise ValueError("FakeTable.query requires IndexName")
        values = kwargs["ExpressionAttributeValues"]
        closed, start, end = values[":closed"], values[":start"], values[":end"]

        matches = sorted(
            (
                item
                for item in self.items.values()
                if item.get("status") == closed
                and item.get("closedAt") is not None
                and start <= item["closedAt"] <= end
            ),
            key=lambda item: (item["closedAt"], item["ticketId"]),
        )

        last = kwargs.get("ExclusiveStartKey")
        if last is not None:
            after = (last["closedAt"], last["ticketId"])
            matches = [m for m in matches if (m["closedAt"], m["ticketId"]) > after]

        page = matches if self.page_size is None else matches[: self.page_size]
        result = {"Items": [dict(item) for item in page]}
        if self.page_size is not None and len(matches) > self.page_size:
            tail = page[-1]
            result["LastEvaluatedKey"] = {
                "ticketId": tail["ticketId"],
                "status": tail["status"],
                "closedAt": tail["closedAt"],
            }
        return result


class FakeS3:
    """Just enough of the boto3 S3 client for the export."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.calls: list[dict] = []

    def put_object(self, Bucket, Key, Body, ContentType):
        self.calls.append(
            {"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType}
        )
        self.objects[(Bucket, Key)] = Body


@pytest.fixture
def table():
    return FakeTable()


@pytest.fixture
def s3():
    return FakeS3()


@pytest.fixture
def bucket_name():
    return "helpdesk-finance-exports-123456789012"


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
