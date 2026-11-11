"""Export destination: bucket and key are derived from the Run_Date."""
import pytest

from export.nightly_export import run_export

RUN_DATES = ("2026-06-15", "2026-01-01", "2026-12-31", "2028-02-29", "2026-03-04")


def _closed(ticket_id, subject="x", closed_at="2026-01-02T00:00:00Z"):
    return {
        "ticketId": ticket_id,
        "status": "CLOSED",
        "requester": subject,
        "priority": "P3",
        "createdAt": "2026-01-01T00:00:00Z",
        "closedAt": closed_at,
    }


TICKET_SETS = {
    "empty": [],
    "non_empty": [_closed("T-0001"), _closed("T-0002")],
}


# Feature: nightly-ticket-export, Property 3: Destination key follows the Run_Date
# Validates: Requirements 4.1, 4.2
@pytest.mark.parametrize("run_date", RUN_DATES)
@pytest.mark.parametrize("tickets", TICKET_SETS.values(), ids=TICKET_SETS.keys())
def test_destination_key_follows_run_date(table, s3, bucket_name, run_date, tickets):
    for t in tickets:
        table.put_item(Item=t)

    run_export(table, s3, bucket_name, run_date)

    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["Bucket"] == bucket_name
    assert call["Key"] == f"ticket-exports/closed-tickets-{run_date}.csv"
    assert call["Key"].startswith("ticket-exports/")


# Feature: nightly-ticket-export, Property 3: Destination key follows the Run_Date
# Validates: Requirements 4.1, 4.2
def test_same_run_date_overwrites_with_latest_content(table, s3, bucket_name):
    run_date = "2026-06-15"
    in_window = "2026-06-14T12:00:00Z"
    table.put_item(Item=_closed("T-0001", closed_at=in_window))
    run_export(table, s3, bucket_name, run_date)

    table.put_item(Item=_closed("T-0002", closed_at=in_window))
    run_export(table, s3, bucket_name, run_date)

    assert len(s3.calls) == 2
    assert len(s3.objects) == 1
    stored = s3.objects[(bucket_name, f"ticket-exports/closed-tickets-{run_date}.csv")]
    assert stored == s3.calls[-1]["Body"]
    assert b"T-0002" in stored
