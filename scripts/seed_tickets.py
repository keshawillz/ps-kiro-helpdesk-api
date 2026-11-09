#!/usr/bin/env python3
"""Seed the helpdesk-tickets table with realistic data for the course.

Default counts match the Pluralsight runbooks:
  204 CLOSED tickets spread over the previous 90 days (not yesterday)
    8 CLOSED tickets closed in the previous UTC calendar day
   30 OPEN or IN_PROGRESS tickets
    0 CLOSED tickets closed earlier today (set --today to add some; they prove
      requirement 2.2 against real data, and they change the 212 count)

Run it the same UTC day you run the export, or the "yesterday" bucket will
be wrong. --reset deletes everything in the table first.

Usage:
  python scripts/seed_tickets.py --reset
  python scripts/seed_tickets.py --reset --today 4
"""
import argparse
import random
from datetime import datetime, timedelta, timezone

import boto3

REQUESTERS = [
    "Ada Lovelace", "Grace Hopper", "Katherine Johnson", "Mary Jackson",
    "Dorothy Vaughan", "Annie Easley", "Evelyn Boyd Granville", "Marsha Rhea Williams",
    "Hedy Lamarr", "Radia Perlman", "Smith, Jordan", "Okafor, Chidi",  # two with commas
]
SUBJECTS = [
    "VPN drops every hour", "Badge reader offline", "Laptop will not boot",
    "Need access to finance share", "Printer on 4 jammed", "MFA reset",
    "Email stuck in outbox", "Monitor flickers", "Wi-Fi weak in east wing",
    "Password expired early", "Zoom audio echo", "New hire account setup",
]
PRIORITIES = ["P1", "P2", "P2", "P3", "P3", "P3", "P4"]
ASSIGNEES = ["ops-team", "desktop-support", "network-team", None]


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def random_time_on(day: datetime, rng: random.Random) -> datetime:
    return day.replace(hour=rng.randint(0, 23), minute=rng.randint(0, 59), second=rng.randint(0, 59))


def make_ticket(n: int, rng: random.Random, created: datetime, closed: datetime | None, status: str) -> dict:
    item = {
        "ticketId": f"T-{n:06d}",
        "status": status,
        "requester": rng.choice(REQUESTERS),
        "subject": rng.choice(SUBJECTS),
        "priority": rng.choice(PRIORITIES),
        "createdAt": iso(created),
    }
    assignee = rng.choice(ASSIGNEES)
    if assignee:
        item["assignee"] = assignee
    if closed is not None:
        item["closedAt"] = iso(closed)
    return item


def build(args) -> list[dict]:
    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    items: list[dict] = []
    n = 1

    # Older closed tickets: closed 2 to 90 days ago.
    for _ in range(args.older):
        closed_day = today - timedelta(days=rng.randint(2, 90))
        closed = random_time_on(closed_day, rng)
        created = closed - timedelta(hours=rng.randint(1, 72))
        items.append(make_ticket(n, rng, created, closed, "CLOSED")); n += 1

    # Yesterday's closed tickets. Pin two to the edges so the window test has
    # something real to find: one at 00:00:00 and one at 23:59:59.
    for i in range(args.yesterday):
        if i == 0:
            closed = yesterday
        elif i == 1:
            closed = yesterday.replace(hour=23, minute=59, second=59)
        else:
            closed = random_time_on(yesterday, rng)
        created = closed - timedelta(hours=rng.randint(1, 48))
        items.append(make_ticket(n, rng, created, closed, "CLOSED")); n += 1

    # Closed earlier today (outside yesterday's window). First one at exactly midnight.
    for i in range(args.today):
        closed = today if i == 0 else today + timedelta(seconds=rng.randint(1, max(1, int((now - today).total_seconds()) - 1)))
        created = closed - timedelta(hours=rng.randint(1, 48))
        items.append(make_ticket(n, rng, created, closed, "CLOSED")); n += 1

    # Open tickets.
    for _ in range(args.open):
        created = random_time_on(today - timedelta(days=rng.randint(0, 14)), rng)
        status = rng.choice(["OPEN", "OPEN", "IN_PROGRESS"])
        items.append(make_ticket(n, rng, created, None, status)); n += 1

    return items


def reset(table) -> int:
    deleted = 0
    scan = table.scan(ProjectionExpression="ticketId")
    while True:
        with table.batch_writer() as batch:
            for item in scan.get("Items", []):
                batch.delete_item(Key={"ticketId": item["ticketId"]})
                deleted += 1
        if "LastEvaluatedKey" not in scan:
            break
        scan = table.scan(ProjectionExpression="ticketId", ExclusiveStartKey=scan["LastEvaluatedKey"])
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", default="helpdesk-tickets")
    parser.add_argument("--older", type=int, default=204)
    parser.add_argument("--yesterday", type=int, default=8)
    parser.add_argument("--today", type=int, default=0)
    parser.add_argument("--open", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="delete every item first")
    parser.add_argument("--dry-run", action="store_true", help="print counts, write nothing")
    args = parser.parse_args()

    items = build(args)
    closed = sum(1 for i in items if i["status"] == "CLOSED")
    print(f"Prepared {len(items)} tickets: {closed} CLOSED "
          f"({args.older} older, {args.yesterday} yesterday, {args.today} today), {args.open} open.")
    if args.dry_run:
        return

    table = boto3.resource("dynamodb").Table(args.table)
    if args.reset:
        print(f"Deleted {reset(table)} existing items.")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"Wrote {len(items)} items to {args.table}.")
    print("Expected first export (no window): "
          f"{closed} rows. Expected after the fix: {args.yesterday} rows.")


if __name__ == "__main__":
    main()
