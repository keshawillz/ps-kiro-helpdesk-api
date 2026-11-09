"""Thin wrapper over the DynamoDB tickets table."""
from typing import Optional


class TicketStore:
    def __init__(self, table) -> None:
        self._table = table

    def get(self, ticket_id: str) -> Optional[dict]:
        result = self._table.get_item(Key={"ticketId": ticket_id})
        return result.get("Item")

    def put(self, item: dict) -> None:
        self._table.put_item(Item=item)

    def update(self, ticket_id: str, fields: dict) -> dict:
        """Set the given attributes and return the updated item."""
        names = {f"#{k}": k for k in fields}
        values = {f":{k}": v for k, v in fields.items()}
        expression = "SET " + ", ".join(f"#{k} = :{k}" for k in fields)
        result = self._table.update_item(
            Key={"ticketId": ticket_id},
            UpdateExpression=expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return result["Attributes"]
