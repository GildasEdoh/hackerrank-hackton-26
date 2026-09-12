import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from image_data import IMAGE_AMOUNTS
from message_parser import parse_messages

def load_all_data(dataset_dir="dataset"):
    # 1. Profiles
    profiles = {}
    with open(os.path.join(dataset_dir, "financial_profiles.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            profiles[r["user_id"]] = r

    # 2. Exchange rates
    # Key: (rate_date, from_currency, to_currency) -> float(rate)
    exchange_rates = {}
    with open(os.path.join(dataset_dir, "exchange_rates.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            exchange_rates[(r["rate_date"], r["from_currency"], r["to_currency"])] = float(r["rate"])

    # 3. Images mapping
    event_to_image = {}
    with open(os.path.join(dataset_dir, "images.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            event_to_image[r["related_event_id"]] = r["image_id"]

    # 4. Financial events
    events = []
    with open(os.path.join(dataset_dir, "financial_events.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ev = dict(r)
            # Fill missing amount if mapped in images
            if not ev["amount"] and ev["event_id"] in event_to_image:
                img_id = event_to_image[ev["event_id"]]
                if img_id in IMAGE_AMOUNTS:
                    ev["amount"] = str(IMAGE_AMOUNTS[img_id])

            # Convert currency to home currency if needed
            uid = ev["user_id"]
            if uid in profiles:
                home_curr = profiles[uid]["home_currency"]
                ev_curr = ev["currency"]
                if ev["amount"] and ev_curr and ev_curr != home_curr:
                    s_date = ev["settlement_date"]
                    rate_key = (s_date, ev_curr, home_curr)
                    if rate_key in exchange_rates:
                        orig_amt = float(ev["amount"])
                        conv_amt = orig_amt * exchange_rates[rate_key]
                        ev["original_amount"] = orig_amt
                        ev["original_currency"] = ev_curr
                        ev["amount"] = str(conv_amt)
                        ev["currency"] = home_curr
            events.append(ev)

    # 5. Payment options
    payment_options = []
    with open(os.path.join(dataset_dir, "request_payment_options.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            payment_options.append(dict(r))

    # 6. Messages parsed
    messages_by_user = parse_messages()

    # 7. Requests (both evaluation and sample)
    eval_requests = []
    req_file = os.path.join(dataset_dir, "requests.csv")
    if os.path.exists(req_file):
        with open(req_file, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                eval_requests.append(dict(r))

    sample_requests = []
    sample_file = os.path.join(dataset_dir, "sample_requests.csv")
    if os.path.exists(sample_file):
        with open(sample_file, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sample_requests.append(dict(r))

    return {
        "profiles": profiles,
        "events": events,
        "exchange_rates": exchange_rates,
        "payment_options": payment_options,
        "messages_by_user": messages_by_user,
        "eval_requests": eval_requests,
        "sample_requests": sample_requests
    }

if __name__ == "__main__":
    data = load_all_data()
    print("Loaded data successfully:")
    print(f"Profiles: {len(data['profiles'])}")
    print(f"Events: {len(data['events'])}")
    print(f"Options: {len(data['payment_options'])}")
    print(f"Eval requests: {len(data['eval_requests'])}")
    print(f"Sample requests: {len(data['sample_requests'])}")
