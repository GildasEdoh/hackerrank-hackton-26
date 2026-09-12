import os, sys
from itertools import combinations
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()
u04_events = [e for e in data["events"] if e["user_id"] == "user_04"]

amts = [(e["event_id"], e["category"], float(e["amount"]), e["description"]) for e in u04_events if e["amount"]]

for r in range(1, 6):
    for combo in combinations(amts, r):
        s = sum(x[2] for x in combo)
        if abs(s - 13118550) < 1:
            print("Match 13118550:", combo)
        if abs(s - 11414250) < 1:
            print("Match 11414250:", combo)
