import os, sys, statistics
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date

data = load_all_data()

class DynamicSimulator:
    def __init__(self, data):
        self.profiles = data["profiles"]
        self.events_by_user = defaultdict(list)
        for e in data["events"]:
            self.events_by_user[e["user_id"]].append(e)
        self.messages_by_user = data["messages_by_user"]

    def forecast_user_cashflow(self, user_id, request_date_str, spending_changes=None):
        if spending_changes is None:
            spending_changes = []

        stopped_events = set()
        reduced_events = {}
        for sc in spending_changes:
            parts = sc.split(":")
            if parts[0] == "stop":
                stopped_events.add(parts[1])
            elif parts[0] == "reduce_to":
                reduced_events[parts[1]] = float(parts[2])

        req_date = parse_date(request_date_str)
        end_date = req_date + timedelta(days=90)

        profile = self.profiles[user_id]
        user_events = self.events_by_user[user_id]
        msg_up = self.messages_by_user.get(user_id, {})

        daily_cashflow = defaultdict(float)

        # 1. Existing events in CSV on or after request_date
        future_events = [e for e in user_events if e["settlement_date"] >= request_date_str]

        for e in future_events:
            if not e["amount"]:
                continue
            amt = float(e["amount"])
            ev_date = parse_date(e["settlement_date"])
            if ev_date > end_date:
                continue

            status = e["status"]
            direction = e["direction"]
            ev_type = e["event_type"]

            if status in ("cancelled", "failed", "unrealized"):
                continue

            if direction == "debit":
                if e["event_id"] in stopped_events:
                    continue
                if e["event_id"] in reduced_events:
                    amt = reduced_events[e["event_id"]]
                daily_cashflow[ev_date] -= amt
            elif direction == "credit":
                if status == "settled" or (status == "scheduled" and ev_type == "income" and e["category"] == "salary"):
                    daily_cashflow[ev_date] += amt

        # 2. Historical patterns
        past_events = [e for e in user_events if e["settlement_date"] < request_date_str and e["amount"]]
        past_valid = [e for e in past_events if e["status"] in ("settled", "pending", "scheduled")]

        by_cat = defaultdict(list)
        for e in past_valid:
            by_cat[e["category"]].append(e)

        # A. Salary recurrence
        all_sal_events = [e for e in past_valid if e["category"] == "salary" and e["direction"] == "credit"]
        salary_ended = msg_up.get("salary_ended", False)
        if all_sal_events and any(w in all_sal_events[-1]["description"].lower() for w in ("final", "severance", "last payroll")):
            salary_ended = True

        salary_events = [
            e for e in all_sal_events
            if not any(w in e["description"].lower() for w in ("bonus", "commission", "incentive", "overtime", "refund", "gain", "dividend", "lottery", "one-off"))
        ]
        if not salary_events and all_sal_events:
            salary_events = all_sal_events

        if not salary_ended and salary_events:
            if msg_up.get("salary_amount") is not None:
                salary_amt = msg_up["salary_amount"]
            else:
                salary_amt = float(salary_events[-1]["amount"])

            if msg_up.get("salary_date"):
                fixed_s_date = parse_date(msg_up["salary_date"])
                salary_day = fixed_s_date.day
            else:
                days = [parse_date(e["settlement_date"]).day for e in salary_events]
                salary_day = max(set(days), key=days.count)

            cur_month = req_date.month
            cur_year = req_date.year
            for m_offset in range(4):
                m = (cur_month - 1 + m_offset) % 12 + 1
                y = cur_year + (cur_month - 1 + m_offset) // 12
                max_d = calendar.monthrange(y, m)[1]
                d_day = min(salary_day, max_d)
                p_date = datetime(y, m, d_day).date()

                if req_date <= p_date <= end_date:
                    already_scheduled = any(
                        e["category"] == "salary" and e["settlement_date"] == format_date(p_date)
                        for e in future_events
                    )
                    if not already_scheduled:
                        daily_cashflow[p_date] += salary_amt

        # B. Monthly recurring categories by description
        monthly_cats = {
            'rent', 'utilities', 'debt_repayment', 'insurance', 'education',
            'gym', 'music_subscription', 'delivery_membership', 'cloud_storage',
            'streaming', 'healthcare', 'housing'
        }

        by_desc = defaultdict(list)
        for e in past_valid:
            by_desc[e["description"]].append(e)

        for desc, evs in by_desc.items():
            cat = evs[0]["category"]
            if cat not in monthly_cats or evs[0]["direction"] != "debit":
                continue

            last_ev = evs[-1]
            last_ev_id = last_ev["event_id"]
            flex = last_ev["flexibility"]

            is_stopped = (last_ev_id in stopped_events)
            is_reduced = (last_ev_id in reduced_events)

            if is_stopped:
                continue

            dates = [parse_date(e["settlement_date"]) for e in evs]
            dates.sort()
            amounts = [float(e["amount"]) for e in evs]

            if len(dates) >= 2:
                diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                median_diff = statistics.median(diffs)
            else:
                median_diff = 30

            if 25 <= median_diff <= 35 or len(dates) >= 3:
                if is_reduced:
                    proj_amt = reduced_events[last_ev_id]
                elif cat == "rent":
                    proj_amt = amounts[-1] * msg_up.get("rent_multiplier", 1.0)
                elif flex == "fixed" and len(set(amounts[-3:])) == 1:
                    proj_amt = amounts[-1]
                else:
                    proj_amt = round(statistics.mean(amounts[-3:]), 2)

                day_of_month = dates[-1].day
                cur_month = req_date.month
                cur_year = req_date.year
                for m_offset in range(4):
                    m = (cur_month - 1 + m_offset) % 12 + 1
                    y = cur_year + (cur_month - 1 + m_offset) // 12
                    max_d = calendar.monthrange(y, m)[1]
                    d_day = min(day_of_month, max_d)
                    p_date = datetime(y, m, d_day).date()
                    if req_date <= p_date <= end_date:
                        if not any(e["description"] == desc and e["settlement_date"] == format_date(p_date) for e in future_events):
                            daily_cashflow[p_date] -= proj_amt

        # C. Variable spending categories with interval < 25 days
        for cat, evs in by_cat.items():
            if cat in monthly_cats or cat == "salary" or evs[0]["direction"] != "debit":
                continue
            if len(evs) < 3:
                continue
            dates = sorted(set(parse_date(e["settlement_date"]) for e in evs))
            if len(dates) < 3:
                continue
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            median_interval = round(statistics.median(diffs))
            if median_interval >= 25 or median_interval <= 0:
                continue

            last_ev = evs[-1]
            last_ev_id = last_ev["event_id"]
            is_stopped = (last_ev_id in stopped_events)
            is_reduced = (last_ev_id in reduced_events)

            if is_stopped:
                continue

            amts = [float(e["amount"]) for e in evs]
            if is_reduced:
                proj_amt = reduced_events[last_ev_id]
            else:
                proj_amt = round(statistics.mean(amts[-4:]), 2)

            last_date = dates[-1]
            next_date = last_date + timedelta(days=median_interval)
            while next_date <= end_date:
                if next_date >= req_date:
                    if not any(e["category"] == cat and e["settlement_date"] == format_date(next_date) for e in future_events):
                        daily_cashflow[next_date] -= proj_amt
                next_date += timedelta(days=median_interval)

        return daily_cashflow

    def simulate_balance(self, user_id, request_date_str, spending_changes=None):
        profile = self.profiles[user_id]
        starting_bal = float(profile["current_available_balance"])
        min_bal = float(profile["minimum_balance_to_keep"])
        req_date = parse_date(request_date_str)

        daily_flow = self.forecast_user_cashflow(user_id, request_date_str, spending_changes)

        running_bal = starting_bal
        balances = {}
        for d_idx in range(91):
            cur_d = req_date + timedelta(days=d_idx)
            running_bal += daily_flow.get(cur_d, 0.0)
            balances[cur_d] = running_bal

        min_projected = min(balances.values())
        return balances, min_projected, min_bal

