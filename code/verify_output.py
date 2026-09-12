"""Verify output.csv format."""
import csv

with open("dataset/output.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Check for scientific notation
sci_count = sum(1 for r in rows if "e+" in r["payment_plan"].lower() or "e-" in r["payment_plan"].lower())
print(f"Rows with scientific notation in payment_plan: {sci_count}")

# Show installment rows
inst_rows = [r for r in rows if r["recommended_payment_method"] == "installments"][:3]
for r in inst_rows:
    print(f"  {r['request_id']}: {r['payment_plan'][:100]}")

print(f"Columns: {list(rows[0].keys())}")
print(f"Total rows: {len(rows)}")

# Status distribution
from collections import Counter
status_dist = Counter(r["affordability_status"] for r in rows)
method_dist = Counter(r["recommended_payment_method"] for r in rows)
print(f"\nStatus distribution: {dict(status_dist)}")
print(f"Method distribution: {dict(method_dist)}")

# Verify no empty request_ids
empty_ids = [r for r in rows if not r["request_id"]]
print(f"Rows with empty request_id: {len(empty_ids)}")

# Check earliest_date format
date_examples = [(r["request_id"], r["earliest_date_for_full_payment"]) for r in rows[:5]]
print(f"Sample earliest dates: {date_examples}")
