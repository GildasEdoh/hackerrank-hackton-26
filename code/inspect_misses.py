"""Inspect the 7 misses to understand ground truth logic."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from decision_engine import DecisionEngine

data = load_all_data()
engine = DecisionEngine(data)
sim = CashFlowSimulator(data)

sample_dict = {r["request_id"]: r for r in data["sample_requests"]}

for req_id in ["request_04", "request_05", "request_06", "request_10", "request_11", "request_13", "request_21"]:
    req = sample_dict[req_id]
    user_id = req["user_id"]
    prof = data["profiles"][user_id]
    res = engine.evaluate_request(req)
    
    print(f"\n=================== {req_id} ({user_id}) ===================")
    print(f"Request: date={req['request_date']}, amt={req['requested_amount']}, deadline={req.get('desired_completion_date')}, partial={req.get('allows_partial_payment')}")
    print(f"User Profile: balance={prof['current_available_balance']}, min_bal={prof['minimum_balance_to_keep']}")
    print(f"Protected: {prof.get('expense_categories_to_protect')}, Willing Stop: {prof.get('expense_categories_user_is_willing_to_stop')}, Willing Reduce: {prof.get('expense_categories_user_is_willing_to_reduce')}")
    print(f"Methods: {prof.get('payment_methods_user_will_consider')}, Max Inst Months: {prof.get('max_installment_months')}")
    print(f"Got: status={res['affordability_status']}, method={res['recommended_payment_method']}, safe_pay={res['amount_safe_to_pay']}, plan={res['payment_plan']}, chg={res['spending_changes_needed']}, earliest={res['earliest_date_for_full_payment']}")
    print(f"Exp: status={req['affordability_status']}, method={req['recommended_payment_method']}, safe_pay={req['amount_safe_to_pay']}, plan={req['payment_plan']}, chg={req['spending_changes_needed']}, earliest={req['earliest_date_for_full_payment']}")
    
    # Check options
    opts = [o for o in data["payment_options"] if o["request_id"] == req_id]
    print(f"Payment Options ({len(opts)}):")
    for o in opts:
        print(f"  id={o['payment_option_id']} method={o['payment_method']} num={o['number_of_payments']} freq={o['payment_frequency_days']} amt={o['payment_amount']} total={o['total_payable_amount']} first={o['first_payment_date']}")
