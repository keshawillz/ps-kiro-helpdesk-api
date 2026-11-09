# Structure

```
infra/                 CDK app
  app.py               Entry point; wires the two stacks
  helpdesk_stack.py    Table, API handlers, REST API
  finance_bucket_stack.py  The Finance-owned exports bucket
src/
  api/                 Ticket API handlers (one module per endpoint) + shared helpers
tests/
  conftest.py          In-memory FakeTable and fixtures
  api/                 One test module per handler
scripts/
  seed_tickets.py      Loads realistic ticket data into the table
.kiro/steering/        These files
CHANGE-REQUEST.md      The current request from Finance
```

## Where new code goes

- A new feature that is not part of the ticket API gets its own package
  under src/ (for example src/export/) and its own test folder under tests/.
- Infrastructure for a feature goes in its own construct file under infra/
  and is instantiated from helpdesk_stack.py.
- Do not modify src/api/ for features that do not change the ticket API.

## Naming

- Python modules and functions: snake_case.
- DynamoDB attributes and JSON fields: camelCase (ticketId, createdAt, closedAt).
- Tests: test_<behavior>.py with one assertion idea per test function.
