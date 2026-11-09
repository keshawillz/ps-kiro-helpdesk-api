# Product

helpdesk-api is the internal support ticketing service. Employees raise
tickets for IT problems; the support team works and closes them.

## Who uses it

- Employees, through an internal web form that calls this API.
- The support team, through the same API from their dashboard.
- Finance, who read closed-ticket data to calculate SLA credits.

## What a ticket is

A ticket has a requester, a subject, a priority (P1 highest to P4 lowest),
an optional assignee, and a status: OPEN, IN_PROGRESS, or CLOSED. It is
stamped with createdAt when raised and closedAt when closed. closedAt is
written only by the close endpoint, so it is the trustworthy timestamp for
any reporting on closed tickets.

## Principles

- Small and boring. Prefer one Lambda to a workflow, one table to several.
- Least access. Every role gets the minimum it needs for its one job.
- Reports read from the table; they never change it.
