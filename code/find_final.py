import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()
for e in data["events"]:
    desc = e["description"].lower()
    if "final" in desc or "last" in desc or "severance" in desc or "termination" in desc:
        print(f"User {e['user_id']}: {e['event_id']} {e['settlement_date']} {e['category']} {e['description']}")
