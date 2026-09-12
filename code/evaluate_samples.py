"""Quick accuracy check against sample_requests.csv"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from decision_engine import DecisionEngine

data = load_all_data()
engine = DecisionEngine(data)
samples = data["sample_requests"]
print(f"Total samples: {len(samples)}")

status_correct = 0
method_correct = 0
total = len(samples)

for s in samples:
    res = engine.evaluate_request(s)
    sc = res["affordability_status"] == s["affordability_status"]
    mc = res["recommended_payment_method"] == s["recommended_payment_method"]
    if sc:
        status_correct += 1
    if mc:
        method_correct += 1
    if not sc or not mc:
        print(f"\n[MISS] {s['request_id']} user={s['user_id']} date={s['request_date']} amt={s['requested_amount']}")
        print(f"  status:   got={res['affordability_status']!r} exp={s['affordability_status']!r}")
        print(f"  method:   got={res['recommended_payment_method']!r} exp={s['recommended_payment_method']!r}")
        print(f"  safe_pay: got={res['amount_safe_to_pay']} exp={s['amount_safe_to_pay']}")
        print(f"  plan_got: {res['payment_plan']}")
        print(f"  plan_exp: {s['payment_plan']}")
        print(f"  chg_got:  {res['spending_changes_needed']}")
        print(f"  chg_exp:  {s['spending_changes_needed']}")
        print(f"  earliest: got={res['earliest_date_for_full_payment']} exp={s['earliest_date_for_full_payment']}")

print(f"\nStatus accuracy: {status_correct}/{total} = {status_correct/total*100:.1f}%")
print(f"Method accuracy: {method_correct}/{total} = {method_correct/total*100:.1f}%")
