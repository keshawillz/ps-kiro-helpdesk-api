# Implementation Plan: Nightly Ticket Export

## Overview

Python 3.12 Lambda plus a CDK construct, as set out in design.md. The export now selects tickets closed within the Export_Window (the previous UTC day) by running a `Query` on a new global secondary index, `helpdesk-tickets-status-closedat`. There is no `Scan` code path. The work goes in this order: test fakes, the export handler, the infrastructure (index, construct, wiring), then verification. All new code lives in `src/export/`, `infra/nightly_export.py`, and `tests/export/`. The only change to an existing infra file is in `infra/helpdesk_stack.py` (the index and the construct). Nothing under `src/api/` changes. Changes to `tests/conftest.py` are additive only. Tests never call AWS. They run with plain pytest and parametrized cases, with no new dependencies: `.venv/bin/python -m pytest -q`. No deploy task is included, because a human runs `cdk deploy`.

Tasks that were completed for the earlier scan-based design and are not affected by the revision stay checked: 1.1 (S3 fake and scaffold), 2.3, 2.4, 2.5, and 4.2. Parent tasks 1 and 2 are unchecked until their new subtasks finish. Tasks whose code or tests change are unchecked and rewritten below, and new tasks are added for the window and the index.

## Tasks

- [x] 1. Update test fakes and package scaffold
  - [x] 1.1 Create the export package and the S3 fake
    - Add a `FakeS3` class whose `put_object(Bucket, Key, Body, ContentType)` stores bytes keyed by `(Bucket, Key)` and records each call. Add `s3` and `bucket_name` fixtures.
    - Create `src/export/__init__.py` and `tests/export/` (follow the `tests/api/` convention for `__init__.py`).
    - Leave existing fakes and fixtures unchanged. Reuse `closed_ticket` and `open_ticket`.
    - _Requirements: 4.1_

  - [x] 1.2 Replace `FakeTable.scan` with an index-aware `FakeTable.query`
    - Remove the `scan` method added for the earlier design. The fake must have no `scan`, so any scan in the export code fails the tests.
    - Add `FakeTable.query(**kwargs)`: require `IndexName`, read `:closed`, `:start` and `:end` from `ExpressionAttributeValues`, and return items whose `status` equals `:closed` and whose `closedAt` is between `:start` and `:end` inclusive, sorted by `closedAt`. Skip items with no `closedAt`, as a real sparse index does.
    - Honor `ExclusiveStartKey`, and return `LastEvaluatedKey` according to a `page_size` attribute (default unlimited).
    - Leave the other existing methods unchanged.
    - _Requirements: 2.1, 2.2_

