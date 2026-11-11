"""utc_run_date returns the UTC calendar date as YYYY-MM-DD."""
from datetime import datetime, timezone

import pytest

from export import nightly_export


def _freeze(monkeypatch, fixed):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed

    monkeypatch.setattr(nightly_export, "datetime", FrozenDatetime)


@pytest.mark.parametrize(
    "fixed, expected",
    [
        (datetime(2026, 11, 3, 6, 0, 0, tzinfo=timezone.utc), "2026-11-03"),
        (datetime(2026, 11, 3, 23, 59, 59, tzinfo=timezone.utc), "2026-11-03"),
        (datetime(2026, 11, 4, 0, 0, 0, tzinfo=timezone.utc), "2026-11-04"),
        (datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc), "2026-12-31"),
        (datetime(2027, 1, 1, 0, 0, 1, tzinfo=timezone.utc), "2027-01-01"),
    ],
)
def test_utc_run_date_formats_fixed_clock(monkeypatch, fixed, expected):
    _freeze(monkeypatch, fixed)

    assert nightly_export.utc_run_date() == expected
