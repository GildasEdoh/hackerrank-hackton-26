import os, sys
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date
from test_dynamic import DynamicSimulator

data = load_all_data()
sim = DynamicSimulator(data)

def find_earliest_safe_date_horizon(user_id, req_date_str, req_amount, horizon_days=30, spending_changes=None):
    req_date = parse_date(req_date_str)
    profile = data["profiles"][user_id]
    min_bal = float(profile["minimum_balance_to_keep"])
    base_balances, _, _ = sim.simulate_balance(user_id, req_date_str, spending_changes)
    
    for d_idx in range(91):
        cand_date = req_date + timedelta(days=d_idx)
        safe_from_cand = True
        # Check from d_idx up to min(d_idx + horizon_days, 91)
        for t_idx in range(d_idx, min(d_idx + horizon_days, 91)):
            t_date = req_date + timedelta(days=t_idx)
            if base_balances[t_date] - req_amount < min_bal:
                safe_from_cand = False
                break
        if safe_from_cand:
            return format_date(cand_date)
    return ""

print("Testing horizon_days=30:")
for s in data["sample_requests"]:
    req_id = s["request_id"]
    user_id = s["user_id"]
    amt = float(s["requested_amount"])
    sc = s["spending_changes_needed"].split("|") if s["spending_changes_needed"] != "none" else None
    earliest = find_earliest_safe_date_horizon(user_id, s["request_date"], amt, horizon_days=30, spending_changes=sc)
    print(f"{req_id} ({user_id}): got={earliest}, exp={s['earliest_date_for_full_payment']}")
