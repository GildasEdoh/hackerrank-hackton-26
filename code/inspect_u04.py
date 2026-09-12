"""Inspect user_04 balance trajectory."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)

req = [r for r in data["sample_requests"] if r["request_id"] == "request_04"][0]
balances, min_proj, min_bal = sim.simulate_balance(req["user_id"], req["request_date"])

print(f"Starting balance: {data['profiles'][req['user_id']]['current_available_balance']}, min_bal={min_bal}")
print(f"min_proj = {min_proj}, min_proj - min_bal = {min_proj - min_bal}")
print("Daily balances below 40,000,000:")
for d, b in balances.items():
    if b < 40000000:
        print(f"  {d}: {b}")
