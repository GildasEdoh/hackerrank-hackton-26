import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import CashFlowSimulator

data = load_all_data()
sim = CashFlowSimulator(data)
flow = sim.forecast_user_cashflow("user_06", "2026-01-03", ["stop:event_476"])
for d in sorted(flow.keys()):
    if "2026-01-03" <= str(d) <= "2026-01-15":
        print(f"  {d}: {flow[d]}")