- [x] 2. Implement the export handler
  - [x] 2.1 Update `src/export/nightly_export.py` to query the index within the Export_Window
    - Keep `COLUMNS`, `EXPORT_PREFIX`, `export_key`, `utc_run_date`, `build_csv`, and the S3 upload as they are.
    - Add `INDEX_NAME = "helpdesk-tickets-status-closedat"`.
    - Add `export_window(run_date)`, returning the start and end of the UTC day before `run_date` as `YYYY-MM-DDT00:00:00Z` and `YYYY-MM-DDT23:59:59Z`.
    - Replace `scan_closed_tickets` with `query_closed_tickets(table, window_start, window_end)`. It calls `table.query` with `IndexName`, `KeyConditionExpression` `#s = :closed AND #c BETWEEN :start AND :end`, names `#s` = `status` and `#c` = `closedAt`, and follows `LastEvaluatedKey` until it is absent. It uses no `FilterExpression`. Remove every `Scan` call and import.
    - `run_export` computes the window from `run_date`, queries, builds the CSV only after the query completes, and calls `s3.put_object` once with the key `ticket-exports/closed-tickets-<run_date>.csv` (the Run_Date, not the window date). It still writes a header-only file when nothing matches and lets exceptions propagate.
    - `handler` reads `TABLE_NAME`, `INDEX_NAME` and `BUCKET_NAME` from the environment and passes the index name through. It keeps importing `boto3` inside the function. Do not import from `src/api/`.
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 6.1_

  - [x] 2.2 Rewrite the parametrized test for ticket selection
    - File: `tests/export/test_export_selects_closed.py`
    - **Property 1: Export contains exactly the tickets closed in the Export_Window**
    - Use a fixed Run_Date of `2026-11-11` (window `2026-11-10T00:00:00Z` to `2026-11-10T23:59:59Z`). Parametrize over page size (unlimited, 1, 2, 3, larger than the table) and ticket mix (all closed in the window, none closed, one of each status, closed in the window mixed with closed earlier).
    - Add boundary cases: closedAt exactly `2026-11-10T00:00:00Z` (included), exactly `2026-11-10T23:59:59Z` (included), `2026-11-09T23:59:59Z` (excluded), and `2026-11-11T00:00:00Z` (excluded).
    - Assert the exported ticketIds equal the expected ids, each once.
    - Tag with `# Feature: nightly-ticket-export, Property 1: Export contains exactly the tickets closed in the Export_Window`.
    - **Validates: Requirements 2.1, 2.2**

  - [x] 2.3 Write parametrized test for CSV format
    - File: `tests/export/test_export_csv_format.py`
    - **Property 2: CSV round trip with header**
    - Parametrize over ticket lists: empty, one plain ticket, several tickets, requester containing a comma, a double quote, a bare LF, a CRLF, and a combination of these, leading or trailing spaces, an empty requester, non-ASCII text, and a missing attribute. Parse the output with `csv.reader`. Assert the first row is the header and the remaining rows equal the tickets' values in column order. Also assert that lines end with CRLF.
    - Tag with `# Feature: nightly-ticket-export, Property 2: CSV round trip with header`.
    - **Validates: Requirements 3.1, 3.2, 6.1**

  - [x] 2.4 Write parametrized test for destination key
    - File: `tests/export/test_export_destination.py`
    - **Property 3: Destination key follows the Run_Date**
    - Parametrize over run dates (typical, 2026-01-01, 2026-12-31, 2028-02-29, 2026-03-04) and ticket sets (empty, non-empty). Assert exactly one `put_object` call, to the configured bucket, with key `ticket-exports/closed-tickets-<date>.csv`, and that the key starts with `ticket-exports/`.
    - Add an overwrite example: two runs with the same date leave one stored object holding the latest content.
    - Tag with `# Feature: nightly-ticket-export, Property 3: Destination key follows the Run_Date`.
    - **Validates: Requirements 4.1, 4.2**

  - [x] 2.5 Write unit tests for empty day and run date
    - Files: `tests/export/test_export_empty_day.py`, `tests/export/test_export_run_date.py`
    - Empty day: with no closed tickets, the body equals the header line and `put_object` was still called.
    - Run date: `utc_run_date` returns `YYYY-MM-DD` for a fixed UTC clock, including a case near midnight UTC.
    - _Requirements: 4.1, 6.1_

  - [x] 2.6 Write unit tests for the Export_Window
    - File: `tests/export/test_export_window.py`
    - `export_window("2026-11-11")` returns `2026-11-10T00:00:00Z` and `2026-11-10T23:59:59Z`.
    - Cover month, year and leap-day rollovers: `2026-03-01`, `2027-01-01`, `2028-03-01`.
    - _Requirements: 2.1, 2.2_

  - [x] 2.7 Write unit test for query pagination
    - File: `tests/export/test_export_follows_pagination.py`
    - With a page size of 1 and several tickets closed in the window, assert every ticket is exported, so the query loop follows `LastEvaluatedKey` to the end.
    - Assert the export code never calls `scan` (the fake has none, so a scan would raise).
    - _Requirements: 2.1_

- [x] 3. Checkpoint - Ensure all tests pass
  - Run `.venv/bin/python -m pytest -q`. Ensure all tests pass, ask the user if questions arise.

