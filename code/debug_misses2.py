"""Debug script part 2 - more detailed analysis."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from decision_engine import DecisionEngine
from collections import defaultdict
from datetime import timedelta
import math

data = load_all_data()
sim = CashFlowSimulator(data)
engine = DecisionEngine(data)

# ---- Request 02: Why is installment not picked? ----
print("=" * 60)
print("DEBUG request_02: Why is installment not picked?")
req = next(s for s in data["sample_requests"] if s["request_id"] == "request_02")
print(f"  allows_partial: {req['allows_partial_payment']}")
print(f"  desired_completion_date: {req['desired_completion_date']}")
profile = data["profiles"][req["user_id"]]
considered_methods = set(m.strip() for m in profile["payment_methods_user_will_consider"].split("|") if m.strip())
print(f"  considered_methods: {considered_methods}")
max_inst_months = None
if profile.get("max_installment_months"):
    try:
        max_inst_months = int(profile["max_installment_months"])
    except:
        pass
print(f"  max_inst_months: {max_inst_months}")

req_id = req["request_id"]
opts = [o for o in data["payment_options"] if o["request_id"] == req_id]
print(f"  Payment options: {len(opts)}")
for o in opts:
    if o["payment_method"] == "installments":
        num_payments = int(o["number_of_payments"])
        freq_days = int(o["payment_frequency_days"] or 30)
        duration_days = (num_payments - 1) * freq_days
        duration_months = math.ceil(duration_days / 30.0)
        print(f"    {o['payment_option_id']}: {num_payments} x {freq_days}d -> duration_months={duration_months} max={max_inst_months}")
        desired_comp = parse_date(req["desired_completion_date"])
        first_p = parse_date(o["first_payment_date"])
        p_dates = [first_p + timedelta(days=k * freq_days) for k in range(num_payments)]
        last_p = p_dates[-1]
        print(f"    first_p={first_p} last_p={last_p} desired_comp={desired_comp}")
        print(f"    last_p > desired_comp: {last_p > desired_comp}")

# ---- Request 05: What large future event is missing? ----
print()
print("=" * 60)
print("DEBUG request_05: What large future event is missing?")
user_id = "user_05"
req_date_str = "2025-11-06"
# Future events from CSV
u5_future = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] >= req_date_str and e["amount"]]
print("  Future CSV events:")
for e in u5_future:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")

# All past events
u5_past = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]
print()
print("  Past events (last 20):")
for e in u5_past[-20:]:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['flexibility']} {e['status']}")

# ---- Request 06: Why is spending change not tried? ----
print()
print("=" * 60)
print("DEBUG request_06: Why spending change not tried?")
req6 = next(s for s in data["sample_requests"] if s["request_id"] == "request_06")
res6 = engine.evaluate_request(req6)
print(f"  Result: {res6}")
# The engine only tries spending changes if no full_payment/installments/partial_payment candidate exists
# It generates a 'wait' candidate first
# Expected: full_payment + stop:event_476
# Problem: The code tries spending changes only when no preferred candidate exists
# But 'wait' is generated, and then no spending_change search is done
# because check is: "not any(c['method'] in ('full_payment','installments','partial_payment')"
# The wait is only method='wait', so spending changes SHOULD be tried... Let's check
user_id = "user_06"
req_date_str = "2026-01-03"
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
amount_safe = max(0, min_proj - min_bal)
req_amount = 620.4
print(f"  Base amount_safe={amount_safe:.2f}")
print(f"  req_amount={req_amount}")
# try stopping event_476
balances_sc, min_sc, _ = sim.simulate_balance(user_id, req_date_str, ["stop:event_476"])
safe_sc = max(0, min_sc - min_bal)
print(f"  With stop:event_476 => safe_sc={safe_sc:.2f}")
print(f"  >= req_amount: {safe_sc >= req_amount}")

# ---- Request 08: forecast horizon ----
print()
print("=" * 60)
print("DEBUG request_08: user_08, 2025-02-07")
user_id = "user_08"
req_date_str = "2025-02-07"
req8 = next(s for s in data["sample_requests"] if s["request_id"] == "request_08")
print(f"  Expected: affordable_later, wait, earliest=2025-04-15")
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = data["profiles"][user_id]
print(f"  Starting balance: {profile['current_available_balance']}")
print(f"  min_bal={min_bal} min_proj={min_proj:.2f}")
print(f"  safe_to_pay = {max(0, min_proj - min_bal):.2f} (expected 284.57)")
req_amount = 996.6
req_d = parse_date(req_date_str)
# Check balances near April 2025
for d_idx in range(55, 70):
    cd = req_d + timedelta(days=d_idx)
    print(f"    {cd}: bal={balances[cd]:.2f} safe={balances[cd]-req_amount:.2f} min={min_bal}")

# Check messages
print(f"  Messages: {data['messages_by_user'].get(user_id)}")

# Future events
u8_future = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] >= req_date_str and e["amount"]]
print("  Future CSV events:")
for e in u8_future:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")

# Past events for salary pattern
u8_past = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["category"] == "salary"]
print("  Past salary events:")
for e in u8_past[-5:]:
    print(f"    {e['event_id']} {e['settlement_date']} {e['amount']} {e['status']}")
