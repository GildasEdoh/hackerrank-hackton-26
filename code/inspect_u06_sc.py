import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator

data = load_all_data()
sim = CashFlowSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_06"][0]
user_id = req["user_id"]
req_date_str = req["request_date"]
req_amount = float(req["requested_amount"])
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])

print(f"User 06 profile: bal={profile['current_available_balance']}, min_bal={min_bal}")
print(f"Willing stop: {profile.get('expense_categories_user_is_willing_to_stop')}")

# Check event_476
e476 = [e for e in data["events"] if e["event_id"] == "event_476"][0]
print("event_476:", e476)

# Test simulation with stop:event_476
b_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, ["stop:event_476"])
print(f"With stop:event_476 -> min_sc = {min_sc}, min_bal = {min_bal}, min_sc - min_bal = {min_sc - min_bal}, req_amt = {req_amount}")