- [x] 4. Add infrastructure and wire it in
  - [x] 4.1 Add the index and update `infra/nightly_export.py`
    - In `infra/helpdesk_stack.py`, right after the table is created, add the global secondary index with `add_global_secondary_index`: `index_name="helpdesk-tickets-status-closedat"`, partition key `status` (string), sort key `closedAt` (string), `ProjectionType.INCLUDE` with `non_key_attributes=["requester", "priority", "createdAt"]`. Leave the table key schema and the existing resources unchanged. Keep the index name in one shared constant used by the table, the policy, and the `INDEX_NAME` environment variable.
    - In the `NightlyExport` construct, replace the `dynamodb:Scan` statement with `dynamodb:Query` on the index ARN only (`<table_arn>/index/helpdesk-tickets-status-closedat`), with no permission on the table ARN itself.
    - Add `INDEX_NAME` to the function environment next to `TABLE_NAME` and `BUCKET_NAME`.
    - Keep everything else as built: the role `helpdesk-nightly-export-role` with no managed policies, the `s3:PutObject` statement on `ticket-exports/*`, the log statement scoped to the function's own log group, the log group `/aws/lambda/helpdesk-nightly-export` with 30-day retention, the function settings, and the rule `helpdesk-nightly-export-schedule` at `cron(0 6 * * ? *)`.
    - No `Resource: "*"`. Do not use `table.grant_read_data`.
    - _Requirements: 1.1, 1.2, 2.1, 5.1, 5.2_

  - [x] 4.2 Instantiate the construct in `infra/helpdesk_stack.py`
    - After the table is created, add `NightlyExport(self, "NightlyExport", table=self.table, finance_bucket_name=finance_bucket_name)`. Leave the existing resources unchanged. The construct call itself is unchanged by the revision.
    - _Requirements: 1.1, 5.1, 5.2_

  - [x] 4.3 Update CDK template assertion tests
    - File: `tests/export/test_export_infra.py`
    - Keep the checks that still hold: the rule `helpdesk-nightly-export-schedule` has `ScheduleExpression` `cron(0 6 * * ? *)` and targets the function; the function and role names; `s3:PutObject` on `.../ticket-exports/*`; the scoped log statement; no `Resource: "*"`; no S3 action other than `PutObject`.
    - Replace the `dynamodb:Scan` assertion with: the table has the global secondary index `helpdesk-tickets-status-closedat` with key schema `status` (HASH) and `closedAt` (RANGE), and the table key schema is unchanged.
    - Assert the role policy has `dynamodb:Query` on the index ARN only, and has no `dynamodb:Scan` and no write action on the table.
    - Add: the log group `/aws/lambda/helpdesk-nightly-export` has `RetentionInDays` 30, and the function environment has `INDEX_NAME`.
    - Use only `aws_cdk.assertions` (part of CDK, not a new dependency).
    - _Requirements: 1.1, 1.2, 2.1, 5.1, 5.2_

  - [x] 4.4 Verify synthesis
    - Run `cdk synth` and confirm both stacks synthesize, with the new index on the table and the updated policy. Do not run `cdk deploy`.
    - _Requirements: 1.1, 2.1, 5.1, 5.2_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Run `.venv/bin/python -m pytest -q`. Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Each task references specific requirements for traceability.
- Properties 1 to 3 are verified with plain parametrized pytest over hand-written cases, with no generated inputs and no new dependencies.
- `src/api/` is not modified. Changes to `tests/conftest.py` are additive, except that the earlier `FakeTable.scan` is replaced by `FakeTable.query`.
- The index is added to an existing table, so the stack update backfills it for existing closed tickets. The first scheduled run is hours after a deploy.
- The Finance bucket must exist before the first scheduled run. The construct only receives its name, so CDK adds no cross-stack dependency.
- Deployment is done by a human with `cdk deploy --all`.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "2.6", "2.7", "4.3"] },
    { "id": 3, "tasks": ["4.4"] }
  ]
}
```
