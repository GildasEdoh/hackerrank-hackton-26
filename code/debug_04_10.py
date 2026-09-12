"""Debug request_04 and request_10."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from datetime import timedelta

data = load_all_data()
sim = CashFlowSimulator(data)

# ---- request_04: user_04, 2024-06-04 ----
print("=" * 60)
print("DEBUG request_04: user_04, 2024-06-04, amt=12693000")
print("  Expected: affordable_later, wait, earliest=2024-06-15")
print("  Got: not_affordable, earliest=2024-06-04")
user_id = "user_04"
req_date_str = "2024-06-04"
req_amount = 12693000.0
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = data["profiles"][user_id]
print(f"  starting_bal={profile['current_available_balance']}")
print(f"  min_bal={min_bal} min_proj={min_proj:.2f}")
print(f"  safe_to_pay={max(0, min_proj-min_bal):.2f} (expected 8401800)")
req_d = parse_date(req_date_str)
# Check June 4 and June 15
for d_idx in [0, 11, 15]:
    cd = req_d + timedelta(days=d_idx)
    print(f"  {cd}: bal={balances[cd]:.2f}, bal-amt={balances[cd]-req_amount:.2f}, min={min_bal}")
# Print cashflows
daily = sim.forecast_user_cashflow(user_id, req_date_str)
print("  Cashflows (first 30 days):")
for d_idx in range(30):
    cd = req_d + timedelta(days=d_idx)
    f = daily.get(cd, 0)
    if f != 0:
        print(f"    {cd}: {f:.2f} -> running_bal={balances[cd]:.2f}")
# Check messages
print(f"  Messages: {data['messages_by_user'].get(user_id)}")
# Check future events
u4_future = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] >= req_date_str]
print("  Future CSV events:")
for e in u4_future:
    if e["amount"]:
        print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")
# Check payment options
opts = [o for o in data["payment_options"] if o["request_id"] == "request_04"]
print(f"  Payment options: {len(opts)}")
for o in opts:
    print(f"    {o['payment_option_id']}: {o['payment_method']} {o['payment_amount']}")

print()
print("=" * 60)
print("DEBUG request_10: user_10, 2024-12-06, amt=266700")
print("  Expected: not_affordable, safe_to_pay=12700")
print("  Got: affordable_with_plan partial_payment, safe_to_pay=111562")
user_id = "user_10"
req_date_str = "2024-12-06"
req_amount = 266700.0
balances, min_proj, min_bal = sim.simulate_balance(user_id, req_date_str)
profile = data["profiles"][user_id]
print(f"  starting_bal={profile['current_available_balance']}")
print(f"  min_bal={min_bal} min_proj={min_proj:.2f}")
print(f"  safe_to_pay={max(0, min_proj-min_bal):.2f} (expected 12700)")
req_d = parse_date(req_date_str)
# Print cashflows
daily = sim.forecast_user_cashflow(user_id, req_date_str)
print("  Cashflows (non-zero):")
for d_idx in range(91):
    cd = req_d + timedelta(days=d_idx)
    f = daily.get(cd, 0)
    if f != 0:
        print(f"    {cd}: {f:.2f} -> running_bal={balances[cd]:.2f}")
# Check messages
print(f"  Messages: {data['messages_by_user'].get(user_id)}")
# Future CSV events
u10_future = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] >= req_date_str and e["amount"]]
print("  Future CSV events:")
for e in u10_future:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")
print()
# Past events
u10_past = [e for e in data["events"] if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]
print("  Past events (last 20):")
for e in u10_past[-20:]:
    print(f"    {e['event_id']} {e['settlement_date']} {e['direction']} {e['amount']} {e['category']} {e['status']}")