# Test accuracy with DynamicSimulator
from decision_engine import DecisionEngine
engine = DecisionEngine(data)
engine.simulator = DynamicSimulator(data)

correct_status = 0
correct_method = 0
total = len(data["sample_requests"])
for s in data["sample_requests"]:
    res = engine.evaluate_request(s)
    sc = res["affordability_status"] == s["affordability_status"]
    mc = res["recommended_payment_method"] == s["recommended_payment_method"]
    if sc:
        correct_status += 1
    if mc:
        correct_method += 1
    if not sc or not mc:
        print(f"\n[MISS] {s['request_id']} user={s['user_id']}")
        print(f"  status: got={res['affordability_status']!r} exp={s['affordability_status']!r}")
        print(f"  method: got={res['recommended_payment_method']!r} exp={s['recommended_payment_method']!r}")
        print(f"  safe:   got={res['amount_safe_to_pay']} exp={s['amount_safe_to_pay']}")
        print(f"  plan:   got={res['payment_plan']} exp={s['payment_plan']}")
        print(f"  chg:    got={res['spending_changes_needed']} exp={s['spending_changes_needed']}")
        print(f"  early:  got={res['earliest_date_for_full_payment']} exp={s['earliest_date_for_full_payment']}")

print(f"\nStatus accuracy: {correct_status}/{total} = {correct_status/total*100:.1f}%")
print(f"Method accuracy: {correct_method}/{total} = {correct_method/total*100:.1f}%")
