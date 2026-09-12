"""Debug request_05 salary and request_08 earliest_date logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from datetime import timedelta

data = load_all_data()
sim = CashFlowSimulator(data)

# --- request_05 --- 
print("=" * 60)
print("request_05 user_05: why min_proj so high?")
user_id = "user_05"
req_date_str = "2025-11-06"
profile = data["profiles"][user_id]
print(f"  current_balance: {profile['current_available_balance']}")
print(f"  min_balance: {profile['minimum_balance_to_keep']}")
# Check all past events more carefully
u5_all = [e for e in data["events"] if e["user_id"] == user_id]
print(f"  Total events for user_05: {len(u5_all)}")
cats = set(e["category"] for e in u5_all)
print(f"  Categories: {cats}")
# Check salary
salary_evs = [e for e in u5_all if e["category"] == "salary"]
print(f"  Salary events: {len(salary_evs)}")
for e in salary_evs:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['status']}")
# Check debt_repayment / loans - is there a large debt payment?
debt_evs = [e for e in u5_all if e["category"] in ("debt_repayment", "loans", "loan")]
print(f"  Debt events: {len(debt_evs)}")
for e in debt_evs:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['status']}")
# Check what events are large and future
large_future = [e for e in u5_all if e["settlement_date"] >= req_date_str and float(e["amount"] or 0) > 5000]
print(f"  Large future events (>5000): {len(large_future)}")
for e in large_future:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")
# What is the expected safe to pay = 737?
# current_balance - min_balance = expected safe?
print(f"  current_balance - min_balance = {float(profile['current_available_balance']) - float(profile['minimum_balance_to_keep']):.2f}")

# Check all categories and their recurrence for user_05
by_cat = {}
for e in u5_all:
    c = e["category"]
    if c not in by_cat:
        by_cat[c] = []
    by_cat[c].append(e)
print("  Category summary:")
for cat, evs in sorted(by_cat.items()):
    debits = [e for e in evs if e["direction"] == "debit" and e["amount"]]
    if debits:
        amts = [float(e["amount"]) for e in debits]
        print(f"    {cat}: {len(debits)} debit events, avg={sum(amts)/len(amts):.2f}, max={max(amts):.2f}")

# --- request_08 find_earliest logic ---
print()
print("=" * 60)
print("request_08 user_08: why earliest_date empty?")
user_id = "user_08"
req_date_str = "2025-02-07"
req_amount = 996.6
req_d = parse_date(req_date_str)
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
print(f"  min_bal={min_bal}")
# The current logic: for each d_idx, check ALL days from d_idx to 91
# On Apr 15 (d_idx=67), does balance stay >= min_bal + req_amount for ALL days after?
for d_idx in range(60, 91):
    cd = req_d + timedelta(days=d_idx)
    safe = True
    for t_idx in range(d_idx, 91):
        t_d = req_d + timedelta(days=t_idx)
        if balances[t_d] - req_amount < min_bal:
            safe = False
            break
    if d_idx >= 67 and d_idx <= 72:
        print(f"  d_idx={d_idx} {cd}: earliest_check_safe={safe}")
        # Show what breaks it
        for t_idx in range(d_idx, 91):
            t_d = req_d + timedelta(days=t_idx)
            if balances[t_d] - req_amount < min_bal:
                print(f"    Fails at t={t_d}: bal={balances[t_d]:.2f} - {req_amount} = {balances[t_d]-req_amount:.2f} < min={min_bal}")
                break

# --- request_06 spending changes logic ---
print()
print("=" * 60)
print("request_06 user_06: spending change simulation detail")
user_id = "user_06"
req_date_str = "2026-01-03"
req_amount = 620.4
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = data["profiles"][user_id]
print(f"  starting_bal={profile['current_available_balance']} min_bal={min_bal}")
# What happens when we stop event_476?
balances_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, ["stop:event_476"])
print(f"  Without spending changes: min_proj={min_proj:.2f} safe={max(0, min_proj-min_bal):.2f}")
print(f"  With stop:event_476: min_sc={min_sc:.2f} safe_sc={max(0, min_sc-min_bal):.2f}")
# Detailed cashflow comparison
req_d = parse_date(req_date_str)
daily_base = sim.forecast_user_cashflow(user_id, req_date_str)
daily_sc = sim.forecast_user_cashflow(user_id, req_date_str, ["stop:event_476"])
print("  Cashflow comparison:")
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    bf = daily_base.get(cd, 0)
    sf = daily_sc.get(cd, 0)
    if bf != sf or abs(bf) > 10:
        print(f"    {cd}: base={bf:.2f} sc={sf:.2f} diff={sf-bf:.2f}")
# The issue: the stop:event_476 only stops ONE occurrence (the last past event)
# But the streaming subscription recurs monthly - so future recurrences still generate
# The simulator stops based on 'last_ev_id in stopped_events' which only checks by_desc last event
