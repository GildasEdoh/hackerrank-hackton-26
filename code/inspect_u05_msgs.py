import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()
u05_events = [e for e in data["events"] if e["user_id"] == "user_05"]
for e in u05_events:
    print(f"{e['event_id']} {e['settlement_date']} {e['event_type']} {e['category']} {e['direction']} {e['amount']} {e['status']} {e['description']}")

print("\nMessages for user_05:")
with open("dataset/messages.csv", "r", encoding="utf-8") as f:
    import csv
    for r in csv.DictReader(f):
        if r["user_id"] == "user_05":
            print(r)
