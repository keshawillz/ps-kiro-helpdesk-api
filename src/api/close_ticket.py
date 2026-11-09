"""POST /tickets/{ticketId}/close

Sets status to CLOSED and stamps closedAt. This is the only code path that
writes closedAt, which is what makes closedAt trustworthy for reporting.
"""
from api import common


def handler(event, context):
    ticket_id = common.path_param(event, "ticketId")
    if not ticket_id:
        return common.error(400, "ticketId is required")

    store = common.get_store()
    existing = store.get(ticket_id)
    if existing is None:
        return common.error(404, f"Ticket {ticket_id} not found")
    if existing.get("status") == common.CLOSED:
        return common.error(409, f"Ticket {ticket_id} is already closed")

    updated = store.update(
        ticket_id,
        {"status": common.CLOSED, "closedAt": common.now_iso()},
    )
    return common.response(200, updated)
