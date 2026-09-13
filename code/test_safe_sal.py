"""Test amount_safe_to_pay until next salary date."""
import os, sys
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date

data = load_all_data()
sim = CashFlowSimulator(data)

print("Comparing amount_safe_to_pay until next salary vs 90 days:")
for s in data["sample_requests"]:
    req_id = s["request_id"]
    user_id = s["user_id"]
    req_date = parse_date(s["request_date"])
    req_amt = float(s["requested_amount"])
    profile = data["profiles"][user_id]
    min_bal = float(profile["minimum_balance_to_keep"])
    
    balances, min_90, _ = sim.simulate_balance(user_id, s["request_date"])
    flow = sim.forecast_user_cashflow(user_id, s["request_date"])
    
    # Find next salary date
    next_sal = None
    for d_idx in range(91):
        cur_d = req_date + timedelta(days=d_idx)
        if flow.get(cur_d, 0) > 500: # salary credit
            next_sal = cur_d
            break
            
    if next_sal:
        days_to_sal = (next_sal - req_date).days
        min_to_sal = min(balances[req_date + timedelta(days=k)] for k in range(days_to_sal + 1))
        safe_sal = min(req_amt, max(0.0, min_to_sal - min_bal))
    else:
        safe_sal = min(req_amt, max(0.0, min_90 - min_bal))
        
    safe_90 = min(req_amt, max(0.0, min_90 - min_bal))
    exp_safe = float(s["amount_safe_to_pay"])
    
    print(f"{req_id} ({user_id}): safe_to_sal={safe_sal:.2f} | safe_90={safe_90:.2f} | exp={exp_safe:.2f} | diff_sal={abs(safe_sal - exp_safe):.2f}")
