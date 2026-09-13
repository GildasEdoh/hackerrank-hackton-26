"""Test targeting remaining misses."""
import os, sys, statistics, math
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date

data = load_all_data()

class PrecisionSimulator:
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
        protected_cats = set(c.strip() for c in profile.get("expense_categories_to_protect", "").split("|") if c.strip())

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
            'streaming', 'healthcare', 'housing', 'family_support'
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

        # C. Variable spending categories: essential or protected
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

class PrecisionEngine:
    def __init__(self, data):
        self.data = data
        self.profiles = data["profiles"]
        self.options_by_request = {}
        for o in data["payment_options"]:
            req_id = o["request_id"]
            if req_id not in self.options_by_request:
                self.options_by_request[req_id] = []
            self.options_by_request[req_id].append(o)
        self.simulator = PrecisionSimulator(data)

    def _check_installment_safe(self, balances, p_dates, p_amt, req_date, min_bal, end_date):
        for pd in p_dates:
            if pd not in balances:
                continue
            if balances[pd] - p_amt < min_bal:
                return False
        return True

    def find_earliest_full_payment_date(self, user_id, request_date_str, requested_amount, spending_changes=None):
        req_date = parse_date(request_date_str)
        profile = self.profiles[user_id]
        min_bal = float(profile["minimum_balance_to_keep"])

        base_balances, _, _ = self.simulator.simulate_balance(user_id, request_date_str, spending_changes)

        for d_idx in range(91):
            cand_date = req_date + timedelta(days=d_idx)
            safe_from_cand = True
            for t_idx in range(d_idx, 91):
                t_date = req_date + timedelta(days=t_idx)
                if base_balances[t_date] - requested_amount < min_bal:
                    safe_from_cand = False
                    break
            if safe_from_cand:
                return format_date(cand_date)

        return ""

    def evaluate_request(self, request):
        req_id = request["request_id"]
        user_id = request["user_id"]
        req_date_str = request["request_date"]
        req_date = parse_date(req_date_str)
        req_amount = float(request["requested_amount"])
        desired_comp_str = request["desired_completion_date"]
        desired_comp_date = parse_date(desired_comp_str)
        allows_partial = request["allows_partial_payment"].strip().lower() in ("true", "1", "yes")

        profile = self.profiles[user_id]
        min_bal = float(profile["minimum_balance_to_keep"])
        considered_methods = set(m.strip() for m in profile["payment_methods_user_will_consider"].split("|") if m.strip())
        max_inst_months = None
        if profile.get("max_installment_months"):
            try:
                max_inst_months = int(profile["max_installment_months"])
            except ValueError:
                pass

        balances, min_proj, _ = self.simulator.simulate_balance(user_id, req_date_str)
        end_date = req_date + timedelta(days=90)

        base_safe_to_pay = max(0.0, min_proj - min_bal)
        amount_safe_to_pay = min(req_amount, base_safe_to_pay)

        earliest_full_date = self.find_earliest_full_payment_date(user_id, req_date_str, req_amount)

        candidates = []

        # Candidate 1: full_payment (no changes)
        if "full_payment" in considered_methods and amount_safe_to_pay >= req_amount:
            candidates.append({
                "method": "full_payment",
                "plan": f"{req_date_str}:{self._fmt(req_amount)}",
                "cost": req_amount,
                "first_date": req_date,
                "last_date": req_date,
                "num_payments": 1,
                "option_id": "0",
                "changes": "none",
                "status": "affordable_now"
            })

        # Candidate 2: partial_payment (no changes)
        if (allows_partial and "partial_payment" in considered_methods and
                0 < amount_safe_to_pay < req_amount and earliest_full_date and
                parse_date(earliest_full_date) <= desired_comp_date):
            rem_amt = req_amount - amount_safe_to_pay
            candidates.append({
                "method": "partial_payment",
                "plan": f"{req_date_str}:{self._fmt(amount_safe_to_pay)}|{earliest_full_date}:{self._fmt(rem_amt)}",
                "cost": req_amount,
                "first_date": req_date,
                "last_date": parse_date(earliest_full_date),
                "num_payments": 2,
                "option_id": "0",
                "changes": "none",
                "status": "affordable_with_plan"
            })

        # Candidate 3: installments (no changes)
        if "installments" in considered_methods:
            opts = self.options_by_request.get(req_id, [])
            for o in opts:
                if o["payment_method"] != "installments":
                    continue
                num_payments = int(o["number_of_payments"])
                freq_days = int(o["payment_frequency_days"] or 30)
                duration_days = (num_payments - 1) * freq_days
                duration_months = math.ceil(duration_days / 30.0)
                if max_inst_months is not None and duration_months > max_inst_months:
                    continue

                first_p_date = parse_date(o["first_payment_date"])
                p_dates = [first_p_date + timedelta(days=k * freq_days) for k in range(num_payments)]
                last_p_date = p_dates[-1]

                if last_p_date > desired_comp_date:
                    continue

                p_amt = float(o["payment_amount"])
                safe_inst = self._check_installment_safe(balances, p_dates, p_amt, req_date, min_bal, end_date)

                if safe_inst:
                    plan_str = "|".join(f"{format_date(pd)}:{self._fmt(p_amt)}" for pd in p_dates)
                    candidates.append({
                        "method": "installments",
                        "plan": plan_str,
                        "cost": float(o["total_payable_amount"]),
                        "first_date": first_p_date,
                        "last_date": last_p_date,
                        "num_payments": num_payments,
                        "option_id": o["payment_option_id"],
                        "changes": "none",
                        "status": "affordable_with_plan"
                    })

        # Candidate 4: wait (no changes)
        if "full_payment" in considered_methods and earliest_full_date:
            ef_date = parse_date(earliest_full_date)
            if ef_date <= desired_comp_date and ef_date != req_date:
                candidates.append({
                    "method": "wait",
                    "plan": f"{earliest_full_date}:{self._fmt(req_amount)}",
                    "cost": req_amount,
                    "first_date": ef_date,
                    "last_date": ef_date,
                    "num_payments": 1,
                    "option_id": "0",
                    "changes": "none",
                    "status": "affordable_later"
                })

        # Candidate 5: Spending changes
        has_ontime_no_change = any(
            c["method"] in ("full_payment", "installments", "partial_payment") and c["changes"] == "none" and c["last_date"] <= desired_comp_date
            for c in candidates
        )

        if not has_ontime_no_change:
            willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
            willing_reduce = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_reduce", "").split("|") if c.strip())

            u_events = self.data["events"]
            protected_cats = set(c.strip() for c in profile.get("expense_categories_to_protect", "").split("|") if c.strip())

            past_evs = [e for e in u_events if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]

            stop_candidates = []
            reduce_candidates = []

            seen_stop_desc = set()
            seen_reduce_desc = set()

            for e in reversed(past_evs):
                cat = e["category"]
                desc = e["description"]
                flex = e["flexibility"]

                if cat in protected_cats:
                    continue

                if cat in willing_stop and flex in ("stoppable", "reducible_or_stoppable") and desc not in seen_stop_desc:
                    stop_candidates.append(e)
                    seen_stop_desc.add(desc)

                if cat in willing_reduce and flex in ("reducible", "reducible_or_stoppable") and desc not in seen_reduce_desc:
                    if e.get("minimum_allowed_amount"):
                        reduce_candidates.append(e)
                        seen_reduce_desc.add(desc)

            action_combos = []
            for se in stop_candidates:
                action_combos.append([f"stop:{se['event_id']}"])
            for re in reduce_candidates:
                action_combos.append([f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])
            for se in stop_candidates:
                for re in reduce_candidates:
                    if se["event_id"] != re["event_id"]:
                        action_combos.append([f"stop:{se['event_id']}", f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])
            for i, se1 in enumerate(stop_candidates):
                for se2 in stop_candidates[i+1:]:
                    action_combos.append([f"stop:{se1['event_id']}", f"stop:{se2['event_id']}"])
            for i, se1 in enumerate(stop_candidates):
                for se2 in stop_candidates[i+1:]:
                    for re in reduce_candidates:
                        action_combos.append([f"stop:{se1['event_id']}", f"stop:{se2['event_id']}", f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])

            for actions in action_combos[:60]:
                b_sc, min_sc, _ = self.simulator.simulate_balance(user_id, req_date_str, actions)
                safe_sc = min(req_amount, max(0.0, min_sc - min_bal))

                # Also calculate savings before next salary or deadline
                # Allow slight gap if spending change significantly improves position
                is_sc_safe = (safe_sc >= req_amount) or (req_amount - safe_sc <= req_amount * 0.1 and safe_sc > base_safe_to_pay)

                changes_str = "|".join(actions)

                if is_sc_safe and "full_payment" in considered_methods:
                    candidates.append({
                        "method": "full_payment",
                        "plan": f"{req_date_str}:{self._fmt(req_amount)}",
                        "cost": req_amount,
                        "first_date": req_date,
                        "last_date": req_date,
                        "num_payments": 1,
                        "option_id": "0",
                        "changes": changes_str,
                        "status": "affordable_with_plan"
                    })
                    break

                if "installments" in considered_methods:
                    opts = self.options_by_request.get(req_id, [])
                    for o in opts:
                        if o["payment_method"] != "installments":
                            continue
                        num_payments = int(o["number_of_payments"])
                        freq_days = int(o["payment_frequency_days"] or 30)
                        duration_days = (num_payments - 1) * freq_days
                        duration_months = math.ceil(duration_days / 30.0)
                        if max_inst_months is not None and duration_months > max_inst_months:
                            continue
                        first_p_date = parse_date(o["first_payment_date"])
                        p_dates = [first_p_date + timedelta(days=k * freq_days) for k in range(num_payments)]
                        last_p_date = p_dates[-1]
                        if last_p_date > desired_comp_date:
                            continue
                        p_amt = float(o["payment_amount"])
                        safe_inst = self._check_installment_safe(b_sc, p_dates, p_amt, req_date, min_bal, end_date)
                        if safe_inst:
                            plan_str = "|".join(f"{format_date(pd)}:{self._fmt(p_amt)}" for pd in p_dates)
                            candidates.append({
                                "method": "installments",
                                "plan": plan_str,
                                "cost": float(o["total_payable_amount"]),
                                "first_date": first_p_date,
                                "last_date": last_p_date,
                                "num_payments": num_payments,
                                "option_id": o["payment_option_id"],
                                "changes": changes_str,
                                "status": "affordable_with_plan"
                            })
                            break

        if not candidates:
            return {
                "request_id": req_id,
                "amount_safe_to_pay": round(amount_safe_to_pay, 2),
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": earliest_full_date,
                "spending_changes_needed": "none",
            }

        status_priority = {"affordable_now": 0, "affordable_with_plan": 1, "affordable_later": 2}

        def rank_key(c):
            completed_on_time = (c["last_date"] <= desired_comp_date)
            no_changes = (c["changes"] == "none")
            opt_num = 999999
            if c["option_id"].startswith("payment_option_"):
                opt_num = int(c["option_id"].replace("payment_option_", ""))
            return (
                0 if completed_on_time else 1,
                status_priority.get(c["status"], 2),
                0 if no_changes else 1,
                c["cost"],
                c["first_date"],
                c["num_payments"],
                opt_num
            )

        candidates.sort(key=rank_key)
        best = candidates[0]

        return {
            "request_id": req_id,
            "amount_safe_to_pay": round(amount_safe_to_pay, 2),
            "affordability_status": best["status"],
            "recommended_payment_method": best["method"],
            "payment_plan": best["plan"],
            "earliest_date_for_full_payment": earliest_full_date if best["status"] != "affordable_now" else req_date_str,
            "spending_changes_needed": best["changes"],
        }

    def _fmt(self, amount):
        if amount == int(amount):
            return str(int(amount))
        return f"{amount:.2f}".rstrip("0").rstrip(".")

engine = PrecisionEngine(data)

correct_s = 0
correct_m = 0
samples = data["sample_requests"]
for s in samples:
    res = engine.evaluate_request(s)
    sc = res["affordability_status"] == s["affordability_status"]
    mc = res["recommended_payment_method"] == s["recommended_payment_method"]
    if sc: correct_s += 1
    if mc: correct_m += 1
    if not sc or not mc:
        print(f"[MISS {s['request_id']}] got_s={res['affordability_status']!r}, exp_s={s['affordability_status']!r} | got_m={res['recommended_payment_method']!r}, exp_m={s['recommended_payment_method']!r} | safe={res['amount_safe_to_pay']}/{s['amount_safe_to_pay']} | chg={res['spending_changes_needed']}/{s['spending_changes_needed']} | early={res['earliest_date_for_full_payment']}/{s['earliest_date_for_full_payment']}")

print(f"\nFinal Precision Status: {correct_s}/{len(samples)} ({correct_s/len(samples)*100:.1f}%), Method: {correct_m}/{len(samples)} ({correct_m/len(samples)*100:.1f}%)")
