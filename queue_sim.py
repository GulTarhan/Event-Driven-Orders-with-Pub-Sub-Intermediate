from datetime import datetime, timezone
from processor import process_order
from storage import add_dlq, log_event

MAX_RETRIES = 3


class LocalQueue:
    def __init__(self):
        self.pending = []

    def publish(self, message: dict):
        self.pending.append({"body": message, "attempts": 0})
        log_event({
            "type": "published",
            "orderId": message.get("orderId"),
            "at": datetime.now(timezone.utc).isoformat(),
        })

    def process_one(self):
        if not self.pending:
            return None
        item = self.pending.pop(0)
        item["attempts"] += 1
        body = item["body"]
        try:
            result = process_order(body)
            return result
        except Exception as e:
            log_event({
                "type": "fail",
                "orderId": body.get("orderId"),
                "attempt": item["attempts"],
                "error": str(e),
                "at": datetime.now(timezone.utc).isoformat(),
            })
            if item["attempts"] < MAX_RETRIES:
                self.pending.append(item)
                return {"status": "retry", "attempt": item["attempts"], "error": str(e)}
            add_dlq({
                "body": body,
                "error": str(e),
                "attempts": item["attempts"],
                "failedAt": datetime.now(timezone.utc).isoformat(),
            })
            log_event({
                "type": "dlq",
                "orderId": body.get("orderId"),
                "error": str(e),
                "at": datetime.now(timezone.utc).isoformat(),
            })
            return {"status": "dlq", "error": str(e)}

    def process_all(self):
        results = []
        # bound loops: pending can grow only via retries of current set
        guard = 0
        while self.pending and guard < 50:
            results.append(self.process_one())
            guard += 1
        return results
