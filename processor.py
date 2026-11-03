from datetime import datetime, timezone
from storage import get_order, save_order, log_event


MENU = {
    "margherita": {"name": "Margherita", "price": 12.50},
    "pepperoni": {"name": "Pepperoni", "price": 14.00},
    "bbq_chicken": {"name": "BBQ Chicken", "price": 15.50},
    "veggie": {"name": "Veggie Supreme", "price": 13.75},
    "four_cheese": {"name": "Four Cheese", "price": 14.50},
    "hawaiian": {"name": "Hawaiian", "price": 13.25},
}


def calc_total(items):
    total = 0.0
    normalized = []
    for it in items or []:
        key = (it.get("id") or "").lower()
        qty = int(it.get("qty") or 0)
        if key not in MENU or qty < 1:
            continue
        unit = MENU[key]["price"]
        normalized.append({
            "id": key,
            "name": MENU[key]["name"],
            "qty": qty,
            "unitPrice": unit,
            "lineTotal": round(unit * qty, 2),
        })
        total += unit * qty
    return normalized, round(total, 2)


def process_order(message: dict) -> dict:
    if not isinstance(message, dict):
        raise ValueError("invalid message")

    order_id = str(message.get("orderId") or "").strip()
    if not order_id:
        raise ValueError("orderId is required")

    existing = get_order(order_id)
    if existing is not None:
        log_event({"type": "skip", "orderId": order_id, "at": datetime.now(timezone.utc).isoformat()})
        return {"status": "skipped", "orderId": order_id}

    items, total = calc_total(message.get("items"))
    if not items:
        raise ValueError("at least one valid menu item is required")

    doc = {
        "orderId": order_id,
        "customerName": (message.get("customerName") or "Guest").strip(),
        "phone": (message.get("phone") or "").strip(),
        "address": (message.get("address") or "").strip(),
        "items": items,
        "total": total,
        "status": "received",
        "processedAt": datetime.now(timezone.utc).isoformat(),
    }
    save_order(order_id, doc)
    log_event({"type": "saved", "orderId": order_id, "total": total, "at": doc["processedAt"]})
    return {"status": "saved", "orderId": order_id, "total": total}
