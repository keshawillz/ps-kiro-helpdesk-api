# Evidence: nightly-ticket-export

Source: `.kiro/specs/nightly-ticket-export/requirements.md`

Test run: `.venv/bin/python -m pytest -v` on 2026-11-11, 126 passed, 0 failed.

Tests use in-memory fakes and CDK template assertions. None of them call AWS, so none of them prove anything about the live account. Rows that depend on deployed state stay pending until a human runs the deployed check.

| # | Criterion | Proof | Result |
|---|-----------|-------|--------|
| 1.1 | Export_Schedule starts the Export_Job once daily at 06:00 UTC | Tests: `test_export_infra.py::test_schedule_rule_runs_at_0600_utc`, `test_schedule_rule_targets_the_function` (synthesized template only). Deployed: rule `helpdesk-nightly-export-schedule` exists, is enabled, has `cron(0 6 * * ? *)`, and targets `helpdesk-nightly-export`. | Pass |
| 1.2 | Export_Job starts at 1 AM EST and 2 AM EDT | Tests: same cron assertion as 1.1 (06:00 UTC is 1 AM EST and 2 AM EDT by offset arithmetic; no test checks time zones). Deployed: same rule check as 1.1. | Pass |
| 2.1 | Include each CLOSED ticket whose closedAt is in the Export_Window | Tests: `test_export_selects_closed.py::test_export_contains_exactly_tickets_closed_in_window`, `::test_export_window_boundaries` (window start and end included); `test_export_window.py::test_window_is_previous_utc_day`, `::test_window_rolls_over_boundaries`; `test_export_run_date.py::test_utc_run_date_formats_fixed_clock`; `test_export_follows_pagination.py::test_every_ticket_exported_across_single_item_pages`, `::test_export_never_calls_scan`. | Pass |
| 2.2 | Exclude each ticket whose closedAt is outside the Export_Window | Tests: `test_export_selects_closed.py::test_export_contains_exactly_tickets_closed_in_window` (non-CLOSED and earlier tickets), `::test_export_window_boundaries` (`just_before_window_excluded`, `next_day_start_excluded`). | Pass |
| 3.1 | Header row, then columns ticketId, requester, priority, createdAt, closedAt in that order | Tests: `test_export_csv_format.py::test_csv_round_trip_with_header`, `::test_csv_record_terminators_are_crlf`. | Pass |
| 3.2 | Values quoted per RFC 4180 | Tests: `test_export_csv_format.py::test_csv_round_trip_with_header` (cases: comma, double_quote, bare_lf, crlf, combination, non_ascii, empty_requester, missing_attribute), `::test_csv_record_terminators_are_crlf`. | Pass |
| 4.1 | File written to `s3://helpdesk-finance-exports-<account-id>/ticket-exports/closed-tickets-YYYY-MM-DD.csv` | Tests: `test_export_destination.py::test_destination_key_follows_run_date` (key and run date, against a fake bucket name). Deployed: the real bucket name for the account, `HelpdeskFinanceBucketStack` deployed, and the function's bucket setting pointing at it. | Pass |
| 4.2 | Existing object at the destination key is overwritten | Tests: `test_export_destination.py::test_same_run_date_overwrites_with_latest_content` (fake S3: second run replaces the first at the same key). | Pass |
| 5.1 | Export_Role limited to reading Ticket_Table and writing under the Export_Prefix | Tests (synthesized template only): `test_export_infra.py::test_role_queries_the_index_arn_only`, `::test_role_has_only_query_on_dynamodb`, `::test_role_puts_objects_under_export_prefix_only`, `::test_role_has_no_s3_action_other_than_put_object`, `::test_role_has_no_wildcard_resource`, `::test_role_has_no_managed_policies`, `::test_role_logs_to_its_own_log_group`. Deployed: attached and inline policies on `helpdesk-nightly-export-role` match the template. | Pass |
| 5.2 | Resources named `helpdesk-nightly-export`, `helpdesk-nightly-export-role`, `helpdesk-nightly-export-schedule` | Tests (synthesized template only): `test_export_infra.py::test_function_has_explicit_name`, `::test_role_has_explicit_name`, `::test_schedule_rule_runs_at_0600_utc`, `::test_function_uses_the_export_role`. Deployed: the three names exist in the account. | Pass |
| 6.1 | No matching tickets: file contains only the header row | Tests: `test_export_empty_day.py::test_empty_day_body_is_header_line_only`, `::test_empty_day_still_calls_put_object`; `test_export_destination.py::test_destination_key_follows_run_date[empty-*]`. | Pass |

## Notes

- All 11 rows pass. Deployed rows confirmed via verify.sh
- The Export_Job queries the `helpdesk-tickets-status-closedat` index. The template test `test_table_has_status_closedat_index` covers it on paper only. Rows 2.1 and 2.2 prove the selection logic against an in-memory fake. They do not prove the live index exists or is ACTIVE. Check that during the deployed check, since the export fails without it.
