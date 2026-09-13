import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_06"][0]
balances, min_proj, min_bal = sim.simulate_balance(req["user_id"], req["request_date"], ["stop:event_476"])

print(f"User 06 with stop:event_476:")
print(f"Start balance: {data['profiles']['user_06']['current_available_balance']}")
print(f"min_bal: {min_bal}")
print(f"min_proj: {min_proj}, min_proj - min_bal: {min_proj - min_bal}")

for d, b in balances.items():
    if b < 1500:
        print(f"  {d}: bal={b:.2f}, bal - min_bal={b - min_bal:.2f}")
