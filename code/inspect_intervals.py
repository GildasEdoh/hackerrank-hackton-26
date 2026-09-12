import os, sys
import statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date

data = load_all_data()

for user_id in ["user_01", "user_04", "user_06", "user_08", "user_11", "user_13", "user_21"]:
    u_events = [e for e in data["events"] if e["user_id"] == user_id and e["amount"] and e["status"] in ("settled", "pending", "scheduled")]
    print(f"\nUser {user_id}:")
    cats = set(e["category"] for e in u_events if e["direction"] == "debit")
    for cat in cats:
        evs = [e for e in u_events if e["category"] == cat]
        dates = sorted(set(parse_date(e["settlement_date"]) for e in evs))
        if len(dates) >= 3:
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            med = statistics.median(diffs)
            print(f"  {cat}: count={len(evs)}, median_interval={med:.1f} days, avg_amt={statistics.mean([float(e['amount']) for e in evs]):.2f}")
