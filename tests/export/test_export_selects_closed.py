"""Export contains exactly the tickets closed in the Export_Window."""
import csv
import io

import pytest

from export.nightly_export import export_key, run_export

RUN_DATE = "2026-11-11"  # window: 2026-11-10T00:00:00Z .. 2026-11-10T23:59:59Z

IN_WINDOW = "2026-11-10T12:00:00Z"
EARLIER = "2026-11-05T12:00:00Z"

# Each mix is a list of (status, closedAt); ticket ids are assigned in order.
MIXES = {
    "all_closed_in_window": [
        ("CLOSED", "2026-11-10T01:00:00Z"),
        ("CLOSED", "2026-11-10T06:00:00Z"),
        ("CLOSED", IN_WINDOW),
        ("CLOSED", "2026-11-10T18:30:00Z"),
        ("CLOSED", "2026-11-10T22:00:00Z"),
    ],
    "none_closed": [("OPEN", None), ("IN_PROGRESS", None), ("OPEN", None)],
    "one_of_each_status": [
        ("OPEN", None),
        ("IN_PROGRESS", None),
        ("CLOSED", IN_WINDOW),
    ],
    "closed_in_window_mixed_with_earlier": [
        ("CLOSED", EARLIER),
        ("CLOSED", IN_WINDOW),
        ("OPEN", None),
        ("CLOSED", "2026-11-09T08:00:00Z"),
        ("CLOSED", "2026-11-10T09:00:00Z"),
        ("IN_PROGRESS", None),
        ("CLOSED", "2026-11-01T00:00:00Z"),
    ],
}

BOUNDARIES = {
    "window_start_included": ("2026-11-10T00:00:00Z", True),
    "window_end_included": ("2026-11-10T23:59:59Z", True),
    "just_before_window_excluded": ("2026-11-09T23:59:59Z", False),
    "next_day_start_excluded": ("2026-11-11T00:00:00Z", False),
}

# None = unlimited; 100 is larger than any table here.
PAGE_SIZES = [None, 1, 2, 3, 100]


def _put(table, index, status, closed_at):
    ticket_id = f"T-{index:04d}"
    item = {
        "ticketId": ticket_id,
        "status": status,
        "requester": f"user{index}",
        "priority": "P3",
        "createdAt": "2026-11-01T09:00:00Z",
    }
    if closed_at is not None:
        item["closedAt"] = closed_at
    table.put_item(Item=item)
    return ticket_id


def _exported_ids(s3, bucket_name):
    body = s3.objects[(bucket_name, export_key(RUN_DATE))].decode("utf-8")
    rows = list(csv.reader(io.StringIO(body, newline="")))
    return [row[0] for row in rows[1:]]


# Feature: nightly-ticket-export, Property 1: Export contains exactly the tickets closed in the Export_Window
@pytest.mark.parametrize("page_size", PAGE_SIZES)
@pytest.mark.parametrize("mix", MIXES.values(), ids=MIXES.keys())
def test_export_contains_exactly_tickets_closed_in_window(
    table, s3, bucket_name, mix, page_size
):
    expected = []
    for i, (status, closed_at) in enumerate(mix, start=1):
        ticket_id = _put(table, i, status, closed_at)
        if status == "CLOSED" and "2026-11-10T00:00:00Z" <= closed_at <= "2026-11-10T23:59:59Z":
            expected.append(ticket_id)
    table.page_size = page_size

    result = run_export(table, s3, bucket_name, RUN_DATE)

    exported_ids = _exported_ids(s3, bucket_name)
    assert sorted(exported_ids) == sorted(expected)
    assert len(exported_ids) == len(set(exported_ids))
    assert result["count"] == len(expected)


# Feature: nightly-ticket-export, Property 1: Export contains exactly the tickets closed in the Export_Window
@pytest.mark.parametrize("page_size", PAGE_SIZES)
@pytest.mark.parametrize(
    "closed_at, included", BOUNDARIES.values(), ids=BOUNDARIES.keys()
)
def test_export_window_boundaries(
    table, s3, bucket_name, closed_at, included, page_size
):
    ticket_id = _put(table, 1, "CLOSED", closed_at)
    table.page_size = page_size

    run_export(table, s3, bucket_name, RUN_DATE)

    expected = [ticket_id] if included else []
    assert _exported_ids(s3, bucket_name) == expected
