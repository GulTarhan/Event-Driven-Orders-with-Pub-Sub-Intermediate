import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
ORDERS_FILE = DATA_DIR / "orders.json"
DLQ_FILE = DATA_DIR / "dead_letter.json"
LOG_FILE = DATA_DIR / "events.json"


def _read(path):
    if not path.exists() or path.stat().st_size == 0:
        return [] if "dead" in path.name or "events" in path.name else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return [] if "dead" in path.name or "events" in path.name else {}


def _write(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get_order(order_id):
    return _read(ORDERS_FILE).get(order_id)


def save_order(order_id, order):
    data = _read(ORDERS_FILE)
    if order_id in data:
        return False
    data[order_id] = order
    _write(ORDERS_FILE, data)
    return True


def list_orders():
    data = _read(ORDERS_FILE)
    # newest first
    return dict(sorted(data.items(), key=lambda x: x[1].get("processedAt", ""), reverse=True))


def add_dlq(item):
    rows = _read(DLQ_FILE)
    if not isinstance(rows, list):
        rows = []
    rows.append(item)
    _write(DLQ_FILE, rows)


def list_dlq():
    rows = _read(DLQ_FILE)
    return rows if isinstance(rows, list) else []


def log_event(event):
    rows = _read(LOG_FILE)
    if not isinstance(rows, list):
        rows = []
    rows.append(event)
    _write(LOG_FILE, rows[-100:])  # keep last 100


def list_events():
    rows = _read(LOG_FILE)
    return list(reversed(rows if isinstance(rows, list) else []))


def reset_all():
    _write(ORDERS_FILE, {})
    _write(DLQ_FILE, [])
    _write(LOG_FILE, [])
