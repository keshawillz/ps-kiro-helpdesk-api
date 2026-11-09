"""GET /tickets/{ticketId}"""
from api import common


def handler(event, context):
    ticket_id = common.path_param(event, "ticketId")
    if not ticket_id:
        return common.error(400, "ticketId is required")

    ticket = common.get_store().get(ticket_id)
    if ticket is None:
        return common.error(404, f"Ticket {ticket_id} not found")
    return common.response(200, ticket)
