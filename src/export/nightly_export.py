"""Nightly export of CLOSED tickets to the Finance exports bucket as CSV."""

import csv
import io
import os
from datetime import datetime, timedelta, timezone

INDEX_NAME = "helpdesk-tickets-status-closedat"
COLUMNS = ("ticketId", "requester", "priority", "createdAt", "closedAt")
EXPORT_PREFIX = "ticket-exports/"


def export_key(run_date: str) -> str:
    """Return the S3 key for the given Run_Date (YYYY-MM-DD)."""
    return f"{EXPORT_PREFIX}closed-tickets-{run_date}.csv"


def utc_run_date() -> str:
    """Return today's UTC date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def export_window(run_date: str) -> tuple[str, str]:
    """Return (start, end) of the UTC day before run_date (YYYY-MM-DD)."""
    day = datetime.strptime(run_date, "%Y-%m-%d") - timedelta(days=1)
    prefix = day.strftime("%Y-%m-%d")
    return f"{prefix}T00:00:00Z", f"{prefix}T23:59:59Z"


def query_closed_tickets(
    table, window_start: str, window_end: str, index_name: str = INDEX_NAME
) -> list[dict]:
    """Return CLOSED tickets with closedAt in [window_start, window_end].

    Queries the status/closedAt index and follows LastEvaluatedKey until it
    is absent.
    """
    kwargs = {
        "IndexName": index_name,
        "KeyConditionExpression": "#s = :closed AND #c BETWEEN :start AND :end",
        "ExpressionAttributeNames": {"#s": "status", "#c": "closedAt"},
        "ExpressionAttributeValues": {
            ":closed": "CLOSED",
            ":start": window_start,
            ":end": window_end,
        },
    }
    items: list[dict] = []
    while True:
        page = table.query(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return items


def build_csv(tickets: list[dict]) -> str:
    """Build an RFC 4180 CSV: header row, then one row per ticket."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for ticket in tickets:
        writer.writerow([str(ticket.get(c, "")) for c in COLUMNS])
    return buffer.getvalue()


def run_export(
    table, s3, bucket: str, run_date: str, index_name: str = INDEX_NAME
) -> dict:
    """Query the Export_Window, build, upload. Returns {"key": ..., "count": n}."""
    window_start, window_end = export_window(run_date)
    tickets = query_closed_tickets(table, window_start, window_end, index_name)
    body = build_csv(tickets)
    key = export_key(run_date)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="text/csv; charset=utf-8",
    )
    return {"key": key, "count": len(tickets)}


def handler(event, context) -> dict:
    """Lambda entry point. Wires real boto3 clients and calls run_export."""
    import boto3

    table_name = os.environ["TABLE_NAME"]
    index_name = os.environ["INDEX_NAME"]
    bucket = os.environ["BUCKET_NAME"]
    table = boto3.resource("dynamodb").Table(table_name)
    s3 = boto3.client("s3")
    return run_export(table, s3, bucket, utc_run_date(), index_name)
