"""Test ranking priority: on_time -> no_changes -> status -> cost."""
import os, sys, statistics, math
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import load_all_data
from simulator import parse_date, format_date

data = load_all_data()

from scratch_test import PrecisionSimulator, PrecisionEngine

engine = PrecisionEngine(data)

def rank_key_fixed(c, desired_comp_date):
    completed_on_time = (c["last_date"] <= desired_comp_date)
    no_changes = (c["changes"] == "none")
    status_priority = {"affordable_now": 0, "affordable_with_plan": 1, "affordable_later": 2}
    opt_num = 999999
    if c["option_id"].startswith("payment_option_"):
        opt_num = int(c["option_id"].replace("payment_option_", ""))
    return (
        0 if completed_on_time else 1,
        0 if no_changes else 1,
        status_priority.get(c["status"], 2),
        c["cost"],
        c["first_date"],
        c["num_payments"],
        opt_num
    )

# Override evaluate_request with updated rank_key
orig_eval = engine.evaluate_request

def eval_fixed(request):
    req_id = request["request_id"]
    user_id = request["user_id"]
    req_date_str = request["request_date"]
    req_date = parse_date(req_date_str)
    req_amount = float(request["requested_amount"])
    desired_comp_str = request["desired_completion_date"]
    desired_comp_date = parse_date(desired_comp_str)
    allows_partial = request["allows_partial_payment"].strip().lower() in ("true", "1", "yes")

    profile = engine.profiles[user_id]
    min_bal = float(profile["minimum_balance_to_keep"])
    considered_methods = set(m.strip() for m in profile["payment_methods_user_will_consider"].split("|") if m.strip())
    max_inst_months = None
    if profile.get("max_installment_months"):
        try:
            max_inst_months = int(profile["max_installment_months"])
        except ValueError:
            pass

    balances, min_proj, _ = engine.simulator.simulate_balance(user_id, req_date_str)
    end_date = req_date + timedelta(days=90)

    base_safe_to_pay = max(0.0, min_proj - min_bal)
    amount_safe_to_pay = min(req_amount, base_safe_to_pay)

    earliest_full_date = engine.find_earliest_full_payment_date(user_id, req_date_str, req_amount)

    candidates = []

    # Candidate 1: full_payment (no changes)
    if "full_payment" in considered_methods and amount_safe_to_pay >= req_amount:
        candidates.append({
            "method": "full_payment",
            "plan": f"{req_date_str}:{engine._fmt(req_amount)}",
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
            "plan": f"{req_date_str}:{engine._fmt(amount_safe_to_pay)}|{earliest_full_date}:{engine._fmt(rem_amt)}",
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
        opts = engine.options_by_request.get(req_id, [])
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
            safe_inst = engine._check_installment_safe(balances, p_dates, p_amt, req_date, min_bal, end_date)

            if safe_inst:
                plan_str = "|".join(f"{format_date(pd)}:{engine._fmt(p_amt)}" for pd in p_dates)
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
                "plan": f"{earliest_full_date}:{engine._fmt(req_amount)}",
                "cost": req_amount,
                "first_date": ef_date,
                "last_date": ef_date,
                "num_payments": 1,
                "option_id": "0",
                "changes": "none",
                "status": "affordable_later"
            })

    # Candidate 5: Spending changes
    willing_stop = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_stop", "").split("|") if c.strip())
    willing_reduce = set(c.strip() for c in profile.get("expense_categories_user_is_willing_to_reduce", "").split("|") if c.strip())

    u_events = engine.data["events"]
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
        b_sc, min_sc, _ = engine.simulator.simulate_balance(user_id, req_date_str, actions)
        safe_sc = min(req_amount, max(0.0, min_sc - min_bal))

        is_sc_safe = (safe_sc >= req_amount) or (req_amount - safe_sc <= req_amount * 0.1 and safe_sc > base_safe_to_pay)

        changes_str = "|".join(actions)

        if is_sc_safe and "full_payment" in considered_methods:
            candidates.append({
                "method": "full_payment",
                "plan": f"{req_date_str}:{engine._fmt(req_amount)}",
                "cost": req_amount,
                "first_date": req_date,
                "last_date": req_date,
                "num_payments": 1,
                "option_id": "0",
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

    candidates.sort(key=lambda c: rank_key_fixed(c, desired_comp_date))
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

engine.evaluate_request = eval_fixed

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

print(f"\nFinal Fixed Status: {correct_s}/{len(samples)} ({correct_s/len(samples)*100:.1f}%), Method: {correct_m}/{len(samples)} ({correct_m/len(samples)*100:.1f}%)")
