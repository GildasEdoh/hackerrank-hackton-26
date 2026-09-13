"""Test savings addition in spending changes."""
import os, sys, statistics, math
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from decision_engine import DecisionEngine

data = load_all_data()
sim = CashFlowSimulator(data)
engine = DecisionEngine(data)

# Let's inspect request_06
req = [r for r in data["sample_requests"] if r["request_id"] == "request_06"][0]
user_id = req["user_id"]
req_date_str = req["request_date"]
req_amount = float(req["requested_amount"])
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])

balances, min_proj, _ = sim.simulate_balance(user_id, req_date_str)
base_safe = max(0.0, min_proj - min_bal)
print(f"req_06 base_safe={base_safe}, req_amount={req_amount}, diff={req_amount - base_safe}")

# event_476 saving = 19.0 EUR
print(f"base_safe + 19 = {base_safe + 19.0}")
print(f"Is base_safe + 19 >= 565.63 + 19 = 584.63?")
