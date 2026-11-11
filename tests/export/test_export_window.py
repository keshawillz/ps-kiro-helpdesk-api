import pytest

from export.nightly_export import export_window


def test_window_is_previous_utc_day():
    assert export_window("2026-11-11") == (
        "2026-11-10T00:00:00Z",
        "2026-11-10T23:59:59Z",
    )


@pytest.mark.parametrize(
    "run_date, day",
    [
        ("2026-03-01", "2026-02-28"),  # month rollover (non-leap February)
        ("2027-01-01", "2026-12-31"),  # year rollover
        ("2028-03-01", "2028-02-29"),  # leap-day rollover
    ],
)
def test_window_rolls_over_boundaries(run_date, day):
    assert export_window(run_date) == (f"{day}T00:00:00Z", f"{day}T23:59:59Z")
