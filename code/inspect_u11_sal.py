import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()
u11_salaries = [e for e in data["events"] if e["user_id"] == "user_11" and e["category"] == "salary"]
for s in u11_salaries:
    print(s["event_id"], s["settlement_date"], s["amount"], s["description"])
