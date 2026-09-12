import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator

data = load_all_data()
sim = CashFlowSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_11"][0]
balances, min_proj, min_bal = sim.simulate_balance(req["user_id"], req["request_date"])

print("User 11 events around May-July 2025:")
u_events = [e for e in data["events"] if e["user_id"] == "user_11"]
for e in u_events:
    if "2025-04" <= e["settlement_date"] <= "2025-07":
        print(f"  {e['event_id']} {e['settlement_date']} {e['category']} {e['direction']} {e['amount']} {e['status']} {e['description']}")

print(f"\nUser 11 starting balance: {data['profiles']['user_11']['current_available_balance']}, min_bal={min_bal}")
daily_flow = sim.forecast_user_cashflow(req["user_id"], req["request_date"])
for d, flow in sorted(daily_flow.items()):
    if flow > 0:
        print(f"  Credit {d}: {flow}")
