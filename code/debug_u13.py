import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)

# Check user_13
req13 = [r for r in data["sample_requests"] if r["request_id"] == "request_13"][0]
balances, min_proj, min_bal = sim.simulate_balance("user_13", req13["request_date"])
flow13 = sim.forecast_user_cashflow("user_13", req13["request_date"])
print("User 13 flow:")
for d in sorted(flow13.keys()):
    if flow13[d] > 0:
        print(f"  Credit {d}: {flow13[d]}")
    if str(d) <= "2024-03-16":
        print(f"  Day {d}: flow={flow13[d]}, bal={balances.get(d)}")
