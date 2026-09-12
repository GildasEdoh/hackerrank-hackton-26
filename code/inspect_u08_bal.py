import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date
from test_dynamic import DynamicSimulator

data = load_all_data()
sim = DynamicSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_08"][0]
balances, min_proj, min_bal = sim.simulate_balance("user_08", req["request_date"])

print("User 08 profile:", data["profiles"]["user_08"])
print(f"req_amt: {req['requested_amount']}")
print(f"min_bal: {min_bal}")

print("\nBalances around 2025-04-15:")
for d_idx in range(60, 75):
    d = parse_date(req["request_date"]) + sys.modules["datetime"].timedelta(days=d_idx)
    print(f"  {d}: bal={balances.get(d, 0):.2f}, bal - req_amt = {balances.get(d, 0) - float(req['requested_amount']):.2f} vs min_bal={min_bal}")
