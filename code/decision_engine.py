import os
import sys
import math
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulator import CashFlowSimulator, parse_date, format_date


def fmt_amt(amount):
    """Format a monetary amount without scientific notation, dropping trailing zeros."""
    if amount == int(amount):
        return str(int(amount))
    # Up to 2 decimal places, strip trailing zeros
    s = f"{amount:.2f}".rstrip("0").rstrip(".")
    return s


class DecisionEngine:
    def __init__(self, data):
        self.data = data
        self.profiles = data["profiles"]
        self.options_by_request = {}
        for o in data["payment_options"]:
            req_id = o["request_id"]
            if req_id not in self.options_by_request:
                self.options_by_request[req_id] = []
            self.options_by_request[req_id].append(o)
        self.simulator = CashFlowSimulator(data)

    def _check_installment_safe(self, balances, p_dates, p_amt, req_date, min_bal, end_date):
        """
        Check if each installment payment is safe on its due date.
        For each payment date, we check: balance_at_payment_date >= min_bal + payment_amount.
        This allows salary top-ups between payments to make subsequent payments feasible.
        """
        for pd in p_dates:
            if pd not in balances:
                continue  # payment date beyond our simulation window
            if balances[pd] - p_amt < min_bal:
                return False
        return True

    def find_earliest_full_payment_date(self, user_id, request_date_str, requested_amount, spending_changes=None):
        """
        Find the earliest date on which the user can safely make a full payment.
        Two conditions must both hold:
        1. On the candidate date: balance >= min_bal + requested_amount (can make the payment)
        2. On all subsequent days: balance >= min_bal (natural cashflow stays above minimum,
           independent of whether the payment could be made again — payment already happened)
        """
        req_date = parse_date(request_date_str)
        profile = self.profiles[user_id]
        min_bal = float(profile["minimum_balance_to_keep"])

        base_balances, _, _ = self.simulator.simulate_balance(user_id, request_date_str, spending_changes)

        for d_idx in range(91):
            cand_date = req_date + timedelta(days=d_idx)
            # When paying requested_amount on cand_date, balance for the 30-day cycle is checked
            safe_from_cand = True
            for t_idx in range(d_idx, min(d_idx + 30, 91)):
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

        # 1. Base simulation (no spending changes)
        balances, min_proj, _ = self.simulator.simulate_balance(user_id, req_date_str)
        end_date = req_date + timedelta(days=90)

        # Amount safe to pay: the maximum we can pay today such that balance stays >= min_bal
        # This is the balance TODAY minus min_bal (capped at req_amount)
        # But we must also ensure future cash flow can sustain it, so use min_proj
        base_safe_to_pay = max(0.0, min_proj - min_bal)
        amount_safe_to_pay = min(req_amount, base_safe_to_pay)

        earliest_full_date = self.find_earliest_full_payment_date(user_id, req_date_str, req_amount)

        # Candidate plans: list of dicts
        candidates = []

        # Candidate 1: full_payment (no changes)
        if "full_payment" in considered_methods and amount_safe_to_pay >= req_amount:
            candidates.append({
                "method": "full_payment",
                "plan": f"{req_date_str}:{fmt_amt(req_amount)}",
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
                "plan": f"{req_date_str}:{fmt_amt(amount_safe_to_pay)}|{earliest_full_date}:{fmt_amt(rem_amt)}",
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
                # check duration vs max_installment_months
                duration_days = (num_payments - 1) * freq_days
                duration_months = math.ceil(duration_days / 30.0)
                if max_inst_months is not None and duration_months > max_inst_months:
                    continue

                first_p_date = parse_date(o["first_payment_date"])
                p_dates = [first_p_date + timedelta(days=k * freq_days) for k in range(num_payments)]
                last_p_date = p_dates[-1]

                # Check completion date
                if last_p_date > desired_comp_date:
                    continue

                # Check cashflow safety using running balance simulation
                p_amt = float(o["payment_amount"])
                safe_inst = self._check_installment_safe(balances, p_dates, p_amt, req_date, min_bal, end_date)

                if safe_inst:
                    plan_str = "|".join(f"{format_date(pd)}:{fmt_amt(p_amt)}" for pd in p_dates)
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

        # Candidate 4: wait (no changes) — only if earliest_full_date is within deadline
        if "full_payment" in considered_methods and earliest_full_date:
            ef_date = parse_date(earliest_full_date)
            if ef_date <= desired_comp_date and ef_date != req_date:
                candidates.append({
                    "method": "wait",
                    "plan": f"{earliest_full_date}:{fmt_amt(req_amount)}",
                    "cost": req_amount,
                    "first_date": ef_date,
                    "last_date": ef_date,
                    "num_payments": 1,
                    "option_id": "0",
                    "changes": "none",
                    "status": "affordable_later"
                })

        # Candidate 5: Spending changes (try when no full_payment/installments/partial_payment without changes)
        has_good_candidate = any(
            c["method"] in ("full_payment", "installments", "partial_payment") and c["changes"] == "none"
            for c in candidates
        )
        if not has_good_candidate:
            willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
            willing_reduce = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_reduce", "").split("|") if c.strip())

            # Find candidates from past events
            u_events = self.data["events"]
            protected_cats = set(c.strip() for c in profile.get("expense_categories_to_protect", "").split("|") if c.strip())

            past_evs = [e for e in u_events if e["user_id"] == user_id and e["settlement_date"] < req_date_str and e["amount"]]

            # Find stoppable and reducible events (most recent per description)
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

            # Try up to 3 spending changes (all combos up to 3 actions)
            action_combos = []
            # single stop
            for se in stop_candidates:
                action_combos.append([f"stop:{se['event_id']}"])
            # single reduce
            for re in reduce_candidates:
                action_combos.append([f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])
            # pair of stop + reduce
            for se in stop_candidates:
                for re in reduce_candidates:
                    if se["event_id"] != re["event_id"]:
                        action_combos.append([f"stop:{se['event_id']}", f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])
            # pair of stops
            for i, se1 in enumerate(stop_candidates):
                for se2 in stop_candidates[i+1:]:
                    action_combos.append([f"stop:{se1['event_id']}", f"stop:{se2['event_id']}"])
            # triple: stop + stop + reduce
            for i, se1 in enumerate(stop_candidates):
                for se2 in stop_candidates[i+1:]:
                    for re in reduce_candidates:
                        action_combos.append([f"stop:{se1['event_id']}", f"stop:{se2['event_id']}", f"reduce_to:{re['event_id']}:{re['minimum_allowed_amount']}"])

            for actions in action_combos[:50]:  # limit combos for performance
                b_sc, min_sc, _ = self.simulator.simulate_balance(user_id, req_date_str, actions)
                safe_sc = min(req_amount, max(0.0, min_sc - min_bal))
                changes_str = "|".join(actions)

                if safe_sc >= req_amount and "full_payment" in considered_methods:
                    candidates.append({
                        "method": "full_payment",
                        "plan": f"{req_date_str}:{fmt_amt(req_amount)}",
                        "cost": req_amount,
                        "first_date": req_date,
                        "last_date": req_date,
                        "num_payments": 1,
                        "option_id": "0",
                        "changes": changes_str,
                        "status": "affordable_with_plan"
                    })
                    break

                # Also try installments with spending changes
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
                            plan_str = "|".join(f"{format_date(pd)}:{fmt_amt(p_amt)}" for pd in p_dates)
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

        # Filter and Rank Candidates
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

        # Ranking key:
        # 1. Complete by desired_completion_date (True before False)
        # 2. Status priority: affordable_now > affordable_with_plan > affordable_later
        # 3. No spending changes (True before False)
        # 4. Minimize total cost
        # 5. Start earlier (first_date)
        # 6. Fewer payments
        # 7. Lowest payment_option_id
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

        # Determine affordability_status for the result
        return {
            "request_id": req_id,
            "amount_safe_to_pay": round(amount_safe_to_pay, 2),
            "affordability_status": best["status"],
            "recommended_payment_method": best["method"],
            "payment_plan": best["plan"],
            "earliest_date_for_full_payment": earliest_full_date if best["status"] != "affordable_now" else req_date_str,
            "spending_changes_needed": best["changes"],
        }


if __name__ == "__main__":
    from data_loader import load_all_data
    data = load_all_data()
    engine = DecisionEngine(data)
    for s in data["sample_requests"][:10]:
        res = engine.evaluate_request(s)
        print(f"[{s['request_id']}] Status: {res['affordability_status']} (exp: {s['affordability_status']}) | Method: {res['recommended_payment_method']} (exp: {s['recommended_payment_method']})")
        print(f"   Plan: {res['payment_plan']}")
        print(f"   Expected: {s['payment_plan']}")
        print(f"   Changes: {res['spending_changes_needed']} (exp: {s['spending_changes_needed']}")
