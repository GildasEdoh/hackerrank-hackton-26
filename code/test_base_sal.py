import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()

# Let's test filtering base salary
for s in data["sample_requests"]:
    user_id = s["user_id"]
    u_events = [e for e in data["events"] if e["user_id"] == user_id]
    past_valid = [e for e in u_events if e["settlement_date"] < s["request_date"] and e["amount"] and e["status"] in ("settled", "pending", "scheduled")]
    
    base_salaries = [e for e in past_valid if e["category"] == "salary" and e["direction"] == "credit" and not any(w in e["description"].lower() for w in ("bonus", "commission", "incentive", "overtime", "refund", "gain", "dividend", "lottery", "one-off"))]
    all_salaries = [e for e in past_valid if e["category"] == "salary" and e["direction"] == "credit"]
    
    if len(base_salaries) != len(all_salaries):
        print(f"{s['request_id']} ({user_id}): filtered {len(all_salaries) - len(base_salaries)} non-base salary events.")
        for e in all_salaries:
            if e not in base_salaries:
                print(f"   Excluded: {e['settlement_date']} {e['description']} {e['amount']}")
