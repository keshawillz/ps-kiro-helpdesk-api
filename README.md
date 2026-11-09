# helpdesk-api

A small internal ticketing service on AWS, used as the running example in the
Pluralsight course **Demo: Building a cloud change with Kiro**.

Four Lambda handlers behind API Gateway, one DynamoDB table, deployed with
AWS CDK in Python. The app is small on purpose. The course is about the
process of changing it with an agent, not about the app.

## Branches

| Branch | What it is |
|---|---|
| `main` | Starting state. Deploy this before you start Module 1. |
| `solution/nightly-export` | Finished state after Module 3. Diff it against `main` to see every change the course makes. |

## Follow along or watch

Both work. If you want to build the change yourself, deploy `main` to your own
AWS account using the steps below, then work through each clip in Kiro while
you watch. Your Kiro run will not match the video word for word: file names,
task numbers, and wording vary from run to run. What matters is that each
result matches its requirement. If you get stuck, diff your work against
`solution/nightly-export`.

## What you need

- Python 3.12
- Node.js 20 or later and the AWS CDK CLI (`npm install -g aws-cdk`)
- An AWS account you can deploy to. Use a sandbox, never production.
- An AWS CLI profile for that account. Any profile type works. The course
  uses one named `helpdesk-sandbox` backed by IAM Identity Center. If yours has
  a different name, change `"profile"` in `cdk.json` and substitute it wherever
  you see `helpdesk-sandbox`.
- Kiro IDE 1.x, signed in.
- Enough Kiro credits for a full run: about 45. In the author's run, Module 1
  used about 12, Module 2 about 31, and Module 3 under 2. The free tier's 50
  credits a month covers one clean run with little room for retries, so check
  the meter in Kiro's status bar before you start Module 2.

## Set up

```bash
git clone <your fork> helpdesk-api
cd helpdesk-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export AWS_PROFILE=helpdesk-sandbox
aws sts get-caller-identity          # confirm you are in the sandbox

# cdk.json pins the profile and the venv, so cdk commands work from any
# shell in this repo, including Kiro's.

cdk bootstrap                        # once per account/region
cdk deploy --all --require-approval never
```

`cdk deploy --all` creates two stacks:

- `HelpdeskApiStack`: the table, the four API handlers, and the REST API.
- `HelpdeskFinanceBucketStack`: the bucket Finance owns,
  `helpdesk-finance-exports-<account-id>`. It lives in its own stack because
  in the story it belongs to another team.

## Seed the table

Run this the morning you work through Module 2. The course counts (212
closed tickets, 8 of them closed yesterday) depend on the seed running
on the same UTC day you run the export.

```bash
python scripts/seed_tickets.py --reset
```

Flags: `--older 204` closed tickets spread over the previous 90 days,
`--yesterday 8` closed in the previous UTC day, `--open 30` still open,
`--today 0` closed earlier today. Change them if you want different numbers;
say your numbers on screen.

## Run the tests

```bash
pytest -q
```

22 tests on `main`. 31 on `solution/nightly-export`.

## Try the API

```bash
API=$(aws cloudformation describe-stacks --stack-name HelpdeskApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)

curl -s -X POST "$API/tickets" -d '{"requester":"Ada Lovelace","subject":"VPN drops","priority":"P2"}'
curl -s "$API/tickets/<ticketId>"
curl -s -X POST "$API/tickets/<ticketId>/close"
```

## Clean up

```bash
cdk destroy --all
```

The bucket is created with `auto_delete_objects=True` and the table with
`RemovalPolicy.DESTROY`, so `cdk destroy` removes everything. This is a
sandbox configuration. Do not copy it into a production stack.

## Cost

Everything here is pay per request or free tier: DynamoDB on demand, Lambda,
API Gateway, EventBridge, and a few kilobytes in S3. Working through the
course should cost well under a dollar. Destroy the stacks when you are done.

## Layout

```
infra/          CDK app (Python)
src/api/        Ticket API handlers
tests/          pytest suite
scripts/        seed_tickets.py
.kiro/steering  Foundation steering files Kiro loads in every session
CHANGE-REQUEST.md   The note from Finance that starts the course
```
