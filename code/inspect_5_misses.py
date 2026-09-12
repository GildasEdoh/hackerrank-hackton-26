import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from decision_engine import DecisionEngine

data = load_all_data()
engine = DecisionEngine(data)

for req_id in ["request_06", "request_08", "request_11", "request_13", "request_21"]:
    req = [r for r in data["sample_requests"] if r["request_id"] == req_id][0]
    print(f"\n=================== {req_id} ({req['user_id']}) ===================")
    print(f"Date: {req['request_date']}, Amt: {req['requested_amount']}, Deadline: {req['desired_completion_date']}")
    
    # Evaluate without spending changes
    ef_date = engine.find_earliest_full_payment_date(req["user_id"], req["request_date"], float(req["requested_amount"]))
    print(f"Earliest full date (no changes): '{ef_date}' vs deadline '{req['desired_completion_date']}'")
    if ef_date:
        print(f"Is within deadline? {parse_date(ef_date) <= parse_date(req['desired_completion_date'])}")
