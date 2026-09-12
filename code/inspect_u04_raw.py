import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()
u04_events = [e for e in data["events"] if e["user_id"] == "user_04"]
for e in u04_events:
    print(e)
print("\nMessages:")
print(data["messages_by_user"].get("user_04"))
