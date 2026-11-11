---
inclusion: always
---
# Boundary for the nightly-ticket-export change

- Work only inside infra/, src/export/, and tests/. Do not modify src/api/.
- Do not add third-party dependencies without asking first.
- Name every new AWS resource explicitly with the helpdesk- prefix.
- Read only from the helpdesk-tickets table. Write only to the
  ticket-exports/ prefix of the finance exports bucket.
- Do not run cdk deploy or any aws command. A human runs those.
- Verify infrastructure with cdk synth and the test suite. Do not write
  ad hoc Python scripts to inspect templates.
- Edit files with your file tools, not shell commands like cat, sed, or tee.
- Delete this file when the change is merged.