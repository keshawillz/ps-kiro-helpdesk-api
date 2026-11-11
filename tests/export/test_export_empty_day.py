"""Empty day: no closed tickets still produces a header-only export."""
from export.nightly_export import COLUMNS, run_export


def test_empty_day_body_is_header_line_only(table, s3, bucket_name, open_ticket):
    result = run_export(table, s3, bucket_name, "2026-11-03")

    expected = (",".join(COLUMNS) + "\r\n").encode("utf-8")
    assert s3.objects[(bucket_name, result["key"])] == expected


def test_empty_day_still_calls_put_object(table, s3, bucket_name):
    result = run_export(table, s3, bucket_name, "2026-11-03")

    assert len(s3.calls) == 1
    assert result["count"] == 0
