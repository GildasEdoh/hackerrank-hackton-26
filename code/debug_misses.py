"""Debug script for each miss category."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from collections import defaultdict
from datetime import timedelta

data = load_all_data()
sim = CashFlowSimulator(data)

# ---- CATEGORY 1: Installment checks too strict (request_02, 07, 12, 17) ----
# These get 'not_affordable' but should be 'affordable_with_plan' via installments.
# The installment check uses cumulative running_deduction logic.
# Expected plan for request_02: 2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67
# Let's see what the balance trajectory looks like for user_02

print("=" * 60)
print("DEBUG request_02: user_02, 2025-08-05")
user_id = "user_02"
req_date_str = "2025-08-05"
req_amount = 46018000.0
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
req_d = parse_date(req_date_str)

print(f"  Starting balance: {sim.profiles[user_id]['current_available_balance']}")
print(f"  min_bal = {min_bal}")
print(f"  min_proj = {min_proj:.2f}")
print(f"  safe_to_pay = {max(0, min_proj - min_bal):.2f} (expected 17229139.2)")
print()

# Print the cashflow day-by-day for first 100 days
print("  Cashflow day by day:")
for d_idx in range(0, 80, 1):
    cd = req_d + timedelta(days=d_idx)
    flow = sim.forecast_user_cashflow(user_id, req_date_str).get(cd, 0)
    if flow != 0 or d_idx < 5:
        print(f"    {cd}: flow={flow:.2f} bal={balances[cd]:.2f}")

# Check the installment option
opts = [o for o in data["payment_options"] if o["request_id"] == "request_02" and o["payment_method"] == "installments"]
for o in opts:
    num_p = int(o["number_of_payments"])
    freq = int(o["payment_frequency_days"] or 30)
    first_p = parse_date(o["first_payment_date"])
    p_dates = [first_p + timedelta(days=k * freq) for k in range(num_p)]
    p_amt = float(o["payment_amount"])
    print(f"\n  Installment option {o['payment_option_id']}: {num_p} x {p_amt} every {freq}d from {first_p}")
    print(f"  Payment dates: {[str(d) for d in p_dates]}")
    # simulate cumulative check
    running_deduct = defaultdict(float)
    for pd in p_dates:
        running_deduct[pd] += p_amt
    curr_deduct = 0.0
    for d_idx in range(91):
        cd = req_d + timedelta(days=d_idx)
        prev = curr_deduct
        curr_deduct += running_deduct.get(cd, 0.0)
        if curr_deduct != prev:
            print(f"    After deduct on {cd}: bal={balances[cd]:.2f} deduct={curr_deduct:.2f} bal_after={balances[cd]-curr_deduct:.2f} min={min_bal:.2f} OK={balances[cd]-curr_deduct >= min_bal}")

print()
print("=" * 60)
print("DEBUG request_05: user_05, 2025-11-06")
# Got: affordable_now, Expected: not_affordable
# Got safe_to_pay=15488 but expected 737
# This suggests the forecast is missing a big expense or has wrong income
user_id = "user_05"
req_date_str = "2025-11-06"
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = sim.profiles[user_id]
print(f"  Starting balance: {profile['current_available_balance']}")
print(f"  min_bal = {min_bal}")
print(f"  min_proj = {min_proj:.2f}")
print(f"  safe_to_pay = {max(0, min_proj - min_bal):.2f} (expected 737)")
req_d = parse_date(req_date_str)
# Print all cashflow
daily_flow = sim.forecast_user_cashflow(user_id, req_date_str)
print("  Key cashflows:")
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    f = daily_flow.get(cd, 0)
    if f != 0:
        print(f"    {cd}: {f:.2f}")

print()
# Check messages for user_05
print("  Messages for user_05:", data["messages_by_user"].get("user_05"))

# Look at future events in CSV for user_05 to see if there's a large debit
user05_events = [e for e in data["events"] if e["user_id"] == "user_05" and e["settlement_date"] >= req_date_str]
for e in user05_events:
    if e["amount"]:
        print(f"  Future event: {e['event_id']} {e['settlement_date']} {e['event_type']} {e['direction']} {e['amount']} {e['category']} {e['status']}")

print()
print("=" * 60)
print("DEBUG request_06: user_06, 2026-01-03")
# Got: affordable_later (wait), Expected: affordable_with_plan (full_payment + stop:event_476)
# So spending changes not triggering
user_id = "user_06"
req_date_str = "2026-01-03"
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = sim.profiles[user_id]
print(f"  Starting balance: {profile['current_available_balance']}")
print(f"  min_bal = {min_bal}")
print(f"  min_proj = {min_proj:.2f}")
print(f"  safe_to_pay = {max(0, min_proj - min_bal):.2f} (expected 603.3)")
print(f"  willing_stop: {profile['expense_categories_user_is_willing_to_stop']}")
print(f"  willing_reduce: {profile['expense_categories_user_is_willing_to_reduce']}")

# Check event_476
ev476 = [e for e in data["events"] if e["event_id"] == "event_476"]
if ev476:
    print(f"  event_476: {ev476[0]}")

# Check what past events are in stoppable categories for user_06
past_evs = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]
willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
print(f"  willing_stop: {willing_stop}")
stoppable = [e for e in past_evs if e["category"] in willing_stop and e["flexibility"] in ("stoppable", "reducible_or_stoppable")]
print(f"  Stoppable past events: {len(stoppable)}")
for e in stoppable[-5:]:
    print(f"    {e['event_id']} {e['settlement_date']} {e['category']} {e['description']} {e['amount']}")
