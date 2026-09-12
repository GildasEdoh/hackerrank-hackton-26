"""Debug request_11 spending changes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date

data = load_all_data()
sim = CashFlowSimulator(data)

user_id = "user_11"
req_date_str = "2025-05-03"
req_amount = 13110000.0
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])

print("Profile:")
for k, v in profile.items():
    print(f"  {k}: {v}")
print()

# Check event_989
ev989 = [e for e in data["events"] if e["event_id"] == "event_989"]
if ev989:
    print("event_989:", ev989[0])
print()

# Try the expected spending change
balances_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, ["reduce_to:event_989:665950"])
safe_sc = max(0, min_sc - min_bal)
print(f"With reduce_to:event_989:665950: min_sc={min_sc:.2f} safe_sc={safe_sc:.2f} req={req_amount}")
print(f"Works: {safe_sc >= req_amount}")

# Base
balances_base, min_base, _ = sim.simulate_balance(user_id, req_date_str)
print(f"Base: min_base={min_base:.2f} safe={max(0, min_base-min_bal):.2f}")

# Past events for spending changes
past_evs = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]
willing_reduce = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_reduce", "").split("|") if c.strip())
willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
print(f"willing_reduce: {willing_reduce}")
print(f"willing_stop: {willing_stop}")

reduce_candidates = [e for e in past_evs if e["category"] in willing_reduce and e["flexibility"] in ("reducible", "reducible_or_stoppable") and e.get("minimum_allowed_amount")]
print(f"Reduce candidates ({len(reduce_candidates)}):")
for e in reduce_candidates[-5:]:
    print(f"  {e['event_id']} {e['settlement_date']} {e['category']} {e['amount']} -> min={e['minimum_allowed_amount']}")

# Check messages
print(f"Messages: {data['messages_by_user'].get(user_id)}")

# Show what the forecast looks like
from datetime import timedelta
req_d = parse_date(req_date_str)
daily_base = sim.forecast_user_cashflow(user_id, req_date_str)
daily_sc = sim.forecast_user_cashflow(user_id, req_date_str, ["reduce_to:event_989:665950"])
print("\nCashflow comparison (non-zero or different):")
from simulator import format_date
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    bf = daily_base.get(cd, 0)
    sf = daily_sc.get(cd, 0)
    if abs(bf) > 100000 or bf != sf:
        print(f"  {cd}: base={bf:.2f} sc={sf:.2f}")
