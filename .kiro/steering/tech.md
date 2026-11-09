# Tech

## Stack

- Python 3.12 for all Lambda code. Standard library plus boto3 only; ask
  before adding any third-party dependency.
- AWS CDK v2 in Python for all infrastructure. Two stacks: HelpdeskApiStack
  (table, handlers, API) and HelpdeskFinanceBucketStack (the Finance bucket).
- pytest for tests. Tests never call AWS; they use the in-memory fakes in
  tests/conftest.py.
- Lambda assets are built from the src/ directory. Handler strings are
  module paths under src, for example api.create_ticket.handler.

## AWS resources

- DynamoDB table helpdesk-tickets. Partition key ticketId (string). On-demand
  billing. Timestamps are ISO 8601 UTC strings with a Z suffix and second
  precision, so string comparison is time comparison.
- Finance exports bucket: helpdesk-finance-exports-<account-id>, owned by
  Finance, created by HelpdeskFinanceBucketStack. Exports write under the
  ticket-exports/ prefix only.

## Conventions

- Set explicit physical names on Lambda functions, IAM roles, and EventBridge
  rules using the helpdesk- prefix (for example helpdesk-api-create-ticket).
  Predictable names make deployed state easy to verify from the CLI.
- IAM policies name specific resource ARNs. No Resource "*" unless the action
  requires it.
- Scheduled rules use EventBridge cron expressions in UTC.
- Read-only code paths (exports, reports) get read permissions only.

## Commands

- Python: use .venv/bin/python. There is no `python` on PATH; the venv lives at .venv.
- Tests: .venv/bin/python -m pytest -q
- Synthesize: cdk synth (cdk.json already pins the venv and the AWS profile)
- Deploy (run by a human, never by the agent): cdk deploy --all
