import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator, parse_date, format_date
from decision_engine import DecisionEngine

data = load_all_data()
engine = DecisionEngine(data)
req = [r for r in data["sample_requests"] if r["request_id"] == "request_06"][0]
res = engine.evaluate_request(req)

print(f"Result for request_06: {res}")
