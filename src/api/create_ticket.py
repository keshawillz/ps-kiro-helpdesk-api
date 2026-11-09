"""POST /tickets"""
import uuid

from api import common


def handler(event, context):
    body = common.parse_body(event)
    if body is None:
        return common.error(400, "Request body must be a JSON object")

    requester = (body.get("requester") or "").strip()
    subject = (body.get("subject") or "").strip()
    priority = body.get("priority", "P3")

    if not requester:
        return common.error(400, "requester is required")
    if not subject:
        return common.error(400, "subject is required")
    if priority not in common.PRIORITIES:
        return common.error(400, f"priority must be one of {', '.join(common.PRIORITIES)}")

    ticket = {
        "ticketId": f"T-{uuid.uuid4().hex[:8].upper()}",
        "status": "OPEN",
        "requester": requester,
        "subject": subject,
        "priority": priority,
        "createdAt": common.now_iso(),
    }
    common.get_store().put(ticket)
    return common.response(201, ticket)
