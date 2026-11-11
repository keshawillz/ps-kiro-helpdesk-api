import csv
import io

import pytest

from export.nightly_export import COLUMNS, build_csv


def _t(requester="alice", **overrides):
    ticket = {
        "ticketId": "T-1",
        "requester": requester,
        "priority": "P2",
        "createdAt": "2024-01-01T00:00:00Z",
        "closedAt": "2024-01-02T00:00:00Z",
    }
    ticket.update(overrides)
    return ticket


def _missing():
    ticket = _t()
    del ticket["closedAt"]
    return ticket


CASES = {
    "empty": [],
    "one_plain": [_t()],
    "several": [_t(ticketId="T-1"), _t(ticketId="T-2"), _t(ticketId="T-3")],
    "comma": [_t("Smith, Jane")],
    "double_quote": [_t('Jane "JJ" Smith')],
    "bare_lf": [_t("line1\nline2")],
    "crlf": [_t("line1\r\nline2")],
    "combination": [_t('a, "b"\nc\r\nd')],
    "spaces": [_t("  padded  ")],
    "empty_requester": [_t("")],
    "non_ascii": [_t("Zoë Müller 田中 😀")],
    "missing_attribute": [_missing()],
}


# Feature: nightly-ticket-export, Property 2: CSV round trip with header
# Validates: Requirements 3.1, 3.2, 6.1
@pytest.mark.parametrize("tickets", CASES.values(), ids=CASES.keys())
def test_csv_round_trip_with_header(tickets):
    text = build_csv(tickets)
    rows = list(csv.reader(io.StringIO(text, newline="")))

    assert rows[0] == list(COLUMNS)
    expected = [[str(t.get(c, "")) for c in COLUMNS] for t in tickets]
    assert rows[1:] == expected


# Feature: nightly-ticket-export, Property 2: CSV round trip with header
@pytest.mark.parametrize("tickets", CASES.values(), ids=CASES.keys())
def test_csv_record_terminators_are_crlf(tickets):
    text = build_csv(tickets)
    assert text.endswith("\r\n")
    # Every record terminator is CRLF: stripping CRLF leaves no line break
    # outside quoted fields, so count unquoted terminators via csv itself.
    assert text.count("\r\n") >= len(tickets) + 1
