Slice Queue — local event-driven pizza orders
Full local web app. No Google Cloud, no cost.

Run (PyCharm or terminal)
cd pizza_orders_app
pip install -r requirements.txt
python app.py
Open http://127.0.0.1:5000

What you can do
Fill customer + choose pizzas → Publish to queue
Click Process queue → orders saved (local Firestore)
Check "invalid message" → retries → Dead letter
See event log
Later (free-tier GCP)
Same idea: browser/API publishes to Pub/Sub topic orders, Cloud Function runs processor logic, Firestore stores documents.
