"""PATCH /tickets/{ticketId}

Updates priority, assignee, subject, or status (OPEN or IN_PROGRESS only).
Closing a ticket goes through POST /tickets/{ticketId}/close so that closedAt
is always stamped in one place.
"""
from api import common

ALLOWED_FIELDS = ("priority", "assignee", "subject", "status")


def handler(event, context):
    ticket_id = common.path_param(event, "ticketId")
    if not ticket_id:
        return common.error(400, "ticketId is required")

    body = common.parse_body(event)
    if body is None:
        return common.error(400, "Request body must be a JSON object")

    fields = {k: v for k, v in body.items() if k in ALLOWED_FIELDS}
    if not fields:
        return common.error(400, f"Provide at least one of {', '.join(ALLOWED_FIELDS)}")

    if "priority" in fields and fields["priority"] not in common.PRIORITIES:
        return common.error(400, f"priority must be one of {', '.join(common.PRIORITIES)}")
    if "status" in fields and fields["status"] not in common.OPEN_STATUSES:
        return common.error(
            400, "status must be OPEN or IN_PROGRESS; use the close endpoint to close a ticket"
        )

    store = common.get_store()
    existing = store.get(ticket_id)
    if existing is None:
        return common.error(404, f"Ticket {ticket_id} not found")
    if existing.get("status") == common.CLOSED:
        return common.error(409, f"Ticket {ticket_id} is closed and cannot be updated")

    updated = store.update(ticket_id, fields)
    return common.response(200, updated)
