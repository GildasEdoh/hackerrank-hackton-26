import os, sys
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date
from test_dynamic import DynamicSimulator

data = load_all_data()
sim = DynamicSimulator(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_08"][0]
balances, min_proj, min_bal = sim.simulate_balance("user_08", req["request_date"])

req_amt = float(req["requested_amount"])
print("Days where bal - req_amt < min_bal after 2025-04-15:")
for d_idx in range(91):
    d = parse_date(req["request_date"]) + timedelta(days=d_idx)
    if d >= parse_date("2025-04-15"):
        diff = balances[d] - req_amt
        if diff < min_bal:
            print(f"  {d}: bal={balances[d]:.2f}, diff={diff:.2f} < {min_bal}")
