"""
Buy or Wait? — Main entry point.
Reads dataset/requests.csv, runs the financial decision engine for each request,
and writes dataset/output.csv.
Also writes evaluation/usage_report.md.

Run from repo root:
    python code/main.py
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone

# Ensure code/ is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_all_data
from decision_engine import DecisionEngine

DATASET_DIR = "dataset"
OUTPUT_CSV = "output.csv"  # repo root, as required by submission spec
USAGE_REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation", "usage_report.md")

OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]


def generate_explanation(request, result, profile):
    """Generate a concise, grounded decision explanation."""
    req_id = result["request_id"]
    status = result["affordability_status"]
    method = result["recommended_payment_method"]
    amount = float(request["requested_amount"])
    currency = profile.get("home_currency", "")
    safe_pay = result["amount_safe_to_pay"]
    plan = result["payment_plan"]
    earliest = result["earliest_date_for_full_payment"]
    changes = result["spending_changes_needed"]
    min_bal = float(profile["minimum_balance_to_keep"])
    desired = request["desired_completion_date"]

    amt_str = f"{currency} {amount:,.2f}".strip()
    safe_str = f"{currency} {safe_pay:,.2f}".strip()
    min_str = f"{currency} {min_bal:,.2f}".strip()

    if status == "affordable_now":
        return (
            f"The full amount of {amt_str} can be paid on {request['request_date']} "
            f"while keeping the {min_str} minimum balance protected."
        )
    elif status == "affordable_with_plan":
        if method == "full_payment":
            if changes != "none":
                return (
                    f"The full {amt_str} is payable on {request['request_date']} "
                    f"after applying spending adjustments ({changes}), "
                    f"which free up sufficient cash while protecting the {min_str} minimum."
                )
            else:
                return (
                    f"The full {amt_str} is payable via {method.replace('_', ' ')} "
                    f"by {desired} without breaching the {min_str} minimum balance."
                )
        elif method == "installments":
            num_p = len(plan.split("|"))
            return (
                f"The {amt_str} is best paid in {num_p} installments "
                f"({plan[:80]}{'...' if len(plan) > 80 else ''}), "
                f"each timed to when the balance can safely absorb the payment above {min_str}."
            )
        elif method == "partial_payment":
            return (
                f"Pay {safe_str} immediately and the remainder by {earliest}, "
                f"keeping the {min_str} minimum protected at every step."
            )
        else:
            return (
                f"Payment of {amt_str} can be completed by {desired} "
                f"using a structured plan: {plan[:100]}."
            )
    elif status == "affordable_later":
        return (
            f"Insufficient funds today; {safe_str} is safely available now. "
            f"Wait until {earliest} when projected cash flow supports the full {amt_str} "
            f"above the {min_str} minimum balance."
        )
    else:  # not_affordable
        return (
            f"Do not make this payment by {desired}. "
            f"Only {safe_str} is safely available now; "
            f"none of the available options keeps the {min_str} minimum protected "
            f"while covering the full {amt_str}."
        )


def main():
    start_time = time.time()

    print("Loading data...")
    data = load_all_data(DATASET_DIR)
    print(f"  Profiles: {len(data['profiles'])}")
    print(f"  Events:   {len(data['events'])}")
    print(f"  Options:  {len(data['payment_options'])}")
    print(f"  Requests: {len(data['eval_requests'])}")

    if not data["eval_requests"]:
        print("ERROR: No evaluation requests found in dataset/requests.csv")
        sys.exit(1)

    engine = DecisionEngine(data)

    print("Processing requests...")
    results = []
    for i, req in enumerate(data["eval_requests"]):
        req_id = req["request_id"]
        user_id = req["user_id"]
        profile = data["profiles"].get(user_id, {})

        result = engine.evaluate_request(req)
        explanation = generate_explanation(req, result, profile)
        result["decision_explanation"] = explanation

        results.append(result)
        if (i + 1) % 10 == 0 or (i + 1) == len(data["eval_requests"]):
            print(f"  Processed {i + 1}/{len(data['eval_requests'])} requests...")

    print(f"Writing output to {OUTPUT_CSV}...")
    os.makedirs(os.path.dirname(OUTPUT_CSV) if os.path.dirname(OUTPUT_CSV) else ".", exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    elapsed = time.time() - start_time
    num_req = len(results)

    # Status summary
    status_counts = {}
    for r in results:
        s = r["affordability_status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    print("\nStatus distribution:")
    for s, n in sorted(status_counts.items()):
        print(f"  {s}: {n}")

    print(f"\nDone. {num_req} rows written in {elapsed:.1f}s.")

    # Write usage report (no LLM used — pure deterministic engine)
    os.makedirs(os.path.dirname(USAGE_REPORT), exist_ok=True)
    with open(USAGE_REPORT, "w", encoding="utf-8") as f:
        f.write("# Buy or Wait? — Evaluation Usage Report\n\n")
        f.write(f"**Run date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        f.write(f"**Total requests processed:** {num_req}\n\n")
        f.write(f"**Total elapsed time:** {elapsed:.1f}s\n\n")
        f.write(f"**Average time per request:** {elapsed / max(num_req, 1) * 1000:.1f}ms\n\n")
        f.write("## Model / AI Usage\n\n")
        f.write(
            "This solution uses a **fully deterministic, rule-based financial engine** with "
            "no external AI/LLM calls. All decisions are computed locally from the provided "
            "CSV datasets using the following components:\n\n"
        )
        f.write("| Component | Description |\n")
        f.write("|-----------|-------------|\n")
        f.write("| `data_loader.py` | Loads all CSVs, applies exchange-rate conversions, fills image-sourced amounts |\n")
        f.write("| `message_parser.py` | Parses salary/rent signals from messages.csv |\n")
        f.write("| `image_data.py` | Pre-extracted amounts from dataset/media/images/ |\n")
        f.write("| `simulator.py` | 90-day cashflow simulation with salary/expense recurrence |\n")
        f.write("| `decision_engine.py` | Evaluates full/partial/installment/wait candidates and ranks them |\n")
        f.write("\n## Token / Cost Summary\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write("| Model providers | None (no LLM used) |\n")
        f.write("| Model calls | 0 |\n")
        f.write("| Input tokens | 0 |\n")
        f.write("| Output tokens | 0 |\n")
        f.write("| Total tokens | 0 |\n")
        f.write(f"| Avg tokens per request | 0 |\n")
        f.write("| Estimated total cost | $0.00 |\n")
        f.write("| Estimated cost per request | $0.00 |\n")
        f.write("\n## Notes\n\n")
        f.write(
            "- Exchange rates from `exchange_rates.csv` are applied at settlement date.\n"
            "- Image amounts pre-extracted via OCR and stored in `image_data.py`.\n"
            "- Messages parsed with regex for salary changes, rent adjustments, and employment end.\n"
            "- Forecast window: 90 days from request date.\n"
            "- All amounts in the user's home currency.\n"
        )

    print(f"Usage report written to {USAGE_REPORT}")


if __name__ == "__main__":
    main()
