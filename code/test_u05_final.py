import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator

data = load_all_data()
# In simulator, if last salary event description has "final", salary_ended = True
req = [r for r in data["sample_requests"] if r["request_id"] == "request_05"][0]
user_id = req["user_id"]
u_events = [e for e in data["events"] if e["user_id"] == user_id]
salary_events = [e for e in u_events if e["category"] == "salary" and e["direction"] == "credit"]
last_sal = salary_events[-1]
print("Last salary:", last_sal)
if "final" in last_sal["description"].lower():
    print("Salary ended!")

# Let's test simulation with salary_ended
sim = CashFlowSimulator(data)
data["messages_by_user"][user_id]["salary_ended"] = True
balances, min_proj, min_bal = sim.simulate_balance(user_id, req["request_date"])
print(f"min_proj = {min_proj}, min_bal = {min_bal}, min_proj - min_bal = {min_proj - min_bal}")
