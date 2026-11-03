# Slice Queue — local event-driven pizza orders

Full local web app. No Google Cloud, no cost.

## Run (PyCharm or terminal)

```bash
cd pizza_orders_app
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## What you can do
1. Fill customer + choose pizzas → Publish to queue
2. Click Process queue → orders saved (local Firestore)
3. Check "invalid message" → retries → Dead letter
4. See event log

## Later (free-tier GCP)
Same idea: browser/API publishes to Pub/Sub topic `orders`,
Cloud Function runs processor logic, Firestore stores documents.
