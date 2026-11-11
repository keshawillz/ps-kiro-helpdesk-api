"""Requirement 2.1: the export follows LastEvaluatedKey and never scans."""
import csv
import io

from export.nightly_export import export_key, run_export

RUN_DATE = "2026-11-03"


def _add_closed(table, count):
    for n in range(count):
        table.put_item(
            Item={
                "ticketId": f"T-{n:04d}",
                "status": "CLOSED",
                "requester": f"user{n}",
                "priority": "P3",
                "createdAt": "2026-11-01T08:00:00Z",
                "closedAt": f"2026-11-02T10:{n:02d}:00Z",
            }
        )


def test_every_ticket_exported_across_single_item_pages(table, s3, bucket_name):
    table.page_size = 1
    _add_closed(table, 5)

    result = run_export(table, s3, bucket_name, RUN_DATE)

    body = s3.objects[(bucket_name, export_key(RUN_DATE))].decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(body)))
    assert result["count"] == 5
    assert sorted(r["ticketId"] for r in rows) == [f"T-{n:04d}" for n in range(5)]


def test_export_never_calls_scan(table, s3, bucket_name):
    # FakeTable has no scan method, so any scan call would raise AttributeError.
    assert not hasattr(table, "scan")
    table.page_size = 1
    _add_closed(table, 3)

    run_export(table, s3, bucket_name, RUN_DATE)

    assert len(s3.calls) == 1
