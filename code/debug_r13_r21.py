"""Debug remaining misses: 13, 21."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from datetime import timedelta

data = load_all_data()
sim = CashFlowSimulator(data)

# --- request_13: user_13, 2024-03-07, amt=941.6 ---
print("=" * 60)
print("request_13: user_13, 2024-03-07, amt=941.6")
print("Expected: affordable_later, wait, earliest=2024-05-15, safe_pay=433.4")
user_id = "user_13"
req_date_str = "2024-03-07"
req_amount = 941.6
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])
balances, min_proj, _ = sim.simulate_balance(user_id, req_date_str)
req_d = parse_date(req_date_str)
print(f"  starting_bal={profile['current_available_balance']}")
print(f"  min_bal={min_bal} min_proj={min_proj:.2f}")
print(f"  safe_to_pay={max(0, min_proj-min_bal):.2f}")
print(f"  balance on request_date: {balances[req_d]:.2f}")
print(f"  Cond1 on Mar 7: {balances[req_d] - req_amount:.2f} >= {min_bal}: {balances[req_d] - req_amount >= min_bal}")
# Condition 2 check: all subsequent days >= min_bal
print("  Days with balance < min_bal:")
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    if balances[cd] < min_bal:
        print(f"    {cd}: bal={balances[cd]:.2f} < min={min_bal}")
print()
# Show key cashflows
daily = sim.forecast_user_cashflow(user_id, req_date_str)
print("  Key cashflows:")
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    f = daily.get(cd, 0)
    if abs(f) > 50:
        print(f"    {cd}: {f:.2f} -> bal={balances[cd]:.2f}")
print(f"  Messages: {data['messages_by_user'].get(user_id)}")

# --- request_21: user_21, 2026-04-03 ---
print()
print("=" * 60)
print("request_21: user_21, 2026-04-03, amt=1574.4")
print("Expected: affordable_with_plan, full_payment, stop:event_1815|reduce_to:event_1816:23.50")
print("Expected safe_pay=1543.35")
user_id = "user_21"
req_date_str = "2026-04-03"
req_amount = 1574.4
profile = data["profiles"][user_id]
min_bal = float(profile["minimum_balance_to_keep"])
balances, min_proj, _ = sim.simulate_balance(user_id, req_date_str)
req_d = parse_date(req_date_str)
print(f"  starting_bal={profile['current_available_balance']}")
print(f"  min_bal={min_bal} min_proj={min_proj:.2f}")
print(f"  safe_to_pay={max(0, min_proj-min_bal):.2f}")
print(f"  Profile: {profile}")

ev1815 = [e for e in data["events"] if e["event_id"] == "event_1815"]
ev1816 = [e for e in data["events"] if e["event_id"] == "event_1816"]
if ev1815: print(f"  event_1815: {ev1815[0]}")
if ev1816: print(f"  event_1816: {ev1816[0]}")

# Try the expected spending change
balances_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, ["stop:event_1815", "reduce_to:event_1816:23.50"])
safe_sc = max(0, min_sc - min_bal)
print(f"  With stop:event_1815|reduce_to:event_1816:23.50: safe_sc={safe_sc:.2f} req={req_amount}")
print(f"  Works: {safe_sc >= req_amount}")

# Check what spending change candidates our code finds
willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
willing_reduce = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_reduce", "").split("|") if c.strip())
print(f"  willing_stop: {willing_stop}")
print(f"  willing_reduce: {willing_reduce}")
past_evs = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]
stop_cands = [e for e in past_evs if e["category"] in willing_stop and e["flexibility"] in ("stoppable", "reducible_or_stoppable")]
reduce_cands = [e for e in past_evs if e["category"] in willing_reduce and e["flexibility"] in ("reducible", "reducible_or_stoppable") and e.get("minimum_allowed_amount")]
print(f"  Stop candidates: {len(stop_cands)}")
for e in stop_cands[-3:]:
    print(f"    {e['event_id']} {e['category']} {e['description'][:30]} flex={e['flexibility']}")
print(f"  Reduce candidates: {len(reduce_cands)}")
for e in reduce_cands[-3:]:
    print(f"    {e['event_id']} {e['category']} {e['description'][:30]} min={e['minimum_allowed_amount']}")
