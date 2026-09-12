import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator

data = load_all_data()
sim = CashFlowSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_05"][0]
balances, min_proj, min_bal = sim.simulate_balance(req["user_id"], req["request_date"])

print("User 05 simulation:")
print(f"Start balance: {data['profiles']['user_05']['current_available_balance']}, min_bal: {min_bal}")
print(f"min_proj: {min_proj}, min_proj - min_bal: {min_proj - min_bal}")
print("Daily flow:")
daily_flow = sim.forecast_user_cashflow(req["user_id"], req["request_date"])
for d, flow in sorted(daily_flow.items()):
    print(f"  {d}: {flow}")
