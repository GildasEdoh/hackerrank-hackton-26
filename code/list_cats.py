import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data

data = load_all_data()

# Let's inspect all unique categories in dataset
cats = set(e["category"] for e in data["events"] if e["category"])
print("All categories:", sorted(cats))
