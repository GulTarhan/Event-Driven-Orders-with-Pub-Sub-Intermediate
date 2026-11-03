import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from processor import MENU, calc_total
from queue_sim import LocalQueue
from storage import list_orders, list_dlq, list_events, reset_all, get_order

app = Flask(__name__)
app.secret_key = "slice-queue-local-dev"
queue = LocalQueue()

DEALS = [
    {"title": "Large Pepperoni", "price": 11.99, "old": 14.00, "tag": "Limited"},
    {"title": "2 Medium + Drinks", "price": 22.50, "old": 28.00, "tag": "Combo"},
    {"title": "Family Feast", "price": 34.99, "old": 42.00, "tag": "Best value"},
]

LOCATIONS = [
    {"name": "Downtown", "addr": "120 Market Street", "phone": "555-0101", "hours": "10:00 – 23:00"},
    {"name": "Campus", "addr": "45 University Ave", "phone": "555-0144", "hours": "11:00 – 01:00"},
    {"name": "Westside", "addr": "9 Harbor Blvd", "phone": "555-0190", "hours": "10:30 – 22:30"},
]


def cart():
    return session.setdefault("cart", {})


def cart_items():
    c = cart()
    items = []
    total = 0.0
    for key, qty in c.items():
        if key in MENU and qty > 0:
            price = MENU[key]["price"]
            line = round(price * qty, 2)
            items.append({"id": key, "name": MENU[key]["name"], "qty": qty, "unitPrice": price, "lineTotal": line})
            total += line
    return items, round(total, 2)


@app.context_processor
def inject_globals():
    items, total = cart_items()
    return {
        "cart_count": sum(i["qty"] for i in items),
        "cart_total": total,
        "pending_count": len(queue.pending),
        "orders_count": len(list_orders()),
    }


@app.route("/")
def home():
    featured = list(MENU.items())[:4]
    return render_template("home.html", featured=featured, deals=DEALS)


@app.route("/menu")
def menu_page():
    return render_template("menu.html", menu=MENU)


@app.route("/cart")
def cart_page():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add", methods=["POST"])
def cart_add():
    key = request.form.get("id")
    try:
        qty = int(request.form.get("qty") or 1)
    except ValueError:
        qty = 1
    if key in MENU and qty > 0:
        c = cart()
        c[key] = min(20, c.get(key, 0) + qty)
        session["cart"] = c
        flash(f"Added {MENU[key]['name']} to cart.", "ok")
    return redirect(request.referrer or url_for("menu_page"))


@app.route("/cart/update", methods=["POST"])
def cart_update():
    c = {}
    for key in MENU:
        try:
            qty = int(request.form.get(f"qty_{key}") or 0)
        except ValueError:
            qty = 0
        if qty > 0:
            c[key] = min(20, qty)
    session["cart"] = c
    flash("Cart updated.", "ok")
    return redirect(url_for("cart_page"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_items()
    if request.method == "GET":
        return render_template("checkout.html", items=items, total=total)

    if not items:
        flash("Your cart is empty.", "warn")
        return redirect(url_for("menu_page"))

    customer = (request.form.get("customerName") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    address = (request.form.get("address") or "").strip()
    force_bad = request.form.get("forceBad") == "on"

    if force_bad:
        queue.publish({"customerName": customer or "Unknown", "items": items, "phone": phone, "address": address})
        session["cart"] = {}
        flash("Invalid message published (no orderId). Open Kitchen to process → DLQ.", "warn")
        return redirect(url_for("kitchen"))

    if not customer:
        flash("Name is required.", "warn")
        return redirect(url_for("checkout"))

    order_id = "ord-" + uuid.uuid4().hex[:8]
    msg = {
        "orderId": order_id,
        "customerName": customer,
        "phone": phone,
        "address": address,
        "items": items,
        "total": total,
    }
    queue.publish(msg)
    session["cart"] = {}
    flash(f"Order {order_id} sent to the kitchen queue (${total:.2f}).", "ok")
    return redirect(url_for("kitchen"))


@app.route("/kitchen", methods=["GET", "POST"])
def kitchen():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "process":
            results = queue.process_all()
            saved = sum(1 for r in results if r and r.get("status") == "saved")
            skipped = sum(1 for r in results if r and r.get("status") == "skipped")
            dlq = sum(1 for r in results if r and r.get("status") == "dlq")
            flash(f"Queue processed · saved={saved} skipped={skipped} dlq={dlq}", "ok")
        elif action == "reset":
            reset_all()
            queue.pending.clear()
            flash("Local kitchen data cleared.", "ok")
        return redirect(url_for("kitchen"))

    return render_template(
        "kitchen.html",
        orders=list_orders(),
        dlq=list_dlq(),
        events=list_events()[:25],
        pending=len(queue.pending),
    )


@app.route("/track", methods=["GET", "POST"])
def track():
    order = None
    q = (request.values.get("orderId") or "").strip()
    if q:
        order = get_order(q)
    return render_template("track.html", order=order, query=q)


@app.route("/locations")
def locations():
    return render_template("locations.html", locations=LOCATIONS)


@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, port=5000)