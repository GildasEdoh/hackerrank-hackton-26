import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_06"][0]
user_id = req["user_id"]
req_date_str = req["request_date"]
req_amount = float(req["requested_amount"])
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])

# Candidate 5 logic:
actions = ["stop:event_476"]
b_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, actions)
safe_sc = min(req_amount, max(0.0, min_sc - min_bal))
print(f"actions={actions}, min_sc={min_sc}, min_bal={min_bal}, min_sc - min_bal = {min_sc - min_bal}, safe_sc={safe_sc}, req_amount={req_amount}")
print(f"safe_sc >= req_amount? {safe_sc >= req_amount}")
