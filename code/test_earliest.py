"""Test corrected find_earliest_full_payment_date."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from datetime import datetime, timedelta
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)

def find_earliest_safe_date(user_id, req_date_str, req_amount, spending_changes=None):
    req_date = parse_date(req_date_str)
    profile = data["profiles"][user_id]
    min_bal = float(profile["minimum_balance_to_keep"])
    base_balances, _, _ = sim.simulate_balance(user_id, req_date_str, spending_changes)
    
    for d_idx in range(91):
        cand_date = req_date + timedelta(days=d_idx)
        # Check if paying req_amount on cand_date keeps all subsequent balances >= min_bal
        safe_from_cand = True
        for t_idx in range(d_idx, 91):
            t_date = req_date + timedelta(days=t_idx)
            if base_balances[t_date] - req_amount < min_bal:
                safe_from_cand = False
                break
        if safe_from_cand:
            return format_date(cand_date)
    return ""

sample_dict = {r["request_id"]: r for r in data["sample_requests"]}
for req_id, req in sample_dict.items():
    user_id = req["user_id"]
    req_amt = float(req["requested_amount"])
    sc = []
    if req["spending_changes_needed"] != "none":
        sc = req["spending_changes_needed"].split("|")
    earliest_no_chg = find_earliest_safe_date(user_id, req["request_date"], req_amt, None)
    earliest_with_chg = find_earliest_safe_date(user_id, req["request_date"], req_amt, sc)
    print(f"{req_id} ({user_id}): got_no_chg={earliest_no_chg}, got_with_chg={earliest_with_chg}, exp={req['earliest_date_for_full_payment']}")
